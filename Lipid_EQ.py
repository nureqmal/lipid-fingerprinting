import io
import pandas as pd
import streamlit as st

from lib import db, pipeline
from lib.theme import get_theme, apply_global_css, render_header
from lib.sidebar import render_common_sidebar
from lib.ui import section_header, info_banner


def _safe_cell(val):
    if val is None:
        return ''
    try:
        if pd.isna(val):
            return ''
    except (TypeError, ValueError):
        pass
    return val


if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

db.init_db()
T = get_theme()
apply_global_css(T)
render_header(T, subtitle="Pipeline")

with st.sidebar:
    blacklist = render_common_sidebar(T)

    st.markdown(f"<div style='font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:8px;'>⚙️ Analytical Controls</div>", unsafe_allow_html=True)

    q_threshold = st.slider("NIST Quality Threshold", 0, 100, 80, 1,
        help="Filters compound identity accuracy. (Default: 80)")
    rt_tolerance = st.slider("RT Tolerance (min)", 0.01, 0.20, 0.10, 0.01,
        help="Max RT difference for a name-matched blank peak to qualify. (Default: 0.10)")
    area_threshold = st.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01,
        help="Removes small noise peaks before matching. (Default: 0.00)")
    area_ratio_threshold = st.slider("Area Ratio Threshold (sample/blank)", 1.0, 20.0, 5.0, 0.5,
        help="A compound is only PURGED if sample area / blank area < this value. "
             "If ratio ≥ threshold, compound is kept as RETAINED_HIGH_AREA "
             "(true analyte, not background). (Default: 5×)")

    st.markdown("---")
    st.markdown(f"""
    <div style="background:{T['bg3']}; border:1px solid {T['border']}; border-radius:10px; padding:12px;">
        <div style="font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:8px;">📋 Filtering Logic</div>
        <div style="font-size:11px; color:{T['text']}; line-height:1.6;">
            A compound is <b>PURGED</b> only when all 3 conditions are met:<br>
            1️⃣ Name matches blank pool<br>
            2️⃣ RT within ±{rt_tolerance} min<br>
            3️⃣ Area ratio &lt; {area_ratio_threshold:.1f}×<br><br>
            If ratio ≥ {area_ratio_threshold:.1f}× → <b>RETAINED_HIGH_AREA</b><br>
            (true analyte, not background)
        </div>
    </div>
    """, unsafe_allow_html=True)

batches = db.list_batches()

tab1, tab2 = st.tabs(["📊  Single File Analysis", "🔬  Multi-File PCA Matrix"])

