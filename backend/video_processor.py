"""
Extracts spoken text from a video file by pulling out the audio track
with ffmpeg, then transcribing that audio with Whisper.

Requires the `ffmpeg` binary to be installed and on PATH.
"""

import os
import subprocess
import uuid
import tempfile

from audio_processor import transcribe_audio


def extract_text_from_video(video_path: str) -> str:
    audio_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.wav")
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                audio_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed to extract audio from video: {result.stderr.decode(errors='ignore')[-500:]}"
            )
        return transcribe_audio(audio_path)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
