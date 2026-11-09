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
