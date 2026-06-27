from typing import Any

from pydantic import BaseModel, Field, field_validator


class ExperimentStateWrite(BaseModel):
    sid: str | None = None
    state: dict[str, Any]


class CalculationRequest(BaseModel):
    f: float = Field(gt=0)
    delta_X_cm: float = Field(gt=0)
    H0: float
    h: float
    L: float = Field(gt=0)
    rho: float = Field(gt=0)
    sigma0: float | None = Field(default=None, gt=0)


class FitPoint(BaseModel):
    k: float = Field(gt=0)
    f: float = Field(gt=0)


class FitRequest(BaseModel):
    experiment_data: list[FitPoint]
    rho: float = Field(gt=0)
    sigma0: float | None = Field(default=None, gt=0)

    @field_validator("experiment_data")
    @classmethod
    def enough_points(cls, value):
        if len(value) < 2:
            raise ValueError("至少需要两组有效数据")
        return value
