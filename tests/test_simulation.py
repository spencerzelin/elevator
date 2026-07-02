import unittest

from elevator.models import Passenger
from elevator.scheduler import NearestCarScheduler, RoundRobinScheduler
from elevator.simulation import Simulation


def make_sim(requests, num_elevators=2, num_floors=60, capacity=8, scheduler=None):
    return Simulation(
        requests=requests,
        num_elevators=num_elevators,
        num_floors=num_floors,
        capacity=capacity,
        scheduler=scheduler or NearestCarScheduler(),
    )


class TestSimulationBasics(unittest.TestCase):
    def test_all_passengers_eventually_served(self):
        requests = [
            Passenger(0, "p1", 1, 51),
            Passenger(0, "p2", 1, 37),
            Passenger(10, "p3", 20, 1),
        ]
        result = make_sim(requests).run()

        for p in result.passengers:
            self.assertIsNotNone(p.pickup_time, f"{p.id} never picked up")
            self.assertIsNotNone(p.dropoff_time, f"{p.id} never dropped off")
            self.assertGreaterEqual(p.pickup_time, p.time)
            self.assertGreaterEqual(p.dropoff_time, p.pickup_time)

    def test_does_not_peek_ahead(self):
        # A request at time 10 must not affect elevator behavior before t=10.
        requests = [Passenger(0, "early", 1, 5), Passenger(10, "late", 55, 56)]
        result = make_sim(requests, num_elevators=1).run()
        # Before t=10, elevator 0 should never have moved toward floor 55
        # (it should be busy with / finished the early request near floor 1-5).
        for row in result.position_log:
            t, floor = row[0], row[1]
            if t < 10:
                self.assertLessEqual(floor, 6, f"elevator moved toward the late request too early (t={t}, floor={floor})")

    def test_position_log_starts_at_zero_and_is_contiguous(self):
        requests = [Passenger(0, "p1", 1, 10)]
        result = make_sim(requests, num_elevators=1).run()
        times = [row[0] for row in result.position_log]
        self.assertEqual(times, list(range(len(times))))
        self.assertEqual(times[0], 0)

    def test_degenerate_same_floor_request(self):
        requests = [Passenger(3, "p1", 7, 7)]
        result = make_sim(requests, num_elevators=1).run()
        p = result.passengers[0]
        self.assertEqual(p.pickup_time, 3)
        self.assertEqual(p.dropoff_time, 3)
        self.assertEqual(p.wait_time, 0)
        self.assertEqual(p.total_time, 0)

    def test_capacity_enforced_across_the_run(self):
        # 1 elevator, capacity 1, two people want to leave floor 1 at once.
        requests = [Passenger(0, "a", 1, 20), Passenger(0, "b", 1, 30)]
        result = make_sim(requests, num_elevators=1, capacity=1).run()
        for p in result.passengers:
            self.assertIsNotNone(p.dropoff_time)
        # They can't have been onboard at the same time with capacity 1;
        # simplest observable proxy: pickup times differ.
        a, b = result.passengers
        self.assertNotEqual(a.pickup_time, b.pickup_time)

    def test_round_robin_scheduler_also_completes(self):
        requests = [Passenger(0, "a", 1, 20), Passenger(0, "b", 30, 5), Passenger(5, "c", 10, 50)]
        result = make_sim(requests, num_elevators=2, scheduler=RoundRobinScheduler()).run()
        for p in result.passengers:
            self.assertIsNotNone(p.dropoff_time)

    def test_empty_request_list_terminates_immediately(self):
        result = make_sim([]).run()
        self.assertEqual(result.ticks, 0)
        self.assertEqual(len(result.position_log), 1)  # just the t=0 row


class TestSimulationValidation(unittest.TestCase):
    def test_rejects_floor_out_of_range(self):
        with self.assertRaises(ValueError):
            make_sim([Passenger(0, "a", 1, 999)], num_floors=60)

    def test_rejects_zero_elevators(self):
        with self.assertRaises(ValueError):
            make_sim([], num_elevators=0)

    def test_rejects_zero_capacity(self):
        with self.assertRaises(ValueError):
            make_sim([], capacity=0)


if __name__ == "__main__":
    unittest.main()
