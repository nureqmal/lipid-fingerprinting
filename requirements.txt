# Lipid EQ v3 — Blank Pool restructure

## What changed from v2 (your original `app__22_.py`)

v2 compared one sample against exactly **one uploaded blank file**.

v3 compares each sample against a **Blank Pool**: every Solvent, Method,
Carryover, and Reagent blank you've tagged to that sample's batch, combined.
Every purged peak now also records **which blank type / which blank file**
matched it, so you can answer "why was this peak removed?" instead of just
"it was removed."

This directly implements the workflow from your second Perplexity answer:
solvent-specific blanks, method blanks, and carryover blanks, all pooled per
batch rather than handled as one-off single-blank comparisons.

## Running it

```bash
pip install -r requirements.txt
streamlit run Lipid_EQ.py
```

A SQLite file `lipid_eq_data.db` is created automatically on first run in
the project root. It replaces the old `blacklist_config.json` and stores:

- **batches** — one row per solvent/extraction batch (e.g. "Hexane Batch 1")
- **blank_uploads** — every blank file you upload, tagged with a `blank_type`
  (Solvent / Method / Carryover / Reagent) and linked to a batch
- **blank_compounds** — the parsed compound rows for each blank upload
- **blacklist_keywords** — your blacklist, now shared consistently across
  every page instead of a single JSON file

## Recommended workflow

1. **Batch Settings** → create a batch per solvent system
   (e.g. "Hexane Batch 1", solvent system "n-Hexane").
2. **Blank Library** → upload your Solvent blank, Method blank, and
   Carryover blank for that batch, tagging each with its type.
3. **Pipeline** → pick the batch, choose which blank types to include in
   the pool (default: all available), upload your sample, run the analysis.
   The Excel export now includes a "Purge breakdown by blank type" section
   on the Dashboard sheet.

## Files

```
Lipid_EQ.py                    Home page / entry point (run this with streamlit)
lib/
  db.py                        SQLite layer: batches, blank pool, blacklist
  pipeline.py                  GC-MS parsing, classification, pool matching
  theme.py                     Dark/light theme tokens + global CSS
  sidebar.py                   Shared sidebar (theme toggle + blacklist manager)
  ui.py                        section_header / info_banner helpers
pages/
  1_🧪_Pipeline.py              Single-file analysis + Multi-file PCA matrix
  2_📦_Blank_Library.py         Upload & tag blanks per batch
  3_⚙️_Batch_Settings.py        Create/manage batches
requirements.txt
```

## Notes / things to double check before your next lab run

- If you have **existing single blank files** from the old workflow, re-upload
  them in **Blank Library** and tag each one with the correct `blank_type`
  (most of your old blanks were probably acting as a de facto "Solvent" blank).
- The **Excluded (Blacklist)** view on the Pipeline page now only shows
  sample-side exclusions — blank-side blacklist filtering already happens
  automatically the moment you upload a blank in the Blank Library page.
- `lipid_eq_data.db` is a single local file. Fine for one analyst on one
  machine; if multiple lab members need to share the same blank library
  concurrently, that file should eventually move to a shared location or a
  proper client-server database — flagged here for later, not needed now.
