# Rule map: 2026-27 Technical Regulations vs the referee

Source: `STEM Racing Professional Class Tech Regs 2026-2027.pdf` (text: `regulations_text_2026-27.txt`), read in full 2026-11-09.
Code read: `part5-simulation/legality.py` (the referee) and the Part 4 gates (`wings.py`, `nose.py`, `assembly.py`, `beam_support.py`), which the referee copies in as `P4.<gate>`.

All limits are absolute (T2.7.1): 48.0 g passes, 47.9 g fails. No rule gives a measuring tolerance unless stated. PP = proportional penalty (T2.5.2).

**Status key**
- `checked`: the referee measures it on the final meshes or files (key in `legality.json`).
- `gate only`: checked only through a Part 4 gate (`P4.*`), worked out while building the part, often from the design value, not measured from outside. Not independent.
- `constant`: compared on a fixed design value, not measured.
- `by construction`: true because of how the car is built; nothing checks it.
- `not checkable`: the model cannot test it; reason given.
- `GAP`: should be checked and is not. Listed at the end with a proposed fix.

## Article T1: definitions (p7-14)

| id | page | short text | limit | check | status |
| --- | --- | --- | --- | --- | --- |
| T1.1 | 7-8 | Only the listed components; one 8 g cartridge | - | parts list in `assembly.json` | by construction (see T3.3) |
| T1.2 | 8 | Fully assembled car = no cartridge, on 4 wheels | - | definition | not checkable: definition |
| T1.3 | 8 | Body = one piece of block material behind Ref A | - | `T4.1_single_body` | checked (via T4.1) |
| T1.4 | 8 | Chamber bounded only by body | - | `T5.5_wall` (partly) | see T5.5 |
| T1.5 | 9 | Wing defined by span, chord, thickness | - | definition | not checkable: definition |
| T1.6.1-3 | 10 | Wing supports and end plate definitions | - | definition | not checkable: definition |
| T1.7 | 10 | Nose cone only forward of Ref A | - | `T8.2_nose_overhang`, `T8.5.1_*` | checked (via T8) |
| T1.8 | 10 | Wheel definition | - | definition | not checkable: definition |
| T1.9 | 10 | Wheel supports inside the wheel cylinder | - | `P4.T7.12.1_*` | gate only (see T7.12.1) |
| T1.10 | 10 | Tether guide fully surrounds the line | - | guide is a closed ring | by construction (see T6.3) |
| T1.11 | 10 | Finish and decals count in dimensions | - | - | not checkable: paint and decals not modelled (user, 2026-11) |
| T1.12 | 11 | Logo decal 30 x 15 mm | 30 x 15 mm | `T4.6_logo_decal_room` | checked (via T4.6) |
| T1.13 | 11 | Hand finishing kept to a minimum | - | - | not checkable: process |
| T1.14 | 11 | Made from the official Model Block | 223 x 65 x 50 | `block_body_inside_official_block`, `block_length/width/height` | checked |
| T1.15 | 11 | Engineering drawings | - | - | not checkable: documentation |
| T1.16 | 12 | Renderings | - | - | not checkable: documentation |
| T1.17.1-3 | 12-13 | Reference planes; Ref A 16.0 ahead of front axle, Ref B 16.0 behind rear | 16.0 mm | used as `ref_a = x_front - 16`, `ref_b = x_front + W + 16` in `check` | checked (used by every T8/T9 check) |
| T1.18 | 13 | Anything else is an additional component | - | see T3.3 | by construction |
| T1.19 | 13 | "Normal" definition | - | definition | not checkable: definition |
| T1.20 | 13 | Cartridge, see Appendix vi | - | `T5.6_protrusion` uses 64.5 mm min length | constant |
| T1.21 | 14 | Halo mandatory, pocket for a 6.35 mm ball | - | `T4.4.4_halo_fits_pocket` | checked (fit); see T4.4.1 |
| T1.22 | 14 | Ballast only in the container under the halo | - | `T1.22_ballast_capacity` | checked (capacity only; location by construction) |

