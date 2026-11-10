# Part 2: the stopwatch (CFD + race model). Complete build brief

You are the agent that owns **Part 2** of the STEM Racing car project. This file is everything you need: read all of it before you touch anything. You build, test and prove Part 2 **on its own** until it meets the "Done" bar in section 11. **Section 12 is the technical specification:** how the code works (units, frames, maths, algorithms), exactly what to build and why, how to test it, the statistics behind every pass mark, the hand-offs and the known failure modes. Read it before section 7. You work **on your own, continuously**: you report only at real milestones, in simple bullets, and keep going, and you stop only for the real decisions listed in rule 3. Nothing here may be skipped.

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
   - After every step, update **only your own file** `progress/part2.json`:
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

## 2. Your job: what Part 2 must do

Part 2 takes **a finished car** and returns **its race time with an honest error bar**. It is the judge of "faster"; every other part trusts it. So it must be:

1. **Right enough:** drag and lift close to reality, checked against published wind-tunnel data and against the team's real cars where possible.
2. **Quiet:** a tiny shape change gives a tiny time change. Today a 0.01 mm skin change moves the time by about 1 ms, which hides real gains of 1 to 3 ms.
3. **Consistent:** the cheap search mesh ranks cars in the same order as the expensive fine mesh.
4. **Fast enough:** one car on the search mesh in ≤ 35 min on one 4-core GitHub machine.
5. **Repeatable:** the same car on any machine gives the same answer. Today 6 machines built byte-identical car files and agreed within 0.28 ms; the target is ≤ 0.1 ms.
6. **Physically complete in the race model:** measured thrust curve, rolling friction, wheel inertia, mass, centre of mass, tether drag, all from the team's measurements, not guesses.

It has two halves:
- **CFD:** OpenFOAM v2412 (ESI). Half car with a symmetry plane, k-omega SST, moving ground, wheels as rotating walls, snappyHexMesh. Output: drag and lift at 20 m/s (`D20_N`, `L20_N`), split by part.
- **Race model:** a JAX 1-D ODE over 20 m. Output: race time and its slopes with respect to every input.

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
| `part2-simulation/openfoam_case.py` | Builds and runs the case. `OpenFOAMRunConfig`, `build_case`, `run_stages`, `build_snappy_dict`, `build_control_dict`, mesh levels `RESOLUTION_REFINEMENT`, parsers for forces, residuals, y+ and convergence |
| `part2-simulation/cfd_wrapper.py` | `run_half_car_cfd(...)` and `run_half_car_adjoint(...)`, `CFDHealthReport`, watertight check |
| `part2-simulation/openfoam_adjoint.py`, `adjoint_contract.py` | The adjoint case (Part 3 owns its correctness; you own the shared primal settings) |
| `part2-simulation/race_objective.py` | The JAX race model: `race_time_seconds`, `race_value_and_grad`, `finite_difference_check`, `make_param_vector`, thrust from a CSV by RBF fit |
| `part2-simulation/race_objective_adapter.py`, `mass_com_ingest.py`, `candidate_record.py`, `physics_contract.py` | Glue: CFD forces + mass report → race time record |
| `part5-simulation/run_car.py` | One car end to end: `--cfd --res medium --np 4 --cfd-iters 1000 --cfd-json '{...}'` |
| Workflows `noise.yml`, `noise_long.yml`, `noise_var.yml`, `repeat.yml` | The noise and repeatability experiments |

**Cleanup notes (2026-11-09):** `race_objective_hash.txt` (a stale fingerprint), the duplicate thrust CSV in Part 1 and the test of Part 5's removed `merge_results.py` are gone; all Part 2 tests pass. Used only by their own tests (keep or remove, ask the user): `adjoint_contract.compute_adjoint_objective`, `package_gradient_bundle`, `get_active_objective_weights`, `physics_contract.grams_to_kg`.

Key code, quoted:

