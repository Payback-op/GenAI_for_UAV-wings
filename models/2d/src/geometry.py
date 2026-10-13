"""Source-native cubic CST: first four lower, last four upper coefficients.

Source: data/reference/CST_airfoil_fit.m, N1=0.5, N2=1, dz=0.
Generated shapes use a normalized closed leading/trailing edge at y=0.
"""
import numpy as np

def chord_grid(count=301):
    return (1 - np.cos(np.linspace(0, np.pi, count))) / 2

def surfaces(coefficients, x=None):
    x = chord_grid() if x is None else np.asarray(x, dtype=float)
    w = np.asarray(coefficients, dtype=float)
    if w.shape[-1] != 8 or not np.isfinite(w).all():
        raise ValueError("Expected eight finite source-native CST coefficients.")
    basis = np.array([(1-x)**3, 3*x*(1-x)**2, 3*x**2*(1-x), x**3])
    basis *= np.sqrt(x) * (1-x)
    lower = w[..., :4] @ basis
    upper = w[..., 4:] @ basis
    return x, lower, upper

def geometry_checks(coefficients, minimum, maximum):
    x, lower, upper = surfaces(coefficients)
    thickness = upper - lower
    max_thickness = thickness.max(axis=-1)
    camber = np.abs((upper+lower)/2).max(axis=-1)
    # Cubic CST guarantees analytic smoothness on the interior and closed edges.
    valid = np.isfinite(thickness).all(axis=-1) & (thickness[..., 1:-1].min(axis=-1) > 0)
    valid &= (max_thickness >= minimum) & (max_thickness <= maximum) & (camber <= 0.12)
    return valid, max_thickness, camber