## Article T2: general principles (p15-17)

| id | page | short text | limit | check | status |
| --- | --- | --- | --- | --- | --- |
| T2.1-T2.4 | 15 | Documents, interpretation, amendments, classes | - | - | not checkable: administrative |
| T2.5 | 15 | Penalties; PP list: T3.4, T3.5, T3.6, T3.7, T5.2, T5.6, T7.2-T7.5, T7.11, T8.6, T9.5.1-4 | per mm / g | every numeric check reports a margin | checked (margins reported) |
| T2.6 | 16 | No rulings before the event | - | - | not checkable: administrative |
| T2.7.1 | 16 | Limits are absolute | - | `_entry`: pass if margin >= -1e-6 | checked |
| T2.7.2 | 16 | Measured incl. paint/decals; some with cartridge in | - | - | see T3.5, T3.7, T5.2, T5.4, T7.11 |
| T2.7.3 | 16 | Official scales | - | - | not checkable: process |
| T2.8-T2.10 | 16-17 | Benefit of doubt, spirit, originality | - | - | not checkable: judge's call |

## Article T3: fully assembled car (p19-21)

| id | page | short text | limit | tolerance | check | status |
| --- | --- | --- | --- | --- | --- | --- |
| T3.1.1-4 | 19 | CAD/CAM, CNC body, hologram sticker, both cars identical | - | - | - | not checkable: process |
| T3.2.1-2 | 19 | Safe construction | - | - | - | not checkable: judge's call |
| T3.3 | 19 | Only T1.1 components | - | - | - | GAP (small): no check lists the parts |
| T3.4 | 19 | Total width | 65.0-85.0 mm, PP | - | `T3.4_width_min`, `T3.4_width_max` | checked |
| T3.5 | 19 | Total height (cartridge in, on 4 wheels) | <= 65.0 mm, PP | - | `T3.5_height` | checked (without cartridge; it sits below the top) |
| T3.6 | 20 | Total weight, no cartridge | >= 48.0 g, PP | - | `T3.6_mass` | checked (needs `mass_state`) |
| T3.7 | 20 | Track clearance, all but wheels | >= 1.5 mm, PP | - | `T3.7_clearance`; also `P4.T3.7_*` | checked |
| T3.8 | 20 | Nothing swapped during racing | - | - | - | not checkable: process |
| T3.9, T3.9.1-2 | 20-21 | Spare parts | - | - | - | not checkable: process |

## Article T4: body (p22-25)

| id | page | short text | limit | check | status |
| --- | --- | --- | --- | --- | --- |
| T4.1 | 22 | One piece of block behind Ref A, holding cargo and chamber | 1 piece | `T4.1_single_body` | checked |
| T4.2 | 22 | Virtual cargo wholly inside the body, between the axle lines | figure sizes | `T4.2_cargo_inside_body` | checked (inside); GAP: "between the axle lines" not checked |
| T4.3 | 22 | Cargo shown on drawings | - | - | not checkable: documentation |
| T4.4.1 | 23 | Halo used unchanged | - | - | GAP (small): halo file not compared with the official file |
| T4.4.2 | 23 | Halo seen from front and side | no obstruction | `T4.4.2_halo_seen_from_front`, `T4.4.2_halo_seen_from_side` | checked |
| T4.4.3 | 23 | Halo seen from top (helmet excepted) | no obstruction | `T4.4.3_halo_seen_from_top` | checked |
| T4.4.4 | 24 | Notch centre 34.0 +-1.0 above track; pocket floor at 24.0, flat | 34.0 +-1.0 mm | `T4.4.4_pocket_floor` (uses +-0.5), `T4.4.4_halo_fits_pocket` | checked (stricter than the rule) |
| T4.4.5 | 24 | Halo load test, 2 kg | - | - | not checkable: physical test |
| T4.5 | 24 | Helmet used unchanged | - | part of the halo file | GAP (small): as T4.4.1 |
| T4.6 | 25 | Logo decal wholly on each side, 100% seen from the side | 30 x 15 mm | `T4.6_logo_decal_room` | checked |
| T4.7 | 25 | Team number on the body between halo and Ref A, seen from above; also "A"/"B" | text >= 8.0 mm | `T4.7_team_number_room` (9 x 15 window) | checked (number); the A/B letter shares the window, not checked apart |
| T4.8 | 25 | Decal thickness | <= 0.5 mm | - | not checkable: decals not modelled (user) |

