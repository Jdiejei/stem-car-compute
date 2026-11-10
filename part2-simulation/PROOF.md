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

## Reshaped meshes on carved shapes (remesh limit, in progress)

Six local cuts from Part 1's cutter on the start block (nose, sidepod side, tail
top; 0.5 and 2 mm deep, Gaussian patch sigma 8 mm), each timed on a mesh reshaped
from a reference car and on a fresh mesh; reference = the start block through a
negligible cut, so it shares the cutter's milling (shawshanker18/stem-racing-car
run 42804229269, `cut_cars.py`, `p2_reshape_cuts.yml`):

| cut | D fresh N | D reshaped N | diff mN | diff ms | reshaped mesh |
| --- | --- | --- | --- | --- | --- |
| nose 0.5 mm | 0.5933 | 0.5938 | +0.43 | +0.22 | OK |
| nose 2 mm | 0.5939 | 0.5937 | -0.23 | -0.12 | OK |
| rear 0.5 mm | 0.5935 | 0.5949 | +1.36 | +0.70 | OK |
| rear 2 mm | 0.5936 | 0.5937 | +0.07 | +0.04 | OK |
| sidepod 0.5 mm | 0.5956 | 0.5917 | -3.85 | -1.99 | OK |
| sidepod 2 mm | 0.5897 | 0.5896 | -0.11 | -0.05 | OK |

- The same car on two fresh meshes differs by up to 1.8 mN (run 42713902174, where
  every reshape fell back to a fresh mesh), so 5 of 6 cuts agree within that.
- The sidepod 0.5 mm case (3.85 mN) is not explained yet.
- How the reshape got here: plain projection onto the new surface folded one face
  on every cut. Moving each point by the CHANGE of the surface, read from a
  16-digit ASCII copy of the reference mesh, fixed most of it. Smoothing that change
  over 0.5 mm removed the point-to-point jumps at sharp edges. A reference mesh
  reshaped onto itself (zero move) gives the identical drag (+0.04 mN, run 42767113050).

## Timing noise (Step 2, in progress; pass mark 0.3 ms)

Residual SD of race time about a fitted line, ≥ 15 converged cars at skins
0.006–0.01 mm apart, search mesh (medium, no layers), with the 95 % chi-square
interval and the part explained by each car's own averaging error
(`noise_stats.py`). All after the SIMPLE early stop was removed.

| set-up | sigma ms (95 %) | averaging part ms | run |
| --- | --- | --- | --- |
| fresh mesh per car, 1000 it | 8.65 (6.27–13.93) | 0.61 | blackwingftc-lang 42654416947 |
| fresh mesh, 3000 it | 5.02 (3.68–7.92) | 0.28 | mxnviir 42670749731 |
| fresh mesh + warm start | 6.88 (4.93–11.35) | 0.44 | shawshanker18 42804234820 |
| reshaped mesh (first method, one face folded) | 4.09 (2.96–6.59) | 0.57 | blackwingftc-lang 42654555331 |
| **reshaped mesh + warm start, 1000 it** | **0.78 (0.56–1.25)** | 0.62 | shawshanker18 42830660133 |

- Fresh meshes put near-identical cars on different drag levels (up to 12 % apart:
  body and rear-wheel drag switch together). A time-accurate run (pimpleFoam, 0.12 s,
  about 11 flow-throughs, shawshanker18 42760508026) kept each car on its own level.
- With one reshaped mesh and a warm start, all 16 cars sit on one branch and drag
  falls smoothly with skin. What remains is mostly each car's averaging error. A
  3000-iteration run of that set-up is next.
- The skins 4.00–4.05 mm of the first runs also carried a Part 1 body step (fixed in
  Part 1 55696e3), so the later ladders stop at 3.99 mm.

## Repeatability (1 car x 6 machines; pass mark spread ≤ 0.1 ms): FAIL so far

Start car at skin 3.95 mm, fresh search mesh, 1000 iterations, six GitHub machines
(shawshanker18/stem-racing-car run 42864304133): T_at_target 1.57259, 1.57293,
1.57265, 1.57200, 1.57234, 1.57199 s, all converged; **spread 0.94 ms**.

- The earlier 0.28 ms (2026-11) was measured with the SIMPLE early stop, which ended
  every solve at about 170 iterations.
- Run to its full length, the wake keeps moving, so small machine-to-machine
  arithmetic differences change each run's average. The spread is the size of one
  car's averaging error (rms about 0.6 ms on the noise ladders), so the same fix
  applies: longer averaging (3000 iterations running).
- At 0.6 ms per 200 averaged steps, reaching 0.1 ms by averaging alone would need
  about 36 times longer. If longer runs don't get there, this pass mark needs the
  team lead's decision, with this evidence.

## Still to prove

- Ahmed body benchmarks: 35° reported (RANS limit); 25° and the cube are the pass cases (decision 2026-11-09).
- Noise ≤ 0.3 ms: being fixed (reshaped meshes plus warm starts).
- Repeatability, warm start, chained long runs, race model on measured inputs, model vs track.
