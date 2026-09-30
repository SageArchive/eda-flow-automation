import json
from pathlib import Path

import pytest

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "flow" / "configs"

REQUIRED_KEYS = {"variant_name", "description", "top_module", "clock_period_ns", "params"}
REQUIRED_PARAM_KEYS = {
    "ENABLE_MUL",
    "ENABLE_FAST_MUL",
    "ENABLE_DIV",
    "BARREL_SHIFTER",
    "ENABLE_IRQ",
    "COMPRESSED_ISA",
}


def all_config_paths():
    return sorted(CONFIGS_DIR.glob("*.json"))


@pytest.mark.parametrize("config_path", all_config_paths(), ids=lambda p: p.stem)
def test_config_has_required_top_level_keys(config_path):
    config = json.loads(config_path.read_text())
    missing = REQUIRED_KEYS - config.keys()
    assert not missing, f"{config_path.name} is missing keys: {missing}"


@pytest.mark.parametrize("config_path", all_config_paths(), ids=lambda p: p.stem)
def test_config_params_are_binary_flags(config_path):
    config = json.loads(config_path.read_text())
    missing = REQUIRED_PARAM_KEYS - config["params"].keys()
    assert not missing, f"{config_path.name} params missing: {missing}"

    for name, value in config["params"].items():
        if name not in ("MASKED_IRQ", "LATCHED_IRQ", "PROGADDR_RESET", "PROGADDR_IRQ", "STACKADDR"):
            assert value in (0, 1), f"{config_path.name}: {name}={value} is not a 0/1 flag"


@pytest.mark.parametrize("config_path", all_config_paths(), ids=lambda p: p.stem)
def test_config_clock_period_is_positive(config_path):
    config = json.loads(config_path.read_text())
    assert config["clock_period_ns"] > 0


def test_variant_names_are_unique():
    names = [json.loads(p.read_text())["variant_name"] for p in all_config_paths()]
    assert len(names) == len(set(names)), "Duplicate variant_name across config files"
