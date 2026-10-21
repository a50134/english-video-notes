"""Build the Notion page text for one day.

  py -3.13 render.py <workdir> todo            list clips that still have no note
  py -3.13 render.py <workdir> <day>           write out/day<D>_chunk<K>.md (needs notes and uploads for that day)
  py -3.13 render.py <workdir> review          write out/review.md for the last day
  py -3.13 render.py <workdir> board           write out/days.json in the pronunciation-board format

Notes live in notes/*.json, each a dict  clip -> {"zh", "grammar": [..], "usage" (optional), "example", "exampleZh"}.
uploads.tsv has one "clip<TAB>file_upload_id" line per uploaded clip (written by upload.sh).
Upload a few clips, then add them with --chunk K, so uploads never sit unused long enough to expire.
Options: --db <url of the 造句口說紀錄 database>  --board <pronunciation board url, "{d}" becomes the day number>
"""
import argparse
import glob
import os

import common

DB = "https://app.notion.com/p/d8c2cbdb50c648b48e5b2b90b7e9550f"
PER_CHUNK = 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("what")
    ap.add_argument("--db", default=DB)
    ap.add_argument("--board")
    ap.add_argument("--chunk", type=int, help="only check and write this chunk (0 = page header, 1.. = 8 sentences each)")
    a = ap.parse_args()
    work = a.workdir
    plan = common.load(os.path.join(work, "plan.json"))
    notes = {}
    for p in sorted(glob.glob(os.path.join(glob.escape(work), "notes", "*.json"))):
        notes.update(common.load(p))
    out = os.path.join(work, "out")
    os.makedirs(out, exist_ok=True)
    last = plan["totalDays"]
    mention = '<mention-database url="%s"/>' % a.db

    def bad(r):
        n = notes.get(r["clip"]) or {}
        return not (n.get("zh") and n.get("grammar") and n.get("example"))

    if a.what == "todo":
        for d, rows in plan["days"].items():
            miss = [r["clip"] for r in rows if bad(r)]
            print("Day %s: %d of %d missing%s" % (d, len(miss), len(rows), (" -> " + ", ".join(miss[:6]) + (" ..." if len(miss) > 6 else "")) if miss else ""))
        return

    if a.what == "board":
        days = {d: [{"en": r["en"], "zh": (notes.get(r["clip"]) or {}).get("zh", ""), "clip": r["clip"]} for r in rows] for d, rows in plan["days"].items()}
        days[str(last)] = [x for d in sorted(plan["days"], key=int) for x in days[d]]
        common.dump(days, os.path.join(out, "days.json"))
        print("wrote", os.path.join(out, "days.json"))
        return

    if a.what == "review":
        md = """## 今天的流程
### ① 複習不熟的句子
- [ ] 打開 %s，篩出 🔴 不熟，每句唸 3 遍
- [ ] 回到 Day 1–%d，把勾了「🔴 不熟」的句子各跟讀 3 遍
### ② 整部影片 Shadowing 5 遍
- [ ] 第 1 遍：0.75 倍速，看稿
- [ ] 第 2 遍：1 倍速，看稿
- [ ] 第 3 遍：1 倍速，看稿
- [ ] 第 4 遍：1 倍速，不看稿
- [ ] 第 5 遍：1 倍速，不看稿，錄音
### ③ 口說
- [ ] 用今天最熟的 5 個句型，各說一個自己的句子並錄音
- [ ] 請 AI 批改，把結果填回造句口說紀錄
## 心得
- 進步最多的地方：
- 還是卡住的 3 句：
""" % (mention, last - 1)
        open(os.path.join(out, "review.md"), "w", encoding="utf-8").write(md)
        print("wrote review.md | title: %s｜Day %d 總複習" % (plan["title"], last))
        return

    d = int(a.what)
    rows = plan["days"][str(d)]
    ups = {}
    tsv = os.path.join(work, "uploads.tsv")
    if os.path.exists(tsv):
        for line in open(tsv, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) == 2:
                ups[p[0]] = p[1]
    need = rows if a.chunk is None else rows[(a.chunk - 1) * PER_CHUNK:a.chunk * PER_CHUNK] if a.chunk else []
    miss_n, miss_u = [r["clip"] for r in need if bad(r)], [r["clip"] for r in need if r["clip"] not in ups]
    if miss_n or miss_u:
        raise SystemExit("missing notes: %s\nmissing uploads: %s" % (miss_n, miss_u))

    k = len(rows)
    warm = "" if d == 1 else "### ⓪ 暖身（5 分鐘）\n- [ ] 打開 %s，把前一天標成 🔴 的句子各唸 3 遍\n" % mention
    board = ""
    if a.board:
        board = "## 🔊 點字發音板\n點任何單字就會唸出來，點 ▶ 唸整句。要錄音比對發音，請在新分頁開啟發音板。\n<embed src=\"%s\">Day %d 點字發音板</embed>\n" % (a.board.replace("{d}", str(d)), d)
    head = board + """## 今天的流程（約 60–70 分鐘）
%s### ① 理解（3 遍）
- [ ] 第 1 遍：不開字幕看
- [ ] 第 2 遍：開中文字幕看
- [ ] 第 3 遍：開英文字幕看，對照下面「今天的句子」的筆記
- [ ] 🖨️ 筆記已列印
### ② 自己造句（至少 5 句）
- [ ] 從今天的句型挑 5 個，在該句的「我的造句」寫下自己生活會用到的句子
- [ ] 同時記到 %s，「學習日」選 Day %d
### ③ 錄音口說 ＋ AI 判斷
- [ ] 錄音，和原音比對
- [ ] 請 AI 批改造句，把結果填回造句口說紀錄
- [ ] 照「修正後句子」再說一次、再錄一次
### ④ Shadowing 5 遍
- [ ] 第 1 遍：0.75 倍速，看稿
- [ ] 第 2 遍：0.75 倍速，看稿
- [ ] 第 3 遍：1 倍速，看稿
- [ ] 第 4 遍：1 倍速，看稿
- [ ] 第 5 遍：1 倍速，不看稿
### ⑤ 標註熟悉度
- [ ] 跟不上、說不出來的句子，勾選該句下面的「🔴 不熟」
- [ ] 在造句口說紀錄裡，把今天的造句標成 🔴 不熟／🟡 普通／🟢 熟練
## 今天的句子（%d 句）
""" % (warm, mention, d, k)

    def block(i, r):
        n = notes[r["clip"]]
        b = ["### %02d｜%s" % (i, r["en"]), "中文：" + n["zh"], '<audio src="file-upload://%s"></audio>' % ups[r["clip"]], "**文法**"]
        b += ["- " + g for g in n["grammar"]]
        b.append("")  # blank line ends the list; otherwise Notion folds the next lines into the last bullet
        if n.get("usage"):
            b.append("**使用說明**：" + n["usage"])
        b.append("**例句**：" + n["example"])
        if n.get("exampleZh"):
            b.append("中文：" + n["exampleZh"])
        return "\n".join(b + ["**我的造句**", "英文：", "中文：", "- [ ] 🔴 不熟", "---"])

    blocks = [block(i, r) if r in need else "" for i, r in enumerate(rows, 1)]
    chunks = [head] + ["\n".join(blocks[i:i + PER_CHUNK]) + "\n" for i in range(0, k, PER_CHUNK)]
    chunks[-1] += "## 今日心得\n- 最卡的 3 句：\n- 今天學到的一個句型：\n"
    for i, c in enumerate(chunks):
        if a.chunk is not None and i != a.chunk:
            continue
        open(os.path.join(out, "day%d_chunk%d.md" % (d, i)), "w", encoding="utf-8").write(c)
    print("chunks: %d | sentences: %d | title: %s｜Day %d｜%d 句" % (len(chunks), k, plan["title"], d, k))


if __name__ == "__main__":
    main()
