import streamlit as st
import pandas as pd
import io
import matplotlib.pyplot as plt

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

# --- SIDEBAR CONTROL ---
st.sidebar.header("⚙️ Analytical Controls")
q_threshold = st.sidebar.slider(
    "Select NIST Quality Threshold", 
    min_value=50, 
    max_value=95, 
    value=80, 
    step=5
)

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1.  **Metadata Preservation**: Captures and retains original NIST headers (Rows 1–9).
2.  **Dynamic Quality Thresholding**: Filtering peaks with NIST Quality **≥ {q_threshold}**.
3.  **Expert Chemical Classification**: Categorizes compounds into Clean Lipids, Artifacts, or Contaminants.
4.  **RT-Aware Blank Exclusion**: Matches compounds using Name + RT Tolerance (±0.05 min).
---
""")

def run_strict_procedure(file, threshold):
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    df_header = df_full_raw.iloc[0:9, :].copy()
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip() 

    df_clean = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df_clean['Quality'] = pd.to_numeric(df_clean['Quality'], errors='coerce')
    df_clean = df_clean[df_clean['Quality'] >= threshold]

    blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
    contaminants = ['iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene', 'benzothiophene', 'naphthalene', 'benzene,']

    def classify_compound(name):
        name_lower = str(name).lower()
        if any(x in name_lower for x in blacklist): return "Discard (Artifact/Bleed)"
        if any(x in name_lower for x in contaminants): return "Review (Potential Contaminant)"
        return "Clean (Lipid/Oxidation Product)"

    df_clean['Chemical_Status'] = df_clean['Hit Name'].apply(classify_compound)
    df_clean = df_clean[df_clean['Chemical_Status'] != "Discard (Artifact/Bleed)"]
    df_clean = df_clean.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    df_clean = df_clean.sort_values(by='RT (min)')
    
    return df_header, df_clean

col1, col2 = st.columns(2)
with col1:
    sample_file = st.file_uploader("Upload SAMPLE File", type=['xlsx'])
with col2:
    blank_file = st.file_uploader("Upload BLANK File", type=['xlsx'])

if sample_file and blank_file:
    try:
        sample_header, df_sample = run_strict_procedure(sample_file, q_threshold)
        blank_header, df_blank = run_strict_procedure(blank_file, q_threshold)

        # --- SMART BLANK MATCHING ---
        rt_tolerance = 0.05
        def check_match(row, target_df):
            matches = target_df[target_df['Hit Name'] == row['Hit Name']]
            for _, t_row in matches.iterrows():
                if abs(row['RT (min)'] - t_row['RT (min)']) <= rt_tolerance: return "YES"
            return "NO"

        df_sample['Matched_In_Blank?'] = df_sample.apply(lambda r: check_match(r, df_blank), axis=1)
        df_blank['Matched_In_Sample?'] = df_blank.apply(lambda r: check_match(r, df_sample), axis=1)
        df_final = df_sample[df_sample['Matched_In_Blank?'] == "NO"].copy()
        
        # METRICS
        total_sample = len(df_sample)
        excluded = len(df_sample[df_sample['Matched_In_Blank?'] == "YES"])
        final_count = len(df_final)
        purity = (final_count / total_sample * 100) if total_sample > 0 else 0
        
        st.subheader("📊 Analysis Summary Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Sample Peaks", f"{total_sample}")
        m2.metric("Blank Matches (Excluded)", f"{excluded}", delta=f"-{excluded}", delta_color="inverse")
        m3.metric("Final Unique Compounds", f"{final_count}")
        m4.metric("Sample Purity Score", f"{purity:.1f}%")

        # TABS
        t1, t2, t3 = st.tabs(["1. Solvent Blank Data", "2. Sample Mapping", "3. Final Unique Fingerprint"])
        with t1: st.dataframe(df_blank.style.apply(lambda x: ['background: #FFEB9C' if x['Matched_In_Sample?'] == 'YES' else '' for _ in x], axis=1))
        with t2: st.dataframe(df_sample.style.apply(lambda x: ['background: #FFEB9C' if x['Matched_In_Blank?'] == 'YES' else '' for _ in x], axis=1))
        with t3: st.dataframe(df_final.drop(columns=['Matched_In_Blank?']))

        # EXCEL EXPORT
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Dashboard Sheet
            ws_dash = writer.book.add_worksheet('Dashboard')
            ws_dash.write('B2', 'LIPIDEXPERT SUMMARY', writer.book.add_format({'bold': True, 'font_size': 16}))
            ws_dash.write('B4', 'Quality Threshold'); ws_dash.write('C4', q_threshold)
            ws_dash.write('B5', 'Total Peaks'); ws_dash.write('C5', total_sample)
            ws_dash.write('B6', 'Excluded Peaks'); ws_dash.write('C6', excluded)
            ws_dash.write('B7', 'Purity Score'); ws_dash.write('C7', f"{purity:.2f}%")

            # Report Sheet
            rs = 'Analytical_Report'
            blank_header.to_excel(writer, sheet_name=rs, startrow=1, index=False, header=False)
            df_blank.to_excel(writer, sheet_name=rs, startrow=10, index=False, header=False)
            
            s2 = len(df_blank) + 15
            sample_header.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
            df_sample.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
            
            s3 = s2 + len(df_sample) + 15
            fh = sample_header.copy(); fh.iloc[0,0] = f"{fh.iloc[0,0]} (CORRECTED)"
            fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
            df_final.drop(columns=['Matched_In_Blank?']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)

            # FORMATTING
            wb, ws = writer.book, writer.sheets[rs]
            yellow = wb.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
            red = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            
            # Highlight Table 1 (Blank) - Check column Matched_In_Sample?
            blank_col_letter = chr(65 + len(df_blank.columns) - 1)
            ws.conditional_format(10, 0, 10 + len(df_blank), 20, {'type': 'formula', 'criteria': f'=${blank_col_letter}11="YES"', 'format': yellow})

            # Highlight Table 2 (Sample) - Check column Matched_In_Blank?
            sample_col_letter = chr(65 + len(df_sample.columns) - 1)
            ws.conditional_format(s2 + 10, 0, s2 + 10 + len(df_sample), 20, {'type': 'formula', 'criteria': f'=${sample_col_letter}{s2+11}="YES"', 'format': yellow})

            ws.conditional_format(0, 0, 5000, 30, {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': red})

        st.download_button("📥 Download Analytical Report", output.getvalue(), "LipidExpert_Analytical_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
