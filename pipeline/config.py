"""Paths and config loading."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
RUNS_DIR = ROOT / "runs"


def load_yaml(name):
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_niches():
    return load_yaml("niches.yaml")["niches"]


def load_platforms():
    return load_yaml("platforms.yaml")


def niche_by_id(niche_id, niches=None):
    for niche in niches if niches is not None else load_niches():
        if niche["id"] == niche_id:
            return niche
    raise KeyError(f"unknown niche: {niche_id}")
