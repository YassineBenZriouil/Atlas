import pytest

from atlas.windows.keyboard import key_to_vk, normalize_key


def test_normalize_alias():
    assert normalize_key("control") == "ctrl"
    assert normalize_key("Escape") == "esc"


def test_key_to_vk_letter():
    assert key_to_vk("c") == ord("C")


def test_key_to_vk_digit():
    assert key_to_vk("5") == ord("5")


def test_key_to_vk_special():
    assert key_to_vk("enter") != 0
    assert key_to_vk("control") == key_to_vk("ctrl")


def test_key_to_vk_space():
    assert key_to_vk(" ") == key_to_vk("space")


def test_key_to_vk_function_key():
    assert key_to_vk("f1") != key_to_vk("f2")


def test_key_to_vk_unknown_raises():
    with pytest.raises(ValueError):
        key_to_vk("thisisnotakey")
