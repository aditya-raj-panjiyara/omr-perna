"""
Delhi IAS Academy OMR checker (wraps OMRChecker).

  bash run.sh                 -> reads every scan in ./scans
  bash run.sh /path/to/folder -> reads every scan in that folder

Accepts .jpg / .jpeg / .png images and multi-page .pdf files.
If answer_key.csv (100 lines like "q1,B") sits next to this file, sheets are also scored.
Results go to ./results/<date_time>/
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import re
import runpy
import shutil
import sys
import types
from fractions import Fraction

import cv2
import numpy as np
import pandas as pd

KIT = os.path.dirname(os.path.abspath(__file__))
OMRCHECKER = os.path.join(KIT, "OMRChecker")
SHEET = os.path.join(KIT, "sheet")
IMG_EXT = {".jpg", ".jpeg", ".png"}
QUESTIONS = [f"q{i}" for i in range(1, 101)]


def clean(img_bgr):
    """Red channel drops the pink printed shading; dividing by the background drops the grey watermark."""
    r = img_bgr[:, :, 2].astype(np.float32)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))
    bg = cv2.GaussianBlur(cv2.morphologyEx(r, cv2.MORPH_CLOSE, k), (31, 31), 0)
    return np.clip(r / np.maximum(bg, 1) * 255, 0, 255).astype(np.uint8)


def collect_scans(src, dst):
    try:
        import pymupdf as fitz  # PyMuPDF, installed with OMRChecker
    except ImportError:
        import fitz

    names = []
    files = sorted(f for f in glob.glob(os.path.join(src, "*")) if not os.path.basename(f).startswith("."))
    for f in files:
        stem, ext = os.path.splitext(os.path.basename(f))
        ext = ext.lower()
        if ext in IMG_EXT:
            img = cv2.imread(f)
            if img is None:
                print(f"  ! could not open {os.path.basename(f)}, skipped")
                continue
            pages = [(stem, img)]
        elif ext == ".pdf":
            pages = []
            with fitz.open(f) as doc:
                for i, page in enumerate(doc, 1):
                    pix = page.get_pixmap(dpi=200)
                    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                    img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR if pix.n == 4 else cv2.COLOR_RGB2BGR)
                    pages.append((f"{stem}_p{i:02d}", img))
        else:
            continue
        for name, img in pages:
            cv2.imwrite(os.path.join(dst, name + ".jpg"), clean(img), [cv2.IMWRITE_JPEG_QUALITY, 95])
            names.append(name)
    return names


def load_answer_key(path):
    key = {}
    with open(path, newline="") as fh:
        for row in csv.reader(fh):
            if not row or not row[0].strip():
                continue
            q = row[0].strip().lower()
            if not re.fullmatch(r"q\d+", q):
                continue  # header or junk line
            ans = (row[1] if len(row) > 1 else "").strip().upper()
            key[q] = ans
    missing = [q for q in QUESTIONS if key.get(q, "") not in {"A", "B", "C", "D"}]
    if missing:
        sys.exit(f"answer_key.csv: every question q1..q100 needs one of A/B/C/D. Problem with: {', '.join(missing[:15])}"
                 + (" ..." if len(missing) > 15 else ""))
    return key


def roll_digit(value):
    """One roll column: blank -> 'O', two or more bubbles filled -> 'X', otherwise the digit."""
    if value == "":
        return "O"
    return "X" if len(value) > 1 else value


def patch_roll_concatenation():
    """Build Roll column by column so blanks/double marks stay visible; unused columns at the end are dropped."""
    import src.utils.parsing as parsing

    original = parsing.get_concatenated_response

    def concatenated(omr_response, template):
        response = original(omr_response, template)
        cols = template.custom_labels.get("Roll")
        if cols:
            response["Roll"] = "".join(roll_digit(omr_response.get(k, "")) for k in cols).rstrip("O")
        return response

    parsing.get_concatenated_response = concatenated


def load_marking():
    """Marks per verdict from sheet/evaluation.json, e.g. {"correct": 2, "incorrect": -2/3, "unmarked": 0}."""
    with open(os.path.join(SHEET, "evaluation.json")) as fh:
        scheme = json.load(fh)["marking_schemes"]["DEFAULT"]
    return {k: float(Fraction(str(scheme[k]))) for k in ("correct", "incorrect", "unmarked")}


def run_omrchecker(in_dir, out_dir):
    # OMRChecker asks for the screen size at import; give it a fixed one so it never needs a display.
    import screeninfo
    screeninfo.get_monitors = lambda: [types.SimpleNamespace(width=1920, height=1080)]
    sys.path.insert(0, OMRCHECKER)
    patch_roll_concatenation()  # must run before main.py imports src.entry
    cwd, argv = os.getcwd(), sys.argv
    os.chdir(OMRCHECKER)
    sys.argv = ["main.py", "-i", in_dir, "-o", out_dir]
    try:
        runpy.run_path(os.path.join(OMRCHECKER, "main.py"), run_name="__main__")
    except SystemExit as e:
        if e.code not in (0, None):
            raise
    finally:
        os.chdir(cwd)
        sys.argv = argv


def main():
    ap = argparse.ArgumentParser(description="Read Delhi IAS Academy OMR sheets")
    ap.add_argument("scans", nargs="?", default=os.path.join(KIT, "scans"), help="folder with scans (default: ./scans)")
    ap.add_argument("--key", default=os.path.join(KIT, "answer_key.csv"), help="answer key csv (default: ./answer_key.csv)")
    ap.add_argument("--out", default=os.path.join(KIT, "results"), help="where results go (default: ./results)")
    args = ap.parse_args()

    scans = os.path.abspath(os.path.expanduser(args.scans))
    if not os.path.isdir(scans):
        sys.exit(f"Scans folder not found: {scans}")
    run_dir = os.path.join(os.path.abspath(args.out), dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    work = os.path.join(run_dir, "_work")
    os.makedirs(work)

    print(f"Reading scans from {scans}")
    names = collect_scans(scans, work)
    if not names:
        sys.exit("No .jpg/.jpeg/.png/.pdf files found in that folder.")
    print(f"  {len(names)} sheet image(s) prepared")

    for f in ("template.json", "config.json", "reference.jpg"):
        shutil.copy(os.path.join(SHEET, f), work)
    key = None
    if os.path.isfile(args.key):
        key = load_answer_key(args.key)
        with open(os.path.join(work, "answer_key.csv"), "w") as fh:
            fh.writelines(f"{q},{key[q]}\n" for q in QUESTIONS)
        shutil.copy(os.path.join(SHEET, "evaluation.json"), work)
        print("  answer_key.csv found -> scoring enabled")
    else:
        print("  no answer_key.csv -> reading answers only (no scores)")

    omr_out = os.path.join(run_dir, "_omrchecker")
    print("Running OMRChecker...")
    run_omrchecker(work, omr_out)

    res = glob.glob(os.path.join(omr_out, "Results", "*.csv"))
    if not res:
        sys.exit(f"OMRChecker produced no results. See {omr_out}/Manual/ErrorFiles.csv")
    d = pd.read_csv(res[0], dtype=str).fillna("").sort_values("file_id")
    d["Sheet"] = d["file_id"].str.replace(r"\.jpg$", "", regex=True)
    d["MultiMarked"] = d[QUESTIONS].apply(lambda r: " ".join(q for q in QUESTIONS if len(r[q]) > 1), axis=1)
    # Two or more bubbles on one question: drop the answer and treat the question as blank.
    d[QUESTIONS] = d[QUESTIONS].mask(d[QUESTIONS].apply(lambda c: c.str.len() > 1), "")
    d["Answered"] = (d[QUESTIONS] != "").sum(axis=1)
    d["Blank"] = 100 - d["Answered"]
    cols = ["Sheet", "Roll", "Answered", "Blank", "MultiMarked"]
    if key:
        marks = load_marking()
        d["Correct"] = d[QUESTIONS].apply(lambda r: sum(r[q] == key[q] for q in QUESTIONS), axis=1)
        d["Wrong"] = d["Answered"] - d["Correct"]
        score = d["Correct"] * marks["correct"] + d["Wrong"] * marks["incorrect"] + d["Blank"] * marks["unmarked"]
        d["Score"] = score.astype(float).round(2)
        cols += ["Correct", "Wrong", "Score"]
    out_csv = os.path.join(run_dir, "OMR_results.csv")
    d[cols + QUESTIONS].to_csv(out_csv, index=False)

    checked = os.path.join(run_dir, "checked_sheets")
    shutil.move(os.path.join(omr_out, "CheckedOMRs"), checked)
    errors = glob.glob(os.path.join(omr_out, "Manual", "ErrorFiles", "*"))
    shutil.rmtree(work)  # prepared page images: ~1 MB per sheet, only needed while OMRChecker runs

    print("\n" + d[cols].to_string(index=False))
    print(f"\nResults:        {out_csv}")
    print(f"Marked images:  {checked}")
    if errors:
        print(f"!! {len(errors)} sheet(s) could not be read - see {os.path.join(omr_out, 'Manual')}")
    if (d["MultiMarked"] != "").any():
        print("Note: MultiMarked = student filled 2+ bubbles; those questions were counted as blank (no marks).")


if __name__ == "__main__":
    main()
