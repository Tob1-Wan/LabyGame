# runned by:    py -3.13 ./code/main.py
"""Entry point. The game lives in the ``labygame`` package (see CLAUDE.md)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # make 'labygame' importable

from labygame.app import Game

if __name__ == "__main__":
    Game().run()
