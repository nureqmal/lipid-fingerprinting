import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

# --- SIDEBAR CONTROL ---
st.sidebar.header("⚙️ Analytical Controls")

q_threshold = st.sidebar.slider(
    "Select NIST Quality Threshold", 50, 95, 80, 5,
    help="**NIST Match Factor:** Filters compound identity accuracy."
)

rt_tolerance = st.sidebar.slider(
    "Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01,
    help="**Retention Time Buffer:** Time error limit for comparing Sample vs Blank."
)

area_threshold = st.sidebar.slider(
    "Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01,
    help="**Baseline Cut-off:** Removes small peaks (noise)."
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

# --- CODE EMAS (UNTOUCHED LOGIC) ---
def run_strict_procedure(file, q_min, area_min):
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    df_header = df_full_raw.iloc[0:9, :].copy()
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip() 

    df = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df['Quality'] = pd.to_numeric(df['Quality'], errors='coerce')
    
    total_area = df['Area (Ab*s)'].sum()
    df['Area (%)'] = (df['Area (Ab*s)'] / total_area) * 100
    df = df[(df['Quality'] >= q_min) & (df['Area (%)'] >= area_min)]

    blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
    contaminants = ['iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene', 'benzothiophene', 'naphthalene', 'benzene,']

    def classify_compound(name):
        n = str(name).lower()
        if any(x in n for x in blacklist): return "Discard (Artifact)"
        if any(x in n for x in contaminants): return "Review (Potential Contaminant)"
        return "Clean (Lipid/Oxidation)"

    df['Chemical_Status'] = df['Hit Name'].apply(classify_compound)
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    
    return df_header, df.sort_values(by='RT (min)')

# --- FILE UPLOAD SECTION ---
st.warning("⚠️ **IMPORTANT**: Please ensure your files are in **.xlsx** format.")

col1, col2 = st.columns(2)
with col1: 
    sample_file = st.file_uploader("Upload SAMPLE File (.xlsx only)", type=['xlsx'])
with col2: 
    blank_file = st.file_uploader("Upload BLANK File (.xlsx only)", type=['xlsx'])

if sample_file and blank_file:
    try:
        h_s, df_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
        h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

        # --- EXPERT RT SHIFT LOGIC ---
        def check_match_expert(row, target_df, tol):
            matches = target_df[target_df['Hit Name'] == row['Hit Name']]
            if matches.empty: return "NO", None
            for _, t_row in matches.iterrows():
                diff = abs(row['RT (min)'] - t_row['RT (min)'])
                if diff <= tol: return "YES", diff 
            closest_diff = matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()
            return "RT_SHIFT_DETECTED", closest_diff

        res_s = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
        df_s['In_Blank'] = [x[0] for x in res_s]
        df_s['RT_Diff'] = [x[1] for x in res_s]

        res_b = df_b.apply(lambda r: check_match_expert(r, df_s, rt_tolerance), axis=1)
        df_b['In_Sample'] = [x[0] for x in res_b]

        df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
        total_sample, excluded, final_count = len(df_s), len(df_s[df_s['In_Blank'] == "YES"]), len(df_final)
        purity = (final_count / total_sample * 100) if total_sample > 0 else 0
        
        st.subheader("📊 Analysis Summary Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Sample Peaks", total_sample)
        m2.metric("Blank Matches (Purged)", excluded, delta=f"-{excluded}", delta_color="inverse")
        m3.metric("Final Unique Compounds", final_count)
        m4.metric(label="Sample Purity Score", value=f"{purity:.1f}%")

        # --- DATA ANALYSIS TABS (DASHBOARD UI STYLING RETURNED) ---
        t1, t2, t3, t4 = st.tabs(["1. Solvent Blank", "2. Sample Mapping", "3. Final Fingerprint", "4. 🧠 Expert RT Analysis"])
        
        with t1: 
            def highlight_blank(row):
                styles = ['' for _ in row.index]
                if row['In_Sample'] == "YES": styles = ['background-color: #FFEB9C' for _ in row.index]
                elif row['In_Sample'] == "RT_SHIFT_DETECTED":
                    rt_idx = row.index.get_loc('RT (min)')
                    styles[rt_idx] = 'background-color: #002060; color: white'
                return styles
            st.dataframe(df_b.style.apply(highlight_blank, axis=1))
        
        with t2: 
            def highlight_sample(row):
                styles = ['' for _ in row.index]
                if row['In_Blank'] == "YES": styles = ['background-color: #FFEB9C' for _ in row.index]
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
                st.info(f"Found **{len(rt_issues)}** compounds with significant RT shifts.")
                st.table(rt_issues[['Hit Name', 'RT (min)', 'RT_Diff']])
            else: st.success("No significant RT shifts detected.")

        st.markdown("---")
        
        # --- INDIVIDUAL EXPORT LOGIC (ALL FORMATS RESTORED) ---
        custom_filename = st.text_input("📁 Enter Filename for Individual Export", value="LipidExpert_Report")
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

            ws_dash = wb.add_worksheet('Dashboard')
            ws_dash.merge_range('B2:E2', 'LIPIDEXPERT ANALYTICAL SUMMARY', header_fmt)
            metrics_list = [('Quality Threshold', q_threshold), ('RT Tolerance', rt_tolerance), ('Area Threshold', area_threshold), ('Final Biomarkers', final_count), ('Purity Score', f"{purity:.2f}%")]
            for i, (l, v) in enumerate(metrics_list, start=4):
                ws_dash.write(f'B{i}', l, label_fmt); ws_dash.write(f'C{i}', v, val_fmt)
            
            ws_dash.write('B10', 'COLOR LEGEND / GUIDELINE:', wb.add_format({'bold': True, 'underline': True}))
            ws_dash.write('B11', 'Yellow Row', yellow_fmt); ws_dash.write('C11', 'Matched in Blank/Sample (Shared Compound)')
            ws_dash.write('B12', 'Navy Blue RT Cell', navy_fmt); ws_dash.write('C12', 'RT Shift Detected (Retained)')
            ws_dash.write('B13', 'Pink Cell', pink_fmt); ws_dash.write('C13', 'Potential Contaminant')
            ws_dash.set_column('B:B', 30); ws_dash.set_column('C:C', 85)

            rs = 'Analytical_Report'
            h_b.to_excel(writer, sheet_name=rs, startrow=2, index=False, header=False)
            df_b.to_excel(writer, sheet_name=rs, startrow=11, index=False, header=False)
            
            s2 = len(df_b) + 16
            h_s.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
            df_s.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
            
            s3 = s2 + len(df_s) + 15
            fh = h_s.copy(); fh.iloc[0,0] = f"{fh.iloc[0,0]} (CORRECTED UNIQUE)"
            fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
            df_final.drop(columns=['In_Blank', 'RT_Diff']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)

            ws_rep = writer.sheets[rs]
            b_rt_idx, b_match_idx, b_status_idx = df_b.columns.get_loc('RT (min)'), df_b.columns.get_loc('In_Sample'), df_b.columns.get_loc('Chemical_Status')
            ws_rep.conditional_format(11, 0, 11+len(df_b), len(df_b.columns)-1, {'type': 'formula', 'criteria': f'=${chr(65 + b_match_idx)}12="YES"', 'format': yellow_fmt})
            ws_rep.conditional_format(11, b_rt_idx, 11+len(df_b), b_rt_idx, {'type': 'formula', 'criteria': f'=${chr(65 + b_match_idx)}12="RT_SHIFT_DETECTED"', 'format': navy_fmt})

            s_rt_idx, s_match_idx, s_status_idx = df_s.columns.get_loc('RT (min)'), df_s.columns.get_loc('In_Blank'), df_s.columns.get_loc('Chemical_Status')
            ws_rep.conditional_format(s2+10, 0, s2+10+len(df_s), len(df_s.columns)-1, {'type': 'formula', 'criteria': f'=${chr(65 + s_match_idx)}{s2+11}="YES"', 'format': yellow_fmt})
            ws_rep.conditional_format(s2+10, s_rt_idx, s2+10+len(df_s), s_rt_idx, {'type': 'formula', 'criteria': f'=${chr(65 + s_match_idx)}{s2+11}="RT_SHIFT_DETECTED"', 'format': navy_fmt})
            
            # Pink Format for Contaminants in Final Report
            f_status_idx = df_final.columns.get_loc('Chemical_Status')
            ws_rep.conditional_format(s3+10, f_status_idx, s3+10+len(df_final), f_status_idx, {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': pink_fmt})

        st.download_button(label=f"📥 Download Report", data=output.getvalue(), file_name=final_save_name)
    except Exception as e: st.error(f"Error: {e}")
