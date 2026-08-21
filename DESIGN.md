# Lattice Runner — Game Design Document

**Status:** single-file prototype at [`index.html`](index.html) — open directly in a browser, no build step. Served into the PtychoHub Kids section through a thin proxy route that fetches this repo's `index.html` from GitHub raw, the same way [TheBrilliantFacility](https://github.com/yijiang1/TheBrilliantFacility) and [GravityQuest](https://github.com/yijiang1/GravityQuest) are. Pushing to `main` here publishes the game.

## Concept

A 2D platformer where the player controls a scanning probe moving across an atomic lattice reconstructed via electron ptychography. Atom columns are jump platforms. The signature mechanic: atoms start as faint unresolved ghosts and only become solid once the probe lingers nearby long enough — mirroring how a real ptychography reconstruction is built up scan-position by scan-position, not revealed all at once.

The goal is not a numeric completion percentage. A true reconstruction image sits behind a fog layer; resolving atoms punches holes in the fog, so the payoff is literally watching the hidden picture emerge as you play.

The tension comes from the central bargain of electron microscopy: **to see an atom you must hit it with electrons, and the electrons destroy it.** You carry one specimen's worth of dose. Proximity is what resolves an atom and proximity is what knocks it out — the same act, two consequences — so there is no separate "hazard" system bolted on. How much of the picture you get to see before the beam runs out is the score.

Inspired by the research pass on platformer design (Celeste, Super Mario Bros, Spelunky, Hollow Knight, Braid — see conversation history / commit context): movement forgiveness is the invisible foundation, goals should be concrete rather than an abstract meter, and risk/reward needs to be tightly coupled rather than decorative.

---

## Core Mechanics

### The probe (player character)
Drawn as the ray diagram it actually is: a cone of electrons converging from the column above down to a bright focal spot, with the transmitted cone diverging below toward the detector. The focal spot is the body; the cones read as a silhouette.

Character comes from three cheap tricks rather than a sprite — the rig leans into horizontal velocity, the focal spot squashes and stretches with speed, and an eye tracks the facing direction. It runs orange instead of blue whenever it's close to knocking something out, so the avatar visibly *heats up* while doing damage. Blanked, the cones drop to a dashed outline and the spot shrinks and dims.

### Movement
Standard run/jump with forgiveness layered on top so input feels answered rather than frame-perfect:
- **Coyote time** (0.12s) — jump still fires briefly after walking off a ledge
- **Jump buffering** (0.12s) — a jump press slightly before landing queues up and fires on landing
- **Variable jump height** — releasing jump early clamps upward velocity, giving a short hop instead of the full arc
- **Heavier fall gravity** (1.6×) — snappier descent than the rise

### Resolve-by-proximity
Each unresolved atom has a `resolveProgress` (0–1) that:
- builds while the probe is within `RESOLVE_RADIUS` (150px), taking `RESOLVE_TIME` (0.5s) of continuous presence to complete
- decays at 2.2× the build rate if the probe leaves before finishing (leaving early costs real progress, not just time)
- once complete, permanently resolves the atom into a solid platform and erases a patch of fog around it on the reveal image

This is deliberately not instant — it's the "cost" that turns exploration into a pace-yourself decision rather than a free trigger.

### Dose (self-inflicted risk)
The probe deposits dose into **every** atom within its radius, not just the one it's standing on, at a rate falling off with distance the way a real beam profile does:

```
rate = DOSE_PEAK / (1 + d² / DOSE_FALLOFF²)
```

Standing on an atom is simply the closest you can physically get, so it cooks fastest (~2s for carbon); a neighbour one lattice spacing away still takes dose, at roughly 1/2.5 the rate. Dose anneals back off slowly (`DOSE_ANNEAL`) once the atom is out of the beam.

Past its tolerance an atom **knocks out**: it flickers between solid and non-solid, so it's still traversable but no longer trustworthy. This is dynamic, not pre-scripted — any atom can become a hazard, including one the probe is still trying to resolve. Dose rings render on unresolved atoms too, so you can watch yourself damaging the thing you're mid-way through revealing.

### The dose budget
A run carries `DOSE_BUDGET` (130) units of dose. A real beam runs at fixed current, so total electrons spent is just beam-on time — the budget is a clock, but one the player controls rather than one that runs regardless.

A run ends one of two ways, neither of which is a failure screen:
- **Reconstruction complete** — every atom resolved; the card reports what it cost.
- **Beam exhausted** — the electrons ran out; the card reports how much of the lattice you got, and points at blanking.

