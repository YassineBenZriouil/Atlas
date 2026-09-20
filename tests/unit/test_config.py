import pytest

from atlas.config.loader import ConfigError, load_config, save_config
from atlas.config.schema import AtlasConfig


def test_load_creates_default_when_missing(tmp_path):
    path = tmp_path / "config.toml"
    config = load_config(path)
    assert path.exists()
    assert isinstance(config, AtlasConfig)
    assert config.wake.phrase == "atlas"


def test_round_trip(tmp_path):
    path = tmp_path / "config.toml"
    config = load_config(path)
    config.wake.phrase = "computer"
    save_config(path, config)

    reloaded = load_config(path)
    assert reloaded.wake.phrase == "computer"


def test_corrupt_config_raises(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("not = [valid toml", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_future_version_rejected(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("config_version = 999\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_default_applications_include_known_aliases(tmp_path):
    path = tmp_path / "config.toml"
    config = load_config(path)
    assert "vs code" in config.applications["vscode"].aliases
