"""Spread the kept sentences over the study days and cut one audio clip per sentence.

  py -3.13 plan.py <workdir> --days 10          9 learning days + Day 10 for review
  py -3.13 plan.py <workdir> --days 10 --only Day3-07,Day3-08    re-cut just these after editing plan.json

Reads sentences.json (rows with "skip": true are left out). Writes plan.json and clips/Day<D>-<NN>.mp3.
To fix a clip that starts late or ends early, change its "s"/"e" in plan.json and run again with --only.
"""
import argparse
import os
import subprocess

import common


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("--days", type=int, required=True)
    ap.add_argument("--only")
    a = ap.parse_args()
    work, plan_path = a.workdir, os.path.join(a.workdir, "plan.json")
    clips = os.path.join(work, "clips")
    os.makedirs(clips, exist_ok=True)

    if a.only:
        plan = common.load(plan_path)
    else:
        kept = [s for s in common.load(os.path.join(work, "sentences.json")) if not s.get("skip")]
        n = max(1, a.days - 1)
        base, extra = divmod(len(kept), n)
        plan, i = {"title": common.load(os.path.join(work, "meta.json")).get("title"), "totalDays": a.days, "days": {}}, 0
        for d in range(1, n + 1):
            k = base + (1 if d <= extra else 0)
            plan["days"][str(d)] = [dict({"clip": "Day%d-%02d" % (d, j + 1)}, **{f: s[f] for f in ("id", "en", "s", "e", "conf", "zhSub") if f in s})
                                    for j, s in enumerate(kept[i:i + k])]
            i += k
        for f in os.listdir(clips):
            os.remove(os.path.join(clips, f))
        common.dump(plan, plan_path)

    only = set(a.only.split(",")) if a.only else None
    audio, done = os.path.join(work, "audio.mp3"), 0
    for d, rows in plan["days"].items():
        for r in rows:
            if only and r["clip"] not in only:
                continue
            res = subprocess.run([common.ffmpeg(), "-v", "error", "-y", "-ss", str(r["s"]), "-t", str(round(r["e"] - r["s"], 2)), "-i", audio, "-vn",
                                  "-c:a", "libmp3lame", "-q:a", "4", os.path.join(clips, r["clip"] + ".mp3")], capture_output=True, text=True)
            if res.returncode:
                print("FAIL", r["clip"], res.stderr[:200])
            else:
                done += 1
    print("days:", ", ".join("Day %s = %d" % (d, len(r)) for d, r in plan["days"].items()), "| review day: Day %d" % plan["totalDays"])
    print("clips cut:", done, "->", clips)


if __name__ == "__main__":
    main()
