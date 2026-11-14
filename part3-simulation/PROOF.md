# Part 3 proof

Every number here comes from a GitHub Actions run in `<account>/stem-racing-car`
(account named when it isn't shawshanker18). Marks are the BUILD_SPEC section 8 marks and
have not been changed. Status on 2026-11-14: **not done**. The wing tests and unit tests are
finished. The fast (adjoint) map was dropped on 2026-11-13 because it failed the known-answer
test on every setting (section 1); the measured map is the compass. The car tests are running:
the medium-mesh method test (section 4) and the fine-mesh check (section 4b). Every compass
result that counts and every carving-loop step is on the fine mesh, and finalists are confirmed
on the resolved mesh (user decision, 2026-11-13).

| Test (BUILD_SPEC 8) | Mark | Result | Evidence |
| --- | --- | --- | --- |
| Known-answer wing, adjoint map | sign ≥ 9/10, r ≥ 0.9 | **FAIL** (r 0.53) | 42705451545 |
| Known-answer wing, measured map | same | **PASS** (r 0.977, signs 95 %) | 42705451545 |
| Measured map, wing shapes outside its modes | sign ≥ 80 %, r ≥ 0.8 | **PASS** (r 0.952, signs 90 %) | 42705451545; finer mesh mxnviir 42705489756 |
| Chain rule to race time | within 1 % of Part 2 finite differences | **PASS** (18 tests) | 42668820158 |
| Compass test on cars (medium mesh, method test only) | sign ≥ 80 %, r ≥ 0.8, ≥ 25 qualifying, sign not fitted | running, none judged | p3_car_modes.yml, section 4 |
| Compass on the fine mesh vs its medium twin | per-mode sign agreement, correlation | running; chaining proven | p3_fine_modes.yml, section 4b |
| Loop timings only on fine or resolved | test fails on coarse, medium or unset | written; tests.yml cars=true 43569628984 running | tests/test_loop_mesh.py |
| Step test, 5 fresh cars | ≥ 4 of 5 faster by > 2 × noise | waiting (fine compass) | section 5 |

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

**Status (2026-11-14):** 45 carved cars (skins 3.76 to 3.95 mm) on 2 cores, one car per run,
spread over Part 3's accounts. None is judged yet. Cars 1 and 2 ran on 4 cores before Part 2's
4-core check failed (spread 0.12 ms against a 0.01 ms limit, run 43279305307); cars 6 and 7
repeat them on 2 cores. The lead decided (Q11) that these medium cars are a **method test
only**: they show whether the measured map can pass the marks on a car, but they are not car
results, because the medium mesh may bend the directions near the nose, wings and supports.

## 4b. Fine-mesh check (Q11)

`p3_fine_modes.yml`. The same measured map on the fine mesh, for 3 cars that also run on
medium, then compared mode by mode (sign agreement and correlation):

| fine car | medium twin | account | start car |
| --- | --- | --- | --- |
| 3.95 mm | car 6 | Jdiejei | done, 2 linked jobs (43427583689, 43487558208) |
| 3.90 mm | car 7 | Jdiejei | done, 2 linked jobs (43474797135, 43524963070) |
| 3.87 mm | car 37 | mxnviir | done, 2 linked jobs (43512261897, 43548319825) |

- A fine solve is longer than GitHub's 6-hour job. Each timing stops at its time budget, saves
  its case (Part 2's checkpoints), and starts the next job from it. All three start cars
  finished this way, so the chaining works.
- The first 3.90 mm try lost its machine after 2 h 13 min (43427795268, "runner lost
  communication"; likely memory or disk). It was rerun with an 8 GB swapfile, about 20 GB of disk
  freed, and a memory and disk log every 5 minutes; later runs also use Part 2's slimmer disk use
  (66de290). It has not recurred.
- Modes 0 to 11 (±) are being timed on each car, 4 at a time. Result: pending.

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

**Open point:** σ = 0.36 ms is Part 2's medium-mesh noise. Steps and marks on the fine mesh use
Part 2's fine-mesh noise once it is posted; nothing here is re-sized until then.

## 6. Part 5 carving loop plan (Stage E)

`part5-simulation/carve_loop.py` decides; the fine-mesh workflow times.
- **Mesh:** every loop timing is fine; finalists are confirmed on resolved. A timing with no mesh,
  or a loop timing on coarse or medium, stops with an error (`car_modes.mesh()`,
  `solver.evaluate`), and `tests/test_loop_mesh.py` fails if that guard is removed.
- **Chains:** one search chain, as only 4 working accounts are left. Two more only if extra
  compute is added.
- **Each round:** the current car is timed (twice the first time, so its noise is known), plus
  one candidate per step size (0.25, 0.5, 1 and 2 × the chain's trust) along the compass.
- **Keep rule:** the best candidate is re-timed on fresh runs (2, then 4, up to 256 while it
  looks better but is not yet clear). It is kept only if its fresh mean beats the current car by
  z·σ, with z Bonferroni-corrected over the candidates and σ pooled from the chain's own repeat
  pairs. Choosing and keeping use different runs, so the luckiest candidate is not rewarded.
- **Direction:** along the compass, bent by the chain's own kept steps (L-BFGS). Trust doubles
  after a keep at the largest size and halves after none. The chain stops below 1/64 trust,
  after 25 rounds (40 while it is still keeping), or when the compass looks wrong (90 % of 12 or
  more candidates slower).
- **Timing a candidate:** a step is the start car plus a mix of compass modes (`s<name>` items
  in `p3_fine_modes.yml`), timed on the fine mesh and carried across 6-hour jobs.
  End-to-end proof: run 43569631533 (mxnviir), one step on the 3.87 mm fine car. Result: pending.
- **Starts when:** this proof and tests.yml cars=true pass, Part 2's fine gates pass, and Part 4
  is tagged. Part 1 is tagged (p1-stage-a-1, dd7427a, whole-car test 43453873060 green). Only
  the final run needs the user's go.

**Start cars (lead decision 2026-11-14: 3 chains).**
- **Chain 1:** Part 1's plain start car (`cutter.start_block`, run_car's default layout), a
  smooth baseline. Its fine compass map is the one being built in section 4b.
- **Chains 2 and 3:** two legal bodies from Part 1's 2,000-body test on p1-stage-a-1, chosen to
  be far apart in shape (front width, nose position, halo distance) and not lumpy: bodies with
  few settings moved, or small moves, are preferred, because a random stress body would spend
  steps undoing its own lumps. Chosen from batch 1 (run 43561978552, seeds 50000-50059, 59 legal):
  - **Chain 2: seed 50047** (legal, 59.4 g). The widest smooth body: W 126.8 mm (start 120.3).
    Only one other setting moved (support strip width 7.5 mm). One carve step, bias −0.92 mm.
  - **Chain 3: seed 50027** (legal, 50.3 g). A different direction: the front moved back
    (x_front 51.7 mm, start 46.0) with a longer, blunter nose (nose length 18.2 mm, nose.p 2.54).
    No layout width or halo change. Two carve steps, bias −1.29 mm.
  - Why these: among the 60 bodies, these have the fewest settings moved and the fewest carve
    steps (1 or 2) while each changes a different part of the shape (width vs nose and front),
    so the three chains start apart. Seed 50032 (one carve step, halo moved back to 64.8 mm) was
    the runner-up; it was passed over because it also moves five wing and support settings.
- **Held (reviewer, 2026-11-14):** Part 4 found car 50002/0 illegal through p4_assembly but
  legal through p1_carve_stress on the same code. The loop builds and judges every car through
  one path, the referee's. Seeds 50047 and 50027 are re-judged through exactly that path before
  their compass maps start, and nothing starts until Part 4 says whether the two paths agree.
  Part 4 answered: the two paths differ (stress_cars.carve_field vs cutter.cut give different
  bodies for one seed). 50047 and 50027 were judged legal through p4_assembly, so their base
  cars are built through exactly that path, and every loop car through the one canonical path
  Part 1 names. Still held until Part 1 names it.
- Each chain gets its own fine compass map before its first step. Slots are shared round-robin
  between chains (`carve_loop.to_start`, `tests/test_carve_chains.py`).
