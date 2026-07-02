from __future__ import annotations

import argparse
import os

from elevator.io_utils import load_requests, print_summary, summarize, write_position_log
from elevator.scheduler import NearestCarScheduler, RoundRobinScheduler
from elevator.simulation import Simulation

SCHEDULERS = {"nearest": NearestCarScheduler, "round_robin": RoundRobinScheduler}


def parse_args():
    """
    Helper function to parse command line arguments.
    
    Args Include:
    --requests: Path to CSV with columns time,id,source,dest
    --elevators: Number of elevators in the simulation
    --floors: Number of floors in the simulation
    --capacity: Capacity of each elevator
    --scheduler: Scheduler to use for the simulation
    --output: Where to write the position log
    """
    parser = argparse.ArgumentParser(description="Run the elevator system simulation.")
    parser.add_argument("--requests", default="data/sample_requests.csv", help="Path to CSV with columns time,id,source,dest")
    parser.add_argument("--elevators", type=int, default=4)
    parser.add_argument("--floors", type=int, default=60)
    parser.add_argument("--capacity", type=int, default=8)
    parser.add_argument("--scheduler", choices=sorted(SCHEDULERS.keys()), default="nearest")
    parser.add_argument("--output", default="output/positions.csv", help="Where to write the position log")
    return parser.parse_args()


def main():
    # Run the helper fcn to parse command line arguments
    args = parse_args()

    # Load requests into a list of Passenger objects
    requests = load_requests(args.requests)

    # Initialize the scheduler chosen and simulation
    scheduler = SCHEDULERS[args.scheduler]()
    sim = Simulation(
        requests=requests, 
        num_elevators=args.elevators, 
        num_floors=args.floors, 
        capacity=args.capacity, 
        scheduler=scheduler
    )
    
    # Run the simulation and write the position log
    result = sim.run()

    # write_position_log also creates the output dir, but do it here too so a
    # bad --output path fails fast rather than after the (possibly slow) run.
    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    write_position_log(result, args.elevators, args.output)

    # Summary metrics are printed to the console for testing/convenience
    # Position log is the main output of the simulation.
    print_summary(summarize(result))
    print(f"\nPosition log written to {args.output}")


if __name__ == "__main__":
    main()
