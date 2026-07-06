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
    num_elevators (int): The number of elevators in the simulation.
    num_floors (int): The number of floors in the building.
    capacity (int): The maximum capacity of each elevator.
    start_floor (int): The starting floor for all elevators.
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

        # Handle source = destination where requests dont need elevator... can resolve.
        for request in self.requests:
            if request.source == request.dest:
                request.pickup_time = request.time
                request.dropoff_time = request.time

    def run(self, max_ticks: int = 1_000_000) -> SimulationResult:
        """
        This function runs the simulation until all passengers have been serviced or max ticks is reached.
        It releases passengers based on their arrival time, assigns them to elevators using the scheduler, and
        moves the elevators accordingly.
        Args:
        max_ticks (int): The max # of ticks to run the simulation. Default is 1,000,000.
        Returns:
        SimulationResult (class): result of the simulation
        """
        position_log: List[List[int]] = []
        next_request_idx = 0
        t = 0
        unassigned: List[Passenger] = []

        while True:
            # Get the passengers from the requests whose arrival time has come
            while next_request_idx < len(self.requests) and self.requests[next_request_idx].time == t:
                passenger = self.requests[next_request_idx]
                next_request_idx += 1
                if passenger.source != passenger.dest:
                    unassigned.append(passenger)
            
            # Try to assign passengers to an elevator with committed capacity.
            unassigned = self._assign_available(unassigned)

            # Board/alight passengers at each elevator's current floor before moving.
            for elevator in self.elevators:
                elevator.service_current_floor(t)

            # Log positions of elevators current floors
            position_log.append([t] + [e.current_floor for e in self.elevators])

            # Did we release everyone? Are elevators all idle?
            all_released = next_request_idx >= len(self.requests)
            all_idle = all(e.is_idle() for e in self.elevators)

            if all_released and not unassigned and all_idle:
                break
            if t >= max_ticks:
                raise RuntimeError(f"Simulation did not terminate within {max_ticks} ticks")
            
            # Finally move the elevators and tick
            for elevator in self.elevators:
                elevator.move()
            t += 1
        return SimulationResult(passengers=self.requests, position_log=position_log, ticks=t)

    def _assign_available(self, passengers: List[Passenger]) -> List[Passenger]:
        """
        This functoin attempts to assign each passenger to an elevator
        Anyone the scheduler can't place yet (all elevators full) is carried over to next tick.
        
        Args:
        passengers (List[Passenger]): list of unassigned passengers part of this tick
        Returns:
        still_unassigned (List[Passenger]): list of STILL unassigned passengers after this tick
        """
        still_unassigned = []
        for passenger in passengers:
            chosen = self.scheduler.choose(passenger, self.elevators)
            if chosen is None:
                still_unassigned.append(passenger)
            else:
                chosen.assign(passenger)
        return still_unassigned