```python
# openfoam_case.py
RESOLUTION_REFINEMENT = {"coarse": (2, 3), "medium": (3, 4), "fine": (4, 5), "resolved": (5, 5)}
# background cell = car length / 12; levels are (min, max) surface refinement
@dataclass
class OpenFOAMRunConfig:
    reference_speed_mps: float = 20.0
    air_density_kgm3: float = 1.225
    turbulence_model: str = "kOmegaSST"
    resolution: str = "medium"
    max_iterations: int = 2000
    n_subdomains: int = 1            # >1 decomposes with scotch + mpirun
    underbody_refinement_level: int = 1
    turbulence_intensity: float = 0.005
    turbulent_viscosity_ratio: float = 5.0
    wall_function: str = "spalding"
    wake_refinement: bool = True
    wall_resolved: bool = False      # y+ <= 2 layer stack (team requirement 2026-09-30)
    first_layer_m: float = 1.5e-5
    layer_overrides: Optional[dict] = None

# race_objective.py
PARAM_NAMES = ("drag_20_n", "car_weight_kg", "mu", "wheel_moi_kg_m2",
               "time_coefficient", "com_height_m", "lift_20_n", "com_x_m")
R_WHEEL = 0.01413; N_WHEELS = 4; G = 9.81; TRACK_LENGTH = 20.0
# a = [F_thrust(t) - D20*q/20^2 - mu*m(t)*g] / [m(t) + N*I/r^2],  q = v^2, integrated in x
# D(v) = D20*(v/20)^2  (single-point aero)
make_param_vector(drag_20_n, car_weight_g, mu, wheel_moi_g_mm2,
                  time_coefficient_percent=100, com_height_mm=30, lift_20_n=0, com_x_mm=0)

# part5-simulation/solver.py, the search settings
SEARCH_CFD = {"layer_overrides": {"nSurfaceLayers": 0}}   # no surface layers on the search mesh
SEARCH_ITERS = 1000
NOISE_S = 1.0e-3
```

---

## 5. Measured facts and history you must not repeat

**Speed:**

| Mesh | Size | Time on 4 cores |
| --- | --- | --- |
| Medium, no layers, 1,000 iterations (search mesh) | about 0.65 M cells | about 30 min |
| Fine | | about 4.4 h |
| Resolved | | over 6 h; it times out at GitHub's 6 h limit |

- Long tests `start_fine` and `start_resolved` still fail by timeout. They need chaining across jobs or a longer machine.

**Noise:** cars 0.01 mm apart in skin thickness jump about 1 ms in race time.
- Remeshing is the main source: snappyHexMesh makes a different mesh for a tiny change.
- Iteration averaging is the next source. `noise_var.yml` reads drag at 250, 500, 750, 1,000, 1,500 and 2,000 iterations to see when it settles.

**Repeatability:** the same car on 6 machines: byte-identical car files, race times within 0.28 ms. CPU type makes no difference.

**Hardware options tested on paper and by measurement:**
- Kaggle GPU (P100 or 2×T4, about 30 h a week, 12 h sessions): only about 1.1 to 2× faster, even at 8 M cells, because AmgX only speeds up the pressure solve. Its value is the 12 h session for long meshes.
- Oracle's free ARM machine (4 cores, 24 GB, no time limit) could also run long meshes.
- GitHub runners can't talk to each other natively, so one car can't span machines. Tailscale is possible but slow over the internet.

**Race model weaknesses:**
- **The thrust curve is invented:** about 60% of a real cartridge's impulse. Every trade-off, drag against mass for example, depends on it.
- The centre-of-mass penalty tables (`_COM_PENALTY_DATA_MM/_S`, `_COM_X_PENALTY_K`) are **placeholders**, not measurements.
- Drag is single-point (D ∝ v²). Lift enters only through friction.

**Past mistakes:**
- Calling model times track times.
- Trusting single runs inside the noise.
- A wrong lift sign in a comment (fixed: L is positive up).

**The other plan (OVERVIEW.md)** aimed for CFD within 2% of the Ahmed-body benchmark and 0.2 ms noise. Our pass marks are 5% (on the 35° case, which RANS can do) and 0.3 ms. Report whether you also reach 2% and 0.2 ms.

---

## 6. Interfaces (contracts with other parts)

