from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional


class Direction(IntEnum):
    """
    This enum represents the direction of an elevator or passenger.
    DOWN: The elevator or passenger is moving downwards.
    IDLE: The elevator or passenger is not moving.
    UP: The elevator or passenger is moving upwards.
    """
    DOWN = -1
    IDLE = 0
    UP = 1


@dataclass
class Passenger:
    """
    This class represents a passenger in the elevator system.
    This class is used to ultimately keep track of the passenger's times.

    Request Attributes:
    time (int): The time when the passenger made the request.
    id (str): A unique identifier for the passenger.
    source (int): The floor where the passenger is waiting.
    dest (int): The floor where the passenger wants to go.

    In-System Attributes:
    assigned_elevator (Optional[int]): The ID of the elevator assigned to the passenger.
    pickup_time (Optional[int]): The time when the passenger was picked up.
    dropoff_time (Optional[int]): The time when the passenger was dropped off.
    """
    time: int
    id: str
    source: int
    dest: int

    assigned_elevator: Optional[int] = None
    pickup_time: Optional[int] = None
    dropoff_time: Optional[int] = None

    @property
    def direction(self) -> Direction:
        """
        Determine the direction the passenger wants to go based on their source & destination floors.
        Returns:
        Direction: The direction the passenger wants to go (UP, DOWN, or IDLE).
        """
        if self.dest > self.source:
            return Direction.UP
        if self.dest < self.source:
            return Direction.DOWN
        return Direction.IDLE

    @property
    def wait_time(self) -> Optional[int]:
        """
        Calculate the time the passenger waited before being picked up.
        Returns:
        Optional[int]: The wait time, or None if the passenger hasn't been picked up yet.
        """
        if self.pickup_time is None:
            return None
        return self.pickup_time - self.time

    @property
    def travel_time(self) -> Optional[int]:
        """
        Calculate the time the passenger spent in the elevator.
        Returns:
        Optional[int]: The travel time, or None if the passenger hasn't been dropped off yet.
        """
        if self.pickup_time is None or self.dropoff_time is None:
            return None
        return self.dropoff_time - self.pickup_time

    @property
    def total_time(self) -> Optional[int]:
        """
        Calculate the total time the passenger spent from making the request to being dropped off.
        Returns:
        Optional[int]: The total time, or None if the passenger hasn't been dropped off yet.
        """
        if self.dropoff_time is None:
            return None
        return self.dropoff_time - self.time


@dataclass
class _Stop:
    """
    This class represents a stop in the elevator system, which can have passengers waiting to be picked up or dropped off.
    Attributes:
    pickups (List[Passenger]): A list of passengers waiting to be picked up at this stop
    dropoffs (List[Passenger]): A list of passengers waiting to be dropped off at this stop
    """
    pickups: List[Passenger] = field(default_factory=list)
    dropoffs: List[Passenger] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """
        Check if there are no passengers waiting to be picked up or dropped off at this stop.
        Returns:
        bool: True if there are no passengers waiting, False otherwise.
        """
        return not self.pickups and not self.dropoffs


