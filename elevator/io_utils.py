from __future__ import annotations

import csv
import statistics
from pathlib import Path
from typing import Dict, List

from .models import Passenger
from .simulation import SimulationResult


def load_requests(path: str | Path) -> List[Passenger]:
    """
    Load requests from a CSV file and return a list of Passenger objects.
    Args:
    path (str | Path): Path to the CSV file containing requests.
    Returns:
    List[Passenger]: A list of Passenger objects created from the CSV data.
    """
    path = Path(path)
    passengers = []
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        required_fields = {"time", "id", "source", "dest"}
        if set(reader.fieldnames or []) != required_fields:
            raise ValueError("CSV must have exactly these columns: time,id,source,dest")
        seen_ids = set()
        for row in reader:
            passenger_id = row["id"].strip()
            if passenger_id in seen_ids:
                # IDs are used as dict keys for onboard passengers
                # Duplicates would let one passenger silently clobber another's state.
                raise ValueError(f"Duplicate passenger id: {passenger_id}")
            seen_ids.add(passenger_id)
            passengers.append(
                Passenger(
                    time=int(row["time"]),
                    id=passenger_id,
                    source=int(row["source"]),
                    dest=int(row["dest"]),
                )
            )
    return passengers


def write_position_log(result: SimulationResult, num_elevators: int, path: str | Path) -> None:
    """
    Write the position log of the simulation to a CSV file.
    Args:
    result (SimulationResult): The result of the simulation containing the position log.
    num_elevators (int): The number of elevators in the simulation.
    path (str | Path): The path to the output CSV file.
    """
    path = Path(path)
    # Create the parent directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create headers for the CSV... time + elevator_0, elevator_1, ...
    headers = ["time"] + [f"elevator_{i}" for i in range(num_elevators)]

    # Write the position log from sim result to CSV
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(result.position_log)


def _metric_row(values: List[int]) -> Dict[str, float]:
    """
    Helper function to compute min, max, avg, median, and stdev for a list of values.
    Args:
    values (List[int]): A list of integer values (time) to compute metrics for.
    Returns:
    Dict[str, float]: A dictionary containing the computed metrics.
    """
    # Handle no values case to avoid statistics errors
    if not values:
        return {"min": 0, "max": 0, "avg": 0, "median": 0, "stdev": 0}

    # Compute metrics based on values per requirements
    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
        "median": statistics.median(values),
        # Use sample standard deviation when possible.
        "stdev": statistics.stdev(values) if len(values) > 1 else 0,
    }


def summarize(result: SimulationResult) -> Dict[str, object]:
    """
    Summarize the simulation results, including passengers served, ticks, and metrics.
    Args:
    result (SimulationResult): The result of the simulation containing passengers and ticks.
    Returns:
    Dict[str, object]: A dictionary containing the summary of the simulation results.
    """
    # Create list of compl passengers (those picked up and dropped off)
    completed = [
        passenger
        for passenger in result.passengers
        if passenger.pickup_time is not None and passenger.dropoff_time is not None
    ]

    # Create lists of wait, travel, and total times for completed passengers
    wait_times = [p.wait_time for p in completed]
    travel_times = [p.travel_time for p in completed]
    total_times = [p.total_time for p in completed]

    # Use helper fcn to return summary analytics
    return {
        "passengers_served": len(completed),
        "ticks": result.ticks,
        "metrics": {
            "Wait time": _metric_row(wait_times),
            "Travel time": _metric_row(travel_times),
            "Total time": _metric_row(total_times),
        },
    }


def _format_number(value: float) -> str:
    """Format integers cleanly and decimals to two places."""
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def print_summary(summary: Dict[str, object]) -> None:
    """
    Print a summary of the simulation results, including passengers served, ticks, and metrics.
    Args:
    summary (Dict[str, object]): A dictionary containing the summary of the simulation results.
    """
    print(f"Passengers served: {summary['passengers_served']}")
    print(f"Simulation ticks:  {summary['ticks']}")
    print()
    # Print the metrics table header
    print(f"{'':<15}{'min':>6}{'max':>6}{'avg':>8}{'median':>9}{'stdev':>8}")

    metrics = summary["metrics"]
    for label in ["Wait time", "Travel time", "Total time"]:
        row = metrics[label]
        print(
            f"{label:<15}"
            f"{_format_number(row['min']):>6}"
            f"{_format_number(row['max']):>6}"
            f"{_format_number(row['avg']):>8}"
            f"{_format_number(row['median']):>9}"
            f"{_format_number(row['stdev']):>8}"
        )
