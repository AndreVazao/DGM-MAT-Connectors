from pathlib import Path

from dgm_mat_connectors import ObsidianConnector


def test_index_and_export(tmp_path: Path):
    connector = ObsidianConnector(tmp_path / "vault")
    note = connector.vault_path / "memory" / "hello.md"
    note.write_text("# Hello\n\nSee [[World]] #test", encoding="utf-8")

    result = connector.index_vault()

    assert result["total_notes"] == 1
    assert result["notes"][0]["links"] == ["World"]
    assert "#test" in result["notes"][0]["tags"]
    assert connector.export_to_markdown("missions", "mission_1", "# Mission")
    assert (connector.vault_path / "missions" / "mission_1.md").exists()


def test_create_mission_note(tmp_path: Path):
    connector = ObsidianConnector(tmp_path / "vault")
    assert connector.create_mission_note(
        {"id": "m1", "title": "Test Mission", "status": "PENDING", "objective": "Validate"}
    )
    content = (connector.vault_path / "missions" / "mission_m1.md").read_text(encoding="utf-8")
    assert "Test Mission" in content
    assert "Validate" in content