**Input (from Part 4 / Part 5), one folder per car:**
- `car_half.stl`: watertight, metres, half car (y ≥ 0), solid named `car`.
- Extra surfaces named `wheelF`, `wheelR` for the rotating walls.
- `mass_report.json`: total mass in grams with and without the cartridge, `com_mm`, and wheel mass and inertia.

**Output `stopwatch.json`:**

```json
{"D20_N": 0.0, "L20_N": 0.0, "parts": {"car": {"D_N": 0.0}, "wheelF": {}, "wheelR": {}},
 "race_time_s": 1.5412, "race_time_sd_s": 0.0003,
 "dT_d": {"drag_20_n": 0.48, "car_weight_kg": 16.6, "lift_20_n": 0.0, "com_x_m": 0.0, "com_height_m": 0.0},  // seconds per unit (s/N, s/kg, s/m)
 "mesh": {"res": "medium", "cells": 650000, "layers": 0, "iters": 1000},
 "converged": true, "residual_p": 1e-4, "force_osc_frac": 0.001, "seconds": 1800,
 "model_inputs": {"thrust_csv": "measured_2026-xx.csv", "mu": 0.0, "wheel_moi_kg_m2": 0.0}}
```

- The `dT_d` slopes are what Part 3 multiplies its drag and lift maps by. Keep the names exactly as they appear in `PARAM_NAMES`.
- **Paired comparison API** for Part 5: `compare(car_a, car_b) -> (dT, sd)`. Run both cars on the same machine type and the same mesh recipe, and give an honest sd from repeats.

---

## 7. What to build, in order

**Step 1: benchmark the CFD against published data.**
- Run the Ahmed body (25° and 35° slant) at the published Reynolds number, with our settings and our mesh recipe scaled to its length.
  - Look up the published experimental drag coefficient and cite the source in `PROOF.md`.
  - RANS is known to struggle with the 25° case. Report it honestly, and treat 35° as the pass case.
- Add one bluff body at our Reynolds number (about 3×10⁵ on car length) with published drag. Pick one and cite it.
- Run each at medium, fine and resolved to show grid convergence (Richardson extrapolation / GCI).

**Step 2: cut the noise.** Target a race-time SD ≤ 0.3 ms for tiny changes on the search mesh. Try these in order, measuring each with `noise_var.yml`-style runs of at least 16 cars at skins 0.01 mm apart (8 cars pin σ only to a factor of 3; method in 12.3):
1. Longer averaging windows.
2. Fixed background mesh and snap settings.
3. Mesh morphing instead of re-snapping for small moves. This is likely the biggest win: the mesh topology stays the same, so the noise from remeshing disappears.
4. Surface layers versus none.
5. More iterations.

Report the noise, the time per car, and the best combination.

**Step 3: ranking agreement.**
- Take 20 cars spread over the space, including carved shapes from Part 1's stress cars.
- Run each on the search mesh and on the fine mesh.
- Pass: Spearman rank correlation ≥ 0.9, and sign agreement ≥ 90% for every pair that differs by more than 3 ms on the fine mesh.

**Step 4: warm start.**
- Start a car's CFD from a neighbour's converged solution (`mapFields`).
- Pass: the same drag as a cold start within the noise, and at least 30% less time.

**Step 5: long runs past 6 h.**
- Checkpoint the case and upload it as an artifact before the time limit. The next job downloads it and continues.
- Pass: a chained fine run matches an unbroken run within 0.1% in drag. Test on a run short enough to also do unbroken.
- Then make `start_fine` and `start_resolved` pass.

**Step 6: a real race model.**
- Replace the invented thrust with the team's measured thrust curve (ask, section 10).
- Use measured rolling friction (slope test), wheel mass and inertia (CAD or a spin-down test), the weighed mass, and tether drag if measurable.
- Replace the placeholder centre-of-mass penalties with measurements, or remove them and say so.
- Keep `finite_difference_check` passing (JAX gradient against finite difference within 0.1%).

**Step 7: model against track.**
- If the team has timed runs of real cars, compare the model time with the track time.
- Report the error. Never hide it. If the error is over 3%, find out why before anyone trusts the trade-offs.

