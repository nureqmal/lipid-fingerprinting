import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

# --- SIDEBAR CONTROL ---
st.sidebar.header("⚙️ Analytical Controls")
analysis_mode = st.sidebar.radio("Select Analysis Mode", ["Single Sample", "Multiple Samples (PCA Ready)"])
q_threshold = st.sidebar.slider("Select NIST Quality Threshold", 50, 95, 80, 5)
rt_tolerance = st.sidebar.slider("Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01)
area_threshold = st.sidebar.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01)

# --- CODE EMAS (UNTOUCHED LOGIC) ---
def run_strict_procedure(file, q_min, area_min):
    # Support for both UploadedFile and BytesIO
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

# --- UI LOGIC ---
if analysis_mode == "Single Sample":
    st.info("💡 **Single Analysis Mode**: Best for deep-diving into one specific sample.")
    col1, col2 = st.columns(2)
    with col1: sample_file = st.file_uploader("Upload SAMPLE File", type=['xlsx'])
    with col2: blank_file = st.file_uploader("Upload BLANK File", type=['xlsx'])

    if sample_file and blank_file:
        h_s, df_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
        h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)
        
        # Expert Logic (Apply Blank Correction)
        res_s = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
        df_s['In_Blank'] = [x[0] for x in res_s]
        df_s['RT_Diff'] = [x[1] for x in res_s]
        
        df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
        st.success(f"Analysis Complete. Found {len(df_final)} corrected unique compounds.")
        st.dataframe(df_final)

else:
    st.info("🚀 **Multiple Analysis Mode**: Batch processing for PCA. 1 Blank will be used to clean all Samples.")
    blank_file = st.file_uploader("1. Upload BLANK File (Fixed Reference)", type=['xlsx'])
    sample_files = st.file_uploader("2. Upload Multiple SAMPLE Files", type=['xlsx'], accept_multiple_files=True)

    if blank_file and sample_files:
        _, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)
        
        all_results = []
        
        with st.status("Processing Batch Samples...", expanded=True) as status:
            for f in sample_files:
                st.write(f"Analyzing {f.name}...")
                _, df_s = run_strict_procedure(f, q_threshold, area_threshold)
                
                # Correction Logic
                res_s = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
                df_s['In_Blank'] = [x[0] for x in res_s]
                
                # Filter out blank matches
                df_clean = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
                df_clean['Sample_Source'] = f.name
                all_results.append(df_clean)
            
            status.update(label="Batch Processing Complete!", state="complete")

        # --- PCA MASTER TABLE GENERATION ---
        if all_results:
            master_df = pd.concat(all_results)
            
            # Pivot table: Rows = Hit Name, Columns = Samples, Values = Area (%)
            pca_table = master_df.pivot_table(
                index='Hit Name', 
                columns='Sample_Source', 
                values='Area (%)'
            ).fillna(0) # Fill missing compounds with 0 for PCA
            
            st.subheader("📊 PCA Master Table (Corrected Unique Compounds)")
            st.write("This table contains cleaned biomarkers from all samples, ready for multivariate analysis.")
            st.dataframe(pca_table)

            # Export PCA Table
            output_pca = io.BytesIO()
            with pd.ExcelWriter(output_pca, engine='xlsxwriter') as writer:
                pca_table.to_excel(writer, sheet_name='PCA_Ready_Data')
            
            st.download_button(
                label="📥 Download PCA Master Table",
                data=output_pca.getvalue(),
                file_name="PCA_Master_Table.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- GLOBAL FOOTER ---
st.markdown("---")
st.caption("LipidExpert Suite | Halal Science Research | Built for Precision")
