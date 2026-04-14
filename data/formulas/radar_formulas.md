# STARDAR — Core Radar Formulas Reference

## 1. Bistatic Radar Equation

```
SNR = (Pt * Gt * Gr * λ² * σ) / ((4π)³ * RT² * RR² * k * T * B * L)
```

In dB:
```
SNR_dB = EIRP_dBW + Gr_dBi + 20*log10(λ) - 30*log10(4π)
         - 20*log10(RT) - 20*log10(RR) + σ_dBsm
         - 10*log10(k*T*B) + G_int_dB - L_dB
```

Where:
- Pt = transmit power (W)
- Gt = transmit antenna gain (linear)
- Gr = receive antenna gain (linear)
- λ  = wavelength (m) = c/f
- σ  = target radar cross section (m²)
- RT = transmitter-to-target range (m)
- RR = target-to-receiver range (m)
- k  = Boltzmann constant = 1.38e-23 J/K
- T  = system noise temperature (K)
- B  = receiver bandwidth (Hz)
- L  = system losses (linear)

## 2. Integration Gain

Coherent integration (matched filter + slow-time FFT):
```
G_int = B * T_int
```

In dB: `G_int_dB = 10 * log10(B * T_int)`

Example: B=250 MHz, T_int=10s → G_int = 54 dB

Non-coherent integration (N pulses):
```
G_nc ≈ sqrt(N)    (approximate, SNR-dependent)
```

## 3. Range Resolution

Monostatic: `δr = c / (2B)`

Bistatic: `δr_bi = c / (2B * cos(β/2))`

Where β is the bistatic angle at the target.

Example: B=250 MHz, β=0 → δr = 0.6 m

## 4. Azimuth (Cross-range) Resolution — SAR

```
δa = λ * R / (2 * V * T_int)     [unfocused SAR]
δa = D / 2                        [focused SAR, D = physical aperture]
```

For Starlink: λ=0.025m, R=560km, V=7600 m/s, T_int=10s:
```
δa = (0.025 * 560e3) / (2 * 7600 * 10) = 9.2 m
```

## 5. Bistatic Range

```
R_bi = RT + RR
```

Bistatic range rate:
```
dR_bi/dt = v_T · r̂_T + v_target · (r̂_T - r̂_R)
```

## 6. Bistatic Doppler

```
f_d = -(1/λ) * d(RT + RR)/dt
    = -(1/λ) * [v_sat · r̂_T + v_target · (r̂_T - r̂_R)]
```

For stationary target, stationary receiver, moving satellite at angle θ:
```
f_d = -(v_sat / λ) * cos(θ)
```

Max Doppler (satellite overhead): f_d_max = v_sat / λ = 7600 / 0.025 = 304 kHz

## 7. Bistatic Angle

```
β = arccos( r̂_T · r̂_R )
```

Where r̂_T = unit vector from target to Tx, r̂_R = unit vector from target to Rx.

Forward scatter: β → 180° (enhanced RCS)
Backscatter: β → 0° (same as monostatic)

## 8. Free-Space Path Loss

```
FSPL = (4π R / λ)²    [linear]
FSPL_dB = 20*log10(4π R / λ)
```

At 12 GHz (λ=0.025m):
- R = 550 km: FSPL = 167.8 dB
- R = 20 km:  FSPL = 140.0 dB

## 9. SAR Synthetic Aperture Length

```
L_sa = V * T_int
```

For Starlink pass: V=7600 m/s, T_int=480s (full pass above 10°):
```
L_sa = 7600 * 480 = 3,648 km
```

## 10. Noise Floor

```
N_floor = k * T_sys * B     [W]
N_floor_dBW = 10*log10(k) + 10*log10(T_sys) + 10*log10(B)
```

Example: T_sys=300K, B=250MHz:
```
N_floor = 1.38e-23 * 300 * 250e6 = 1.035e-12 W = -119.9 dBW
```

## 11. CFAR Threshold

Cell-Averaging CFAR (CA-CFAR):
```
T = α * μ_noise
α = N * (P_fa^(-1/N) - 1)    [for N reference cells]
```

## 12. Back-Projection SAR (Basic)

For each pixel at position p = (x, y):
```
I(p) = Σ_t s_rc(t, R_bi(p,t)) * exp(j * 2π/λ * R_bi(p,t))
```

Where s_rc is the range-compressed signal and the sum is over slow-time t.

## 13. Starlink Orbital Parameters (Shell 1)

```
Altitude:      h = 550 km
Orbital radius: r = Re + h = 6921 km
Orbital velocity: v = sqrt(μ/r) = sqrt(3.986e14 / 6.921e6) ≈ 7,580 m/s
Orbital period: T = 2π*r/v ≈ 5,737 s ≈ 95.6 min
Inclination:   53° (Shell 1), 70° (Shell 2), 97.6° (polar)
Pass duration above 10° elevation: ~480 s
```

## 14. EIRP Budget (Starlink Estimate)

Published/estimated parameters:
```
Satellite Tx power (estimated): 20-30 W per beam → 13-15 dBW
Satellite antenna gain (phased array): ~22-24 dBi
EIRP estimate: ~35-40 dBW per spot beam
```

Note: SpaceX does not publish exact EIRP. FCC filings suggest ~34 dBW.
