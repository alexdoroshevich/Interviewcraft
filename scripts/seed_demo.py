#!/usr/bin/env python3
"""Redirect to the authoritative seed script in backend/scripts/seed_demo.py.

The seed script lives in backend/ so it can be found inside the Docker container
at /app/scripts/seed_demo.py. This wrapper lets you run it from the repo root.
"""

import runpy
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "backend"))
runpy.run_path(
    str(pathlib.Path(__file__).parent.parent / "backend" / "scripts" / "seed_demo.py"),
    run_name="__main__",
)
