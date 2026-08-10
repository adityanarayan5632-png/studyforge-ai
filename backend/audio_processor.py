"""
Transcribes audio files to text using OpenAI's Whisper, run locally.
Requires the `ffmpeg` binary to be installed and on PATH (Whisper shells
out to it internally to decode audio).

Model size is configurable via the WHISPER_MODEL env var (default "base").
Larger models ("small", "medium") are more accurate but slower and use
more memory; pick based on what the host machine can handle.
"""

import os
import whisper

_model = None
_model_name = os.environ.get("WHISPER_MODEL", "base")


def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model(_model_name)
    return _model


def transcribe_audio(audio_path: str) -> str:
    model = _get_model()
    result = model.transcribe(audio_path)
    return result.get("text", "").strip()
