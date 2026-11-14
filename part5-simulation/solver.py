"""
solver.py -- search for the fastest car the settings can describe, on its own.

Slopes for every setting come from one of two places:

  adjoint   one solve gives the drag's sensitivity on every surface; how each setting
            moves those surfaces (geometry only, no CFD) turns that into a slope for
            every setting. Fast, but only used if it passes the gradient check.
  measured  a pair of real CFD cars per setting. Slow, but true.

The slope is corrected for the car staying at 48.2 g: growing one part means the skin
shrinks everywhere to pay for it.

    start     every chain's car measured twice, from different starting cars
    check     (once) adjoint slopes against direct CFD on 16 settings: sets the slope
              sign, or falls back to measured slopes if they do not agree
    round     slopes -> steps of several sizes -> each built, re-sized, rule-checked and
              measured by direct CFD. A chain moves only if the best beats its own repeat
              measurement by more than the noise; else it tries smaller steps, then stops.

The solver only proposes: direct CFD decides, so a wrong slope costs time, not a worse car.

This CANNOT prove a global maximum. `report` says what it can establish: a peak nothing
nearby beats by more than the noise, and how many independent starts reached it. And it
is a maximum of the model, not of the real car.

    python solver.py init --chains 8
    python solver.py jobs                     # what to run next, as JSON
    python solver.py adjoint --chain 0 --out o/
    python solver.py eval --id 3 --out o/
    python solver.py advance results/         # read the results, plan the next jobs
    python solver.py report
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import random
import tempfile
from pathlib import Path

import numpy as np

import paths  # noqa: F401
import pattern

HERE = Path(__file__).resolve().parent
STATE = HERE / "search" / "solver_state.json"
BATCH = HERE / "search" / "solver_batch.json"
STEPS_MM = (0.5, 1.0, 2.0, 4.0)      # the typical surface move of one step
# Floor on a car's noise. A repeat of one car gets the same mesh and agrees to 0.01 ms, which
# says nothing. Measured at skins 0.01 mm apart (start car, 8 CFD runs each, 7 Nov 2026), standard
# deviation and end to end: 1.3 and 4.3 ms with layers, 2.2 and 7.6 with "better" layers, 1.0 and
# 3.3 with none, as each new mesh lands differently on the body. 5000 iterations changed nothing.
NOISE_S = 1.0e-3
# The search's mesh: no layers, 1000 iterations. Drag there is settled to 0.06 ms against 2000,
# a car takes 30 minutes rather than 75, and the noise is lowest. Its drag differs from the layered
# mesh by 5 %, and the fine mesh lies between the two: the winner must be confirmed on a finer one.
SEARCH_CFD = {"layer_overrides": {"nSurfaceLayers": 0}}
SEARCH_ITERS = 1000
MAX_ROUNDS = 25
FOAM_G_CM3 = 0.163
MIN_SCALE = 0.2                      # stop once steps are this small and still gain nothing
# Measured slopes are 222 cars a round, 7 hours on 40 machines, on differences mostly under
# the mesh noise. So a failed gradient check stops the solver and asks, instead of starting them.
AUTO_MEASURED = False
MEASURED_CHAINS = 1                  # measured slopes cost ~170 cars a round: only the best chain
# The adjoint must earn its place: the bar was set before seeing any result.
CHECK_MIN_SIGN_SHARE = 0.8
CHECK_MIN_CORRELATION = 0.8


def pb():
    import param_body
    return param_body


def body_settings() -> list:
    return pattern.LOFT + [f"mode{i}" for i in range(pb().N_MODES)] + list(pattern.FLOOR)


def all_settings() -> list:
    return body_settings() + list(pattern.PARTS) + list(pattern.LAYOUT)


# ------------------------------------------------------------------- slopes
def _phi(params: dict, P: np.ndarray, a: float, b: float, skin_mm: float = 0.0) -> np.ndarray:
    return pb().phi_mm(pb().BodyParams.from_dict(params), P[:, 0], np.abs(P[:, 1]), P[:, 2], a, b, skin_mm=skin_mm)


def _span(d: dict, name: str, h: float) -> tuple:
    lo, hi = pattern.bounds(name)
    v = pattern.get(d, name)
    up, down = min(v + h, hi), max(v - h, lo)
    return up, down


def surface_speed(d: dict, name: str, P: np.ndarray, grad_norm: np.ndarray, a: float, b: float,
                  skin_mm: float = 0.0) -> np.ndarray:
    """Outward move of each surface point, mm per unit of this setting. phi is negative
    inside, so raising phi at a point pulls the surface in past it."""
    up, down = _span(d, name, 0.1 * pattern.step0(name))
    if up == down:
        return np.zeros(len(P))
    dphi = (_phi(pattern.put(d, name, up)["params"], P, a, b, skin_mm)
            - _phi(pattern.put(d, name, down)["params"], P, a, b, skin_mm)) / (up - down)
    return -dphi / grad_norm


def _soft_volume(phi: np.ndarray, dv: float) -> float:
    """Both halves, mm3, from a 2 mm grid: a 2 mm blur of the surface, so a small move
    changes it smoothly. Only used for the mass balance, not for the mass itself."""
    return float(np.clip(0.5 - phi / 2.0, 0.0, 1.0).sum()) * dv * 2.0


def body_slopes(d: dict, skin_mm: float, P: np.ndarray, s: np.ndarray, a: float, b: float) -> dict:
    """{setting: {dD, dV, speed}} from the sensitivity s (N per mm of outward move) at
    surface points P, plus "_skin": the same for growing the whole body by 1 mm."""
    eps = 0.1
    base = d["params"]
    grad = np.stack([(_phi(base, P + e, a, b, skin_mm) - _phi(base, P - e, a, b, skin_mm)) / (2 * eps)
                     for e in np.eye(3) * eps], axis=1)
    grad_norm = np.maximum(np.linalg.norm(grad, axis=1), 0.2)
    # Only where the drawn shape IS the surface: masks, pockets and the chamber wall stay put.
    active = np.abs(_phi(base, P, a, b, skin_mm)) < 1.0
    X, Y, Z = (g.ravel() for g in np.meshgrid(np.arange(a, b, 2.0), np.arange(0.0, 34.0, 2.0),
                                              np.arange(2.0, 52.0, 2.0), indexing="ij"))
    params = pb().BodyParams.from_dict(base)

    def field(p):
        return pb().phi_mm(p, X, Y, Z, a, b, skin_mm=skin_mm)

    out = {"_skin": {"dD": float((s * active).sum()),
                     "dV": (_soft_volume(field(params) - 0.5, 8.0) - _soft_volume(field(params) + 0.5, 8.0)),
                     "speed": 1.0}}
    for name in body_settings():
        v = surface_speed(d, name, P, grad_norm, a, b, skin_mm) * active
        up, down = _span(d, name, 0.5 * pattern.step0(name))
        dV = 0.0
        if up != down:
            hi_p = pb().BodyParams.from_dict(pattern.put(d, name, up)["params"])
            lo_p = pb().BodyParams.from_dict(pattern.put(d, name, down)["params"])
            dV = (_soft_volume(field(hi_p), 8.0) - _soft_volume(field(lo_p), 8.0)) / (up - down)
        out[name] = {"dD": float((s * v).sum()), "dV": dV,
                     "speed": float(np.sqrt(np.mean(v[active] ** 2))) if active.any() else 0.0}
    return out


def part_slopes(car: dict, P: dict, s: dict, body_stl: str) -> dict:
    """{setting: {dD, dV, speed}} for the printed parts. Each part is rebuilt with the
    setting moved, and a surface point's signed distance to the new part is its move:
    exact geometry, no CFD. dV is the foam volume with the same mass as the plastic."""
    import trimesh
    import assembly as p4
    import joints
    import run_car as rc

    def build(parts):
        a = rc.parse_args(["--out", "x"] + [f for k, flag in pattern.PART_FLAGS.items() if parts.get(k)
                                            for f in (flag, json.dumps(parts[k]))])
        td = tempfile.mkdtemp()
        return p4.build(car["W"], car["x_front"], car["d_halo"], body_stl, td, **rc.part4_kwargs(a))

    def loaded(asm):
        return {x["name"]: trimesh.load(x["stl"], force="mesh") for x in asm["extra_surfaces"]
                if not x["name"].startswith("wheel")}

    base = loaded(build(car["parts"]))
    out = {}
    d = {"params": car["params"], "parts": car["parts"]}
    for name in pattern.PARTS:
        up, down = _span(d, name, 0.5 * pattern.step0(name))
        v0 = pattern.get(d, name)
        moved = up if up != v0 else down
        if moved == v0:
            continue
        try:
            new = loaded(build(pattern.put(d, name, moved)["parts"]))
        except (ValueError, SystemExit):
            continue                            # no slope for a part that will not build
        dD, dV, moves = 0.0, 0.0, []
        for pname, m in new.items():
            if pname not in P or not m.is_volume:
                continue
            # P is in mm and the part in metres. Unconverted, each point sat about 100 "m"
            # from its part and every printed setting read about 1e9, which sank the check.
            dist = trimesh.proximity.signed_distance(m, P[pname] / 1e3) * 1e3   # + = inside the new part
            dD += float((s[pname] * dist).sum())
            moves.append(dist)
            rho = joints.DENSITY_G_CM3.get(pname, 1.24)
            if base[pname].is_volume:
                dV += 2 * (abs(m.volume) - abs(base[pname].volume)) * 1e9 * rho / FOAM_G_CM3
        step = moved - v0
        speed = float(np.sqrt(np.mean(np.concatenate(moves) ** 2))) / abs(step) if moves else 0.0
        out[name] = {"dD": dD / step, "dV": dV / step, "speed": speed}
    return out


def constant_mass(slopes: dict) -> dict:
    """What a setting is worth once the skin has grown or shrunk to keep the mass: its
    own drag change, less the drag of the skin that pays for its volume."""
    skin = slopes["_skin"]
    per_mm3 = skin["dD"] / max(skin["dV"], 1.0)
    return {k: v["dD"] - per_mm3 * v["dV"] for k, v in slopes.items() if not k.startswith("_")}


def plan_step(d: dict, g: dict, speeds: dict, move_mm: float) -> dict:
    """The car moved downhill so the typical surface move is move_mm. Settings are
    weighted by their natural step, so mm and degrees can be compared."""
    raw = {k: -(pattern.step0(k) ** 2) * g[k] for k in g}
    total = math.sqrt(sum((raw[k] * speeds.get(k, 0.0)) ** 2 for k in g))
    if total <= 0.0:
        return d
    out = d
    for k, r in raw.items():
        lo, hi = pattern.bounds(k)
        out = pattern.put(out, k, float(np.clip(pattern.get(out, k) + r * move_mm / total, lo, hi)))
    return out


# ------------------------------------------------------------------- gradient check
def check_settings(adjoint: dict) -> list:
    """The 12 settings the adjoint says move drag most in one step. Two cars a step apart
    differ by 4 mN from the mesh alone (see NOISE_S), which swamped a fixed list: of its
    11 usable settings, only 2 stood clear of that. A wrong adjoint still fails here, since
    settings it overrates will measure small."""
    return sorted(adjoint, key=lambda n: -abs(adjoint[n] * pattern.step0(n)))[:12]


def judge_check(direct: dict, adjoint_slopes: dict) -> dict:
    """direct: {setting: dD/dp measured by CFD}. Is the adjoint right, and which way up?"""
    names = [k for k in direct if k in adjoint_slopes and abs(direct[k]) > 0]
    a = np.array([adjoint_slopes[k] for k in names])
    b = np.array([direct[k] for k in names])
    if len(names) < 4 or a.std() == 0 or b.std() == 0:
        return {"passed": False, "sign": None, "n": len(names), "reason": "too few usable settings"}
    # Scale each setting by its step so one big-unit setting cannot decide the correlation.
    w = np.array([pattern.step0(k) for k in names])
    r = float(np.corrcoef(a * w, b * w)[0, 1])
    sign = 1.0 if r >= 0 else -1.0
    share = float(np.mean(np.sign(sign * a) == np.sign(b)))
    return {"passed": share >= CHECK_MIN_SIGN_SHARE and abs(r) >= CHECK_MIN_CORRELATION,
            "sign": sign, "sign_share": share, "correlation": r, "n": len(names)}


# ------------------------------------------------------------------- state
def random_start(seed: int) -> dict:
    """A different car per chain, so they can land on different peaks. Chain 0 is the
    start car; others move every setting within 30 % of its range."""
    d = {"params": pb().BodyParams().as_dict(), "parts": {}}
    if seed == 0:
        return d
    rng = random.Random(seed)
    for name in all_settings():
        lo, hi = pattern.bounds(name)
        v = pattern.get(d, name)
        d = pattern.put(d, name, float(np.clip(v + rng.uniform(-0.3, 0.3) * (hi - lo), lo, hi)))
    return d


def _case(i: int, chain: int, tag: str, d: dict, skin=None) -> dict:
    return {"id": i, "chain": chain, "tag": tag, "params": d["params"], "parts": d["parts"],
            "layout": d.get("layout", {}), "skin_mm": skin}


def _d(c: dict) -> dict:
    return {"params": c["car"]["params"], "parts": c["car"]["parts"], "layout": c["car"].get("layout", {})}


def _layout_args(layout: dict) -> list:
    return [x for k, flag in pattern.LAYOUT_FLAGS.items() if k in layout for x in (flag, str(layout[k]))]


def _save(state: dict, cases: list) -> None:
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1, default=float))
    BATCH.write_text(json.dumps({"round": state["round"], "phase": state["phase"], "cases": cases},
                                indent=1, default=float))


def _start_cases(state: dict) -> list:
    cases = []
    for c in state["chains"]:
        if c["T"] is None and not c["stopped"]:
            cases += [_case(len(cases), c["id"], "current", _d(c)), _case(len(cases) + 1, c["id"], "repeat", _d(c))]
    return cases


def init(chains: int) -> dict:
    state = {"round": 0, "phase": "start", "slopes": "adjoint", "sign": None, "next_seed": chains, "check": None,
             "chains": [dict(id=i, car=random_start(i), T=None, noise=None, scale=1.0, stopped=None,
                             history=[], skin_mm=None, starts=1) for i in range(chains)]}
    _save(state, _start_cases(state))
    return state


def jobs() -> dict:
    """What to run next: {"kind": "adjoint"|"eval"|"done", "ids": [...]}."""
    state = json.loads(STATE.read_text())
    live = [c["id"] for c in state["chains"] if not c["stopped"]]
    if not live or state["phase"] == "done":
        return {"kind": "done", "ids": []}
    if state["phase"] in ("check_adjoint", "adjoint"):
        return {"kind": "adjoint", "ids": live if state["phase"] == "adjoint" else live[:1]}
    return {"kind": "eval", "ids": [c["id"] for c in json.loads(BATCH.read_text())["cases"]]}


# ------------------------------------------------------------------- one machine
def evaluate(case_id: int, out: Path) -> dict:
    """One car: rule-checked and measured by direct CFD; sized to 48.2 g unless the case
    fixes the skin, as a gradient measurement must."""
    import run_car as rc
    B = json.loads(BATCH.read_text())
    c = next(x for x in B["cases"] if x["id"] == case_id)
    res = __import__("os").environ.get("P5_RES", "")      # required: no default mesh (user 2026-11-13)
    if res not in ("fine", "resolved"):
        raise SystemExit(f"P5_RES={res!r}: loop timings run on fine or resolved only")
    args = ["--out", str(out), "--cfd", "--cfd-if-legal", "--res", res, "--np", "2",
            "--cfd-iters", str(SEARCH_ITERS), "--cfd-json", json.dumps(SEARCH_CFD),
            "--body-json", json.dumps(c["params"])]
    args += _layout_args(c.get("layout", {}))
    for part, flag in pattern.PART_FLAGS.items():
        if c.get("parts", {}).get(part):
            args += [flag, json.dumps(c["parts"][part])]
    if c.get("skin_mm") is not None:
        args += ["--skin-mm", str(c["skin_mm"])]
    row = dict(c, ok=False, round=B["round"], phase=B["phase"])
    try:
        S = rc.main(args)
        failed = S["legality"]["summary"]["failed"]
        if c.get("skin_mm") is not None:          # a fixed skin is not sized
            failed = [f for f in failed if f != "T3.6_mass"]
        row.update(failed=failed, mass_g=S["mass"]["manufactured_mass_g"], skin=S["body"]["build"].get("skin_offset_mm"))
        ci = S.get("cfd_initial")                 # none if the car broke a rule: see --cfd-if-legal
        if ci is not None:
            row.update(T_s=ci["T_at_target_s"], D20_N=ci["D20_N"], converged=ci["converged"],
                       ok=bool(ci["converged"] and not failed))
    except (Exception, SystemExit) as exc:  # noqa: BLE001 -- a car that fails is a result
        row["error"] = f"{type(exc).__name__}: {exc}"[:300]
    out.mkdir(parents=True, exist_ok=True)
    (out / f"car_{B['round']}_{B['phase']}_{case_id}.json").write_text(json.dumps(row, indent=1, default=str))
    return row


def adjoint(chain_id: int, out: Path) -> dict:
    """One adjoint solve on a chain's car; writes every setting's slope."""
    import assembly as p4
    import openfoam_adjoint as oa
    import run_car as rc
    state = json.loads(STATE.read_text())
    c = next(x for x in state["chains"] if x["id"] == chain_id)
    out.mkdir(parents=True, exist_ok=True)
    argv = ["--out", str(out), "--body-json", json.dumps(c["car"]["params"])] + _layout_args(c["car"].get("layout", {}))
    for part, flag in pattern.PART_FLAGS.items():
        if c["car"].get("parts", {}).get(part):
            argv += [flag, json.dumps(c["car"]["parts"][part])]
    if c["skin_mm"] is not None:
        argv += ["--skin-mm", str(c["skin_mm"])]
    a = rc.parse_args(argv)
    geom, info, asm = rc.build_car(a, out, **rc.part4_kwargs(a))
    b = rc.make_bindings(a, out, asm, seed_geom=copy.deepcopy(geom))
    gate = b.run_quality_gates(copy.deepcopy(geom), "initial", str(out / "gates"))
    if not gate.stl_half_path:
        raise SystemExit(f"the car failed the CFD gate: {gate.failure_reason}")
    ref_a, ref_b = a.x_front - 16.0, a.x_front + a.W + 16.0
    frame = (((ref_a - 41.0) / 1e3, 0.0, 0.0), ((ref_b + 41.0) / 1e3, 0.0435, 0.066))
    cfg = oa.AdjointRunConfig(resolution="medium", n_subdomains=4, domain_reference_bounds=frame,
                              extra_surfaces=p4.extra_surfaces_from(str(Path(asm["_dir"]) / "assembly.json")),
                              sensitivity_on_all_parts=True, layer_overrides=SEARCH_CFD["layer_overrides"])
    raw = oa.invoke_adjoint(str(gate.stl_half_path), str(Path(oa.__file__).resolve().parent / "cfd_case_template"),
                            cfg, by_patch=True)
    # raw: d(half-car kinematic drag)/d(move in m) per point. To N per mm of move, whole
    # car: x rho x 2 x 1e-3. Only its pattern and the sign the check sets are relied on.
    scale = cfg.air_density_kgm3 * 2.0 * 1e-3
    P = {k: v[0] * 1e3 for k, v in raw.items()}
    s = {k: v[1] * scale for k, v in raw.items()}
    d = _d(c)
    skin = (info.get("build") or {}).get("skin_offset_mm") or 0.0
    slopes = body_slopes(d, skin, P["car"], s["car"], ref_a, a.x_front + a.W + 56.0)
    slopes.update(part_slopes(dict(d, W=a.W, x_front=a.x_front, d_halo=a.d_halo), P, s, str(out / "body_half.stl")))
    row = {"chain": chain_id, "round": state["round"], "phase": state["phase"], "skin_mm": skin, "slopes": slopes}
    (out / f"slopes_{state['round']}_{chain_id}.json").write_text(json.dumps(row, indent=1, default=float))
    return row


# ------------------------------------------------------------------- advancing
def _car_rows(root: Path, B: dict) -> list:
    rows = [json.loads(p.read_text()) for p in Path(root).rglob("car_*.json")]
    return [r for r in rows if r["round"] == B["round"] and r["phase"] == B["phase"]]


def _slope_rows(root: Path, state: dict) -> dict:
    rows = (json.loads(p.read_text()) for p in Path(root).rglob("slopes_*.json"))
    return {r["chain"]: r for r in rows if r["round"] == state["round"] and r["phase"] == state["phase"]}


def _steps_from(state: dict, chain_slopes: dict) -> None:
    """chain_slopes: {chain: (g, speeds)} -> measure every live chain's current car and steps."""
    cases = []
    for c in state["chains"]:
        if c["stopped"]:
            continue
        cases += [_case(len(cases), c["id"], "current", _d(c)), _case(len(cases) + 1, c["id"], "repeat", _d(c))]
        if c["id"] in chain_slopes:
            g, speeds = chain_slopes[c["id"]]
            for move in STEPS_MM:
                m = move * c["scale"]
                cases.append(_case(len(cases), c["id"], f"step{m:g}", plan_step(_d(c), g, speeds, m)))
        if state["slopes"] == "adjoint":
            # The adjoint cannot price moving whole parts, so the layout is tried directly:
            # six more cars, judged like any other step. Measured slopes already cover it.
            d = _d(c)
            for n in pattern.LAYOUT:
                lo, hi = pattern.bounds(n)
                for sign in (1, -1):
                    v = float(np.clip(pattern.get(d, n) + sign * c["scale"] * pattern.step0(n), lo, hi))
                    if v != pattern.get(d, n):
                        cases.append(_case(len(cases), c["id"], f"step {n}={v:g}", pattern.put(d, n, v)))
    state["phase"] = "steps"
    _save(state, cases)


