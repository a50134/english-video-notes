"""Get audio.mp3 and subtitles for one video into a work folder.

  py -3.13 fetch.py <url> <workdir>              download audio + subtitles with yt-dlp
  py -3.13 fetch.py <url> <workdir> --check      only show title, length and which subtitles exist
  py -3.13 fetch.py <file> <workdir> [--subs x.srt] [--zh-subs y.srt]   use files already on disk

Writes audio.mp3, en.<ext> / zh.<ext> when found, and meta.json.
"""
import argparse
import glob
import os
import shutil
import subprocess

import common

EN = ["en", "en-US", "en-GB", "en-CA", "en-AU", "en-orig"]
ZH = ["zh-TW", "zh-Hant", "zh-HK", "zh", "zh-Hans", "zh-CN"]


def pick(table, wanted):
    for lang in wanted:
        if table.get(lang):
            return lang
    for lang in table:  # e.g. en-j3PyPqV-e1s
        if lang.split("-")[0] == wanted[0].split("-")[0] and table[lang]:
            return lang
    return None


def to_mp3(src, dst):
    subprocess.run([common.ffmpeg(), "-v", "error", "-y", "-i", src, "-vn", "-c:a", "libmp3lame", "-q:a", "4", dst], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("workdir")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--subs")
    ap.add_argument("--zh-subs")
    a = ap.parse_args()
    os.makedirs(a.workdir, exist_ok=True)
    meta = {"source": a.source, "enSubs": None, "enSubsKind": "none", "zhSubs": None}

    if os.path.exists(a.source):
        meta["title"] = os.path.splitext(os.path.basename(a.source))[0]
        to_mp3(a.source, os.path.join(a.workdir, "audio.mp3"))
        for key, path, name in (("enSubs", a.subs, "en"), ("zhSubs", a.zh_subs, "zh")):
            if path:
                dst = name + os.path.splitext(path)[1].lower()
                shutil.copyfile(path, os.path.join(a.workdir, dst))
                meta[key] = dst
        if a.subs:
            meta["enSubsKind"] = "manual"
    else:
        import yt_dlp
        base = {"quiet": True, "no_warnings": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(base) as y:
            info = y.extract_info(a.source, download=False)
        manual, auto = info.get("subtitles") or {}, info.get("automatic_captions") or {}
        en, zh = pick(manual, EN), pick(manual, ZH)
        meta.update(title=info.get("title"), id=info.get("id"), duration=info.get("duration"), uploader=info.get("uploader"))
        meta["enSubsKind"] = "manual" if en else ("auto" if pick(auto, EN) else "none")
        print("title   :", meta["title"])
        print("length  : %s s" % meta["duration"])
        print("en subs :", meta["enSubsKind"], en or "")
        print("zh subs :", zh or "none")
        if a.check:
            return
        langs = [x for x in (en, zh) if x]
        opts = dict(base, format="bestaudio/best", outtmpl=os.path.join(a.workdir, "source.%(ext)s"),
                    writesubtitles=bool(langs), subtitleslangs=langs, subtitlesformat="vtt/srt/best",
                    ffmpeg_location=common.ffmpeg())
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([a.source])
        for key, lang, name in (("enSubs", en, "en"), ("zhSubs", zh, "zh")):
            hit = glob.glob(os.path.join(glob.escape(a.workdir), "source.%s.*" % lang)) if lang else []
            if hit:
                dst = name + os.path.splitext(hit[0])[1]
                os.replace(hit[0], os.path.join(a.workdir, dst))
                meta[key] = dst
        media = [p for p in glob.glob(os.path.join(glob.escape(a.workdir), "source.*"))]
        to_mp3(media[0], os.path.join(a.workdir, "audio.mp3"))
        os.remove(media[0])

    common.dump(meta, os.path.join(a.workdir, "meta.json"))
    print("saved   :", os.path.join(a.workdir, "audio.mp3"))
    if meta["enSubsKind"] != "manual":
        print("note    : no human-made English subtitles; segment.py will use the speech-recognition text, so proofread it.")


if __name__ == "__main__":
    main()
