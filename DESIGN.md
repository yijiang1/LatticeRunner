# Lattice Runner — Game Design Document

**Status:** single-file prototype at [`index.html`](index.html) — open directly in a browser, no build step. Served into the PtychoHub Kids section through a proxy route, the same way [TheBrilliantFacility](https://github.com/yijiang1/TheBrilliantFacility) and [GravityQuest](https://github.com/yijiang1/GravityQuest) are — except this repo is private for now, so that route uses the authenticated GitHub Contents API and is session-gated, and the card is contributor-only. Pushing to `main` updates the game for contributors; making the repo public is what ships it to everyone.

## Concept

A 2D platformer where the player controls a scanning probe moving across an atomic lattice reconstructed via electron ptychography. Atom columns are jump platforms. The signature mechanic: atoms start as faint unresolved ghosts and only become solid once the probe lingers nearby long enough — mirroring how a real ptychography reconstruction is built up scan-position by scan-position, not revealed all at once.

The goal is not a numeric completion percentage. A true reconstruction image sits behind a fog layer; resolving atoms punches holes in the fog, so the payoff is literally watching the hidden picture emerge as you play.

The tension comes from the central bargain of electron microscopy: **to see an atom you must hit it with electrons, and the electrons destroy it.** You carry one specimen's worth of dose. Proximity is what resolves an atom and proximity is what knocks it out — the same act, two consequences — so there is no separate "hazard" system bolted on. How much of the picture you get to see before the beam runs out is the score.

Inspired by the research pass on platformer design (Celeste, Super Mario Bros, Spelunky, Hollow Knight, Braid — see conversation history / commit context): movement forgiveness is the invisible foundation, goals should be concrete rather than an abstract meter, and risk/reward needs to be tightly coupled rather than decorative.

---

## Core Mechanics

### The probe (player character)
Drawn as the ray diagram it actually is: a cone of electrons converging from the column above down to a bright focal spot, with the transmitted cone diverging below toward the detector. The focal spot is the body; the cones read as a silhouette. Electron streaks fall down the illumination cone and visibly converge on the spot, Airy rings sit around it because a focused probe is a diffraction pattern rather than a dot, and an anamorphic flare crosses it so it reads as the brightest thing on screen.

Character comes from cheap tricks rather than a sprite — the rig leans into horizontal velocity, the focal spot squashes and stretches with speed and squashes again on a hard landing, a short comet trail shows where it has been, and an eye tracks the facing direction. It runs orange instead of blue whenever it's close to knocking something out, so the avatar visibly *heats up* while doing damage. Blanked, the cones drop to a dashed outline and the spot collapses to a closed-aperture ring — dim, but never so dim that the avatar gets lost against the lattice.

### Movement
Standard run/jump with forgiveness layered on top so input feels answered rather than frame-perfect:
- **Coyote time** (0.12s) — jump still fires briefly after walking off a ledge
- **Jump buffering** (0.12s) — a jump press slightly before landing queues up and fires on landing
- **Variable jump height** — releasing jump early clamps upward velocity, giving a short hop instead of the full arc
- **Heavier fall gravity** (1.6×) — snappier descent than the rise

Horizontal motion is acceleration plus damping, and the damping is resolved
per second (`vx *= FRICTION ** (dt·60)`), not per frame. A raw per-frame
`vx *= 0.82` made top speed a function of refresh rate — 237 px/s at 30 Hz,
118 at 60, 49 at 144 — and above about 90 Hz the probe could no longer clear a
lattice gap at all, so the game was quietly unplayable on a 120 Hz display.
Top speed is now ~120 px/s from 30 Hz to 144 Hz. Note that `MOVE_SPEED` (260)
is the *clamp*, not the speed: damping settles the probe at about half of it.

Coyote time and jump buffering are both in, and measurement says neither one
matters here (sweeping coyote from 0.08s to 0.35s moved unpractised survival by
less than the noise). What decides whether a jump lands is the gap geometry,
not the input window — see **Balance** below.

### Resolve-by-proximity
Each unresolved atom has a `resolveProgress` (0–1) that:
- builds while the probe is within `RESOLVE_RADIUS` (150px), taking `RESOLVE_TIME` (0.5s) of continuous presence to complete
- decays at 2.2× the build rate if the probe leaves before finishing (leaving early costs real progress, not just time)
- once complete, permanently resolves the atom into a solid platform and erases a patch of fog around it on the reveal image

This is deliberately not instant — it's the "cost" that turns exploration into a pace-yourself decision rather than a free trigger.

Visually an unresolved site is a *speckle cloud that has not converged*: a ring of dots scattered around the column, collapsing onto it as `resolveProgress` builds, wrapped by an arc that fills to show the dwell. Completing it snaps the sphere in with an overshoot, a spark burst and an expanding ring. Nothing about the site is a placeholder dashed circle any more — it is a reconstruction mid-convergence.

### Dose (self-inflicted risk)
The probe deposits dose into **every** atom within its radius, not just the one it's standing on, at a rate falling off with distance the way a real beam profile does:

```
rate = DOSE_PEAK / (1 + d² / DOSE_FALLOFF²)
```

Standing on an atom is simply the closest you can physically get, so it cooks fastest (~2s for carbon); a neighbour one lattice spacing away still takes dose, at roughly 1/2.5 the rate. Dose anneals back off slowly (`DOSE_ANNEAL`) once the atom is out of the beam.

Past its tolerance an atom **knocks out**, and knock-out is permanent. The column flickers for `DAMAGE_COLLAPSE / vib` seconds — long enough to feel it go, and to give anyone standing on it a moment to leave — and then it is gone for the rest of the run. A displaced atom does not return to its site, so the lattice you damage stays damaged: the platform is not coming back, and the hole you made is now part of the level.

This is dynamic, not pre-scripted — any atom can become a hazard, including one the probe is still trying to resolve. Dose renders as an arc winding around the column, a gauge filling toward knock-out, and it renders on unresolved atoms too, so you can watch yourself damaging the thing you're mid-way through revealing. Knock-out cracks the sphere, kicks a shockwave and embers out of it, and shakes the frame. Mid-collapse the column reads warm and dashed; once emptied it goes cool and hollow, so "still going" and "gone for good" never look alike.

### The dose budget
A run carries `DOSE_BUDGET` (100) units of dose, before instrument upgrades. A real beam runs at fixed current, so total electrons spent is just beam-on time — the budget is a clock, but one the player controls rather than one that runs regardless.

100 is measured, not estimated — see **Balance** below.

A run ends one of three ways, none of which is a failure screen — the report and the upgrade pick are earned by what the scan recovered, however it stopped:
- **Reconstruction complete** — every atom resolved; the card reports what it cost.
- **Beam exhausted** — the electrons ran out; the card reports how much of the lattice you got, and points at blanking.
- **Probe lost** — the probe dropped past the lattice and struck the detector.

The third one is the only ending the player can walk into by mistake, and it exists because the geometry leaves no alternative: the lowest atom row sits ~470px above the detector plane and a full jump clears ~114px, so there is no climbing back. Before it was added, landing down there was an unrecoverable soft-lock — you walked around the detector until the beam ran out. Knocking out a column you are standing on is now a real way to fall, which is what ties the dose model to the platforming.

### Balance (measured)

Numbers below come from driving the shipped simulation headlessly at a fixed
timestep, not from a feel judgement.

**What coverage costs.** Riding a single row from one end of the specimen to the
other converges about half the lattice, because the 150px scan field reaches one
row up and one row down:

| Route | Reconstructed | Electrons |
|---|---|---|
| row 1, end to end | 49% | 20 |
| row 4, end to end | 55% | 20 |
| rows 1 then 4 | **100%** | **38** |
| rows 1, 3, 5 | 100% | 58 |
| every row | 100% | 59 |

So a perfectly routed full clear costs 38 electrons. Naive play — running right
and jumping at every edge, which drifts diagonally down the lattice and re-scans
ground it has already covered — costs about 1.1 electrons per percent, so ~110
for the same result. `DOSE_BUDGET` of 100 sits deliberately between the two:
sloppy routing tops out short of a complete reconstruction, and row discipline
and blanking are what close the gap. At the old 130 even naive play cleared the
lattice with headroom, which made the game's central resource inert.

**Knock-out only punishes lingering.** Sweeping a row at top speed (~120 px/s)
destroys nothing. At 90 px/s it costs 4 columns; at 70 px/s, 45. The dose model
therefore reads as "keep scanning, don't hover", which is the intended lesson.

**Difficulty is gap geometry, not input forgiveness.** Columns sit on a 90px
pitch. At the original collision width (`r · 2.3` ≈ 40px) the gaps were 50px —
wider than the platforms — while a full jump from a 40px runway reaches only
65–75px, and a missed platform is fatal because unconverged lattice is not
solid and cannot be converged on the way past (0.5s of dwell, under 0.3s in
range at fall speed). Widening the standable top measurably lengthens an
unpractised run:

| Collision width | Platform / gap | Median survival |
|---|---|---|
| `r · 2.3` | 40 / 50px | 3.1s |
| `r · 2.7` (current) | 46 / 44px | 3.9s |
| `r · 3.2` | 55 / 35px | 5.4s |
| `r · 3.6` | 62 / 28px | 6.4s |

2.7 is the current setting: it is still visibly a lattice of separate columns,
and the standable top stays inside the glow already drawn around each sphere.
There is clearly more room to move here if playtesting says the opening is
still too steep.

**Where runs actually end.** Every measured run ends on *Probe lost*, not on
*Beam exhausted* — a weak run spends 8–25 of its 100 electrons before falling.
The budget only becomes the binding constraint once a player can reliably stay
on the lattice. That is the honest state of the difficulty curve.

### Beam blanking
Holding **SHIFT** blanks the beam: no budget drain, no dose deposited, no resolving, and atoms anneal while it's off. Blanking is a standard technique for beam-sensitive specimens, and it turns the budget from pure pressure into a routing decision — cross ground you've already scanned for free, unblank when you actually want to see something. The illumination circle vanishing is the whole visual read: no circle, no cost.

### Wobble hazard (scan-drift)
A subset of atoms drift vertically once resolved. They are telegraphed in motion language rather than by hue: before they are ever solid their speckle cloud is stretched vertically and a dashed vertical track runs through the site, and once solid they carry a ghosted motion smear of where they just were. Colour stays reserved for element identity, which is what frees violet for the nitrogen dopant. Distinct from overexposure damage — this is environmental, not caused by the player.

### Vacancies (gaps)
Missing lattice sites are simply absent — no platform, so the player must jump the gap. Most are single-width; one location has two adjacent vacancies for a wider chasm, giving jump-distance variety.

### Mass-driven behaviour
One number, `vibrationFactor = √(reference_mass / element_mass)`, drives three separate visible behaviours:

1. **Wobble speed and amplitude** — lighter atoms jiggle faster and wider (a nod to Debye–Waller thermal motion).
2. **How long a knocked-out column survives** — `DAMAGE_COLLAPSE / vib`, so a light carbon is out of its site in half a second and gold hangs on four times as long.
3. **Dose tolerance** — `doseLimit = DOSE_LIMIT / vib`, i.e. proportional to √mass. Knock-on damage displaces a light carbon long before it budges a gold atom.

The third is what makes it matter for play rather than flavour: the gold dopant is a genuinely safe place to stand and think, and carbon is where you cannot dawdle. Real knock-on physics producing real level design for free.

### Curiosity content (dopants)
A few lattice sites are real dopant/defect elements (not the base carbon lattice), each with distinct color/size and a one-line real fact shown as a toast the first time it's resolved. These sit off the critical path so players who beeline the exit don't see them — reward for exploring, not a requirement.

---

## The Run Loop

A session is one run; the game is the sequence of them.

### Draft, not a shop
Every completed run ends in a draft: three instruments are offered, the player keeps **one**, and it applies permanently from the next session. No currency, no shop, no inventory to manage — one decision, taken while the scan report is still on screen.

### Picks are the score
How much of the lattice a run recovered decides how many picks it earns:

| Resolved | Picks |
|----------|-------|
| any      | 1 |
| ≥ 40%    | 2 |
| ≥ 70%    | 3 |

One pick is guaranteed so a bad run still moves you forward, and the thresholds mean the reward for playing well is *more choices*, not a bigger number. Picks bank in the save file, so closing the tab mid-draft doesn't lose them.

Abandoning a run with **R** earns nothing — credits only settle when the beam actually runs out or the lattice is fully phased. Without that, resolving the ten easy atoms near spawn and restarting would out-earn playing a full session.

### The upgrades
Seven lines, three levels each — 21 picks to max the instrument, so roughly 8–15 sessions. Every one is a real technique, because "how do you get more picture out of fewer electrons" is the actual subject of the game and the draft is where it gets taught.

| Code | Instrument | Scales | Why it's real |
|------|-----------|--------|---------------|
| 80 kV | Low-voltage column | `DOSE_LIMIT` ×1.3 → ×2.1 | Below carbon's knock-on threshold the beam stops displacing atoms |
| MSR | Mixed-state reconstruction | `RESOLVE_TIME` ×0.82 → ×0.55 | Modelling partial coherence converges from fewer scan positions |
| DED | Direct electron detector | `DOSE_BUDGET` +30 → +105 | Counting single electrons beats integrating a current |
| BLNK | Fast electrostatic blanker | `DOSE_ANNEAL` ×2 → ×4.2 | Microsecond blanking gives the specimen real rest |
| FOV | Wide-field scan coils | `RESOLVE_RADIUS` +26 → +88 | More columns per position — and more of them irradiated |
| CRYO | Cryogenic stage | wobble amplitude ×0.7 → ×0.3 | Cooling suppresses the thermal motion the drift hazard models |
| SPRS | Sparse scan strategy | `RESOLVE_DECAY_MULT` ×0.65 → ×0.3 | Smarter scan patterns keep partial information instead of discarding it |

FOV is the only one with a genuine downside, and the card says so: a wider field irradiates everything it takes in. That is the trade a real operator makes.

### What this fixes
`DOSE_BUDGET` at 130 made "reconstruction complete" close to unreachable — a known limitation below. The upgrade path is what makes it reachable: early sessions end in *beam exhausted* and the full clear is something the instrument eventually earns, rather than a win condition that was mis-set from the start.

### Persistence
`localStorage` under `latticeRunner.v1`, holding session count, banked picks, best percentage and upgrade levels. Reads and writes are wrapped — private mode and sandboxed iframes throw on access, and the game has to run there too, just without carrying progress. Levels are clamped on load, so a corrupted or hand-edited save can't put the instrument out of range.

---

## Visual System

The renderer is deliberately layered so that art direction and game logic stay separable — every pass below is additive polish over the same simulation.

**Palette.** One cool base (deep blue-black vacuum, cyan lattice) with warm accents reserved entirely for damage and dose. Nothing warm appears on screen unless the player is spending or destroying something, so heat is readable at a glance and never decorative. Element colour is identity only: carbon cyan, nitrogen violet, oxygen coral, gold amber.

**Atom shading.** Each column is a shaded sphere — key light upper-left, rim light wrapping the lower right, one specular hit, crisp edge — baked once per `(element, radius)` pair into a cached sprite, so 152 atoms cost 152 `drawImage` calls rather than 152 gradient constructions a frame. Halo strength scales with a per-element `z` weight standing in for Rutherford scattering, which is why gold glows hardest: physics, not art direction.

**Bloom.** Bright elements are accumulated into a quarter-resolution buffer and composited additively; the upscale supplies most of the blur for free, with a small `ctx.filter` blur on top where the browser supports it (feature-detected, and it degrades to a slightly harder bloom rather than breaking).

**The reveal image.** `renderTargetImage()` accumulates a scalar phase field from per-column Gaussians *plus the bonding network between nearest neighbours*, then maps it through a false-colour LUT and upsamples. The bonds are what make the uncovered picture read as a honeycomb lattice rather than a field of dots — the single biggest contributor to the reveal feeling like a reward.

**The fog.** Unresolved territory is not black, it is *unconverged*: dark speckle and coarse blotches, held a hair under opaque so the out-of-focus parallax plane behind still reads as depth without giving away the reconstruction.

**Depth.** Three parallax layers behind the world — a defocused plane of the crystal, tilted crystal-direction rules, and drifting dust. Dust is composited *above* the fog sheet, since anything drawn under a full-world fog layer is never seen.

**Post.** A slow raster line sweeps down the frame trailing a decaying glow (it is a scanning microscope), over device-pixel scanlines, animated grain and a vignette. The vignette warms and pulses as the specimen cooks or the budget runs low, so both alarms live at the edge of vision instead of as another number on the panel.

**Camera.** Smoothed, with look-ahead proportional to velocity, plus a short shake on knock-out.

**Instrumentation over decoration.** The dose radius is a rotating dashed circle with a hard edge, not a haze, so the boundary is measurable by eye. The standable surface of a sphere is drawn explicitly as a contact plane — but only for columns near the probe, because drawn on every column it stops being an affordance and starts looking like a scratch across the art.

**HUD.** System font stack (no network dependency), a glass panel with segmented tracks, tabular numerals, and an end card carrying a stat grid and a thumbnail of exactly how much of the phase image the run recovered.

**Resolution.** The canvas backing store is scaled by `devicePixelRatio` and the whole renderer works in CSS pixels, so nothing is soft on a retina display.

---

## Elements

| Symbol | Role | Mass (amu) | Vibration factor | Dose tolerance | Notes |
|--------|------|-----------|-------------------|----------------|-------|
| C | Base lattice | 12.011 | 1.00 | 2.0 | Everything not a vacancy or dopant. Knocks out in ~2s of standing |
| N | Dopant | 14.007 | 0.93 | 2.2 | "A single substituted nitrogen atom can change how an entire 2D material conducts electricity." |
| O | Dopant | 15.999 | 0.87 | 2.3 | "Oxygen dopants are light and hard to see with X-rays, but electron ptychography can resolve them directly." |
| Au | Dopant | 196.97 | 0.25 | 8.1 | Effectively a rest stop — 4× carbon's tolerance. "Gold sits far heavier than carbon; dense atoms scatter electrons more strongly and glow brighter in a real STEM image." |

`vibrationFactor(element) = √(ATOMIC_MASS.C / ATOMIC_MASS[element])`, defined once and reused for wobble kinematics, flicker rate, and dose tolerance.

---

## Data Contract

The lattice is generated synthetically today (`generateSyntheticLattice()`), but the shape a real ptychography reconstruction export should match to drop in without touching game logic is:

```js
{ x, y, element, intensity }
```

- `x, y` — lattice-unit coordinates, scaled to world pixels via `WORLD_SCALE`
- `element` — symbol string, looked up in `ATOMIC_MASS` for vibration behavior (unknown symbols fall back to a neutral factor of 1)
- `intensity` — 0–1, used as a rough proxy for platform size on non-dopant atoms

The `targetCanvas` reveal image (currently a procedurally rendered false-color composite) is the other swap point — once a real reconstruction image exists, it replaces the canvas drawing in `renderTargetImage()`.

---

## Current Level

Single hand-tuned level: a 26×6 atom grid with a gentle sine-wave vertical undulation (so it reads as terrain, not a flat strip) rather than a real reconstruction. Contains:
- A seeded survey scan: every column within `RESOLVE_RADIUS · 1.25` of the spawn (6 of 152) starts converged. One pre-resolved column was not enough — the first second of a run used to be unsurvivable in both directions. Step off the single spawn column and the probe fell through six rows of unconverged speckle to the detector; stand on it long enough to converge the row below and the column under you knocked out instead. The survey patch gives the opening both ground to step onto and ground to fall back to.
- Hard scan-field edges at the outermost columns, so the probe cannot run off the end of the specimen into empty frame
- 4 vacancy gaps (one is a 2-wide chasm)
- 3 dopants (Au, N, O) spread early/mid/late across the level
- 3 wobble (drift) hazard atoms

---

## Controls

| Key | Action |
|-----|--------|
| ← / A | Move left |
| → / D | Move right |
| Space / ↑ / W | Jump (buffered + coyote-time forgiving) |
| Shift (hold) | Blank the beam — no dose spent, no resolving |
| R | Restart |

---

## Known Limitations

- **Single synthetic level.** No real reconstruction data yet; geometry, hazard placement, and difficulty are hand-tuned guesses, not derived from actual material structure.
- **Fixed camera framing.** Smoothing and velocity look-ahead are in, but there is no zoom; the framing works for one screen-sized level and is untested at larger world sizes.
- **Renderer cost is untested on low-end hardware.** Bloom, parallax, particles and post all run every frame. Headless software rasterisation holds ~8ms/frame, which leaves room on real GPUs, but there is no quality toggle if a weak machine can't keep 60fps.
- **No mobile/touch controls.** Keyboard only.
- **Potential tunneling at high fall speed.** Simple discrete AABB collision could in principle skip through a thin platform if the frame rate drops and fall velocity is high; not yet observed but not hardened against either. A related case *was* observed and fixed: a column knocking out under the probe flickers, so the probe sank into it on non-solid frames and was then read as a side hit and ejected sideways off the column. A collapsing column now only ever holds the probe up.
- **No sound.** No audio feedback for resolve, damage, or the win state — the only sense that hasn't had a pass.
- **Toast facts aren't tracked.** Re-triggering the same dopant fact on restart is fine, but there's no persistent "discovered" log across sessions.
- **`DOSE_BUDGET` is measured against a bot, not a player.** 100 comes from headless simulation of routed sweeps and of naive edge-running (see **Balance**). Both are proxies; no human has played against the new number.
- **Runs still end by falling, not by running out of electrons.** Every measured run, at every skill level the harness can model, ends on *Probe lost*. Unconverged lattice is not solid and cannot be converged while falling through it, so a single missed platform is unrecoverable. The fixes so far removed the unfair versions of this (frame-rate-dependent movement, the spawn trap, being ejected sideways by a collapsing column, walking off the end of the specimen); the underlying precision demand is untouched and is the next thing to look at.
- **100% may be an unreasonable win bar on a *base* instrument.** Requiring all 152 atoms means early sessions almost always end on "beam exhausted." The upgrade path is the intended answer — the full clear is something the rig earns over several sessions — but whether that arc lands is unmeasured.
- **The upgrade curve is untuned.** Step sizes, the 40%/70% pick thresholds and 21 total picks are estimates, not playtest results. A fully upgraded instrument may trivialise the single level.
- **Nothing to spend picks on once maxed.** With every line at level 3 the draft is over and further sessions give no progression — the medium-term answer is more levels, not more upgrade tiers.
- **Blanking is undiscoverable without the instruction line.** It's currently taught by text, which violates the teach-through-geometry principle below.

---

## Roadmap

### Near-term
- **Tune the upgrade curve from playtesting** — step sizes, the pick thresholds, and whether 21 picks is the right length for the arc.
- **Tune `DOSE_BUDGET` from playtesting**, then `DOSE_PEAK`, `DOSE_ANNEAL`, `RESOLVE_TIME`, wobble amplitude. The budget is the dial that decides whether the game is tense or hopeless.
- **Reconsider the win threshold** — likely a percentage (85%?) rather than all 152 atoms, so "complete" is reachable and partial runs still resolve into a real ending.
- **Teach blanking and the resolve mechanic through geometry** — a "level 1-1" opening with a long stretch of pre-resolved ground where blanking is obviously free, before any dose pressure. No text.
- **Sound/juice pass** — landing thud, resolve chime, knock-out crackle, a hum that cuts out when the beam blanks.

### Medium-term
- **Swap in a real reconstruction.** Once recon data is available (owner is sourcing it separately), replace `generateSyntheticLattice()` output and `renderTargetImage()` with the real dataset — the `{x, y, element, intensity}` contract should make this a drop-in.
- **Multiple levels**, one per paper/structure, selectable like Explore mode in `optimization-quest.html`. Difficulty comes from real defect density, not synthetic tuning.
- **Probe modes** — a wide/defocused probe resolves safely but coarsely; a tight coherent probe is riskier but reveals rare defects. Unlocking modes recontextualizes earlier levels on replay (Metroidvania-style backtrack incentive) instead of a flat difficulty curve.

### Long-term
- **Richer end card** — dose efficiency grade and defects found, on top of the current stat grid, recovered-image thumbnail and dose/knock-out summary.
- **Mobile touch controls** if the Kids section audience needs them.

---

## Design Principles

1. **The goal is seeing the image, not filling a meter.** Numeric completion percentages are a means of tracking progress, never the reward itself — the reward is watching the true structure emerge from the fog.
2. **Resolving must cost something.** Free, instant reveals remove any tension from the signature mechanic. Dwell time, decay-on-leaving, local dose, and a global budget all price the same act.
3. **Seeing and destroying should be one action, not two.** Proximity resolves an atom and proximity knocks it out. A hazard system layered on top of the reveal mechanic would be arbitrary; a hazard that *is* the reveal mechanic is the subject matter.
4. **A budget needs counterplay.** A global dose limit on its own is a countdown the player can only lose to. Beam blanking turns it into a routing decision, which is where the skill lives.
5. **Hazards should be physically motivated where possible.** Wobble, flicker, and dose tolerance all come from atomic mass, not arbitrary tuning — more defensible and more teachable than a random difficulty knob.
6. **Movement forgiveness is invisible but load-bearing.** Coyote time, jump buffering, variable height, and fall-gravity punch should be protected, not regressed, by any future feature work.
7. **Curiosity content should never punish the direct path.** Off-path dopants reward exploration with real facts; players who beeline the exit lose nothing structurally.
8. **Teach through geometry, not text.** The first encounter with any new mechanic (resolve dwell, blanking, wobble, dose) should be introduced by safe level layout before it's ever combined with real stakes.
9. **Every visual effect should be the physics, drawn.** Converging electron streaks, Airy rings, the raster sweep, the unconverged speckle cloud, brightness scaling with atomic number — each is something the instrument actually does. Effects that would only be "sci-fi polish" don't earn their frame time, and effects that are the subject matter teach it for free.
10. **Colour is identity; warmth is cost.** Element hue means element. Anything warm on screen means the player is spending dose or destroying something. Hazards that aren't dose-driven (scan drift) are telegraphed with motion, never by borrowing a hue that already means something else.
