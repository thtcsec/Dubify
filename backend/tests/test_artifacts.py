import pytest

pytest.importorskip("pydantic_settings")

from app.utils.artifacts import persist_dubbing_artifacts, resolve_artifact_paths


def test_persist_and_resolve_artifacts(tmp_path, monkeypatch):
    from app.core import config

    artifacts_root = tmp_path / "artifacts"
    temp_root = tmp_path / "temp"
    artifacts_root.mkdir()
    temp_root.mkdir()
    monkeypatch.setattr(config.settings, "ARTIFACTS_DIR", artifacts_root)
    monkeypatch.setattr(config.settings, "TEMP_DIR", temp_root)

    job_id = "job-test"
    session = temp_root / job_id
    session.mkdir()
    (session / "translated.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")

    dest = persist_dubbing_artifacts(job_id, session)
    assert dest is not None
    assert (artifacts_root / job_id / "translated.srt").exists()

    resolved = resolve_artifact_paths(job_id)
    assert resolved["subtitle_path"] == artifacts_root / job_id / "translated.srt"
