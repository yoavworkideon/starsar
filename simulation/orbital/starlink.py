"""
Starlink orbital mechanics using TLE data via skyfield.

Provides satellite position/velocity in ECEF at any given time.
"""

import numpy as np
from pathlib import Path
from skyfield.api import load, EarthSatellite, wgs84
from skyfield.framelib import itrs

# Default TLE for a Starlink Gen1 satellite (update regularly)
# Source: celestrak.org/SOCRATES or space-track.org
_DEFAULT_TLE = (
    "STARLINK-1007",
    "1 44713U 19074A   24001.50000000  .00002000  00000-0  14000-3 0  9991",
    "2 44713  53.0536 120.0000 0001480  80.0000 280.0000 15.05000000 00001",
)

STARLINK_ALTITUDE_KM = 550.0
STARLINK_VELOCITY_MS = 7600.0    # approximate orbital velocity m/s
STARLINK_FREQ_HZ = 12.0e9        # Ku-band center frequency
STARLINK_WAVELENGTH_M = 3e8 / STARLINK_FREQ_HZ
STARLINK_BANDWIDTH_HZ = 250e6    # max channel bandwidth


def load_satellite(tle_lines: tuple[str, str, str] = None) -> EarthSatellite:
    """
    Load a Starlink satellite from TLE lines.

    Args:
        tle_lines: (name, line1, line2) tuple. Uses built-in default if None.

    Returns:
        skyfield EarthSatellite object
    """
    ts = load.timescale()
    name, line1, line2 = tle_lines or _DEFAULT_TLE
    return EarthSatellite(line1, line2, name, ts)


def satellite_state_ecef(satellite: EarthSatellite, t_unix: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Get satellite position and velocity in ECEF at a given Unix timestamp.

    Args:
        satellite: skyfield EarthSatellite
        t_unix: Unix timestamp (seconds)

    Returns:
        pos_m: ECEF position [x, y, z] in meters
        vel_ms: ECEF velocity [vx, vy, vz] in m/s
    """
    ts = load.timescale()
    t = ts.ut1_jd(2440587.5 + t_unix / 86400.0)
    geo = satellite.at(t)

    # Position in ITRS (ECEF)
    itrs_pos = geo.frame_xyz(itrs).km
    pos_m = itrs_pos.T[0] * 1e3  # km -> m

    # Velocity in ITRS
    itrs_vel = geo.frame_xyz_and_velocity(itrs)[1].km_per_s
    vel_ms = itrs_vel.T[0] * 1e3  # km/s -> m/s

    return pos_m, vel_ms


def pass_duration_seconds(elevation_deg: float = 10.0) -> float:
    """
    Approximate visible pass duration above given elevation.
    Simplified formula for circular LEO orbit.

    Args:
        elevation_deg: minimum elevation angle in degrees

    Returns:
        approximate pass duration in seconds
    """
    Re = 6371e3   # Earth radius m
    alt = STARLINK_ALTITUDE_KM * 1e3
    v = STARLINK_VELOCITY_MS

    # Half-angle subtended at satellite above elevation
    el_rad = np.radians(elevation_deg)
    rho = np.arccos(Re * np.cos(el_rad) / (Re + alt)) - el_rad
    arc = 2 * rho * (Re + alt)
    return arc / v


def ground_station_ecef(lat_deg: float, lon_deg: float, alt_m: float = 0.0) -> np.ndarray:
    """
    Convert geodetic coordinates to ECEF position.

    Args:
        lat_deg: geodetic latitude in degrees
        lon_deg: longitude in degrees
        alt_m: altitude above WGS84 ellipsoid in meters

    Returns:
        pos_m: ECEF position [x, y, z] in meters
    """
    ts = load.timescale()
    location = wgs84.latlon(lat_deg, lon_deg, elevation_m=alt_m)
    t = ts.now()
    geo = location.at(t)
    pos_km = geo.frame_xyz(itrs).km
    return pos_km.T[0] * 1e3
