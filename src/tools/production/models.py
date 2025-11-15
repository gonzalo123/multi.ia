from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from random import gauss, random, uniform
from typing import List

from pydantic import BaseModel, Field, field_validator, model_validator


class Shift(str, Enum):
    """Production shift.
    A = Morning, M = Afternoon, N = Night."""

    A = "A"  # Morning
    M = "M"  # Afternoon
    N = "N"  # Night

    @staticmethod
    def from_hour(hour: int) -> "Shift":
        # Shift boundaries: Morning 06-13, Afternoon 14-21, Night 22-05
        if 6 <= hour < 14:
            return Shift.A
        if 14 <= hour < 22:
            return Shift.M
        return Shift.N


class ProductionData(BaseModel):
    """Hourly production KPIs for an industrial machine.

    Synthetic but coherent rules:
    - Optimal temperature ~ (75-85°C). Deviation increases scrap.
    - Higher speed may increase scrap if experience is low.
    - High humidity or pressure far from mid-range penalize scrap.
    - Unplanned stop triggers a significant scrap increase.
    """

    timestamp: datetime = Field(description="Timestamp (start of hour)")
    machine_id: str = Field(description="Machine identifier")
    shift: Shift = Field(description="Production shift (A/M/N)")

    temperature: float = Field(ge=0, le=200, description="Process temperature (°C)")
    speed: float = Field(ge=0, le=1000, description="Production speed (units/hour)")
    humidity: float = Field(ge=0, le=100, description="Relative humidity (%)")
    pressure: float = Field(ge=0, le=50, description="Pressure (bar)")

    operator_experience: float = Field(ge=0, le=50, description="Operator experience (years)")
    scrap_kg: float = Field(ge=0, description="Scrap produced (kg) in the hour")
    unplanned_stop: bool = Field(description="Unplanned stop indicator")

    @field_validator("timestamp")
    @classmethod
    def truncate_to_hour(cls, v: datetime) -> datetime:
        # Ensure timestamp aligned to hour start
        return v.replace(minute=0, second=0, microsecond=0)

    @model_validator(mode="after")
    def recompute_shift(self) -> "ProductionData":
        # Enforce consistency between hour and shift
        expected_shift = Shift.from_hour(self.timestamp.hour)
        if self.shift != expected_shift:
            object.__setattr__(self, "shift", expected_shift)
        return self

    @staticmethod
    def _synthetic_scrap(
        temperature: float,
        speed: float,
        humidity: float,
        pressure: float,
        operator_experience: float,
        unplanned_stop: bool,
    ) -> float:
        # Base scrap inversely related to experience
        base = max(0.2, 3.0 - operator_experience * 0.1)
        # Penalties for suboptimal conditions (using 0.0 for float consistency)
        temp_penalty = max(0.0, abs(temperature - 80) * 0.05)  # optimal 80°C
        speed_penalty = max(0.0, (speed - 600) * 0.003) if speed > 600 else 0.0
        humidity_penalty = 0.02 * max(0.0, humidity - 60)
        pressure_penalty = 0.1 * max(0.0, abs(pressure - 20))
        stop_penalty = 5.0 if unplanned_stop else 0.0

        noise = max(0.0, gauss(0.0, 0.3))  # small positive noise
        scrap = base + temp_penalty + speed_penalty + humidity_penalty + pressure_penalty + stop_penalty + noise
        return round(max(scrap, 0.0), 2)

    @classmethod
    def synthetic_record(
        cls,
        machine_id: str,
        dt: datetime,
        operator_experience: float | None = None,
        force_unplanned_stop: bool | None = None,
    ) -> "ProductionData":
        """Generate a coherent synthetic hourly record.

        Args:
            machine_id: Machine ID.
            dt: Date/time (will be truncated to hour).
            operator_experience: Years of experience (random 1-25 if None).\n
            force_unplanned_stop: Explicit override for unplanned stop.
        """
        dt_trunc = dt.replace(minute=0, second=0, microsecond=0)
        shift = Shift.from_hour(dt_trunc.hour)

        exp = operator_experience if operator_experience is not None else round(uniform(1, 25), 1)

        # Base parameters by shift (e.g. slightly lower night temperature)
        base_temp = 82 if shift == Shift.A else (80 if shift == Shift.M else 78)
        temperature = round(base_temp + gauss(0, 3), 2)

        speed = round(uniform(500, 750) + (exp * 2), 1)
        humidity = round(uniform(40, 70), 1)
        pressure = round(uniform(18, 22) + gauss(0, 1.2), 2)

        unplanned_stop = force_unplanned_stop if force_unplanned_stop is not None else (random() < 0.05)

        scrap = cls._synthetic_scrap(
            temperature=temperature,
            speed=speed,
            humidity=humidity,
            pressure=pressure,
            operator_experience=exp,
            unplanned_stop=unplanned_stop,
        )
        return cls(
            timestamp=dt_trunc,
            machine_id=machine_id,
            shift=shift,
            temperature=temperature,
            speed=speed,
            humidity=humidity,
            pressure=pressure,
            operator_experience=exp,
            scrap_kg=scrap,
            unplanned_stop=unplanned_stop,
        )

    @classmethod
    def synthetic_day(
        cls,
        machine_id: str,
        day: datetime,
        operator_experience: float | None = None,
    ) -> List["ProductionData"]:
        """Generate 24 hourly records for a full day."""
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        return [
            cls.synthetic_record(machine_id=machine_id, dt=start + timedelta(hours=i), operator_experience=operator_experience)
            for i in range(24)
        ]


class ProductionDataset(BaseModel):
    """Container for multiple ProductionData records plus simple aggregates."""
    records: List[ProductionData] = Field(default_factory=list, description="Hourly production records")
    total_scrap_kg: float = Field(ge=0, description="Total scrap (kg) across all records")
    avg_scrap_kg: float = Field(ge=0, description="Average scrap (kg) per record")
    unplanned_stops: int = Field(ge=0, description="Number of unplanned stops")

    @classmethod
    def from_records(cls, records: List[ProductionData]) -> "ProductionDataset":
        if not records:
            return cls(records=[], total_scrap_kg=0.0, avg_scrap_kg=0.0, unplanned_stops=0)
        total = sum(r.scrap_kg for r in records)
        stops = sum(1 for r in records if r.unplanned_stop)
        avg = round(total / len(records), 2)
        return cls(records=records, total_scrap_kg=round(total, 2), avg_scrap_kg=avg, unplanned_stops=stops)


__all__ = ["Shift", "ProductionData", "ProductionDataset"]
