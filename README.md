# Lattice Runner

A 2D platformer about electron ptychography, where the thing you use to see is the thing that does the damage.

You play a scanning probe crossing an atomic lattice. Atom columns are your platforms — but they start as dim, out-of-focus ghosts and only sharpen into solid ground once you linger nearby long enough, the way a real reconstruction is built up scan position by scan position. Behind a layer of fog sits the true reconstruction image, and every atom you resolve punches a hole in it. The reward is watching the picture emerge.

The catch is the central bargain of electron microscopy: **to see an atom you have to hit it with electrons, and the electrons knock it out.** Proximity is what resolves an atom and proximity is what destroys it — the same act, two consequences. You carry one specimen's worth of dose, and how much of the picture you get to see before the beam runs out is the score.

The orange arc around a column is a net gauge while the column is under the probe: dose going in, minus the damage annealing back out. Getting away winds it down, and getting away vertically works best, because the probe is focused in the specimen plane and jumping defocuses it. So the arc filling under your feet is something you can actually outrun — jump, and it stalls. Get clear of the scan field entirely and the arc freezes where it stands: the specimen does not un-irradiate itself because you walked away, and that reading is still waiting for you when you come back.

Knock-out is permanent. A column you overexpose collapses out of its site and does not come back, so the platform you were standing on can become the hole you fall through — and below the lattice there is only the detector.

Falling isn't the end of the session, though. A real operator who loses the probe retracts the stage, re-inserts, and re-finds focus, and that costs beam time; so does this. You get put back on the nearest column still standing, twelve electrons lighter. The run only ends down there when there is nothing left to pay with.

## Play

Open [`index.html`](index.html) in a browser. No build step, no dependencies, no server — it's one self-contained file.

