"""Modular event-tile framework.

An event tile sits on a walkable cell and reacts when the player stands on it and
triggers it (E). Add a new kind by subclassing :class:`EventTile`, decorating it
with ``@register("name")`` and putting that name in a level's ``events`` list in
lvl.json -- nothing else in the engine changes.

The generator emits plain dicts (``{"type", "x", "y", ...}``); the runtime calls
:func:`create` to turn each into a live object bound to loaded textures.
"""
EVENT_REGISTRY = {}
_warned = set()


def register(name):
    def deco(cls):
        cls.type_name = name
        EVENT_REGISTRY[name] = cls
        return cls
    return deco


def create(data, assets):
    """Instantiate the event described by ``data``. Returns ``None`` for an
    unregistered type (so an unknown name in lvl.json just leaves that cell
    inert instead of crashing)."""
    name = data["type"]
    cls = EVENT_REGISTRY.get(name)
    if cls is None:
        if name not in _warned:
            _warned.add(name)
            print(f"[events] no event registered for type {name!r}; skipping")
        return None
    return cls(data, assets)


class EventTile:
    """Base class for everything placeable as an event.

    Override :meth:`update`, :meth:`draw` and :meth:`on_trigger`. The base keeps
    the grid position and serialisable state in sync (``self.data``).
    """
    type_name = "event"

    def __init__(self, data, assets):
        self.x = data["x"]
        self.y = data["y"]
        self.data = data          # backing dict, kept in sync for saving
        self.assets = assets
        self.triggered = bool(data.get("dug", False))

    def update(self, dt):
        """Advance animation (dt in seconds)."""

    def draw(self, surface, screen_pos, tile_px):
        """Draw at ``screen_pos`` (top-left px) sized to ``tile_px``."""

    def on_trigger(self, game):
        """Called once when triggered. Return an optional HUD message and mutate
        ``self.data`` so progress is saved."""
        return None

    def trigger(self, game):
        if self.triggered:
            return None
        self.triggered = True
        self.data["dug"] = True
        return self.on_trigger(game)

    def to_dict(self):
        return self.data
