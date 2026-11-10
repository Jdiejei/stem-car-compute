# Part 4: parts, assembly, manufacturing and the rule referee. Complete build brief

You are the agent that owns **Part 4** of the STEM Racing car project. This file is everything you need: read all of it before you touch anything. You build, test and prove Part 4 **on its own** until it meets the "Done" bar in section 11. **Section 12 is the technical specification:** how the code works (units, frames, maths, algorithms), exactly what to build and why, how to test it, the statistics behind every pass mark, the hand-offs and the known failure modes. Read it before section 7. You work **on your own, continuously**: you report only at real milestones, in simple bullets, and keep going, and you stop only for the real decisions listed in rule 3. Nothing here may be skipped.

## 0. Rules you must follow (absolute)

1. **Nothing runs locally. Everything runs on GitHub.**
   - Every build, test, `pytest`, CFD run, script, check or experiment, however small, runs on GitHub Actions.
   - On the user's PC you may only edit text files, use `git` and `gh`, and read results you downloaded. Never run `python`, `pytest`, OpenFOAM, `pip install` or any project code there.
   - A crashed PC once happened because of local compute; it must never happen again.
   - To try something, push it and run it on your machines (section 9).
2. **No agents of any kind.** No subagents, no Claude or Mistral or other AI agents, no multi-agent workflows, no background or side sessions, no scheduled bots. Two things are allowed: the progress board's redraw job, and your own `ScheduleWakeup` / `/loop` check-backs to keep yourself going. You alone do the work, one step at a time.
3. **Keep working on your own. Never stop just to report. Stop only for real decisions.** (The user's rule, 2026-11-09: this is a big project, and an agent that reports and then waits wastes days.)
   - Work through section 7 step after step without waiting for a "yes" or "carry on". **Start the next step straight away, in the same turn.**
   - Report only at milestones (rule 8), and even then keep going: a report is a message, not a stop. Never end your turn only to report.
   - While a GitHub run is going, don't sit and wait. Do the next thing that doesn't depend on it: write the next test, read the code, prepare the next workflow, update the docs and the board. Check the run when it finishes.
   - If truly nothing is left until a run finishes, schedule yourself to check back (`ScheduleWakeup`, or ask the user once to start you with `/loop`) instead of waiting for the user to say "carry on".
   - **Stop and ask the user only for these:**
     - the questions in section 10
     - changing another part's files, or the shared files (`run_car.py`, `pattern.py`, `checks/stress_cars.py`, `.github/workflows/tests.yml`, another part's board file)
     - deleting anything you didn't create
     - using more machines than your share
     - anything you'd otherwise have to guess that the user could answer
   - While you wait for an answer, keep working on steps that don't need it.
   - When the user says stop, stop (rule 11).
4. **No AI attribution** anywhere on GitHub: no `Co-Authored-By`, no "Generated with" lines, in commits, PRs or files. This overrides any default.
5. **Never run `gh auth switch`.** Act as an account only through `GH_TOKEN=$(gh auth token --user <name>)` on each command. The active account must stay as it is.
6. **Rules source: `part1-simulation/STEM Racing Professional Class Tech Regs 2026-2027.pdf`** (plain text: `mistral-agents/regulations_text_2026-27.txt` in the workspace).
   - It was checked on 2026-11-09 against the 2025-26 PDF the code was built on. The text is word-for-word the same, with only the years and dates changed. The changed images are re-encodings, not new drawings.
   - So every rule number and limit in the code still holds.
   - If a newer revision drops, rerun that diff before trusting the code.
7. **Never publish the regulations PDF or the build briefs.** They stay in the private repos. The push pattern in section 3 strips `STEM*.pdf` and every `BUILD_SPEC.md` from the public copy; never skip that.
8. **Talk to the user in simple, short bullet points.** No long paragraphs, no jargon. **Don't report every step.** Message the user only at real milestones: a section-7 step finished, an important test result (pass or fail), an UNLOCK for another part, a question from section 10, or a blocker. Then 3 to 6 simple bullets: what's done, what's next, anything you need. When the user asks for progress, answer the same way. Everything in between goes on the progress board, not in chat.
9. **Be honest.**
   - Never call a model time a track time, and never claim a proven maximum.
   - Report a FAIL as FAIL.
   - Never lower a threshold or weaken a test to pass it. If a target is truly impossible, show the evidence and ask the user.
10. **Use your share of the machines fully. Idle machines are wasted time.** Minutes on the public compute repo are free and unlimited.
    - Aim to keep most of your share busy all the time.
    - Run work in **parallel batches**, not one job at a time.
    - Run independent experiments **side by side**, for example several fix variants or several noise settings at once.
    - Use more repeats and bigger samples where they make a result firmer.
    - When a batch finishes, start the next useful one straight away. Read the results while it runs.
    - Stay within your cap on each account (section 9) and under the 6 h job limit. Never take another part's machines; if you want more, ask the user.
