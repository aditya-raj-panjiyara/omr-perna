# Delhi IAS Academy OMR Checker: run it on your Mac

Reads the 100-question Delhi IAS Academy OMR sheet (Roll No. + Q1–Q100, A–D) from scanner images or PDFs.
It writes a results CSV and an image of each sheet with the detected answers marked on it.
It uses the open-source OMRChecker underneath. This kit downloads it for you.

---

## 1. One-time setup (about 5 minutes)

### a) Check Python
Open **Terminal** (Spotlight → type "Terminal"), then run:

    python3 --version

You need **Python 3.10 or newer**.
If it says 3.9 or lower, or asks to install developer tools, install Python from
https://www.python.org/downloads/macos/ (the "macOS 64-bit universal2 installer"). Then open a **new** Terminal window.
(If you use Homebrew, `brew install python@3.12` works too.)

### b) Put the kit somewhere simple
Unzip `omr_kit.zip`, for example into your Documents folder, so you have `~/Documents/omr_kit/`.

### c) Run setup

    cd ~/Documents/omr_kit
    bash setup.sh

This downloads OMRChecker and installs OpenCV and the other packages into a private `.venv` folder inside the kit.
It doesn't touch your system Python.
It finishes with: `Setup OK` → `Done. Put your scans in the 'scans' folder...`

### d) Test it

    bash run.sh sample_scans

You should see two rows, with Roll **39501** (99 answered, MultiMarked `q12 q15 q41`) and **39502** (99 answered).
If you do, everything works.

---

## 2. Every time you check a batch

1. Copy the scans into `omr_kit/scans/`. Delete the previous batch first.
   - Accepted: `.jpg`, `.jpeg`, `.png` and `.pdf` (multi-page PDFs are fine; each page is one sheet)
2. Run:

       cd ~/Documents/omr_kit
       bash run.sh

   Or point it at any folder: `bash run.sh ~/Desktop/test_batch_12oct`
3. The results are in `omr_kit/results/<date_time>/`:
   - `OMR_results.csv`: one row per sheet (Sheet, Roll, Answered, Blank, MultiMarked, then Q1–Q100). Opens in Excel or Numbers.
   - `checked_sheets/`: each sheet with the detected answer letter printed on the bubble. Use these to spot-check.

21 sheets take about 15–20 seconds.

---

## 3. Scoring (optional)

1. Make a copy of `answer_key_TEMPLATE.csv` named **`answer_key.csv`** in the same folder.
2. Fill in the answer for each question:

       q1,B
       q2,D
       ...
       q100,A

3. Run `bash run.sh` again. The CSV now also has **Correct**, **Wrong** and **Score**.

Marking is +2 for correct, −2/3 for wrong and 0 for blank. A double-marked question counts as wrong.
To change the marks, edit `sheet/evaluation.json` (the `correct` / `incorrect` / `unmarked` values).
To stop scoring, delete or rename `answer_key.csv`.

---

## 4. Scanning tips (these matter)

- The template is tuned for **flatbed scanner** output: **A4, colour, 200 dpi, full page**. That's the same as the IMG_00xx.jpg files it was built from.
  Small tilts or shifts on the glass are fine, because each scan is auto-aligned.
- Phone photos or phone "scan" apps give curved, distorted pages and less reliable results. Use the scanner.
- Students must fill bubbles fully, with a blue or black pen. Ticks, crosses or dots may be missed.
- If a student fills one bubble and puts an X on another, both get read. It shows up in **MultiMarked**, so decide those by hand.

---

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| `Python 3.10 or newer not found` | Install Python from python.org (step 1a), open a new Terminal, run `bash setup.sh` again |
| `Run setup first` | Run `bash setup.sh` from inside the kit folder |
| `No .jpg/.jpeg/.png/.pdf files found` | Check the scans are directly inside the folder, not in a subfolder |
| Setup fails while downloading | Check your internet connection and run `bash setup.sh` again (it resumes) |
| Roll numbers look wrong, or many questions show as blank or multi-marked | Open the matching image in `checked_sheets/`. If the marks sit beside the bubbles, the scan differs from the expected format (see section 4) |
| Want to start completely fresh | Delete the `.venv` and `OMRChecker` folders inside the kit, then run `bash setup.sh` |

## What's inside
- `setup.sh`: one-time install
- `run.sh` / `omr.py`: cleans each scan (removes the pink shading and the watermark), runs OMRChecker and builds the results CSV
- `sheet/`: the template for this sheet (bubble positions, alignment reference image, scoring settings)
- `scans/`: put your scans here
- `sample_scans/`: two sheets for testing the setup
- `answer_key_TEMPLATE.csv`: copy to `answer_key.csv` and fill in to enable scoring
