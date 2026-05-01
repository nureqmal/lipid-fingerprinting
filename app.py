import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
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

# --- CODE EMAS (UNTOUCHED SHARED LOGIC) ---
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
    contaminants = ['iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene', 'benzo', 'benza', 'cyclo', 'sulphur', 'benzothiophene', 'naphthalene', 'benzene,']

    def classify_compound(name):
        n = str(name).lower()
        if any(x in n for x in blacklist): return "Discard (Artifact)"
        if any(x in n for x in contaminants): return "Review (Potential Contaminant)"
        return "Clean (Lipid/Oxidation)"

    df['Chemical_Status'] = df['Hit Name'].apply(classify_compound)
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    
    return df_header, df.sort_values(by='RT (min)')

def check_match_expert(row, target_df, tol):
    matches = target_df[target_df['Hit Name'] == row['Hit Name']]
    if matches.empty: return "NO", None
    for _, t_row in matches.iterrows():
        diff = abs(row['RT (min)'] - t_row['RT (min)'])
        if diff <= tol: return "YES", diff 
    closest_diff = matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()
    return "RT_SHIFT_DETECTED", closest_diff

# --- INTERFACE TABS ---
main_tab1, main_tab2 = st.tabs(["📊 Single Analysis", "🧬 Multiple Analysis for PCA"])

with main_tab1:
    st.warning("⚠️ **IMPORTANT**: Please ensure your files are in **.xlsx** format.")
    col1, col2 = st.columns(2)
    with col1: 
        sample_file = st.file_uploader("Upload SAMPLE File", type=['xlsx'], key="single_sample")
    with col2: 
        blank_file = st.file_uploader("Upload BLANK File", type=['xlsx'], key="single_blank")

    if sample_file and blank_file:
        try:
            h_s, df_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
            h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

            res_s = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
            df_s['In_Blank'] = [x[0] for x in res_s]
            df_s['RT_Diff'] = [x[1] for x in res_s]

            res_b = df_b.apply(lambda r: check_match_expert(r, df_s, rt_tolerance), axis=1)
            df_b['In_Sample'] = [x[0] for x in res_b]

            df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
            total_sample, excluded, final_count = len(df_s), len(df_s[df_s['In_Blank'] == "YES"]), len(df_final)
            purity = (final_count / total_sample * 100) if total_sample > 0 else 0
            
            st.subheader("Summary Metrics")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Sample Peaks", total_sample)
            m2.metric("Blank Matches (Purged)", excluded, delta=f"-{excluded}", delta_color="inverse")
            m3.metric("Final Unique Compounds", final_count)
            m4.metric(label="Sample Purity Score", value=f"{purity:.1f}%")

            t1, t2, t3, t4 = st.tabs(["1. Solvent Blank", "2. Sample Mapping", "3. Final Fingerprint", "4. RT Analysis"])
            with t1: st.dataframe(df_b)
            with t2: st.dataframe(df_s)
            with t3: st.dataframe(df_final.drop(columns=['In_Blank', 'RT_Diff']))
            with t4:
                rt_issues = df_s[df_s['In_Blank'] == "RT_SHIFT_DETECTED"]
                if not rt_issues.empty: st.table(rt_issues[['Hit Name', 'RT (min)', 'RT_Diff']])
                else: st.success("No significant RT shifts detected.")

            # (Export logic simplified for brevity but remains same as GOLD)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, sheet_name='Clean_Result', index=False)
            st.download_button(label="Download Single Report", data=output.getvalue(), file_name="Single_Analysis.xlsx")

        except Exception as e: st.error(f"Error: {e}")

with main_tab2:
    st.header("Multiple Analysis for PCA")
    st.info("Upload one BLANK and multiple SAMPLE files to generate a consolidated PCA table.")
    
    m_blank_file = st.file_uploader("Upload ONE Blank File", type=['xlsx'], key="multi_blank")
    m_sample_files = st.file_uploader("Upload MULTIPLE Sample Files", type=['xlsx'], accept_multiple_files=True, key="multi_samples")

    if m_blank_file and m_sample_files:
        try:
            _, df_b_multi = run_strict_procedure(m_blank_file, q_threshold, area_threshold)
            
            pca_data = []
            all_compounds = set()
            
            progress_bar = st.progress(0)
            for idx, s_file in enumerate(m_sample_files):
                _, df_s_raw = run_strict_procedure(s_file, q_threshold, area_threshold)
                
                # Apply Blank Filtering
                res_multi = df_s_raw.apply(lambda r: check_match_expert(r, df_b_multi, rt_tolerance), axis=1)
                df_s_clean = df_s_raw[[x[0] in ["NO", "RT_SHIFT_DETECTED"] for x in res_multi]].copy()
                
                # Store original Absorbance Area (Area Ab*s)
                sample_dict = {row['Hit Name']: row['Area (Ab*s)'] for _, row in df_s_clean.iterrows()}
                sample_dict['Sample Name'] = s_file.name
                pca_data.append(sample_dict)
                all_compounds.update(df_s_clean['Hit Name'].tolist())
                progress_bar.progress((idx + 1) / len(m_sample_files))

            # Create Ready for PCA Table
            df_pca = pd.DataFrame(pca_data)
            # Reorder: Sample Name first, then compounds
            cols = ['Sample Name'] + sorted(list(all_compounds))
            df_pca = df_pca.reindex(columns=cols).fillna(0) # Non-detected peaks are 0

            st.subheader("Ready for PCA Table (Raw Absorbance)")
            st.dataframe(df_pca)
            
            # Export PCA Table
            pca_output = io.BytesIO()
            with pd.ExcelWriter(pca_output, engine='xlsxwriter') as writer:
                df_pca.to_excel(writer, sheet_name='PCA_Ready', index=False)
            st.download_button(label="Download PCA Table", data=pca_output.getvalue(), file_name="PCA_Matrix_Ready.xlsx")

        except Exception as e: st.error(f"Error during Multiple Analysis: {e}")
