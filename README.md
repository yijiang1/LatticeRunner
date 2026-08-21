# Lattice Runner

A 2D platformer about electron ptychography, where the thing you use to see is the thing that does the damage.

You play a scanning probe crossing an atomic lattice. Atom columns are your platforms — but they start as unresolved speckle clouds and only condense into solid ground once you linger nearby long enough, the way a real reconstruction is built up scan position by scan position. Behind a layer of fog sits the true reconstruction image, and every atom you resolve punches a hole in it. The reward is watching the honeycomb picture emerge.

The catch is the central bargain of electron microscopy: **to see an atom you have to hit it with electrons, and the electrons knock it out.** Proximity is what resolves an atom and proximity is what destroys it — the same act, two consequences. You carry one specimen's worth of dose, and how much of the picture you get to see before the beam runs out is the score.

Knock-out is permanent. A column you overexpose collapses out of its site and does not come back, so the platform you were standing on can become the hole you fall through — and below the lattice there is only the detector, which ends the session.

## Play

Open [`index.html`](index.html) in a browser. No build step, no dependencies, no server — it's one self-contained file.

It also runs inside the [PtychoHub](https://ptychohub.com) Kids section, which fetches this repo's `index.html` through an authenticated proxy route. While this repo is private that card is contributor-only and the route is session-gated, so the game isn't reachable by the public. Making the repo public is the switch that ships it.

## Runs and upgrades

A session ends when the electrons run out or the lattice is fully phased — then you draft. Three instruments are offered, you keep one, and it carries into every session after. How much of the picture you recovered decides how many picks you get: one always, two at 40%, three at 70%. Abandoning a run with **R** earns nothing.

Every upgrade is a real technique for getting more picture out of fewer electrons — an 80 kV column that sits under carbon's knock-on threshold, mixed-state reconstruction, a direct electron detector, a fast blanker, wide-field scan coils, a cryo stage, sparse scanning. Seven lines, three levels each. Progress is kept in `localStorage`; if that's unavailable the game still runs, it just won't remember.

This is also the answer to a problem the base game had: on a stock instrument, 100 electrons make a full reconstruction hard to reach. The full clear is something the rig earns over several sessions.

## Controls

| Key | Action |
|-----|--------|
| ← → / A D | Move |
| Space / ↑ / W | Jump — coyote time and jump buffering are on, so it forgives near-misses |
| Shift (hold) | Blank the beam: no dose spent, no resolving, atoms cool off |
| R | Abandon the run and restart (earns no upgrade) |

Blanking is the whole skill. Crossing ground you've already scanned costs nothing if the beam is off, so a good run is mostly about routing — not about moving fast.

## The physics is doing real work

Atomic mass isn't flavour text here. A single `vibrationFactor = √(m_C / m)` drives three separate behaviours:

- **how much dose an atom survives** — knock-on damage displaces a light carbon long before it budges a gold atom, so gold dopants are genuinely safe places to stand and think
- **how long a knocked-out atom survives** before it leaves its site for good — carbon is out in half a second, gold hangs on four times as long
- **how far drifting atoms wobble** — a nod to Debye–Waller thermal motion

Which means the level design falls out of the material rather than out of a difficulty knob.

## Swapping in real data

The lattice is synthetic today, but it's generated behind a deliberate seam. `generateSyntheticLattice()` emits an array of:

```js
{ x, y, element, intensity }
```

Match that shape with a real ptychography reconstruction export and it drops in without touching game logic. `renderTargetImage()` is the other swap point — it draws the procedural false-colour reveal image that a real reconstruction would replace.

## Look

Everything on screen is meant to be the instrument, drawn. The probe is a real ray diagram — electrons stream down the illumination cone and converge on a focal spot ringed by its own Airy pattern, with the transmitted cone heading for the detector below. Unresolved sites are speckle clouds that haven't converged. Dose is an arc winding around a column toward knock-out. A raster line sweeps down the frame trailing a decaying glow, because this is a scanning microscope. Gold glows harder than carbon because heavier nuclei scatter harder.

Colour carries one meaning each: hue is element identity, and anything warm means you are spending dose or destroying something. The scan-drift hazard is telegraphed in motion — a stretched speckle cloud and a dashed vertical track — rather than by borrowing a colour that already means nitrogen.

Under it: cached sphere sprites, a quarter-res additive bloom pass, three parallax layers, a false-colour phase LUT with the bonding network baked into the hidden image, device-pixel scanlines, film grain, and a DPR-aware canvas so none of it is soft on a retina display. Still one file, still no dependencies.

## Balance

The tuning is measured rather than guessed. Riding one row end to end converges half the lattice for 20 electrons; rows 1 and 4 together reach 100% for 38. Running right and jumping at every edge — which drifts diagonally down the lattice and re-scans ground it has already covered — costs about 1.1 electrons per percent, so ~110 for the same picture. The budget of 100 sits between those two on purpose: sloppy routing runs out short, and row discipline plus blanking are what close the gap.

Sweeping at full speed destroys nothing. Slow to 90 px/s and it costs four columns; slow to 70 and it costs forty-five. Hovering is the only thing the dose model punishes, which is the point.

One fix worth calling out: horizontal damping used to be applied per frame rather than per second, so the probe's top speed depended on your refresh rate — 237 px/s at 30 Hz, 118 at 60, 49 at 144. Above about 90 Hz it could no longer clear a gap in the lattice, which made the game close to unplayable on a 120 Hz display. Top speed is now ~120 px/s on any monitor.

## More

[`DESIGN.md`](DESIGN.md) has the full design document: mechanics, tuning constants, the measured balance tables, known limitations, and roadmap.
