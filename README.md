# STARDAR

Passive bistatic SAR simulation using Starlink LEO satellites as illuminators of opportunity.

> **Status**: Phase 1 — Geometry & Feasibility Simulation

See [ARCHITECTURE.md](./ARCHITECTURE.md) for full system design.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Structure

```
stardar/
├── ARCHITECTURE.md          # Full system architecture
├── simulation/
│   ├── geometry/            # Bistatic geometry, isorange/isodoppler
│   ├── orbital/             # Starlink TLE-based orbit modeling
│   ├── signal/              # Waveform and signal models
│   ├── processing/          # Range-Doppler, SAR back-projection
│   └── visualization/       # Plotting utilities
├── notebooks/               # Jupyter exploration notebooks
├── data/tle/                # Starlink TLE files
└── tests/
```
