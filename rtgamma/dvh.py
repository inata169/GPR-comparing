from typing import Dict, Tuple

import numpy as np


def calculate_dvh(dose: np.ndarray, mask: np.ndarray, n_bins: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate the cumulative Dose-Volume Histogram (DVH).
    
    Parameters
    ----------
    dose : np.ndarray
        3D dose grid.
    mask : np.ndarray
        3D boolean mask of the ROI.
    n_bins : int
        Number of bins for the histogram.
        
    Returns
    -------
    bin_centers : np.ndarray
        Dose values (x-axis).
    cumulative_volume : np.ndarray
        Cumulative volume percentage (y-axis, 0-100).
    """
    roi_dose = dose[mask]
    if roi_dose.size == 0:
        return np.zeros(0), np.zeros(0)
    
    d_min, d_max = np.nanmin(roi_dose), np.nanmax(roi_dose)
    if d_min == d_max:
        # Avoid division by zero in histogram
        return np.array([d_min]), np.array([100.0])
        
    counts, bin_edges = np.histogram(roi_dose, bins=n_bins, range=(0, d_max * 1.05))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    
    # Calculate cumulative volume (from high dose to low dose)
    # Sum counts from right to left
    cumulative_counts = np.cumsum(counts[::-1])[::-1]
    
    # Normalize to percentage
    total_voxels = roi_dose.size
    cumulative_volume = (cumulative_counts / total_voxels) * 100.0
    
    return bin_centers, cumulative_volume

def get_dvh_metric(bin_centers: np.ndarray, cumulative_volume: np.ndarray, volume_pct: float) -> float:
    """Get dose at a specific volume percentage (e.g., D95)."""
    if bin_centers.size == 0:
        return float('nan')
    # Find the dose where cumulative_volume >= volume_pct
    # Since cumulative_volume is non-increasing, we can use interp
    # We need to flip because interp expects increasing x
    return float(np.interp(volume_pct, cumulative_volume[::-1], bin_centers[::-1]))

def calculate_dvh_stats(dose: np.ndarray, mask: np.ndarray) -> Dict:
    """Calculate common DVH statistics for an ROI."""
    roi_dose = dose[mask]
    if roi_dose.size == 0:
        return {
            'mean': float('nan'),
            'max': float('nan'),
            'min': float('nan'),
            'd98': float('nan'),
            'd95': float('nan'),
            'd50': float('nan'),
            'd2': float('nan'),
        }
    
    bin_centers, cumulative_vol = calculate_dvh(dose, mask)
    
    return {
        'mean': float(np.nanmean(roi_dose)),
        'max': float(np.nanmax(roi_dose)),
        'min': float(np.nanmin(roi_dose)),
        'd98': get_dvh_metric(bin_centers, cumulative_vol, 98.0),
        'd95': get_dvh_metric(bin_centers, cumulative_vol, 95.0),
        'd50': get_dvh_metric(bin_centers, cumulative_vol, 50.0),
        'd2': get_dvh_metric(bin_centers, cumulative_vol, 2.0),
        'dvh_bins': bin_centers.tolist(),
        'dvh_vol': cumulative_vol.tolist()
    }
