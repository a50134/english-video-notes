"""Report which tools the skill needs are present. Installs nothing."""
import importlib
import os

import common

missing = []
for mod, pip in (("yt_dlp", "yt-dlp"), ("faster_whisper", "faster-whisper"), ("imageio_ffmpeg", "imageio-ffmpeg"), ("numpy", "numpy")):
    try:
        importlib.import_module(mod)
        print("ok      ", pip)
    except Exception as e:
        print("MISSING ", pip, "-", str(e)[:80])
        missing.append(pip)

has_model = any("model.bin" in fs for _, _, fs in os.walk(common.MODELS))
print("ok       whisper model" if has_model else "MISSING  whisper model (downloaded from Hugging Face on first run of segment.py, about 460 MB)")
if missing:
    print("\nAsk the user before installing, then run:")
    print('py -3.13 -m pip install --target "%s" %s' % (common.DEPS, " ".join(missing)))
