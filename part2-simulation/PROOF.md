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
| reshaped mesh + warm start, 3000 it (ref 3.945) | 0.71 (0.52–1.12) | 0.34 | shawshanker18 42855557668, stats 42915302504 |
| reshaped mesh only, 1000 it (ref 3.945) | 0.57 (0.41–0.89) | 0.54 | shawshanker18 42896269550, stats 42915322488 |

- **3000 iterations do shrink the averaging part**, from 0.62 to 0.34 ms. That is about
  1/√3, as expected for three times more averaged steps.
- **Both 2026-11-10 ladders show the same drag step** between skins 3.966 and 3.972 mm:
  about 3.7 mN lower, worth about 2 ms. Per part at 3.966 → 3.972 (reshaped only), body
  −2.2 mN and rear wheels −1.5 mN; every other part changes by less than 0.15 mN. A
  straight line fitted through a step leaves most of the residual SD.
- Inside the 12 cars below the step (3.900–3.966), the SD about their mean is about
  0.26 ms reshaped only and 0.33 ms reshaped plus warm start. This is for information
  only, not a pass: the test is the full ladder.
- **Is the step the shape or the mesh? It's the mesh, through a two-way flow.** The same
  ladder reshaped from 3.978 instead (shawshanker18 42915580709, stats 42937310306)
  gives **5.52 ms (4.04–8.70)**, with an averaging part of 0.41 ms. Drag jumps between
  levels about 0.413, 0.428, 0.442 and 0.454 N, and the step at 3.97 mm is gone.
- Same car (3.978), two references: 0.447 N reshaped from 3.945, 0.413 N on its own
  mesh. The difference is all in body drag (0.062 → 0.042 N) and rear wheels (0.116 →
  0.099 N); every other part is within 0.5 mN. That is the same body-and-rear-wheel
  switch the fresh meshes showed.
- So the flow behind the body and rear wheel has more than one steady solution, and
  the mesh picks which one. Reshaping keeps the mesh the same but doesn't stop the
  switch. The 3.945 reference happens to sit well inside one solution, so its ladders
  were quiet; the 3.978 reference sits near the switch.
- Reshape plus warm start from 3.978 (shawshanker18 42937465031, stats 43029712345):
  **4.95 ms**, with the same levels. Starting from one flow does not hold the cars on
  one solution on that older code.
- **On current main the levels are gone for reference 3.945.** Run mw7 (shawshanker18
  42899718105, both, 3000 it, stats 43029734107) gives **0.362 ms (0.265–0.571)**.
  The averaging part is only 0.059 ms. All 16 cars sit at 0.408–0.411 N with body drag
  about 0.034 N, on a different body from the older code.
- **Part of that 0.36 ms is real shape change.** Part 1's body is built on a grid, so
  the skin ladder isn't smooth. Six of the 16 cars (3.930, 3.936, 3.972–3.990) carry
  about 0.035 g less body and about 500 fewer removed cells. Fitting time against skin
  plus that family gives a family effect of −0.62 ms and a residual of 0.25 ms (13
  dof). That figure is fitted after looking at the data, so it is evidence, not a pass.
- Next, a clean test: one car stretched smoothly across its width in 16 steps of about
  0.01 mm (`body_scale_y`, `p2_noise_morph` input `scales`). Also mw10 (reference
  3.978 on main, run 43017128788), to check whether the levels are gone for that
  reference too.

- Fresh meshes put near-identical cars on different drag levels (up to 12 % apart:
  body and rear-wheel drag switch together). A time-accurate run (pimpleFoam, 0.12 s,
  about 11 flow-throughs, shawshanker18 42760508026) kept each car on its own level.
- With one reshaped mesh and a warm start, all 16 cars sit on one branch and drag
  falls smoothly with skin. What remains is mostly each car's averaging error. A
  3000-iteration run of that set-up is next.
- The skins 4.00–4.05 mm of the first runs also carried a Part 1 body step (fixed in
  Part 1 55696e3), so the later ladders stop at 3.99 mm.

| reshaped + warm, 3000 it, ref 3.960 (main code) | 0.42 (0.31–0.66) | 0.14 | mxnviir/stem-car-compute 43066031633 |
| reshaped + warm, 3000 it, ref 3.990 (main code) | 0.58 (0.43–0.92) | 0.21 | blackwingftc-lang/stem-car-compute 43066095540 |

