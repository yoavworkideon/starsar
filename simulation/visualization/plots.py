"""
Visualization utilities for STARDAR simulations.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


def plot_bistatic_geometry_2d(tx_positions: np.ndarray, rx_pos: np.ndarray,
                               target_pos: np.ndarray, title: str = "Bistatic Geometry"):
    """
    2D top-down view of bistatic geometry (ground projection).

    Args:
        tx_positions: (N, 3) satellite positions over time in ECEF or local ENU
        rx_pos: receiver position (3,)
        target_pos: target position (3,)
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    ax.plot(tx_positions[:, 0] / 1e3, tx_positions[:, 1] / 1e3,
            'b-', linewidth=2, label='Satellite track (ground projection)')
    ax.plot(tx_positions[0, 0] / 1e3, tx_positions[0, 1] / 1e3,
            'b>', markersize=10, label='Sat start')
    ax.plot(tx_positions[-1, 0] / 1e3, tx_positions[-1, 1] / 1e3,
            'b|', markersize=10, label='Sat end')

    ax.plot(rx_pos[0] / 1e3, rx_pos[1] / 1e3,
            'g^', markersize=12, label='Receive array', zorder=5)
    ax.plot(target_pos[0] / 1e3, target_pos[1] / 1e3,
            'rx', markersize=12, markeredgewidth=3, label='Target', zorder=5)

    ax.set_xlabel('East (km)')
    ax.set_ylabel('North (km)')
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    plt.tight_layout()
    return fig, ax


def plot_range_doppler(range_doppler: np.ndarray, range_bins: np.ndarray,
                       doppler_bins: np.ndarray, title: str = "Range-Doppler Map",
                       dynamic_range_db: float = 40.0):
    """
    Plot a range-Doppler map in dB scale.

    Args:
        range_doppler: 2D array (range_bins x doppler_bins), power
        range_bins: range axis values (m)
        doppler_bins: Doppler frequency axis values (Hz)
        dynamic_range_db: display dynamic range in dB
    """
    rd_db = 10 * np.log10(np.abs(range_doppler) + 1e-30)
    rd_db -= rd_db.max()
    rd_db = np.clip(rd_db, -dynamic_range_db, 0)

    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(rd_db.T, aspect='auto', origin='lower', cmap='inferno',
                   extent=[range_bins[0] / 1e3, range_bins[-1] / 1e3,
                           doppler_bins[0], doppler_bins[-1]],
                   vmin=-dynamic_range_db, vmax=0)

    plt.colorbar(im, ax=ax, label='Relative power (dB)')
    ax.set_xlabel('Bistatic range (km)')
    ax.set_ylabel('Doppler frequency (Hz)')
    ax.set_title(title)
    plt.tight_layout()
    return fig, ax


def plot_snr_budget(params: dict, title: str = "SNR Budget"):
    """Bar chart of SNR budget components."""
    fig, ax = plt.subplots(figsize=(10, 5))

    keys = list(params.keys())
    vals = list(params.values())
    colors = ['green' if v >= 0 else 'red' for v in vals]

    bars = ax.bar(keys, vals, color=colors, alpha=0.7, edgecolor='black')
    ax.axhline(0, color='black', linewidth=0.8)

    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, val + (0.5 if val >= 0 else -1.5),
                f'{val:.1f} dB', ha='center', va='bottom', fontsize=9)

    ax.set_ylabel('dB')
    ax.set_title(title)
    ax.grid(True, axis='y', alpha=0.3)
    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()
    return fig, ax
