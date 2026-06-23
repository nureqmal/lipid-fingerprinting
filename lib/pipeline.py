"""
Core GC-MS data-cleaning logic for Lipid EQ.

Two filtering layers, independent of each other:
  1. Artifact / contaminant classification (blacklist keywords + known
     contaminant fragments) - same logic as the original single-file app.
  2. Blank subtraction - now matches against a *pool* of blanks (solvent +
     method + carryover + reagent, depending on what's tagged to the batch)
     instead of a single uploaded blank file. Every match also records
     which blank_type / which blank file it came from, for provenance.
"""

import pandas as pd

CONTAMINANTS = [
    'iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene',
    'benzo', 'benza', 'cyclo', 'sulphur', 'benzothiophene', 'naphthalene',
    'benzene,'
]


def classify_compound(name, blacklist):
    n = str(name).lower()
    if any(x in n for x in blacklist):
        return "Discard (Artifact)"
    if any(x in n for x in CONTAMINANTS):
        return "Review (Potential Contaminant)"
    return "Clean (Lipid/Oxidation)"


def get_matched_keywords(name, blacklist):
    n = str(name).lower()
    return ', '.join([kw for kw in blacklist if kw in n])


def run_strict_procedure(file, q_min, area_min, blacklist):
    """Parses a raw LibRes export, applies quality + noise threshold,
    classifies every compound, and splits out blacklisted artifacts.

    Returns (df_header, df_clean, df_excluded).
    """
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    df_header = df_full_raw.iloc[0:9, :].copy()
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df['Quality'] = pd.to_numeric(df['Quality'], errors='coerce')
    total_area = df['Area (Ab*s)'].sum()
    df['Area (%)'] = (df['Area (Ab*s)'] / total_area) * 100
    df = df[(df['Quality'] >= q_min) & (df['Area (%)'] >= area_min)]
    df['Chemical_Status'] = df['Hit Name'].apply(lambda n: classify_compound(n, blacklist))

    df_excluded = df[df['Chemical_Status'] == "Discard (Artifact)"].copy()
    df_excluded['Matched Keyword'] = df_excluded['Hit Name'].apply(lambda n: get_matched_keywords(n, blacklist))
    df_excluded = (df_excluded.sort_values(by='Area (Ab*s)', ascending=False)
                   .drop_duplicates(subset=['Hit Name'], keep='first')
                   .sort_values(by='RT (min)'))

    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    return df_header, df.sort_values(by='RT (min)'), df_excluded


def check_match_expert(row, target_df, tol):
    """Original 1-to-1 matcher (kept for blank-vs-blank diagnostics)."""
    matches = target_df[target_df['Hit Name'] == row['Hit Name']]
    if matches.empty:
        return "NO", None
    for _, t_row in matches.iterrows():
        if abs(row['RT (min)'] - t_row['RT (min)']) <= tol:
            return "YES", abs(row['RT (min)'] - t_row['RT (min)'])
    return "RT_SHIFT_DETECTED", matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()


def check_match_against_pool(row, pool_df, tol):
    """Matches one sample compound against the combined blank pool.

    Returns (status, rt_diff, blank_type, blank_source):
      status        -> "NO" | "YES" | "RT_SHIFT_DETECTED"
      rt_diff        -> float or None
      blank_type     -> which blank category caused the match (or the
                        closest one, if only an RT-shifted match exists)
      blank_source   -> filename of the specific blank that matched
    """
    if pool_df.empty:
        return "NO", None, None, None

    matches = pool_df[pool_df['Hit Name'] == row['Hit Name']]
    if matches.empty:
        return "NO", None, None, None

    for _, t_row in matches.iterrows():
        diff = abs(row['RT (min)'] - t_row['RT (min)'])
        if diff <= tol:
            return "YES", diff, t_row.get('Blank_Type'), t_row.get('Blank_Source')

    diffs = matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1)
    idx_min = diffs.idxmin()
    closest = matches.loc[idx_min]
    return "RT_SHIFT_DETECTED", diffs.min(), closest.get('Blank_Type'), closest.get('Blank_Source')


def match_sample_against_pool(df_sample, pool_df, tol):
    """Vectorised helper - applies check_match_against_pool across a
    whole sample dataframe and attaches the result columns.
    """
    results = df_sample.apply(lambda r: check_match_against_pool(r, pool_df, tol), axis=1)
    df_sample = df_sample.copy()
    df_sample['Match_Status'] = [r[0] for r in results]
    df_sample['RT_Diff'] = [r[1] for r in results]
    df_sample['Matched_Blank_Type'] = [r[2] for r in results]
    df_sample['Matched_Blank_Source'] = [r[3] for r in results]
    return df_sample
