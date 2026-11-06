# STEM Racing car optimiser

Software that designs, checks and measures a STEM Racing Professional Class car.
The five folders must stay side by side.

| Folder | What it does |
|---|---|
| `part1-simulation` | the milled body and the rules that shape it |
| `part2-simulation` | OpenFOAM airflow and the race-time model |
| `part3-simulation` | the links between Parts 1 and 2 |
| `part4-simulation` | wheels, wings, supports, nose, joints and print files |
| `part5-simulation` | runs a whole car, checks it against the rules, searches for a faster one |

Every push runs all the tests and builds whole cars in parallel (see the Actions
tab). The STEM Racing regulations are not included: get them from the organisers.

Status: the car has not been built or track-tested. Its race times are model
numbers, not measurements.

No licence is granted. All rights reserved.