**Step 8: docs.** `part2-simulation/README.md` covers the API, the contracts, the mesh recipes and how to read `stopwatch.json`.

---

## 8. Tests (all on GitHub)

| Test | Pass mark |
| --- | --- |
| Unit tests `pytest part2-simulation/tests` (11 files today) | 100% pass from a clean clone on main |
| Ahmed 35° drag vs published | within 5% at the finest mesh; GCI reported |
| Ahmed 25° | reported with the error and explained; no pass/fail |
| Second benchmark at our Re | within 5% |
| Noise, ≥ 16 cars 0.01 mm apart, search mesh | residual SD about a fitted line ≤ 0.3 ms, with its 95% interval (today about 1 ms) |
| Repeatability, 1 car × 6 machines | spread ≤ 0.1 ms (today 0.28 ms) |
| Ranking, 20 cars, search vs fine | Spearman ≥ 0.9; pair sign agreement ≥ 90% for gaps > 3 ms |
| Warm start, 10 cars | drag within noise of cold start; ≥ 30% faster |
| Chained long run | within 0.1% of the unbroken run |
| Race model gradient check | JAX vs finite difference within 0.1% on every parameter |
| Convergence gate | every car reports `converged`, residual and force oscillation; unconverged cars are flagged, never silently used |
| Speed | search mesh ≤ 35 min per car on 4 cores |

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

**Your share: 40 machines.** blackwingftc-lang 20 + mxnviir 20 (shared with Part 3). A noise batch of 8 cars is 8 jobs × 30 min. The 20-car ranking study is 20 search jobs plus 20 fine jobs × 4.4 h, so run the fine ones on the 20 you have on one account. Codespaces on blackwingftc-lang and mxnviir for meshes over 6 h, after the Codespace test.


**Your commands:**

```bash
# blackwingftc-lang: all 20 jobs are yours. A noise study (8 cars at skins 0.01 mm apart):
export GH_TOKEN=$(gh auth token --user blackwingftc-lang)
gh repo sync blackwingftc-lang/stem-racing-car --source shawshanker18/stem-racing-car
gh workflow run noise_var.yml -R blackwingftc-lang/stem-racing-car --ref main -f label=n1 -f res=medium -f iters=1000 -f opt='{}'
# benchmarks, ranking, warm start and chained runs: write p2_*.yml in shawshanker18/stem-racing-car,
# sync the fork, then run them on blackwingftc-lang the same way

# mxnviir: 20 of its 40 jobs are yours (Part 3 has the other 20), through p2_*.yml with max-parallel: 20
export GH_TOKEN=$(gh auth token --user mxnviir)
gh repo sync mxnviir/stem-racing-car --source shawshanker18/stem-racing-car
gh workflow run p2_fine.yml -R mxnviir/stem-racing-car --ref main
```

You have no slice of the main account.

**How to use your machines** (all of this is dispatching and reading; the work itself runs on GitHub):

- **Teammate accounts** run the workflows on their own fork, `<account>/stem-racing-car`. Before each run, sync the fork so it has the latest code and workflows:

```bash
export GH_TOKEN=$(gh auth token --user <account>)        # per command; never gh auth switch
gh repo sync <account>/stem-racing-car --source shawshanker18/stem-racing-car
gh workflow run <workflow>.yml -R <account>/stem-racing-car --ref main -f <input>=<value>
gh run list -R <account>/stem-racing-car --limit 5        # find the run id, watch its state
gh run download <id> -R <account>/stem-racing-car -D <temp folder>
```

- **Your slice of the main account** (`shawshanker18`, shared by four parts) runs only through your own workflow files `p2_*.yml` in `shawshanker18/stem-racing-car`, with `max-parallel` set to your cap:

