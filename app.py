import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="Lipid EQ", layout="wide")
st.title("Lipid EQ- Sorting & Cleaning")

# --- SIDEBAR CONTROL ---
st.sidebar.header("⚙️ Analytical Controls")

q_threshold = st.sidebar.slider(
    "Select NIST Quality Threshold", 50, 95, 80, 5,
    help="**NIST Match Factor:** Filters compound identity accuracy. (Default: 80)"
)

rt_tolerance = st.sidebar.slider(
    "Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01,
    help="**Retention Time Buffer:** Time error limit for comparing Sample vs Blank.(Default: 0.05)"
)

area_threshold = st.sidebar.slider(
    "Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01,
    help="**Baseline Cut-off:** Removes small peaks/noise (Default: 0.00)."
)

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1.  **Metadata Preservation**: NIST headers (Rows 1–9) retained.
2.  **Quality Gate**: Filtering peaks with NIST Quality **≥ {q_threshold}**.
3.  **Noise Reduction**: Removing baseline peaks with Area **< {area_threshold:.2f}%**.
4.  **RT-Aware Matching**: Matching compounds using Name + RT Tolerance (**±{rt_tolerance} min**).
---
""")

# --- BLACKLIST & CONTAMINANTS (shared reference) ---
BLACKLIST = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
CONTAMINANTS = ['iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene', 'benzo', 'benza', 'cyclo', 'sulphur', 'benzothiophene', 'naphthalene', 'benzene,']

def classify_compound(name):
    n = str(name).lower()
    if any(x in n for x in BLACKLIST): return "Discard (Artifact)"
    if any(x in n for x in CONTAMINANTS): return "Review (Potential Contaminant)"
    return "Clean (Lipid/Oxidation)"

def get_matched_keywords(name):
    """Return which blacklist keyword(s) triggered the exclusion — so user knows WHY compound was excluded."""
    n = str(name).lower()
    matched = [kw for kw in BLACKLIST if kw in n]
    return ', '.join(matched) if matched else ''

# --- CODE EMAS (UPDATED - returns excluded compounds too) ---
def run_strict_procedure(file, q_min, area_min):
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    df_header = df_full_raw.iloc[0:9, :].copy()
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip()

    df = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df['Quality'] = pd.to_numeric(df['Quality'], errors='coerce')

    total_area = df['Area (Ab*s)'].sum()
    df['Area (%)'] = (df['Area (Ab*s)'] / total_area) * 100

    # Apply quality + area filter first (same as original)
    df = df[(df['Quality'] >= q_min) & (df['Area (%)'] >= area_min)]

    # Classify all compounds
    df['Chemical_Status'] = df['Hit Name'].apply(classify_compound)

    # --- CAPTURE EXCLUDED (BLACKLIST) after quality filter, before dropping ---
    # df_excluded retains FULL compound names (e.g. "Octasiloxane, hexadecamethyl-")
    # plus a helper column showing which keyword triggered the exclusion
    df_excluded = df[df['Chemical_Status'] == "Discard (Artifact)"].copy()
    df_excluded['Matched Keyword'] = df_excluded['Hit Name'].apply(get_matched_keywords)
    df_excluded = df_excluded.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    df_excluded = df_excluded.sort_values(by='RT (min)')

    # Remove blacklist compounds (original logic preserved — untouched)
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')

    return df_header, df.sort_values(by='RT (min)'), df_excluded

def check_match_expert(row, target_df, tol):
    matches = target_df[target_df['Hit Name'] == row['Hit Name']]
    if matches.empty: return "NO", None
    for _, t_row in matches.iterrows():
        diff = abs(row['RT (min)'] - t_row['RT (min)'])
        if diff <= tol: return "YES", diff
    closest_diff = matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()
    return "RT_SHIFT_DETECTED", closest_diff

# --- TAB SYSTEM ---
tab1, tab2 = st.tabs(["Single File (Detail)", "Multiple Files (for PCA)"])

with tab1:
    st.warning("⚠️ **IMPORTANT**: Please ensure your files are in **.xlsx** format.")
    col1, col2 = st.columns(2)
    with col1:
        sample_file = st.file_uploader("Upload SAMPLE File (.xlsx only)", type=['xlsx'], key="s_file")
    with col2:
        blank_file = st.file_uploader("Upload BLANK File (.xlsx only)", type=['xlsx'], key="b_file")

    if sample_file and blank_file:
        try:
            h_s, df_s, df_s_excluded = run_strict_procedure(sample_file, q_threshold, area_threshold)
            h_b, df_b, df_b_excluded = run_strict_procedure(blank_file, q_threshold, area_threshold)

            res_s = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
            df_s['In_Blank'] = [x[0] for x in res_s]
            df_s['RT_Diff'] = [x[1] for x in res_s]

            res_b = df_b.apply(lambda r: check_match_expert(r, df_s, rt_tolerance), axis=1)
            df_b['In_Sample'] = [x[0] for x in res_b]

            df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
            total_sample = len(df_s)
            excluded = len(df_s[df_s['In_Blank'] == "YES"])
            final_count = len(df_final)
            purity = (final_count / total_sample * 100) if total_sample > 0 else 0

            st.subheader("Summary Metrics")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Sample Peaks", total_sample)
            m2.metric("Blank Matches (Purged)", excluded, delta=f"-{excluded}", delta_color="inverse")
            m3.metric("Final Unique Compounds", final_count)
            m4.metric(
                label="Sample Purity Score",
                value=f"{purity:.1f}%",
                help="""
            **Halal Integrity Metrics (Area-Weight)**

            This score represents the concentration-weighted purity of the lipid profile.
            It filters out solvent background (blank) and non-lipid artifacts.

            Formula:
            (Σ Area of Clean Lipid Peaks / Total Original Peak Area) × 100
            """
            )
            m5.metric("Blacklist Excluded (Sample)", len(df_s_excluded), delta=f"-{len(df_s_excluded)}", delta_color="inverse")

            t1, t2, t3, t4, t5 = st.tabs(["1. Solvent Blank", "2. Sample Mapping", "3. Final Fingerprint", "4. RT Analysis", "5. Excluded (Blacklist)"])

            with t1:
                def highlight_blank(row):
                    styles = ['' for _ in row.index]
                    if row['In_Sample'] == "YES":
                        styles = ['background-color: #FFEB9C' for _ in row.index]
                    elif row['In_Sample'] == "RT_SHIFT_DETECTED":
                        rt_idx = row.index.get_loc('RT (min)')
                        styles[rt_idx] = 'background-color: #002060; color: white'
                    return styles
                st.dataframe(df_b.style.apply(highlight_blank, axis=1))

            with t2:
                def highlight_sample(row):
                    styles = ['' for _ in row.index]
                    if row['In_Blank'] == "YES":
                        styles = ['background-color: #FFEB9C' for _ in row.index]
                    elif row['In_Blank'] == "RT_SHIFT_DETECTED":
                        rt_idx = row.index.get_loc('RT (min)')
                        styles[rt_idx] = 'background-color: #002060; color: white'
                    return styles
                st.dataframe(df_s.style.apply(highlight_sample, axis=1))

            with t3:
                st.dataframe(df_final.drop(columns=['In_Blank', 'RT_Diff']))

            with t4:
                rt_issues = df_s[df_s['In_Blank'] == "RT_SHIFT_DETECTED"]
                if not rt_issues.empty:
                    st.info(f"Found **{len(rt_issues)}** compounds with significant RT shifts (>0.2). The compounds are retained.")
                    st.table(rt_issues[['Hit Name', 'RT (min)', 'RT_Diff']])
                else:
                    st.success("No significant RT shifts detected.")

            # --- TAB 5: EXCLUDED BLACKLIST COMPOUNDS ---
            with t5:
                st.markdown("### ⛔ Excluded Compounds (Blacklist Artifacts)")
                st.info(
                    "Compounds below were **originally detected in the raw data** but excluded because their "
                    "full compound name contains a blacklisted keyword. "
                    "For example, **'Octasiloxane, hexadecamethyl-'** is excluded because its name contains **'siloxane'** — "
                    "a known GC column bleed artifact family. "
                    "The **'Matched Keyword'** column tells you exactly which keyword triggered each exclusion."
                )

                st.markdown("#### Sample — Excluded Compounds")
                if df_s_excluded.empty:
                    st.success("No blacklisted compounds found in Sample.")
                else:
                    def highlight_excluded_s(row):
                        return ['background-color: #FFD7D7' for _ in row.index]
                    st.dataframe(df_s_excluded.style.apply(highlight_excluded_s, axis=1), use_container_width=True)
                    st.caption(f"🔴 {len(df_s_excluded)} compound(s) excluded from Sample. Full compound names shown above — 'Matched Keyword' column shows why each was excluded.")

                st.markdown("---")
                st.markdown("#### Blank — Excluded Compounds")
                if df_b_excluded.empty:
                    st.success("No blacklisted compounds found in Blank.")
                else:
                    def highlight_excluded_b(row):
                        return ['background-color: #FFD7D7' for _ in row.index]
                    st.dataframe(df_b_excluded.style.apply(highlight_excluded_b, axis=1), use_container_width=True)
                    st.caption(f"🔴 {len(df_b_excluded)} compound(s) excluded from Blank. Full compound names shown above — 'Matched Keyword' column shows why each was excluded.")

            st.markdown("---")
            custom_filename = st.text_input("📁 Rename your file before download", value="eg. SF-HEX-1", key="rename_s")
            final_save_name = f"{custom_filename.strip().replace(' ', '_')}.xlsx"

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                wb = writer.book
                header_fmt = wb.add_format({'bold': True, 'font_size': 16, 'bg_color': '#2E75B6', 'font_color': 'white', 'border': 1, 'align': 'center'})
                label_fmt = wb.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
                val_fmt = wb.add_format({'border': 1, 'align': 'center'})
                yellow_fmt = wb.add_format({'bg_color': '#FFEB9C', 'border': 1})
                navy_fmt = wb.add_format({'bg_color': '#002060', 'font_color': 'white', 'border': 1})
                pink_fmt = wb.add_format({'bg_color': '#FFC0CB', 'border': 1})
                red_fmt = wb.add_format({'bg_color': '#FFD7D7', 'border': 1})
                red_hdr_fmt = wb.add_format({'bold': True, 'font_size': 13, 'bg_color': '#C00000', 'font_color': 'white', 'border': 1, 'align': 'center'})
                red_sub_fmt = wb.add_format({'bold': True, 'bg_color': '#FFD7D7', 'border': 1, 'align': 'center'})
                note_fmt = wb.add_format({'italic': True, 'font_color': '#C00000', 'text_wrap': True})

                # --- DASHBOARD SHEET ---
                ws_dash = wb.add_worksheet('Dashboard')
                ws_dash.merge_range('B2:E2', 'LIPID EQ ANALYTICAL SUMMARY', header_fmt)
                metrics_list = [
                    ('Quality Threshold', q_threshold),
                    ('RT Tolerance', rt_tolerance),
                    ('Area Threshold', area_threshold),
                    ('Final Biomarkers', final_count),
                    ('Purity Score', f"{purity:.2f}%"),
                    ('Blacklist Excluded (Sample)', len(df_s_excluded)),
                    ('Blacklist Excluded (Blank)', len(df_b_excluded)),
                ]
                for i, (l, v) in enumerate(metrics_list, start=4):
                    ws_dash.write(f'B{i}', l, label_fmt)
                    ws_dash.write(f'C{i}', v, val_fmt)

                ws_dash.write('B12', 'COLOR LEGEND / GUIDELINE:', wb.add_format({'bold': True, 'underline': True}))
                ws_dash.write('B13', 'Yellow Row', yellow_fmt); ws_dash.write('C13', 'Matched in Blank/Sample (Shared Compound)')
                ws_dash.write('B14', 'Blue RT Cell', navy_fmt); ws_dash.write('C14', 'RT Shift Detected (Retained)')
                ws_dash.write('B15', 'Pink Cell', pink_fmt); ws_dash.write('C15', 'Potential contaminant/Unique compound')
                ws_dash.write('B16', 'Red Row', red_fmt); ws_dash.write('C16', 'Excluded Blacklist Artifact (Originally in Raw Data — full name preserved)')
                ws_dash.set_column('B:B', 30)
                ws_dash.set_column('C:C', 85)

                # --- ANALYTICAL REPORT SHEET ---
                rs = 'Analytical_Report'
                h_b.to_excel(writer, sheet_name=rs, startrow=2, index=False, header=False)
                df_b.to_excel(writer, sheet_name=rs, startrow=11, index=False, header=False)
                s2 = len(df_b) + 16
                h_s.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
                df_s.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
                s3 = s2 + len(df_s) + 15
                fh = h_s.copy()
                fh.iloc[0, 0] = f"{fh.iloc[0,0]} (Clean Version ✅)"
                fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
                df_final.drop(columns=['In_Blank', 'RT_Diff']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)

                ws_rep = writer.sheets[rs]
                b_rt_idx = df_b.columns.get_loc('RT (min)')
                b_match_idx = df_b.columns.get_loc('In_Sample')
                ws_rep.conditional_format(11, 0, 11+len(df_b), len(df_b.columns)-1, {'type': 'formula', 'criteria': f'=${chr(65+b_match_idx)}12="YES"', 'format': yellow_fmt})
                ws_rep.conditional_format(11, b_rt_idx, 11+len(df_b), b_rt_idx, {'type': 'formula', 'criteria': f'=${chr(65+b_match_idx)}12="RT_SHIFT_DETECTED"', 'format': navy_fmt})
                s_rt_idx = df_s.columns.get_loc('RT (min)')
                s_match_idx = df_s.columns.get_loc('In_Blank')
                ws_rep.conditional_format(s2+10, 0, s2+10+len(df_s), len(df_s.columns)-1, {'type': 'formula', 'criteria': f'=${chr(65+s_match_idx)}{s2+11}="YES"', 'format': yellow_fmt})
                ws_rep.conditional_format(s2+10, s_rt_idx, s2+10+len(df_s), s_rt_idx, {'type': 'formula', 'criteria': f'=${chr(65+s_match_idx)}{s2+11}="RT_SHIFT_DETECTED"', 'format': navy_fmt})
                f_status_idx = df_final.columns.get_loc('Chemical_Status')
                ws_rep.conditional_format(s3+10, f_status_idx, s3+10+len(df_final), f_status_idx, {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': pink_fmt})

                # --- NEW SHEET: EXCLUDED COMPOUNDS (full compound names + matched keyword) ---
                ws_excl = wb.add_worksheet('Excluded_Compounds')

                # Figure out column span for merge
                max_cols = max(
                    len(df_s_excluded.columns) if not df_s_excluded.empty else 6,
                    len(df_b_excluded.columns) if not df_b_excluded.empty else 6
                )
                last_col_letter = chr(64 + min(max_cols, 26))

                ws_excl.merge_range(f'A1:{last_col_letter}1', '⛔ EXCLUDED BLACKLIST COMPOUNDS — Originally Present in Raw Data', red_hdr_fmt)
                ws_excl.merge_range(f'A2:{last_col_letter}2',
                    'NOTE: These compounds passed the quality filter but were removed because their full compound name '
                    'contains a blacklisted keyword (e.g. "Octasiloxane, hexadecamethyl-" excluded via keyword "siloxane"). '
                    'Full compound names and all metadata are preserved here for traceability. '
                    'See "Matched Keyword" column to understand why each compound was excluded.',
                    note_fmt)
                ws_excl.set_row(1, 50)

                # SAMPLE excluded table
                ws_excl.merge_range(f'A4:{last_col_letter}4', 'SAMPLE — Excluded Blacklist Compounds', red_sub_fmt)
                if not df_s_excluded.empty:
                    for col_idx, col_name in enumerate(df_s_excluded.columns):
                        ws_excl.write(4, col_idx, col_name, label_fmt)
                    for row_idx, (_, row) in enumerate(df_s_excluded.iterrows()):
                        for col_idx, val in enumerate(row):
                            ws_excl.write(5 + row_idx, col_idx, val, red_fmt)
                    s_excl_end = 5 + len(df_s_excluded)
                else:
                    ws_excl.write(4, 0, 'No blacklisted compounds found in Sample.', wb.add_format({'italic': True, 'font_color': '#666666'}))
                    s_excl_end = 6

                # BLANK excluded table
                blank_start = s_excl_end + 2
                ws_excl.merge_range(f'A{blank_start}:{last_col_letter}{blank_start}', 'BLANK — Excluded Blacklist Compounds', red_sub_fmt)
                if not df_b_excluded.empty:
                    for col_idx, col_name in enumerate(df_b_excluded.columns):
                        ws_excl.write(blank_start, col_idx, col_name, label_fmt)
                    for row_idx, (_, row) in enumerate(df_b_excluded.iterrows()):
                        for col_idx, val in enumerate(row):
                            ws_excl.write(blank_start + 1 + row_idx, col_idx, val, red_fmt)
                else:
                    ws_excl.write(blank_start, 0, 'No blacklisted compounds found in Blank.', wb.add_format({'italic': True, 'font_color': '#666666'}))

                ws_excl.set_column('A:A', 45)
                ws_excl.set_column('B:B', 12)
                ws_excl.set_column('C:C', 15)
                ws_excl.set_column('D:D', 12)
                ws_excl.set_column('E:E', 25)
                ws_excl.set_column('F:F', 25)
                ws_excl.set_column('G:G', 25)

            st.download_button(label="Download Report", data=output.getvalue(), file_name=final_save_name)

        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    st.header("Multiple Files for PCA")
    m_blank = st.file_uploader("Upload ONE Blank File", type=['xlsx'], key="m_b")
    m_samples = st.file_uploader("Upload MULTIPLE Sample Files", type=['xlsx'], accept_multiple_files=True, key="m_s")

    if m_blank and m_samples:
        try:
            _, df_b_multi, _ = run_strict_procedure(m_blank, q_threshold, area_threshold)
            pca_list = []
            all_compounds = set()

            for s_f in m_samples:
                _, df_s_raw, _ = run_strict_procedure(s_f, q_threshold, area_threshold)
                res = df_s_raw.apply(lambda r: check_match_expert(r, df_b_multi, rt_tolerance), axis=1)
                df_clean = df_s_raw[res.apply(lambda x: x[0] in ["NO", "RT_SHIFT_DETECTED"])].copy()

                s_dict = {row['Hit Name']: row['Area (Ab*s)'] for _, row in df_clean.iterrows()}
                s_dict['Sample Name'] = s_f.name
                pca_list.append(s_dict)
                all_compounds.update(df_clean['Hit Name'].tolist())

            df_pca = pd.DataFrame(pca_list)
            cols = ['Sample Name'] + sorted(list(all_compounds))
            df_pca = df_pca.reindex(columns=cols).fillna(0)
            st.subheader("Ready for PCA Table (Raw Absorbance)")
            st.dataframe(df_pca)

            pca_out = io.BytesIO()
            with pd.ExcelWriter(pca_out, engine='xlsxwriter') as writer:
                df_pca.to_excel(writer, sheet_name='PCA_Data', index=False)
            st.download_button("Download PCA Matrix", data=pca_out.getvalue(), file_name="PCA_Matrix_Ready.xlsx")

        except Exception as e:
            st.error(f"PCA Error: {e}")
