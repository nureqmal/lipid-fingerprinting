import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("Lipid EQ: Advanced Fingerprinting Suite")

# --- SIDEBAR CONTROL ---
st.sidebar.header("⚙️ Analytical Controls")
q_threshold = st.sidebar.slider("Select NIST Quality Threshold", 50, 95, 80, 5)
rt_tolerance = st.sidebar.slider("Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01)
area_threshold = st.sidebar.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01)

# --- GLOBAL FUNCTIONS ---
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

def check_match_expert(row, target_df, tol):
    matches = target_df[target_df['Hit Name'] == row['Hit Name']]
    if matches.empty:
        return "NO", None
    for _, t_row in matches.iterrows():
        diff = abs(row['RT (min)'] - t_row['RT (min)'])
        if diff <= tol:
            return "YES", diff 
    closest_diff = matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()
    return "RT_SHIFT_DETECTED", closest_diff

# --- FEATURE TABS ---
main_tab1, main_tab2 = st.tabs(["🎯 Single Analysis", "📊 Multiple Analysis (PCA Ready)"])

with main_tab1:
    st.markdown(f"""
    ### Standard Operating Procedure (SOP):
    1. **Metadata Preservation**: NIST headers (Rows 1–9) retained.
    2. **Quality Gate**: Filtering peaks with NIST Quality **≥ {q_threshold}**.
    3. **Noise Reduction**: Removing baseline peaks with Area **< {area_threshold:.2f}%**.
    4. **RT-Aware Matching**: Matching compounds using Name + RT Tolerance (**±{rt_tolerance} min**).
    """)

    st.warning("⚠️ **IMPORTANT**: Please ensure your files are in **.xlsx** format.")
    col1, col2 = st.columns(2)
    with col1:
        sample_file = st.file_uploader("Upload SAMPLE File (.xlsx only)", type=['xlsx'], key="single_sample")
    with col2:
        blank_file = st.file_uploader("Upload BLANK File (.xlsx only)", type=['xlsx'], key="single_blank")

    if sample_file and blank_file:
        try:
            h_s, df_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
            h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

            res_s = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
            df_s['In_Blank'] = [x[0] for x in res_s]
            df_s['RT_Diff'] = [x[1] for x in res_s]

            df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
            
            total_sample_peaks = len(df_s)
            total_area_original = df_s['Area (Ab*s)'].sum()
            clean_area_sum = df_final[df_final['Chemical_Status'] == "Clean (Lipid/Oxidation)"]['Area (Ab*s)'].sum()
            purity = (clean_area_sum / total_area_original * 100) if total_area_original > 0 else 0
            final_count = len(df_final)
            excluded = len(df_s[df_s['In_Blank'] == "YES"])

            st.subheader("📊 Halal Integrity Metrics (Area-Weighted)")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Peaks Detected", total_sample_peaks)
            m2.metric("Blank Matches (Purged)", excluded, delta=f"-{excluded}", delta_color="inverse")
            m3.metric("Final Biomarkers", final_count)
            
            # --- THE UPDATE: Added help parameter for the tooltip ---
            m4.metric(
                "Sample Purity Score", 
                f"{purity:.1f}%",
                help="""
                **Integrity Metric Explanation:**
                This score represents the concentration-weighted purity of the lipid profile. 
                It filters out solvent background (blank) and non-lipid artifacts.
                
                **Formula:**
                (Σ Area of Clean Lipid Peaks / Total Original Peak Area) × 100
                """
            )

            t1, t2, t3, t4 = st.tabs(["1. Solvent Blank", "2. Sample Mapping", "3. Final Fingerprint", "4. RT Analysis"])
            
            with t1:
                def highlight_blank(row):
                    styles = ['' for _ in row.index]; n = row['Chemical_Status']; match = row['In_Sample']
                    if n == "Review (Potential Contaminant)": styles = ['background-color: #FFC0CB' for _ in row.index]
                    elif match == "YES": styles = ['background-color: #FFEB9C' for _ in row.index]
                    elif match == "RT_SHIFT_DETECTED": styles[row.index.get_loc('RT (min)')] = 'background-color: #002060; color: white'
                    return styles
                st.dataframe(df_b.style.apply(highlight_blank, axis=1))

            with t2:
                def highlight_sample(row):
                    styles = ['' for _ in row.index]; n = row['Chemical_Status']; match = row['In_Blank']
                    if n == "Review (Potential Contaminant)": styles = ['background-color: #FFC0CB' for _ in row.index]
                    elif match == "YES": styles = ['background-color: #FFEB9C' for _ in row.index]
                    elif match == "RT_SHIFT_DETECTED": styles[row.index.get_loc('RT (min)')] = 'background-color: #002060; color: white'
                    return styles
                st.dataframe(df_s.style.apply(highlight_sample, axis=1))

            with t3:
                def highlight_final(row):
                    return ['background-color: #FFC0CB' if row['Chemical_Status'] == "Review (Potential Contaminant)" else '' for _ in row.index]
                st.dataframe(df_final.drop(columns=['In_Blank', 'RT_Diff']).style.apply(highlight_final, axis=1))

            with t4:
                rt_issues = df_s[df_s['In_Blank'] == "RT_SHIFT_DETECTED"]
                if not rt_issues.empty:
                    st.info(f"Found **{len(rt_issues)}** compounds with significant RT shifts.")
                    st.table(rt_issues[['Hit Name', 'RT (min)', 'RT_Diff']])
                else:
                    st.success("No significant RT shifts detected.")

            custom_filename = st.text_input("📁 Enter Filename", value="Analytical_Report", key="single_fn")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, sheet_name='Analytical_Report') 
            
            st.download_button("📥 Download Full Analytical Report", output.getvalue(), file_name=f"{custom_filename}.xlsx")
        except Exception as e: st.error(f"Error: {e}")

with main_tab2:
    st.header("🔬 Multiple Sample Analysis (PCA Master Table)")
    st.info("Upload ONE Blank and multiple Samples for PCA processing.")
    
    m_blank = st.file_uploader("1. Upload BLANK Reference", type=['xlsx'], key="multi_blank")
    m_samples = st.file_uploader("2. Upload Multiple SAMPLES", type=['xlsx'], accept_multiple_files=True, key="multi_samples")

    if m_blank and m_samples:
        _, df_b_multi = run_strict_procedure(m_blank, q_threshold, area_threshold)
        
        pca_data = []
        for f in m_samples:
            _, df_s_multi = run_strict_procedure(f, q_threshold, area_threshold)
            res = df_s_multi.apply(lambda r: check_match_expert(r, df_b_multi, rt_tolerance), axis=1)
            df_s_multi['In_Blank'] = [x[0] for x in res]
            
            df_clean = df_s_multi[df_s_multi['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
            df_clean['Sample_Name'] = f.name
            pca_data.append(df_clean)
        
        if pca_data:
            master_pca = pd.concat(pca_data)
            pivot_df = master_pca.pivot_table(
                index='Sample_Name', 
                columns='Hit Name', 
                values='Area (Ab*s)'
            ).fillna(0)
            
            st.subheader("🏁 Corrected Unique Master Table (PCA Ready)")
            st.dataframe(pivot_df)
            
            pca_out = io.BytesIO()
            with pd.ExcelWriter(pca_out, engine='xlsxwriter') as writer:
                pivot_df.to_excel(writer, sheet_name='PCA_Data')
            
            st.download_button(
                label="📥 Download PCA Master Table",
                data=pca_out.getvalue(),
                file_name="PCA_Master_Table_Original_Abs.xlsx"
            )
