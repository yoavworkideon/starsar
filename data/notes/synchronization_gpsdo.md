# Synchronisation & GPSDO for Passive Bistatic Radar — STARDAR Reference

## The Synchronisation Problem

In a monostatic radar, the transmitter and receiver share one clock — coherence is trivial.
In a bistatic/PCL system, transmitter and receiver are separated; any clock offset or drift
produces a phase error that corrupts the CAF output.

Two categories of sync error:

| Error Type | Effect on CAF | Tolerable Limit |
|------------|--------------|-----------------|
| Time offset Δt | Range bias: ΔR = c×Δt | < λ/2c (sub-wavelength for Doppler) |
| Frequency offset Δf | Doppler bias: Δf_d = Δf | < 1/(2×T_int) |
| Phase noise / drift | CAF peak broadening, sidelobe rise | Phase noise PSD < -70 dBc/Hz at 1 kHz |

For STARDAR (f_c = 12 GHz, T_int up to 480 s, B = 250 MHz):
- Allowable timing jitter: < 1 ns (for sub-0.3m range error)
- Allowable frequency offset: < 1 mHz (for 480 s integration)
- Phase noise dominates for long CPI — oscillator quality critical

## GPS-Disciplined Oscillator (GPSDO) Architecture

A GPSDO combines:
1. **GPS timing receiver** — provides 1PPS (pulse per second) with ~10-50 ns absolute accuracy
2. **OCXO or TCXO** — provides clean short-term phase noise
3. **Phase-locked loop (PLL)** — disciplines oscillator to GPS 1PPS over seconds–minutes

```
GPS Antenna → GPS Receiver → 1 PPS signal ─┐
                                             ├─→ PLL/Divider → Disciplined 10 MHz
OCXO/TCXO ────────────────────────────────┘     (or 100 MHz) Reference
```

### Key Specifications (Sandenbergh UCT Thesis, 2019)

From "Synchronising coherent networked radar using low-cost GPS-disciplined oscillators":

- **GPS 1PPS accuracy**: 10-50 ns RMS (vs UTC, clear sky, open sky)
- **OCXO free-running stability**: 1-10 ppb (parts per billion) over minutes
- **GPSDO combined**: < 50 ns RMS timing, < 0.05 ppb frequency
- **Phase noise at 10 MHz reference**: typically -130 dBc/Hz at 1 kHz offset

### Timing Bandwidth Constraint (Critical for STARDAR)

GPS 1PPS accuracy of 50 ns limits exploitable bandwidth:

```
Maximum unambiguous range from GPS timing: ΔR = c × Δt_GPS
50 ns → 15 m ambiguity (range measurement uncertainty)

For PCL: only useful if range bin > timing uncertainty
δr_min = c/(2B) > c × Δt_GPS
→ B < 1/(2 × Δt_GPS) = 1/(2 × 50ns) = 10 MHz
```

**Sandenbergh finding**: GPS timing limits coherent bandwidth for range-sync to ~10 MHz
(some sources cite 37.5 MHz for 13.3 ns timing). For STARDAR 250 MHz, GPS sync alone
is insufficient for fine range; must use **signal-level synchronisation** (SLS).

## Signal-Level Synchronisation (SLS)

Also called "direct-path synchronisation" or "self-calibration":

The direct-path reference signal itself is used to estimate and correct residual
sync errors — the known signal structure enables sub-sample timing estimation.

### Algorithm:
1. Capture direct path on reference channel (known delay τ_0 from geometry)
2. Cross-correlate against pilot/preamble known structure in signal
3. Estimate: Δt_residual from CAF peak offset, Δφ from phase of peak
4. Apply correction to surveillance channel before CAF computation

For Starlink OFDM waveform:
- OFDM pilots (spaced sub-carriers) → frequency error estimation (like AFC)
- Cyclic prefix → timing synchronisation (standard OFDM sync)
- After SLS: residual timing error < 1 sample period = 1/B ≈ 4 ns at 250 MHz

### Practical SLS Accuracy:
- **Timing**: < 1/B = 4 ns (at 250 MHz) → residual range error < 0.6 m
- **Frequency**: < 1/(2×T_int) → coherent over full pass
- **Phase**: sufficient for SAR focusing (< π/8 rad residual)

## Clock Error Budget for STARDAR

| Source | Timing Error | Frequency Error | Notes |
|--------|-------------|-----------------|-------|
| GPSDO (timing baseline) | 10-50 ns | 0.05 ppb | Before SLS |
| SLS correction | < 4 ns | < 0.001 ppb | After signal-level sync |
| Residual (post-SLS) | < 1 ns | negligible | Meets STARDAR req |

