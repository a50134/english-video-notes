"""Split the video into sentences and find where each one is spoken.

  py -3.13 segment.py <workdir> [--model small.en]

Reads audio.mp3 and meta.json (from fetch.py). Speech recognition gives a time for every spoken
word (cached in words.json). Sentence text comes from the human-made English subtitles when there
are any, otherwise from the recognised text. Writes sentences.json:
  id, en, s, e (seconds), conf (share of words found in the audio, 1 = all), zhSub (subtitle hint),
  dup, oneWord, noise, heard, skip (true = leave out of the plan; edit by hand for name-only lines).
"""
import argparse
import difflib
import os
import re
import subprocess
import time

import common

ABBR = {"mr.", "mrs.", "ms.", "dr.", "st.", "vs.", "jr.", "sr.", "mt."}
PAD_START, PAD_END = 0.15, 0.30
NOISE = re.compile(r"^(a+h+|a+r*g+h+|o+h+|o+w+|u+h+|u+m+|u+g+h+|h+m+|m+|ha+h*|he+|whe+w|e+k|gr+)$")  # screams and grunts, not worth a note


def transcribe(work, model):
    cache = os.path.join(work, "words.json")
    if os.path.exists(cache):
        return common.load(cache)
    import numpy as np
    from faster_whisper import WhisperModel
    # Decode with ffmpeg ourselves: faster-whisper's own decoder breaks with some PyAV versions.
    pcm = subprocess.run([common.ffmpeg(), "-v", "error", "-i", os.path.join(work, "audio.mp3"), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    print("audio: %d s, recognising speech (roughly a quarter of the audio length on CPU)..." % (len(audio) / 16000), flush=True)
    t0 = time.time()
    m = WhisperModel(model, device="cpu", compute_type="int8", download_root=common.MODELS)
    segs, _ = m.transcribe(audio, language="en", word_timestamps=True, vad_filter=False, condition_on_previous_text=False, beam_size=5)
    words = [[w.word.strip(), round(w.start, 2), round(w.end, 2)] for s in segs for w in (s.words or []) if w.word.strip()]
    common.dump(words, cache)
    print("recognised %d words in %d s" % (len(words), time.time() - t0), flush=True)
    return words


def ts(t):
    p = t.strip().replace(",", ".").split(":")
    return sum(float(x) * 60 ** i for i, x in enumerate(reversed(p)))


def clean(text):
    text = re.sub(r"<[^>]+>|\{[^}]*\}", "", text)
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)|[♪♫#]+", " ", text)
    text = re.sub(r"(^|\s)(>>+|-)\s+", " ", text)
    text = re.sub(r"(^|\s)[A-Z][A-Z .'#0-9]{1,20}:\s", " ", text)  # speaker labels like "PHINEAS: "
    return re.sub(r"\s+", " ", text.replace("&nbsp;", " ").replace("&amp;", "&")).strip()


def cues(path):
    out = []
    raw = open(path, encoding="utf-8-sig", errors="replace").read().replace("\r", "")
    for block in re.split(r"\n\s*\n", raw):
        lines = block.strip().split("\n")
        k = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if k is None:
            continue
        a, b = lines[k].split("-->")[:2]
        text = clean(" ".join(lines[k + 1:]))
        if text:
            out.append((ts(a), ts(b.split()[0]), text))
    return out


def norm(tok):
    return re.sub(r"[^a-z0-9]", "", tok.lower())


def split_sentences(tokens, soft=()):
    """tokens: list of display words; soft: indices where a new subtitle line or a pause starts.
    Returns list of (first, last) index pairs."""
    soft = set(soft)
    spans, start = [], 0
    for i, t in enumerate(tokens):
        if re.search(r"[.?!…][\"'”’)]*$", t) and t.lower() not in ABBR:
            spans.append((start, i))
            start = i + 1
    if start < len(tokens):
        spans.append((start, len(tokens) - 1))
    out = []
    for a, b in spans:  # break very long sentences (song lyrics, run-ons) at a comma, subtitle line or pause near the middle
        stack = [(a, b)]
        while stack:
            x, y = stack.pop()
            commas = [i for i in range(x + 4, y - 4) if re.search(r"[,;:—]$", tokens[i]) or i + 1 in soft]
            if y - x + 1 > 28 and commas:
                mid = min(commas, key=lambda i: abs(i - (x + y) / 2))
                stack += [(mid + 1, y), (x, mid)]
            else:
                out.append((x, y))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("--model", default="small.en")
    a = ap.parse_args()
    work = a.workdir
    meta = common.load(os.path.join(work, "meta.json"))
    words = [w for w in transcribe(work, a.model) if norm(w[0])]
    use_subs = meta.get("enSubsKind") == "manual" and meta.get("enSubs")

    if use_subs:
        en_cues = cues(os.path.join(work, meta["enSubs"]))
        toks = [t for c in en_cues for t in c[2].split()]
        enders = sum(1 for t in toks if re.search(r"[.?!]$", t))
        if enders * 40 < len(toks):  # subtitles without punctuation: one cue = one sentence
            spans, i = [], 0
            for c in en_cues:
                n = len(c[2].split())
                spans.append((i, i + n - 1))
                i += n
        else:
            starts, i = [], 0
            for c in en_cues:
                starts.append(i)
                i += len(c[2].split())
            spans = split_sentences(toks, starts)
        keep = [i for i, t in enumerate(toks) if norm(t)]
        sm = difflib.SequenceMatcher(None, [norm(toks[i]) for i in keep], [norm(w[0]) for w in words], autojunk=False)
        hit = {}
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                hit[keep[blk.a + k]] = blk.b + k
    else:
        toks = [w[0] for w in words]
        spans = split_sentences(toks, [i for i in range(1, len(words)) if words[i][1] - words[i - 1][2] >= 0.35])
        hit = {i: i for i in range(len(toks))}

    rows = []
    for x, y in spans:
        idx = [i for i in range(x, y + 1) if norm(toks[i])]
        if not idx:
            continue
        m = [hit[i] for i in idx if i in hit]
        rows.append({"en": " ".join(toks[x:y + 1]), "n": len(idx), "m": m,
                     "lead": next((k for k, i in enumerate(idx) if i in hit), 0),
                     "tail": next((k for k, i in enumerate(reversed(idx)) if i in hit), 0)})

    total = words[-1][2] if words else 0
    for k, r in enumerate(rows):
        prev_last = next((rows[j]["m"][-1] for j in range(k - 1, -1, -1) if rows[j]["m"]), -1)
        next_first = next((rows[j]["m"][0] for j in range(k + 1, len(rows)) if rows[j]["m"]), len(words))
        if r["m"]:
            w0 = max(prev_last + 1, r["m"][0] - r["lead"])   # unmatched words at the edges still belong to this sentence
            w1 = min(next_first - 1, r["m"][-1] + r["tail"])
            w0, w1 = min(w0, r["m"][0]), max(w1, r["m"][-1])
            s, e = words[w0][1], words[w1][2]
            s = max(s, words[w0][2] - 0.9)  # a word after silence or music often gets a start time that is far too early
        else:
            s = words[prev_last][2] if prev_last >= 0 else 0
            e = words[next_first][1] if next_first < len(words) else total
        r["s"], r["e"] = round(max(0, s - PAD_START), 2), round(min(total + 1, max(e, s + 0.4) + PAD_END), 2)

    zh_cues = cues(os.path.join(work, meta["zhSubs"])) if meta.get("zhSubs") else []
    seen, out = set(), []
    for k, r in enumerate(rows, 1):
        key = " ".join(norm(t) for t in r["en"].split() if norm(t))
        zh = " ".join(c[2] for c in zh_cues if r["s"] <= (c[0] + c[1]) / 2 <= r["e"])
        o = {"id": k, "en": r["en"], "s": r["s"], "e": r["e"], "conf": round(len(r["m"]) / r["n"], 2),
             "dup": key in seen, "oneWord": r["n"] == 1}
        o["noise"] = all(NOISE.match(norm(t)) for t in r["en"].split() if norm(t))
        o["skip"] = o["dup"] or o["noise"]
        if use_subs and r["m"]:
            o["heard"] = " ".join(w[0] for w in words[r["m"][0]:r["m"][-1] + 1])  # recognised text: has normal capitals when the subtitles are ALL CAPS
        if zh:
            o["zhSub"] = zh
        seen.add(key)
        out.append(o)
    common.dump(out, os.path.join(work, "sentences.json"))

    low = [o for o in out if o["conf"] < 0.6]
    print("text from:", "subtitles" if use_subs else "speech recognition (proofread it)")
    print("sentences: %d, duplicates skipped: %d, one-word: %d, uncertain timing: %d" % (
        len(out), sum(o["dup"] for o in out), sum(o["oneWord"] for o in out), len(low)))
    for o in low[:40]:
        print("  check #%d %.1f-%.1f conf %.2f  %s" % (o["id"], o["s"], o["e"], o["conf"], o["en"][:70]))


if __name__ == "__main__":
    main()
