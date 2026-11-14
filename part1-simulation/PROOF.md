# Part 1 (the cutter): what is proved

Every claim below names its pass mark and the GitHub run that showed it. Nothing was run on a
PC. Runs are on `shawshanker18/stem-racing-car` unless an account is named
(`J` = Jdiejei, `M` = mxnviir, `A` = anasssssssss1, `B` = blackwingftc-lang, `C` =
`shawshanker18/stem-racing-compute`). Pass marks were never relaxed. Every gap is explained,
and anything still open says so.

Frozen tag: **`p1-stage-a-1` = `dd7427a`** (2026-11-14).

## The gates, in order

| # | What | Pass mark | Result | Run(s) |
|---|------|-----------|--------|--------|
| 1 | Grid study: the same body cut at 1 mm and 0.5 mm | every body's mass within 0.5 %, rule margins of the same sign | 20 of 20 within 0.5 %. 10 more seeds (41381-41390) also within 0.5 % | 43026438679; 43118866738 (J) |
| 2 | Weight sizing, 200 bodies | every reachable body within ±0.05 g, none under 48.0 g, at most 16 builds | reported green on 2026-11-13 (code before the tag); the per-body table is not reproduced here, so the binding result is the rerun on the tag (2') | 43142211899 (B), 43142217956 (J) |
| 3 | Remap: a body moved to a new layout still passes the mesh check | mesh passes with no slivers | passes as is, no code change needed | 43066533385 (M) |
| 4a | Carving, 200 random bodies | 0 crashes; every reject traced to its cause | 0 crashes. 197 legal on 6bcf377, 2 illegal (traced, now fixed, see below), 1 over the 900 s time limit (41608/1: legal when rebuilt on the tag, C 43570179438) | 43208030293 (J), 43208036651 (A), 43210156312 |
| 4b | Repeatability: same input and same commit give the same verdict | identical verdicts and reject volumes on two runs | identical: 41594/8 and 41518/4 fail twice on 6bcf377 with the same mm³, and are legal twice on dd7427a | C 43475044495, 43475108989 (6bcf377); C 43475347878, 43475404245 (dd7427a) |
| 4c | Every car of the two reject seeds on the final code | all legal | 14 of 14 legal (41594/0-8, 41518/0-4) | C 43454007507 |
| 4d | Markings: the number and logo room kept by the carver | 0 number or logo rejects | 60 cars: 54 legal, 0 number/logo rejects, 0 body-piece faults. The 6 others belong to Part 4 (5 rear slot corner, fixed by Part 4 in aa08f57; 1 claw, which is Part 4's support part) | 43387299037 |
| 5 | Whole-car test on the exact tag commit (`tests.yml cars=true`) | every job green, including the chained fine and resolved CFD cars | all jobs green on dd7427a | C 43453873060 |
| 6 | 2,000-body test on the tag | 0 crashes, 0 illegal | **running**, one car per job. Batch 1: 59 legal, 1 illegal (50002/0, T7.12.1 rear support in cylinder: Part 4's support; the same car is legal in three lab builds of the same code), 0 crashes. Batches 2-3 queued | C 43561978552; C 43586226627, 43586228801 |
| 2' | Weight sizing rerun on the tag | as gate 2 | **running** | C 43561981406 |

## How the last rejects were cleared

Both were found to be deterministic (gate 4b), so they were real faults, not noise. The commit
that cleared each one was found by building the same car on each commit in turn:

- **41594/8** (halo seen from the front 14.0 mm³, body outside the block 33.8 mm³). Illegal on
  2ca326e, legal on **e70ad72**. That commit dropped the T8.5.1 cap boxes from the exact cut:
  they cut at the zone edge rather than 0.05 mm clear of it. Runs C 43512326600 and C 43512319448.
- **41518/4** (halo seen from the top 6.9 mm³). Still illegal on e70ad72 and on 54906c4. Legal on
  **c371b29**, which keeps body room for the T4.6 logo and T4.7 number. Runs C 43561927806 and
  C 43561934242.
  - On c371b29 alone, car 41518/2 failed the halo-front check. The two follow-up commits that
    finished the number deck (17db5ef, a237d78) fixed it: 41518/2 is legal on dd7427a (4c).

## Other faults found and fixed on the way

- Car L1 mesh was not watertight: 194 grid samples sat exactly on the surface after the 0.5 mm
  milling change. The whole-car mesh now retries with the samples nudged off the surface
  (9984b8a). L1 passes: 43308948727 (M).
- `test_cutter`: a body too light for the ballast capsule to make up was accepted. `cutter.finish`
  now refuses it (54906c4).
- The number deck came out as a second body piece when it ended ahead of the carved body
  (44016/0). It now runs back to the halo pocket (a237d78).

## Checked and found not to need a carver change

- Halo pocket T4.4.4 on 44408, 44411 and 44473: legal on current main. The carver's pocket matches
  the halo placement (Part 4).
- T7.13 claw blocked on 44130/0 and 44430/0: the blocker is Part 4's support part, not the body.
  The carver's wheel column already keeps the claw ring clear.
- Nose root (Part 4's nose cone copies the body section at Ref A + 1 mm): the carver's T8.5.1 cap
  keeps that section 24.45 mm high and 14.45 mm half-wide at most. The T3.7 floor (1.5 mm plus a
  0.05 mm margin) limits the cone's lift to 0.05 mm, so it stays under 25 mm.

## Open

- Gates 6 and 2' on the tag are running. This page is updated when they finish.
- `p1-stage-a-2`: an explicit T7.13 claw-ring air zone. It changes no rule result (the wheel
  column already covers the ring), and 44130/0 and 44430/0 are legal with it (C 43562044181).
  Same-body proof, 20 bodies on both (C 43569632670 on stage-a-1, C 43569652478 on stage-a-2):
  the carved field `carved.npy` and `body_half.stl` are identical for 20 of 20. The machined body
  and support files differ only through Part 4's newer support commits (59c0d95, 4b183ff); no
  Part 1 file but `exact_zones.py` changed. Next: claw-branch tests, merge, whole-car test, tag.
