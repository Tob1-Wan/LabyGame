# LabyGame — guide for AI assistants

Endless top-down maze runner in **pygame** (Python 3.13). The player is centred on
screen; WASD scrolls the world; reach the goal to advance to a bigger maze. Buried
event tiles can be dug up (SPACE) for items (carrots), bear traps hurt you unless
you trick them, and a wounded player leaves a blood trail. Items and health are
per-play (reset every time a level is (re)entered).

Read this file first — it should be enough to work without reading every module.

## Run
```
py -3.13 ./code/main.py
```
pygame must be on 3.13 (3.14 has no wheels). Controls: **WASD** move, **SPACE** dig,
**E** throw an item at the trap you face (springs a bear_trap), **F11/F** fullscreen,
**ESC** quit.

## Project layout
```
code/
  main.py                 tiny launcher -> labygame.app.Game
  labygame/
    tiles.py              cell codes (WALL/PATH/START/END/EVENT), TILE=16, paths, get_tile()
    config.py             runtime tunables (screen, speed, hitbox, health, blood, colours)
    settings.py           read/write res/data/settings.json
    fonts.py              shared pixel font (one TTF, any size, cached) -> all text
    maze.py               pure-data maze generation + feasible event/trap placement
    autotile.py           wall art id from N/S/E/W neighbour mask
    baking.py             render a grid -> maze PNG (walls only) + static bg PNG
    levels.py             create-or-load a level; resolve style from lvl.json; BAKE_VERSION
    level.py              runtime Level: load baked assets, scale, draw bg/end-tile, is_wall/is_blocked
    player.py             animated Player sprite (keeps facing dir for throws)
    app.py                Game: window, input, update loop, render, HUD, health, blood
    inventory.py          bottom-centre HUD bar: item slots + heart health bar
    events/
      base.py             EventTile base + register()/create() registry
      hidden_loot.py      "hidden_loot" event (dig -> item, no lingering hole)
      carrot.py           "carrot" event (dig -> carrot + sound; leaves a hole)
      bear_trap.py        "bear_trap" event (walk over = -2 hearts; E-throw to disarm safely)
res/
  data/lvl.json           per-level-range style/config (see below)
  data/settings.json      {fullscreen, ...}
  assets/textures/*.png   tilesets, sprites, carrots.png, bear_trap.png, blood.png, vignette.png
  assets/textures/emojis-free/        carrot/item icons + "emoji style ui/" (HUD bar + heart sheet)
  assets/fonts/*.ttf       pixelFont-7-8x14-sproutLands.ttf (the game font)
  assets/sounds/*.mp3      digging.mp3 (carrot dig sound)
  lvls/                   generated: <n>.lvl (JSON grid), <n>.png (maze), <n>_bg.png (static bg)
  sprites/                LEGACY, unused
```

## Data flow
1. `app.Game.load_level(n)` -> `level.Level(n)` -> `levels.get_level(n)`.
2. `levels.get_level`: resolves style from `lvl.json`; if files exist and match
   `BAKE_VERSION` it loads, else `maze.generate` -> `baking.bake` -> save. On a
   cache hit it refreshes runtime-only style fields (`vignette`, `character`) from
   the live lvl.json (see `_RUNTIME_STYLE_FIELDS`) so cosmetic edits apply without
   a rebuild.
3. `Level` loads the baked PNG(s), the live end-tile + outer/background chunks, and
   instantiates event objects from the saved dicts via `events.create`. Every load
   forces each event un-dug / traps re-armed (items are per-play, never carried).
4. `Game` runs the loop: input -> move with collision (`is_blocked`) -> trap damage
   / blood / end-check -> draw.

A level's `.lvl` (the semantic grid) is the single source of truth: the baked
image and collision both derive from it. **Dug/armed state is never persisted** —
`Level.save` was removed; items and health reset on every `load_level`.

## Key conventions
- **Cell codes** (`tiles.py`): 0 wall, 1 path, 2 start, 3 end, 4 event. Walkable =
  not wall. Only walls are baked; the end tile and all events are drawn **live**
  (so they animate and so the 2.5D wall pass never paints them over the player).
- **Tile ids**: `[tileset_index, tile_id]`, `tile_id` is row-major 0-based; column
  count comes from sheet width (wall sheets are 11 wide / 77 tiles). `get_tile`.
- **Coordinates / uniform pixels**: player position is in TILE units
  (scale-independent). `tile_px` is **snapped to an integer multiple of TILE(16)**
  in `Game._on_resize` (`ppt = round(screen_h/(VISIBLE_TILES_V*TILE))`,
  `tile_px = ppt*TILE`), so one texture pixel = `ppt` screen pixels everywhere —
  one uniform pixel grid for tiles, sprites, blood, the end tile. ~16 tiles fit
  vertically; the exact count varies slightly with the snap. Camera centres the
  player. Draw world art at `round(ox + tex_pixel*ppt)` to stay on the grid.
- **player_tile()**: uses the **feet** position `int(pty + FEET_DY)`, not the
  sprite centre, so digging / end / trap detection match where the player stands.
- **Maze**: perfect maze (recursive backtracker) with a solid wall border ring;
  start/end are the two ends of the longest path (double BFS).
