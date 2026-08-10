"""
Extracts text from a YouTube video given its URL.

Strategy:
  1. Try to pull existing captions/auto-captions via yt-dlp (fast, no
     audio download or transcription needed).
  2. If no captions are available, fall back to downloading just the
     audio track and transcribing it with Whisper.

Requires the `ffmpeg` binary to be installed and on PATH (yt-dlp uses it
for audio extraction in the fallback path).
"""

import os
import re
import tempfile
import uuid

import yt_dlp

from audio_processor import transcribe_audio


def extract_text_from_youtube(url: str) -> str:
    if not url or not url.strip():
        raise ValueError("A YouTube URL is required.")

    caption_text = _try_captions(url)
    if caption_text:
        return caption_text

    return _transcribe_audio_track(url)


def _try_captions(url: str) -> str | None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_template = os.path.join(tmp_dir, "%(id)s.%(ext)s")
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-US", "en-GB"],
            "subtitlesformat": "vtt",
            "quiet": True,
            "no_warnings": True,
            "outtmpl": out_template,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception:
            return None

        video_id = info.get("id") if info else None
        if not video_id:
            return None

        for fname in os.listdir(tmp_dir):
            if fname.startswith(video_id) and fname.endswith(".vtt"):
                return _vtt_to_text(os.path.join(tmp_dir, fname))

    return None


def _vtt_to_text(path: str) -> str:
    lines: list[str] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
                continue
            if "-->" in line:
                continue
            if line.isdigit():
                continue
            # strip inline VTT tags like <00:00:01.234><c> word</c>
            line = re.sub(r"<[^>]+>", "", line).strip()
            if line:
                lines.append(line)

    # auto-captions repeat the previous line as a rolling window; collapse
    # consecutive duplicates so the transcript isn't full of repeats
    deduped: list[str] = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)

    return " ".join(deduped).strip()


def _transcribe_audio_track(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_path = os.path.join(tmp_dir, uuid.uuid4().hex)
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": base_path + ".%(ext)s",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }
            ],
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        audio_path = base_path + ".wav"
        if not os.path.exists(audio_path):
            raise RuntimeError("Couldn't download audio for this YouTube video.")

        return transcribe_audio(audio_path)
