import json
import os
import sys


def _load():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "config.json")) as f:
        return json.load(f)


_data = _load()


class Config:
    DATABASE_NAME = _data.get("DATABASE_NAME", "")
    DATABASE_USER = _data.get("DATABASE_USER", "")
    DATABASE_PASSWORD = _data.get("DATABASE_PASSWORD", "")
    DATABASE_HOST = _data.get("DATABASE_HOST", "")
    DATABASE_PORT = _data.get("DATABASE_PORT", "3306")
