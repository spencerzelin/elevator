from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .models import Elevator, Passenger
from .scheduler import Scheduler


@dataclass
class SimulationResult:
    """
    This class represents the result of a simulation run.
    Attributes:
    passengers (List[Passenger]): A list of passengers that were part of the simulation.
    position_log (List[List[int]]): A log of the positions of elevators at each tick
    ticks (int): The total number of ticks the simulation ran for.
    """
    passengers: List[Passenger]
    position_log: List[List[int]]
    ticks: int


class Simulation:
    """
    This class represents a simulation of an elevator system.
    It initializes the elevators and passengers, and runs the simulation based on the provided scheduler.
    Attributes:
    requests (List[Passenger]): A list of passengers that will be part of the simulation.
    elevators (List[Elevator]): A list of elevators that will be part of the simulation
    scheduler (Scheduler): The scheduling algorithm used to assign passengers to elevators.
    """
    def __init__(self, requests: List[Passenger], num_elevators: int, num_floors: int, capacity: int, scheduler: Scheduler, start_floor: int = 1):
        # Validate input parameters to ensure they are within acceptable ranges.
        if num_elevators < 1:
            raise ValueError("num_elevators must be at least 1")
        if num_floors < 2:
            raise ValueError("num_floors must be at least 2")
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        if not (1 <= start_floor <= num_floors):
            raise ValueError(f"start_floor {start_floor} is outside 1..{num_floors}")
        for request in requests:
            if request.time < 0:
                raise ValueError(f"Request {request.id!r} has negative time")
            if not (1 <= request.source <= num_floors):
                raise ValueError(f"Request {request.id!r} has invalid source floor")
            if not (1 <= request.dest <= num_floors):
                raise ValueError(f"Request {request.id!r} has invalid destination floor")
        
        # Ensure requests are in the correct order during the simulation.
        self.requests = sorted(requests, key=lambda r: r.time)

        # Create list of initialized elevators
        self.elevators = [Elevator(elevator_id=i, capacity=capacity, start_floor=start_floor) for i in range(num_elevators)]
        self.scheduler = scheduler

        # Source == dest requests need no elevator; resolve them immediately.
        for request in self.requests:
            if request.source == request.dest:
                request.pickup_time = request.time
                request.dropoff_time = request.time

    def run(self, max_ticks: int = 1_000_000) -> SimulationResult:
        """
        This function runs the elevator simulation until all passengers have been serviced or the maximum number of ticks is reached.
        It releases passengers based on their arrival time, assigns them to elevators using the scheduler, and
        moves the elevators accordingly.
        Args:
        max_ticks (int): The maximum number of ticks to run the simulation. Default is 1,000,000.
        Returns:
        SimulationResult: The result of the simulation, including the list of passengers, position log,
        and total ticks.
        """
        position_log: List[List[int]] = []
        next_request_idx = 0
        t = 0
        unassigned: List[Passenger] = []
        while True:
            # Release any requests whose arrival time has come, skipping
            # same-floor "requests" that were already resolved instantly in __init__.
            while next_request_idx < len(self.requests) and self.requests[next_request_idx].time == t:
                passenger = self.requests[next_request_idx]
                next_request_idx += 1
                if passenger.source != passenger.dest:
                    unassigned.append(passenger)
            # Try to hand off newly released (or previously unassignable) passengers
            # to an elevator with committed capacity.
            unassigned = self._assign_available(unassigned)
            # Board/alight passengers at each elevator's current floor before moving.
            for elevator in self.elevators:
                elevator.service_current_floor(t)
            position_log.append([t] + [e.current_floor for e in self.elevators])
            all_released = next_request_idx >= len(self.requests)
            all_idle = all(e.is_idle() for e in self.elevators)
            if all_released and not unassigned and all_idle:
                break
            if t >= max_ticks:
                raise RuntimeError(f"Simulation did not terminate within {max_ticks} ticks")
            for elevator in self.elevators:
                elevator.move()
            t += 1
        return SimulationResult(passengers=self.requests, position_log=position_log, ticks=t)

    def _assign_available(self, passengers: List[Passenger]) -> List[Passenger]:
        """Attempt to assign each passenger to an elevator; anyone the
        scheduler can't place yet (e.g. all elevators full) is carried over
        to be retried next tick."""
        still_unassigned = []
        for passenger in passengers:
            chosen = self.scheduler.choose(passenger, self.elevators)
            if chosen is None:
                still_unassigned.append(passenger)
            else:
                chosen.assign(passenger)
        return still_unassigned
