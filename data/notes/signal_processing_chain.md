# STARDAR Signal Processing Chain — Detailed Notes

## Overview

```
[Starlink Satellite Tx]
        |
        |--- Direct Path ---> [Reference Antenna + SDR]  → s_ref(t)
        |
        |--- Reflected -----> [Surveillance Array + SDR] → s_surv(t)

s_ref(t), s_surv(t) → [Processing Pipeline] → SAR Image I(x,y)
```

## Step 1: ADC and IQ Sampling

Both channels sampled at fs ≥ B (Nyquist).
For B = 250 MHz: fs = 300 MHz (with some guard band).

IQ demodulation at f_c = 12 GHz:
```
s(t) = Re{s_bb(t) * exp(j*2π*f_c*t)}
→ s_bb(t) = lowpass{ s(t) * exp(-j*2π*f_c*t) }
```

Output: complex baseband IQ samples at 300 MHz.
Storage: 4 bytes per sample (2x float16) → 300e6 * 4 = 1.2 GB/s per channel.
For 10s integration: 12 GB per channel → 24 GB total (ref + surv).

## Step 2: Direct Path Cancellation (DPC)

The surveillance channel contains a strong direct-path component (Starlink
signal arriving directly from satellite, not via target reflection).
This must be removed before cross-correlation.

Methods:
### a) Adaptive Filter (ECA — Extensive Cancellation Algorithm)
  Standard approach in passive radar.
  Model: s_surv = α * s_ref + s_target + noise
  Estimate α via least-squares: α̂ = (s_ref^H s_surv) / (s_ref^H s_ref)
  Residual: s_clean = s_surv - α̂ * s_ref

### b) Batch ECA (ECA-B)
  Process in blocks. More robust to time-varying channel.
  Recommended for STARDAR due to fast-moving satellite (geometry changes).

### c) Sequential Projection (SP)
  Project out the subspace spanned by s_ref and its Doppler-shifted copies.
  Best performance, highest complexity.

## Step 3: Range Compression

Cross-correlate surveillance with reference:
```
χ(t, τ) = ∫ s_surv(t + τ') * conj(s_ref(τ')) dτ'
         = IFFT{ FFT{s_surv} * conj(FFT{s_ref}) }
```

Output: range profile χ(t, τ) where τ is bistatic delay (proportional to R_bi).

Range axis: R_bi = c * τ  (bistatic range, in meters)
Range resolution: δR_bi = c / (2B)  (for small bistatic angle)

Note: This is equivalent to matched filtering with the reference waveform.
The cross-correlation peak appears at delay τ = (RT + RR) / c.

## Step 4: Range-Doppler Processing

Arrange range profiles into a 2D matrix: rows = slow time, cols = range.
Apply FFT along slow time (Doppler processing):

```
RD(f_d, τ) = Σ_n  χ(n*T_s, τ) * exp(-j*2π*f_d*n*T_s)
```

Where T_s = slow-time sample interval (≈ 1/PRF for pulsed, or processing interval for CW).

Output: Range-Doppler (RD) map.
- Range axis: bistatic range R_bi (m)
- Doppler axis: bistatic Doppler frequency f_d (Hz)

Doppler resolution: δf_d = 1 / T_int
For T_int = 10s: δf_d = 0.1 Hz

## Step 5: CFAR Detection

Apply Cell-Averaging CFAR (CA-CFAR) on the RD map:

For each cell under test (CUT):
1. Compute mean noise power in surrounding guard + reference cells
2. Set threshold: T = α * μ_noise where α = P_fa^(-1/N) - 1
3. Declare detection if |RD(f_d, τ)|² > T

Typical settings:
- Guard cells: 2 (range) x 2 (Doppler)
- Reference cells: 16 (range) x 8 (Doppler)
- P_fa = 1e-6

## Step 6: SAR Back-Projection

For each detected cell OR for grid imaging:

For each pixel (x, y) on the ground:
```python
for t in slow_time:
    RT = norm(sat_pos(t) - target_pos)
    RR = norm(rx_pos - target_pos)
    tau_bi = (RT + RR) / c
    I[x, y] += s_rc[t, round(tau_bi * fs)] * exp(j * 2*pi * fc * tau_bi)
```

GPU implementation: each pixel assigned to one CUDA thread.
Memory pattern: s_rc in L2 cache (read many times), I in global memory (write once).

## Coordinate Systems

**ECEF (Earth-Centered Earth-Fixed)**:
- Origin at Earth center
- x-axis: 0° longitude, equator
- z-axis: North Pole
- Used for: satellite ephemeris (TLE → ECEF), absolute positioning

**ENU (East-North-Up)**:
- Origin at receiver location
- Local tangent plane
- Used for: local scene geometry, target positioning

**Slant Range / Ground Range**:
- Slant range: actual 3D distance (used in processing)
- Ground range: horizontal distance (used in image display)
- Conversion: R_ground = sqrt(R_slant² - h²) where h = target height

## Key Parameters Summary

| Parameter | Value | Notes |
|-----------|-------|-------|
| f_c | 12 GHz | Center frequency |
| λ | 2.5 cm | Wavelength |
| B | 250 MHz | Max bandwidth |
| fs | 300 MHz | Sample rate |
| δR_bi | 0.6 m | Range resolution |
| δf_d (10s) | 0.1 Hz | Doppler resolution |
| δa (10s) | 9.2 m | Azimuth resolution |
| Max Doppler | ±304 kHz | From satellite velocity |
| Integration gain (10s) | 54 dB | G = B*T_int |

## Computational Complexity

| Step | Complexity | Notes |
|------|-----------|-------|
| DPC (ECA) | O(N²) | N = samples per CPI |
| Range compression | O(N log N) | FFT-based |
| RD map | O(M*N log M) | M = slow-time samples |
| CFAR | O(M*N) | Linear scan |
| Back-projection | O(P * M) | P = pixels, M = pulses |

For 1000x1000 image, 5000 pulses: BPA = 5×10⁹ MACs → needs GPU.
AGX Orin: ~275 TOPS → ~2.75s per image at 10s CPI.