```yaml
name: p2_<what>                     # your own file; never edit another part's
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

1. Do you have a real thrust curve (force against time) for the cartridges you race? If not, can the team measure one, or name a published one to use?
2. Rolling friction: can the team do a slope or roll-down test? Give the angle and roll distance.
3. Wheels: mass of one front and one rear wheel, or the CAD file?
4. Timed runs: any real track times for cars whose CAD you have?
5. Benchmark: is Ahmed 35° within 5% good enough as the outside-truth check, or do you want a different one?

Ask each as one short question with clear options. Only the step that needs the answer waits. Keep working on everything else while you wait for an answer (rule 3).

---

## 11. Done means (all must hold, shown on GitHub, rerun from a clean clone on main)

- Every test in section 8 at its pass mark. Record the run links and outputs in `part2-simulation/PROOF.md`.
- The noise target met, or, if truly impossible, the evidence shown to the user and their written agreement to a new number.
- The race model runs on measured inputs, or every remaining guess is listed in `PROOF.md` and the user has accepted the list.
- `stopwatch.json` and `compare()` are used by Part 5 without changes.
- The progress board shows Part 2 at 100% with status `done`, in plain words.
- The user has been told the results in short bullets and has agreed it is done.

Anything short of this is **not done**: say what's missing.

---

## 12. Technical specification (read before section 7)

Read from the code on 2026-11-09. File and function names are exact. **Design** marks a proposal; **Verify** marks something not yet checked.

### 12.1 The CFD case (`openfoam_case.py`, `cfd_wrapper.py`)

**Frame:** the same as Part 1. x runs nose to tail, y is the half-width (y ≥ 0), z is up from the track. SI units.

**Physics:**
- Steady, incompressible RANS (`simpleFoam`, ESI OpenFOAM v2412).
- k-ω SST.
- U∞ = 20 m/s, ρ = 1.225 kg/m³, ν = μ/ρ ≈ 1.5e-5 m²/s.
- Reynolds number on car length (about 0.23 m) is about 3 × 10⁵.

**Domain** (`domain_box`):
- 3 car lengths upstream and 8 downstream.
- 5 × the car's width to the side and 5 × its height above.
- y_min = 0 is a `symmetryPlane`.
- z_min = 0 **is the track**. It used to sit 252 mm below the car, which removed ground effect; fixed 2026-07-24.

**Boundaries:**

| Boundary | U | p | Turbulence |
| --- | --- | --- | --- |
| inlet | `fixedValue (20 0 0)` | zeroGradient | k = 1.5(I·U)² with I = 0.5%; ω = k/(r·ν) with r = νt/ν = 5 |
| outlet | `inletOutlet` | fixedValue 0 | inletOutlet |
| outer, upperWall | slip | | |
| lowerWall (track) | moving ground `fixedValue (20 0 0)` | | |
| car | no-slip | | |
| wheels | `rotatingWallVelocity` about their axle (`axis`, `omega` from the surface spec) | | |

**Verify** that ω = U∞/R_wheel, about 1,415 rad/s, with the sign that makes the contact patch match the ground speed.

**Mesh:**
- `blockMesh` background cell = reference length / 12.
- `snappyHexMesh` surface refinement levels (min, max) per resolution: coarse (2, 3), medium (3, 4), fine (4, 5), resolved (5, 5).
- `nCellsBetweenLevels 3`, `resolveFeatureAngle 30`.
- An underbody box one level finer (`underbody_refinement_level`), because the gap is about 1.5 mm.
- Wake boxes.
- **Layers:** by default 3, expansion 1.2, final thickness 0.5 (relative). The **search mesh uses none** (`SEARCH_CFD`).
- **Wall-resolved** (`wall_resolved=True` or `resolved`): first layer 1.5e-5 m for y+ ≤ 2 (a team requirement from 2026-09-30). Otherwise the Spalding wall function, valid at any y+.

**Forces:**
- `forces` and `forceCoeffs` function objects per patch, with CofR at the nose tip.
- Half-car values × 2 give the full car (`to_full_car`; `ADJOINT_HALF_CAR_SCALING` = 2.0 for the adjoint).
- **D20_N** is the full-car force along +x. **L20_N** is the full-car force along +z (positive up, so downforce is negative).

**When a solve counts as converged** (`cfd_wrapper.py`):
- the final pressure residual is ≤ 5e-3
- the mean force is averaged over the last 20% of iterations (`FORCE_AVERAGE_FRACTION`)
- the **standard error of that mean** is ≤ 1% (`MAX_FORCE_MEAN_STDERR`). It's corrected for autocorrelation: N_eff = N / (1 + 2Σρ_k), because SIMPLE iterations are strongly correlated.
- the drift is ≤ 2% (`MAX_FORCE_DRIFT`): |slope| × window / mean

An unconverged solve doesn't raise. It's flagged in `CFDHealthReport`, and callers must not rank on it.

### 12.2 The race model (`race_objective.py`)

**State:** (t, q = v²), integrated over distance x from 1e-4 m to 20 m.
- RK4 on a "powered" grid: 1,000 steps with the points bunched near the start (power 2). This handles dt/dx = 1/√q, which is singular at launch.

**Equations:**
- dt/dx = 1/√q
- dq/dx = 2a
- a = (F_thrust(t) − D20·q/400 − μ·(m·g − L20·q/400)) / (m + 4·I/r²), with r = 14.13 mm and I the inertia of one wheel

**Mass:**
- m(t) = `car_weight_kg` (the whole car **including the empty cartridge shell**) + the unspent CO2.
- Thrust and CO2 mass vs time come from `co2_thrust_data.csv`, fitted with 80 Gaussian basis functions (ridge 1e-8) and a 25 ms exponential tail.

**Differentiable:**
- JAX in float64.
- `race_value_and_grad` gives T and dT/d(every parameter in `PARAM_NAMES`).
- `finite_difference_check` compares those against finite differences.

**Penalties:**
- `com_height_time_penalty` is a degree-4 polynomial through **placeholder** points.
- `com_x_time_penalty` = 0.001 s/m² × (x_com − 0)², also a **placeholder**.

**Measured sensitivities at today's car:** about 0.48 ms per mN of D20, and about 16.6 ms per gram.

**What's wrong today:**
- the thrust curve is invented (about 60% of a real cartridge's impulse)
- μ = 0.010 and I = 1.39e-7 kg·m² are placeholders (`physics_contract`)
- the centre-of-mass penalties are placeholders

### 12.3 Noise: what it is and how to measure it properly

**Definition:** noise is the scatter of race time for geometrically near-identical cars, for example skins 0.01 mm apart, whose true drag differs by far less than the scatter.

**Procedure:**
1. Build n ≥ 16 cars on a fine ladder of skin offsets.
2. Fit a straight line of T against offset (the true trend).
3. Take the residual SD as σ.

Report a 95% interval for σ from the chi-square distribution. With n = 8 that's [0.66σ̂, 2.03σ̂], which is too wide; with n = 16 it's [0.74σ̂, 1.55σ̂].

**Sources, in expected order of size:**
1. Remeshing: snappyHexMesh topology changes with any geometry change.
2. The averaging window.
3. Unconverged iterations.

**Why 0.3 ms:** Part 5 keeps a step only if the best of about 10 candidates beats the current car by 2 × noise.
- At σ = 1 ms the chance that pure noise passes that test is about 30%.
- At σ = 0.3 ms with a 2 ms floor it's below 1% (see Part 5, section 12.2).
- So σ ≤ 0.3 ms is what makes a 1 to 2 ms real gain trustworthy.

**Fix ladder, with the reason for each step:**
1. **Longer averaging:** the standard error falls as 1/√N_eff.
2. **A fixed background mesh and fixed snap settings:** removes topology changes from the background.
3. **Mesh morphing for small moves:** move the existing surface points by the shape change instead of re-snapping. With the same topology, remesh noise is zero by construction. In OpenFOAM: a `displacementLaplacian` motion solver with the boundary displacement set from the new STL.
4. **Surface layers:** wall shear is better resolved, but layer collapse can add noise.
5. **More iterations:** only if the drift gate fails.

### 12.4 Benchmarks

**Ahmed body:**
- Generic car-like body: length 1.044 m, width 0.389 m, height 0.288 m, rounded front, rear slant at 25° or 35°, on stilts 50 mm above the floor.
- Experiment: Ahmed, Ramm & Faltin (SAE 840300, 1984) at 60 m/s (Re about 4.3 × 10⁶ on length).
- Look up and cite the published drag coefficients (commonly quoted near 0.29 at 25° and 0.26 at 35°; **verify from the source**).
- Run it at that Reynolds number with our solver settings, our turbulence model and our mesh rules scaled to the body.
- RANS is known to miss the 25° case's partly attached slant flow, so 35° is the pass case.

**Grid convergence** (Roache's GCI), on three meshes with refinement ratio r:
- observed order p = ln((f₃ − f₂)/(f₂ − f₁)) / ln r
- GCI_fine = 1.25 · |(f₁ − f₂)/f₁| / (r^p − 1)
- Report p, the GCI and the extrapolated value.

**Second benchmark at our Reynolds number** (about 3 × 10⁵): pick one with published drag at that Re, and say why it suits a small, sharp-edged ground vehicle. Avoid a smooth sphere, because the drag crisis sits near this Re.

### 12.5 The ranking test, warm start and long runs

**Ranking:**
- 20 cars, each on the search mesh and the fine mesh.
- Spearman ρ ≥ 0.9.
- Sign agreement ≥ 90% for every pair more than 3 ms apart on the fine mesh. That gap is about 3σ at today's noise, so the fine-mesh order is itself trustworthy.

**Warm start:**
- `mapFields -consistent` (the same mesh recipe) or `-mapMethod` from a neighbour's converged fields into the new case.
- Pass: |D_warm − D_cold| < the noise, and at least 30% fewer iterations to reach the convergence gates.

**Long runs:**
- Write time directories every N iterations.
- Shortly before the 6 h limit (`timeout-minutes` 350), tar the case (mesh + latest time) and upload it as an artifact.
- The next job downloads it and restarts with `startFrom latestTime`.
- Pass: a chained run matches an unbroken run within 0.1% in drag, on a case short enough to also run unbroken.
- Or use a **Codespace** with no 6 h limit (section 9), once its idle timeout has been tested.

### 12.6 Making the race model real

**Thrust curve:**
- A load cell sampled at ≥ 1 kHz over the about 0.5 s burn, several cartridges, averaged.
- Store it as CSV with the same columns as today (time, force, CO2 mass), and refit the RBF.
- Report the impulse and compare it with the invented curve.

**Rolling friction:**
- **Roll-down test:** a car released on a ramp at angle θ settles to a constant speed when μ ≈ tan θ (ignoring drag at low speed).
- **Or coast-down:** fit the deceleration a = μg + D(v)/m.

**Wheel inertia:** from CAD (`wheel.mean_inertia_kg_m2`, already measured from the mesh) or a spin-down test.

**Tether drag:** a small constant force. Measure it, or bound it and say so.

**Model vs track:**
- For cars with known CAD and timed runs: compare the model time with the track time.
- Over 3% error means the model's trade-offs can't be trusted. Find which input causes it.

### 12.7 Integration (exact hand-offs)

**In, from Part 4:**
- `car_half.stl` (metres, y ≥ 0, solids named `car`, `wheelF`, `wheelR`)
- `mass_report.json`: `car_weight_kg` including the empty cartridge shell, `com_mm`, wheel inertia

**Out:**
- `stopwatch.json` (section 6)
- `compare(car_a, car_b) -> (dT, sd)`. **Design:** run both on the same machine type with the same mesh recipe. The sd comes from the measured noise σ: sd = σ·√2 for one run each, or the pooled repeats.

**Give Part 3:** the converged primal case directory, so the adjoint runs on exactly the same mesh and flow.

### 12.8 Known failure modes

| Symptom | Read | Usual cause |
| --- | --- | --- |
| stderr > 1% | `CFDHealthReport` | too short a window, or vortex shedding (a steady solver can't converge on unsteady flow) |
| drift > 2% | force history | not enough iterations |
| drag doubles | `_assert_watertight_stl` and the half-car check | a full car fed as a half car |
| no ground effect | domain z_min | the lower wall not at the track |
| a timeout at 6 h | the job log | fine or resolved meshes: chain them, or use a Codespace |
