import os
from dataclasses import dataclass

from config import settings

AUDIO_EXTS = {".mp3", ".wav", ".m4a"}
VIDEO_EXTS = {".mp4"}
SUPPORTED_MEDIA = ".mp3 .wav .m4a .mp4"


@dataclass
class TextUnit:
    text: str
    source_file: str
    timestamp: float = None
    transcribed: bool = True


def is_media(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in AUDIO_EXTS or ext in VIDEO_EXTS


def load_media(path):
    if not os.path.isfile(path):
        raise ValueError(f"file not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    source = os.path.basename(path)

    if ext in AUDIO_EXTS:
        return load_audio(path, source)
    if ext in VIDEO_EXTS:
        if not settings.VIDEO_ENABLED:
            raise ValueError("video ingestion is disabled; set VIDEO_ENABLED=true to enable it")
        return load_video(path, source)
    raise ValueError(f"unsupported media type: {ext}. supported: {SUPPORTED_MEDIA}")


def load_audio(path, source):
    return _segments_to_units(_transcribe(path), source)


def load_video(path, source):
    audio_path = _extract_audio(path)
    try:
        return load_audio(audio_path, source)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


def _segments_to_units(segments, source, window_chars=800):
    units = []
    buf = []
    buf_len = 0
    start_ts = None
    for start, text in segments:
        text = text.strip()
        if not text:
            continue
        if start_ts is None:
            start_ts = start
        buf.append(text)
        buf_len += len(text)
        if buf_len >= window_chars:
            units.append(TextUnit(text=" ".join(buf), source_file=source,
                                  timestamp=round(start_ts, 1), transcribed=True))
            buf, buf_len, start_ts = [], 0, None
    if buf:
        units.append(TextUnit(text=" ".join(buf), source_file=source,
                              timestamp=round(start_ts or 0.0, 1), transcribed=True))
    return units


def _transcribe(path):
    provider = settings.ASR_PROVIDER
    if provider == "local":
        return _asr_local(path)
    if provider == "groq":
        return _asr_groq(path)
    raise ValueError(f"invalid ASR_PROVIDER: {provider}")


def _asr_local(path):
    from faster_whisper import WhisperModel

    model = WhisperModel(settings.ASR_MODEL)
    segments, _ = model.transcribe(path)
    return [(seg.start, seg.text) for seg in segments]


def _asr_groq(path):
    from groq import Groq

    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")
    client = Groq(api_key=settings.GROQ_API_KEY)
    with open(path, "rb") as fh:
        result = client.audio.transcriptions.create(
            file=(os.path.basename(path), fh.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
        )
    segments = result.segments or []
    return [(s["start"], s["text"]) for s in segments]


def _extract_audio(video_path):
    import subprocess
    import tempfile

    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        [ffmpeg, "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", out],
        check=True,
        capture_output=True,
    )
    return out