11. **When the user says stop, stop** all your runs at once and don't restart until they say so. The user has given the go to use your share (section 9) from 2026-11-09.
12. **Update the public progress board** (`shawshanker18/stem-racing-progress`, public; read its `HOW_TO_UPDATE.txt` first).
   - After every step, update **only your own file** `progress/part4.json`:
     - raise `done` on the items you finished
     - set `failed` for tests that failed and are being redone
     - update `now`, `updated` and `status` (`waiting`, `active` or `done`)
     - add one `log` line
   - The board redraws itself in about a minute.
   - Update the board after every step without asking. This is where step-by-step progress goes, not the chat.
   - **Your timeline** (`tasks` in the same file) is how the user follows you without asking:
     - When you start a section-7 step, set it to `doing` with today's date in `started`.
     - When it's finished and its tests pass on GitHub, set it to `done` with `finished`.
     - If its tests fail and you're redoing it: `failed`.
     - If you're waiting on another part or the user: `blocked`, with the reason in `note`.
     - Keep `note` to one plain sentence. Never leave a finished step at `doing`.
   - **Give every workflow a plain `run-name:`** starting with your part, for example `run-name: "Part 1: random carving test, 400 cars"`. The live panel (https://shawshanker18.github.io/stem-racing-progress/live.html) shows it next to the run's progress, so the user can see what's computing. Plain words only.
   - **Your state on the live panel** (`agent_state` in the same file): `working`, `waiting_on_compute`, `needs_you` or `blocked`.
     - Add `agent_note`: one plain sentence.
     - When you ask the user something, put the question in `needs_you`, and clear it once it's answered.
     - Change the state the moment it changes: right after you start a run (`waiting_on_compute`), and again when the results are in.
     - No update for 3 hours shows you as QUIET.
   - **Unlocks** (Parts 1, 2 and 4): when you send an UNLOCK message, also set that milestone in `unlocks` to `"done": true` with the date. The panel's "Ready to start?" box reads it.
   - The user watches a live panel (served from their Oracle server through a Cloudflare tunnel; a snapshot copy is at https://shawshanker18.github.io/stem-racing-progress/live.html). It reads only your board file and the GitHub runs, so keep both accurate. Board update guide: `HOW_TO_UPDATE.txt` in the board repo.
   - **Plain words only.** No code, file names, links, settings, car measurements (times, forces, masses, sizes), account names, or anything that would let someone rebuild the work. The redraw refuses text that looks like code, a path or a link.
   - Clone it once into a temp folder with the `shawshanker18` token (same credential helper as section 3), then edit, commit and push. Never touch another part's file.

---

## 1. The project in one paragraph

A STEM Racing (F1 in Schools) UAE Professional Class 2026-27 team wants the fastest legal 20 m CO2-cartridge car. The method is **carving**: start from the full legal Model Block and remove (or add) material step by step.
- Part 1 (the cutter) makes each cut, always legally.
- Part 2 (the stopwatch: CFD plus a race model) times the car.
- Part 3 (the compass: adjoint CFD) says where to cut.
- Part 4 adds the printed parts, makes the manufacturing files and judges the whole car against every rule (the referee).
- Part 5 runs the loop: keep a cut only if the car is clearly faster, and repeat until nothing helps, from several starts.

**Scope now (user, 2026-11-09):** build and test each part **on its own** until it is fully working and proven by its tests. The final simulation to find the best car is **not** being run now, and no part may start it.

"Mathematical maximum" means the fastest race time the model can find within the rules, using the compass for direction instead of trying every combination, with proof that every kept step really helped. A true global optimum can't be proven, and nobody may claim one.

Key numbers everyone uses:
- Model Block 223 × 65 × 50 mm; 20 m/s reference speed; air 1.225 kg/m³.
- Mass ≥ 48.0 g without the cartridge; the target today is 48.2 g.
- Race time is most sensitive to drag (about **0.48 ms per mN** at 20 m/s) and mass (about **16.6 ms per g**).
- Model race times run 1.37 to 1.66 s, slower than real top cars (about 1.0 to 1.1 s), mainly because our thrust curve is invented (about 60% of a real cartridge's impulse).

---

## 2. Your job: what Part 4 must do

Part 4 turns **a carved body** into **a whole legal car** and **judges it**. It has three jobs:

1. **Parts and assembly.**
   - Attach the nose cone, front wing with its supports and end plates, rear wing with its supports, the wheel support structures (beam supports), wheels and hubcaps, the tether guides and the cartridge.
   - Cut the joints into the body (the "machined body").
   - Output:
     - the half car for CFD, with named surfaces `car`, `wheelF`, `wheelR`
     - the full car
     - total mass and centre of mass
   - Part settings (wing chord, tilt, height, pylon and so on) are inputs that Part 5 may search.
2. **Manufacturing files.**
   - The CNC body file, one STL per printed part and a parts list.
   - Every file must be makeable on the team's machines.
3. **The referee** (`legality.py`). It lives in `part5-simulation`, but **you own it**; Part 5 doesn't edit it.
   - An **independent** check of the finished car against every rule in the regulations, measured on the final meshes like a scrutineer would, with the margin for every numeric rule.
   - It must not trust Part 1's construction. That is why it is not inside Part 1: Part 1 makes the body legal by construction, and the referee checks the whole car, from the outside, with code that shares nothing with the cutter.

---

## 3. Where the code lives and how you push

- **Private repos** (owner `shawshanker18`): `part1-simulation` … `part5-simulation`, cloned side by side in one folder. Branch: **`main`**. Since 2026-11-09 it holds the carving code. The other chats' old `main` and every old branch are kept read-only as `archive/*` tags; never build on them. Each repo also carries its part's brief as `BUILD_SPEC.md`. The parts import each other through these sibling folders.
- **Workspace on this PC:** `C:/Users/shash/AppData/Roaming/Claude/scratch-workspaces/4314fcf2-a6e3-41fe-ba08-c22aef76a41f/eb244363-9678-4133-bff4-b2431f8b738c/scratch-2026-11-06-9528ad`. Read `CONTEXT.md` there first; it has the project state, accounts and decisions.
- **Public compute repo:** `shawshanker18/stem-racing-car`. It holds a copy of all five parts plus `.github/workflows` and `.github/lab`. Private repos have their Actions blocked by billing; the public repo runs free.
  - This is THE compute repo. The other chats' `stem-compute` repos belong to the plan the user set aside on 2026-11-09; don't use them.
- **Existing workflows** in the public repo (all under its `.github/workflows`):
  - `stress.yml`, `tests.yml`, `solver.yml`
  - `noise.yml`, `noise_long.yml`, `noise_var.yml`, `repeat.yml`
  - `adj_lab.yml`, `car_debug.yml`, `body_lab.yml`, `impact.yml`, `impact_wheels.yml`, `line_lab.yml`, `pinch_lab.yml`, `smooth.yml`
  - `capacity.yml`, `car_libs.yml`
  - Read one before you write a new one, and copy its install steps.
- **Push pattern:**

```bash
export GH_TOKEN=$(gh auth token --user shawshanker18)
cred=(-c credential.helper= -c "credential.helper=!f(){ echo username=x-access-token; echo password=$GH_TOKEN; }; f")
id=(-c user.name=shawshanker18 -c user.email=shawshanker18@users.noreply.github.com)
cd <partN>-simulation && git add <files> && git "${id[@]}" commit -m "<what and why>" && git "${cred[@]}" push origin HEAD
# replace the public copy (so deleted files go too), then strip private files
git -C <public> rm -r -q <partN>-simulation && mkdir -p <public>/<partN>-simulation
git archive HEAD | tar -x -C <public>/<partN>-simulation
cd <public> && rm -f part1-simulation/STEM*.pdf part*-simulation/BUILD_SPEC.md \
  && sed -i 's|\[`BUILD_SPEC.md`\](BUILD_SPEC.md)|`BUILD_SPEC.md` (in the private repo)|' <partN>-simulation/README.md \
  && git add -A <partN>-simulation \
  && git "${id[@]}" commit -m "<short> [skip ci]" && git pull --rebase && git "${cred[@]}" push origin HEAD:main
```

- **Install recipe for any GitHub job** (proven; keep the pinned versions, because unpinned versions changed the built files):

```yaml
env:
  PY_DEPS: numpy==2.4.6 scipy==1.17.1 pandas trimesh==5.2.0 scikit-image shapely rtree==1.4.1 mapbox-earcut manifold3d==3.5.4 fast_simplification==0.2.0 jax jaxlib matplotlib pymeshlab==2025.7.post1
  OMPI_MCA_hwloc_base_use_hwthreads_as_cpus: "1"
  OMPI_MCA_rmaps_base_oversubscribe: "1"
jobs:
  car:
    runs-on: ubuntu-24.04
    timeout-minutes: 350          # GitHub kills any job at 6 h
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - timeout-minutes: 25
        run: |
          (for i in 1 2 3 4 5 6; do timeout 90 sudo apt-get update -q && break; done)
          sudo apt-get install -y -q libopengl0 libglu1-mesa libegl1 libgl1 libgomp1 libxkbcommon0
          curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash   # CFD jobs only
          sudo apt-get install -y -q openfoam2412-default                  # CFD jobs only
      - run: pip install $PY_DEPS
```

- **Dispatching on a teammate fork:**
  - Sync it first: `GH_TOKEN=$(gh auth token --user <acct>) gh repo sync <acct>/stem-racing-car --source shawshanker18/stem-racing-car`
  - Then run: `gh workflow run <wf>.yml -R <acct>/stem-racing-car --ref main -f ...`
  - Teammates allow car rounds, tests and fork syncs only. Never change their settings or touch their other repos.
- **Your own working copies (added 2026-11-09, from Part 1's run).** Several agents work at once. Never edit, commit or push from a shared checkout (the old scratchpad copies of the board and of `stem-racing-car`): other agents' unsaved edits sit there. Clone your own copy of the public compute repo and of the progress board into your own scratchpad and work only there. Your private part repo is yours alone.
- **Pushes race.** Other agents push to `stem-racing-car` and to the board all the time. Commit, then `git pull --rebase` and push, retrying a few times if it's rejected. Before dispatching a run, check that GitHub has your commit: `gh api repos/<account>/stem-racing-car/commits/main -q .sha` must equal your `git rev-parse HEAD` (on a fork, after `gh repo sync`). A run dispatched after a rejected push runs the old code.
- **The shared `tests.yml` runs every part's tests on every push** to `stem-racing-car`, unless the commit message has `[skip ci]`. Always put it on public-copy commits, and dispatch tests on purpose.

- **Reading results:** `gh run download <id> -R <repo> -D <temp folder>` (never inside the repos). Read the summaries; don't re-run anything locally.

---

## 4. What already exists (read these files in full)

| File | What it does |
| --- | --- |
| `part4-simulation/assembly.py` | `build(W_mm, x_front_mm, d_halo_mm, body_half_stl, ...)`, `tether_guide`, `fixed_hardware_kwargs`, `extra_surfaces_from` |
| `part4-simulation/wings.py` | `build_front_wing` (auto-raises or lowers within the 5 mm track clearance and 20 mm outboard height), `front_wing_gates`, `build_rear_wing`, `rear_wing_gates`, `naca4`, chord measured horizontally (calipers: `min(fw.chord_mm, bbox x-extent)`) |
| `part4-simulation/nose.py` | `build_nose`, `nose_gates`, `body_section` (each ring kept 0.1 mm above the T3.7 line) |
| `part4-simulation/joints.py` | `cut`, `pod_joint`, `machined_body`, `nose_part`, `make_all`, `t55_keep_out`, `nose_shell` |
| `part4-simulation/beam_support.py` | Wheel support structures: `section`, `frame`, `pod_channel`, `sized_disc_t_mm`, `sized_root_d_mm` |
| `part4-simulation/wheel.py` | Team wheels: `team_wheel_meshes`, `mean_inertia_kg_m2`, `cfd_surface` |
| `part4-simulation/mesh_fairing.py` | `remesh_file` (tries 5 sizes: 1, 1.25, 0.8, 0.6 and 1.6× target, then a midpoint split of long edges) |
| `part4-simulation/component_contract.py` | Dimensions and constants of fixed hardware |
| `part5-simulation/legality.py` | The referee: `check(body_half_stl, assembly, mass_state=None, ...)`, `manufactured_checks`, `t55_wall_fraction`, `official_block_mm`, `summary` (count its checks as part of Step 1) |
| `part5-simulation/pattern.py` | Ranges of every searchable setting (body and parts) |
| `part5-simulation/checks/stress_cars.py` | Random cars; `--carve` carves the block first |

What the referee does today, beyond the basics:
- **T4.6 decal:** rays on a 1 mm grid at any surface except wheels, hubcaps and halo, with x extended ±45 mm. Notes report the tallest and longest clear patch.
- **T4.7 team number:** body only, between Ref A and the halo, on a 9 × 15 point window.
- **T4.4.3:** ignores the floor's top 0.3 mm skin and reports where the material is.
- **T4.4.4:** floor tolerance 0.5 mm.
- **T5.5 (3 mm chamber wall):** measured on the milled file `assembly["joints"]["manufactured"]["machined_body"]["file"]`, scaled by 1e-3.

---

## 5. Measured facts and history you must not repeat

- **Lofted random cars:** 98.9% legal, 0 crashes over about 4,000 cars. Most rejects are real T4.6/T4.7 breaks: the sidepod shoulder step caps the flat side at 12 to 14 mm.
- **Two rare faults the user said to ignore:**
  - the front pod channel splits a low body (about 1 in 900)
  - a thin front assembly that won't remesh (about 1 in 1,300)
  Watch for them on carved bodies; if they show up more often there, they matter again.
- **Past false results in the referee:**
  - T5.5 read 0% because it measured the half-body file instead of the milled body. Fixed.
  - A T4.4.3 sliver came from a 0.2 mm floor skin. Fixed by ignoring the top 0.3 mm skin.
  - Wing chord was measured along the surface, not horizontally. Fixed.
  - **Lesson:** every check needs a test that it fails when it should, not only that it passes.
- **Rear-wing tests:** tilt up, raised, pylon 15 to 20 and chord 20 were each 2 to 5 ms faster on their own. Combined, they didn't add up, so part settings interact and must be searched together.
- **Paint and stickers:** the user said not to model them.
- **Penalties:** many rules carry proportional penalties (T2.5). The referee reports margins so a car can be kept well inside every limit.

**Rules summary** (all from the 2026-27 regs, identical to 2025-26):
- **Body and size:**
  - Width 65 to 85, height ≤ 65.
  - Mass ≥ 48.0 g without the cartridge.
  - Track clearance ≥ 1.5.
- **Wheels:**
  - Wheelbase 120 to 140.
  - Wheel diameter 28 to 32.
  - Contact width ≥ 13 front and ≥ 17 rear, excluding fillets.
  - T7.9 keep-clear zones; T7.11 front view ≤ 20; T7.13 claw clearance 1.5.
- **Nose:** ≤ 40 ahead of Ref A, ≤ 25 high and ±15 wide.
- **Front wing:**
  - ≤ 20 high outboard, span ≥ 50.
  - Chord 15 to 25, measured horizontally.
  - Thickness 2 to 6, 5 mm clear air.
- **Rear wing:**
  - Behind Ref B, overhang ≤ 40, ≤ 65 high.
  - Span ≥ 50, chord 15 to 25, 5 mm clear air.
  - Visible from the front.
- **Chamber:**
  - Diameter 18 to 18.5, centre 30 to 40 above the track.
  - Depth 45 to 58, 3 mm wall.
  - The cartridge protrudes ≥ 5.
- **Halo:** notch centre at 34 ± 1, floor at 24.
- **Decals:** logo decal 30 × 15 on each side; team number 8 mm between the halo and Ref A.

Always confirm against the PDF text, not this summary.

---

## 6. Interfaces (contracts with other parts)

**Input from Part 1:**
- the cutter output JSON: `body_half_stl`, `machined_body_stl`, `mass_g`, `com_mm`
- the layout `{W, x_front, d_halo}`
- part settings from Part 5 (JSON per part: `--nose-json`, `--fwing-json`, `--rwing-json`, `--support-json`)

**Output, one car folder:**

```
car_half.stl             # CFD: solids car / wheelF / wheelR, metres, y >= 0
car_full.stl             # whole car, for renders
assembly.json            # every part: file, mass_g, com_mm, settings, joints incl. machined_body file
mass_report.json         # total mass with and without the cartridge, com_mm, wheel inertia
legality.json            # every check: rule id, pass/fail, measured value, limit, margin, note
manufacture/             # today: machined_body.stl, printed_*.stl (mm), from joints.make_all; add parts_list.csv
```

- `legality.json` summary: `{"legal": bool, "fails": [...], "min_margin_mm": ..., "n_checks": ...}`.
- Part 5 keeps only cars with `legal == true`.

---

## 7. What to build, in order

**Step 1: rule map.**
- Write `part5-simulation/RULES_MAP.md`: every rule in the 2026-27 regs (T1 to T10 and the appendices) in one table.
- Columns: rule id, short text, numeric limit, the check function that tests it, or "not checkable by model" with the reason (judge's call, material, paint, process).
- Nothing may be missing. A rule without a check and without a reason is a fail.

**Step 2: a pass and a fail test for every numeric rule.**
- For each numeric rule, make a car that is just inside (+0.2 mm or the rule's own tolerance) and one just outside.
- The referee must pass the first and fail the second, for the right rule.
- Build these by editing a known-good car, for example moving a wing, scaling the nose or thinning a wall.
- Put them in `part5-simulation/tests/test_rules_edges.py`.

**Step 3: independence check.**
- `legality.py` must import nothing from `part1-simulation` that builds or masks the body (no `unified_phi`, no `param_body` masks).
- Add a test that fails if it does.
- Today it also imports rule **geometry** from Part 1 (`geometry_contract`, `wheel_visibility_zones`, `virtual_cargo`, `halo_pocket`). Give the referee its own rule numbers, typed in from the PDF with page references, plus a cross-check test against Part 1's (12.3).

**Step 4: parts on carved bodies.**
- Carved bodies have shapes the lofted builder never made: steps, thin noses, odd sidepods.
- Run the carve stress (shared with Part 1's carve runs) and check that every part attaches, every joint cuts and every mesh is watertight.

**Step 5: real masses.**
- Replace the guessed densities and wheel masses with the team's printed-part material and weighed parts (ask, section 10).
- Mass sizing then targets the real total.

**Step 6: manufacturing export.**
- `manufacture/` files with a parts list.
- Check minimum wall thickness against the team's printer and the CNC tool (6.25 mm ball end, from top, bottom, left and right).
- The team confirms they can make one.

**Step 7: part settings for the search.**
- Make sure every part setting in `pattern.py` has a range that is legal at both ends for typical bodies.
- Report which settings the referee most often rejects.

**Step 8: docs.** `part4-simulation/README.md` and the rule map.

---

## 8. Tests (all on GitHub)

| Test | Pass mark |
| --- | --- |
| Unit tests `pytest part4-simulation/tests part5-simulation/tests` | 100% pass from a clean clone on main |
| Rule map | 100% of rules mapped to a check or a stated reason |
| Edge tests (Step 2) | every numeric rule: just-inside passes, just-outside fails, on the right rule id |
| Independence test | no imports of the cutter's masks |
| Carved-car assembly, 2,000 carved bodies | 0 crashes; every legal body gets a full car, or a stated, real reason why not |
| Lofted regression, 1,000 cars | ≥ 98.9% legal, 0 crashes (no worse than today) |
| Referee vs a hand check, 3 reference cars | the referee agrees with a careful manual measurement in CAD on every numeric rule (within 0.1 mm) |
| Mass | computed mass within 1% of the weighed printed parts (once weighings exist) |
| Manufacturing | the team confirms one exported car is makeable |

---

## 9. Compute allocation

**Scope of this split:** building and testing each part on its own. No final best-car run is planned now (user, 2026-11-09).

**Usable today: 179 machines** (every account measured with a dummy-job test, 2026-11-08 and 2026-11-09). Each is 4 cores and 16 GB, with a 6 h job limit.

**Need per part,** estimated from each brief's section 8 tests, including one rerun for fixes and the clean final rerun. These are machine-hours, not promises:

| Part | Main work | Estimate (machine-h) | Machines | Wall time at that share |
| --- | --- | --- | --- | --- |
| 1 Cutter | 2,000 carved cars (≈ 170 h), 0.5 mm grid study, repeats, reruns | ≈ 450 | **25** | ≈ 18 h |
| 2 Stopwatch | benchmarks on 3 meshes, noise studies, 20-car search-vs-fine ranking (fine = 4.4 h a car), warm start, chained runs | ≈ 350 | **40** | ≈ 10 h; long fine jobs set the pace |
| 3 Compass | known-answer case, compass test 80 runs × repeats, up to 6 fix attempts, step test, maybe the measured compass | 250 to 900, ≈ 600 | **75** | ≈ 8 h; the most uncertain and on the critical path |
| 4 Parts and rules | 2,000 carved assemblies, 1,000 lofted regression, edge tests, reruns | ≈ 350 | **34** | ≈ 10 h |
| 5 Loop | fake-stopwatch bench (almost free), resume tests, 20 real false-keep pairs, a small smoke run | ≈ 60 | **5** | ≈ 12 h |

**Accounts:**

| Account | Jobs at once | Split |
| --- | --- | --- |
| shawshanker18 (main, shared) | 40 | Part 3: 15, Part 4: 15, Part 1: 5, Part 5: 5 |
| mxnviir (Pro, shared) | 40 | Part 2: 20, Part 3: 20 |
| blackwingftc-lang | 20 | Part 2: 20 |
| Jdiejei | 20 | Part 1: 20 |
| instagramshashank8-bot | 20 | Part 3: 20 |
| blackwingstem-wq | 20 | Part 3: 20 |
| blackwinglinkedin-crypto | 14 | Part 4: 14 |
| anasssssssss1 | 5 | Part 4: 5 |

- **Shared accounts (main and mxnviir):** use your own workflow files named `p<N>_*.yml` (they live in `shawshanker18/stem-racing-car`; forks get them on sync). Set `strategy.max-parallel` to your cap on that account, and keep at most one run of yours in flight there, so the caps add up. Before dispatching, count your running and queued jobs (`gh run list -R <account>/stem-racing-car --status in_progress` and `--status queued`).
- **Seeds and labels by part** (on every account): Part 1 **41000+**, Part 2 **47000+**, Part 3 **42000+**, Part 4 **43000+**, Part 5 **46000+**. Main's 30000 to 38000 and the old per-account ranges were already used.
- **When a part finishes,** its machines go to whichever part has the most work left. Only the user moves them, so ask.
- Never use more than your share, and never another part's share. If you need more, ask the user with numbers: what for, how many machine-hours.
- **Codespaces (GitHub's cloud dev machines, all 8 accounts allowed since 2026-11-09):**
  - Each account has a free monthly allowance (about 120 core-hours, 180 on Pro; that's GitHub's published figure, so check each account's billing page).
  - They have no 6 h job limit and can be 8 or 16 cores, so they're for runs that don't fit Actions: Part 2's detailed and wall-resolved meshes, and Part 3's finer-mesh compass checks.
  - Not yet tested: a long run must survive the idle timeout (30 min by default, 4 h at most). Before relying on them, ask the user, and prove it with one run.
  - Keep each account's Codespaces spending limit at $0 so nothing is ever charged. Delete a codespace when its run is done.
  - They count as running on GitHub, not locally.

**Your share: 34 machines.** blackwinglinkedin-crypto 14 + anasssssssss1 5 + main 15. Most of your work needs no CFD: about 50 min per 10 cars per machine, so a 2,000-car carved run is about 6 rounds (about 5 h).


**Your commands:**

```bash
# anasssssssss1: all 5 jobs are yours (a 40-job stress run takes eight waves here)
export GH_TOKEN=$(gh auth token --user anasssssssss1)
gh repo sync anasssssssss1/stem-racing-car --source shawshanker18/stem-racing-car
gh workflow run stress.yml -R anasssssssss1/stem-racing-car --ref main -f cars_per_machine=10 -f seed_base=43000 -f carve=true

# blackwinglinkedin-crypto: all 14 jobs are yours (a 40-job stress run takes three waves here)
export GH_TOKEN=$(gh auth token --user blackwinglinkedin-crypto)
gh repo sync blackwinglinkedin-crypto/stem-racing-car --source shawshanker18/stem-racing-car
gh workflow run stress.yml -R blackwinglinkedin-crypto/stem-racing-car --ref main -f cars_per_machine=10 -f seed_base=43800 -f carve=true

# main: 15 jobs, through p4_*.yml with max-parallel: 15 (most of your carved-car runs go here)
export GH_TOKEN=$(gh auth token --user shawshanker18)
gh workflow run p4_assembly.yml -R shawshanker18/stem-racing-car --ref main -f seed_base=43400
```

Keep your seed ranges apart on your three accounts (for example 43000+ on anas, 43400+ on main, 43800+ on blackwinglinkedin-crypto), so no car is built twice.

**How to use your machines** (all of this is dispatching and reading; the work itself runs on GitHub):

- **Teammate accounts** run the workflows on their own fork, `<account>/stem-racing-car`. Before each run, sync the fork so it has the latest code and workflows:

```bash
export GH_TOKEN=$(gh auth token --user <account>)        # per command; never gh auth switch
gh repo sync <account>/stem-racing-car --source shawshanker18/stem-racing-car
gh workflow run <workflow>.yml -R <account>/stem-racing-car --ref main -f <input>=<value>
gh run list -R <account>/stem-racing-car --limit 5        # find the run id, watch its state
gh run download <id> -R <account>/stem-racing-car -D <temp folder>
```

- **Your slice of the main account** (`shawshanker18`, shared by four parts) runs only through your own workflow files `p4_*.yml` in `shawshanker18/stem-racing-car`, with `max-parallel` set to your cap:

```yaml
name: p4_<what>                     # your own file; never edit another part's
on:
  workflow_dispatch:
    inputs: { seed_base: { default: "<your seed base>" } }
permissions: { contents: read }
jobs:
  job:
    runs-on: ubuntu-24.04
    timeout-minutes: 350
    strategy:
      fail-fast: false
      max-parallel: <your cap on main>
      matrix: { i: [0, 1, 2, 3, 4] }   # as many as the work needs; max-parallel limits how many run at once
    steps:
      # the install recipe from section 3, then your command
```

- **New or changed workflows** go into `shawshanker18/stem-racing-car` first (push pattern, section 3). Teammate forks get them on the next `gh repo sync`.
- **Matrix size versus cap:** `stress.yml` starts 40 jobs (one per seed). On a 20-job account that runs in two waves, and on a 5-job account in eight. That's fine, but count it in your time estimate.
- **Before every dispatch,** check that your running plus queued jobs stay within your cap on each account.

---

## 10. Questions to ask the user (only these, and only when you reach them)

1. What material and printer do you use for the printed parts (nose, wings, supports)? Its density, or a weighed test piece?
2. Weights of the real wheels, hubcaps, tether guides and bearings, if any?
3. If you fall behind: can you have machines from a finished part?
4. Can someone check one exported car (files only) and confirm the team can make it?

Ask each as one short question with clear options. Only the step that needs the answer waits. Keep working on everything else while you wait for an answer (rule 3).

---

## 11. Done means (all must hold, shown on GitHub, rerun from a clean clone on main)

- Every test in section 8 at its pass mark. Record the run links and outputs in `part4-simulation/PROOF.md`.
- `RULES_MAP.md` is complete, and every numeric rule has a passing pair of edge tests.
- 2,000 carved cars assemble with 0 crashes, and every reject is real.
- The manufacturing files are confirmed makeable by the team.
- The progress board shows Part 4 at 100% with status `done`, in plain words.
- The user has been told the results in short bullets and has agreed it is done.

Anything short of this is **not done**: say what's missing.

---

## 12. Technical specification (read before section 7)

Read from the code on 2026-11-09. File and function names are exact. **Design** marks a proposal; **Verify** marks something not yet checked.

### 12.1 Frames, units and materials

**Frame:** the same as Part 1. x runs nose to tail (x = 0 at the nose tip), y is the half-width, z is up from the track.
- The code works in SI.
- **Manufacturing files are in millimetres** (`joints.make_all`).
- The CFD files are in metres, right half (y ≥ 0).

**Densities:**

| Material | Density | Where set | Status |
| --- | --- | --- | --- |
| Foam block | 0.163 g/cm³ | `geometry_contract.DENSITY_BODY_KGM3` = 163, `joints.FOAM_G_CM3` | |
| Printed nose | 1.0 g/cm³ | `DENSITY_NOSE_KGM3` | **placeholder** until the team gives the printer material |
| PA12 and PLA parts | | `joints.DENSITY_G_CM3` | **Verify** each value against the team's weighed parts |

**Mass:**
- `manufactured_g` = every manufactured file's volume × density, plus wheels, bearings and the halo. It's "the car on the scale", and T3.6 is checked on it.
- Part 1's sizing targets it.

### 12.2 How a car is assembled (`assembly.build`)

**The order:**
1. Body (from Part 1)
2. Wheels and supports
3. Halo
4. Nose
5. Front and rear wing
6. Tether guides
7. Joints
8. Manufacturing files
9. Mass rollup
10. Gates

**Wheels** (`wheel.py`):
- The team's STL wheels in PA12, each with a 6 mm seat for one 3 × 6 × 2.5 bearing.
- Mass and inertia measured from the mesh (`mean_inertia_kg_m2`).
- For CFD, each wheel is replaced by a closed spinning disc (`cfd_surface`).

**Supports** (`beam_support.py`):
- One PA12 part per axle: beam, stub axles, disc, boss, hubcap.
- It sits in a channel milled from below (`pod_channel`).
- Sized for the load case: `sized_disc_t_mm`, `sized_root_d_mm`.
- Gates for T7.12.1 and T3.7, plus the T7.13 claw clearance (a 12.0 mm disc; the v2 CAD's 12.7 mm disc blocked the claw).

**Nose** (`nose.py`):
- A printed shell ahead of Ref A.
- Rings lofted from the body's own section at Ref A (`body_section`), each kept 0.1 mm above the T3.7 line.
- T8.2 (≤ 40 mm overhang) and T8.5.1 (|y| ≤ 15, z ≤ 25) gates.

**Front wing** (`wings.build_front_wing`):
- NACA four-digit section (`naca4`) extruded across the span, with a flap.
- Automatically raised or lowered (`z_chord_mm`) to keep 5 mm of clear air to the track and stay ≤ 20 mm high outboard (T8).
- **Chord is measured horizontally,** as calipers would: `min(fw.chord_mm, bounding-box x extent)`.
- Gates: span ≥ 50, chord 15 to 25, thickness 2 to 6.

**Rear wing** (`build_rear_wing`):
- Behind Ref B, overhang ≤ 40, height ≤ 65, span ≥ 50, chord 15 to 25, 5 mm clear air.
- Visible from the front (T9.7).
- Trimmed at the body surface and surface-bonded (no pocket fits over the cartridge wall).

**Joints** (`joints.py`):
- Each printed part has a positive (tenon or keel) glued into a milled negative (pocket).
- Pockets are shaped so the 6.25 mm ball can cut them (`cut`, `pod_joint`), and they keep out of the T5.5 wall (`t55_keep_out`).
- `machined_body` subtracts every pocket.
- `make_all` writes one closed solid per part, re-reads each file, and reports whether it's closed, its piece count, its volume and its mass.

**Remeshing** (`mesh_fairing.remesh_file`):
- Tries 5 target sizes (1, 1.25, 0.8, 0.6 and 1.6 × the base size).
- Falls back to splitting long edges at their midpoints.
- About 1 front assembly in 1,300 still fails. The user said to ignore that on lofted bodies; watch for it on carved ones.

**Outputs:**
- `car_half.stl` (solids `car`, `wheelF`, `wheelR`) and the `extra_surfaces` list for Part 2.
- `assembly.json`, `mass_report.json`, `legality.json`, and the `manufacture/` folder.

### 12.3 The referee (`part5-simulation/legality.py`, owned by you)

**Rule ids it checks today** (exact strings in the code):
- T1.22_ballast_capacity
- T3.4_width_min / max, T3.5_height, T3.6_mass (and _g), T3.7_clearance
- T4.1_single_body, T4.2_cargo_inside_body
- T4.4.2_halo_seen_from_front / side, T4.4.3_halo_seen_from_top, T4.4.4_halo_fits_pocket, T4.4.4_pocket_floor
- T4.6_logo_decal_room, T4.7_team_number_room
- T5.1_diameter, T5.2_height, T5.3_depth, T5.5_wall, T5.6_protrusion
- T6.1_tether_line_clear
- T7.3_W_min / max, T7.10_{part}_seen_from_side, T7.11_front_wheel_seen_from_front, T7.13_{tag}_claw_clearance
- T8.2_nose_overhang, T8.5.1_nose_half_width, T8.5.1_nose_z
- T8.7_front_wing_clear_air_all_parts, T8.8_front_wing_seen_from_front
- T9.4.2_rear_overhang, T9.6_rear_wing_clear_air_all_parts, T9.7_rear_wing_seen_from_front
- plus every Part 4 gate, and `manufactured_checks` (every file closed, piece count right)

**The methods, by type:**

| Type | Method | Examples |
| --- | --- | --- |
| Size | bounding boxes and sections of the final meshes | width, height, overhang |
| Mass | from the manufactured files | T3.6 |
| Visibility | rays on a 1 mm grid from the named view; a target is visible if no other part blocks the ray | T4.4.x, T7.10, T7.11, T8.8, T9.7 |
| Room for decals | the largest clear flat patch found by ray hits on a 1 mm grid | T4.6: 30 × 15 on any surface except wheels, hubcaps and halo; x extended ±45 mm. T4.7: body only, between Ref A and the halo, a 9 × 15 point window |
| Clear air | the regulation's 5.0 mm ball and 2 mm rod swept against all parts | T8.7, T9.6 |
| Chamber | measured on the **milled** body file (half-body file × 1e-3 gave a false 0% once) | T5.x |

**Margins:** every numeric check records the measured value, the limit and the margin, so the car can be held well inside each rule. Many rules carry proportional penalties (T2.5).

**Independence problem (fix it):** the referee imports rule geometry from Part 1:
- `geometry_contract`
- `wheel_visibility_zones.zone_polygons_mm`
- `virtual_cargo` sizes
- `halo_pocket.ballast_capsule_mesh_m`

If one of those is wrong, the cutter and the referee are wrong together and nothing notices. **Design:** give the referee its own constants file, typed in from the 2026-27 PDF with the page and rule number per value. Then add a test that compares it with Part 1's values: a mismatch fails both and is reported. Shared code may stay only for pure geometry helpers (meshes, rays), never for rule numbers or zone shapes.

### 12.4 Rule map and edge tests (**Design**)

**`RULES_MAP.md`:** one row per rule in the PDF.

| Column | Contents |
| --- | --- |
| id | the rule number |
| page | the PDF page |
| short text | plain words |
| numeric limit(s) and unit | |
| tolerance | the rule's own, if any |
| check | the function, and the result key in `legality.json` |
| status | `checked`, or `not checkable by model` with a reason (judge's call, material, paint, process) |

**Edge-test generator,** for each numeric rule:
1. Start from a known-good car.
2. Change one thing to land just inside the limit (limit − max(0.2 mm, the rule's tolerance)), and one to land just outside (limit + the same).
   - Examples: wing z, wing chord, nose length, body skin, wheel x.
3. The check must pass the first, fail the second, and name the **right rule id**.
4. Where one change trips several rules, assert the set.

**The why:** this proves each check has the right threshold and the right sign. A check that only ever passes proves nothing; the T5.5 0% bug was exactly that.

### 12.5 Tests, with the statistics

**Carved-car assembly, 2,000 cars:**
- 0 crashes, which bounds the crash rate below 0.15% with 95% confidence.
- Every legal body gets a full car or a stated, real reason.
- Report the reject causes by rule id.

**Lofted regression, 1,000 cars:**
- At least 98.9% legal (today's rate on 4,000).
- The 95% error at n = 1,000 is ±0.65%. A drop below 98.2% is a real regression; between 98.2 and 98.9, rerun with more cars before deciding.

**Hand check, 3 reference cars:**
- A careful manual CAD measurement of every numeric rule, matching the referee within 0.1 mm.
- Choose cars near limits, so a 0.1 mm error would flip a verdict.

**Mass:**
- Computed vs weighed printed parts within 1%, once weighings exist.
- Until then, list every density as a placeholder.

**Manufacturing:** the team confirms one exported car is makeable on their printer and mill.

### 12.6 Integration (exact hand-offs)

**In, from Part 1:**
- `body_half.stl` (metres), the machined body, `cut.json`
- the layout `{W, x_front, d_halo}` in mm
- part settings JSON per part (`--nose-json`, `--fwing-json`, `--rwing-json`, `--support-json`; the ranges are in `pattern.py`)

**Out:**
- `car_half.stl` (metres, y ≥ 0, solids `car` / `wheelF` / `wheelR`), for Parts 2 and 3
- `assembly.json`
- `mass_report.json` (`car_weight_kg` including the empty cartridge shell, `com_mm`, wheel inertia)
- `legality.json` (`legal`, `fails`, `min_margin_mm`, `n_checks`, and every check)
- `manufacture/` (mm)

### 12.7 Failure modes and what to read

| Symptom | Read | Usual cause |
| --- | --- | --- |
| T4.6 / T4.7 fail on most bodies | the notes (tallest and longest clear patch) | the sidepod shoulder step limits the flat side to 12 to 14 mm |
| T5.5 reads 0% | the file used | the half body measured instead of the milled one |
| a wing fails chord | the measurement method | measured along the surface instead of horizontally |
| a remesh fails | `remesh_file` tries | a thin front assembly; known to be rare |
| a body split by a pod channel | the joint report | a low body: the channel cuts through it |