def _measure_plan(state: dict) -> None:
    """Measured slopes: every setting up and down, at a fixed skin, on the best chains."""
    live = sorted((c for c in state["chains"] if not c["stopped"]), key=lambda c: c["T"])
    for c in live[MEASURED_CHAINS:]:
        c["stopped"] = "dropped: measured slopes only afford the best chains"
    cases = []
    for c in live[:MEASURED_CHAINS]:
        d = _d(c)
        cases += [_case(len(cases), c["id"], "base", d, c["skin_mm"]), _case(len(cases) + 1, c["id"], "base_repeat", d, c["skin_mm"])]
        for n in all_settings():
            for sign in (1, -1):
                lo, hi = pattern.bounds(n)
                v = float(np.clip(pattern.get(d, n) + sign * c["scale"] * pattern.step0(n), lo, hi))
                if v != pattern.get(d, n):
                    cases.append(_case(len(cases), c["id"], f"{n}|{v}", pattern.put(d, n, v), c["skin_mm"]))
    state["phase"] = "measure"
    _save(state, cases)


def _next_round(state: dict) -> None:
    if all(c["stopped"] for c in state["chains"]) or state["round"] >= MAX_ROUNDS:
        for c in state["chains"]:
            c["stopped"] = c["stopped"] or "round limit"
        state["phase"] = "done"
        _save(state, [])
    elif state["slopes"] == "measured":
        if AUTO_MEASURED:
            _measure_plan(state)
        else:
            state["phase"] = "done"
            _save(state, [])
    else:
        state["phase"] = "adjoint"
        _save(state, [])