# ══════════════════════════════════════════════════════════════════════════
with tab1:
    if batches.empty:
        info_banner(T, "⚠️ No batches configured. Go to <b>Batch Settings</b> to create one, then add blanks in <b>Blank Library</b>.", T['warn'])
        st.stop()

    info_banner(T, "Pick the batch your sample belongs to. Blank subtraction uses all blanks pooled for that batch, with 3-condition filtering (name + RT + area ratio).", T['accent'])

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
        info_banner(T, f"⚠️ No blanks uploaded yet for batch <b>{sel_batch_name}</b>. All compounds will be retained (nothing to subtract against).", T['danger'])
    else:
        st.dataframe(summary, width='stretch', hide_index=True)

    sample_file = st.file_uploader("Upload SAMPLE (.xlsx)", type=['xlsx'], key="s_file")

    if sample_file:
        try:
            h_s, df_s, df_s_excluded = pipeline.run_strict_procedure(
                sample_file, q_threshold, area_threshold, blacklist)
            pool_df = db.get_blank_pool(sel_batch_id, sel_types if sel_types else None)
            df_s = pipeline.match_sample_against_pool(
                df_s, pool_df, rt_tolerance, area_ratio_threshold)

            # Final fingerprint = everything except PURGED
            df_final = df_s[df_s['Match_Status'] != 'PURGED'].copy()

            total_sample      = len(df_s)
            n_purged          = len(df_s[df_s['Match_Status'] == 'PURGED'])
            n_retained_high   = len(df_s[df_s['Match_Status'] == 'RETAINED_HIGH_AREA'])
            final_count       = len(df_final)
            purity            = (final_count / total_sample * 100) if total_sample > 0 else 0

            st.markdown(f"""
            <div style="margin:16px 0 10px; font-size:13px; font-weight:700; color:{T['text']};">
                Pipeline Results
                <span style="font-size:10px; font-weight:500; color:{T['muted']}; margin-left:8px;">{sample_file.name} · batch: {sel_batch_name}</span>
            </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Total Sample Peaks", total_sample)
            m2.metric("Purged (Background)", n_purged,
                      delta=f"-{n_purged}", delta_color="inverse")
            m3.metric("Retained (High Area)", n_retained_high,
                      help=f"Matched blank in name+RT but area ratio ≥ {area_ratio_threshold:.1f}× — kept as true analyte")
            m4.metric("Final Fingerprint", final_count)
            m5.metric("Purity Score", f"{purity:.1f}%")
            m6.metric("Blacklist Excluded", len(df_s_excluded),
                      delta=f"-{len(df_s_excluded)}", delta_color="inverse")

            # Purge breakdown by blank type
            purged_df = df_s[df_s['Match_Status'] == 'PURGED']
            if not purged_df.empty:
                breakdown = (purged_df.groupby('Matched_Blank_Type')
                             .size().reset_index(name='Peaks Purged'))
                section_header(T, "Purge breakdown by blank type")
                st.dataframe(breakdown, width='stretch', hide_index=True)

            st.markdown("<div style='margin:6px 0'></div>", unsafe_allow_html=True)

            t1, t2, t3, t4, t5 = st.tabs([
                "1. Blank Pool", "2. Sample Mapping",
                "3. Final Fingerprint", "4. RT & Area Analysis", "5. Excluded (Blacklist)"
            ])

            with t1:
                section_header(T, "Blank Pool Composition",
                    f"Combined from {', '.join(sel_types) if sel_types else 'no'} blank type(s) — {sel_batch_name}")
                if pool_df.empty:
                    st.info("Pool is empty for the selected types.")
                else:
                    st.dataframe(pool_df, width='stretch')

            with t2:
                section_header(T, "Sample Compound Mapping",
                    "Yellow = PURGED · Green = RETAINED_HIGH_AREA · Blue RT cell = RT_SHIFT_DETECTED · Pink = Potential Contaminant")

                def hl_sample(row):
                    base = ['' for _ in row.index]
                    status = row.get('Match_Status', '')
                    if status == 'PURGED':
                        return ['background-color:#FFEB9C; color:#5a4a00' for _ in row.index]
                    if status == 'RETAINED_HIGH_AREA':
                        return ['background-color:#C6EFCE; color:#276221' for _ in row.index]
                    if status == 'RT_SHIFT_DETECTED':
                        try:
                            rt_idx = row.index.get_loc('RT (min)')
                            base[rt_idx] = 'background-color:#002060; color:white'
                        except KeyError:
                            pass
                    if row.get('Chemical_Status') == 'Review (Potential Contaminant)':
                        return ['background-color:#FFC0CB; color:#5a0020' for _ in row.index]
                    return base

                display_cols = ['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)',
                                'Quality', 'Chemical_Status', 'Match_Status',
                                'RT_Diff', 'Area_Ratio', 'Matched_Blank_Type', 'Matched_Blank_Source']
                st.dataframe(df_s[display_cols].style.apply(hl_sample, axis=1), width='stretch')

            with t3:
                section_header(T, "Final Lipid Fingerprint",
                    "All compounds except PURGED ones — includes RETAINED_HIGH_AREA, RT_SHIFT_DETECTED, and NO-match")

                def hl_final(row):
                    if row.get('Match_Status') == 'RETAINED_HIGH_AREA':
                        return ['background-color:#C6EFCE; color:#276221' for _ in row.index]
                    if row.get('Chemical_Status') == 'Review (Potential Contaminant)':
                        return ['background-color:#FFC0CB; color:#5a0020' for _ in row.index]
                    return ['' for _ in row.index]

                final_cols = ['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)',
                              'Quality', 'Chemical_Status', 'Match_Status', 'Area_Ratio']
                st.dataframe(df_final[final_cols].style.apply(hl_final, axis=1), width='stretch')

            with t4:
                section_header(T, "RT Shift & Area Ratio Analysis",
                    "Compounds that matched in name but were retained due to RT shift or high area ratio")

                rt_issues  = df_s[df_s['Match_Status'] == 'RT_SHIFT_DETECTED']
                high_area  = df_s[df_s['Match_Status'] == 'RETAINED_HIGH_AREA']

                if not high_area.empty:
                    info_banner(T,
                        f"<b>{len(high_area)}</b> compound(s) matched blank by name+RT but had area ratio "
                        f"≥ {area_ratio_threshold:.1f}× — retained as true analytes.",
                        T['success'])
                    st.table(high_area[['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area_Ratio',
                                        'Matched_Blank_Type', 'Matched_Blank_Source']])
                else:
                    st.success("✅ No high-area-ratio retained compounds.")

                if not rt_issues.empty:
                    info_banner(T,
                        f"<b>{len(rt_issues)}</b> compound(s) with RT shift detected — retained.",
                        T['warn'])
                    st.table(rt_issues[['Hit Name', 'RT (min)', 'RT_Diff',
                                        'Matched_Blank_Type', 'Matched_Blank_Source']])
                else:
                    st.success("✅ No RT shifts detected.")

            with t5:
                section_header(T, "Excluded Blacklist Compounds (Sample)")
                st.markdown(f"""
                <div style="background:{T['bg3']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 16px; margin-bottom:14px;">
                    <div style="font-size:11px; font-weight:600; color:{T['text']}; margin-bottom:6px;">Active blacklist keywords</div>
                    <div>{"".join([f'<span style="background:{T["danger"]}18; color:{T["danger"]}; border:1px solid {T["danger"]}35; border-radius:5px; padding:2px 9px; font-size:11px; font-weight:500; margin:2px; display:inline-block;">{kw}</span>' for kw in blacklist])}</div>
                </div>
                """, unsafe_allow_html=True)
                if df_s_excluded.empty:
                    st.success("No blacklisted compounds in this sample.")
                else:
                    red_style = lambda df: pd.DataFrame(
                        'background-color:#FFD7D7; color:#5a0000',
                        index=df.index, columns=df.columns)
                    st.dataframe(df_s_excluded.style.apply(red_style, axis=None), width='stretch')

            # ── EXPORT ────────────────────────────────────────────────────
            st.markdown(f"<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:{T['bg2']}; border:1px solid {T['border']}; border-radius:12px; padding:16px 20px; margin-top:8px;">
                <div style="font-size:13px; font-weight:600; color:{T['text']};">Export Report</div>
                <div style="font-size:11px; color:{T['muted']}; margin-top:2px;">Dashboard · Analytical Report · Excluded Compounds</div>
            </div>
            """, unsafe_allow_html=True)

            dl_col1, dl_col2 = st.columns([3, 1])
            with dl_col1:
                custom_filename = st.text_input("Filename", value="SF-HEX-1",
                    label_visibility="collapsed", placeholder="e.g. SF-HEX-1", key="rename_s")
            final_save_name = f"{custom_filename.strip().replace(' ', '_')}.xlsx"

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                wb = writer.book

                # ── formats ──────────────────────────────────────────────
                hdr_fmt   = wb.add_format({'bold':True,'font_size':13,'bg_color':'#2563eb','font_color':'white','border':1,'align':'center','font_name':'Calibri'})
                lbl_fmt   = wb.add_format({'bold':True,'bg_color':'#EEF1FB','border':1,'font_name':'Calibri'})
                val_fmt   = wb.add_format({'border':1,'align':'center','font_name':'Calibri'})
                yellow_fmt= wb.add_format({'bg_color':'#FFEB9C','border':1})
                green_fmt = wb.add_format({'bg_color':'#C6EFCE','font_color':'#276221','border':1})
                blue_fmt  = wb.add_format({'bg_color':'#002060','font_color':'white','border':1})
                pink_fmt  = wb.add_format({'bg_color':'#FFC0CB','border':1})
                red_fmt   = wb.add_format({'bg_color':'#FFD7D7','border':1})
                red_hdr   = wb.add_format({'bold':True,'font_size':12,'bg_color':'#dc2626','font_color':'white','border':1,'align':'center','font_name':'Calibri'})
                note_fmt  = wb.add_format({'italic':True,'font_color':'#dc2626','text_wrap':True,'font_name':'Calibri'})
                wrap_fmt  = wb.add_format({'border':1,'text_wrap':True,'font_name':'Calibri'})

                # ── DASHBOARD ────────────────────────────────────────────
                ws_dash = wb.add_worksheet('Dashboard')
                ws_dash.merge_range('B2:G2', 'LIPID EQ — ANALYTICAL SUMMARY REPORT', hdr_fmt)

                metrics_list = [
                    ('Batch', sel_batch_name),
                    ('Blank Types Included', ', '.join(sel_types) if sel_types else 'None'),
                    ('Quality Threshold', q_threshold),
                    ('RT Tolerance (min)', rt_tolerance),
                    ('Area % Noise Filter', area_threshold),
                    ('Area Ratio Threshold (sample/blank)', area_ratio_threshold),
                    ('Total Sample Peaks', total_sample),
                    ('Purged (Background)', n_purged),
                    ('Retained (High Area Ratio)', n_retained_high),
                    ('Final Fingerprint Compounds', final_count),
                    ('Purity Score (%)', f"{purity:.2f}%"),
                    ('Blacklist Keywords Active', len(blacklist)),
                    ('Blacklist Excluded (Sample)', len(df_s_excluded)),
                ]
                for i, (lbl, val) in enumerate(metrics_list, start=4):
                    ws_dash.write(f'B{i}', lbl, lbl_fmt)
                    ws_dash.write(f'C{i}', _safe_cell(val), val_fmt)

                row_ptr = 4 + len(metrics_list) + 1
                ws_dash.write(f'B{row_ptr}', 'Purge Breakdown by Blank Type', lbl_fmt)
                ws_dash.merge_range(f'C{row_ptr}:D{row_ptr}', '', val_fmt)
                row_ptr += 1
                if not purged_df.empty:
                    for _, brow in breakdown.iterrows():
                        ws_dash.write(f'B{row_ptr}', f"  {_safe_cell(brow['Matched_Blank_Type'])}", lbl_fmt)
                        ws_dash.write(f'C{row_ptr}', int(brow['Peaks Purged']), val_fmt)
                        row_ptr += 1
                else:
                    ws_dash.write(f'B{row_ptr}', '  None purged', lbl_fmt)
                    row_ptr += 1

                row_ptr += 1
                ws_dash.write(f'B{row_ptr}', 'Blacklist Keywords', lbl_fmt)
                ws_dash.write(f'C{row_ptr}', ', '.join(blacklist), wrap_fmt)
                ws_dash.set_row(row_ptr - 1, 28)

                # Legend
                legend_row = row_ptr + 2
                ws_dash.write(f'B{legend_row}', 'COLOR LEGEND', wb.add_format({'bold':True,'underline':True,'font_name':'Calibri'}))
                ws_dash.write(f'B{legend_row+1}', 'Yellow Row',       yellow_fmt); ws_dash.write(f'C{legend_row+1}', 'PURGED — name+RT match, area ratio < threshold')
                ws_dash.write(f'B{legend_row+2}', 'Green Row',        green_fmt);  ws_dash.write(f'C{legend_row+2}', 'RETAINED_HIGH_AREA — matched but sample >> blank (true analyte)')
                ws_dash.write(f'B{legend_row+3}', 'Blue RT Cell',     blue_fmt);   ws_dash.write(f'C{legend_row+3}', 'RT_SHIFT_DETECTED — name match, RT outside tolerance (retained)')
                ws_dash.write(f'B{legend_row+4}', 'Pink Row',         pink_fmt);   ws_dash.write(f'C{legend_row+4}', 'Review (Potential Contaminant)')
                ws_dash.write(f'B{legend_row+5}', 'Red Row',          red_fmt);    ws_dash.write(f'C{legend_row+5}', 'Excluded Blacklist Artifact')
                ws_dash.set_column('B:B', 38); ws_dash.set_column('C:C', 80)

                # ── ANALYTICAL REPORT ────────────────────────────────────
                ws_rep = wb.add_worksheet('Analytical_Report')

                # Pool
                ws_rep.merge_range('A1:H1', f'BLANK POOL — {sel_batch_name}', hdr_fmt)
                if not pool_df.empty:
                    for ci, cn in enumerate(pool_df.columns):
                        ws_rep.write(2, ci, cn, lbl_fmt)
                    for ri, (_, prow) in enumerate(pool_df.iterrows()):
                        for ci, val in enumerate(prow):
                            ws_rep.write(3 + ri, ci, _safe_cell(val), val_fmt)
                    pool_end = 3 + len(pool_df) + 2
                else:
                    ws_rep.write(2, 0, 'Pool is empty.', note_fmt)
                    pool_end = 5

                # Sample mapping
                sample_cols = ['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)',
                               'Quality', 'Chemical_Status', 'Match_Status',
                               'RT_Diff', 'Area_Ratio', 'Matched_Blank_Type', 'Matched_Blank_Source']
                ws_rep.merge_range(f'A{pool_end+1}:H{pool_end+1}', 'SAMPLE — Full Mapping', hdr_fmt)
                for ci, cn in enumerate(sample_cols):
                    ws_rep.write(pool_end + 2, ci, cn, lbl_fmt)
                for ri, (_, srow) in enumerate(df_s[sample_cols].iterrows()):
                    for ci, val in enumerate(srow):
                        ws_rep.write(pool_end + 3 + ri, ci, _safe_cell(val), val_fmt)
                sdata_start = pool_end + 3
                sdata_end   = sdata_start + len(df_s)
                match_col   = sample_cols.index('Match_Status')
                rt_col      = sample_cols.index('RT (min)')
                mc = chr(65 + match_col)
                ws_rep.conditional_format(sdata_start, 0, sdata_end-1, len(sample_cols)-1,
                    {'type':'formula','criteria':f'=${mc}{sdata_start+1}="PURGED"','format':yellow_fmt})
                ws_rep.conditional_format(sdata_start, 0, sdata_end-1, len(sample_cols)-1,
                    {'type':'formula','criteria':f'=${mc}{sdata_start+1}="RETAINED_HIGH_AREA"','format':green_fmt})
                ws_rep.conditional_format(sdata_start, rt_col, sdata_end-1, rt_col,
                    {'type':'formula','criteria':f'=${mc}{sdata_start+1}="RT_SHIFT_DETECTED"','format':blue_fmt})

                # Final fingerprint
                final_cols2 = ['Hit Name','RT (min)','Area (Ab*s)','Area (%)','Quality',
                               'Chemical_Status','Match_Status','Area_Ratio']
                final_start = sdata_end + 2
                ws_rep.merge_range(f'A{final_start}:H{final_start}', 'FINAL FINGERPRINT ✅', hdr_fmt)
                for ci, cn in enumerate(final_cols2):
                    ws_rep.write(final_start, ci, cn, lbl_fmt)
                for ri, (_, frow) in enumerate(df_final[final_cols2].iterrows()):
                    for ci, val in enumerate(frow):
                        ws_rep.write(final_start + 1 + ri, ci, _safe_cell(val), val_fmt)
                fdata_start = final_start + 1
                fdata_end   = fdata_start + len(df_final)
                fmc = chr(65 + final_cols2.index('Match_Status'))
                ws_rep.conditional_format(fdata_start, 0, fdata_end-1, len(final_cols2)-1,
                    {'type':'formula','criteria':f'=${fmc}{fdata_start+1}="RETAINED_HIGH_AREA"','format':green_fmt})
                sc_idx = final_cols2.index('Chemical_Status')
                ws_rep.conditional_format(fdata_start, sc_idx, fdata_end-1, sc_idx,
                    {'type':'cell','criteria':'equal to',
                     'value':'"Review (Potential Contaminant)"','format':pink_fmt})
                ws_rep.set_column('A:A', 32); ws_rep.set_column('B:K', 16)

                # ── EXCLUDED ─────────────────────────────────────────────
                ws_excl = wb.add_worksheet('Excluded_Compounds')
                cols_excl = list(df_s_excluded.columns) if not df_s_excluded.empty else ['Hit Name']
                lc = chr(64 + min(len(cols_excl), 26))
                ws_excl.merge_range(f'A1:{lc}1',
                    '⛔ EXCLUDED BLACKLIST COMPOUNDS (SAMPLE)', red_hdr)
                ws_excl.merge_range(f'A2:{lc}2',
                    f'Removed because compound name contains a blacklisted keyword. '
                    f'Keywords: {", ".join(blacklist)}.', note_fmt)
                ws_excl.set_row(1, 42)
                if not df_s_excluded.empty:
                    for ci, cn in enumerate(df_s_excluded.columns):
                        ws_excl.write(3, ci, cn, lbl_fmt)
                    for ri, (_, erow) in enumerate(df_s_excluded.iterrows()):
                        for ci, val in enumerate(erow):
                            ws_excl.write(4 + ri, ci, _safe_cell(val), red_fmt)
                else:
                    ws_excl.write(3, 0, 'No blacklisted compounds found.', note_fmt)
                ws_excl.set_column('A:A', 48); ws_excl.set_column('B:G', 18)

            with dl_col2:
                st.download_button("⬇️ Download Report", data=output.getvalue(),
                    file_name=final_save_name, width='stretch')

        except Exception as e:
            st.error(f"Pipeline error: {e}")
            import traceback
            st.code(traceback.format_exc())

