import unittest

from elevator.models import Direction, Elevator, Passenger, _Stop


class TestPassenger(unittest.TestCase):
    def test_direction(self):
        self.assertEqual(Passenger(0, "a", 1, 10).direction, Direction.UP)
        self.assertEqual(Passenger(0, "a", 10, 1).direction, Direction.DOWN)
        self.assertEqual(Passenger(0, "a", 5, 5).direction, Direction.IDLE)

    def test_times_before_assignment(self):
        p = Passenger(0, "a", 1, 10)
        self.assertIsNone(p.wait_time)
        self.assertIsNone(p.travel_time)
        self.assertIsNone(p.total_time)

    def test_times_after_full_trip(self):
        p = Passenger(time=5, id="a", source=1, dest=10)
        p.pickup_time = 8
        p.dropoff_time = 17
        self.assertEqual(p.wait_time, 3)
        self.assertEqual(p.travel_time, 9)
        self.assertEqual(p.total_time, 12)
        self.assertEqual(p.wait_time + p.travel_time, p.total_time)


class TestElevatorAssignAndService(unittest.TestCase):
    def test_assign_books_pickup_and_dropoff(self):
        e = Elevator(0, capacity=4, start_floor=1)
        p = Passenger(0, "a", 5, 10)
        e.assign(p)
        self.assertIn(5, e.stops)
        self.assertIn(10, e.stops)
        self.assertEqual(e.stops[5].pickups, [p])
        self.assertEqual(e.stops[10].dropoffs, [p])

    def test_pickup_then_dropoff_normal_order(self):
        e = Elevator(0, capacity=4, start_floor=1)
        p = Passenger(0, "a", 1, 3)
        e.assign(p)

        e.service_current_floor(0)  # car is already at floor 1
        self.assertEqual(p.pickup_time, 0)
        self.assertIn("a", e.onboard)

        e.current_floor = 3
        e.service_current_floor(2)
        self.assertEqual(p.dropoff_time, 2)
        self.assertNotIn("a", e.onboard)
        self.assertEqual(e.stops, {})

    def test_capacity_respected_passenger_requeued(self):
        """
        assign() gates committed capacity, so two pending pickups can never
        legitimately land on a 1-seat car via assign() itself (the second
        call would raise). That gate is what keeps this situation from
        arising in practice. This test bypasses assign() to write directly
        into e.stops, so it can still exercise the defensive boarding-time
        fallback in service_current_floor() in isolation.
        """
        e = Elevator(0, capacity=1, start_floor=1)
        p1 = Passenger(0, "a", 1, 5)
        p2 = Passenger(0, "b", 1, 5)
        for p in (p1, p2):
            e.stops.setdefault(p.source, _Stop()).pickups.append(p)
            e.stops.setdefault(p.dest, _Stop()).dropoffs.append(p)

        e.service_current_floor(0)
        # Only one seat: exactly one of them boards, the other keeps waiting.
        self.assertEqual(e.load, 1)
        boarded_id = next(iter(e.onboard))
        waiting = p2 if boarded_id == "a" else p1
        self.assertIsNone(waiting.pickup_time)
        self.assertIn(1, e.stops)  # stop stays open for the still-waiting passenger

    def test_dropoff_reached_before_pickup_does_not_crash(self):
        """Car starts above BOTH floors of an upward trip (source=10,
        dest=20, car at 30): the nearer floor it reaches first is the
        *dropoff* floor, even though nobody has boarded yet. This must
        not raise, and the passenger must still eventually be delivered.
        """
        e = Elevator(0, capacity=4, start_floor=30)
        p = Passenger(0, "a", source=10, dest=20)
        e.assign(p)

        # Walk the car down floor by floor, servicing each stop, exactly
        # as Simulation.run() would.
        for _ in range(40):
            e.service_current_floor(0)
            if p.dropoff_time is not None:
                break
            e._choose_direction()
            if e.direction == Direction.IDLE:
                break
            e.current_floor += int(e.direction)

        self.assertEqual(p.pickup_time is not None, True)
        self.assertEqual(p.dropoff_time is not None, True)
        self.assertGreaterEqual(p.dropoff_time, p.pickup_time)


class TestElevatorDirection(unittest.TestCase):
    def test_idle_picks_nearer_stop(self):
        e = Elevator(0, capacity=4, start_floor=10)
        e.stops[12] = e.stops.get(12)
        from elevator.models import _Stop
        e.stops[12] = _Stop(pickups=[Passenger(0, "a", 12, 20)])
        e.stops[9] = _Stop(pickups=[Passenger(0, "b", 9, 1)])
        e._choose_direction()
        # 12 is 2 away, 9 is 1 away -> should head down
        self.assertEqual(e.direction, Direction.DOWN)

    def test_continues_until_exhausted_then_reverses(self):
        from elevator.models import _Stop
        e = Elevator(0, capacity=4, start_floor=5)
        e.direction = Direction.UP
        e.stops[3] = _Stop(pickups=[Passenger(0, "a", 3, 1)])
        # No stops above floor 5, but one below -> should flip to DOWN
        e._choose_direction()
        self.assertEqual(e.direction, Direction.DOWN)

    def test_is_idle(self):
        e = Elevator(0, capacity=4, start_floor=1)
        self.assertTrue(e.is_idle())
        e.assign(Passenger(0, "a", 1, 5))
        self.assertFalse(e.is_idle())


if __name__ == "__main__":
    unittest.main()
