# STARDAR — System Architecture

**Passive Bistatic SAR using Starlink as Illuminator of Opportunity**

---

## 1. Concept Overview

STARDAR is a passive radar system that exploits Starlink LEO satellite downlink signals (~10.7–12.7 GHz, Ku-band) as an uncooperative illuminator of opportunity to form Synthetic Aperture Radar (SAR) images from a fixed ground-based receive array.

The system does not transmit — it only receives. No modification to or cooperation from SpaceX infrastructure is required.

```
                        [Starlink Satellite]
                        ~550 km altitude, ~7.6 km/s
                       /                          \
                      /  direct path               \ reflected path
                     /   (reference channel)        \ (surveillance channel)
                    v                                v
         [Starlink Terminal / SDR]           [Beamforming Array]
          phased array pointed at sat         ground-facing, ku-band
          captures direct path IQ             captures scene reflections
                    \                                /
                     \_______ [Processing Unit] ____/
                              cross-correlation
                              range-Doppler map
                              SAR image formation
```

---

## 2. Physical Requirements Checklist

| Requirement | Status | Solution |
|-------------|--------|----------|
| Illuminator motion (relative to fixed receiver) | ✅ | Starlink LEO, ~7.6 km/s, ~8 min pass |
| Signal bandwidth ≥ 15 MHz | ✅ | Up to ~250 MHz per Ku-band channel |
| Azimuth resolution (Doppler rate) | ✅ | High velocity → rich Doppler history |
| Reference signal available | ⚠️ | Direct path capture via SDR (blind reference) |
| SNR budget | ✅ | Low altitude (550 km) → favorable R² |
| Orbit knowledge (sub-wavelength) | ✅ | Starlink terminal GPS + precise TLE |
| Phase/time synchronization | ✅ | GPS disciplined oscillator (GPSDO) |

### Key parameters at 12 GHz (λ = 2.5 cm):
- Range resolution (250 MHz BW): δr ≈ c / 2B ≈ **0.6 m**
- Azimuth resolution (8 min pass, R=550 km): δa ≈ λR / 2VT ≈ **~1–5 m** (geometry dependent)
- Free-space path loss at 550 km: ~167 dB

---

## 3. System Architecture

### 3.1 Receive Chain

```
[Ku-band antenna] → [LNA] → [Downconverter] → [ADC] → [IQ samples]
```

Two parallel channels:
- **Reference channel**: Starlink user terminal (or dedicated Ku SDR) pointed at target satellite. Captures direct path signal for cross-correlation.
- **Surveillance channel**: Phased array of Ku-band elements, electronically steered toward scene of interest.

### 3.2 Synchronization

All timing disciplined by **GPS-disciplined oscillator (GPSDO)**:
- Time sync to ~1 ns (vs. required ~1/B ≈ 4 ns for 250 MHz)
- Phase coherence maintained over full integration time
- Satellite ephemeris updated via real-time TLE or Starlink terminal state

### 3.3 Signal Processing Pipeline

```
raw IQ (reference) ──────────────────────────────────────┐
                                                          ▼
raw IQ (surveillance) → [Range compression] → [Cross-correlation] → [Range-Doppler map]
                                                          ↓
                                               [CFAR detection]
                                                          ↓
                                               [SAR back-projection]
                                                          ↓
                                               [SAR image]
```

**Step 1 — Direct Path Cancellation**: Remove the strong direct path signal from surveillance channel.

**Step 2 — Range Compression**: Cross-correlate surveillance channel with reference (direct path). Yields range/delay profile per pulse.

**Step 3 — Doppler Processing**: Apply CFAR across slow-time dimension. Produces Range-Doppler map.

**Step 4 — SAR Formation**: Back-projection algorithm using precise bistatic geometry to focus image.

### 3.4 Bistatic Geometry

```
              Satellite (Tx)
              position: (xs, ys, zs)
              velocity: (vx, vy, vz)
             /              \
            / RT              \ RR
           /                    \
    Reference Rx            Surveillance Rx
    position: (xr, yr, zr)  position: (xa, ya, za)
                    \            /
                     \          /
                      [Target]
                      position: (xt, yt, zt)
```

Bistatic range: `R_bi = RT + RR`

