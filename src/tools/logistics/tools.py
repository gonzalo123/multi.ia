import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

from strands import tool

from settings import Dbnames
from .models import ShipmentRecord, LogisticsDataset

logger = logging.getLogger(__name__)


class LogisticsTools:
    def __init__(self, node: Dbnames, default_origins: Optional[List[str]] = None,
                 default_destinations: Optional[List[str]] = None):
        self.node = node
        self.default_origins = default_origins or ["WH-A", "WH-B"]
        self.default_destinations = default_destinations or ["CUST-1", "CUST-2", "CUST-3"]

    def get_tools(self, tools=None) -> List[tool]:
        @tool
        def get_logistics_data(
                from_date: date,
                to_date: date,
                origins: Optional[List[str]] = None,
                destinations: Optional[List[str]] = None,
                hours_per_day: int = 8,
        ) -> LogisticsDataset:
            """Generate synthetic logistics shipment data.
            Args:
                from_date: Start date (inclusive)
                to_date: End date (inclusive)
                origins: Origin codes list (defaults internal)
                destinations: Destination codes list (defaults internal)
                hours_per_day: How many hourly shipment slots to simulate per origin
            Returns:
                LogisticsDataset with aggregated metrics
            """
            if to_date < from_date:
                raise ValueError("to_date must be >= from_date")
            origins = origins or self.default_origins
            destinations = destinations or self.default_destinations

            records: List[ShipmentRecord] = []
            day_cursor = from_date
            while day_cursor <= to_date:
                base_dt = datetime.combine(day_cursor, datetime.min.time())
                for origin in origins:
                    for h in range(hours_per_day):
                        dest = destinations[(h + len(origin)) % len(destinations)]
                        records.append(
                            ShipmentRecord.synthetic(idx=h, base_dt=base_dt, origin=origin, destination=dest))
                day_cursor += timedelta(days=1)

            logger.info(f"[get_logistics_data] Generated {len(records)} shipment records")
            return LogisticsDataset.from_records(records)

        @tool
        def get_logistics_summary(
                from_date: date,
                to_date: date,
        ) -> Dict[str, Any]:
            """Quick summary of synthetic logistics KPIs for date range."""
            ds = get_logistics_data(from_date=from_date, to_date=to_date)
            return {
                "total_shipments": ds.total_shipments,
                "delivered": ds.delivered,
                "delayed": ds.delayed,
                "avg_delay_minutes": ds.avg_delay_minutes,
                "total_weight_kg": ds.total_weight_kg,
                "total_distance_km": ds.total_distance_km,
                "total_cost_eur": ds.total_cost_eur,
            }

        @tool
        def get_logistics_route_analysis(
                from_date: date,
                to_date: date,
                origins: Optional[List[str]] = None,
                destinations: Optional[List[str]] = None,
                hours_per_day: int = 8,
                sort_by: str = "delay_rate",
                top: int = 10,
        ) -> List[Dict[str, Any]]:
            """Analyze origin-destination routes and return aggregated metrics.
            Args:
                from_date: Start date (inclusive)
                to_date: End date (inclusive)
                origins: Override origin list
                destinations: Override destination list
                hours_per_day: Slots per origin per day passed to generator
                sort_by: One of 'delay_rate', 'avg_delay_minutes', 'total_cost_eur'
                top: Limit number of routes returned
            Returns:
                List of dicts with: route, origin, destination, shipments, delayed, delay_rate, avg_delay_minutes,
                total_cost_eur, avg_cost_eur, total_weight_kg, total_distance_km, cost_per_km
            """
            dataset = get_logistics_data(
                from_date=from_date,
                to_date=to_date,
                origins=origins,
                destinations=destinations,
                hours_per_day=hours_per_day,
            )
            if sort_by not in {"delay_rate", "avg_delay_minutes", "total_cost_eur"}:
                sort_by = "delay_rate"
            route_stats: Dict[str, Dict[str, Any]] = {}
            for r in dataset.records:
                key = f"{r.origin}->{r.destination}"
                stats = route_stats.setdefault(key, {
                    "route": key,
                    "origin": r.origin,
                    "destination": r.destination,
                    "shipments": 0,
                    "delayed": 0,
                    "total_delay_minutes": 0,
                    "total_cost_eur": 0.0,
                    "total_weight_kg": 0.0,
                    "total_distance_km": 0.0,
                })
                stats["shipments"] += 1
                if r.delay_minutes > 0:
                    stats["delayed"] += 1
                stats["total_delay_minutes"] += r.delay_minutes
                stats["total_cost_eur"] += r.cost_eur
                stats["total_weight_kg"] += r.weight_kg
                stats["total_distance_km"] += r.distance_km

            enriched: List[Dict[str, Any]] = []
            for key, s in route_stats.items():
                shipments = s["shipments"]
                delay_rate = s["delayed"] / shipments if shipments else 0.0
                avg_delay = s["total_delay_minutes"] / shipments if shipments else 0.0
                avg_cost = s["total_cost_eur"] / shipments if shipments else 0.0
                cost_per_km = s["total_cost_eur"] / s["total_distance_km"] if s["total_distance_km"] else 0.0
                enriched.append({
                    "route": s["route"],
                    "origin": s["origin"],
                    "destination": s["destination"],
                    "shipments": shipments,
                    "delayed": s["delayed"],
                    "delay_rate": round(delay_rate, 3),
                    "avg_delay_minutes": round(avg_delay, 2),
                    "total_cost_eur": round(s["total_cost_eur"], 2),
                    "avg_cost_eur": round(avg_cost, 2),
                    "total_weight_kg": round(s["total_weight_kg"], 1),
                    "total_distance_km": round(s["total_distance_km"], 1),
                    "cost_per_km": round(cost_per_km, 4),
                })
            enriched.sort(key=lambda d: d[sort_by], reverse=True)
            logger.info(f"[get_logistics_route_analysis] Computed stats for {len(enriched)} routes")
            return enriched[:top]

        all_tools = [get_logistics_data, get_logistics_summary, get_logistics_route_analysis]
        return all_tools if tools is None else [t for t in all_tools if t.__name__ in tools]
