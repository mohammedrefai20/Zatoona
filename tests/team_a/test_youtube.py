import pytest

from vector_db import loaders, youtube


# --- T011: url detection -----------------------------------------------------

@pytest.mark.parametrize("url, expected", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", ("video", "dQw4w9WgXcQ")),
    ("https://youtu.be/dQw4w9WgXcQ", ("video", "dQw4w9WgXcQ")),
    ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", ("video", "dQw4w9WgXcQ")),
    # watch?v=...&list=... is the whole playlist...
    ("https://www.youtube.com/watch?v=VID12345678&list=PL123abc",
     ("playlist", "https://www.youtube.com/watch?v=VID12345678&list=PL123abc")),
    # ...unless it is a Radio/Mix (list=RD...), which is the single video
    ("https://www.youtube.com/watch?v=VID12345678&list=RD123abc", ("video", "VID12345678")),
    ("https://www.youtube.com/playlist?list=PL123abc",
     ("playlist", "https://www.youtube.com/playlist?list=PL123abc")),
])
def test_parse_target_classifies(url, expected):
    assert youtube.is_youtube_url(url)
    assert youtube.parse_target(url) == expected


def test_non_youtube_url_rejected():
    assert not youtube.is_youtube_url("https://vimeo.com/12345")
    with pytest.raises(ValueError):
        youtube.parse_target("https://vimeo.com/12345")


# --- T011: fetch_transcript --------------------------------------------------

def test_fetch_transcript_builds_timestamped_units(monkeypatch):
    monkeypatch.setattr(youtube, "_raw_caption",
                        lambda vid: ([(0.0, "the cell is the basic unit of life"),
                                      (5.0, "mitochondria produce atp")], False))
    units = youtube.fetch_transcript("vid123")

    assert units
    assert all(u.source_file == "vid123" for u in units)
    assert units[0].timestamp is not None
    assert all(u.transcribed is False for u in units)  # manual track is not approximate


def test_fetch_transcript_flags_auto_captions_transcribed(monkeypatch):
    monkeypatch.setattr(youtube, "_raw_caption",
                        lambda vid: ([(0.0, "auto generated caption text here")], True))
    units = youtube.fetch_transcript("vid123")
    assert all(u.transcribed is True for u in units)


def test_fetch_transcript_no_captions_returns_empty(monkeypatch):
    monkeypatch.setattr(youtube, "_raw_caption", lambda vid: None)
    assert youtube.fetch_transcript("vid123") == []


def test_fetch_transcript_unavailable_raises(monkeypatch):
    def boom(vid):
        raise ValueError("YouTube video vid123 is unavailable")
    monkeypatch.setattr(youtube, "_raw_caption", boom)
    with pytest.raises(ValueError):
        youtube.fetch_transcript("vid123")


# --- T012: audio fallback ----------------------------------------------------

def test_audio_fallback_transcribes_and_removes_temp_file(tmp_path, monkeypatch):
    fake = tmp_path / "vid123.m4a"
    fake.write_bytes(b"fake audio bytes")
    monkeypatch.setattr(youtube, "_download_audio", lambda vid: str(fake))
    monkeypatch.setattr(loaders, "_transcribe",
                        lambda p: [(0.0, "spoken intro about cells"), (4.0, "and how they make energy")])

    units = youtube.audio_fallback("vid123")

    assert units
    assert all(u.transcribed is True for u in units)
    assert all(u.source_file == "vid123" for u in units)
    assert not fake.exists()  # temp file cleaned up


def test_audio_fallback_cleans_up_even_when_asr_fails(tmp_path, monkeypatch):
    fake = tmp_path / "vid123.m4a"
    fake.write_bytes(b"fake audio bytes")
    monkeypatch.setattr(youtube, "_download_audio", lambda vid: str(fake))

    def boom(p):
        raise RuntimeError("ASR unavailable")
    monkeypatch.setattr(loaders, "_transcribe", boom)

    with pytest.raises(RuntimeError):
        youtube.audio_fallback("vid123")
    assert not fake.exists()  # no temp file left behind


# --- T017: playlist enumeration ----------------------------------------------

def test_list_playlist_returns_ordered_ids(monkeypatch):
    monkeypatch.setattr(youtube, "_flat_playlist",
                        lambda url: [{"id": "a"}, {"id": "b"}, {"id": "c"}])
    assert youtube.list_playlist("https://www.youtube.com/playlist?list=PL") == ["a", "b", "c"]


def test_list_playlist_caps_at_max(monkeypatch):
    monkeypatch.setattr(youtube.settings, "YOUTUBE_PLAYLIST_MAX", 2)
    monkeypatch.setattr(youtube, "_flat_playlist",
                        lambda url: [{"id": "a"}, {"id": "b"}, {"id": "c"}])
    assert youtube.list_playlist("u") == ["a", "b"]


def test_list_playlist_empty_raises(monkeypatch):
    monkeypatch.setattr(youtube, "_flat_playlist", lambda url: [])
    with pytest.raises(ValueError):
        youtube.list_playlist("u")


def test_list_playlist_unavailable_propagates(monkeypatch):
    def boom(url):
        raise ValueError("playlist is private")
    monkeypatch.setattr(youtube, "_flat_playlist", boom)
    with pytest.raises(ValueError):
        youtube.list_playlist("u")
