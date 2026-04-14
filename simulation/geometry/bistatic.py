"""
Bistatic geometry calculations for STARDAR.

Coordinate system: ECEF (Earth-Centered, Earth-Fixed), meters.
All angles in radians unless stated otherwise.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class BistaticGeometry:
    """Represents a snapshot of the bistatic radar geometry."""
    tx_pos: np.ndarray       # Transmitter (satellite) position [x, y, z] m
    tx_vel: np.ndarray       # Transmitter velocity [vx, vy, vz] m/s
    rx_pos: np.ndarray       # Receiver position [x, y, z] m
    target_pos: np.ndarray   # Target position [x, y, z] m


def bistatic_range(geom: BistaticGeometry) -> tuple[float, float, float]:
    """
    Compute bistatic range components.

    Returns:
        RT: transmitter-to-target range (m)
        RR: target-to-receiver range (m)
        R_bi: bistatic range sum RT + RR (m)
    """
    RT = np.linalg.norm(geom.target_pos - geom.tx_pos)
    RR = np.linalg.norm(geom.rx_pos - geom.target_pos)
    return RT, RR, RT + RR


def bistatic_angle(geom: BistaticGeometry) -> float:
    """
    Compute bistatic angle β at the target (angle between Tx and Rx directions).

    Returns:
        beta: bistatic angle in radians
    """
    r_t = geom.tx_pos - geom.target_pos
    r_r = geom.rx_pos - geom.target_pos
    cos_beta = np.dot(r_t, r_r) / (np.linalg.norm(r_t) * np.linalg.norm(r_r))
    return np.arccos(np.clip(cos_beta, -1.0, 1.0))


def bistatic_doppler(geom: BistaticGeometry, wavelength: float,
                     target_vel: np.ndarray = None) -> float:
    """
    Compute bistatic Doppler frequency shift.

    f_d = (1/λ) * d/dt(RT + RR)
        = (1/λ) * [v_tx · r̂_T + v_target · (r̂_T - r̂_R)]

    Args:
        geom: bistatic geometry snapshot
        wavelength: signal wavelength (m)
        target_vel: target velocity vector (m/s), defaults to zero

    Returns:
        f_d: Doppler frequency (Hz)
    """
    if target_vel is None:
        target_vel = np.zeros(3)

    r_t = geom.target_pos - geom.tx_pos
    r_r = geom.rx_pos - geom.target_pos

    r_hat_t = r_t / np.linalg.norm(r_t)   # unit vector Tx -> target
    r_hat_r = r_r / np.linalg.norm(r_r)   # unit vector target -> Rx

    # Rate of change of RT (satellite moving, target potentially moving)
    dRT_dt = np.dot(geom.tx_vel, r_hat_t) + np.dot(target_vel, r_hat_t)

    # Rate of change of RR (target moving toward/away from Rx)
    dRR_dt = -np.dot(target_vel, r_hat_r)

    f_d = -(dRT_dt + dRR_dt) / wavelength
    return f_d


def range_resolution(bandwidth_hz: float) -> float:
    """Range resolution from signal bandwidth. δr = c / 2B"""
    c = 3e8
    return c / (2 * bandwidth_hz)


def azimuth_resolution(wavelength: float, slant_range: float,
                       velocity: float, integration_time: float) -> float:
    """
    Bistatic azimuth resolution estimate.
    δa ≈ λ * R / (2 * V * T_int)
    """
    return (wavelength * slant_range) / (2 * velocity * integration_time)


def synthetic_aperture_length(velocity: float, integration_time: float) -> float:
    """L = V * T_int"""
    return velocity * integration_time
