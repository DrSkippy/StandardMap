"""Shared pytest fixtures; forces SDL into headless mode before pygame loads."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