# ══════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(f"""
    <div style="font-size:20px; font-weight:700; color:{T['text']}; margin-bottom:4px;">Multi-File PCA Matrix</div>
    <div style="font-size:13px; color:{T['muted']}; margin-bottom:18px;">Upload multiple sample files to generate a compound × sample matrix, blank-subtracted using the same 3-condition logic.</div>
    """, unsafe_allow_html=True)

    if batches.empty:
        info_banner(T, "⚠️ No batches configured. Go to <b>Batch Settings</b> first.", T['warn'])
        st.stop()

    info_banner(T, "Same analytical controls from the sidebar apply to all files.", T['warn'])

    batch_name_to_id2 = {row['name']: int(row['id']) for _, row in batches.iterrows()}
    sel_batch_name2 = st.selectbox("Batch", options=list(batch_name_to_id2.keys()), key="t2_batch")
    sel_batch_id2   = batch_name_to_id2[sel_batch_name2]
    summary2 = db.pool_summary(sel_batch_id2)
    available_types2 = summary2['Blank Type'].tolist() if not summary2.empty else []
    sel_types2 = st.multiselect("Blank types to include in pool", options=db.BLANK_TYPES,
        default=available_types2, key="t2_types")

    m_samples = st.file_uploader("Sample files (multiple)", type=['xlsx'],
        accept_multiple_files=True, key="m_s")

    if m_samples:
        try:
            pool_df2   = db.get_blank_pool(sel_batch_id2, sel_types2 if sel_types2 else None)
            pca_list   = []
            all_cpds   = set()
            progress   = st.progress(0, text="Processing files...")
            for i, s_f in enumerate(m_samples):
                _, df_raw, _ = pipeline.run_strict_procedure(s_f, q_threshold, area_threshold, blacklist)
                df_raw = pipeline.match_sample_against_pool(df_raw, pool_df2, rt_tolerance, area_ratio_threshold)
                df_clean = df_raw[df_raw['Match_Status'] != 'PURGED'].copy()
                s_dict = {row['Hit Name']: row['Area (Ab*s)'] for _, row in df_clean.iterrows()}
                s_dict['Sample Name'] = s_f.name
                pca_list.append(s_dict)
                all_cpds.update(df_clean['Hit Name'].tolist())
                progress.progress((i + 1) / len(m_samples), text=f"Processing {s_f.name}...")
            progress.empty()

            df_pca = pd.DataFrame(pca_list)
            df_pca = df_pca.reindex(columns=['Sample Name'] + sorted(list(all_cpds))).fillna(0)

            st.markdown(f"""
            <div style="display:flex; gap:16px; margin:14px 0 10px;">
                <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 18px; text-align:center;">
                    <div style="font-size:22px; font-weight:700; color:{T['accent']};">{len(m_samples)}</div>
                    <div style="font-size:10px; color:{T['muted']}; text-transform:uppercase;">Samples</div>
                </div>
                <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 18px; text-align:center;">
                    <div style="font-size:22px; font-weight:700; color:{T['teal']};">{len(all_cpds)}</div>
                    <div style="font-size:10px; color:{T['muted']}; text-transform:uppercase;">Unique Compounds</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            section_header(T, "PCA Matrix — Raw Absorbance", "Rows = samples · Columns = compounds · 0 = absent")
            st.dataframe(df_pca, width='stretch')

            pca_out = io.BytesIO()
            with pd.ExcelWriter(pca_out, engine='xlsxwriter') as writer:
                df_pca.to_excel(writer, sheet_name='PCA_Data', index=False)
            st.download_button("⬇️ Download PCA Matrix", data=pca_out.getvalue(),
                file_name="PCA_Matrix_Ready.xlsx")

        except Exception as e:
            st.error(f"PCA error: {e}")
