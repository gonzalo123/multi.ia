from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from random import gauss, uniform, random
from typing import List

from pydantic import BaseModel, Field


class TransportMode(str, Enum):
    TRUCK = "TRUCK"
    TRAIN = "TRAIN"
    SHIP = "SHIP"
    AIR = "AIR"


class ShipmentStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    DELAYED = "DELAYED"


class ShipmentRecord(BaseModel):
    timestamp: datetime = Field(description="Timestamp (hour granularity)")
    shipment_id: str = Field(description="Unique shipment identifier")
    origin: str = Field(description="Origin location code")
    destination: str = Field(description="Destination location code")
    transport_mode: TransportMode = Field(description="Transport mode")

    pallets: int = Field(ge=0, description="Number of pallets")
    weight_kg: float = Field(ge=0, description="Gross weight (kg)")
    distance_km: float = Field(ge=0, description="Estimated distance (km)")

    status: ShipmentStatus = Field(description="Current status")
    delay_minutes: int = Field(ge=0, description="Delay minutes (0 if on time)")
    cost_eur: float = Field(ge=0, description="Estimated or actual cost (EUR)")

    @staticmethod
    def synthetic(
        idx: int,
        base_dt: datetime,
        origin: str,
        destination: str,
    ) -> "ShipmentRecord":
        ts = base_dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=idx)
        mode = uniform(0, 1)
        if mode < 0.55:
            transport_mode = TransportMode.TRUCK
        elif mode < 0.7:
            transport_mode = TransportMode.TRAIN
        elif mode < 0.9:
            transport_mode = TransportMode.SHIP
        else:
            transport_mode = TransportMode.AIR

        pallets = int(uniform(5, 40))
        weight_kg = round(pallets * uniform(150, 350), 1)
        distance_km = round(uniform(50, 1500), 1)

        # Base cost by mode
        cost_factor = {
            TransportMode.TRUCK: 1.0,
            TransportMode.TRAIN: 0.8,
            TransportMode.SHIP: 0.6,
            TransportMode.AIR: 2.5,
        }[transport_mode]
        cost_eur = round(distance_km * 0.9 * cost_factor + pallets * 5, 2)

        # Delay probability by mode (air lower, ship higher)
        delay_prob = {
            TransportMode.TRUCK: 0.15,
            TransportMode.TRAIN: 0.1,
            TransportMode.SHIP: 0.25,
            TransportMode.AIR: 0.05,
        }[transport_mode]
        delayed = random() < delay_prob
        delay_minutes = int(gauss(45, 20)) if delayed else 0
        if delay_minutes < 0:
            delay_minutes = 0

        status = ShipmentStatus.DELIVERED if not delayed else ShipmentStatus.DELAYED
        # Some still in transit (simple heuristic)
        if random() < 0.1:
            status = ShipmentStatus.IN_TRANSIT
        if random() < 0.05:
            status = ShipmentStatus.PLANNED

        return ShipmentRecord(
            timestamp=ts,
            shipment_id=f"S{ts.strftime('%Y%m%d%H')}-{idx:03d}",
            origin=origin,
            destination=destination,
            transport_mode=transport_mode,
            pallets=pallets,
            weight_kg=weight_kg,
            distance_km=distance_km,
            status=status,
            delay_minutes=delay_minutes,
            cost_eur=cost_eur,
        )


class LogisticsDataset(BaseModel):
    records: List[ShipmentRecord]
    total_shipments: int
    delivered: int
    delayed: int
    avg_delay_minutes: float
    total_weight_kg: float
    total_distance_km: float
    total_cost_eur: float

    @classmethod
    def from_records(cls, records: List[ShipmentRecord]) -> "LogisticsDataset":
        if not records:
            return cls(records=[], total_shipments=0, delivered=0, delayed=0, avg_delay_minutes=0.0,
                       total_weight_kg=0.0, total_distance_km=0.0, total_cost_eur=0.0)
        total_shipments = len(records)
        delivered = sum(1 for r in records if r.status == ShipmentStatus.DELIVERED)
        delayed = sum(1 for r in records if r.status == ShipmentStatus.DELAYED)
        avg_delay = round(sum(r.delay_minutes for r in records) / total_shipments, 2)
        total_weight = round(sum(r.weight_kg for r in records), 1)
        total_distance = round(sum(r.distance_km for r in records), 1)
        total_cost = round(sum(r.cost_eur for r in records), 2)
        return cls(
            records=records,
            total_shipments=total_shipments,
            delivered=delivered,
            delayed=delayed,
            avg_delay_minutes=avg_delay,
            total_weight_kg=total_weight,
            total_distance_km=total_distance,
            total_cost_eur=total_cost,
        )


__all__ = ["TransportMode", "ShipmentStatus", "ShipmentRecord", "LogisticsDataset"]

