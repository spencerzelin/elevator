# Elevator System Simulation

A discrete-time simulation of a destination-dispatch elevator system.

Passengers submit an origin and destination floor at a specific request
time. The simulation assigns each passenger to an elevator, moves the
elevators one floor per time step, and records passenger statistics and
elevator positions.

------------------------------------------------------------------------

# Features

-   Multiple elevators
-   Configurable building size and elevator capacity
-   Destination-dispatch scheduling
-   Direction-aware nearest-car scheduler (default)
-   Round Robin scheduler for comparison
-   Position logging
-   Passenger wait/travel/total time statistics
-   Unit test suite using Python's standard `unittest` library

------------------------------------------------------------------------

# Running the Simulation

No external dependencies are required (Python 3.9+).

``` bash
python main.py
```

or specify custom options:

``` bash
python main.py \
    --requests sample_requests.csv \
    --elevators 4 \
    --floors 60 \
    --capacity 8 \
    --scheduler nearest
```

### Command Line Options

  -----------------------------------------------------------------------------
  Flag            Description                      Default
  --------------- -------------------------------- ----------------------------
  `--requests`    Input CSV                        `data/sample_requests.csv`
                  (`time,id,source,dest`)          

  `--elevators`   Number of elevators              `4`

  `--floors`      Number of floors                 `60`

  `--capacity`    Elevator capacity                `8`

  `--scheduler`   `nearest` or `round_robin`       `nearest`

  `--output`      Position log output              `output/positions.csv`
  -----------------------------------------------------------------------------

Note: the default `--requests` path (`data/sample_requests.csv`) assumes a
`data/` folder that isn't checked into this repo. Pass `--requests
sample_requests.csv` (or `sample_requests2.csv`), both of which live at the
repo root, or point at your own CSV.

The simulation writes:

-   `output/positions.csv`
-   Passenger summary statistics to the console

------------------------------------------------------------------------

# Project Structure

``` text
main.py
elevator/
├── models.py          Passenger, Elevator and Direction models
├── scheduler.py       Scheduling algorithms
├── simulation.py      Discrete-time simulation loop
└── io_utils.py        CSV parsing and output utilities

tests/
└── Unit tests

sample_requests.csv     Small example request file (time,id,source,dest)
sample_requests2.csv    A second, smaller example request file
elevator.pptx           Slide deck walking through the design and results
output/                 Position log output (created at runtime)
```

------------------------------------------------------------------------

# Input Format

The input CSV must contain:

``` csv
time,id,source,dest
0,passenger1,1,51
0,passenger2,1,37
10,passenger3,20,1
```

Requests become available only when their timestamp is reached. The
scheduler never has access to future requests.

------------------------------------------------------------------------

# Implementation Overview

## Simulation Loop

Each simulation tick performs the following steps:

1.  Release newly arrived requests.
2.  Assign requests to elevators.
3.  Drop off passengers at the current floor.
4.  Pick up waiting passengers.
5.  Move each elevator one floor.
6.  Record elevator positions.

The simulation ends once:

-   every request has been released,
-   every passenger has been dropped off,
-   every elevator is idle.

------------------------------------------------------------------------

## Scheduling

### Nearest Car Scheduler (default)

The primary scheduler is a direction-aware nearest-car heuristic.

For each new request, every elevator receives an estimated pickup cost
based on:

-   distance to the pickup floor,
-   current travel direction,
-   whether the passenger is already on the elevator's path,
-   number of committed stops.

Elevators that have reached **committed capacity** are excluded from
consideration.

This approach is intentionally greedy rather than globally optimal. It
makes decisions using only the current system state and never looks
ahead to future requests.

### Round Robin Scheduler

A simple baseline scheduler is included for comparison.

Round Robin ignores elevator position and direction and simply cycles
through available elevators. It provides a useful reference when
comparing scheduling strategies.

------------------------------------------------------------------------

# Committed Capacity

The scheduler distinguishes between:

-   passengers currently onboard, and
-   passengers already assigned but waiting to be picked up.

This prevents assigning more passengers to an elevator than it will
eventually be able to serve.

------------------------------------------------------------------------

# Assumptions

-   One time unit equals one floor of travel.
-   Boarding and exiting are instantaneous.
-   Drop-offs occur before pickups at the same floor.
-   Elevators start on floor 1.
-   Requests with the same source and destination are treated as
    immediately complete.
-   The scheduler does not look ahead to future requests.

------------------------------------------------------------------------

# Time Spent

Approximately 10 hours total:

-   ~8 hours on core code/logic (models, scheduler, simulation loop, tests)
-   ~2 hours on visuals and the presentation deck

------------------------------------------------------------------------

# Future Improvements

Given additional time, possible enhancements include:

-   benchmarking multiple scheduling algorithms
-   idle elevator repositioning
-   fairness / maximum wait constraints
-   visualization of elevator movement
-   tuning scheduler cost parameters using larger simulated workloads

------------------------------------------------------------------------

# Testing

Run the test suite with:

``` bash
python -m unittest discover -s tests -v
```

The tests cover:

-   passenger and elevator models
-   scheduler behavior
-   elevator capacity
-   no-look-ahead behavior
-   invalid inputs
-   end-to-end simulation

------------------------------------------------------------------------

# Presentation Materials

-   `elevator.pptx` — a walkthrough deck covering the problem spec,
    architecture, scheduling logic, and demo results.

Example commands for generating comparable output when presenting:

``` bash
python main.py --requests sample_requests.csv \
    --elevators 4 --floors 60 --capacity 8 \
    --scheduler nearest --output output/positions_nearest.csv

python main.py --requests sample_requests.csv \
    --elevators 4 --floors 60 --capacity 8 \
    --scheduler round_robin --output output/positions_roundrobin.csv
```
