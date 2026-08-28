import base64
import math
from io import BytesIO

import numpy as np

from backend.schemas.experiment import CalculationRequest, FitRequest


LAMBDA_0 = 632.8e-9
GRAVITY = 9.80665


def _depth_factor(wave_number: float, fluid_depth_cm: float | None) -> float:
    if fluid_depth_cm is None:
        return 1.0
    return math.tanh(wave_number * fluid_depth_cm / 100)


def calculate_surface_tension(data: CalculationRequest) -> dict:
    """Calculate surface tension from the gravity-capillary dispersion relation."""
    height = data.H0 - data.h
    alpha = math.atan(height / data.L)
    beta = math.atan((data.delta_X_cm + height) / data.L)
    delta = beta - alpha
    wave_number = (2 * math.pi / LAMBDA_0) * math.sin(delta / 2) * (
        math.sin(alpha + delta / 2) + math.sin(alpha - delta / 2)
    )
    wave_number = abs(wave_number)
    if wave_number < 1e-12:
        raise ValueError("波数接近零，请检查输入参数")
    omega = 2 * math.pi * data.f
    depth_factor = _depth_factor(wave_number, data.fluid_depth_cm)
    corrected_omega_squared = omega**2 / depth_factor
    capillary_term = corrected_omega_squared - GRAVITY * wave_number
    if capillary_term <= 0:
        raise ValueError(
            "输入不满足重力-毛细波色散关系：当前频率不足以支持该波数，"
            "请核对条纹级次、间距、频率和几何量"
        )
    sigma = data.rho * capillary_term / wave_number**3
    return {
        "delta": round(delta, 8),
        "k": round(wave_number, 4),
        "sigma": round(sigma, 6),
        "gravity_fraction": round(GRAVITY * wave_number / corrected_omega_squared, 6),
        "depth_factor": round(depth_factor, 6),
        "model": "finite-depth-gravity-capillary" if data.fluid_depth_cm else "deep-water-gravity-capillary",
        "relative_error": round(abs(sigma - data.sigma0) / data.sigma0 * 100, 4)
        if data.sigma0
        else None,
    }


def fit_surface_tension(data: FitRequest) -> dict:
    k_arr = np.asarray([point.k for point in data.experiment_data], dtype=np.float64)
    f_arr = np.asarray([point.f for point in data.experiment_data], dtype=np.float64)
    omega_arr = 2 * np.pi * f_arr
    if data.fluid_depth_cm is None:
        depth_factors = np.ones_like(k_arr)
    else:
        depth_factors = np.tanh(k_arr * data.fluid_depth_cm / 100)
    capillary_target = omega_arr**2 / depth_factors - GRAVITY * k_arr
    if np.any(capillary_target <= 0):
        raise ValueError(
            "拟合数据中存在不满足重力-毛细波色散关系的点，请核对波数、频率和液深"
        )

    k_cubed = k_arr**3
    coefficient = float(np.dot(k_cubed, capillary_target) / np.dot(k_cubed, k_cubed))
    predicted = coefficient * k_cubed
    residual = float(np.sum((capillary_target - predicted) ** 2))
    total = float(np.sum((capillary_target - np.mean(capillary_target)) ** 2))
    r_squared = round(1 - residual / total, 6) if total > 0 else 0.0
    sigma_fit = data.rho * coefficient
    diagnostic_slope, _ = np.polyfit(np.log(k_arr), np.log(omega_arr), 1)

    image = _render_fit_plot(
        k_arr, omega_arr, sigma_fit, data.rho, data.fluid_depth_cm, r_squared
    )
    return {
        "a": round(math.sqrt(coefficient), 6),
        "slope": round(float(diagnostic_slope), 6),
        "sigma_fit": round(sigma_fit, 6),
        "relative_error_fit": round(abs(sigma_fit - data.sigma0) / data.sigma0 * 100, 4)
        if data.sigma0
        else None,
        "r_squared": r_squared,
        "model": "finite-depth-gravity-capillary" if data.fluid_depth_cm else "deep-water-gravity-capillary",
        "img_base64": base64.b64encode(image).decode("ascii"),
    }


def _render_fit_plot(
    k_arr,
    omega_arr,
    sigma_fit: float,
    rho: float,
    fluid_depth_cm: float | None,
    r_squared: float,
) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.scatter(k_arr, omega_arr, color="#6366F1", s=90, label="实验数据")
    k_fit = np.linspace(k_arr.min() * 0.8, k_arr.max() * 1.2, 300)
    depth_factors = (
        np.ones_like(k_fit)
        if fluid_depth_cm is None
        else np.tanh(k_fit * fluid_depth_cm / 100)
    )
    omega_fit = np.sqrt((GRAVITY * k_fit + sigma_fit * k_fit**3 / rho) * depth_factors)
    ax.plot(
        k_fit,
        omega_fit,
        color="#EC4899",
        linewidth=2.8,
        label=rf"重力-毛细拟合: $\sigma={sigma_fit:.4g}\,\mathrm{{N/m}}$",
    )
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