class Elevator:
    """
    This class represents an elevator in the elevator system.
    Attributes:
    id (int): unique identifier for the elevator.
    capacity (int): The max # of passengers the elevator can hold.
    current_floor (int): The floor where the elevator is currently located.

    direction (Direction): The current direction of the elevator (UP, DOWN, or IDLE).
    onboard (Dict[str, Passenger]): A dictionary of passengers currently in the elevator, keyed by passenger ID.
    stops (Dict[int, _Stop]): A dictionary of stops the elevator is committed to servicing, keyed by floor number.
    floors_traveled (int): The total number of floors the elevator has traveled since the start of the simulation.
    """
    def __init__(self, elevator_id: int, capacity: int, start_floor: int = 1):

        # Initialize the elevator w/ its attr
        self.id = elevator_id
        self.capacity = capacity
        self.current_floor = start_floor
        
        # Elevator starts idle w/ no passengers onboard and no committed stops.
        self.direction = Direction.IDLE
        self.onboard: Dict[str, Passenger] = {}
        self.stops: Dict[int, _Stop] = {}
        self.floors_traveled = 0

    @property
    def load(self) -> int:
        """Number of passengers currently onboard."""
        return len(self.onboard)

    def has_capacity(self) -> bool:
        """Check if the elevator has room for more passengers. Calc by onboard vs capacity."""
        return self.load < self.capacity

    def committed_load(self) -> int:
        """Onboard passengers plus passengers assigned but not yet picked up."""
        # Count the # of passengers waiting to be picked up at each committed stop.
        pending_pickups = sum(len(stop.pickups) for stop in self.stops.values())
        return self.load + pending_pickups

    def has_committed_capacity(self) -> bool:
        """Check if the elevator has room for more passengers, incl those committed to be picked up."""
        return self.committed_load() < self.capacity

    def is_idle(self) -> bool:
        """Check if the elevator is idle (not moving, no committed stops, and no passengers onboard)."""
        return self.direction == Direction.IDLE and not self.stops and not self.onboard

    def assign(self, passenger: Passenger) -> None:
        """
        This function assigns the passenger to this elevator and commits their pickup and dropoff stops.
        This function is called by the scheduler when it decides to assign a passenger to this elevator.
        Args:
        passenger (Passenger): The passenger to be assigned to this elevator.
        Raises:
        ValueError: If the elevator has no committed capacity available.
        """
        # If elevator has no committed cap, raise error (sim made mistake)
        if not self.has_committed_capacity():
            raise ValueError(f"Elevator {self.id} has no committed capacity available.")
        
        # Assign passenger to elevator and add their pickup/dropoff stops to the elevator's schedule.
        passenger.assigned_elevator = self.id

        # Add the passenger to the pickup and dropoff stops for this elevator. 
        # If the stop doesn't exist yet, create it.
        self.stops.setdefault(passenger.source, _Stop()).pickups.append(passenger)
        self.stops.setdefault(passenger.dest, _Stop()).dropoffs.append(passenger)

    def service_current_floor(self, t: int) -> None:
        """
        This function services the current floor of the elevator.
        The function drops off passengers who have reached their destination and picks up passengers who are waiting to be picked up.
        Args:
        t (int): The current time in the simulation.
        """
        # Get the stop for the current floor. If there is no stop, return early.
        stop = self.stops.get(self.current_floor)
        if stop is None:
            return
        
        # Drop off who have reached their destination.
        still_to_drop = []
        for passenger in stop.dropoffs:
            if passenger.id in self.onboard:
                del self.onboard[passenger.id]
                passenger.dropoff_time = t
            else:
                # Passenger was committed to this stop but never actually boarded
                # (e.g. the elevator was full when it passed their pickup floor).
                still_to_drop.append(passenger)
        stop.dropoffs = still_to_drop

        # Pick up those who are waiting.
        still_waiting = []
        for passenger in stop.pickups:
            # Check if elevator has capacity to pickup.
            if self.has_capacity():
                self.onboard[passenger.id] = passenger
                passenger.pickup_time = t
            else:
                # No room right now. Leave them at this floor for a later pass.
                still_waiting.append(passenger)
        stop.pickups = still_waiting

        # If none are waiting to be picked up or dropped off, remove the stop.
        if stop.is_empty:
            del self.stops[self.current_floor]

    def _choose_direction(self) -> None:
        """
        This function determines the direction the elevator should move based on its current state.
        - The elevator will continue in its current direction if there are committed stops in that direction.
        - If there are no committed stops in the current direction, the elevator will check for stops in the opposite direction.
        - If there are no committed stops in either direction, the elevator will remain idle.
        
        The elevator will also consider the nearest committed stops in both directions when it is currently idle.
        """
        # Determine the committed stops in both directions relative to the current floor.
        ups = [floor for floor in self.stops if floor > self.current_floor]
        downs = [floor for floor in self.stops if floor < self.current_floor]

        # Determine the new direction based on the current direction and the committed stops.
        if self.direction == Direction.UP:
            self.direction = Direction.UP if ups else Direction.DOWN if downs else Direction.IDLE
        elif self.direction == Direction.DOWN:
            self.direction = Direction.DOWN if downs else Direction.UP if ups else Direction.IDLE
        else:
            # Currently idle: head toward whichever side has a stop, and if both
            # sides do, pick whichever is closer.
            if ups and not downs:
                self.direction = Direction.UP
            elif downs and not ups:
                self.direction = Direction.DOWN
            elif ups and downs:
                # If there are stops in both directions, choose the nearest one.
                nearest_up = min(ups) - self.current_floor
                nearest_down = self.current_floor - max(downs)
                self.direction = Direction.UP if nearest_up <= nearest_down else Direction.DOWN
            else:
                self.direction = Direction.IDLE

    def move(self) -> None:
        """
        This function moves the elevator one floor in its current direction.
        The function determines the direction, then updates the current floor and the total # of floors traveled.
        """
        self._choose_direction()
        if self.direction != Direction.IDLE:
            self.current_floor += int(self.direction)
            self.floors_traveled += 1
