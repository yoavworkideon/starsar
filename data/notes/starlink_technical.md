# Starlink Technical Parameters — STARDAR Reference

## Orbital Shells (as of 2024)

| Shell | Altitude (km) | Inclination | Satellites | Status |
|-------|--------------|-------------|-----------|--------|
| 1 | 550 | 53° | ~1,500 | Operational |
| 2 | 540 | 53.2° | ~1,000 | Operational |
| 3 | 570 | 70° | ~500 | Operational |
| 4 | 560 | 97.6° | ~500 | Operational (polar) |
| V2 Mini | 530 | 43° | ~2,000 | Deploying |

Total operational (2024): ~5,500 satellites

## Radio Frequency Characteristics

### Downlink to User Terminals (Ku-band)
- Frequency: 10.7 – 12.7 GHz
- Modulation: OFDM-based (proprietary, encrypted)
- Bandwidth per channel: up to ~250 MHz
- EIRP estimate: 34–40 dBW per spot beam
- Polarization: circular (RHCP/LHCP)
- Beam type: electronically steered spot beams

### Gateway Uplink (Ka-band)
- Frequency: 27.5 – 30 GHz (uplink to satellite)
- Not useful for STARDAR (uplink, not downlink)

### Inter-Satellite Links (Laser)
- V2 satellites: optical ISL
- Not relevant for RF passive radar

## Antenna System

### Satellite (Gen 1):
- Phased array, ~40 dBi gain toward user terminal beam
- ~16 beams per satellite simultaneously
- Beam hopping: each beam active for ~1–2 ms slots

### User Terminal (Flat Panel — "Dishy"):
- Size: ~50 cm × 30 cm (Gen 2 rectangular)
- Frequency: 10.7–12.75 GHz (Rx), 14–14.5 GHz (Tx uplink)
- Gain: ~32–34 dBi receive
- Element count: ~1,280 elements (Gen 2)
- Field of view: ±70° from boresight
- Tracking: electronic beam steering, continuous satellite tracking
- Update rate: beam steering updated at ~100 Hz

## Relevance to STARDAR

### Using Terminal as Reference Receiver:
The Starlink user terminal's phased array is ideally suited as our
reference channel hardware:
- Already tuned to 10.7–12.7 GHz
- High gain (32–34 dBi) toward satellite → high SNR reference
- Electronic tracking → maintains alignment through full pass
- GPS integrated → provides timing reference
- Commercial availability (used units ~$200–300)

Problem: Output is IP packets. Raw IQ not accessible without hardware modification.

### SDR Alongside Terminal Approach (Recommended):
Mount a separate Ku-band LNA + downconverter + SDR adjacent to the terminal.
Use the terminal's pointing angle to aim a secondary horn/patch antenna.
Tap the terminal's 1-PPS GPS output for timing synchronization.

### Beam Scheduling (Key Unknown):
Starlink uses dynamic beam hopping — a specific spot beam may only
illuminate a given area for ~1–2 ms out of every ~16 ms frame.
This creates a duty cycle of ~6–12% at any given point.

Implications:
- Effective integration is not continuous
- Need to detect active beam windows in received signal
- Alternatively: process only during active windows (gating)

### Signal Structure (What We Know):
From FCC filings and reverse engineering efforts (public research):
- Frame-based OFDM structure
- Guard intervals consistent with CP-OFDM
- Some pilot structure (inferred from spectrum analysis)
- User data encrypted (AES-based, likely)

What this means for passive radar:
- The OFDM pilot subcarriers are deterministic → could serve as partial reference
- The data subcarriers are random (encrypted) → behave like random BPSK/QAM
- Random BPSK over OFDM = excellent ambiguity function (thumbtack-like)
- In practice: blind cross-correlation exploits the entire signal bandwidth

## Visibility Analysis

For a receiver at latitude 32°N (Israel/Middle East):
- Starlink visible above 10°: ~15–20 satellites simultaneously
- Average pass duration above 10°: ~6–8 minutes
- Passes per day: ~40–60 (depends on constellation density)
- Average revisit: ~15–20 minutes

Polar shell (97.6°) provides additional coverage at high elevations.

## TLE Data Sources

For precise orbital predictions:
- CelesTrak: celestrak.org/SOCRATES/query.php
- Space-Track: space-track.org (requires registration)
- Starlink TLE group: celestrak.org/SATCAT/records.php?SATNAME=STARLINK

TLE accuracy: ~100–500 m (updated every few hours).
For SAR phase coherence: insufficient → need Starlink terminal ephemeris
or real-time precise orbit determination (POD).

## Power Budget Estimation

From FCC filings (IBFS) and ITU filings:
- Satellite transmit power: ~20–40 W per beam (estimated)
- Terminal gain: ~32–34 dBi
- EIRP toward user: ~43–49 dBW (toward terminal, not toward radar scene)
- EIRP toward scene (side-lobe): significantly lower

Note: STARDAR exploits the MAIN BEAM illumination of the ground scene,
not the terminal uplink. The satellite's beam illuminates a ~50–100 km
diameter spot on the ground. Our target and receiver must be within
(or near the edge of) this spot.