- **2.5D**: walls draw over the player only below the foot line (`GROUND_CLIP`).
  Collision uses a small feet hitbox; walls are shrunk by `WALL_INSET`.
  `Level.is_blocked` = wall OR a solid event (currently nothing is solid).

## Events
EventTile base (`events/base.py`) holds grid pos + serialisable `data`; the
generator emits plain dicts, the runtime builds objects via `events.create`.
- **hidden_loot** / **carrot**: dug with SPACE when standing on them. Carrot plays
  `digging.mp3`, collects a `"carrot"` (shown in the HUD), and leaves a hole frame.
- **bear_trap** (`data["armed"]`): the 4-frame `bear_trap.png` (0 idle, 1-3 snap).
  Armed traps are **walkable but dangerous**: stepping on one springs it and opens a
  bleeding wound (`Game.bleeding += TRAP_BLEED`; see Health & bleeding). The safe way
  past is to **throw**: stand on the tile in front facing the trap and press E
  (`Game.try_throw`) — consumes one item and disarms it without injury.

### Trap placement (maze._scatter_events)
Candidate path cells (dead-ends preferred) are sorted by distance from start; a
running `surplus = items_so_far - traps_so_far` only allows a trap when
`surplus >= 1`. This guarantees: no trap at spawn, never two traps behind one
item, traps never outnumber items, and every trap is trickable (an item is always
reachable first). `TRAP_TYPES` marks which event names are traps.

## HUD: inventory + health (inventory.py)
`inventory.draw(surface, screen_w, screen_h, counts, health)` draws one bottom-
centre artwork (`emoji style ui/inventory_example_with_slots_2.png`, 304x96) with
six 32x32 item slots and five heart sockets. Item icons (see `_ICONS`/`_SLOTS`,
carrot only for now) go in the slots with a count. `Game.health` is a **float**, so
hearts drain **top-down by whole texture-pixel rows** — for heart `i` the fill is
`clamp(health - i, 0, 1)`, and the bottom `round(14*fill)` rows of the full-heart
overlay (`Inventory_Herat_Spritesheet.png` @ 0,2) are shown over the empty socket.
Other HUD text (level, controls, banner) is drawn in `Game.draw_hud`.

## Health & bleeding (config.py + app.py)
- `Game.health` is a float in hearts (`MAX_HEALTH` max); resets to full on every
  `load_level`.
- Stepping on an armed trap: lose `TRAP_DAMAGE` (half a heart) **instantly**, then
  add `TRAP_BLEED` to `Game.bleeding`.
- **Bleeding** (`Game.bleeding`, intensity >= 0; 0 = not bleeding) does **not**
  clot. Each frame `Game._update_bleeding(dt, moved)` drains
  `bleeding * BLEED_DAMAGE * dt` hearts (slow) and drops a trail while moving
  (spacing `BLOOD_SPACING / bleeding`). It only ends at death (health 0 -> respawn
  via `load_level`) or on reaching the goal (next level resets it). Each extra trap
  raises the intensity, so you bleed out faster. A future bandage item would lower
  `bleeding`.
- **Blood trail**: `_drop_splatter` adds a splatter near the feet stored as integer
  **texture-pixel** coords (grid-snapped); `_draw_blood` draws them at the uniform
  `ppt` scale, **over** the floor and event tiles (drawn after the events loop),
  under walls/player. `blood.png` is a 16x4 strip of four 4x4 splatters. Blood is
  per-level (cleared in `load_level`).

## lvl.json (res/data/lvl.json)
List of blocks; `"lvls": [lo, hi]` is an inclusive level range. Fields: `size`
`[w,h]`, `events` (pool of event type-names incl. `"carrot"`/`"bear_trap"`, `[]` =
none), `end` (`"random"` = longest path, or `[x,y]`), `end_tile`, `character`,
`filenames` (tilesets, walls from `[0]`), `animated_background`, `bg_tile_array`,
`wall_tiles` (mask-name -> id), `vignette`. Past the last range, the last block is
reused and its size grows by `+round(size*0.1)` per level (endless).

`animated_background: true` means `bg_tile_array` are animation frames, tiled live
(no baked bg PNG). `false` means they're random ground variations, baked once.

## Extending
- **New event type**: subclass `EventTile` in `labygame/events/`, decorate with
  `@register("name")`, import it in `events/__init__.py`, add `"name"` to a range's
  `events` in lvl.json. For a trap-like blocker/hazard, also add the name to
  `maze.TRAP_TYPES`. Unknown names are skipped gracefully.
- **New look / size / range**: edit `lvl.json` only.
- **Changed generation/baking or event-data schema**: bump `BAKE_VERSION` in
  `levels.py` so on-disk levels rebuild (currently 8).

## Gotchas
- Head-less generation works (baking uses raw `image.load`, no `convert`); the
  runtime uses `convert`/`convert_alpha` and needs a display.
- Deleting files in `res/lvls/` just causes regeneration on next visit.
- Keep `tile_px` an integer multiple of TILE and draw on the texture-pixel grid —
  fractional scaling/positions break the uniform pixel-art look.
- All text uses `fonts.get(size)` (the pixel TTF) rendered with antialias=False.