It also runs inside the [PtychoHub](https://ptychohub.com) Kids section, which fetches this repo's `index.html` through an authenticated proxy route. While this repo is private that card is contributor-only and the route is session-gated, so the game isn't reachable by the public. Making the repo public is the switch that ships it.

## Modes

Three of them, picked on the between-sessions card — **Esc** opens it from inside a run. All three run the same simulation and the same physics; knock-out is permanent in every one of them, because that is the specimen rather than a difficulty setting. What changes is which resource is scarce, and that turns out to be enough to change what playing well means.

| Mode | Scarce | What it asks of you |
|------|--------|---------------------|
| **Dose-limited session** | 100 electrons, no clock | The campaign. Route, blank, and spend the budget on picture instead of on re-alignment. The only mode that earns upgrades. |
| **60-second acquisition** | 60 seconds, dose free | Stage drift smears a frame after about a minute, so a minute is what you get. Blanking now costs you seconds and saves you nothing, so the whole skill is coverage per second — the exact inverse of a session. |
| **Open survey** | nothing | No clock, no budget, and the bar moves from 85% to every last column. Knock-out still bites, so the lattice can still be ruined; it just can't be hurried. **Enter** ends the run and prints the report. |

The sprint is the interesting one, because it inverts the lesson. In a session the beam is the resource and standing still is what costs you; in a sprint the clock is the resource and blanking is what costs you — but leaving the beam on while you loiter still destroys the columns you are about to want to stand on. Two opposite pressures, one dose model.

Only the dose-limited session feeds the draft, and only on a specimen that shipped with the game. The other two modes, and any lattice you drew yourself, keep their own best-percentage but pay no picks — a mode with nothing scarce in it would out-earn the one the balance is tuned against within a couple of runs.

## Runs and upgrades

A session ends when the electrons run out or the reconstruction is solved — 85% of the lattice, which is where a real reconstruction stops being ambiguous — and then you draft. Three instruments are offered, you keep one, and it carries into every session after. How much of the picture you recovered decides how many picks you get: one always, two at 40%, three at 70%. Abandoning a run with **R** earns nothing.

Picks settle only on a dose-limited session over a specimen that shipped with the game — see **Modes**. Every upgrade is a real technique for getting more picture out of fewer electrons — an 80 kV column that sits under carbon's knock-on threshold, mixed-state reconstruction, a direct electron detector, a fast blanker, wide-field scan coils, a cryo stage, sparse scanning. Three more buy handling rather than picture: a faster scan generator to slew the probe between positions, a piezo focal stage that steps further out of the specimen plane — which is what a jump is here — and beam-shift deflectors to carry the probe sideways while it's up there. Ten lines, three levels each. Progress is kept in `localStorage`; if that's unavailable the game still runs, it just won't remember.

Fully rigged, those three take the probe from 117 to 163 px/s, from a 109px jump to a 203px one, and from clearing one 90px lattice gap to clearing two and a half. They're the only upgrades that change which routes exist rather than what a route costs.

On a stock instrument a solved reconstruction is reachable but tight — it leaves room for about three falls and not much sloppy routing. The rig is what makes it comfortable.

## Controls

| Key | Action |
|-----|--------|
| ← → / A D | Move |
| Space / ↑ / W | Jump — coyote time and jump buffering are on, so it forgives near-misses |
| Shift (hold) | Blank the beam: no dose spent, no resolving, atoms cool off |
| Esc | Abandon the run and open the card — modes, specimens, upgrades |
| Enter | End an open survey and read the report |
| M | Mute / unmute |
| R | Abandon the run and restart (earns no upgrade) |

Blanking is the whole skill. Crossing ground you've already scanned costs nothing if the beam is off, so a good run is mostly about routing — not about moving fast.

## The physics is doing real work

Atomic mass isn't flavour text here. A single `vibrationFactor = √(m_C / m)` drives three separate behaviours:

- **how much dose an atom survives** — knock-on damage displaces a light carbon long before it budges a gold atom, so gold dopants are genuinely safe places to stand and think
- **how long a knocked-out atom survives** before it leaves its site for good — carbon is out in half a second, gold hangs on four times as long
- **how far drifting atoms wobble** — a nod to Debye–Waller thermal motion

Which means the level design falls out of the material rather than out of a difficulty knob.

## Specimens

Two lattices ship with the game, chosen from the card between sessions, and you can draw your own alongside them — see **Design your own specimen** below. The instrument you build carries across all of them; that's the point of having more than one, since a rig tuned on light carbon meets an oxide that punishes the same habits differently.

**Doped 2D lattice** — synthetic. A carbon sheet with three substitutions hidden in it and four vacancies to jump. Even ground, even columns; what it costs you is dose, not footing.

**Perovskite scandate** — measured, not invented. Traced off `obj_phase_roi_sum_Niter200.tiff`, a 277×277 px electron ptychography phase reconstruction at 200 iterations. 253 column peaks were located to sub-pixel precision and a lattice fitted through them, and what came back was a near-perfect square cell — a = 43.20 px, b = 42.98 px, interior angle 91.8° — with every site landing inside 0.012 of a cell edge. The 1.8° of shear is scan distortion, not crystallography.

The cell contents are the textbook ABO₃ perovskite projection down a pseudo-cubic ⟨100⟩ axis:

| Site | Position | What it does |
|------|----------|--------------|
| A-site cation | corner | Split into a resolved dumbbell, 5.2 px apart along 127° — the antipolar A displacement of an orthorhombic (Pbnm) tilt system |
| B-site cation | body centre | Unsplit. It sits on an inversion centre, so it's the one site in the cell that doesn't move |
| Oxygen ×2 | cell edges | 0.34× the cations' peak height, and *not* on the edge midpoints: each is displaced 4.54 px off it, and in 100% of the 83 columns measured the direction is set by the parity of the cell indices. That's an antiphase octahedral tilt — and it's what puts the half-order reflections in the FFT, a superlattice at 30 px, 45° off the cell axes |

Column σ came out at 2.0–2.6 px, so the information limit sits well inside a single cell: this reconstruction resolves the splitting, which is the entire reason a phase image is worth retrieving. If the pseudo-cubic edge is ~4.0 Å, the pixel is 0.093 Å, the field of view is 2.6 nm, the A-site dumbbell is 0.48 Å across and the oxygen displacement is 0.42 Å.

Calling the three site classes Pr / Sc / O is the one assumption in there — it's the rare-earth-scandate reading of an A:B integrated-intensity ratio of 2.4. The site classes themselves are measured. A different perovskite is a three-symbol edit in `SCANDATE_SITES` and nothing else.

**The layout is the reconstruction.** The field is 6.1 cells wide and 6.2 tall, which is the wrong shape for a side-scroller, so it's cut along a lattice plane into two 3-cell bands and the lower band is laid to the right of the upper one, offset by a whole number of cells in both directions. Both halves are the same crystal, so the join is seamless — rows line up, the checkerboard continues. Every measured column is used exactly once and carries its own real deviation from the ideal site. The 44 faintest peaks were dropped: they sit on no consistent sublattice, so they're the noise floor, not oxygen.

**And the structure is the level design.** Every row is a continuous chain at the same 90 px pitch the carbon sheet runs at, but the footholds alternate: heavy cation, oxygen, heavy cation. The A-site dumbbell's two columns are 16 px apart and fuse into one wide safe pad; the B-site is a single broad column; oxygen is a small one. Then `vibrationFactor` does the rest — oxygen survives 2.3 units of dose against the A-site's 6.8, and drifts three times as far. So the fast route along a row keeps landing on the fragile thing, and the only way across a perovskite is the oxygen. Which is also true in a real microscope, where oxygen is the first thing you lose.

## Design your own specimen

The card has a **＋ Design a specimen** slot next to the two shipped lattices. It opens a grid editor at the same 90 px pitch the real specimens run at: drag to paint columns, right-drag or **E** to erase, **1**–**6** to pick an element, **D** to make a column drift. Play it straight from the editor, and it plays under whichever mode is selected, on your current instrument.

Nothing about a lattice you drew is a special case in the engine. The designer emits exactly the atom array `scandate()` emits, so the hidden phase image, the fog, the opening survey scan, knock-on tolerance and the field notes all come along for free — that is what the `SPECIMENS` seam was for.

Element choice is the level design, the same way it is in the perovskite. Each palette entry carries the two numbers that matter: how wide a platform it makes, and how much dose it survives, both of which fall out of atomic mass. Oxygen is a 32 px pad at 1.2× carbon's tolerance — a tightrope that dies first. Gold is a 57 px pad at 4×, a bench you can stand on and think.

**The editor knows your jump arc.** It walks the lattice you have drawn using the real constants the run flies on — `JUMP_VELOCITY`, gravity, the airborne speed your SCAN/PZT/SHFT levels actually give you — and rings in amber every column the probe could neither reach nor scan from the spawn. Which means the advice is not a guess about the game, it is the game solved for reachability, and it changes as your instrument does: a layout that is unplayable on a stock column opens up once the piezo stage is in. The footer quotes the numbers it is reasoning from — jump height, the gap it clears, the scan field, the lattice pitch.

Alternate rows sit half a cell over, exactly the way the carbon sheet lays its rows out. That is mechanical rather than decorative: on a rigid grid every column has another column directly overhead and the probe fights a ceiling it can't land on, while offset rows put the site above you 45 px to one side — the geometry the whole game was tuned against, and what a close-packed lattice does anyway.

Eight designs are kept, in `localStorage` alongside the rest of your progress.

## Swapping in more real data

Specimens live in the `SPECIMENS` array behind a deliberate seam. Each one's `build()` emits an array of:

```js
{ x, y, element, intensity, r?, wobble?, note? }
```

Match that shape with any reconstruction export and it drops in without touching game logic. `renderTargetImage()` draws the false-colour reveal image from those columns, so a specimen brings its own hidden picture along with it.

## Look

Everything on screen is meant to be the instrument, drawn. The probe is a real ray diagram — electrons stream down the illumination cone and converge on a focal spot ringed by its own Airy pattern, with the transmitted cone heading for the detector below. Unresolved sites are the same columns at a worse information limit — blurred and faint, pulling into focus and up in brightness as they converge, because that is what a reconstruction gaining data actually looks like. No progress bar: the image quality is the progress bar. Dose is an arc winding around a column toward knock-out. A raster line sweeps down the frame trailing a decaying glow, because this is a scanning microscope. Gold glows harder than carbon because heavier nuclei scatter harder.

Colour carries one meaning each: hue is element identity, and anything warm means you are spending dose or destroying something. The scan-drift hazard is telegraphed in motion — a vertically biased ghost and a dashed vertical track — rather than by borrowing a colour that already means nitrogen.

Under it: cached sphere sprites, a quarter-res additive bloom pass, three parallax layers, a false-colour phase LUT with the bonding network baked into the hidden image, device-pixel scanlines, film grain, and a DPR-aware canvas so none of it is soft on a retina display. Still one file, still no dependencies.

## Sound

Synthesised at runtime — no samples, still one file. The only continuous sound is the beam hum, and its filter opens as the probe heats up, so a column starting to cook is audible before the warning appears. It stops the instant you blank. That's the whole lesson of blanking, delivered by ear.

## Balance

The tuning is measured rather than guessed, by driving the shipped game headlessly at a fixed timestep. Riding one row end to end converges half the lattice for 20 electrons; rows 1 and 4 together solve it for 33. That's the floor. A bot that actually has to jump spends about 90 and falls four times on the way, which is 48 electrons gone on re-alignment rather than on looking at anything — the end card says so in as many words.

Leaving the beam on costs roughly 30 percentage points and twenty destroyed columns against the same route played with blanking. That gap is the game.

Sweeping at full speed destroys nothing, and neither does 90 px/s. Slow to 70 and it costs thirty-six columns. Hovering is the only thing the dose model punishes, which is the point.

The two new modes are not tuned to that standard yet, and the doc says so. The one sprint number that exists is the floor: a probe nobody touches at all still phases 18% of the carbon sheet in its sixty seconds, while destroying 19 columns and falling seven times. What a routed sprint scores — and therefore whether sixty seconds is the right window — is unmeasured.

One fix worth calling out: horizontal damping used to be applied per frame rather than per second, so the probe's top speed depended on your refresh rate — 237 px/s at 30 Hz, 118 at 60, 49 at 144. Above about 90 Hz it could no longer clear a gap in the lattice, which made the game close to unplayable on a 120 Hz display. Top speed is now ~120 px/s on any monitor.

## More

[`DESIGN.md`](DESIGN.md) has the full design document: mechanics, tuning constants, the measured balance tables, known limitations, and roadmap.
