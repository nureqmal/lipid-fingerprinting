import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

# --- SIDEBAR CONTROL ---
st.sidebar.header("⚙️ Analytical Controls")

q_threshold = st.sidebar.slider("Select NIST Quality Threshold", 50, 95, 80, 5)
rt_tolerance = st.sidebar.slider("Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01)
area_threshold = st.sidebar.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01)

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1.  **Metadata Preservation**: Captures and retains original NIST headers (Rows 1–9).
2.  **Quality Gate**: Filtering peaks with NIST Quality **≥ {q_threshold}**.
3.  **Noise Reduction**: Removing baseline peaks with Area **< {area_threshold:.2f}%**.
4.  **RT-Aware Matching**: Matching compounds using Name + RT Tolerance (**±{rt_tolerance} min**).
---
""")

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
    def classify_compound(name):
        n = str(name).lower()
        if any(x in n for x in blacklist): return "Discard (Artifact)"
        return "Clean (Lipid/Oxidation)"

    df['Chemical_Status'] = df['Hit Name'].apply(classify_compound)
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    
    return df_header, df.sort_values(by='RT (min)')

col1, col2 = st.columns(2)
with col1:
    sample_file = st.file_uploader("Upload SAMPLE File", type=['xlsx'])
with col2:
    blank_file = st.file_uploader("Upload BLANK File", type=['xlsx'])

if sample_file and blank_file:
    try:
        h_s, df_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
        h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

        def check_match(row, target_df, tol):
            matches = target_df[target_df['Hit Name'] == row['Hit Name']]
            for _, t_row in matches.iterrows():
                if abs(row['RT (min)'] - t_row['RT (min)']) <= tol: return "YES"
            return "NO"

        df_s['In_Blank'] = df_s.apply(lambda r: check_match(r, df_b, rt_tolerance), axis=1)
        df_b['In_Sample'] = df_b.apply(lambda r: check_match(r, df_s, rt_tolerance), axis=1)
        df_final = df_s[df_s['In_Blank'] == "NO"].copy()
        
        # --- METRICS DASHBOARD ---
        total_sample = len(df_s); excluded = len(df_s[df_s['In_Blank'] == "YES"])
        final_count = len(df_final); purity = (final_count / total_sample * 100) if total_sample > 0 else 0
        
        st.subheader("📊 Analysis Summary Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Sample Peaks", f"{total_sample}")
        m2.metric("Blank Matches (Excluded)", f"{excluded}", delta=f"-{excluded}", delta_color="inverse")
        m3.metric("Final Unique Compounds", f"{final_count}")
        m4.metric("Sample Purity Score", f"{purity:.1f}%")

        st.info("### 🧠 LipidExpert Intelligence")
        purity_status = "High" if purity > 85 else "Moderate" if purity > 60 else "Low"
        st.markdown(f"**Data Integrity Status: {purity_status}**")

        # Tabs
        t1, t2, t3 = st.tabs(["1. Solvent Blank Data", "2. Sample Mapping", "3. Final Unique Fingerprint"])
        with t1: st.dataframe(df_b.style.apply(lambda x: ['background: #FFEB9C' if x['In_Sample'] == 'YES' else '' for _ in x], axis=1))
        with t2: st.dataframe(df_s.style.apply(lambda x: ['background: #FFEB9C' if x['In_Blank'] == 'YES' else '' for _ in x], axis=1))
        with t3: st.dataframe(df_final.drop(columns=['In_Blank']))

        # --- EXCEL EXPORT (THE "PCA GOLD" EDITION) ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            wb = writer.book
            
            # --- DASHBOARD SHEET ---
            ws_dash = wb.add_worksheet('Dashboard')
            header_fmt = wb.add_format({'bold': True, 'font_size': 16, 'bg_color': '#2E75B6', 'font_color': 'white', 'border': 1, 'align': 'center'})
            ws_dash.merge_range('B2:E2', 'LIPIDEXPERT ANALYTICAL SUMMARY', header_fmt)
            
            # Legend/Guideline for Yellow highlights
            yellow_fmt = wb.add_format({'bg_color': '#FFEB9C', 'border': 1})
            ws_dash.write('B11', 'COLOR LEGEND:', wb.add_format({'bold': True}))
            ws_dash.write('B12', 'Yellow Highlight', yellow_fmt)
            ws_dash.write('C12', 'Detected in BOTH Sample & Blank (Excluded from Final Profile)')

            # --- ANALYTICAL REPORT SHEET ---
            rs = 'Analytical_Report'
            ws_rep = wb.add_worksheet(rs)
            ws_rep.write('A1', 'NOTE: Rows highlighted in YELLOW indicate compounds matched in both Sample and Blank.', wb.add_format({'italic': True, 'font_color': 'red'}))
            h_b.to_excel(writer, sheet_name=rs, startrow=2, index=False, header=False)
            df_b.to_excel(writer, sheet_name=rs, startrow=11, index=False, header=False)
            s2 = len(df_b) + 16
            h_s.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
            df_s.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)

            # --- NEW SHEET: PCA_Ready_Matrix ---
            pca_sheet = 'PCA_Ready_Matrix'
            # Prepare PCA data: Rows = Compounds, sorted by Area
            df_pca = df_final[['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)', 'Quality']].copy()
            df_pca = df_pca.sort_values(by='Area (Ab*s)', ascending=False)
            df_pca.to_excel(writer, sheet_name=pca_sheet, index=False)
            
            # Formatting PCA sheet
            ws_pca = writer.sheets[pca_sheet]
            ws_pca.set_column('A:A', 40) # Wider Compound Name
            ws_pca.set_column('B:E', 15)
            pca_header_fmt = wb.add_format({'bold': True, 'bg_color': '#E2EFDA', 'border': 1})
            for col_num, value in enumerate(df_pca.columns.values):
                ws_pca.write(0, col_num, value, pca_header_fmt)

            # Highlight conditional formatting in report
            yellow_bg = wb.add_format({'bg_color': '#FFEB9C'})
            ws_rep.conditional_format(11, 0, 11 + len(df_b), 25, {'type': 'formula', 'criteria': f'=${chr(65 + len(df_b.columns)-1)}12="YES"', 'format': yellow_bg})
            ws_rep.conditional_format(s2+10, 0, s2+10 + len(df_s), 25, {'type': 'formula', 'criteria': f'=${chr(65 + len(df_s.columns)-1)}{s2+11}="YES"', 'format': yellow_bg})

        st.download_button("📥 Download PCA-Ready Report", output.getvalue(), "LipidExpert_PCA_Analysis.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
