# Lattice Runner — Game Design Document

**Status:** single-file prototype at [`index.html`](index.html) — open directly in a browser, no build step. Served into the PtychoHub Kids section through a proxy route, the same way [TheBrilliantFacility](https://github.com/yijiang1/TheBrilliantFacility) and [GravityQuest](https://github.com/yijiang1/GravityQuest) are — except this repo is private for now, so that route uses the authenticated GitHub Contents API and is session-gated, and the card is contributor-only. Pushing to `main` updates the game for contributors; making the repo public is what ships it to everyone.

## Concept

A 2D platformer where the player controls a scanning probe moving across an atomic lattice reconstructed via electron ptychography. Atom columns are jump platforms. The signature mechanic: atoms start as faint unresolved ghosts and only become solid once the probe lingers nearby long enough — mirroring how a real ptychography reconstruction is built up scan-position by scan-position, not revealed all at once.

The goal is not a numeric completion percentage. A true reconstruction image sits behind a fog layer; resolving atoms punches holes in the fog, so the payoff is literally watching the hidden picture emerge as you play.

The tension comes from the central bargain of electron microscopy: **to see an atom you must hit it with electrons, and the electrons destroy it.** You carry one specimen's worth of dose, and everything that goes wrong — including falling off the lattice — is paid for out of it. Proximity is what resolves an atom and proximity is what knocks it out — the same act, two consequences — so there is no separate "hazard" system bolted on. How much of the picture you get to see before the beam runs out is the score.

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

Landing uses a **swept** test rather than a discrete overlap. A column top is
only ~24px tall and at terminal fall speed a single 33ms frame carries the probe
53px — clean through it, with a box test seeing nothing at either end. If the
probe started the frame above the top and finished below it, it landed,
whatever the boxes say now.

### Resolve-by-proximity
Each unresolved atom has a `resolveProgress` (0–1) that:
- builds while the probe is within `RESOLVE_RADIUS` (150px), taking `RESOLVE_TIME` (0.5s) of continuous presence to complete
- decays at 2.2× the build rate if the probe leaves before finishing (leaving early costs real progress, not just time)
- once complete, permanently resolves the atom into a solid platform and erases a patch of fog around it on the reveal image

This is deliberately not instant — it's the "cost" that turns exploration into a pace-yourself decision rather than a free trigger.

Visually an unresolved site is a *speckle cloud that has not converged*: a ring of dots scattered around the column, collapsing onto it as `resolveProgress` builds, wrapped by an arc that fills to show the dwell. Completing it snaps the sphere in with an overshoot, a spark burst and an expanding ring. Nothing about the site is a placeholder dashed circle any more — it is a reconstruction mid-convergence.

### Dose (self-inflicted risk)
The probe deposits dose into **every** atom within its radius, not just the one it's standing on, at a rate falling off with distance the way a real beam profile does. Deposition and annealing both run all the time, and what the arc shows is the net:

```
d² = dx² + (dy · DOSE_DEFOCUS)²
rate = DOSE_PEAK / (1 + d² / DOSE_FALLOFF²) - DOSE_ANNEAL
```

Standing on an atom is simply the closest you can physically get, so it cooks fastest (1.97s measured for carbon); a neighbour one lattice spacing away still takes dose, at roughly 1/3 the rate.

Two details in that formula are load-bearing, and both were added to fix the same bug.

**Annealing is unconditional.** It used to apply only *outside* the probe field, which made the gauge a ratchet: anywhere inside the 150px radius the arc could climb but never fall, and it flipped sign at a hard edge — an atom at 149px gained dose, one at 151px lost it. Backing off did nothing you could see until you crossed that line. Now moving away registers on the ring immediately, and far enough away the arc winds back down with the beam still on.

**Vertical distance counts double.** The probe is focused *in* the specimen plane; leaving that plane defocuses it, and a defocused probe spreads the same current over a much larger disc, so the dose density on any one column collapses. `DOSE_DEFOCUS` (2.0) is the factor vertical offset counts for. Without it the entire 0.62s jump arc stays inside the beam's waist — apex is only 114px up, against a 70px falloff — so the gauge you are jumping to escape keeps filling while you are airborne. Measured on a carbon at the warning threshold, a jump straight up used to add **+0.126** of the limit and could knock the column out from under the probe mid-flight; it now adds **+0.004**, and the arc visibly stalls and dips at the apex.

The asymmetry is deliberate rather than incidental: horizontal collateral is the mechanic the balance rests on (see the sweep-speed table below), so it is left alone, while vertical escape is the one verb the player has besides blanking. `DOSE_PEAK` was raised 1.1 → 1.7 to hold the standing knock-out time at the designed ~2s once the anneal term became unconditional.

Past its tolerance an atom **knocks out**, and knock-out is permanent. The column flickers for `DAMAGE_COLLAPSE / vib` seconds — long enough to feel it go, and to give anyone standing on it a moment to leave — and then it is gone for the rest of the run. A displaced atom does not return to its site, so the lattice you damage stays damaged: the platform is not coming back, and the hole you made is now part of the level.

This is dynamic, not pre-scripted — any atom can become a hazard, including one the probe is still trying to resolve. Dose renders as an arc winding around the column, a gauge filling toward knock-out, and it renders on unresolved atoms too, so you can watch yourself damaging the thing you're mid-way through revealing. Knock-out cracks the sphere, kicks a shockwave and embers out of it, and shakes the frame. Mid-collapse the column reads warm and dashed; once emptied it goes cool and hollow, so "still going" and "gone for good" never look alike.

### The dose budget
A run carries `DOSE_BUDGET` (100) units of dose, before instrument upgrades. A real beam runs at fixed current, so total electrons spent is just beam-on time — the budget is a clock, but one the player controls rather than one that runs regardless. It is also what falling is paid out of, which is what finally made it the binding constraint.

100 is measured, not estimated — see **Balance** below.

A run ends one of three ways, none of which is a failure screen — the report and the upgrade pick are earned by what the scan recovered, however it stopped:
- **Reconstruction solved** — `WIN_FRAC` (85%) of the lattice phased; the card reports what it cost.
- **Beam exhausted** — the electrons ran out; the card reports how much of the lattice you got, and points at blanking.
- **Probe lost** — the probe struck the detector with too little beam left to recover.

### Losing the probe, and getting it back
The lowest atom row sits ~470px above the detector plane and a full jump clears
~110px, so there is no climbing back out under your own power. Falling used to
end the session outright, and that turned out to be the single worst thing about
the balance: **every** measured run, at every skill level the harness could
model, ended on *Probe lost* with 75+ of its 100 electrons unspent. The resource
the entire game is about was never the thing that ran out.

A real operator who loses the probe does not throw the specimen away. They
retract the stage, re-insert, re-find focus — and that costs beam time. So does
this. Hitting the detector spends `REALIGN_COST` (12) electrons and puts the
probe back over the **nearest column still standing to where it went down**,
not the spawn: falling is meant to cost electrons, not progress, and sending
the player back across specimen they have already paid to scan would charge
them twice for one mistake. The beam stays blanked for `REALIGN_GRACE` (0.7s)
while the stage settles, so you are never billed for frames you did not choose.

The session still ends down there in two cases, and the card says which: there
is not enough beam left to pay for the re-align, or there is no resolved,
undamaged column left to come back to. Knocking out the column you are standing
on is a real way to fall, which is what ties the dose model to the platforming —
it is now expensive rather than terminal.

### What counts as solved
A reconstruction is not called solved when every column is perfect; it is called
solved when the structure is unambiguous. Requiring all 152 columns made
"complete" a bar the base instrument could not clear at any skill level, which
turned the win state into decoration. `WIN_FRAC` is 0.85, drawn on the HUD
meter as a tick so the goal is visible from inside the run rather than being a
percentage in a sentence on the end card.

### Balance (measured)

Numbers below come from driving the shipped simulation headlessly at a fixed
timestep, not from a feel judgement.

**What coverage costs.** Riding a single row from one end of the specimen to the
other converges about half the lattice, because the 150px scan field reaches one
row up and one row down:

| Route | Reconstructed | Electrons |
|---|---|---|
| row 1, end to end | 49% | 21 |
| row 4, end to end | 55% | 20 |
| rows 1 then 4 | **86% — solved** | **33** |
| rows 1, 3, 5 | 86% | 41 |
| rows 0, 2, 4 | 86% | 50 |

So the theoretical floor for a solved reconstruction is 33 electrons: two rows,
ridden end to end, at speed. That is the number `DOSE_BUDGET` of 100 is set
against — it leaves room for about three falls and a lot of imperfect routing,
and no more. At the old 130 even naive play cleared the lattice with headroom,
which made the game's central resource inert.

Speed matters because the budget is a clock: the same two-row sweep costs 55
electrons at 70 px/s and 20 at 200 px/s.

**Knock-out only punishes lingering.** Sweeping a row at top speed (~120 px/s)
destroys nothing. At 90 px/s it costs nothing either; at 70 px/s it costs 36
columns. The dose model therefore reads as "keep scanning, don't hover", which
is the intended lesson — and the net-rate change above deliberately did not
soften it, because the punishment is horizontal and the change is vertical.

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

**Falling is now what the budget is spent on.** With stage re-insertion in, the
same routes play out completely differently. Each row below is the median of 7
page loads (the three drift atoms take a random phase per load, so single runs
are noisy), driven by a route-following bot at a fixed timestep:

| Bot | Reconstructed | Electrons | Knock-outs | Falls | Endings (of 7) |
|---|---|---|---|---|---|
| routed, blanking | 86% | 89 | 0 | 4 | **solved 7** |
| routed, beam always on | 80% | 94 | 2 | 3 | lost 3, solved 2, exhausted 2 |
| loose jump timing, blanking | 86% | 79 | 0 | 3 | **solved 7** |
| loose timing, beam always on | 56% | 95 | 20 | 2 | lost 7 |
| random inputs (n=200) | 5% | 94 | — | 7 | lost 178, exhausted 22 |

Two things fall out of this. Blanking is worth roughly 30 percentage points and
twenty columns of the specimen, which is the lesson the game exists to teach.
And a bot that falls four times has spent 48 of its 100 electrons on
re-alignment — the end card says so in as many words, because "you lost the
probe four times, 48 of those electrons went on re-aligning it rather than on
looking at anything" is the whole feedback loop in one line.

The unconditional-anneal change moved these: the routed rows gained 2–4 points
and the routed-with-blanking bot went from solving 2 runs in 7 to solving all 7.
That is the cost of making the gauge honest, and it lands entirely on players
who are already routing well. The unblanked rows barely moved, so the gap the
game is built around survived intact.

Before the change, the same panel was 100% *Probe lost* at 14–53s with 60–80
electrons still in the tank. Now the endings are a real mix and every run uses
most of its budget.

**Frame-rate independence still holds** after the swept-collision change, at a
flat 0.63s of airtime from 30Hz to 144Hz:

| fps | terminal vx | jump reach | rise |
|---|---|---|---|
| 30 | 107 px/s | 68 px | 103 px |
| 60 | 118 px/s | 75 px | 109 px |
| 90 | 123 px/s | 78 px | 110 px |
| 120 | 125 px/s | 79 px | 111 px |
| 144 | 126 px/s | 80 px | 112 px |

### Beam blanking
Holding **SHIFT** blanks the beam: no budget drain, no dose deposited, no resolving, and atoms anneal while it's off. Blanking is a standard technique for beam-sensitive specimens, and it turns the budget from pure pressure into a routing decision — cross ground you've already scanned for free, unblank when you actually want to see something. The illumination circle vanishing is the whole visual read: no circle, no cost.

### Sound
Synthesised at runtime with WebAudio — a single self-contained file has nowhere
to put a sample and no build step to inline one, so everything is an oscillator
or a burst of noise through a filter. That suits the subject.

The only continuous sound is the **beam hum**: three detuned oscillators under a
low-pass, and its cutoff opens with `probeHeat`, so a column starting to cook is
audible before the warning panel ever fires. It stops the instant SHIFT goes
down. That is the blanking lesson delivered by ear, which is closer to
teach-through-geometry than a line of text is.

One-shots cover jump, landing (pitched by impact speed), resolve, knock-out,
stage re-insertion, the low-budget warning and the three end cards. Resolve
pitch tracks `vib`, so a heavy column lands lower than a light one — the same
sqrt(mass) that already drives wobble, flicker and dose tolerance.

Nothing is constructed until a real gesture: browsers refuse to start an
AudioContext without one, and one-shots deliberately never call the constructor
themselves. On an untouched page, and in the headless balance harness, every
call is a silent no-op against a null context. **M** mutes, and that persists.

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

Abandoning a run with **R** earns nothing — credits only settle when the beam actually runs out, the probe is lost for good, or the lattice is solved. Without that, resolving the ten easy atoms near spawn and restarting would out-earn playing a full session.

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
The win state used to be out of reach on a base instrument, and the upgrade path was the intended answer to that. Two of the three fixes since have come from elsewhere — `WIN_FRAC` at 85% and stage re-insertion — so the draft is no longer load-bearing for reachability. It is now what makes a *comfortable* clear, and what a player spends bad runs earning. Whether that is enough for it to do is unmeasured.

### Persistence
`localStorage` under `latticeRunner.v1`, holding session count, banked picks, best percentage, upgrade levels, the dopant facts already logged (`found`), the mute setting, and whether the blanking prompt has been shown (`taughtBlank`). Reads and writes are wrapped — private mode and sandboxed iframes throw on access, and the game has to run there too, just without carrying progress. Levels are clamped on load, so a corrupted or hand-edited save can't put the instrument out of range.

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

The survey patch is also where a fall usually returns you, since re-insertion
picks the nearest standing column to the impact point and early falls happen
near the spawn.

---

## Controls

| Key | Action |
|-----|--------|
| ← / A | Move left |
| → / D | Move right |
| Space / ↑ / W | Jump (buffered + coyote-time forgiving) |
| Shift (hold) | Blank the beam — no dose spent, no resolving |
| M | Mute / unmute (persists) |
| R | Restart |

---

## Known Limitations

- **Single synthetic level.** No real reconstruction data yet; geometry, hazard placement, and difficulty are hand-tuned guesses, not derived from actual material structure.
- **Fixed camera framing.** Smoothing and velocity look-ahead are in, but there is no zoom; the framing works for one screen-sized level and is untested at larger world sizes.
- **Renderer cost is still untested on low-end hardware, and cannot be tested here.** What *is* measured: a full `draw()` costs **0.5ms of JavaScript**, and the 152 atoms, their halos, the speckle clouds, the probe rig and the bloom composite are all free to the millisecond. Everything expensive is a full-screen fill — post, the parallax background, and the two full-world `drawImage` calls for the reconstruction and the fog over it. That is fill rate, which a software rasteriser punishes (100ms/frame at 2880x1800 headless) and any real GPU handles without noticing. An adaptive quality system that sheds those passes was written and then reverted: on the only instrument available it produced no measurable saving, so shipping it would have been guesswork wearing a measurement's clothes. If a real weak machine ever turns up, the ablation ranking above says exactly what to cut first.
- **No mobile/touch controls.** Keyboard only.
- ~~**Potential tunneling at high fall speed.**~~ Fixed: landing is a swept test now, so a frame that carries the probe clean past a column top still lands it. Two related cases were fixed earlier — a collapsing column ejecting the probe sideways, and frame-rate-dependent damping.
- **Sound is unmixed and unheard.** A full WebAudio pass is in (see **Sound**), but every level, filter cutoff and envelope in it was chosen by reading the code, not by listening — this environment has no audio device. Expect the balance between the hum and the one-shots to need real ears.
- **Field notes are logged but barely surfaced.** Dopant facts now persist across sessions and the end card carries a Notes count, but there is no place to re-read one you have already found.
- **`DOSE_BUDGET` is measured against a bot, not a player.** 100 comes from headless simulation of routed sweeps and of naive edge-running (see **Balance**). Both are proxies; no human has played against the new number.
- **A bad run still reads as *Probe lost*, because it is.** Stage re-insertion moved the pressure onto the budget — routed play now ends on *solved* or *beam exhausted* — but a random-input run falls seven times, spends 84 of its 94 electrons on re-alignment, and then hits the detector with nothing left to pay with. That ending is accurate and the card explains it, but the underlying precision demand of the platforming is untouched: unconverged lattice is not solid and cannot be converged on the way past (0.5s of dwell needed, under 0.3s in range at fall speed). Widening the columns further is the measured lever if playtesting says it is still too steep.
- **85% is now too *easy* a win bar for a good player.** The bar was moved down from all 152 columns because nothing could reach it. A routed bot on a base instrument used to solve about half its attempts; since dose became a net rate it solves **all seven of seven**, before spending a single upgrade. Two rows ridden end to end cover 86% for 33 of the 100 electrons, so the ceiling is structural: a player who knows the route has nothing left to spend the budget on. Raising `WIN_FRAC` is a one-constant change, but the honest fix is a lattice whose coverage is not saturated by two horizontal sweeps.
- **The upgrade curve is untuned.** Step sizes, the 40%/70% pick thresholds and 21 total picks are estimates, not playtest results. A fully upgraded instrument may trivialise the single level.
- **Nothing to spend picks on once maxed.** With every line at level 3 the draft is over and further sessions give no progression — the medium-term answer is more levels, not more upgrade tiers.
- **Blanking is still taught by text, just at a better moment.** The prompt now fires the first time the beam has spent three seconds with nothing new in range and 15 electrons already gone, and only once across all sessions. The beam hum cutting out on SHIFT teaches the same thing by ear. Neither is the "level 1-1" geometry the principle below actually asks for.

---

## Roadmap

### Near-term
- **Put it in front of a human.** Everything below the top of this file is measured against bots. `DOSE_BUDGET`, `REALIGN_COST` and `WIN_FRAC` are the three constants that a single playtest would settle, and all three are one-line changes.
- **Tune the upgrade curve from playtesting** — step sizes, the pick thresholds, and whether 21 picks is the right length for the arc. Untouched by any of the balance work so far.
- **Mix the audio with real ears.** Levels and cutoffs were chosen by reading, not listening.
- **Teach blanking through geometry** — a "level 1-1" opening with a long stretch of pre-resolved ground where blanking is obviously free, before any dose pressure. The contextual prompt and the hum are stand-ins for this, not replacements.
- ~~Reconsider the win threshold~~ — done, `WIN_FRAC` is 0.85 with a tick on the HUD meter.
- ~~Sound/juice pass~~ — done, see **Sound**.

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
