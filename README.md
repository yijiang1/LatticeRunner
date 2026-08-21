# Lattice Runner

A 2D platformer about electron ptychography, where the thing you use to see is the thing that does the damage.

You play a scanning probe crossing an atomic lattice. Atom columns are your platforms — but they start as unresolved ghosts and only become solid once you linger nearby long enough, the way a real reconstruction is built up scan position by scan position. Behind a layer of fog sits the true reconstruction image, and every atom you resolve punches a hole in it. The reward is watching the picture emerge.

The catch is the central bargain of electron microscopy: **to see an atom you have to hit it with electrons, and the electrons knock it out.** Proximity is what resolves an atom and proximity is what destroys it — the same act, two consequences. You carry one specimen's worth of dose, and how much of the picture you get to see before the beam runs out is the score.

## Play

Open [`index.html`](index.html) in a browser. No build step, no dependencies, no server — it's one self-contained file.

It also runs inside the [PtychoHub](https://ptychohub.com) Kids section, which fetches this repo's `index.html` through an authenticated proxy route. While this repo is private that card is contributor-only and the route is session-gated, so the game isn't reachable by the public. Making the repo public is the switch that ships it.

## Controls

| Key | Action |
|-----|--------|
| ← → / A D | Move |
| Space / ↑ / W | Jump — coyote time and jump buffering are on, so it forgives near-misses |
| Shift (hold) | Blank the beam: no dose spent, no resolving, atoms cool off |
| R | Restart |

Blanking is the whole skill. Crossing ground you've already scanned costs nothing if the beam is off, so a good run is mostly about routing — not about moving fast.

## The physics is doing real work

Atomic mass isn't flavour text here. A single `vibrationFactor = √(m_C / m)` drives three separate behaviours:

- **how much dose an atom survives** — knock-on damage displaces a light carbon long before it budges a gold atom, so gold dopants are genuinely safe places to stand and think
- **how fast a knocked-out atom flickers** out of solidity
- **how far drifting atoms wobble** — a nod to Debye–Waller thermal motion

Which means the level design falls out of the material rather than out of a difficulty knob.

## Swapping in real data

The lattice is synthetic today, but it's generated behind a deliberate seam. `generateSyntheticLattice()` emits an array of:

```js
{ x, y, element, intensity }
```

Match that shape with a real ptychography reconstruction export and it drops in without touching game logic. `renderTargetImage()` is the other swap point — it draws the procedural false-colour reveal image that a real reconstruction would replace.

## More

[`DESIGN.md`](DESIGN.md) has the full design document: mechanics, tuning constants, known limitations, and roadmap. `DOSE_BUDGET` is the most important number in the game and the one most likely to still be wrong.