## Article T5: cartridge chamber (p26-27)

| id | page | short text | limit | check | status |
| --- | --- | --- | --- | --- | --- |
| T5.1 | 26 | Chamber diameter | 18.0-18.5 mm | `T5.1_diameter_min/max` (`chamber_measures`: sections of the milled body along the minimum depth) | checked |
| T5.2 | 26 | Cartridge centre above track | 30.0-40.0 mm, PP | `T5.2_height_min/max` | checked |
| T5.3 | 26 | Chamber depth, rim to end | 45.0-58.0 mm | `T5.3_depth_min/max` | checked |
| T5.4 | 26 | Chamber angle to track | -3 to +3 deg | `T5.4_angle` | checked |
| T5.5 | 26 | 3.0 mm block wall round the chamber; chamber not cut by anything | >= 3.0 mm | `T5.5_wall` (on the milled file, round the measured chamber) | checked (wall); GAP: "bore not intersected" not checked |
| T5.6 | 27 | Cartridge sticks out >= 5.0 mm, visible all round | >= 5.0 mm, PP | `T5.6_protrusion` (64.5 mm shortest cartridge minus measured depth) | checked (protrusion); GAP: "visible all round" not checked |
| - | - | A chamber exists, open at the back | - | `T5_chamber_found` | checked |

## Article T6: tether guides (p28-29)

| id | page | short text | limit | check | status |
| --- | --- | --- | --- | --- | --- |
| T6.1 | 28 | Exactly 2 guides, within 10.0 mm of each axle line; line passes only through them | 0-10.0 mm | `T6.1_two_guides`, `T6.1_front/rear_guide_position` (from the measured wheel axles), `T6.1_tether_line_clear` | checked |
| T6.2 | 28 | Guide hole (3.5 and 6.0 mm tools) | 3.5-6.0 mm | `T6.2_front/rear_hole_min/max` (widest circle through the hole) | checked |
| T6.3 | 29 | Guide closed and robust; 200 g test | - | - | not checkable: physical test (closed ring by construction) |

## Article T7: wheels and supports (p30-34)