| reshaped + warm, 3000 it, ref 3.978 (main code) | 0.86 (0.63–1.36) | 0.17 | shawshanker18/stem-racing-car 43066046473 |
| **smooth width ladder** (one car, body width x0.9968–1.0028, ~0.01 mm steps), reshaped + warm, 3000 it, ref 3.945 | **0.201 (0.147–0.316)** | 0.14 | blackwingftc-lang/stem-car-compute 43066000504 |

- **Confirmed on fresh machines: 0.119 ms (95 % 0.087–0.187)**, mxnviir/stem-car-compute 43142206299 (same set-up, 4 cores).
- **Smooth-change test meets the 0.3 ms mark: 0.20 ms** (upper 95 % bound 0.32). With a shape that truly changes smoothly, the stopwatch noise is 0.20 ms; the larger figures on skin ladders include real body-grid shape steps. Confirmation run ms5 (same set-up, fresh machines) and a no-warm-start variant ms4 are running.

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

- Reshaped + warm start, 1000 it, same car (3.945) on 6 machines (blackwingftc-lang/stem-car-compute 43068512344): T 1.55569–1.55599 s, **spread 0.30 ms** (FAIL vs 0.1 ms; was 0.94 ms on fresh meshes). Each run's averaging error is 0.26 ms, so the spread is still that. 3000 it repeat (rp3) running.

- Same at 3000 it (blackwingftc-lang/stem-car-compute 43066007386): T 1.55719–1.55748 s, **spread 0.29 ms** (FAIL). Averaging error halved (0.13 ms) but the spread did not: the machines differ by more than the averaging. Drag also still creeps between 1000 and 3000 it (0.413 → 0.416 N), so each run is still settling; next check whether the spread comes from parallel arithmetic order.

- **Cause found: running each car on 4 cores.** Same set-up on ONE core per machine (blackwingftc-lang/stem-car-compute 43118251223, 1000 it): all six machines give T = 1.55770 s and D20 = 0.41692 N to every printed digit, **spread 0.000 ms (PASS vs 0.1 ms)**. The 0.29–0.30 ms spread on 4 cores comes from the order the cores add up their parts, which changes run to run. Cost: about 70–80 min per car on one core vs 35–45 on four. Testing 4 cores with a fixed adding order next (rp9, shawshanker18/stem-racing-car 43148978484).
- Two cores (mxnviir/stem-car-compute 43142210991, 1000 it): T 1.55771–1.55772 s, **spread 0.01 ms (PASS)**, same answer as one core.
- Four cores with a fixed MPI adding order (shawshanker18/stem-racing-car 43148978484): spread 0.17 ms, still FAIL; the order of the parallel linear-solver sums is not fixed by that setting. **Decision: the stopwatch runs on 2 cores** (`stopwatch.py` default `--np 2`), which repeats to 0.01 ms. The smooth noise test is being redone at 2 cores (ms7) and 1 core (ms8).
- **Caution, not yet a pass:** one core on main (shawshanker18/stem-racing-car 43142201751): five machines at 1.55641–1.55648 s, one at 1.55773 s (the rp5 value), **spread 1.3 ms**. So one core is not machine-independent either; the likely cause is different processor models on GitHub machines. The 2-core 0.01 ms result may have drawn one processor model. Run rp10 (10 machines, 2 cores, processor model logged per car, 43169235738) tests this.
- **Not the processor.** 2 cores, 10 machines, five processor models (AMD EPYC 7763, 9V45, 9V74; Intel Xeon 8370C, 8573C), one shared reference: T 1.55771–1.55772 s, **spread 0.01 ms** (mxnviir/stem-car-compute 43171163246).
- **The reference case has two flow states ~1.3 ms apart.** Every repeat set agrees within itself, but whole sets land on ~1.5577 s (rp5, rp8, rp12) or ~1.5564 s (rp7, rp9, rp13 same-maths), and one rp7 car flipped. So repeating the whole pipeline, reference included, can differ by 1.3 ms. Proposed fix (QUESTIONS.md Q3): one frozen, stored reference case for all timings.
- Skin ladders ref 3.930 (mxnviir 43066023520): 1.31 ms; ref 3.912 (mxnviir 43066015091): 0.67 ms.

## Still to prove

- Ahmed body benchmarks: 35° reported (RANS limit); 25° and the cube are the pass cases (decision 2026-11-09).
- Noise ≤ 0.3 ms: being fixed (reshaped meshes plus warm starts).
- Repeatability, warm start, chained long runs, race model on measured inputs, model vs track.
