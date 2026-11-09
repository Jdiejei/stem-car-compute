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
