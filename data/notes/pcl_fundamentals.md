# Passive Coherent Location (PCL) — Fundamentals

## What is PCL?

Passive Coherent Location (PCL) is a bistatic radar technique that exploits
existing non-cooperative third-party transmitters ("illuminators of opportunity")
rather than a dedicated transmitter. The system is passive — it only receives.

Key synonyms: passive radar, passive bistatic radar (PBR), commensal radar.

## System Architecture

```
[Illuminator of Opportunity]  (e.g., Starlink satellite)
        |                \
   Direct Path            Reflected Path
  (Reference Rx)         (Surveillance Rx)
        |                        |
   [ADC + IQ]              [ADC + IQ]
        \                       /
         \                     /
          [PCL Processing Chain]
```

### Reference Channel
- Captures direct-path signal from illuminator
- High-gain antenna pointed at transmitter
- Provides matched filter kernel for cross-correlation
- Must have high SNR (>20 dB ideal)

### Surveillance Channel
- Captures scene reflections
- Wider beam covering area of interest
- Contains: target returns + direct path leakage + clutter + noise

## Processing Chain

### Step 1: Direct Path Interference Cancellation
Remove strong direct path signal from surveillance channel.

**ECA (Extensive Cancellation Algorithm)**:
```
s_surv_clean = s_surv - H × s_ref
H = (S_ref^H S_ref)^(-1) S_ref^H s_surv   [least squares]
```
where H is the channel matrix including time delays and Doppler shifts.

**ECA-B (Batch ECA)**: Process in overlapping blocks for time-varying channel.
Recommended for STARDAR (fast-moving Starlink satellite).

**ECA-S (Sliding ECA)**: Sliding window version, better for non-stationary clutter.

### Step 2: Range-Doppler Cross-Correlation (CAF)
Compute the Cross-Ambiguity Function (CAF):
```
χ(τ, f_d) = ∫ s_surv(t) × conj(s_ref(t-τ)) × exp(j2πf_d×t) dt
```
Implemented via FFT:
```
χ[n, m] = IFFT_τ { FFT_t{s_surv(t)} × conj(FFT_t{s_ref(t)}) }
```
Output: 2D Range-Doppler map, axes: bistatic range τ×c and Doppler f_d.

### Step 3: CFAR Detection
Apply 2D CA-CFAR to Range-Doppler map → detection list.

### Step 4: Target Localisation
From bistatic range R_bi and Doppler f_d:
- R_bi = c × τ defines an ellipsoid with Tx and Rx as foci
- f_d gives rate of change of R_bi
- Multiple transmitters → intersection of ellipsoids → point location

## Bistatic Geometry and the CAF

The CAF peak appears at:
- τ = (R_T + R_R) / c    [bistatic range delay]
- f_d = -(1/λ) × d(R_T + R_R)/dt   [bistatic Doppler]

For a stationary target: f_d is determined only by satellite motion.
For a moving target: f_d has an additional component from target velocity.

## Waveform Properties for PCL

Key figure of merit: **Ambiguity Function** of the illuminator signal.
Ideal: thumbtack shape (narrow peak, low sidelobes in range and Doppler).

### OFDM (Starlink waveform class):
- Wide bandwidth → fine range resolution
- Random-like sub-carriers → low range sidelobes
- Periodic structure (OFDM symbol duration) → Doppler ambiguities at 1/T_symbol
- In practice: excellent ambiguity function for radar

### FM Radio (reference illuminator):
- ~100 kHz bandwidth → ~1.5 km range resolution (poor)
- Familiar PCL illuminator in literature

### DVB-T (digital TV):
- 8 MHz bandwidth → ~19 m range resolution (good)
- Most studied PCL illuminator

### Starlink Ku-band:
- Up to 250 MHz bandwidth → 0.6 m range resolution (excellent)
- OFDM-based → good ambiguity function
- High EIRP (~37 dBW) → good SNR
- LEO → fast Doppler evolution, natural SAR aperture

## Performance Metrics

### Detection Range (FM radio illuminator baseline):
- Aircraft (σ=10m²): ~150 km
- Ships (σ=1000m²): >300 km

### STARDAR Expected Performance (Ku-band, terrain mapping):
- Range resolution: 0.6 m (250 MHz)
- Azimuth resolution: ~1-10 m (geometry + integration time dependent)
- SNR at 20 km: ~+29 dB (full pass, 480s integration)
- SNR at 100 km: ~+15 dB (full pass)

## Griffiths-Baker (2005) Key Results

From the foundational IEE PCL paper (paraphrased):
1. PCL exploits broadcast signals with wide coverage and high power
2. Performance limited by: waveform ambiguity, direct path interference, clutter
3. FM and VHF TV give 100-200 km detection of aircraft
4. Processing gain = time-bandwidth product B×T_int
5. Key advantage: covert operation, no RF emission required

## Practical Challenges

1. **Direct path interference**: 80-100 dB stronger than target return
   Solution: ECA/ECA-B cancellation

2. **Clutter**: Buildings, terrain, sea surface
   Solution: Doppler filtering (moving targets), spatial filtering

3. **Waveform variability**: Illuminator may change content/power
   Solution: Continuous reference capture, adaptive processing

4. **Bistatic geometry**: Isorange contours are ellipses, not circles
   Solution: Bistatic coordinate transformation

5. **Synchronisation**: Need coherence between channels
   Solution: GPS-disciplined oscillator (GPSDO) — see sync notes

## Relevance to STARDAR

STARDAR is a PCL system with:
- Illuminator: Starlink LEO satellite (vs FM radio in classical PCL)
- Advantage over classical PCL: much higher bandwidth (250 MHz vs 100 kHz)
- New challenge: satellite moves fast → geometry changes during integration
- Application: terrain SAR imaging (vs moving target detection in classical PCL)
