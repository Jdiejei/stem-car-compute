# Part 4 proof: runs and results

Every result here ran on GitHub Actions (public compute repo `stem-racing-car` or a teammate's fork). Newest first within each section. "Done" needs the clean rerun from main listed at the end.

## Rule map (Step 1)

- `part5-simulation/RULES_MAP.md`: 113 rows covering T1-T10 and appendices i-ix, every one with a check or a stated reason. 68 checked by the referee; 2 small gaps left (T5.6 "visible all round", T4.4.1/T4.5 halo file unchanged).

## Edge tests (Step 2)

`part5-simulation/tests/test_rules_edges.py`: for each numeric rule the referee measures, a box car just inside (limit - 0.2 mm or 0.2 g) passes and one just outside fails, on that rule id alone (or a stated set).

| Date | Run | Result |
| --- | --- | --- |
| 2026-11-09 | shawshanker18/stem-racing-car 42640038773 | first batch (21 rules): 52 passed |
| 2026-11-09 | shawshanker18/stem-racing-car 42641238222 | wings measured: 69 passed, 1 failed (rear height deviation test: a sloping wing's bounding box was taken for the body splitting its span; fixed) |
| 2026-11-09 | shawshanker18/stem-racing-car 42642150121 | wheels: 79 passed |
| 2026-11-09 | shawshanker18/stem-racing-car 42642891898 | chamber: 87 passed |

## Real reference cars through the referee

`p4_cars.yml`: the start car, round 2 car and a parts variant, built whole, every check listed.

| Date | Run | Result |
| --- | --- | --- |
| 2026-11-09 | shawshanker18/stem-racing-car 42642155363 | 141 checks, 0 failed on all three. The measured front-wing span margin is 1.4-1.9 mm (two segments split by the nose), not the +27 mm the Part 4 gate reported. |
| 2026-11-09 | shawshanker18/stem-racing-car 42647671558 | 152 checks; T5.1 widest 19.87 mm and T5.5 99.9 % failed: false, see the chamber lab |
| 2026-11-09 | blackwinglinkedin-crypto 42649568759 (lab) | chamber sections along the bore: area of an 18.16 mm circle, plug fits 18.13 mm, but a notch 0.85 mm deep at y = 0 top and bottom along the bore (the milled file's two halves meet there). The real bore comes drilled in the block. T5.1 now judged with plug gauges; the notch is reported in the note. |
| 2026-11-09 | anasssssssss1 42655272148 | 152 checks, 0 failed (round 2 and parts cars; the start car's download timed out) |

## Independence (Step 3)

`part5-simulation/rules_constants.py` (typed from the regulations with pages) and `tests/test_independence.py` (no Part 1 imports; values agree with Part 1's).

## Carved-car assembly (Step 4), lofted regression

To come.

## Findings for other parts

- The milled body file has a notch about 0.85 mm deep along the top and bottom of the cartridge bore, where its mirrored halves meet (y = 0). In the file only; the block's bore is drilled. Worth fixing where the half body or `joints._full` is made.
- The team's wheels measure 28.26 mm across (T7.5 minimum 28.0) and 13.25 / 17.25 mm wide at full diameter (T7.4 minimums 13.0 / 17.0): legal with 0.25 mm to spare.

## Steps 2 and 3 passed (2026-11-09)

- blackwingstem-wq/stem-racing-car 42672121059 (public 8eabb02): part5 105 passed (all edge tests, independence, chamber-clear, halo, T5.6), part4 17 passed. Earlier attempts died at start-up in GitHub's Actions outage ("Internal server error"), not in the tests.
- Reference cars on Part 1 cb08cb5 (blackwingstem-wq 42675470957): parts car 162/162; start and round2 fail only block_body_inside_official_block by 5.2-5.5 mm3, a strip at the block slot's top corners (y ±2.7-2.9, z 7.7-7.9, x 53-159); being traced with Part 1.

## Step 6: wall thickness of every made file (lab anasssssssss1 42672288239)

Ray from each of 4,000 surface points straight into the part (start and round2 cars; mm):
- machined_body (foam, CNC): 1st percentile 3.8-3.9, median 21. The thinnest 0.00 readings are rays grazing edges (0.1-0.2 % of points under 1 mm).
- printed_hubcaps: 0.70 almost everywhere (the disc as designed).
- printed_support_front/rear: median 0.70-0.88; 5th percentile 0.55-0.65; 50-59 % under 0.8.
- printed_front_assembly: median 2.0; 27 % under 0.8 (wing and flap trailing edges, nose shell edge).
- printed_rwing: median 1.96; 13 % under 0.8 (the NACA trailing edge, sharp by design).
- team wheels: 0.40 (the team's own design, which they already print).
Pass mark: the team confirms these can be made. Needs the printer's minimum wall (question to the team). If it is above 0.7 mm, the supports and hubcaps need a thicker minimum, and the wing trailing edges a blunt minimum.

## Carved canary 1 (not the official run): blackwinglinkedin-crypto 42655282327, summary 42697932704

1,008 cars (42 seeds from 43800) on Part 1's untagged main as of 2026-11-09 ~16:29 UTC: 382 legal, 623 illegal, **3 crashes** ("body_half.stl is not watertight", Part 1's half body; sent to Part 1).
Rejects by rule: T4.4.2 halo seen from front 480 (6-13 mm3 of body ahead of the halo above its base + 4 mm, the p23 front-view outline; checked against the drawing; sent to Part 1 as a cutter zone); T4.6 decal 69; P4.machining_rear_slot_corner_radius 59 (a bare beam support whose section's tightest corner is under the 3.125 mm ball radius: random support settings, for Step 7); T4.2 cargo 25 (5.3 mm3, since fixed by Part 1); T8.6.1 front span 18 (segments 24.65 mm: wing half-span vs nose width, Step 7); T7.9.4 17; mesh_slivers_printed 9 and manufacture_files_are_solids 3 (Part 4 file quality, to trace); T4.4.2 side 4; T4.7 2.

## One print minimum (component_contract.MIN_WALL_MM; P4_MIN_WALL_MM overrides)

Reference cars at 0.7, 1.0 and 1.2 mm (blackwingstem-wq 42682204999, 42682212616, 42682220443): every part builds and every rule passes at all three. The only failure is Part 1's block-slot strip (5-7 mm3), which is Part 1's to fix. Wing thickness grows with the blunt trailing edge: 2.52 / 2.62 / 2.70 mm (limit 6.0). test_min_wall: 2 passed (42682227523; the run reads "failure" only because the filter matched nothing in part5).
Walls at 1.0 mm (lab 42682234702): rear wing ≥ 1.03 everywhere; hubcaps 1.00 (1.5 % of rays under 1, at edges); supports median 1.00-1.05, 1st percentile 0.41-0.51 (edges and grazing rays); front assembly median 2.06, 8 % under 0.8. When the team gives its printer's figure, it is one value.
- The 3 canary cars with "machined_body not one closed solid" (43825/16, 43836/13, 43806/20) did not repeat when rebuilt on the same commit with `stress_cars.py --only` (lab blackwinglinkedin-crypto 42698359819): every file was one closed solid. But the rebuilt cars' masses differ from the batch's (43.6 vs passing T3.6), so `--only` isn't a faithful rebuild and the cause is still open. The check's note now records the file, closed state, pieces and remesh state, so the official run captures the cause if it recurs.

## Lofted canaries on Part 1 9123b41 (not official)

blackwingstem-wq 42696426214 (575 cars, seeds 43700) and blackwinglinkedin-crypto 42696432993 (300 cars, seeds 43723): **every car crashed** with "ValueError: Not all meshes are volumes!" inside trimesh's boolean (boolean_manifold), about 100 s into each car. Same error the halo-slot lab showed on Part 1's body_half at that time. Part 1 has since pushed reload-safe zone cuts (a90e2af, 0bb3701, be43b12). Check run on 78badef: blackwinglinkedin-crypto 42713843308 (20 lofted cars, seeds 43900). These crashes are not counted toward the regression bar; that bar is judged on Part 1's frozen tag.

## Lofted check on Part 1 78badef, and rebuild on b863351 (not official)

- blackwinglinkedin-crypto 42713843308 (20 lofted cars, seeds 43900, 78badef): 3 legal, 16 illegal, 1 crash (PyMeshLab midpoint subdivision). The "not all meshes are volumes" crash is gone. New rejects: T8.2 nose overhang 13 cars (74.6 mm ahead of Ref A in 10 of them, against 40), mesh_slivers_printed 11 (14-31 %), T4.2 4.
- The same seeds rebuilt on b863351 (anasssssssss1 42723665776; only Part 1's be43b12/0bb3701 body changes and two legality notes differ; the car settings are identical): 9 legal, 1 illegal (car 43900/0, T4.2 cargo, Part 1's). Every T8.2 and sliver reject cleared, and the masses moved by 0.02-0.06 g. So both came from the 78badef body, not from Part 4's parts (the blunt trailing edge was suspected and is ruled out). The T8.2 and sliver notes now name the part and file.
- Only 2 of the 4 rebuild machines finished: at about 00:15 UTC GitHub stopped every running job on all four accounts with "repository invocation blocked" (carved canaries 42723347513 and 42723353243, lofted 42723358524, reference cars 42723364126/69288/74253). Not retried, per the lead's rule. Unit tests on b863351 passed before the block (anasssssssss1 42723670829).

## Reference cars on Part 1 19e1a36 (shawshanker18 42754131299, print minimum 0.7 mm)

start, round2 and parts: **162 checks, 0 failed** on each. The block-slot corner strip (block_body_inside_official_block, 5-7 mm3) is gone with Part 1's fix. Sent to Part 1 for its frozen tag.

## Reference cars on Part 1 08ff3dd (shawshanker18 42763411580): the strip is back

start, round2 and parts each fail only block_body_inside_official_block: 34.7, 32.3 and 28.2 mm3, at the block slot's top corners (x 53-159, y ±2.4-2.9, z 7.3-7.9). The only Part 1 change since the 162/162 pass on 19e1a36 is f95173b ("projection lands 1 um past the zone face"). Correction sent to Part 1: don't freeze on f95173b. The same strip appears on lofted trial cars on ef1911e (15-36 mm3, Codespace on blackwinglinkedin-crypto).

## Reference cars on Part 1 fef4130 (shawshanker18 42768594296)

start, round2 and parts: **162 checks, 0 failed** each, with no box-cut fallback in the logs. Cause of the f95173b strip (Part 1): its surface moved exactly onto the zone-box faces, the box boolean failed and the cut was skipped; fef4130 keeps the surface clear and its zone test fails if the cut ever falls back. Sent to Part 1.

## Trial cars on Part 1 fef4130 / 26f095c / 5fef8eb (Codespaces, not official)

- fef4130 (public bb78e33), lofted seeds 43700-43701 (Codespace on blackwinglinkedin-crypto, 4 cores): 20 cars, 13 legal, 0 crashes. Rejects: T4.2 cargo 3, T8.6.1 front span 2 ("two segments of 22.5-24.8 mm", half-span 34.8-36.5 mm: Step 7 range), mesh_slivers_body 2 (4.75 % and 5.49 %).
- fef4130, carved seeds 43100-43101 (Codespace on blackwingstem-wq): 15 cars before the stop, all illegal, 0 crashes; each failed T4.2 cargo by 6-20 mm3 round the ballast slot's top edge (x along the slot, y up to ±7.6, z 20-23.9).
- Cause, found by rebuilding car 43100/0 with its files kept: the gap is the same before and after Part 4's remesh (6.36 vs 6.68 mm3), and Part 1's body_half.stl already has the slot rim rounded out past the exact slot (y = 6.35): top surface z 23.71 at y = 6.8 and 23.88 at y = 7.2, against the cargo top at 23.9. Part 4's exact box and capsule cut can't put that back. Sent to Part 1.
- 26f095c (public 87325db), carved seeds 43100-43101: 20 cars, 3 legal, 16 T4.2 (5.6-19.3 mm3), 0 crashes. Not cleared.
- 5fef8eb (Part 1 draws the slot 2 cells small): car 43100/0 rebuilt is legal; 0.34 mm3 of the cargo shape is still outside the body (under the referee's round-off), rim at y = 6.5 now z 23.87-24.0.
- Part 1 reported that Part 4's remesh turned its 0.88 % thin-triangle body into 12.4 %. remesh_file now keeps the original file when it is closed, has no edge over 8 mm and has no more thin triangles (13e4445; p4_tests 42794294512: part4 20 passed, part5 105 passed).
- 5fef8eb full recheck (public 5fef8eb, carved seeds 43100-43101, Codespace on blackwingstem-wq): 20 cars, 15 legal, 0 crashes. Rejects: T4.2 cargo 2 (43100/8 10.7 mm3, 43101/2 5.8 mm3), T4.6 decal 2, P4.machining_rear_slot_corner_radius 1, T8.6.1 front span 1. The slot-rim gap is gone (0.16-0.26 mm3 left there per car).
- The two T4.2 cars, rebuilt with files kept: the missing cargo is a thin skin on both slanted side faces of the cargo shape (x 81-123.5, |y| 10.2-27.5, z 14-23.9), 2.5-5.1 mm3 per side over about 400 mm2, so the carved side wall sits on average 6-13 um inside the cargo. It is there before the remesh too (5.25 / 10.32 mm3), so it comes from the carved body: the carve takes the side walls right down to the cargo outline with grid round-off, the same kind of miss as the slot rim and the pocket floor. Both cars carve hard (carve_bias -2.35 mm). A real reject; the referee is not changed. Sent to Part 1.
- Lofted cars that failed T4.2 on fef4130, rebuilt on 5fef8eb: all three now pass every check stress_cars counts (43700/9, 43701/0, 43701/2). Correction: an earlier note here said 43701/0 and /2 failed T3.6 mass; that was a misread. The line read was run_car's own list, and stress cars are built at one fixed skin and not sized, so stress_cars ignores T3.6 (IGNORED in stress_cars.py). On fef4130 the same two cars also showed T3.6 in run_car's list (45.74 g and 41.65 g) beside T4.2, and so do most legal lofted cars there.
- Part 1 has since moved the pocket floor and slot draw again (eae7198) and will ask for the final recheck on its green commit; this run is a trial only.

## Stage C: carved cars, one car per job (2026-11-13 / 14)

Every car below was carved, assembled and judged on GitHub (`p4_assembly.yml`, one car per job, the referee `part5-simulation/legality.py`). "Legal" means every check passed.

| Commit | Runs | Cars | Legal | Crashes | Rejects |
| --- | --- | --- | --- | --- | --- |
| 54906c4 | rejudge | 40 | 36 | 0 | (before the rear-slot fix) |
| 1a33a87 | mxnviir + main | 150 | 113 | 0 | (before the rear-slot fix) |
| aa08f57 | main | 120 | 98 | 0 | logo 14, number 12, halo pocket 1 (44294), manufacture_files_are_solids 1 (44310); rear slot 0 |
| 30d92d0 | stem-racing-compute 43398668448, 43398742837; stem-racing-car 43394214089 | 180 | 143 | 0 | logo/number 33, halo pocket 3 (44408, 44411, 44473), T7.13 rear claw 1 (44430) |
| 4d594f6 | stem-racing-compute 43561652849, 43561682124, 43561711541 | 180 | queued | | |

Whole-car tests (`tests.yml`, cars=true) on 30d92d0: stem-racing-compute 43398821646, **every job green**. The resolved CFD car ran in two links (Part 2's checkpoint chaining): link 2 restored link 1's saved case, finished it, and ran Solver logs, Rule checks and "Fail if any rule check failed", all green; link 3 only runs when link 2 itself chains again.

### Reject causes and fixes

- **Rear support slot corner** (P4.machining_rear_slot_corner_radius): a bare beam's section had a corner tighter than the 3.125 mm ball (car 44027/0: 17.214 x 3.96 mm ellipse, corner 0.46 mm). The beam is now grown to the lightest section the ball can follow, a rounded rectangle with corners of the ball's radius (aa08f57; `tests/test_slot_corner.py`). 44004, 44079, 44113 and 44115 then passed; 0 slot rejects in 300 cars since.
- **Logo (T4.6) and number (T4.7) room**: the carved body left too little flat surface. Part 1's carving; Part 1 added the keep-out zones (6d86afd, 60 cars with 0 marking rejects on its check). The 33 on 30d92d0 ran before that fix; the fresh 180 on 4d594f6 checks it.
- **Halo pocket** (T4.4.4, foam inside the real halo+helmet mesh): 44408, 44411 and 44473 failed on 30d92d0 and are all legal on 5e7fe6b (with 6d86afd). Part 4's halo front is exactly Part 1's pocket front (`hardware_geometry.build_halo` places it at `compute_halo_pocket_box_m`'s x_min). The check now writes where foam meets the halo (5e7fe6b) for any future case.
- **T7.13 rear claw** (44130/0, 44430/0): **open.** The same 12 claw points are blocked in both cars (x 163.94-168.66, y 14.80-16.20, z 27.22-27.43, the top of the rear wheel's claw ring, ring radius about 13.6 mm), by the referee's `supports` mesh, which is `supports.stl` (Part 4's beam support), not the body; the body is clear in the same check, and Part 1's wheel column keeps the carved body out of that band. A trim of the plate inside the claw band (59c0d95, sized as a plate-plus-web neck in 4b183ff, new gates `T7.13_<tag>_support_clear_of_claw` and `load_<tag>_claw_neck_stress`) did not clear it: the same points stay blocked, so the blocking piece is not yet identified. The referee now writes the blocking piece's bounds (8bab2ea); trace run stem-racing-compute 43561847205. No fix until the trace names the piece.
- **manufacture_files_are_solids** (44310): open, to trace.
- **T4.4.2 halo from the front + block_body_inside_official_block** (44200, 44226) and **T7.13** (44130 on aa08f57): from earlier batches; to rejudge on the current commit.

The referee was not loosened for any of these. Every change to it only added detail to a failing check's note: ba4331a (T7.13 names the blocking part and points), 8bab2ea (the piece's bounds), 5e7fe6b (T4.4.4 location). `checks/stress_cars.py` used to cut every note to 80 characters, which hid the coordinates; it now keeps 2,000 (0eebad5).

## Part setting ranges (`part_ranges.py`, 4d594f6; test fix 51a6c64)

The legal range of every part setting Part 5's loop may tune, found **on the car** by bisection from the default outwards on the part's own gates (the same gates the assembly and the referee apply). Several limits (wing height, clear air, overhang) depend on the body and layout, so a fixed table would be wrong on other cars. `legal_range(part, setting, car)` returns the bounds, and for each bound the gate that ends it; `RULES` names the regulation behind each setting.

| Part | Settings | Rules they run into |
| --- | --- | --- |
| front wing | chord, t_frac, aoa, half span, chord-line height, flap chord, flap aoa, gap to wheel | T8.6.1-3, T8.5.2, T8.7, T7.9.1, T8.2 |
| rear wing | chord, t_frac, aoa, half span, LE behind Ref B | T9.4.1-3, T9.5.1-3, T9.6 |
| nose | length, k, p | T8.2, T8.5.1 |
| supports | disc radius, plate chord | T7.12.1, rim fit, T7.13, T3.7 |

`tests/test_part_ranges.py`: every bound is checked 0.03 mm (or 0.03 of the setting's unit) just inside (all of the part's gates pass) and just outside (the gate named for that bound fails). p4_tests stem-racing-compute 43567587748 on 51a6c64: passed. (43561445886 on 4d594f6: 45 passed, 3 failed. The nose's default broke T8.5.1 on the plain-box test car because the cone's root copies the body's section at Ref A + 1, which on the box is 40 mm tall and 50 mm wide. The test car got a low nose block, as a real body has. On real bodies the default nose cannot break T8.5.1: Part 1's t851_cap keeps everything ahead of Ref A + 1 within z ≤ 24.45 and |y| ≤ 14.45, and its envelope keeps the body's bottom at ≥ 1.55 mm, so the cone tops out at ≤ 24.5. Of the 180 cars on 30d92d0, 30 kept the default nose and none failed a T8 rule.)

## Part weights (4d594f6)

Each made part's mass is its file's volume times its material's density. Every row of `joints` `manufactured` and of `mass_report.json` now carries `cm3`, `g_cm3`, `density_source` and `weighed`:

| Material | Density | Source | Weighed |
| --- | --- | --- | --- |
| Foam block (machined body) | 0.163 g/cm3 | team spec (`geometry_contract.DENSITY_BODY_KGM3` = 163) | no |
| SLS PA12 (supports, hubcaps, nose / front assembly, wheels) | 1.01 g/cm3 | material datasheet; team material spec 2026-09-27 | no |
| PLA (wings, tether guides) | 1.24 g/cm3 | material datasheet (`component_contract.DENSITY_G_CM3`), solid print | no |

**Flag for the team:** no printed part has been weighed. These are datasheet densities, which assume a solid part; a real print's weight depends on the printer's infill and powder. Replace each with the team's real print weight when the parts are made.
