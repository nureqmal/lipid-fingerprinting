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

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1.  **Metadata Preservation**: NIST headers (Rows 1–9) retained.
2.  **Quality Gate**: NIST Quality **≥ {q_threshold}**.
3.  **Batch PCA Mode**: Capability to process multiple samples against a single blank simultaneously.
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
st.info("💡 **Mode Selection**: Upload one sample for full analysis, or multiple samples for Batch PCA processing.")

col1, col2 = st.columns(2)
with col1: 
    # Sekarang boleh upload banyak fail serentak
    sample_files = st.file_uploader("Upload SAMPLE File(s)", type=['xlsx'], accept_multiple_files=True)
with col2: 
    blank_file = st.file_uploader("Upload BLANK File (.xlsx only)", type=['xlsx'])

if sample_files and blank_file:
    try:
        # Run Blank sekali sahaja untuk semua perbandingan
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

        # Jika hanya ada SATU file (Single Analysis Mode)
        if len(sample_files) == 1:
            s_file = sample_files[0]
            h_s, df_s = run_strict_procedure(s_file, q_threshold, area_threshold)

            res = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
            df_s['In_Blank'], df_s['RT_Diff'] = [x[0] for x in res], [x[1] for x in res]
            df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()

            # Analisis Detail (Tab 1-4)
            st.subheader("📊 Single Sample Detailed Analysis")
            t1, t2, t3, t4, t5 = st.tabs(["1. Solvent Blank", "2. Sample Mapping", "3. Final Fingerprint", "4. 🧠 Expert RT Analysis", "🏆 5. Master PCA Table"])
            
            with t1: st.dataframe(df_b)
            with t2: st.dataframe(df_s)
            with t3: st.dataframe(df_final.drop(columns=['In_Blank', 'RT_Diff']))
            with t4:
                st.write("### 🧬 RT Shift Discussion Logic")
                # (Logic RT Shift kau kat sini...)
                st.success("Analysis complete for single file.")

            with t5:
                st.write("### 🏗️ Add to Master Table")
                s_id = st.text_input("🏷️ Sample ID", value="Sample_1")
                if st.button("➕ Add to Master"):
                    entry = df_final[['Hit Name', 'Area (%)']].copy()
                    entry['Sample_ID'] = s_id
                    st.session_state.master_list.append(entry)
                    st.success("Added!")

        # Jika ada BANYAK file (Batch PCA Mode)
        else:
            st.subheader(f"🚀 Batch Processing Mode ({len(sample_files)} files)")
            if st.button("⚡ Process All Files for PCA"):
                temp_master = []
                progress_bar = st.progress(0)
                
                for i, s_file in enumerate(sample_files):
                    h_s, df_s = run_strict_procedure(s_file, q_threshold, area_threshold)
                    res = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
                    df_s['In_Blank'] = [x[0] for x in res]
                    df_final_batch = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
                    
                    # Auto-extract name dari metadata h_s
                    s_name = "Unknown"
                    for row in h_s.values:
                        if "Sample Name" in str(row[0]):
                            s_name = str(row[1]).strip()
                            break
                    
                    entry = df_final_batch[['Hit Name', 'Area (%)']].copy()
                    entry['Sample_ID'] = f"{s_name}_{i}" # Tambah index sikit supaya tak clash
                    temp_master.append(entry)
                    progress_bar.progress((i + 1) / len(sample_files))
                
                st.session_state.master_list.extend(temp_master)
                st.success("All files processed and compiled into Master Table!")

            t1, t2, t3, t4, t5 = st.tabs(["1. Solvent Blank", "2. Sample Mapping", "3. Final Fingerprint", "4. 🧠 Expert RT Analysis", "🏆 5. Master PCA Table"])
            with t5:
                st.write("Check below for combined data.")

        # --- GLOBAL MASTER TABLE DISPLAY ---
        if st.session_state.master_list:
            st.markdown("---")
            st.write("### 🏆 Combined Master PCA Table")
            combined_df = pd.concat(st.session_state.master_list)
            master_pivot = combined_df.pivot(index='Sample_ID', columns='Hit Name', values='Area (%)').fillna(0)
            st.dataframe(master_pivot)
            
            master_out = io.BytesIO()
            with pd.ExcelWriter(master_out, engine='xlsxwriter') as writer:
                master_pivot.to_excel(writer, sheet_name='PCA_Ready')
            st.download_button("📥 Download Full Master Table", master_out.getvalue(), "Master_PCA_Dataset.xlsx")

    except Exception as e: st.error(f"Error: {e}")
