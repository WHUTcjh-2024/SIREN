import math

from backend.schemas.experiment import CalculationRequest, FitPoint, FitRequest
from backend.services.calculation import calculate_surface_tension, fit_surface_tension


def test_calculation_returns_finite_surface_tension():
    result = calculate_surface_tension(CalculationRequest(
        f=50, delta_X_cm=1.2, H0=20, h=5, L=100, rho=1000
    ))
    assert math.isfinite(result["sigma"])
    assert result["sigma"] > 0


def test_fit_recovers_three_halves_dispersion_slope(monkeypatch):
    monkeypatch.setattr("backend.services.calculation._render_fit_plot", lambda *_: b"png")
    points = [FitPoint(k=k, f=(2.0 * k**1.5) / (2 * math.pi)) for k in (10, 20, 40, 80)]
    result = fit_surface_tension(FitRequest(experiment_data=points, rho=1000))
    assert result["slope"] == 1.5
    assert result["r_squared"] > 0.999
