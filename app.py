import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

# --- SESSION STATE (Untuk Master Table) ---
if 'master_list' not in st.session_state:
    st.session_state.master_list = []

# --- SIDEBAR CONTROL ---
st.sidebar.header("⚙️ Analytical Controls")
q_threshold = st.sidebar.slider("Select NIST Quality Threshold", 50, 95, 80, 5)
rt_tolerance = st.sidebar.slider("Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01)
area_threshold = st.sidebar.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01)

if st.sidebar.button("🗑️ Reset Master Table"):
    st.session_state.master_list = []
    st.sidebar.success("Master Table Cleared!")

# Pilihan Mode
analysis_mode = st.sidebar.radio("📁 Select Analysis Mode", ["Single Sample Analysis", "Batch PCA Mode (Multiple Files)"])

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1. **Quality Gate**: NIST Quality **≥ {q_threshold}**.
2. **Noise Reduction**: Area **< {area_threshold:.2f}%** removed.
3. **RT-Aware Matching**: Name + RT Tolerance (**±{rt_tolerance} min**).
---
""")

# --- CODE EMAS (UNTOUCHED) ---
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
st.warning("⚠️ **IMPORTANT**: Ensure files are in **.xlsx** format.")

col1, col2 = st.columns(2)
with col1: 
    if analysis_mode == "Batch PCA Mode (Multiple Files)":
        sample_files = st.file_uploader("Upload MULTIPLE Sample Files", type=['xlsx'], accept_multiple_files=True)
    else:
        sample_file = st.file_uploader("Upload SINGLE Sample File", type=['xlsx'], accept_multiple_files=False)
with col2: 
    blank_file = st.file_uploader("Upload Solvent BLANK File", type=['xlsx'])

if blank_file and ((analysis_mode == "Single Sample Analysis" and sample_file) or (analysis_mode == "Batch PCA Mode (Multiple Files)" and sample_files)):
    try:
        # Run Blank
        h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

        # EXPERT RT SHIFT LOGIC (UNTOUCHED)
        def check_match_expert(row, target_df, tol):
            matches = target_df[target_df['Hit Name'] == row['Hit Name']]
            if matches.empty: return "NO", None
            for _, t_row in matches.iterrows():
                diff = abs(row['RT (min)'] - t_row['RT (min)'])
                if diff <= tol: return "YES", diff 
            closest_diff = matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()
            return "RT_SHIFT_DETECTED", closest_diff

        # --- MODE 1: SINGLE SAMPLE ---
        if analysis_mode == "Single Sample Analysis":
            h_s, df_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
            res = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
            df_s['In_Blank'] = [x[0] for x in res]
            df_s['RT_Diff'] = [x[1] for x in res]
            df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()

            # Metrics
            total_sample, excluded, final_count = len(df_s), len(df_s[df_s['In_Blank'] == "YES"]), len(df_final)
            purity = (final_count / total_sample * 100) if total_sample > 0 else 0
            
            st.subheader("📊 Single Sample Detailed Analysis")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Sample Peaks", total_sample)
            m2.metric("Blank Matches (Purged)", excluded, delta=f"-{excluded}", delta_color="inverse")
            m3.metric("Final Unique Compounds", final_count)
            m4.metric("Sample Purity Score", f"{purity:.1f}%")

            t1, t2, t3, t4, t5 = st.tabs(["1. Solvent Blank", "2. Sample Mapping", "3. Final Fingerprint", "4. 🧠 Expert RT Analysis", "🏆 5. Master PCA Table"])
            
            with t1: st.dataframe(df_b)
            with t2: st.dataframe(df_s)
            with t3: st.dataframe(df_final.drop(columns=['In_Blank', 'RT_Diff']))
            with t4:
                rt_issues = df_s[df_s['In_Blank'] == "RT_SHIFT_DETECTED"]
                if not rt_issues.empty:
                    st.info(f"RT Shifts detected in {len(rt_issues)} compounds.")
                    st.table(rt_issues[['Hit Name', 'RT (min)', 'RT_Diff']])
                else: st.success("No significant RT shifts.")

            with t5:
                s_id = st.text_input("🏷️ Unique Sample ID", value="OO-HARA-HEX-1")
                if st.button("➕ Add to Master"):
                    entry = df_final[['Hit Name', 'Area (%)']].copy()
                    entry['Sample_ID'] = s_id
                    st.session_state.master_list.append(entry)
                    st.success("Added!")

            # Individual Export
            custom_filename = st.text_input("📁 Filename for Export", value="LipidExpert_Report")
            final_save_name = f"{custom_filename.strip().replace(' ', '_')}.xlsx"
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                wb = writer.book
                header_fmt = wb.add_format({'bold': True, 'bg_color': '#2E75B6', 'font_color': 'white'})
                ws_dash = wb.add_worksheet('Dashboard')
                ws_dash.write('B2', 'LIPIDEXPERT SUMMARY', header_fmt)
                # Simpan data
                h_s.to_excel(writer, sheet_name='Analytical_Report', startrow=2, index=False, header=False)
                df_s.to_excel(writer, sheet_name='Analytical_Report', startrow=11, index=False)
                df_final.to_excel(writer, sheet_name='Final_Unique', index=False)
            st.download_button(label="📥 Download Individual Report", data=output.getvalue(), file_name=final_save_name)

        # --- MODE 2: BATCH PCA ---
        else:
            st.subheader(f"🚀 Batch Processing Mode ({len(sample_files)} files)")
            if st.button("⚡ Start Auto-Batch Processing"):
                temp_master = []
                for i, s_file in enumerate(sample_files):
                    h_s_b, df_s_b = run_strict_procedure(s_file, q_threshold, area_threshold)
                    res_b = df_s_b.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
                    df_s_b['In_Blank'] = [x[0] for x in res_b]
                    df_f_b = df_s_b[df_s_b['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
                    
                    # Sedut nama dari metadata row 1 column 1 (Atau guna filename)
                    s_name = str(h_s_b.iloc[0, 1]).strip() if not h_s_b.empty else s_file.name
                    entry = df_f_b[['Hit Name', 'Area (%)']].copy()
                    entry['Sample_ID'] = s_name
                    temp_master.append(entry)
                
                st.session_state.master_list.extend(temp_master)
                st.success("Batch complete!")

            if st.session_state.master_list:
                combined = pd.concat(st.session_state.master_list)
                master_pivot = combined.pivot(index='Sample_ID', columns='Hit Name', values='Area (%)').fillna(0)
                st.write("### 🏆 Master PCA Table Preview")
                st.dataframe(master_pivot)
                
                m_out = io.BytesIO()
                with pd.ExcelWriter(m_out, engine='xlsxwriter') as writer:
                    master_pivot.to_excel(writer, sheet_name='PCA_Ready')
                st.download_button("📥 Download Master Table", m_out.getvalue(), "Master_PCA_Dataset.xlsx")

    except Exception as e: st.error(f"Error: {e}")
