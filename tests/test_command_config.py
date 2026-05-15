import pytest

from whiscode.handsfree import (
    COMMAND_SLOTS,
    CommandConfigError,
    active_command_slots,
    load_command_config,
)


def test_missing_command_config_defaults_all_slots_enabled(tmp_path):
    slots = active_command_slots(tmp_path / "missing.ini", base_dir=tmp_path / "commands")

    assert [slot.name for slot in slots] == [slot.name for slot in COMMAND_SLOTS]
    assert slots[0].path == tmp_path / "commands" / "page-up"


def test_existing_command_config_is_allowlist(tmp_path):
    path = tmp_path / "commands.ini"
    path.write_text("[commands]\npage-up = true\nenter = yes\nshift-tab = false\n")

    enabled = load_command_config(path)
    slots = active_command_slots(path, base_dir=tmp_path / "commands")

    assert enabled["page-up"] is True
    assert enabled["enter"] is True
    assert enabled["shift-tab"] is False
    assert enabled["page-down"] is False
    assert [slot.name for slot in slots] == ["page-up", "enter"]


def test_command_config_rejects_unknown_names(tmp_path):
    path = tmp_path / "commands.ini"
    path.write_text("[commands]\nescape = true\n")

    with pytest.raises(CommandConfigError, match="Unknown command"):
        load_command_config(path)


def test_command_config_rejects_invalid_booleans(tmp_path):
    path = tmp_path / "commands.ini"
    path.write_text("[commands]\nenter = maybe\n")

    with pytest.raises(CommandConfigError, match="Invalid boolean"):
        load_command_config(path)


def test_command_config_requires_commands_section(tmp_path):
    path = tmp_path / "commands.ini"
    path.write_text("[other]\nenter = true\n")

    with pytest.raises(CommandConfigError, match=r"\[commands\]"):
        load_command_config(path)