### Beam blanking
Holding **SHIFT** blanks the beam: no budget drain, no dose deposited, no resolving, and atoms anneal while it's off. Blanking is a standard technique for beam-sensitive specimens, and it turns the budget from pure pressure into a routing decision — cross ground you've already scanned for free, unblank when you actually want to see something. The illumination circle vanishing is the whole visual read: no circle, no cost.

### Wobble hazard (scan-drift)
A subset of atoms drift vertically once resolved, telegraphed beforehand by a violet-tinted ghost outline before they're ever solid. Distinct from overexposure damage — this is environmental, not caused by the player.

### Vacancies (gaps)
Missing lattice sites are simply absent — no platform, so the player must jump the gap. Most are single-width; one location has two adjacent vacancies for a wider chasm, giving jump-distance variety.

### Mass-driven behaviour
One number, `vibrationFactor = √(reference_mass / element_mass)`, drives three separate visible behaviours:

1. **Wobble speed and amplitude** — lighter atoms jiggle faster and wider (a nod to Debye–Waller thermal motion).
2. **Flicker rate once knocked out** — lighter atoms drop out of solidity faster.
3. **Dose tolerance** — `doseLimit = DOSE_LIMIT / vib`, i.e. proportional to √mass. Knock-on damage displaces a light carbon long before it budges a gold atom.

The third is what makes it matter for play rather than flavour: the gold dopant is a genuinely safe place to stand and think, and carbon is where you cannot dawdle. Real knock-on physics producing real level design for free.

### Curiosity content (dopants)
A few lattice sites are real dopant/defect elements (not the base carbon lattice), each with distinct color/size and a one-line real fact shown as a toast the first time it's resolved. These sit off the critical path so players who beeline the exit don't see them — reward for exploring, not a requirement.

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
- 1 pre-resolved spawn atom (falling onto an unresolved atom before the 0.5s dwell timer completes would just drop the player through it, so the very first landing is guaranteed safe)
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
- **Fixed camera framing.** No zoom or look-ahead; works for one screen-sized level, untested at larger world sizes.
- **No mobile/touch controls.** Keyboard only.
- **Potential tunneling at high fall speed.** Simple discrete AABB collision could in principle skip through a thin platform if the frame rate drops and fall velocity is high; not yet observed but not hardened against either.
- **No sound.** No audio feedback for resolve, damage, or the win state.
- **Toast facts aren't tracked.** Re-triggering the same dopant fact on restart is fine, but there's no persistent "discovered" log across sessions.
- **`DOSE_BUDGET` is an estimate, not a measurement.** 130 was derived from level geometry (~3 sweeps × 9s plus navigation), not from playtest data. It's the single most important number to tune and the most likely to be wrong.
- **100% may be an unreasonable win bar under a budget.** Real reconstructions never resolve everything; requiring all 152 atoms to see the "complete" card may mean almost every run ends on "beam exhausted." A percentage threshold is probably the better win condition.
- **Blanking is undiscoverable without the instruction line.** It's currently taught by text, which violates the teach-through-geometry principle below.

---

## Roadmap

### Near-term
- **Tune `DOSE_BUDGET` from playtesting**, then `DOSE_PEAK`, `DOSE_ANNEAL`, `RESOLVE_TIME`, wobble amplitude. The budget is the dial that decides whether the game is tense or hopeless.
- **Reconsider the win threshold** — likely a percentage (85%?) rather than all 152 atoms, so "complete" is reachable and partial runs still resolve into a real ending.
- **Teach blanking and the resolve mechanic through geometry** — a "level 1-1" opening with a long stretch of pre-resolved ground where blanking is obviously free, before any dose pressure. No text.
- **Sound/juice pass** — landing thud, resolve chime, knock-out crackle, a hum that cuts out when the beam blanks.

### Medium-term
- **Swap in a real reconstruction.** Once recon data is available (owner is sourcing it separately), replace `generateSyntheticLattice()` output and `renderTargetImage()` with the real dataset — the `{x, y, element, intensity}` contract should make this a drop-in.
- **Multiple levels**, one per paper/structure, selectable like Explore mode in `optimization-quest.html`. Difficulty comes from real defect density, not synthetic tuning.
- **Probe modes** — a wide/defocused probe resolves safely but coarsely; a tight coherent probe is riskier but reveals rare defects. Unlocking modes recontextualizes earlier levels on replay (Metroidvania-style backtrack incentive) instead of a flat difficulty curve.

### Long-term
- **Richer end card** — dose efficiency grade, defects found, a thumbnail of exactly how much of the image you revealed, on top of the current dose/knock-out summary.
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
