import streamlit as st
import pandas as pd
import io

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
1.  **Metadata Preservation**: Captures and retains original NIST headers (Rows 1–9) for full traceability.
2.  **Dynamic Quality Thresholding**: Currently filtering peaks with NIST Quality **≥ {q_threshold}**.
3.  **Expert Chemical Classification**: Categorizes compounds into Clean Lipids, Artifacts, or Contaminants.
4.  **RT-Aware Blank Exclusion**: Matches compounds using Name + RT Tolerance (±0.05 min).
5.  **Strict Authentication**: Matched compounds are entirely purged to ensure a unique fingerprint.
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

        rt_tolerance = 0.05
        def check_match(row, target_df):
            matches = target_df[target_df['Hit Name'] == row['Hit Name']]
            for _, t_row in matches.iterrows():
                if abs(row['RT (min)'] - t_row['RT (min)']) <= rt_tolerance: return "YES"
            return "NO"

        df_sample['Matched_In_Blank?'] = df_sample.apply(lambda r: check_match(r, df_blank), axis=1)
        df_blank['Matched_In_Sample?'] = df_blank.apply(lambda r: check_match(r, df_sample), axis=1)
        df_final = df_sample[df_sample['Matched_In_Blank?'] == "NO"].copy()
        
        # Metrics Calculation
        total_sample = len(df_sample)
        excluded = len(df_sample[df_sample['Matched_In_Blank?'] == "YES"])
        final_count = len(df_final)
        purity = (final_count / total_sample * 100) if total_sample > 0 else 0
        
        # UI Display Metrics
        st.subheader("📊 Analysis Summary Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Sample Peaks", f"{total_sample}")
        m2.metric("Blank Matches (Excluded)", f"{excluded}", delta=f"-{excluded}", delta_color="inverse")
        m3.metric("Final Unique Compounds", f"{final_count}")
        m4.metric("Sample Purity Score", f"{purity:.1f}%")

        # Class Distribution for Dashboard
        class_counts = df_final['Chemical_Status'].value_counts()

        st.markdown("---")

        # TABS Display
        t1, t2, t3 = st.tabs(["1. Solvent Blank Data", "2. Sample Mapping", "3. Final Unique Fingerprint"])
        with t1: st.dataframe(df_blank.style.apply(lambda x: ['background: #FFEB9C' if x['Matched_In_Sample?'] == 'YES' else '' for _ in x], axis=1))
        with t2: st.dataframe(df_sample.style.apply(lambda x: ['background: #FFEB9C' if x['Matched_In_Blank?'] == 'YES' else '' for _ in x], axis=1))
        with t3: st.dataframe(df_final.drop(columns=['Matched_In_Blank?']))

        # --- EXCEL EXPORT WITH INTEGRATED DASHBOARD ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Sheet 1: Dashboard
            ws_dash = writer.book.add_worksheet('Dashboard')
            wb = writer.book
            
            # Formats
            header_fmt = wb.add_format({'bold': True, 'font_size': 16, 'bg_color': '#2E75B6', 'font_color': 'white', 'border': 1, 'align': 'center'})
            sub_fmt = wb.add_format({'bold': True, 'font_size': 12, 'bg_color': '#D9E1F2', 'border': 1})
            val_fmt = wb.add_format({'border': 1, 'align': 'center'})
            
            # Title
            ws_dash.merge_range('B2:E2', 'LIPIDEXPERT ANALYTICAL SUMMARY', header_fmt)
            
            # Section 1: Overall Performance
            ws_dash.write('B4', 'OVERALL PERFORMANCE', sub_fmt)
            ws_dash.write('C4', 'VALUE', sub_fmt)
            
            metrics = [
                ('Quality Threshold Used', q_threshold),
                ('Total Cleaned Sample Peaks', total_sample),
                ('Blank Matches (Excluded)', excluded),
                ('Final Unique Biomarkers', final_count),
                ('Sample Purity Score', f"{purity:.2f}%")
            ]
            
            for i, (l, v) in enumerate(metrics, start=5):
                ws_dash.write(f'B{i}', l, wb.add_format({'border': 1}))
                ws_dash.write(f'C{i}', v, val_fmt)
            
            # Section 2: Lipid Class Distribution (NEW SECTION)
            start_class_row = len(metrics) + 7
            ws_dash.write(f'B{start_class_row}', 'FINAL CLASS DISTRIBUTION', sub_fmt)
            ws_dash.write(f'C{start_class_row}', 'COUNT', sub_fmt)
            
            for i, (cls_name, count) in enumerate(class_counts.items(), start=start_class_row + 1):
                ws_dash.write(f'B{i}', cls_name, wb.add_format({'border': 1}))
                ws_dash.write(f'C{i}', count, val_fmt)

            ws_dash.set_column('B:B', 35); ws_dash.set_column('C:C', 20)

            # Sheet 2: Analytical Report
            rs = 'Analytical_Report'
            blank_header.to_excel(writer, sheet_name=rs, startrow=1, index=False, header=False)
            df_blank.to_excel(writer, sheet_name=rs, startrow=10, index=False, header=False)
            
            s2 = len(df_blank) + 15
            sample_header.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
            df_sample.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
            
            s3 = s2 + len(df_sample) + 15
            fh = sample_header.copy(); fh.iloc[0,0] = f"{fh.iloc[0,0]} (CORRECTED UNIQUE PROFILE)"
            fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
            df_final.drop(columns=['Matched_In_Blank?']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)

            ws_rep = writer.sheets[rs]
            yellow = wb.add_format({'bg_color': '#FFEB9C'})
            ws_rep.conditional_format(10, 0, 10 + len(df_blank), 20, {'type': 'formula', 'criteria': f'=${chr(65 + len(df_blank.columns)-1)}11="YES"', 'format': yellow})
            ws_rep.conditional_format(s2+10, 0, s2+10 + len(df_sample), 20, {'type': 'formula', 'criteria': f'=${chr(65 + len(df_sample.columns)-1)}{s2+11}="YES"', 'format': yellow})

        st.download_button("📥 Download Final Report", output.getvalue(), "LipidExpert_Final_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
