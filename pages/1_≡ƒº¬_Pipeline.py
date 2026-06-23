import io
import pandas as pd
import streamlit as st

from lib import db, pipeline
from lib.theme import get_theme, apply_global_css, render_header
from lib.sidebar import render_common_sidebar
from lib.ui import section_header, info_banner

st.set_page_config(page_title="Lipid EQ — Pipeline", layout="wide", page_icon="🧪")

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

db.init_db()
T = get_theme()
apply_global_css(T)
render_header(T, subtitle="Pipeline")

with st.sidebar:
    blacklist = render_common_sidebar(T)
    st.markdown(f"<div style='font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:8px;'>⚙️ Analytical Controls</div>", unsafe_allow_html=True)
    q_threshold = st.slider("NIST Quality Threshold", 50, 95, 80, 5,
        help="Filters compound identity accuracy. (Default: 80)")
    rt_tolerance = st.slider("RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01,
        help="Time error limit when matching Sample peaks against the Blank Pool. (Default: 0.05)")
    area_threshold = st.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01,
        help="Removes small peaks/noise. (Default: 0.00)")

    st.markdown("---")
    st.markdown(f"""
    <div style="background:{T['bg3']}; border:1px solid {T['border']}; border-radius:10px; padding:12px;">
        <div style="font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:8px;">📋 SOP Summary</div>
        {"".join([f'''<div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;">
            <div style="width:18px; height:18px; border-radius:50%; background:linear-gradient(135deg,{T['accent']},{T['accent2']}); display:flex; align-items:center; justify-content:center; font-size:9px; font-weight:700; color:#fff; flex-shrink:0;">{i}</div>
            <div style="font-size:11px; color:{T['text']}; line-height:1.4;">{s}</div>
        </div>''' for i, s in enumerate([
            "Metadata preserved (rows 1–9)",
            f"Quality gate ≥ {q_threshold}",
            f"Noise cut &lt; {area_threshold:.2f}%",
            f"RT matching ±{rt_tolerance} min vs Blank Pool",
            f"Blacklist filter ({len(blacklist)} keywords)"
        ], 1)])}
    </div>
    """, unsafe_allow_html=True)

batches = db.list_batches()

tab1, tab2 = st.tabs(["📊  Single File Analysis", "🔬  Multi-File PCA Matrix"])