**Conclusion**: GPSDO provides coarse sync, SLS provides fine sync.
Together they meet STARDAR requirements for 250 MHz bandwidth, 480 s integration.

## Impact on SAR Processing

### Phase Error During Integration
Phase error φ_err(t) during synthetic aperture must satisfy (SAR focusing criterion):
```
|φ_err(t)| < π/4   for ≥ -1 dB peak loss
|φ_err(t)| < π/8   for ≥ -0.1 dB peak loss (high quality imaging)
```

For a frequency offset Δf_osc:
```
φ_err(t) = 2π × f_c × Δf_osc/f_ref × t
At t = T_int = 480 s, f_c = 12 GHz:
Δf_osc < π/(4 × 2π × f_c × T_int) = 1/(8 × 12e9 × 480) ≈ 2.7e-14 relative
→ Δf < 0.027 ppb (very tight)
```

This is **tighter than GPSDO alone** → SLS mandatory for 480 s integration.

For shorter integration (T_int = 10 s, azimuth strip mode):
```
Δf < 0.027 ppb × (480/10) = 1.3 ppb (relaxed — GPSDO alone sufficient)
```

### Residual Phase after SLS

Post-SLS residual phase modelled as random walk (oscillator phase noise):
```
σ_φ(τ) ≈ 2π × f_c × σ_t(τ)
```
where σ_t(τ) is timing jitter integrated over interval τ.

For a 10 MHz OCXO with -130 dBc/Hz at 1 kHz:
- σ_φ over 10 s ≈ 0.05 rad (excellent, < π/8)
- σ_φ over 480 s ≈ 0.3 rad (marginal, SLS update every 10 s needed)

**Recommendation**: Apply SLS correction every OFDM frame (~1 ms) during processing.
This makes residual phase error dominated by interpolation, not oscillator drift.

## Hardware Recommendations for STARDAR

### Reference Channel GPSDO:
- **Jackson Labs Fury** or **Leo Bodnar GPS Reference** (< $300)
  - 10 MHz output, 1PPS, < 20 ns timing, < 0.3 ppb
- **u-blox LEA-M8F** GPSDO module (embedded, < $50)
  - Less clean phase noise but adequate with SLS

### Surveillance Channel:
- Same GPSDO model, GPS antenna at same location (roof/mast)
- Or: single GPSDO, coax-distribute 10 MHz reference to both ADCs
  - Eliminates inter-channel phase error entirely
  - Recommended if channels < 50m apart

### ADC Reference:
- Both ADCs locked to same 10 MHz GPSDO output
- ADC clock = 10 MHz × PLL multiplier (e.g., ×25 = 250 MHz sample clock)
- Cable delay between GPSDO and ADC: calibrate once, apply fixed correction

## Subclutter Improvement from Coherent Integration

Sandenbergh (2019) measured real-world coherent integration gain:
- **~30 dB subclutter visibility** improvement over incoherent detection
- Achieved with GPSDO + SLS on 1 GHz bandwidth radar
- Key metric: ratio of moving target return to static clutter after Doppler filtering

For STARDAR terrain mapping (static targets, no Doppler):
- Coherent integration still provides √(N) voltage gain = 10×log10(N)/2 in SNR
- 480 s at 250 MHz: N ≈ 480 × 250e6 = 1.2×10^11 samples → theoretical gain +55 dB
- Practical: limited by phase coherence (~30-40 dB achievable with good GPSDO + SLS)

## Summary for STARDAR Implementation

1. **Both channels on same GPSDO** (coax share 10 MHz reference) — eliminates inter-channel error
2. **SLS per OFDM frame** during offline processing — corrects residual Starlink clock offset
3. **GPSDO absolute timing** used for orbital geometry calculation only (coarse sync)
4. **Do NOT rely on GPS timing for range resolution** at 250 MHz — SLS is mandatory
5. For field deployment without coax link: two matched GPSDOs + SLS correction achieves same result

## Sources
- Sandenbergh, J.S. (2019). "Synchronising coherent networked radar using low-cost GPS-disciplined oscillators." PhD thesis, UCT.
- Griffiths, H.D. & Baker, C.J. (2005). "Passive coherent location radar systems." IEE Proc. Radar, Sonar, Nav.
- Ulander et al. (2021). "Bistatic SAR coherence: clock and phase sync requirements." IEEE TGRS.
- Eigel, R. (2020). "OFDM waveform synchronisation for passive radar." PhD thesis, Dresden.
