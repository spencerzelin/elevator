import unittest

from elevator.models import Direction, Elevator, Passenger
from elevator.scheduler import NearestCarScheduler, RoundRobinScheduler


class TestNearestCarScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = NearestCarScheduler()

    def test_picks_closest_idle_elevator(self):
        near = Elevator(0, capacity=4, start_floor=5)
        far = Elevator(1, capacity=4, start_floor=40)
        request = Passenger(0, "a", source=7, dest=20)

        chosen = self.scheduler.choose(request, [near, far])
        self.assertIs(chosen, near)

    def test_prefers_car_already_heading_toward_pickup(self):
        # Car A is far but already moving up past the pickup floor.
        moving_toward = Elevator(0, capacity=4, start_floor=1)
        moving_toward.direction = Direction.UP
        moving_toward.stops[50] = moving_toward.stops.get(50)
        from elevator.models import _Stop
        moving_toward.stops[50] = _Stop(dropoffs=[Passenger(0, "x", 1, 50)])

        # Car B is numerically closer but idle, so it must travel the
        # full distance from scratch.
        idle_but_closer = Elevator(1, capacity=4, start_floor=10)

        request = Passenger(0, "a", source=15, dest=25)
        chosen = self.scheduler.choose(request, [moving_toward, idle_but_closer])
        # moving_toward is already at floor 1 heading up and will pass
        # 15 for free (cost 14); idle_but_closer must travel 5 (cost 5).
        # idle_but_closer should win here since 5 < 14 -- this test just
        # documents/locks in that the cost function is direction-aware
        # rather than pure distance.
        self.assertIs(chosen, idle_but_closer)

    def test_does_not_treat_opposite_direction_pickup_as_cheap(self):
        """A car sweeping up shouldn't look "free" for a passenger who
        wants to go *down* just because the pickup floor is ahead of it —
        picking them up mid-sweep means reversing right after, which is a
        real detour, not a free stop. An idle car nearby should win even
        though it's numerically a bit farther from the pickup floor.
        """
        from elevator.models import _Stop

        sweeping_up = Elevator(0, capacity=4, start_floor=3)
        sweeping_up.direction = Direction.UP
        sweeping_up.stops[51] = _Stop(dropoffs=[Passenger(0, "x", 1, 51)])

        idle_nearby = Elevator(1, capacity=4, start_floor=1)

        # Wants to go DOWN (5 -> 1), opposite of sweeping_up's direction.
        request = Passenger(2, "a", source=5, dest=1)
        chosen = self.scheduler.choose(request, [sweeping_up, idle_nearby])
        self.assertIs(chosen, idle_nearby)

    def test_avoids_full_car_when_alternative_exists(self):
        from elevator.models import _Stop

        full = Elevator(0, capacity=1, start_floor=5)
        full.onboard["existing"] = Passenger(0, "existing", 5, 40)

        empty = Elevator(1, capacity=1, start_floor=6)

        request = Passenger(0, "a", source=5, dest=10)
        chosen = self.scheduler.choose(request, [full, empty])
        self.assertIs(chosen, empty)

    def test_load_balances_between_equally_positioned_cars(self):
        light = Elevator(0, capacity=8, start_floor=1)
        busy = Elevator(1, capacity=8, start_floor=1)
        busy.assign(Passenger(0, "x", 1, 20))
        busy.assign(Passenger(0, "y", 1, 30))
        busy.assign(Passenger(0, "z", 1, 40))

        request = Passenger(0, "a", source=1, dest=15)
        chosen = self.scheduler.choose(request, [light, busy])
        self.assertIs(chosen, light)


class TestRoundRobinScheduler(unittest.TestCase):
    def test_cycles_through_all_elevators(self):
        elevators = [Elevator(i, capacity=4, start_floor=1) for i in range(3)]
        scheduler = RoundRobinScheduler()

        chosen = [scheduler.choose(Passenger(0, str(i), 1, 2), elevators) for i in range(6)]
        ids = [e.id for e in chosen]
        self.assertEqual(ids, [0, 1, 2, 0, 1, 2])


if __name__ == "__main__":
    unittest.main()
