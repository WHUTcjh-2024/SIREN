import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ExperimentStateWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: dict[str, Any]

    @field_validator("state")
    @classmethod
    def bounded_state(cls, value):
        if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > 128 * 1024:
            raise ValueError("实验状态不得超过 128 KiB")
        return value


class CalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    f: float = Field(gt=0)
    delta_X_cm: float = Field(gt=0)
    H0: float
    h: float
    L: float = Field(gt=0)
    rho: float = Field(gt=0)
    sigma0: float | None = Field(default=None, gt=0)
    fluid_depth_cm: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def positive_optical_height(self):
        if self.H0 <= self.h:
            raise ValueError("中央峰位置 H₀ 必须高于液面基准 h")
        return self


class FitPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    k: float = Field(gt=0)
    f: float = Field(gt=0)


class FitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    experiment_data: list[FitPoint] = Field(max_length=1000)
    rho: float = Field(gt=0)
    sigma0: float | None = Field(default=None, gt=0)
    fluid_depth_cm: float | None = Field(default=None, gt=0)

    @field_validator("experiment_data")
    @classmethod
    def enough_points(cls, value):
        if len(value) < 2:
            raise ValueError("至少需要两组有效数据")
        return value
