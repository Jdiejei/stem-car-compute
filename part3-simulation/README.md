<p align="center"><img src="assets/banner.png" alt="part3-simulation" width="100%"></p>

> Where the parts meet and improve each other.

> **Status 2026-11-09:** the plan is carving from the block. How to build and test this part, with its rules and pass marks: `BUILD_SPEC.md` (in the private repo). Old work is kept read-only as `archive/*` tags.

| | |
|---|---|
| **What it is** | The connections between Parts 1 and 2, and the loop that improves one body. |
| **Source** | Private |
| **Public overview** | https://github.com/Shashanksaraswat123939/stem-racing-overview |

**The STEM Racing set**

| Part | Repository |
|---|---|
| 1 | [part1-simulation](https://github.com/Shashanksaraswat123939/part1-simulation) |
| 2 | [part2-simulation](https://github.com/Shashanksaraswat123939/part2-simulation) |
| 3 | [part3-simulation](https://github.com/Shashanksaraswat123939/part3-simulation) |
| 4 | [part4-simulation](https://github.com/Shashanksaraswat123939/part4-simulation) |
| 5 | [part5-simulation](https://github.com/Shashanksaraswat123939/part5-simulation) |

---

| module | what |
|---|---|
| `pipeline_interface.py` | `unified_bindings`: every callable the pipeline needs from Parts 1 and 2 (build the field, quality gates and the CFD-ready half STL, mass report, CFD, race objective, adjoint weight, adjoint, level-set update, candidate record). Part 5's `run_car.py` uses these for every car. |
| `inner_loop.py` | the CFD + adjoint + Hamilton-Jacobi descent on one body (`run_car.py --optimise N`). The adjoint failed its gradient check on this car, so the body search is Part 5's pattern search on direct CFD instead. |
| `optimizer_contract.py` | the loop's configuration and outcome types |
| `convergence.py`, `stability_check.py`, `gradient_combiner.py`, `objective_policy.py` | the loop's convergence tests, the static-stability check, the weighting of drag, mass and COM gradients, and the penalty policy |

The population search over wheelbase and halo position (orchestrator, wheelbase
sweep, evolutionary layer, parallel runner, robustness check) was retired on
2026-09-30 with Part 1's outer search: the parametric body is the car.

```bash
python -m pytest tests -q
```

The five repositories must sit side by side (`part1-simulation` … `part5-simulation`).
