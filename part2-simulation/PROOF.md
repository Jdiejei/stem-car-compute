# Part 2 proof: results against BUILD_SPEC section 8

Every number here comes from a GitHub run (or a Codespace, where stated). Run IDs
are in the repo named with them. Model times are model times, not track times.

## Ranking agreement (Step 3): PASS

| | value | pass mark |
| --- | --- | --- |
| Spearman, all 20 cars | 0.965 | ≥ 0.9 |
| pairs > 3 ms apart on fine that agree, all 20 | 170 / 173 = 98.3 % | ≥ 90 % |
| Spearman, 18 converged cars (C4, C7 fine runs unconverged, left out) | 0.963 | ≥ 0.9 |
| pairs agreeing, 18 converged | 135 / 137 = 98.5 % | ≥ 90 % |

- Cars: Part 5's stress cars, 12 lofted (L0–L11, seed 47000) and 8 carved (C0–C7,
  seed 47001), built by `rank_study.py`, all at commit f5161e5.
- Search mesh (medium, no layers, 1000 iterations): mxnviir/stem-racing-car run
  42660880514 (rs3), 20 of 20.
- Fine mesh (1000 iterations): shawshanker18/stem-racing-car run 42660871261 (rf3),
  18 of 20. C0 and L0 needed more than the 5 h stage limit / 6 h job limit and were
  rerun on 4-core Codespaces (blackwingftc-lang, mxnviir) at the same commit with
  only the stage-runner `cd` fix (no effect on results) and stage_timeout_s 40000:
  C0 T = 1.61772 s, L0 T = 1.56052 s, both converged.
- Statistics: shawshanker18/stem-racing-car runs 42820976300 (20 cars) and
  42820970393 (18 converged), `rank_study.py stats`.
- Ranked on `T_at_target_s` (each car's race time at the mass target), so the order
  is set by aerodynamics, not by mass differences between the cars.

## Still to prove

- Ahmed body benchmarks: 35° reported (RANS limit); 25° and the cube are the pass cases (decision 2026-11-09).
- Noise ≤ 0.3 ms: being fixed (reshaped meshes plus warm starts).
- Repeatability, warm start, chained long runs, race model on measured inputs, model vs track.
