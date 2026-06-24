import pytest

from vector_db import loaders


def test_is_media_detects_audio_and_video():
    assert loaders.is_media("lecture.mp3")
    assert loaders.is_media("lecture.mp4")
    assert not loaders.is_media("notes.pdf")
    assert not loaders.is_media("notes.md")


def test_unsupported_media_raises(tmp_path):
    f = tmp_path / "data.xyz"
    f.write_text("x")
    with pytest.raises(ValueError):
        loaders.load_media(str(f))


def test_missing_file_raises():
    with pytest.raises(ValueError):
        loaders.load_media("nope.mp3")


def test_segments_to_units_windows_with_timestamps():
    segments = [(0.0, "a" * 500), (5.0, "b" * 500), (12.0, "tail")]
    units = loaders._segments_to_units(segments, "lecture.mp3", window_chars=800)

    assert len(units) == 2
    assert units[0].timestamp == 0.0
    assert units[1].timestamp == 12.0
    assert all(u.transcribed for u in units)
    assert all(u.source_file == "lecture.mp3" for u in units)


def test_asr_dispatch_selects_provider(monkeypatch):
    monkeypatch.setattr(loaders.settings, "ASR_PROVIDER", "local")
    monkeypatch.setattr(loaders, "_asr_local", lambda p: [(0.0, "local text")])
    assert loaders._transcribe("a.mp3") == [(0.0, "local text")]

    monkeypatch.setattr(loaders.settings, "ASR_PROVIDER", "groq")
    monkeypatch.setattr(loaders, "_asr_groq", lambda p: [(1.0, "groq text")])
    assert loaders._transcribe("a.mp3") == [(1.0, "groq text")]


def test_invalid_asr_provider_raises(monkeypatch):
    monkeypatch.setattr(loaders.settings, "ASR_PROVIDER", "nope")
    with pytest.raises(ValueError):
        loaders._transcribe("a.mp3")


def test_audio_file_loads_as_transcribed_units(tmp_path, monkeypatch):
    audio = tmp_path / "lecture.mp3"
    audio.write_bytes(b"fake audio")
    monkeypatch.setattr(loaders, "_transcribe", lambda p: [(0.0, "intro to agents"), (8.0, "tool use")])

    units = loaders.load_media(str(audio))

    assert len(units) >= 1
    assert all(u.transcribed for u in units)
    assert units[0].timestamp == 0.0


def test_video_disabled_raises(tmp_path, monkeypatch):
    video = tmp_path / "lecture.mp4"
    video.write_bytes(b"fake video")
    monkeypatch.setattr(loaders.settings, "VIDEO_ENABLED", False)
    with pytest.raises(ValueError):
        loaders.load_media(str(video))


def test_video_enabled_routes_to_video_loader(tmp_path, monkeypatch):
    video = tmp_path / "lecture.mp4"
    video.write_bytes(b"fake video")
    monkeypatch.setattr(loaders.settings, "VIDEO_ENABLED", True)
    monkeypatch.setattr(
        loaders, "load_video",
        lambda path, source: [loaders.TextUnit(text="spoken content", source_file=source, timestamp=0.0, transcribed=True)],
    )

    units = loaders.load_media(str(video))

    assert len(units) == 1
    assert units[0].transcribed is True
