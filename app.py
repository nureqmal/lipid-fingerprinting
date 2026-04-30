import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Master Analytical Suite")

# --- SIDEBAR CONTROL ---
st.sidebar.header("📋 Project Info")
researcher = st.sidebar.text_input("Researcher Name", "Dr. Eqmal")
project_id = st.sidebar.text_input("Project ID", "HALAL-LIPID-2026")

st.sidebar.header("⚙️ Analytical Controls")
q_threshold = st.sidebar.slider("NIST Quality Threshold", 50, 95, 80, 5)
rt_tolerance = st.sidebar.slider("RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01)
area_threshold = st.sidebar.slider("Min Area % (Noise Filter)", 0.0, 5.0, 0.1, 0.1)

st.markdown(f"""
**Researcher:** {researcher} | **Project ID:** {project_id}
---
### SOP Summary:
*   **Identification:** NIST Match ≥ {q_threshold}
*   **Validation:** RT Tolerance ±{rt_tolerance} min
*   **Sensitivity:** Min Area % ≥ {area_threshold}% (Removing baseline noise)
---
""")

def run_strict_procedure(file, q_min, area_min):
    df_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    header = df_raw.iloc[0:9, :].copy()
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip() 

    # Basic Cleaning
    df = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df['Quality'] = pd.to_numeric(df['Quality'], errors='coerce')
    
    # Calculate Area %
    total_area = df['Area (Ab*s)'].sum()
    df['Area (%)'] = (df['Area (Ab*s)'] / total_area) * 100
    
    # Filter by Quality & Area %
    df = df[(df['Quality'] >= q_min) & (df['Area (%)'] >= area_min)]

    # Expert Classification
    blacklist = ['siloxane', 'phthalate', 'bleed', 'plasticizer', 'adipate']
    def classify(name):
        n = str(name).lower()
        if any(x in n for x in blacklist): return "Discard (Artifact)"
        return "Clean (Lipid/Oxidation)"

    df['Chemical_Status'] = df['Hit Name'].apply(classify)
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    
    return header, df.sort_values(by='RT (min)')

col1, col2 = st.columns(2)
with col1: sample_file = st.file_uploader("Upload SAMPLE", type=['xlsx'])
with col2: blank_file = st.file_uploader("Upload BLANK", type=['xlsx'])

if sample_file and blank_file:
    try:
        h_s, df_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
        h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

        def check_match(row, ref_df, tol):
            m = ref_df[ref_df['Hit Name'] == row['Hit Name']]
            for _, r in m.iterrows():
                if abs(row['RT (min)'] - r['RT (min)']) <= tol: return "YES"
            return "NO"

        df_s['Matched_In_Blank?'] = df_s.apply(lambda r: check_match(r, df_b, rt_tolerance), axis=1)
        df_b['Matched_In_Sample?'] = df_b.apply(lambda r: check_match(r, df_s, rt_tolerance), axis=1)
        df_final = df_s[df_s['Matched_In_Blank?'] == "NO"].copy()
        
        # --- METRICS ---
        st.subheader("📊 Executive Summary Dashboard")
        m1, m2, m3, m4 = st.columns(4)
        total, excl = len(df_s), len(df_s[df_s['Matched_In_Blank?']=="YES"])
        purity = (len(df_final)/total*100) if total > 0 else 0
        
        m1.metric("Total Unique Peaks", total)
        m2.metric("Blank Matches", excl, delta=f"-{excl}", delta_color="inverse")
        m3.metric("Final Biomarkers", len(df_final))
        m4.metric("Purity Score", f"{purity:.1f}%")

        # Distribution Table
        st.write("### 🧬 Chemical Class Integrity")
        counts = df_final['Chemical_Status'].value_counts().reset_index()
        st.table(counts)

        # --- TABS ---
        t1, t2, t3 = st.tabs(["Solvent Blank", "Sample Mapping", "Final Fingerprint"])
        with t1: st.dataframe(df_b.style.apply(lambda x: ['background: #FFEB9C' if x['Matched_In_Sample?']=='YES' else '' for _ in x], axis=1))
        with t2: st.dataframe(df_s.style.apply(lambda x: ['background: #FFEB9C' if x['Matched_In_Blank?']=='YES' else '' for _ in x], axis=1))
        with t3: st.dataframe(df_final.drop(columns=['Matched_In_Blank?']))

        # --- EXCEL EXPORT ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            ws_d = writer.book.add_worksheet('Dashboard')
            fmt = writer.book.add_format({'bold':True, 'bg_color':'#2E75B6', 'font_color':'white', 'border':1, 'align':'center'})
            ws_d.merge_range('B2:E2', 'OFFICIAL ANALYTICAL SUMMARY', fmt)
            ws_d.write('B4', 'Analyst'); ws_d.write('C4', researcher)
            ws_d.write('B5', 'Project ID'); ws_d.write('C5', project_id)
            ws_d.write('B6', 'NIST Quality Filter'); ws_d.write('C6', q_threshold)
            ws_d.write('B7', 'RT Tolerance'); ws_d.write('C7', rt_tolerance)
            ws_d.write('B8', 'Final Biomarkers'); ws_d.write('C8', len(df_final))
            ws_d.write('B9', 'Purity Score'); ws_d.write('C9', f"{purity:.2f}%")
            
            # (Analytical Report Logic remains same as previous version)
            rs = 'Analytical_Report'
            h_b.to_excel(writer, sheet_name=rs, startrow=1, index=False, header=False)
            df_b.to_excel(writer, sheet_name=rs, startrow=10, index=False, header=False)
            s2 = len(df_b) + 15
            h_s.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
            df_s.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
            s3 = s2 + len(df_s) + 15
            fh = h_s.copy(); fh.iloc[0,0] = f"{fh.iloc[0,0]} (FINAL FINGERPRINT)"
            fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
            df_final.drop(columns=['Matched_In_Blank?']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)

        st.download_button("📥 Download Official Report", output.getvalue(), f"{project_id}_Final_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
