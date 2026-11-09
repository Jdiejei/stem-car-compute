<p align="center"><img src="assets/banner.png" alt="part3-simulation" width="100%"></p>

> Where the parts meet and improve each other.

> **Status 2026-11-09:** the plan is carving from the block. How to build and test this part, with its rules and pass marks: `BUILD_SPEC.md` (in the private repo). Old work is kept read-only as `archive/*` tags.

| | |
|---|---|
| **What it is** | The connections between Parts 1 and 2, and the loop that improves one body. |
| **Source** | Private |
| **Public overview** | https://github.com/shawshanker18/stem-racing-overview |

**The STEM Racing set**

| Part | Repository |
|---|---|
| 1 | [part1-simulation](https://github.com/shawshanker18/part1-simulation) |
| 2 | [part2-simulation](https://github.com/shawshanker18/part2-simulation) |
| 3 | [part3-simulation](https://github.com/shawshanker18/part3-simulation) |
| 4 | [part4-simulation](https://github.com/shawshanker18/part4-simulation) |
| 5 | [part5-simulation](https://github.com/shawshanker18/part5-simulation) |

---

The compass: where a cut makes the car faster. Not proven yet; see `BUILD_SPEC.md`.

| module | what |
|---|---|
| `pipeline_interface.py` | `unified_bindings`: every callable the pipeline needs from Parts 1 and 2 (build the field, quality gates and the CFD-ready half STL, mass report, CFD, race objective, adjoint weight, adjoint, level-set update, candidate record). Part 5's `run_car.py` uses these for every car |
| `gradient_combiner.py`, `objective_policy.py`, `convergence.py`, `stability_check.py`, `optimizer_contract.py` | weighting of drag, mass and COM slopes, the penalty policy, convergence tests, the static-stability check, and the configuration and outcome types |
| `inner_loop.py` | the OLD carving loop, retired 2026-09-30. `run_car.py --optimise` still calls it; it is to be replaced by the cutter (Part 1) plus compass step and then deleted |

What is known: the drag adjoint had the right sign on only 3 of 8 settings
(2026-09-28). Until it passes the compass test in `BUILD_SPEC.md`, nobody may trust it.

```bash
python -m pytest tests -q
```

The five repositories must sit side by side (`part1-simulation` … `part5-simulation`).