def _gradient_from_pairs(mine: list, base_values: dict) -> tuple:
    """Measured dT/dp per setting from a screen's rows, and a speed of 1 mm per step."""
    base = [r["T_s"] for r in mine if r["tag"] in ("base", "base_repeat") and r["ok"]]
    if not base:
        return None
    T0 = float(np.mean(base))
    g = {}
    pts = {}
    for r in mine:
        if "|" in r["tag"] and r["ok"]:
            n, v = r["tag"].split("|")
            pts.setdefault(n, []).append((float(v), r["T_s"]))
    for n, vals in pts.items():
        vals.sort()
        if len(vals) == 2:                     # both sides measured
            g[n] = (vals[1][1] - vals[0][1]) / (vals[1][0] - vals[0][0])
        else:                                  # at a bound: one side, against the base car
            v0, T1 = vals[0]
            v_base = base_values.get(n)
            if v_base is not None and v0 != v_base:
                g[n] = (T1 - T0) / (v0 - v_base)
    return g, {n: 1.0 / pattern.step0(n) for n in g}


def advance(root: Path) -> str:
    state = json.loads(STATE.read_text())
    B = json.loads(BATCH.read_text())
    phase = state["phase"]
    msg = []

    if phase == "start":
        rows = _car_rows(root, B)
        for c in state["chains"]:
            if c["T"] is not None or c["stopped"]:
                continue
            mine = [r for r in rows if r["chain"] == c["id"]]
            good = [r for r in mine if r["ok"]]
            if len(good) == 2:
                c["T"] = float(np.mean([r["T_s"] for r in good]))
                c["noise"] = max(abs(good[0]["T_s"] - good[1]["T_s"]), NOISE_S)
                c["skin_mm"] = good[0].get("skin")
            elif c["starts"] < 4:
                c["starts"] += 1
                # An illegal random start: draw another. No result at all is a machine that
                # died, which says nothing about the car, so the same car runs again.
                if len(good) < len(mine):
                    c["car"] = random_start(state["next_seed"])
                    state["next_seed"] += 1
            else:
                c["stopped"] = "no legal start in 4 draws"
        pending = _start_cases(state)
        if pending:
            _save(state, pending)
            return f"redrawing {len(pending) // 2} illegal starts"
        if state["sign"] is None and state["slopes"] == "adjoint":
            state["phase"] = "check_adjoint"
            _save(state, [])
            return "starts measured; gradient check next"
        _next_round(state)
        return "starts measured"

    if phase == "check_adjoint":
        rows = _slope_rows(root, state)
        c = next(x for x in state["chains"] if not x["stopped"])
        if c["id"] not in rows:                 # the adjoint itself failed: that is a verdict
            state.update(slopes="measured", check={"passed": False, "reason": "adjoint solve failed"})
            _next_round(state)
            return "adjoint solve failed: using measured slopes"
        state["check"] = {"adjoint": {k: v["dD"] for k, v in rows[c["id"]]["slopes"].items() if not k.startswith("_")},
                          "chain": c["id"], "skin": c["skin_mm"]}
        d = _d(c)
        cases = [_case(0, c["id"], "base", d, c["skin_mm"]), _case(1, c["id"], "base_repeat", d, c["skin_mm"])]
        for n in check_settings(state["check"]["adjoint"]):
            for sign in (1, -1):
                lo, hi = pattern.bounds(n)
                v = float(np.clip(pattern.get(d, n) + sign * pattern.step0(n), lo, hi))
                if v != pattern.get(d, n):
                    cases.append(_case(len(cases), c["id"], f"{n}|{v}", pattern.put(d, n, v), c["skin_mm"]))
        state["phase"] = "check_cars"
        _save(state, cases)
        return f"check: {len(cases)} cars"

    if phase == "check_cars":
        rows = [r for r in _car_rows(root, B) if r["ok"]]
        pts = {}
        for r in rows:
            if "|" in r["tag"]:
                n, v = r["tag"].split("|")
                pts.setdefault(n, []).append((float(v), r["D20_N"]))
        direct = {n: (max(p)[1] - min(p)[1]) / (max(p)[0] - min(p)[0]) for n, p in pts.items() if len(p) == 2}
        verdict = judge_check(direct, state["check"]["adjoint"])
        state["check"] = dict(verdict, direct=direct, adjoint=state["check"]["adjoint"])
        if verdict["passed"]:
            state["sign"] = verdict["sign"]
            msg.append(f"gradient check PASSED: {verdict}")
        else:
            state["slopes"] = "measured"
            msg.append(f"gradient check FAILED, using measured slopes: {verdict}")
        _next_round(state)
        return "\n".join(msg)

    if phase == "adjoint":
        rows = _slope_rows(root, state)
        slopes = {}
        for c in state["chains"]:
            if not c["stopped"] and c["id"] in rows:
                sl = rows[c["id"]]["slopes"]
                g = {k: state["sign"] * v for k, v in constant_mass(sl).items() if k in all_settings()}
                slopes[c["id"]] = (g, {k: v["speed"] for k, v in sl.items() if not k.startswith("_")})
        _steps_from(state, slopes)
        return f"steps planned for {len(slopes)} chains"

    if phase == "measure":
        rows = _car_rows(root, B)
        slopes = {}
        for c in state["chains"]:
            if not c["stopped"]:
                got = _gradient_from_pairs([r for r in rows if r["chain"] == c["id"]],
                                          {n: pattern.get(_d(c), n) for n in all_settings()})
                if got:
                    slopes[c["id"]] = got
        _steps_from(state, slopes)
        return f"steps planned from measured slopes for {len(slopes)} chains"

    if phase == "steps":
        rows = _car_rows(root, B)
        for c in state["chains"]:
            if c["stopped"]:
                continue
            mine = [r for r in rows if r["chain"] == c["id"]]
            base = [r["T_s"] for r in mine if r["tag"] in ("current", "repeat") and r["ok"]]
            if not base:
                c["stopped"] = "its current car no longer measured legal and converged"
                msg.append(f"chain {c['id']}: {c['stopped']}")
                continue
            T0 = float(np.mean(base))
            noise = max(abs(base[0] - base[-1]), NOISE_S)
            steps = [r for r in mine if r["tag"].startswith("step") and r["ok"]]
            best = min(steps, key=lambda r: r["T_s"]) if steps else None
            entry = {"round": state["round"], "T": T0, "noise": noise}
            if best is not None and best["T_s"] < T0 - 2 * noise:
                c["car"] = {"params": best["params"], "parts": best["parts"], "layout": best.get("layout", {})}
                c["T"], c["skin_mm"], c["noise"] = best["T_s"], best.get("skin"), noise
                entry.update(accepted=best["tag"], gain_ms=(T0 - best["T_s"]) * 1e3)
                msg.append(f"chain {c['id']}: accepted {best['tag']}, {(T0 - best['T_s']) * 1e3:.2f} ms")
            else:
                c["T"], c["noise"], c["scale"] = T0, noise, c["scale"] * 0.5
                entry["accepted"] = None
                msg.append(f"chain {c['id']}: no measurable gain, step x{c['scale']:g}")
                if c["scale"] < MIN_SCALE:
                    c["stopped"] = "peak: no step beat the noise, down to a fifth of the size"
            c["history"].append(entry)
        state["round"] += 1
        _next_round(state)
        return "\n".join(msg)

    return f"nothing to advance in phase {phase}"


