# Part 3 proof

Every number here comes from a GitHub Actions run in `<account>/stem-racing-car`
(account named when it isn't shawshanker18). Marks are the BUILD_SPEC section 8 marks and
have not been changed. Status on 2026-11-11: **not done**. The wing tests and unit tests are
finished; the car tests are running or waiting on Part 1's tag and Part 2's noise mark.

| Test (BUILD_SPEC 8) | Mark | Result | Evidence |
| --- | --- | --- | --- |
| Known-answer wing, adjoint map | sign ≥ 9/10, r ≥ 0.9 | **FAIL** (r 0.53) | 42705451545 |
| Known-answer wing, measured map | same | **PASS** (r 0.977, signs 95 %) | 42705451545 |
| Measured map, wing shapes outside its modes | sign ≥ 80 %, r ≥ 0.8 | **PASS** (r 0.952, signs 90 %) | 42705451545; finer mesh mxnviir 42705489756 |
| Chain rule to race time | within 1 % of Part 2 finite differences | **PASS** (18 tests) | 42668820158 |
| Compass test on cars | sign ≥ 80 %, r ≥ 0.8, ≥ 25 qualifying, sign not fitted | running (measured map) | p3_car_modes.yml, below |
| Step test, 5 fresh cars | ≥ 4 of 5 faster by > 2 × noise | waiting (Part 1 tag) | below |

## 1. Known-answer wing (BUILD_SPEC 12.5)

2-D NACA0012 at Re 3 × 10⁵, drag objective. Every shape measured by central difference on a
fixed mesh. Noise is far below the shape effects (spread about 10⁻⁶ of the drag).

**Adjoint map (`adjointOptimisationFoam`, ESI v2412): FAIL on every setting tried.**
- On the car settings, r is 0.53 on the 10 official bumps and 0.70 on all 20 single bumps;
  signs are 75 % once two-way (grow-here, shrink-there) shapes are included (run 42705451545).
- Also tried: Spalart-Allmaras full setup at its design Re of 6 × 10⁶ (mxnviir 42674505090,
  r 0.42 to 0.55, signs 80 %), a 4 × finer mesh (mxnviir 42687748066, r about −0.5), half speed
  (42682128501), and 5 map settings at three mesh fades (42659214363, mxnviir 42659207636,
  instagramshashank8-bot 42659201716).
- Cause of the size error: the map's simple surface formula is about 66 × too large, and the
  gap is the same at half speed, so it isn't a units fault. The full formula (with the
  mesh-movement terms) gets the size right (slope about 1.0), but the pattern stays poor.
- Two real faults were found and fixed along the way, in `part2-simulation/openfoam_adjoint.py`:
  - the map was read against OpenFOAM's into-the-solid normal;
  - the flow run stopped early because of a leftover residual stop.
  After the fixes, the direction is right on 20 of 20 wing bumps, and the nose test is right on
  18 of 18 cars.

**Measured map (BUILD_SPEC 12.7): PASS.**
- 80 Gaussian modes (r = 0.025 chord). Official bumps r 0.977, slope 0.92, signs 95 % with
  the two-way shapes (run 42705451545).
- 20 hard shapes it was never built from (narrow r 0.015 and 0.025, wide 0.08, three-bump
  mixes): r 0.952, slope 0.98, signs 90 % (18 of 20), all clear of 3 × noise.
- Its only two misses are r 0.015 bumps, finer than the modes can resolve. The resolution is
  about the mode radius.
- On the 4 × finer mesh with 40 modes (mxnviir 42705489756): hard shapes r 0.901, signs 90 %.

**Step rehearsal (BUILD_SPEC 7 step 6, on the wing; run 42726652327 and 42725491014).**
One step down the measured map, sized in bump heights:

| step | measured drag change | predicted |
| --- | --- | --- |
| 0.25 | −0.024 | −0.020 |
| 0.5 | −0.068 | −0.041 |
| 1.5 | −0.179 (−0.67 %) | −0.122 |
| 3 | +0.049 | −0.244 |

Small steps are faster, as predicted. Past about 1.5 bump heights the shape leaves the region
where the map holds. So cuts must stay within about 1.5 mode heights.

## 2. Adjoint on cars (side study)

- Run 42754161855: 2 cars, flow stopped at 3000, 3037 and 3074 steps.
  - The map is the same wherever the swinging flow is stopped: r 0.992 to 0.999, the same sign
    on 95 to 97 % of points and on 99 to 100 % of the strongest quarter.
  - The map reaches all but 1.6 to 2.0 % of the real surface. The unmatched points are on the
    flat closing face at y = 0.
  - Still physically wrong: it says growing the whole car evenly lowers drag. So it is not used.

## 3. Race-time chain rule (BUILD_SPEC 7 step 5)

`compass.race_slope` turns drag and lift slopes into race time with Part 2's `stopwatch.race`
slopes. The mass is held at the target through the skin weight, so the mass term becomes the
centre-of-mass redistribution term. 18 unit tests pass, including finite differences of
`stopwatch.race` within 1 % (run 42668820158).

## 4. Measured map on a carved car (running)

`checks/car_modes.py`, `p3_car_modes.yml`.
- **Base car:** Part 1's start block at skin 3.95 mm.
- **Map:** 60 Gaussian modes of radius 10 mm, each run at ± 1 mm (built on the field, so rule
  zones and milling apply). The map is built straight from race time at the mass target.
- **Test shapes:** 40 random cuts from Part 1's cutter (1 to 3 patches of 6 to 20 mm, 1 and
  1.5 mm deep). None of them is in the mode family.
- **Timing:** every car on the base car's mesh reshaped onto it, warm-started from its flow
  (Part 2's lowest-noise set-up, σ ≈ 0.36 ms).
- **What b is:** the real move of every car, measured from the built bodies. So rule zones and
  milling count as built.
- **Scoring:** only cuts whose change is at least 3 × the noise of a difference
  (3 × 0.36 × √2 = 1.53 ms), with the BUILD_SPEC 12.4 marks.

## 5. Step test plan and its power (BUILD_SPEC 7 step 6)

- **Noise of one before/after pair:** σ√2 = 0.51 ms, with σ = 0.36 ms from Part 2 (reshaped
  mesh plus warm start).
- **Mark:** the time must drop by more than 2 × that, i.e. more than 1.02 ms, on ≥ 4 of 5 cars.
- **Size of each cut:** with an expected gain μ, one car passes with probability
  Φ((μ − 1.02)/0.51). For a 90 % chance of passing the test (≥ 4 of 5), each car needs about
  90 %, so μ ≥ 1.02 + 1.28 × 0.51 ≈ 1.7 ms.
  - So each cut must be sized for a predicted gain of at least 1.7 ms. It must also stay within
    about 1.5 mode heights (wing rehearsal).
  - At μ = 2.5 ms, the chance of passing is over 99 %.
- **Repeats:** a repeat on the same mesh gives almost the same number (Part 2: a mesh
  reshaped onto itself gave the same drag within 0.04 mN, run 42767113050), so repeats are
  not used. The
  noise is the spread across nearby shapes, which σ already measures.
- **Sizes needed:** the real ms per mm comes from section 4. The step sizes will be set from
  it and written here before the step test is run.
