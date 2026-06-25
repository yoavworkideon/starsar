"""Regression tests for bistatic Doppler sign/magnitude.

Pins the fix for the tx-velocity sign error in bistatic_doppler(): a transmitter
closing on the target must produce a POSITIVE Doppler shift. The pre-fix code
returned the opposite sign for the tx term, which these tests catch.
"""

import numpy as np

from simulation.geometry.bistatic import BistaticGeometry, bistatic_doppler

WAVELENGTH = 0.025  # Ku-band, ~12 GHz


def _geom(tx_vel):
    # Target at origin; Tx 1000 m out along +x; Rx stationary off +y.
    return BistaticGeometry(
        tx_pos=np.array([1000.0, 0.0, 0.0]),
        tx_vel=np.array(tx_vel, dtype=float),
        rx_pos=np.array([0.0, 1000.0, 0.0]),
        target_pos=np.array([0.0, 0.0, 0.0]),
    )


def test_closing_transmitter_gives_positive_doppler():
    # Tx moving toward the target (-x) shortens R_T -> positive Doppler.
    assert bistatic_doppler(_geom([-100.0, 0.0, 0.0]), WAVELENGTH) > 0


def test_receding_transmitter_gives_negative_doppler():
    assert bistatic_doppler(_geom([100.0, 0.0, 0.0]), WAVELENGTH) < 0


def test_transverse_transmitter_motion_is_zero_doppler():
    # Velocity perpendicular to the Tx->target line -> no range rate.
    assert abs(bistatic_doppler(_geom([0.0, 50.0, 0.0]), WAVELENGTH)) < 1e-6


def test_magnitude_matches_radial_rate():
    # Closing at 100 m/s -> |f_d| = 100 / lambda.
    fd = bistatic_doppler(_geom([-100.0, 0.0, 0.0]), WAVELENGTH)
    assert abs(fd - 100.0 / WAVELENGTH) < 1.0