| id | page | short text | limit | check | status |
| --- | --- | --- | --- | --- | --- |
| T7.1 | 30 | 4 wheels, 2 front 2 rear, opposing wheels share an axis | 4 | - | by construction; GAP (small): not counted |
| T7.2.1 | 30 | Front inner wheel gap | >= 38.0 mm, PP | `T7.2_front_gap` (the car's wheels) | checked |
| T7.2.2 | 30 | Rear inner wheel gap | >= 30.0 mm, PP | `T7.2_rear_gap` | checked |
| T7.3 | 30 | Wheelbase | 120.0-140.0 mm, PP | `T7.3_W_min`, `T7.3_W_max` (between the measured wheel centres) | checked |
| T7.4.1 | 31 | Front contact width, no chamfers/fillets | >= 13.0 mm, PP | `T7.4_front_contact_width` (`wheel_measures`: tread at full radius, on the wheel file) | checked |
| T7.4.2 | 31 | Rear contact width | >= 17.0 mm, PP | `T7.4_rear_contact_width` | checked |
| T7.5 | 31 | Wheel diameter, each wheel | 28.0-32.0 mm, PP | `T7.5_front/rear_diameter_min/max` (on the wheel files) | checked |
| T7.6 | 31 | All 4 wheels touch across full width | - | - | by construction; GAP (small) |
| T7.7 | 31 | Even diameter across contact width | - | - | by construction (team wheel file) |
| T7.8 | 31 | Wheels turn freely on a 3 deg slope | <= 3 deg | - | not checkable: friction/bearing, physical |
| T7.9.1 | 32 | Clear zone ahead of front wheels | >= 5.0 mm | `T7.9.1_zone_clear`; `P4.T7.9.1_zone_ahead_of_wheel` | checked (zone shape from Part 1) |
| T7.9.2 | 32 | Clear zone behind front wheels | figure | `T7.9.2_zone_clear` | checked (zone shape from Part 1) |
| T7.9.3 | 32 | Clear zone ahead of rear wheels | figure | `T7.9.3_zone_clear` | checked (zone shape from Part 1) |
| T7.9.4 | 32 | Clear zone behind rear wheels | >= 5.0 mm | `T7.9.4_zone_clear` | checked (zone shape from Part 1) |
| T7.10 | 33 | Wheels seen from the side (supports excepted) | no obstruction | `T7.10_wheelF_seen_from_side`, `T7.10_wheelR_seen_from_side` | checked |
| T7.11 | 33 | Front wheels hidden from front only up to 20 mm | <= 20 mm, PP | `T7.11_front_wheel_seen_from_front` | checked |
| T7.12.1 | 33 | Supports only inside the wheel cylinder | - | `P4.T7.12.1_*_support_in_cylinder`, `P4.T7.12.1_*_pod_in_cylinder` | gate only |
| T7.12.2 | 34 | Supports shown on drawings | - | - | not checkable: documentation |
| T7.13 | 34 | Claw clearance at the wheel's inner corner (figure); 100 g test | 1.5 x 1.5 mm | `T7.13_front_claw_clearance`, `T7.13_rear_claw_clearance` | checked (clearance); load test not checkable |

## Article T8: nose, front wing, end plates, supports (p35-40)

| id | page | short text | limit | check | status |
| --- | --- | --- | --- | --- | --- |
| T8.1 | 35 | Shown on drawings | - | - | not checkable: documentation |
| T8.2 | 35 | Nose overhang ahead of Ref A | <= 40.0 mm | `T8.2_nose_overhang`; `P4.T8.2_*` | checked |
| T8.3 | 35 | Front wing has leading and trailing edge across its span | - | NACA section | by construction |
| T8.4 | 35 | Wings rigid | - | - | not checkable: judge's call |
| T8.5.1 | 36 | Nose and wing support ahead of Ref A, <= 25.0 high, <= 15 each side | 25.0 / 15 mm | `T8.5.1_nose_z`, `T8.5.1_nose_half_width` (body, printed nose and wing mount ahead of Ref A) | checked |
| T8.5.2 | 37 | Front wing ahead of Ref A; <= 20.0 high where wider than 15 each side | 20.0 mm | `T8.5.2_front_wing_ahead_of_ref_A`, `T8.5.2_front_wing_height_outboard` | checked |
| T8.5.3 | 37 | End plates outside min span, <= 10.0 wide, <= 25.0 high outside the wheels | 10.0 / 25.0 mm | `T8.5.3_endplate<i>_width/outside_span/height` | checked (when end plates exist) |
| T8.6.1 | 38 | Front span; 1 x 50, or 2 x 25 where another part passes through the wing | >= 50.0 mm, PP | `T8.6.1_front_span` (wing mesh; the mount and nose split it) | checked |
| T8.6.2 | 39 | Front chord, horizontal, throughout the span; up to 3 vanes, overlapping | 15.0-25.0 mm, PP | `T8.6.2_front_chord_min/max`, `T8.6.2_front_vanes_overlap` (9 sections across the span) | checked |
| T8.6.3 | 39 | Front thickness throughout span | 2.0-6.0 mm, PP | `T8.6.3_front_thickness_min/max` (widest circle in each section) | checked |
| T8.7 | 40 | 5.0 mm clear air from the wing to any part or the track (5 mm ball on 2 mm rod) | >= 5.0 mm | `T8.7_front_wing_clear_air_all_parts`; `P4.T8.7_*` | checked (nearest distance from 3000 surface points; wing within 5 mm sideways of the nose left out as the fillet) |
| T8.8 | 40 | Front wing seen from the front | no obstruction | `T8.8_front_wing_seen_from_front` | checked |

## Article T9: rear wing and supports (p41-45)

| id | page | short text | limit | check | status |
| --- | --- | --- | --- | --- | --- |
| T9.1 | 41 | Shown on drawings | - | - | not checkable: documentation |
| T9.2 | 41 | Rear wing has leading and trailing edge | - | NACA section | by construction |
| T9.3 | 41 | Rigid | - | - | not checkable: judge's call |
| T9.4.1 | 41 | Whole rear wing and support behind Ref B | - | `T9.4.1_rear_wing_behind_ref_B` | checked |
| T9.4.2 | 41 | Rear overhang behind Ref B | <= 40.0 mm | `T9.4.2_rear_overhang`; `P4.T9.4.2_overhang` | checked |
| T9.4.3 | 41 | Highest point behind Ref B | <= 65.0 mm | `P4.T9.4.3_height`; covered by `T3.5_height` | checked (via T3.5) |
| T9.5.1 | 42 | Rear span, single unbroken | >= 50.0 mm, PP | `T9.5.1_rear_span` (its own pylon under it does not break it; any other part through it does) | checked |
| T9.5.2 | 42 | Rear chord, horizontal, throughout span; up to 2 vanes, overlapping | 15.0-25.0 mm, PP | `T9.5.2_rear_chord_min/max`, `T9.5.2_rear_vanes_overlap` | checked |
| T9.5.3 | 43 | Rear thickness | 2.0-6.0 mm, PP | `T9.5.3_rear_thickness_min/max` | checked |
| T9.5.4 | 43 | Height change along the top of the span | <= 15.0 mm, PP | `T9.5.4_rear_height_deviation` | checked |
| T9.6 | 44 | 5.0 mm clear air from the rear wing | >= 5.0 mm | `T9.6_rear_wing_clear_air_all_parts`; `P4.T9.6_clear_air_body` | checked |
| T9.7 | 45 | Rear wing seen from the front | no obstruction | `T9.7_rear_wing_seen_from_front`; `P4.T9.7_front_view` | checked |

## Article T10 (p45)

| id | page | short text | limit | check | status |
| --- | --- | --- | --- | --- | --- |
| T10.1 | 45 | Only the cartridge touches the launch pods | - | - | not checkable: race process |

## Appendices (p47-57)

| id | page | short text | limit | check | status |
| --- | --- | --- | --- | --- | --- |
| App. i | 47 | Start box, finish beam about 7 mm above the track | ~7 mm | - | not checkable: information (end-plate advice only) |
| App. ii | 48 | Model Block dimensions | figure | `official_block_mm`, `block_body_inside_official_block` | checked (sizes from Part 1's contract) |
| App. iii | 49-50 | Front wing examples | - | see T8.6 | information |
| App. iv | 51-52 | Rear wing examples | - | see T9.5 | information |
| App. v | 53 | Multi-vane overlap | - | single vane + flap | by construction; GAP (small) if multi-vane is ever searched |
| App. vi | 54 | Cartridge size; 28.9-29.4 g | 65.0 -0.5 mm long | `CARTRIDGE_LENGTH_MIN_MM = 64.5` | constant |
| App. vii | 54 | Halo deceleration system | - | - | not checkable: information |
| App. viii | 55 | Component identification example | - | - | not checkable: documentation |
| App. ix | 56-57 | Halo pocket (6.35 ball, 3.175 deep), floor 24.0, notch 10.0 above floor; cargo may share the ballast container, not the halo pocket | 24.0 mm | `T4.4.4_pocket_floor`, `T4.4.4_halo_fits_pocket`, `T4.2_cargo_inside_body` | checked (pocket box from Part 1) |

## Referee checks that are not one rule

| key | what it guards |
| --- | --- |
| `attached_<part>` | every printed part touches the body (within 0.3 mm) |
| `block_length`, `block_width`, `block_height` | body behind Ref A fits 223 x 65 x 50 |
| `block_body_inside_official_block` | milled body inside the real block (bore and slot cut) |
| `manufactured_files_measurable` | every made file is a solid (else the car is rejected) |
| `manufacture_files_are_solids` | one closed solid per part, re-read from disk |
| `fit_printed_parts_clear_of_foam` | printed parts do not overlap the foam |
| `nose_has_tenon` | the nose has a glued tenon, not only a surface bond |
| `mesh_longest_edge`, `mesh_slivers_body`, `mesh_slivers_printed` | mesh quality of the made files |
| `P4.machining_*_foam_over_pod` | foam left over the wheel-support channel |

## Gaps found (to fix in Steps 2-3, each with a fail test)

Numeric rules not measured independently (gate only or constant): these need a referee measurement on the final mesh, not a copy of the Part 4 design value.
1. **T8.6.1 / T9.5.1 span**: design value only. Measure the shortest of LE/TE/top/bottom span on the wing mesh.
2. **T8.6.2 / T9.5.2 chord**: Part 4 gate only. Measure the horizontal chord along the span on the mesh.
3. **T8.6.3 / T9.5.3 thickness**: design value only. Measure on mesh sections.
4. **T9.5.4 height deviation**: hard-coded 0. Measure the top surface along the span.
5. **T8.5.2 front wing ahead of Ref A and <= 20 mm outboard**, **T8.5.3 end plates**, **T9.4.1 rear wing behind Ref B**: gate only. Measure from bounding boxes of the wing meshes.
6. **T8.5.1 printed nose and mount**: the referee measures only body material ahead of Ref A, not the printed nose or mount meshes.
7. **T7.2, T7.4, T7.5 wheels**, **T7.12.1 supports in cylinder**: gate only. Measure on the wheel and support meshes.
8. **T6.1 guide position, T6.2 hole size**: constants. Measure on the guide meshes.
9. **T5.1-T5.3, T5.6**: constants. Measure the bore on the milled body file.
10. **T5.4 chamber angle**: missing. Add (constant 0 deg today; measure the bore axis).
11. **T7.3 wheelbase**: taken from the layout value. Measure from the wheel meshes.

Rules not checked at all (non-numeric or small):
12. **T4.2**: cargo between the axle lines.
13. **T5.5**: nothing inside the bore.
14. **T5.6**: cartridge visible all round behind the car.
15. **T3.3 / T7.1 / T7.6**: list of parts, 4 wheels, all 4 touching.
16. **T4.4.1 / T4.5**: halo and helmet file unchanged (compare with the official file).

Independence (Step 3): the referee takes the Model Block, bore, chamber axis, wheel inner faces, T7.9 zone shapes, cargo sizes and the halo pocket from Part 1 (`geometry_contract`, `wheel_visibility_zones`, `virtual_cargo`, `halo_pocket`).

## Count

Counted from the tables above (some rows group sub-rules, e.g. T3.1.1-4):
- 112 rows, covering every rule in T1-T10 and appendices i-ix. Each has a check or a stated reason; none is blank.
- checked 40 (several with a partial gap noted), gate only 17, constant 6, by construction 9, not checkable 31, GAP 5, pointer to another row ("see", "information") 4.
- Numeric rules not yet measured independently by the referee: 11 groups (list above).
