# Passive Bistatic SAR — Theory Notes

## What is Passive Bistatic SAR?

Passive bistatic SAR (PB-SAR) is a SAR imaging modality that exploits
signals of opportunity (SoO) — transmitters not under the radar operator's
control — as illuminators. The receiver passively collects the reflected
energy and processes it to form a focused image.

Key distinction from active SAR:
- No dedicated transmitter — uses existing RF infrastructure
- Cannot control waveform, timing, or power
- Must solve the "reference signal problem" — obtaining a coherent reference
  for matched filtering

## The Starlink Case

Starlink operates in Ku-band (~10.7–12.7 GHz downlink to user terminals).
Each satellite transmits spot beams with an estimated EIRP of ~35–40 dBW.
At 550 km altitude, the satellite moves at ~7.58 km/s, creating a rich
Doppler history and enabling synthetic aperture formation from a fixed
ground receiver.

### Why Starlink is attractive:
1. Low altitude (550 km) → lower path loss than GEO (~35,000 km)
2. High velocity → fast aperture synthesis, good Doppler discrimination
3. Wide bandwidth (up to 250 MHz per channel) → fine range resolution
4. Dense constellation → frequent passes, potential multi-static geometry
5. Ka-band inter-beam frequency reuse → multiple simultaneous spot beams

### Key challenges:
1. Proprietary/encrypted waveform — cannot generate perfect reference
2. Unknown beam scheduling — unclear which spot beam illuminates scene
3. Rapid orbital motion — geometry changes fast, requires precise ephemeris
4. Multiple satellites visible simultaneously → interference between passes

## The Reference Signal Problem

In passive radar, the reference channel captures the direct-path signal
from the transmitter. This serves as the matched filter kernel for range
compression of the surveillance channel.

Three approaches for Starlink:

### A) Direct Path Capture (Recommended for STARDAR)
- Point a directive antenna (or Starlink terminal phased array) at the satellite
- Record the direct-path IQ signal
- Use this as a "blind reference" for cross-correlation
- Pros: works without knowing the waveform; simple hardware
- Cons: noise on reference degrades SNR (reference noise figure matters)
  SNR loss ≈ 10*log10(1 + 1/SNR_ref) — small if SNR_ref >> 0 dB

### B) Blind Waveform Estimation
- Estimate the transmitted waveform from the received signal
- Useful when direct path is not separable (e.g., reflection-dominated)
- Active research area — methods: CLEAN, iterative deconvolution, ML-based
- More complex but can improve coherence in challenging geometries

### C) Waveform Reconstruction from Standards
- If Starlink uses a known modulation (e.g., DVB-S2X-derived)
- Reconstruct waveform from symbol decisions after decryption
- Not applicable without decryption keys

## SAR Image Formation for Bistatic Geometry

Standard SAR algorithms (RDA, ω-k, CSA) are designed for monostatic or
quasi-monostatic geometries. Bistatic SAR requires modifications.

### Back-Projection Algorithm (BPA)
Most general — works for arbitrary bistatic geometry:

```
I(x, y) = Σ_t  s_rc(t, τ_bi(x,y,t)) * exp(j * 2π * f_c * τ_bi(x,y,t))
```

Where:
- s_rc = range-compressed signal
- τ_bi(x,y,t) = bistatic time delay = (RT(x,y,t) + RR(x,y)) / c
- f_c = carrier frequency

Computational cost: O(N² * M) where N = image pixels per side, M = pulses
For 1000x1000 image, 5000 pulses → 5×10⁹ operations → needs GPU

### Bistatic Range Migration Algorithm (BRMA)
Extension of RDA to bistatic case. Faster than BPA but requires:
- Slowly varying bistatic geometry (valid for long-baseline bistatic)
- Known range migration curve

### Omega-K for Bistatic (Modified Stolt)
Can be adapted for bistatic with approximations. Loses accuracy for
large bistatic angles (β > 30°).

**Recommendation for STARDAR Phase 1**: Use BPA — correctness over speed.
GPU implementation on AGX Orin will make it real-time capable.

## SNR Considerations for Integration Time

The key advantage of SAR over conventional radar is long coherent
integration time, which directly trades with SNR:

G_int = B * T_int  (coherent)

For T_int = 10s, B = 250 MHz: G_int = 54 dB
For T_int = 60s, B = 250 MHz: G_int = 62 dB
For T_int = 300s, B = 250 MHz: G_int = 69 dB

However, long integration requires:
1. Phase stability of transmitter over T_int
2. Target must not migrate more than a range cell during T_int
   → max T_int before migration: δr / v_target_radial
3. Doppler bandwidth must be < PRF (no Doppler aliasing)

## Bistatic RCS vs Monostatic RCS

Target RCS depends on the bistatic angle β:
- β = 0°: bistatic ≈ monostatic
- β > 0°: generally unpredictable, can be larger or smaller
- β → 180° (forward scatter): can be 20-40 dB enhancement for large targets
  (forward scatter enhancement — useful for detecting large targets)

For aircraft: monostatic RCS ≈ 1–15 m² (0–12 dBsm)
Forward scatter: can reach 100–10,000 m² (20–40 dBsm)

## Synchronization Requirements

Phase synchronization between reference and surveillance channels:
- Timing error Δt must satisfy: Δt << 1/B
  For B=250 MHz: Δt << 4 ns → GPS (1-PPS, ±10 ns) is marginal but workable
- Phase error Δφ must satisfy: Δφ << π/2 over T_int
  → Requires GPSDO (GPS-disciplined oscillator) with low phase noise
  Typical GPSDO: < 0.1 ps/s frequency stability → Δφ << 0.01 rad over 1s ✓

Position knowledge requirement:
- For coherent SAR: position error << λ/2 = 1.25 cm
- TLE accuracy: ~100-500 m → NOT sufficient for coherent processing
- Solution: use onboard ephemeris from Starlink terminal
  or differential GPS + precise orbit determination

## Multi-Static Configuration

With N receive antennas, each capturing a different aspect angle:

Benefits:
1. N times more data → N-fold coherent gain (if phases aligned)
2. Different bistatic angles → reduced speckle, better target classification
3. Cross-range resolution improvement via MIMO-SAR synthesis

Challenges:
1. Phase synchronization across all receivers (common clock required)
2. Increased data volume and processing complexity
3. Baseline calibration (sub-wavelength accuracy)

For STARDAR: beamforming array handles this naturally —
all elements share a common clock, phase coherence maintained by design.
