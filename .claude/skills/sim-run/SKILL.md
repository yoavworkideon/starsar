---
name: sim-run
description: Run a STARDAR simulation computation (bistatic geometry, orbital pass, resolution) and plot the result. Use when the user types /sim-run or asks to compute/plot a geometry, Doppler, resolution, or Starlink pass.
---

# /sim-run — run a simulation computation with a plot

The simulation modules are libraries, not scripts. This skill writes a short driver that calls
them, computes the requested quantity, and plots it.

## Available building blocks
- `simulation/geometry/bistatic.py` — `BistaticGeometry`, `bistatic_range`, `bistatic_angle`,
  `bistatic_doppler`, `range_resolution(bandwidth_hz)`, `azimuth_resolution(...)`,
  `synthetic_aperture_length(velocity, integration_time)`
- `simulation/orbital/starlink.py` — `load_satellite`, `satellite_state_ecef(sat, t_unix)`,
  `pass_duration_seconds(elevation_deg)`, `ground_station_ecef(lat, lon, alt)`
- `simulation/visualization/plots.py` — plotting helpers (matplotlib)

## How to run
1. Clarify what the user wants to compute/sweep (e.g. "range resolution vs bandwidth",
   "Doppler over a pass", "aperture length vs integration time").
2. Write a small driver under `scripts/` (e.g. `scripts/sim_<topic>.py`) that imports the
   functions above, computes, and saves a plot to `data/plots/<name>.png`.
3. Run it: `.venv/bin/python3 scripts/sim_<topic>.py`
4. Show the user the saved figure path and summarize the numbers.

Keep drivers reusable (argparse for the swept parameter) and physically labeled (units on axes).
Sanity-check results against the known numbers in CLAUDE.md (e.g. range resolution ≈ 0.6 m at 250 MHz).
