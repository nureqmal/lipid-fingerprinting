"""
Core GC-MS data-cleaning logic for Lipid EQ.

Filtering layers:
  1. Artifact / contaminant classification (blacklist keywords + known
     contaminant fragments).
  2. Blank subtraction — now uses a 3-condition approach:
       (a) Name match (same library ID)
       (b) RT within tolerance (±rt_tol minutes)
       (c) Area ratio: sample_area / blank_area < area_ratio_threshold
     A compound is PURGED only if ALL three conditions are met.
     If name+RT match but area ratio >= threshold, the compound is
     RETAINED_HIGH_AREA — it's likely a true analyte that happens to
     appear as trace background in the blank too.

Match_Status values:
  PURGED              — all 3 conditions met → removed from fingerprint
  RETAINED_HIGH_AREA  — name+RT match, but sample area >> blank → kept
  RT_SHIFT_DETECTED   — name match, RT outside tolerance → kept
  NO                  — no name match at all → kept
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
    df['Chemical_Status'] = df['Hit Name'].apply(
        lambda n: classify_compound(n, blacklist))

    df_excluded = df[df['Chemical_Status'] == "Discard (Artifact)"].copy()
    df_excluded['Matched Keyword'] = df_excluded['Hit Name'].apply(
        lambda n: get_matched_keywords(n, blacklist))
    df_excluded = (df_excluded
                   .sort_values(by='Area (Ab*s)', ascending=False)
                   .drop_duplicates(subset=['Hit Name'], keep='first')
                   .sort_values(by='RT (min)'))

    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = (df.sort_values(by='Area (Ab*s)', ascending=False)
          .drop_duplicates(subset=['Hit Name'], keep='first'))
    return df_header, df.sort_values(by='RT (min)'), df_excluded


def check_match_against_pool(row, pool_df, rt_tol, area_ratio_threshold):
    """3-condition blank subtraction check for one sample compound.

    Returns tuple:
      (status, rt_diff, area_ratio, blank_type, blank_source)

    status options:
      'PURGED'             — name + RT + area_ratio < threshold → remove
      'RETAINED_HIGH_AREA' — name + RT match, but ratio >= threshold → keep
      'RT_SHIFT_DETECTED'  — name match only, RT outside tol → keep
      'NO'                 — no name match → keep
    """
    if pool_df.empty:
        return 'NO', None, None, None, None

    matches = pool_df[pool_df['Hit Name'] == row['Hit Name']]
    if matches.empty:
        return 'NO', None, None, None, None

    sample_area = row['Area (Ab*s)']
    best_rt_match = None
    best_rt_diff = float('inf')

    for _, blank_row in matches.iterrows():
        rt_diff = abs(row['RT (min)'] - blank_row['RT (min)'])
        if rt_diff <= rt_tol:
            # RT match — check area ratio
            blank_area = blank_row['Area (Ab*s)']
            if blank_area and blank_area > 0:
                ratio = sample_area / blank_area
            else:
                ratio = float('inf')  # blank area is 0 → treat as very high

            if ratio < area_ratio_threshold:
                return ('PURGED', rt_diff, ratio,
                        blank_row.get('Blank_Type'), blank_row.get('Blank_Source'))
            else:
                return ('RETAINED_HIGH_AREA', rt_diff, ratio,
                        blank_row.get('Blank_Type'), blank_row.get('Blank_Source'))

        if rt_diff < best_rt_diff:
            best_rt_diff = rt_diff
            best_rt_match = blank_row

    # Name match found but no RT within tolerance
    return ('RT_SHIFT_DETECTED', best_rt_diff, None,
            best_rt_match.get('Blank_Type') if best_rt_match is not None else None,
            best_rt_match.get('Blank_Source') if best_rt_match is not None else None)


def match_sample_against_pool(df_sample, pool_df, rt_tol, area_ratio_threshold):
    """Apply check_match_against_pool across an entire sample dataframe."""
    results = df_sample.apply(
        lambda r: check_match_against_pool(r, pool_df, rt_tol, area_ratio_threshold),
        axis=1
    )
    df_sample = df_sample.copy()
    df_sample['Match_Status']         = [r[0] for r in results]
    df_sample['RT_Diff']              = [r[1] for r in results]
    df_sample['Area_Ratio']           = [r[2] for r in results]
    df_sample['Matched_Blank_Type']   = [r[3] for r in results]
    df_sample['Matched_Blank_Source'] = [r[4] for r in results]
    return df_sample
