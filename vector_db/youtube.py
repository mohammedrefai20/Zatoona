"""Free, no-key YouTube fetching: existing captions first, audio ASR as a fallback.

Captions come from youtube-transcript-api; playlist enumeration and the no-captions audio
download use yt-dlp. The audio fallback reuses the feature-002 ASR pipeline (loaders._transcribe).

# future: youtube-transcript-api occasionally breaks when YouTube changes its player; if that
# happens, swap to yt-dlp's `--write-auto-sub` to pull the caption track instead.
"""

import os
import shutil
from urllib.parse import parse_qs, urlparse

from config import settings
from vector_db import loaders

_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
_TMP_PREFIX = "ytaudio_"


def is_youtube_url(s):
    try:
        return urlparse(s).netloc.lower() in _HOSTS
    except ValueError:
        return False


def parse_target(url):
    if not is_youtube_url(url):
        raise ValueError(f"not a recognized YouTube video or playlist URL: {url}")

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    list_id = qs.get("list", [None])[0]

    if parsed.netloc.lower() == "youtu.be":
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif parsed.path.startswith("/playlist"):
        if not list_id:
            raise ValueError(f"not a recognized YouTube video or playlist URL: {url}")
        return "playlist", url
    else:
        video_id = qs.get("v", [None])[0]

    # A Radio/Mix (list=RD...) accompanies a single video; any other list is the whole playlist.
    if list_id and not list_id.startswith("RD"):
        return "playlist", url
    if video_id:
        return "video", video_id
    raise ValueError(f"not a recognized YouTube video or playlist URL: {url}")


def fetch_transcript(video_id):
    raw = _raw_caption(video_id)
    if not raw:
        return []
    segments, is_generated = raw
    units = loaders._segments_to_units(segments, video_id)
    for unit in units:
        unit.transcribed = is_generated
    return units


def _raw_caption(video_id):
    """Network seam. Returns (segments, is_generated) or None when no usable captions exist.

    Prefers a manually-created track, then auto-generated, honoring YOUTUBE_TRANSCRIPT_LANGS.
    Raises ValueError when the video itself is unavailable/private/removed/region-blocked.
    """
    from youtube_transcript_api import (
        CouldNotRetrieveTranscript,
        NoTranscriptFound,
        TranscriptsDisabled,
        YouTubeTranscriptApi,
    )

    langs = settings.YOUTUBE_TRANSCRIPT_LANGS
    try:
        transcripts = YouTubeTranscriptApi().list(video_id)
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except CouldNotRetrieveTranscript as exc:
        raise ValueError(f"YouTube video {video_id} is unavailable: {exc}") from exc

    try:
        transcript = transcripts.find_manually_created_transcript(langs)
    except NoTranscriptFound:
        try:
            transcript = transcripts.find_generated_transcript(langs)
        except NoTranscriptFound:
            return None

    fetched = transcript.fetch()
    return [(snippet.start, snippet.text) for snippet in fetched], transcript.is_generated


def list_playlist(playlist_url):
    entries = _flat_playlist(playlist_url)
    ids = [e["id"] for e in entries if e and e.get("id")]
    if not ids:
        raise ValueError(f"playlist is empty or unavailable: {playlist_url}")
    return ids[: settings.YOUTUBE_PLAYLIST_MAX]


def _flat_playlist(playlist_url):
    import yt_dlp

    opts = {"extract_flat": True, "skip_download": True, "quiet": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise ValueError(f"could not read playlist {playlist_url}: {exc}") from exc
    return info.get("entries") or []


def audio_fallback(video_id):
    path = _download_audio(video_id)
    try:
        units = loaders._segments_to_units(loaders._transcribe(path), video_id)
        for unit in units:
            unit.transcribed = True
        return units
    finally:
        _cleanup(path)


def _download_audio(video_id):
    import tempfile

    import yt_dlp

    tmpdir = tempfile.mkdtemp(prefix=_TMP_PREFIX)
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ValueError(f"could not download audio for {video_id}: {exc}") from exc

    files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
    if not files:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ValueError(f"could not download audio for {video_id}")
    return files[0]


def _cleanup(path):
    if path and os.path.exists(path):
        os.remove(path)
    parent = os.path.dirname(path or "")
    if os.path.basename(parent).startswith(_TMP_PREFIX):
        shutil.rmtree(parent, ignore_errors=True)
