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

## Still to prove

- Ahmed body benchmarks: 35° reported (RANS limit); 25° and the cube are the pass cases (decision 2026-11-09).
- Noise ≤ 0.3 ms: being fixed (reshaped meshes plus warm starts).
- Repeatability, warm start, chained long runs, race model on measured inputs, model vs track.
