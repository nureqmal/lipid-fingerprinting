import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

# --- SIDEBAR CONTROL (UPDATED WITH TOOLTIPS) ---
st.sidebar.header("⚙️ Analytical Controls")

q_threshold = st.sidebar.slider(
    "Select NIST Quality Threshold", 50, 95, 80, 5,
    help="**NIST Match Factor:** Filters compound identity accuracy. A value >80 means the sample spectrum matches the NIST library very well. The higher the value, the fewer false positives but the higher the risk of missing real data."
)

rt_tolerance = st.sidebar.slider(
    "Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01,
    help="**Retention Time Buffer:** Time error limit for comparing Sample vs Blank. If the same compound appears in this range, it is considered a 'Solvent Peak' and will be discarded. The default of 0.05 is the gold standard for modern GC-MS."
)

area_threshold = st.sidebar.slider(
    "Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01,
    help="**Baseline Cut-off:** Removes small peaks (noise) that are not quantitatively significant. The default of 0.00 allows all data to pass through, while values ​​>0.10 are usually used to focus on the major components (Major Compounds) only."
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
st.warning("⚠️ **IMPORTANT**: Please ensure your files are in **.xlsx** format. Older **.xls** formats are not supported.")

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
            if matches.empty:
                return "NO", None
            for _, t_row in matches.iterrows():
                diff = abs(row['RT (min)'] - t_row['RT (min)'])
                if diff <= tol:
                    return "YES", diff 
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
        
        m4.metric(
            label="Sample Purity Score", 
            value=f"{purity:.1f}%",
            help="""
            **Halal Integrity Metrics (Area-Weight)**
            
            This score represents the concentration-weighted purity of the lipid profile. 
            It filters out solvent background (blank) and non-lipid artifacts.
                
            **Formula:**
            (Σ Area of Clean Lipid Peaks / Total Original Peak Area) × 100
            """
            )

        # --- DATA ANALYSIS TABS ---
        t1, t2, t3, t4 = st.tabs(["1. Solvent Blank", "2. Sample Mapping", "3