# ══════════════════════════════════════════════════════════════════════════
with tab1:
    if batches.empty:
        info_banner(T, "⚠️ No batches configured. Go to <b>Batch Settings</b> to create one, then add blanks in <b>Blank Library</b>.", T['warn'])
        st.stop()

    info_banner(T, "⚠️ Pick the batch your sample belongs to, then upload the sample. Blank subtraction uses the full Blank Pool for that batch.", T['warn'])

    batch_name_to_id = {row['name']: int(row['id']) for _, row in batches.iterrows()}
    col_batch, col_types = st.columns([1, 2])
    with col_batch:
        sel_batch_name = st.selectbox("Batch", options=list(batch_name_to_id.keys()), key="t1_batch")
        sel_batch_id = batch_name_to_id[sel_batch_name]
    with col_types:
        summary = db.pool_summary(sel_batch_id)
        available_types = summary['Blank Type'].tolist() if not summary.empty else []
        sel_types = st.multiselect("Blank types to include in pool", options=db.BLANK_TYPES,
            default=available_types, key="t1_types")

    if summary.empty:
        info_banner(T, f"⚠️ No blanks uploaded yet for batch <b>{sel_batch_name}</b>. Go to <b>Blank Library</b> first — otherwise nothing will be subtracted.", T['danger'])
    else:
        st.dataframe(summary, width='stretch', hide_index=True)

    sample_file = st.file_uploader("Upload SAMPLE (.xlsx)", type=['xlsx'], key="s_file")

    if sample_file:
        try:
            h_s, df_s, df_s_excluded = pipeline.run_strict_procedure(sample_file, q_threshold, area_threshold, blacklist)
            pool_df = db.get_blank_pool(sel_batch_id, sel_types if sel_types else None)
            df_s = pipeline.match_sample_against_pool(df_s, pool_df, rt_tolerance)

            df_final = df_s[df_s['Match_Status'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
            total_sample = len(df_s)
            excluded_blank = len(df_s[df_s['Match_Status'] == "YES"])
            final_count = len(df_final)
            purity = (final_count / total_sample * 100) if total_sample > 0 else 0

            st.markdown(f"""
            <div style="margin:16px 0 10px; font-size:13px; font-weight:700; color:{T['text']};">
                Pipeline Results
                <span style="font-size:10px; font-weight:500; color:{T['muted']}; margin-left:8px;">{sample_file.name} · batch: {sel_batch_name}</span>
            </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Sample Peaks", total_sample)
            m2.metric("Blank Pool Matches Purged", excluded_blank, delta=f"-{excluded_blank}", delta_color="inverse")
            m3.metric("Final Unique Compounds", final_count)
            m4.metric("Purity Score", f"{purity:.1f}%", help="(Σ Area of Clean Lipid Peaks / Total Original Peak Area) × 100")
            m5.metric("Blacklist Excluded", len(df_s_excluded), delta=f"-{len(df_s_excluded)}", delta_color="inverse")

            # ── Purge breakdown by blank type (provenance) ────────────────
            purged = df_s[df_s['Match_Status'] == "YES"]
            if not purged.empty:
                breakdown = purged.groupby('Matched_Blank_Type').size().reset_index(name='Peaks Purged')
                section_header(T, "Purge breakdown by blank type", "Which blank category each purged peak matched against")
                st.dataframe(breakdown, width='stretch', hide_index=True)

            st.markdown("<div style='margin:6px 0'></div>", unsafe_allow_html=True)

            t1, t2, t3, t4, t5 = st.tabs([
                "1. Blank Pool", "2. Sample Mapping",
                "3. Final Fingerprint", "4. RT Analysis", "5. Excluded (Blacklist)"
            ])

            with t1:
                section_header(T, "Blank Pool Composition", f"Combined from {', '.join(sel_types) if sel_types else 'no'} blank type(s) tagged to {sel_batch_name}")
                if pool_df.empty:
                    st.info("Pool is empty — no blanks matched the selected types for this batch.")
                else:
                    st.dataframe(pool_df, width='stretch')

            with t2:
                section_header(T, "Sample Compound Mapping", "Yellow = matched in blank pool (purged) · Blue RT = shift detected but retained")
                def hl_sample(row):
                    if row['Match_Status'] == "YES":
                        return ['background-color: #FFEB9C; color: #5a4a00' for _ in row.index]
                    s = ['' for _ in row.index]
                    if row['Match_Status'] == "RT_SHIFT_DETECTED":
                        s[row.index.get_loc('RT (min)')] = 'background-color: #002060; color: white'
                    return s
                display_cols = ['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)', 'Quality', 'Chemical_Status',
                                 'Match_Status', 'RT_Diff', 'Matched_Blank_Type', 'Matched_Blank_Source']
                st.dataframe(df_s[display_cols].style.apply(hl_sample, axis=1), width='stretch')

            with t3:
                section_header(T, "Final Lipid Fingerprint", "Clean compounds after blank-pool subtraction — ready for reporting")
                def hl_final(row):
                    if row.get('Chemical_Status') == "Review (Potential Contaminant)":
                        return ['background-color: #FFC0CB; color: #5a0020' for _ in row.index]
                    return ['' for _ in row.index]
                final_cols = ['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)', 'Quality', 'Chemical_Status']
                st.dataframe(df_final[final_cols].style.apply(hl_final, axis=1), width='stretch')

            with t4:
                section_header(T, "RT Shift Analysis", "Compounds with retention time shifts against the blank pool")
                rt_issues = df_s[df_s['Match_Status'] == "RT_SHIFT_DETECTED"]
                if not rt_issues.empty:
                    info_banner(T, f"Found <b>{len(rt_issues)}</b> compound(s) with RT shift. These are <b>retained</b> in the final fingerprint.", T['warn'])
                    st.table(rt_issues[['Hit Name', 'RT (min)', 'RT_Diff', 'Matched_Blank_Type', 'Matched_Blank_Source']])
                else:
                    st.success("✅ No significant RT shifts detected.")

            with t5:
                section_header(T, "Excluded Blacklist Compounds (Sample)", "Originally in raw sample — removed because name contains a blacklisted keyword")
                st.markdown(f"""
                <div style="background:{T['bg3']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 16px; margin-bottom:14px;">
                    <div style="font-size:11px; font-weight:600; color:{T['text']}; margin-bottom:6px;">Active blacklist keywords</div>
                    <div>{"".join([f'<span style="background:{T["danger"]}18; color:{T["danger"]}; border:1px solid {T["danger"]}35; border-radius:5px; padding:2px 9px; font-size:11px; font-weight:500; margin:2px; display:inline-block;">{kw}</span>' for kw in blacklist])}</div>
                </div>
                """, unsafe_allow_html=True)
                if df_s_excluded.empty:
                    st.success("No blacklisted compounds in this sample.")
                else:
                    st.dataframe(df_s_excluded.style.apply(lambda r: ['background-color:#FFD7D7;color:#5a0000' for _ in r.index], axis=1), width='stretch')
                    st.caption(f"🔴 {len(df_s_excluded)} compound(s) — 'Matched Keyword' column shows why each was excluded.")
                st.caption("ℹ️ Blank-side blacklist exclusions are already filtered when each blank is uploaded in the Blank Library page.")

            # ── EXPORT ──────────────────────────────────────────────────
            st.markdown(f"<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:{T['bg2']}; border:1px solid {T['border']}; border-radius:12px; padding:16px 20px; margin-top:8px;">
                <div style="font-size:13px; font-weight:600; color:{T['text']};">Export Report</div>
                <div style="font-size:11px; color:{T['muted']}; margin-top:2px;">Download .xlsx report with Dashboard, Analytical Report & Excluded Compounds sheets</div>
            </div>
            """, unsafe_allow_html=True)

            dl_col1, dl_col2 = st.columns([3, 1])
            with dl_col1:
                custom_filename = st.text_input("Filename", value="SF-HEX-1", key="rename_s",
                    label_visibility="collapsed", placeholder="e.g. SF-HEX-1")
            final_save_name = f"{custom_filename.strip().replace(' ', '_')}.xlsx"

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                wb = writer.book
                header_fmt = wb.add_format({'bold': True, 'font_size': 14, 'bg_color': '#2563eb', 'font_color': 'white', 'border': 1, 'align': 'center', 'font_name': 'Calibri'})
                label_fmt = wb.add_format({'bold': True, 'bg_color': '#EEF1FB', 'border': 1, 'font_name': 'Calibri'})
                val_fmt = wb.add_format({'border': 1, 'align': 'center', 'font_name': 'Calibri'})
                yellow_fmt = wb.add_format({'bg_color': '#FFEB9C', 'border': 1})
                navy_fmt = wb.add_format({'bg_color': '#002060', 'font_color': 'white', 'border': 1})
                pink_fmt = wb.add_format({'bg_color': '#FFC0CB', 'border': 1})
                red_fmt = wb.add_format({'bg_color': '#FFD7D7', 'border': 1})
                red_hdr_fmt = wb.add_format({'bold': True, 'font_size': 12, 'bg_color': '#dc2626', 'font_color': 'white', 'border': 1, 'align': 'center', 'font_name': 'Calibri'})
                note_fmt = wb.add_format({'italic': True, 'font_color': '#dc2626', 'text_wrap': True, 'font_name': 'Calibri'})

                # Dashboard
                ws_dash = wb.add_worksheet('Dashboard')
                ws_dash.merge_range('B2:F2', 'LIPID EQ — ANALYTICAL SUMMARY REPORT', header_fmt)
                metrics_list = [
                    ('Batch', sel_batch_name),
                    ('Blank Types Included', ', '.join(sel_types) if sel_types else 'None'),
                    ('Quality Threshold', q_threshold),
                    ('RT Tolerance (min)', rt_tolerance),
                    ('Area Threshold (%)', area_threshold),
                    ('Total Sample Peaks', total_sample),
                    ('Blank Pool Matches Purged', excluded_blank),
                    ('Final Unique Compounds', final_count),
                    ('Purity Score', f"{purity:.2f}%"),
                    ('Active Blacklist Keywords', len(blacklist)),
                    ('Blacklist Excluded (Sample)', len(df_s_excluded)),
                ]
                for i, (l, v) in enumerate(metrics_list, start=4):
                    ws_dash.write(f'B{i}', l, label_fmt)
                    ws_dash.write(f'C{i}', v, val_fmt)
                row_ptr = 4 + len(metrics_list) + 1
                ws_dash.write(f'B{row_ptr}', 'Purge Breakdown by Blank Type', label_fmt)
                ws_dash.merge_range(f'C{row_ptr}:D{row_ptr}', '', val_fmt)
                row_ptr += 1
                if not purged.empty:
                    for _, brow in breakdown.iterrows():
                        ws_dash.write(f'B{row_ptr}', f"  {brow['Matched_Blank_Type']}", label_fmt)
                        ws_dash.write(f'C{row_ptr}', int(brow['Peaks Purged']), val_fmt)
                        row_ptr += 1
                else:
                    ws_dash.write(f'B{row_ptr}', '  None purged', label_fmt)
                    row_ptr += 1
                row_ptr += 1
                ws_dash.write(f'B{row_ptr}', 'Blacklist Keywords Used', label_fmt)
                ws_dash.write(f'C{row_ptr}', ', '.join(blacklist), wb.add_format({'border': 1, 'text_wrap': True, 'font_name': 'Calibri'}))
                ws_dash.set_row(row_ptr - 1, 28)
                legend_row = row_ptr + 2
                ws_dash.write(f'B{legend_row}', 'COLOR LEGEND', wb.add_format({'bold': True, 'underline': True, 'font_name': 'Calibri'}))
                ws_dash.write(f'B{legend_row+1}', 'Yellow Row', yellow_fmt); ws_dash.write(f'C{legend_row+1}', 'Matched in Blank Pool (Purged)')
                ws_dash.write(f'B{legend_row+2}', 'Blue RT Cell', navy_fmt); ws_dash.write(f'C{legend_row+2}', 'RT Shift Detected (Retained)')
                ws_dash.write(f'B{legend_row+3}', 'Pink Cell', pink_fmt); ws_dash.write(f'C{legend_row+3}', 'Potential Contaminant')
                ws_dash.write(f'B{legend_row+4}', 'Red Row', red_fmt); ws_dash.write(f'C{legend_row+4}', 'Excluded Blacklist Artifact (Full Name Preserved)')
                ws_dash.set_column('B:B', 34); ws_dash.set_column('C:C', 80)

                # Analytical report
                rs = 'Analytical_Report'
                ws_rep = wb.add_worksheet(rs)
                ws_rep.merge_range('A1:H1', f'BLANK POOL — {sel_batch_name}', header_fmt)
                if not pool_df.empty:
                    for ci, cn in enumerate(pool_df.columns):
                        ws_rep.write(2, ci, cn, label_fmt)
                    for ri, (_, prow) in enumerate(pool_df.iterrows()):
                        for ci, val in enumerate(prow):
                            ws_rep.write(3 + ri, ci, val, val_fmt)
                    pool_end = 3 + len(pool_df) + 2
                else:
                    ws_rep.write(2, 0, 'Pool is empty.', note_fmt)
                    pool_end = 5

                sample_cols = ['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)', 'Quality', 'Chemical_Status', 'Match_Status', 'RT_Diff', 'Matched_Blank_Type', 'Matched_Blank_Source']
                ws_rep.merge_range(f'A{pool_end+1}:H{pool_end+1}', 'SAMPLE — Full Mapping', header_fmt)
                for ci, cn in enumerate(sample_cols):
                    ws_rep.write(pool_end + 2, ci, cn, label_fmt)
                for ri, (_, srow) in enumerate(df_s[sample_cols].iterrows()):
                    for ci, val in enumerate(srow):
                        ws_rep.write(pool_end + 3 + ri, ci, val, val_fmt)
                sample_start_data = pool_end + 3
                sample_end = sample_start_data + len(df_s)
                match_col_idx = sample_cols.index('Match_Status')
                rt_col_idx = sample_cols.index('RT (min)')
                ws_rep.conditional_format(sample_start_data, 0, sample_end - 1, len(sample_cols) - 1,
                    {'type': 'formula', 'criteria': f'=${chr(65+match_col_idx)}{sample_start_data+1}="YES"', 'format': yellow_fmt})
                ws_rep.conditional_format(sample_start_data, rt_col_idx, sample_end - 1, rt_col_idx,
                    {'type': 'formula', 'criteria': f'=${chr(65+match_col_idx)}{sample_start_data+1}="RT_SHIFT_DETECTED"', 'format': navy_fmt})

                final_cols2 = ['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)', 'Quality', 'Chemical_Status']
                final_start = sample_end + 2
                ws_rep.merge_range(f'A{final_start}:F{final_start}', 'FINAL FINGERPRINT (Clean Version ✅)', header_fmt)
                for ci, cn in enumerate(final_cols2):
                    ws_rep.write(final_start, ci, cn, label_fmt)
                for ri, (_, frow) in enumerate(df_final[final_cols2].iterrows()):
                    for ci, val in enumerate(frow):
                        ws_rep.write(final_start + 1 + ri, ci, val, val_fmt)
                final_data_start = final_start + 1
                final_data_end = final_data_start + len(df_final)
                status_col_idx = final_cols2.index('Chemical_Status')
                ws_rep.conditional_format(final_data_start, status_col_idx, final_data_end - 1, status_col_idx,
                    {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': pink_fmt})
                ws_rep.set_column('A:A', 32); ws_rep.set_column('B:H', 16)

                # Excluded compounds
                ws_excl = wb.add_worksheet('Excluded_Compounds')
                cols_excl = list(df_s_excluded.columns) if not df_s_excluded.empty else ['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)', 'Quality', 'Matched Keyword']
                lc = chr(64 + min(len(cols_excl), 26))
                ws_excl.merge_range(f'A1:{lc}1', '⛔ EXCLUDED BLACKLIST COMPOUNDS (SAMPLE) — Originally Present in Raw Data', red_hdr_fmt)
                ws_excl.merge_range(f'A2:{lc}2', f'NOTE: Removed because compound name contains a blacklisted keyword. Active keywords: {", ".join(blacklist)}.', note_fmt)
                ws_excl.set_row(1, 42)
                if not df_s_excluded.empty:
                    for ci, cn in enumerate(df_s_excluded.columns):
                        ws_excl.write(3, ci, cn, label_fmt)
                    for ri, (_, erow) in enumerate(df_s_excluded.iterrows()):
                        for ci, val in enumerate(erow):
                            ws_excl.write(4 + ri, ci, val, red_fmt)
                else:
                    ws_excl.write(3, 0, 'No blacklisted compounds found in Sample.', note_fmt)
                ws_excl.set_column('A:A', 48); ws_excl.set_column('B:G', 18)

            with dl_col2:
                st.download_button("⬇️ Download Report", data=output.getvalue(), file_name=final_save_name, width='stretch')

        except Exception as e:
            st.error(f"Pipeline error: {e}")

# ══════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(f"""
    <div style="font-size:22px; font-weight:700; color:{T['text']}; margin-bottom:4px; letter-spacing:-0.02em;">Multi-File PCA Matrix</div>
    <div style="font-size:13px; color:{T['muted']}; margin-bottom:18px;">Pick a batch and upload multiple sample files to generate a compound × sample matrix, blank-subtracted against that batch's pool.</div>
    """, unsafe_allow_html=True)

    if batches.empty:
        info_banner(T, "⚠️ No batches configured. Go to <b>Batch Settings</b> first.", T['warn'])
        st.stop()

    info_banner(T, "⚠️ All files must be in <b>.xlsx</b> format. The same analytical controls from the sidebar apply.", T['warn'])

    batch_name_to_id2 = {row['name']: int(row['id']) for _, row in batches.iterrows()}
    sel_batch_name2 = st.selectbox("Batch", options=list(batch_name_to_id2.keys()), key="t2_batch")
    sel_batch_id2 = batch_name_to_id2[sel_batch_name2]
    summary2 = db.pool_summary(sel_batch_id2)
    available_types2 = summary2['Blank Type'].tolist() if not summary2.empty else []
    sel_types2 = st.multiselect("Blank types to include in pool", options=db.BLANK_TYPES,
        default=available_types2, key="t2_types")

    m_samples = st.file_uploader("Sample files (multiple)", type=['xlsx'], accept_multiple_files=True, key="m_s")

    if m_samples:
        try:
            pool_df2 = db.get_blank_pool(sel_batch_id2, sel_types2 if sel_types2 else None)
            pca_list, all_compounds = [], set()
            progress = st.progress(0, text="Processing files...")
            for i, s_f in enumerate(m_samples):
                _, df_s_raw, _ = pipeline.run_strict_procedure(s_f, q_threshold, area_threshold, blacklist)
                df_s_raw = pipeline.match_sample_against_pool(df_s_raw, pool_df2, rt_tolerance)
                df_clean = df_s_raw[df_s_raw['Match_Status'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
                s_dict = {row['Hit Name']: row['Area (Ab*s)'] for _, row in df_clean.iterrows()}
                s_dict['Sample Name'] = s_f.name
                pca_list.append(s_dict)
                all_compounds.update(df_clean['Hit Name'].tolist())
                progress.progress((i + 1) / len(m_samples), text=f"Processing {s_f.name}...")
            progress.empty()

            df_pca = pd.DataFrame(pca_list)
            df_pca = df_pca.reindex(columns=['Sample Name'] + sorted(list(all_compounds))).fillna(0)

            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:16px; margin:14px 0 10px;">
                <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 18px; text-align:center;">
                    <div style="font-size:22px; font-weight:700; color:{T['accent']};">{len(m_samples)}</div>
                    <div style="font-size:10px; color:{T['muted']}; text-transform:uppercase; letter-spacing:0.06em;">Samples</div>
                </div>
                <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 18px; text-align:center;">
                    <div style="font-size:22px; font-weight:700; color:{T['teal']};">{len(all_compounds)}</div>
                    <div style="font-size:10px; color:{T['muted']}; text-transform:uppercase; letter-spacing:0.06em;">Unique Compounds</div>
                </div>
                <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 18px; text-align:center;">
                    <div style="font-size:22px; font-weight:700; color:{T['accent2']};">{len(m_samples) * len(all_compounds)}</div>
                    <div style="font-size:10px; color:{T['muted']}; text-transform:uppercase; letter-spacing:0.06em;">Matrix Cells</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            section_header(T, "PCA Matrix — Raw Absorbance", "Rows = samples · Columns = compounds · Missing values filled with 0")
            st.dataframe(df_pca, width='stretch')

            pca_out = io.BytesIO()
            with pd.ExcelWriter(pca_out, engine='xlsxwriter') as writer:
                df_pca.to_excel(writer, sheet_name='PCA_Data', index=False)
            st.download_button("⬇️ Download PCA Matrix", data=pca_out.getvalue(), file_name="PCA_Matrix_Ready.xlsx")

        except Exception as e:
            st.error(f"PCA error: {e}")
