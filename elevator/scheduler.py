from __future__ import annotations

from abc import ABC, abstractmethod
from itertools import cycle
from typing import List, Optional

from .models import Direction, Elevator, Passenger


class Scheduler(ABC):
    """
    Abstract base class for elevator scheduling algorithms.
    Subclasses must implement the `choose` method to select an elevator for a given passenger.
    """
    @abstractmethod
    def choose(self, passenger: Passenger, elevators: List[Elevator]) -> Optional[Elevator]:
        raise NotImplementedError


class NearestCarScheduler(Scheduler):
    """
    Direction-aware nearest-car scheduler.

    Elevators already moving toward the passenger in the same direction receive a low cost. 
    Elevators at committed capacity are skipped entirely.
    """
    # Cost of picking up a passenger is the number of floors traveled to reach them, plus a penalty for each committed stop already queued up.
    LOAD_PENALTY = 2

    def choose(self, passenger: Passenger, elevators: List[Elevator]) -> Optional[Elevator]:
        """
        This function chooses the best elevator for a given passenger based on the nearest-car scheduling algorithm.
        It calculates the cost for each elevator to pick up the passenger.
        This fcn considers the elevator's current direction, committed stops, and capacity.
        Elevators that are at committed capacity are skipped entirely.
        
        Args:
        passenger (Passenger): The passenger for whom an elevator is being chosen.
        elevators (List[Elevator]): A list of available elevators to choose from.
        Returns:
        Optional[Elevator]: The chosen elevator, or None if no suitable elevator is available."""
        # Get the avail candidate elevators
        candidates = [e for e in elevators if e.has_committed_capacity()]
        if not candidates:
            return None
        # Return the candidate elevator w/ the min cost to pick up the passenger.
        return min(candidates, key=lambda elevator: self._cost(elevator, passenger))

    def _cost(self, elevator: Elevator, passenger: Passenger) -> float:
        """
        This helper function calculates the cost for a given elevator to pick up a specific passenger.
        The cost is determined by the # of floors the elevator must travel to reach the passenger,
        plus a penalty for each committed stop already queued up in the elevator.

        Args:
        elevator (Elevator): The elevator for which the cost is being calculated.
        passenger (Passenger): The passenger for whom the cost is being calculated.
        Returns:
        float: The calculated cost for the elevator to pick up the passenger.
        """
        cur = elevator.current_floor
        src = passenger.source
        if elevator.direction == Direction.IDLE or not elevator.stops:
            # Free to go straight to the pickup floor.
            travel_cost = abs(cur - src)
        else:
            # Check elevator direction (up = True, down = False)
            heading_up = elevator.direction == Direction.UP

            # Is elevator ahead? Check direction w/ source & current floor
            spatially_ahead = (heading_up and src >= cur) or ((not heading_up) and src <= cur)
            
            same_direction = passenger.direction == elevator.direction
            if spatially_ahead and same_direction:
                # Passenger is on the way and wants to go the same way we're
                # already heading, so we'll just pick them up in passing.
                travel_cost = abs(cur - src)
            else:
                # Passenger is behind us or wants the opposite direction, so we
                # have to finish the current sweep before turning back for them.
                turnaround = self._sweep_end(elevator, heading_up)
                travel_cost = abs(cur - turnaround) + abs(turnaround - src)

        # Penalize elevators that already have a lot of committed stops queued up.
        return travel_cost + self.LOAD_PENALTY * len(elevator.stops)

    @staticmethod
    def _sweep_end(elevator: Elevator, heading_up: bool) -> int:
        """Farthest committed stop in the current direction of travel — i.e.
        where the elevator will turn around before it can double back."""
        cur = elevator.current_floor
        if heading_up:
            candidates = [floor for floor in elevator.stops if floor >= cur]
            return max(candidates) if candidates else cur
        candidates = [floor for floor in elevator.stops if floor <= cur]
        return min(candidates) if candidates else cur


class RoundRobinScheduler(Scheduler):
    """
    Simple baseline scheduler for COMPARISON only.
    
    Assigns passengers to elevators in a round-robin fashion, meaning each elevator is considered in turn.
    Elevators that are at committed capacity are skipped.
    """
    def __init__(self):
        # Use a cycle iterator to keep track of the next elevator to consider for assignment.
        self._order: Optional[cycle] = None

    def choose(self, passenger: Passenger, elevators: List[Elevator]) -> Optional[Elevator]:
        """
        This function chooses an elevator for a given passenger using a round-robin approach.
        It iterates through the elevators in a cyclic manner, skipping any elevators that are at committed capacity.
        If all elevators are at committed capacity, it returns None.
        
        Args:
        passenger (Passenger): The passenger for whom an elevator is being chosen.
        elevators (List[Elevator]): A list of available elevators to choose from.
        Returns:
        Optional[Elevator]: The chosen elevator, or None if no suitable elevator is available.
        """
        if self._order is None:
            self._order = cycle(elevators)
        for _ in range(len(elevators)):
            elevator = next(self._order)
            if elevator.has_committed_capacity():
                return elevator
        return None
