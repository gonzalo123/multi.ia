import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

import requests
from strands import tool

from settings import Dbnames
from .models import ProductionData, ProductionDataset

logger = logging.getLogger(__name__)


class ProductionTools:
    def __init__(self, node: Dbnames, default_machines: Optional[List[str]] = None):
        self.node = node
        self.default_machines = default_machines or ["M-01"]

    def get_tools(self, tools=None) -> List[tool]:
        @tool
        def get_production_data(
            from_date: date,
            to_date: date,
            machines: Optional[List[str]] = None,
            operator_experience: Optional[float] = None,
        ) -> ProductionDataset:
            """Generate synthetic hourly production data for a date range.
            Notes:
                - Returns a ProductionDataset including records and simple aggregates.
                - Data is generated locally (no external API calls).
            Args:
                from_date: Start date (inclusive)
                to_date: End date (inclusive)
                machines: List of machine IDs (defaults to internal default list)
                operator_experience: If provided fixes experience for all records
            Returns:
                ProductionDataset: Synthetic dataset
            """
            if to_date < from_date:
                raise ValueError("to_date must be >= from_date")

            machine_ids = machines or self.default_machines
            all_records: List[ProductionData] = []

            current_day = from_date
            days = 0
            while current_day <= to_date:
                day_dt = datetime.combine(current_day, datetime.min.time())
                for mid in machine_ids:
                    day_records = ProductionData.synthetic_day(
                        machine_id=mid,
                        day=day_dt,
                        operator_experience=operator_experience,
                    )
                    all_records.extend(day_records)
                current_day += timedelta(days=1)
                days += 1

            logger.info(
                f"[get_production_data] Generated {len(all_records)} records for {len(machine_ids)} machines over {days} day(s)."
            )
            return ProductionDataset.from_records(all_records)

        @tool
        def get_production_summary(
            from_date: date,
            to_date: date,
            machines: Optional[List[str]] = None,
            operator_experience: Optional[float] = None,
        ) -> Dict[str, Any]:
            """Return only aggregated synthetic production KPIs for quick summaries.
            Args are same as get_production_data.
            Returns:
                Dict with keys: machines, days, hours, total_scrap_kg, avg_scrap_kg, unplanned_stops, scrap_per_machine
            """
            dataset = get_production_data(
                from_date=from_date,
                to_date=to_date,
                machines=machines,
                operator_experience=operator_experience,
            )
            machine_ids = machines or self.default_machines
            scrap_per_machine: Dict[str, float] = {}
            for m in machine_ids:
                scrap_per_machine[m] = round(
                    sum(r.scrap_kg for r in dataset.records if r.machine_id == m), 2
                )
            hours = len(dataset.records)
            days = (to_date - from_date).days + 1
            summary = {
                "machines": machine_ids,
                "days": days,
                "hours": hours,
                "total_scrap_kg": dataset.total_scrap_kg,
                "avg_scrap_kg": dataset.avg_scrap_kg,
                "unplanned_stops": dataset.unplanned_stops,
                "scrap_per_machine": scrap_per_machine,
            }
            logger.info(
                f"[get_production_summary] Summary computed for {len(machine_ids)} machines over {days} day(s)."
            )
            return summary

        all_tools = [get_production_data, get_production_summary]
        return all_tools if tools is None else [t for t in all_tools if t.__name__ in tools]
