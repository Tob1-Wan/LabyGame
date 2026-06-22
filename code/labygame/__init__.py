"""LabyGame - an endless maze runner.

Package layout (see CLAUDE.md for the full guide):

    tiles.py     shared constants: cell codes, TILE size, paths, tile lookup
    config.py    runtime tunables (screen, speed, hitbox, colours)
    settings.py  read/write res/data/settings.json

    maze.py      pure-data maze generation (no pygame)
    autotile.py  pick a wall art tile from its neighbours
    baking.py    render a grid to PNGs (maze + background)
    levels.py    create-or-load a level; resolve style from lvl.json

    level.py     runtime Level: loads baked assets, scales, draws background
    player.py    animated player sprite
    app.py       Game: window, input, update loop, rendering, HUD
    events/      modular event tiles (base class + registry + concrete events)
"""