def report() -> str:
    state = json.loads(STATE.read_text())
    done = sorted((c for c in state["chains"] if c["T"] is not None), key=lambda c: c["T"])
    check = state.get("check") or {}
    L = [f"Round {state['round']}, phase {state['phase']}, slopes from: {state['slopes']}.",
         f"Gradient check: passed={check.get('passed')}, sign share={check.get('sign_share')}, "
         f"correlation={check.get('correlation')}."]
    for c in done:
        L.append(f"  chain {c['id']}: {c['T']:.5f} s, {len(c['history'])} rounds, "
                 f"{'stopped: ' + c['stopped'] if c['stopped'] else 'running'}")
    if done:
        best = done[0]
        peaks = [c for c in done if str(c["stopped"]).startswith("peak")]
        same = [c for c in peaks if c["T"] - best["T"] < 2 * max(c["noise"] or NOISE_S, NOISE_S)]
        L.append(f"{len(peaks)} chains reached a peak; {len(same)} are within the noise of the best ({best['T']:.5f} s).")
        if peaks:
            miss = 1.0 - 0.05 ** (1.0 / len(peaks))
            L.append(f"If all those peaks agree: with 95 % confidence, a new random start has under a "
                     f"{100 * miss:.0f} % chance of finding a better one. That is a statistical statement.")
        L.append("Not established: that this is the global maximum, or that it is the fastest real car. "
                 "This is a model time, on the settings the solver can reach.")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    i_ = sp.add_parser("init")
    i_.add_argument("--chains", type=int, default=8)
    sp.add_parser("jobs")
    a_ = sp.add_parser("adjoint")
    a_.add_argument("--chain", type=int, required=True)
    a_.add_argument("--out", required=True)
    e_ = sp.add_parser("eval")
    e_.add_argument("--id", type=int, required=True)
    e_.add_argument("--out", required=True)
    v_ = sp.add_parser("advance")
    v_.add_argument("root")
    sp.add_parser("report")
    a = ap.parse_args(argv)
    if a.cmd == "init":
        init(a.chains)
    elif a.cmd == "jobs":
        print(json.dumps(jobs()))
    elif a.cmd == "adjoint":
        adjoint(a.chain, Path(a.out))
    elif a.cmd == "eval":
        print(json.dumps(evaluate(a.id, Path(a.out)), default=str)[:800])
    elif a.cmd == "advance":
        print(advance(Path(a.root)))
    else:
        print(report())


if __name__ == "__main__":
    main()
