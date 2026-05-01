import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Batch PCA Suite")

# --- SESSION STATE (Tetap Simpan untuk Master Table) ---
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

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1.  **Batch Processing**: Multiple samples compared against a single Solvent Blank.
2.  **Auto-Compile**: All processed samples automatically added to Master PCA Table.
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

# --- BATCH FILE UPLOAD SECTION ---
st.warning("⚠️ **BATCH MODE**: Select ONE Blank file and MULTIPLE Sample files.")

col1, col2 = st.columns(2)
with col1: 
    # Perhatikan: accept_multiple_files=True
    sample_files = st.file_uploader("Upload ALL Sample Files", type=['xlsx'], accept_multiple_files=True)
with col2: 
    blank_file = st.file_uploader("Upload Solvent BLANK File", type=['xlsx'])

if sample_files and blank_file:
    try:
        # 1. Run Blank sekali je
        h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)
        
        # Simpan result batch dalam list sementara
        batch_results = []

        # 2. Loop setiap sample yang diupload
        for s_file in sample_files:
            h_s, df_s = run_strict_procedure(s_file, q_threshold, area_threshold)

            # --- EXPERT RT SHIFT LOGIC (UNTOUCHED) ---
            def check_match_expert(row, target_df, tol):
                matches = target_df[target_df['Hit Name'] == row['Hit Name']]
                if matches.empty: return "NO", None
                for _, t_row in matches.iterrows():
                    diff = abs(row['RT (min)'] - t_row['RT (min)'])
                    if diff <= tol: return "YES", diff 
                closest_diff = matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()
                return "RT_SHIFT_DETECTED", closest_diff

            res = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
            df_s['In_Blank'], df_s['RT_Diff'] = [x[0] for x in res], [x[1] for x in res]
            df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()

            # Auto-Extract Sample Name dari metadata
            s_name = "Unknown"
            for row in h_s.values:
                if "Sample Name" in str(row[0]):
                    s_name = str(row[1]).strip()
                    break
            
            # Masukkan dalam list untuk Master Table
            master_entry = df_final[['Hit Name', 'Area (%)']].copy()
            master_entry['Sample_ID'] = s_name
            batch_results.append(master_entry)

        # Update Master List Global
        if st.button("🚀 Process & Compile All to Master Table"):
            st.session_state.master_list.extend(batch_results)
            st.success(f"Successfully processed {len(sample_files)} samples!")

        # --- DISPLAY MASTER TABLE ---
        if st.session_state.master_list:
            st.subheader("🏆 Master PCA Table")
            combined_df = pd.concat(st.session_state.master_list)
            master_pivot = combined_df.pivot(index='Sample_ID', columns='Hit Name', values='Area (%)').fillna(0)
            
            st.dataframe(master_pivot)
            
            # Export Master
            master_out = io.BytesIO()
            with pd.ExcelWriter(master_out, engine='xlsxwriter') as writer:
                master_pivot.to_excel(writer, sheet_name='PCA_Ready')
            
            st.download_button("📥 Download Master Table for PCA", master_out.getvalue(), "Master_PCA_Dataset.xlsx")

    except Exception as e: st.error(f"Error processing batch: {e}")
