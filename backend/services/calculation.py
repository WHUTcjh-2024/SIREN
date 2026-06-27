import base64
import math
from io import BytesIO

import numpy as np

from backend.schemas.experiment import CalculationRequest, FitRequest


LAMBDA_0 = 632.8e-9


def calculate_surface_tension(data: CalculationRequest) -> dict:
    """Calculate surface tension while keeping the legacy response contract."""
    height = data.H0 - data.h
    alpha = math.atan(height / data.L)
    beta = math.atan((data.delta_X_cm + height) / data.L)
    delta = beta - alpha
    wave_number = (2 * math.pi / LAMBDA_0) * math.sin(delta / 2) * (
        math.sin(alpha + delta / 2) + math.sin(alpha - delta / 2)
    )
    if abs(wave_number) < 1e-12:
        raise ValueError("波数接近零，请检查输入参数")
    omega = 2 * math.pi * data.f
    sigma = data.rho * omega**2 / abs(wave_number) ** 3
    return {
        "delta": round(delta, 8),
        "k": round(wave_number, 4),
        "sigma": round(sigma, 6),
        "relative_error": round(abs(sigma - data.sigma0) / data.sigma0 * 100, 4)
        if data.sigma0
        else None,
    }


def fit_surface_tension(data: FitRequest) -> dict:
    k_arr = np.asarray([point.k for point in data.experiment_data], dtype=np.float64)
    f_arr = np.asarray([point.f for point in data.experiment_data], dtype=np.float64)
    omega_arr = 2 * np.pi * f_arr
    slope, intercept = np.polyfit(np.log(k_arr), np.log(omega_arr), 1)
    coefficient = float(np.exp(intercept))
    predicted = slope * np.log(k_arr) + intercept
    residual = float(np.sum((np.log(omega_arr) - predicted) ** 2))
    total = float(np.sum((np.log(omega_arr) - np.mean(np.log(omega_arr))) ** 2))
    r_squared = round(1 - residual / total, 6) if total > 0 else 0.0
    sigma_fit = data.rho * coefficient**2

    image = _render_fit_plot(k_arr, omega_arr, coefficient, slope, r_squared)
    return {
        "a": round(coefficient, 6),
        "slope": round(float(slope), 6),
        "sigma_fit": round(sigma_fit, 6),
        "relative_error_fit": round(abs(sigma_fit - data.sigma0) / data.sigma0 * 100, 4)
        if data.sigma0
        else None,
        "r_squared": r_squared,
        "img_base64": base64.b64encode(image).decode("ascii"),
    }


def _render_fit_plot(k_arr, omega_arr, coefficient: float, slope: float, r_squared: float) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.scatter(k_arr, omega_arr, color="#6366F1", s=90, label="实验数据")
    k_fit = np.linspace(k_arr.min() * 0.8, k_arr.max() * 1.2, 300)
    ax.plot(k_fit, coefficient * k_fit**slope, color="#EC4899", linewidth=2.8,
            label=rf"拟合: $\omega={coefficient:.4g}k^{{{slope:.3f}}}$")
    ax.set_xlabel(r"波数 $k$ ($\mathrm{m}^{-1}$)")
    ax.set_ylabel(r"角频率 $\omega$ (rad/s)")
    ax.set_title(rf"数据拟合 ($R^2={r_squared}$)")
    ax.grid(alpha=0.35, linestyle="--")
    ax.legend()
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()
