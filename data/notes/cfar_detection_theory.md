# CFAR Detection Theory — STARDAR Reference

## Overview

Constant False Alarm Rate (CFAR) detection adaptively adjusts the detection
threshold based on the local noise/clutter environment, maintaining a
constant probability of false alarm (Pfa) regardless of noise level changes.

In STARDAR, CFAR is applied to the Range-Doppler map after cross-correlation.

## Core Principle

For a cell under test (CUT) with power z, detection occurs when:
```
z > T = α × μ_noise
```
where:
- T = detection threshold
- α = scaling factor (function of Pfa and N reference cells)
- μ_noise = estimated noise power from reference cells

## CA-CFAR (Cell-Averaging CFAR) — Primary Algorithm

### Algorithm
1. For each cell under test (CUT) at position (r, d) in Range-Doppler map:
2. Define reference window: N_r range cells × N_d Doppler cells around CUT
3. Exclude guard cells (G_r × G_d) immediately adjacent to CUT
4. Estimate noise: μ = (1/N) × Σ reference_cells
5. Set threshold: T = α × μ
6. Declare detection if z_CUT > T

### Threshold Scaling Factor α

For N independent reference cells and target Pfa:
```
α = N × (Pfa^(-1/N) - 1)
```

### False Alarm Probability
For Rayleigh-distributed noise (exponential power):
```
Pfa = (1 + α/N)^(-N)
```

### Detection Probability (Marcum Q-function)
For SNR = S:
```
Pd = Q_M(sqrt(2S), sqrt(2T))
```

### Typical Parameters for STARDAR
- N_range = 16 reference cells per side (32 total)
- N_doppler = 8 reference cells per side (16 total)
- G_range = 2 guard cells per side
- G_doppler = 2 guard cells per side
- Pfa = 1e-6
- → α ≈ 13.8 (for N=32, Pfa=1e-6)

## CFAR Variants

### GO-CFAR (Greatest Of)
Analyzes leading and lagging reference windows separately:
```
μ = max(μ_leading, μ_lagging)
T = α × μ
```
Use when: adjacent to strong clutter edges. Reduces false alarms at clutter boundaries.
Cost: ~3 dB SNR loss vs CA-CFAR in homogeneous noise.

### SO-CFAR (Smallest Of)
```
μ = min(μ_leading, μ_lagging)
T = α × μ
```
Use when: resolving two closely-spaced targets. Reduces target masking.
Cost: Higher Pfa at clutter transitions.

### OS-CFAR (Order Statistic)
Rank-orders all N reference cells, selects k-th largest value:
```
μ = x_(k)   (k-th order statistic)
T = α_OS × x_(k)
```
Robust to: multiple interfering targets in reference window.
Cost: Higher computational complexity. Typically k = 3N/4.

### CASH-CFAR (Cell Averaging Smallest of Highest)
Hybrid method: avoids target masking AND suppresses time sidelobes.
Preferred for pulse-compressed waveforms (relevant to STARDAR cross-correlation output).

## 2D CFAR for Range-Doppler Maps

For STARDAR Range-Doppler processing, 2D CA-CFAR is applied:

```python
# Pseudocode
for r in range_bins:
    for d in doppler_bins:
        # Reference cells (excluding guard zone)
        ref_cells = RD_map[r-Nr-Gr:r+Nr+Gr+1, d-Nd-Gd:d+Nd+Gd+1]
        ref_cells = exclude_guard_zone(ref_cells, Gr, Gd)
        mu = mean(|ref_cells|^2)
        threshold = alpha * mu
        if |RD_map[r, d]|^2 > threshold:
            detections.append((r, d))
```

## Performance in Clutter

For Weibull clutter (land clutter at Ku-band):
- CA-CFAR performance degrades (clutter not Rayleigh)
- OS-CFAR preferred for heterogeneous terrain
- Adaptive OS-CFAR or CASH recommended for STARDAR terrain mapping

For sea clutter (K-distribution):
- Standard CFAR underestimates threshold → high false alarm rate
- K-distributed CFAR or GOCA-CFAR preferred

## SNR Loss Due to CFAR

CA-CFAR incurs an SNR loss vs ideal detector:
```
L_CFAR ≈ 10 * log10(1 + N_ref/N_guard)   [dB, approximate]
```
For N_ref=32, N_guard=8: L_CFAR ≈ 0.5 dB (negligible)

## Integration with STARDAR Pipeline

```
Cross-correlation output → |·|² → 2D CA-CFAR → detection list (r_bi, f_d)
                                                        ↓
                                              back-projection filter
                                              (only process detected cells)
```

This reduces SAR processing cost by only back-projecting detected targets
rather than the full Range-Doppler map.

## Sources
- RadarTutorial.eu — CFAR fundamentals
- Skolnik, M. — Introduction to Radar Systems, Chapter 5
- Richards, M.A. — Fundamentals of Radar Signal Processing, Chapter 6
- IEEE AESS — Radar Handbook, CFAR chapter