Bistatic Doppler:
```
f_d = (1/λ) * d/dt(RT + RR)
    = (1/λ) * [v_sat · r̂_T + v_target · (r̂_T - r̂_R)]
```

Bistatic angle β: angle at target between transmitter and receiver directions.

---

## 4. Hardware Architecture (Target)

| Component | Specification | Notes |
|-----------|--------------|-------|
| Reference antenna | Starlink Gen2 user terminal OR Ku-band dish + SDR | Tracks target satellite |
| Surveillance array | N × Ku-band patch elements, 12 GHz | Electronically steered |
| SDR | USRP X310 or similar, 200 MHz BW | Per channel |
| Processing | NVIDIA AGX Orin | Real-time SAR processing |
| Sync | Leo Bodnar GPSDO or similar | 10 MHz + 1PPS |
| LNA | Low-noise, Ku-band, NF < 1.5 dB | Critical for SNR |

---

## 5. SNR Budget (Link Analysis)

Bistatic radar equation:
```
SNR = (Pt * Gt * Gr * λ² * σ) / ((4π)³ * RT² * RR² * k * T * B * L)
```

Estimated parameters for Starlink downlink:
| Parameter | Value | Notes |
|-----------|-------|-------|
| Pt·Gt (EIRP) | ~37 dBW | Per spot beam estimate |
| RT | 550 km | Satellite to target |
| RR | ~1–10 km | Target to receive array |
| λ | 0.025 m | 12 GHz |
| σ (aircraft) | ~10 m² | 10 dBsm |
| B | 250 MHz | Bandwidth |
| Gr | TBD | Receive array gain |
| T | 290 K | System temperature |

Pre-integration SNR is expected to be negative — coherent integration gain over T_int compensates:
- Integration gain: `G_int = B * T_int`
- For T_int = 1s, B = 250 MHz: G_int = 54 dB

---

## 6. Simulation Plan

### Phase 1 — Geometry & Feasibility (current)
- [ ] Starlink orbital mechanics model (TLE-based)
- [ ] Bistatic geometry calculator
- [ ] SNR budget estimator
- [ ] Synthetic aperture length calculator

### Phase 2 — Signal Model
- [ ] Synthetic wideband waveform (OFDM-like, unknown reference scenario)
- [ ] Direct path capture simulation
- [ ] Multipath and clutter model

### Phase 3 — Processing Chain
- [ ] Range compression via cross-correlation
- [ ] Range-Doppler map generation
- [ ] CFAR detector
- [ ] Back-projection SAR formation algorithm

### Phase 4 — Performance Analysis
- [ ] Resolution cell estimation
- [ ] Ambiguity function analysis
- [ ] Sensitivity vs. integration time
- [ ] Multi-satellite (multistatic) configuration analysis

---

## 7. Technology Stack

| Layer | Technology |
|-------|-----------|
| Simulation | Python 3.11+ |
| Numerical | NumPy, SciPy |
| Orbital mechanics | `skyfield` + TLE data |
| Signal processing | SciPy signal, custom DSP |
| Visualization | Matplotlib, Plotly |
| Notebooks | Jupyter Lab |
| Hardware (future) | C++ / CUDA on AGX Orin |

---

## 8. Key References

1. Griffiths & Baker (2005) — "An Introduction to Passive Coherent Location"
2. Colone et al. (2012) — "Passive Bistatic Radar"
3. Vu et al. (2022) — "Passive Radar using Starlink LEO Signals" *(verify availability)*
4. Meta et al. (2007) — "OFDM Waveforms for Passive Radar"
5. Skolnik — "Radar Handbook", bistatic chapter
6. Krieger & Moreira (2006) — "Spaceborne Bistatic SAR"

---

## 9. Open Questions

1. **Waveform knowledge**: Can we extract partial reference waveform structure from Starlink signal analysis?
2. **Beam scheduling**: Can we predict which Starlink beams illuminate a given area at a given time?
3. **Bistatic angle limits**: At what bistatic angle does the SAR geometry degenerate?
4. **Multi-satellite fusion**: How to coherently combine data from multiple simultaneous Starlink passes?
5. **Clutter**: What is the expected land/sea clutter RCS vs. target RCS at bistatic geometry?
