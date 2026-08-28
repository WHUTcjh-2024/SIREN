import math

from backend.schemas.experiment import CalculationRequest, FitPoint, FitRequest
from backend.services.calculation import calculate_surface_tension, fit_surface_tension


def test_calculation_returns_finite_surface_tension():
    result = calculate_surface_tension(CalculationRequest(
        f=50, delta_X_cm=0.075, H0=20, h=5, L=100, rho=1000, fluid_depth_cm=2
    ))
    assert math.isfinite(result["sigma"])
    assert result["sigma"] > 0
    assert 0 < result["gravity_fraction"] < 1
    assert result["model"] == "finite-depth-gravity-capillary"


def test_fit_recovers_surface_tension_with_gravity(monkeypatch):
    monkeypatch.setattr("backend.services.calculation._render_fit_plot", lambda *_: b"png")
    sigma = 0.072
    rho = 1000
    points = [
        FitPoint(k=k, f=math.sqrt(9.80665 * k + sigma * k**3 / rho) / (2 * math.pi))
        for k in (500, 1000, 1500, 2000)
    ]
    result = fit_surface_tension(FitRequest(experiment_data=points, rho=1000))
    assert result["sigma_fit"] == sigma
    assert result["r_squared"] > 0.999


def test_calculation_rejects_nonphysical_frequency_wave_number_pair():
    try:
        calculate_surface_tension(CalculationRequest(
            f=50, delta_X_cm=1.2, H0=20, h=5, L=100, rho=1000
        ))
    except ValueError as exc:
        assert "不满足重力-毛细波色散关系" in str(exc)
    else:
        raise AssertionError("nonphysical input should be rejected")
