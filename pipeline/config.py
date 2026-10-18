"""Paths and config loading."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
RUNS_DIR = ROOT / "runs"


def load_yaml(name):
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_niches(include_inactive=False):
    """Niches the channel posts in; those with `active: false` only when asked for."""
    niches = load_yaml("niches.yaml")["niches"]
    return niches if include_inactive else [n for n in niches if n.get("active", True)]


def load_platforms():
    return load_yaml("platforms.yaml")


def niche_by_id(niche_id, niches=None):
    for niche in niches if niches is not None else load_niches(include_inactive=True):
        if niche["id"] == niche_id:
            return niche
    raise KeyError(f"unknown niche: {niche_id}")


def strategy_weights(prod_cfg=None):
    """Niche-ranking weights for the current strategy phase (config/production.yaml)."""
    strategy = (prod_cfg or load_yaml("production.yaml")).get("strategy") or {}
    return (strategy.get("phases") or {}).get(strategy.get("phase"), {})
