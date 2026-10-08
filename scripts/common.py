"""Shared paths for the english-video-notes scripts. Run everything with `py -3.13`."""
import json
import os
import sys

HOME = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "english-video-notes")
DEPS = os.path.join(HOME, "deps")      # faster-whisper, imageio-ffmpeg, numpy (pip install --target)
MODELS = os.path.join(HOME, "models")  # Whisper model cache
if os.path.isdir(DEPS):
    sys.path.insert(0, DEPS)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
