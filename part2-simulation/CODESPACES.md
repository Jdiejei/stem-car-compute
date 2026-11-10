# Running a job on a GitHub Codespace (tested by Part 2, 2026-11-09/10)

For jobs that GitHub Actions can't run: over the 6 h job limit, or on an account
whose Actions are blocked. Each account has about 120 core-hours a month free.
Use the 4-core machine (`standardLinux32gb`; only 2- and 4-core were offered).
**Delete the codespace as soon as its results are fetched:** a stopped or idle one
still counts storage, and a running one counts 4 core-hours per hour.

Proven:
- A 2.8 h OpenFOAM job (Ahmed, resolved mesh) ran to the end with nobody attached.
- Two 5+ h fine-mesh cars are running the same way now.

Idle timeout: a codespace stops after `--idle-timeout` (240 min at most) without
activity. A detached job does NOT count as activity, so check in with `gh codespace
ssh` at least every 3 h while it runs.

```bash
export GH_TOKEN=$(gh auth token --user <account>)          # never gh auth switch
# 1. create (from the account's fork of stem-racing-car; branch as needed)
gh codespace create -R <account>/stem-racing-car -b main -m standardLinux32gb \
   --idle-timeout 240m --retention-period 24h -d "<what>"     # prints the codespace NAME
CS=<name>
# 2. write the job script on it and start it DETACHED
gh codespace ssh -c $CS -- 'cat > /tmp/run.sh <<"EOF"
#!/bin/bash
set -x
exec > /workspaces/job.log 2>&1
cd /workspaces/stem-racing-car
sudo apt-get update -q && sudo apt-get install -y -q libopengl0 libglu1-mesa libegl1 libgl1 libgomp1 libxkbcommon0
curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
sudo apt-get install -y -q openfoam2412-default
# the image has Python 3.14; the pinned packages want 3.11
python3 -m pip install --break-system-packages -q uv && uv venv -p 3.11 /workspaces/py && . /workspaces/py/bin/activate
uv pip install -q numpy==2.4.6 scipy==1.17.1 pandas trimesh==5.2.0 scikit-image shapely rtree==1.4.1 mapbox-earcut manifold3d==3.5.4 fast_simplification==0.2.0 jax jaxlib matplotlib pymeshlab==2025.7.post1
export OMPI_MCA_hwloc_base_use_hwthreads_as_cpus=1 OMPI_MCA_rmaps_base_oversubscribe=1
echo START_RUN; date -u
<YOUR COMMAND, e.g. cd part5-simulation && python run_car.py ... --np 4>
echo EXIT $?; date -u
EOF
chmod +x /tmp/run.sh; setsid nohup /tmp/run.sh >/dev/null 2>&1 </dev/null &'
# 3. check (also keeps it awake): at least every 3 h
gh codespace ssh -c $CS -- 'grep -E "START_RUN|EXIT" /workspaces/job.log; tail -2 /workspaces/job.log'
# 4. fetch results
gh codespace cp -c $CS -e 'remote:/workspaces/<result file>' ./<local dir>/
# 5. delete straight away
gh codespace delete -c $CS -f
```

Gotchas found:
- The codespace login shell `cd`s to the workspace, so a stage run with `bash -lc` ran
  outside its case. part2's `openfoam_case._run` now `cd`s into the case by absolute path.
- Start the job with `setsid nohup ... &` so it survives the ssh session.
- Log the core-hours per account on the board: 4 cores × wall hours.
