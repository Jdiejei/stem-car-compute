"""Part 4 lab: the 3 carved canary cars whose milled body was not one closed solid
(linkedin run 42655282327). Rebuilds each on that run's code (6aa47975d7bbebb9fccaa3ef164b574a0bb73b8d) and describes its files."""
import subprocess
import sys

subprocess.run(["git", "checkout", "6aa47975d7bbebb9fccaa3ef164b574a0bb73b8d", "--", "../part1-simulation", "../part4-simulation", "../part5-simulation"], check=True)
for seed, i in ((43825, 16), (43836, 13), (43806, 20)):
    print(f"\n===== car {seed}/{i}", flush=True)
    p = subprocess.run([sys.executable, "-W", "ignore", "checks/stress_cars.py", "--seed", str(seed), "--carve",
                        "--only", str(i), "--out", f"../out/{seed}_{i}"], capture_output=True, text=True)
    print("\n".join(l for l in p.stdout.splitlines() if l.startswith("car")))
    print("\n".join(p.stderr.splitlines()[-8:]))
