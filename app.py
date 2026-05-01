import streamlit as st
import pandas as pd
import io

# Setup Page
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

# SESSION STATE
if 'master_list' not in st.session_state:
    st.session_state.master_list = []

# SIDEBAR
st.sidebar.header("⚙️ Analytical Controls")
q_threshold = st.sidebar.slider("Select NIST Quality Threshold", 50, 95, 80, 5)
rt_tolerance = st.sidebar.slider("Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01)
area_threshold = st.sidebar.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01)

if st.sidebar.button("🗑️ Reset Master Table"):
    st.session_state.master_list = []
    st.sidebar.success("Master Table Cleared!")

# MODE SWITCH
mode = st.radio("🧭 Select Analysis Mode", ["Single Analysis", "Batch Analysis"])

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1. Quality ≥ {q_threshold}
2. Area ≥ {area_threshold:.2f}%
3. RT tolerance ±{rt_tolerance}
---
""")

# =========================
# --- CODE EMAS (UNCHANGED)
# =========================
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


# =========================
# FILE UPLOAD
# =========================
if mode == "Single Analysis":
    col1, col2 = st.columns(2)
    with col1:
        sample_file = st.file_uploader("Upload SAMPLE File", type=['xlsx'])
    with col2:
        blank_file = st.file_uploader("Upload BLANK File", type=['xlsx'])

elif mode == "Batch Analysis":
    sample_files = st.file_uploader("📦 Upload MULTIPLE SAMPLE Files", type=['xlsx'], accept_multiple_files=True)
    blank_file = st.file_uploader("Upload SINGLE BLANK File", type=['xlsx'])

# =========================
# SINGLE MODE (UNCHANGED FLOW)
# =========================
if mode == "Single Analysis" and sample_file and blank_file:
    st.success("Single analysis running... (original pipeline)")

    h_s, df_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
    h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

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

    res = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
    df_s['In_Blank'] = [x[0] for x in res]

    df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])]

    st.write("### Final Fingerprint")
    st.dataframe(df_final)

# =========================
# 🔥 BATCH MODE (NEW)
# =========================
if mode == "Batch Analysis" and sample_files and blank_file:

    st.subheader("📦 Batch Processing Mode")

    h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

    master_list_auto = []
    summary_list = []

    for file in sample_files:
        sample_name = file.name.replace(".xlsx", "")

        h_s, df_s = run_strict_procedure(file, q_threshold, area_threshold)

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

        res = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
        df_s['In_Blank'] = [x[0] for x in res]

        df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])]

        total_sample = len(df_s)
        final_count = len(df_final)
        purity = (final_count / total_sample * 100) if total_sample > 0 else 0

        summary_list.append({
            "Sample": sample_name,
            "Total Peaks": total_sample,
            "Final Compounds": final_count,
            "Purity (%)": round(purity, 2)
        })

        entry = df_final[['Hit Name', 'Area (%)']].copy()
        entry['Sample_ID'] = sample_name
        master_list_auto.append(entry)

    st.write("### 📊 Batch Summary")
    st.dataframe(pd.DataFrame(summary_list))

    combined_df = pd.concat(master_list_auto)
    master_pivot = combined_df.pivot(index='Sample_ID', columns='Hit Name', values='Area (%)').fillna(0)

    st.write("### 🧠 PCA Ready Table")
    st.dataframe(master_pivot)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        master_pivot.to_excel(writer, sheet_name='PCA_Ready')

    st.download_button("📥 Download Batch PCA", output.getvalue(), "Batch_PCA.xlsx")
