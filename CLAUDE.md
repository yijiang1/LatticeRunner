# Lattice Runner

A 2D platformer about electron ptychography: the probe you see with is the beam
that does the damage. The whole game is one file, `index.html` (~5.3k lines:
CSS, one HTML skeleton of DOM overlays, then the JS sim + renderer in an IIFE).

## Hard invariants — do not break these without being asked

- **One self-contained file.** No build step, no bundler, no `package.json`, no
  `node_modules`, no external requests. `index.html` opens straight in a browser
  and also gets fetched as-is by PtychoHub's Kids proxy. Nothing may be split
  out, and nothing may be pulled in over the network (no CDN scripts, fonts,
  images). Assets are generated at runtime (canvas sprites, WebAudio synthesis).
- **No framework, no dependencies.** Plain DOM + canvas 2D + WebAudio. Don't
  introduce a library or a build step to "clean things up".
- **`localStorage` is optional.** Every read/write is wrapped so the game runs
  with storage unavailable — it just won't remember. Keep it that way.
- **Keyboard only.** No mouse-driven gameplay (the specimen designer's
  drag-to-paint is the one exception, and it's editor-only). No touch controls.
- **Knock-out is permanent, in every mode.** That's the specimen, not a
  difficulty setting — see Design Principle 10 in `DESIGN.md`. A mode may change
  *what is scarce* (electrons / seconds / nothing) and *what counts as solved*,
  never the physics.

## Where things live in `index.html`

The JS is one IIFE with `// ====` banner comments between phases. Search by
symbol, not line number — the file churns.

| Concern | Anchor |
|---|---|
| Atomic mass → behaviour | `ATOMIC_MASS`, `vibrationFactor()` |
| Shipped lattices | `SPECIMENS` array; `graphene()`, `scandate()` build them |
| Perovskite site classes | `SCANDATE_SITES` (3-symbol edit swaps the crystal) |
| Data contract for a lattice | atom = `{ x, y, element, intensity, r?, wobble?, dopant?, dopantDef? }` |
| Tuning constants | the `DOSE_*` / `RESOLVE_*` / `REALIGN_*` / `BEAM_DRAIN` / `WIN_FRAC` block |
| Modes | `MODES`, `applyMode()` |
| Upgrades | `UPGRADES`, `currentValue()`, `applyUpgrades()` — effective values are `*Eff` (e.g. `resolveRadiusEff`) |
| Logbook / boards | `BOARDS`, `logRun()`, `sanitiseLog()`, `logKey()` |
| Specimen designer | `activeDesign()`, `designAtoms()`, `sandboxSpecimen()`; reachability walker near "THE SPECIMEN DESIGNER" banner |
| Sim step | `update(dt)` — `dt` is variable, clamped at 0.033 |
| Render | `draw()` and the `ART PIPELINE` / `RENDER` banners |
| Save | `SAVE_KEY = "latticeRunner.v1"`, `writeSave()` |

### The seams that must stay clean

- **`SPECIMENS` contract.** A new specimen is a `build()` returning the atom
  array above, plus `spawn` (index of the pre-resolved column the probe drops
  onto — the first landing must be safe). `loadSpecimen()` rebuilds *everything*
  derived (world geometry, fog, hidden phase image, survey scan, win count);
  nothing holds a reference across that call. A player's drawn lattice goes
  through the exact same path via `sandboxSpecimen()` — id `"sandbox"`. If
  `update()` ever needs to special-case a sandbox specimen, the seam is broken
  (Design Principle 11).
- **`renderTargetImage()`** draws the hidden reveal picture from the specimen's
  own columns — a specimen brings its picture with it, no matching bitmap.
- **Physics is load-bearing, not flavour.** `vibrationFactor = √(m_C / m)` drives
  three separate behaviours: dose an atom survives, how long a knocked-out atom
  lingers, and drift amplitude. Level design falls out of the material. Don't
  add a difficulty knob where a mass would do.

## Tuning constants are measured, not guessed

`DOSE_BUDGET`, `REALIGN_COST`, `WIN_FRAC`, `RESOLVE_TIME`, and the collision
width multiplier are calibrated by driving the shipped sim headlessly at a fixed
timestep. The canonical results live in `DESIGN.md` → **Core Mechanics →
Balance (measured)**. Load-bearing numbers to preserve the meaning of:

- Two rows ridden end to end solve the lattice (86%) for ~33 electrons — that's
  the floor `DOSE_BUDGET = 100` is set against.
- Blanking is worth ~30 percentage points and ~20 columns vs. beam-always-on.
  That gap is the game.
- Sweeping at ≥90 px/s destroys nothing; 70 px/s costs ~36 columns. "Keep
  scanning, don't hover" must survive any change.

If you change one of these constants, **bump `BALANCE_VERSION`** — boards are
keyed by it, and old entries are retired rather than re-ranked. The headless
harness itself is **not committed** (there's a guard seam for it in the audio
init and elsewhere, but no runnable script in the repo); if a task needs balance
numbers, expect to write the driver.

The perovskite scandate specimen ships **un-balance-tested** — its constants are
the carbon sheet's on a stated argument. Don't quote its `WIN_FRAC` as verified.

## Conventions

- **Comment voice.** Comments are flowing prose explaining *why*, often several
  sentences, lowercase, essayistic — "the lockup is used twice: over the game,
  and at the head of the bench". Match that register; don't add terse `// set x`
  noise.
- Keep `README.md` and `DESIGN.md` accurate when behaviour changes — `DESIGN.md`
  is the real design doc (mechanics, tuning tables, `## Known Limitations`,
  `## Roadmap`, `## Design Principles`), `README.md` is the player-facing
  overview.
- Commit only when asked. Branch first if on `main`.
