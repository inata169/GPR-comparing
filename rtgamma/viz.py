import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Optional


def save_gamma_map_2d(path: str, gamma2d: np.ndarray, title: str = "") -> None:
    plt.figure(figsize=(6, 5))
    im = plt.imshow(gamma2d, cmap='turbo', origin='lower')
    plt.colorbar(im, label='Gamma')
    if title:
        plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def save_dose_diff_2d(path: str, ref2d: np.ndarray, eval2d: np.ndarray, title: str = "") -> None:
    diff = eval2d - ref2d
    vmax = np.nanpercentile(np.abs(diff), 99.0)
    plt.figure(figsize=(6, 5))
    im = plt.imshow(diff, cmap='bwr', origin='lower', vmin=-vmax, vmax=vmax)
    plt.colorbar(im, label='Dose diff (pct)')
    if title:
        plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()

