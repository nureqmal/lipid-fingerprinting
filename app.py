import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

st.markdown("""
---
### Standard Operating Procedure (SOP):
1.  **Metadata Preservation**: The system captures and retains the original NIST header (Rows 1–9) for all analytical tables to ensure full sample traceability.
2.  **Quality Thresholding**: Data is filtered through a NIST Match Factor (Quality) threshold of **≥ 80**.
3.  **Expert Chemical Classification**: Known artifacts are discarded, and potential contaminants are flagged for review.
4.  **RT-Aware Blank Exclusion**: Matches compounds between Sample and Blank using **Name + RT Tolerance (±0.05 min)**.
5.  **Strict Authentication**: Matched compounds are purged to ensure a 100% unique fingerprint.
---
""")

def run_strict_procedure(file):
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    df_header = df_full_raw.iloc[0:9, :].copy()
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip() 

    df_clean = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df_clean['Quality'] = pd.to_numeric(df_clean['Quality'], errors='coerce')
    df_clean = df_clean[df_clean['Quality'] >= 80]

    blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
    contaminants = ['iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene', 'benzothiophene', 'naphthalene', 'benzene,']

    def classify_compound(name):
        name_lower = str(name).lower()
        if any(x in name_lower for x in blacklist): return "Discard (Artifact/Bleed)"
        if any(x in name_lower for x in contaminants): return "Review (Potential Contaminant)"
        return "Clean (Lipid/Oxidation Product)"

    df_clean['Chemical_Status'] = df_clean['Hit Name'].apply(classify_compound)
    df_clean = df_clean[df_clean['Chemical_Status'] != "Discard (Artifact/Bleed)"]

    df_clean = df_clean.sort_values(by='Area (Ab*s)', ascending=False)
    df_clean = df_clean.drop_duplicates(subset=['Hit Name'], keep='first')
    df_clean = df_clean.sort_values(by='RT (min)')
    
    return df_header, df_clean

col1, col2 = st.columns(2)
with col1:
    sample_file = st.file_uploader("Upload SAMPLE File", type=['xlsx'])
with col2:
    blank_file = st.file_uploader("Upload BLANK File (Solvent)", type=['xlsx'])

if sample_file and blank_file:
    try:
        sample_header, df_sample = run_strict_procedure(sample_file)
        blank_header, df_blank = run_strict_procedure(blank_file)

        rt_tolerance = 0.05
        def check_match(row, target_df):
            matches = target_df[target_df['Hit Name'] == row['Hit Name']]
            if matches.empty: return "NO"
            for _, t_row in matches.iterrows():
                if abs(row['RT (min)'] - t_row['RT (min)']) <= rt_tolerance:
                    return "YES"
            return "NO"

        df_sample['Matched_In_Blank?'] = df_sample.apply(lambda r: check_match(r, df_blank), axis=1)
        df_blank['Matched_In_Sample?'] = df_blank.apply(lambda r: check_match(r, df_sample), axis=1)

        df_final = df_sample[df_sample['Matched_In_Blank?'] == "NO"].copy()
        
        # --- NEW: INTERACTIVE METRICS DASHBOARD ---
        st.subheader("📊 Analysis Summary Metrics")
        m1, m2, m3, m4 = st.columns(4)
        
        total_sample = len(df_sample)
        excluded = len(df_sample[df_sample['Matched_In_Blank?'] == "YES"])
        final_count = len(df_final)
        purity = (final_count / total_sample * 100) if total_sample > 0 else 0
        
        m1.metric("Total Sample Peaks", f"{total_sample}")
        m2.metric("Blank Matches (Excluded)", f"{excluded}", delta=f"-{excluded}", delta_color="inverse")
        m3.metric("Final Unique Compounds", f"{final_count}", str(final_count))
        m4.metric("Sample Purity Score", f"{purity:.1f}%")
        
        st.markdown("---")

        final_header = sample_header.copy()
        final_header.iloc[0,0] = f"{final_header.iloc[0,0]} (CORRECTED: UNIQUE PROFILE)"

        # --- UI DISPLAY ---
        t1, t2, t3 = st.tabs(["1. Solvent Blank Data", "2. Sample Mapping", "3. Final Unique Fingerprint"])
        
        with t1: 
            st.dataframe(df_blank.style.apply(lambda x: ['background: #FFEB9C' if x['Matched_In_Sample?'] == 'YES' else '' for _ in x], axis=1))
        with t2: 
            st.dataframe(df_sample.style.apply(lambda x: ['background: #FFEB9C' if x['Matched_In_Blank?'] == 'YES' else '' for _ in x], axis=1))
        with t3: 
            st.dataframe(df_final.drop(columns=['Matched_In_Blank?']))

        # --- EXCEL EXPORT ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            sheet = 'Analytical_Report'
            blank_header.to_excel(writer, sheet_name=sheet, startrow=1, index=False, header=False)
            df_blank.to_excel(writer, sheet_name=sheet, startrow=10, index=False, header=False)
            s2_start = len(df_blank) + 15
            sample_header.to_excel(writer, sheet_name=sheet, startrow=s2_start + 1, index=False, header=False)
            df_sample.to_excel(writer, sheet_name=sheet, startrow=s2_start + 10, index=False, header=False)
            s3_start = s2_start + len(df_sample) + 15
            final_header.to_excel(writer, sheet_name=sheet, startrow=s3_start + 1, index=False, header=False)
            df_final.drop(columns=['Matched_In_Blank?']).to_excel(writer, sheet_name=sheet, startrow=s3_start + 10, index=False, header=False)

            wb, ws = writer.book, writer.sheets[sheet]
            title_fmt = wb.add_format({'bold': True, 'font_size': 14, 'bg_color': '#D3D3D3', 'border': 1})
            red_fmt = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            yellow_fmt = wb.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})

            ws.write(0, 0, "TABLE 1: CLEANED SOLVENT BLANK DATA", title_fmt)
            ws.write(s2_start, 0, "TABLE 2: RAW SAMPLE DATA (EXCLUSION MAPPING)", title_fmt)
            ws.write(s3_start, 0, "TABLE 3: UNIQUE LIPID FINGERPRINT (FINAL)", title_fmt)

            ws.conditional_format(10, 0, 10 + len(df_blank), 25, {'type': 'formula', 'criteria': f'=${chr(65 + len(df_blank.columns)-1)}11="YES"', 'format': yellow_fmt})
            ws.conditional_format(s2_start + 10, 0, s2_start + 10 + len(df_sample), 25, {'type': 'formula', 'criteria': f'=${chr(65 + len(df_sample.columns)-1)}{s2_start+11}="YES"', 'format': yellow_fmt})
            ws.conditional_format(0, 0, 5000, 30, {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': red_fmt})

        st.download_button("📥 Download Analytical Report", output.getvalue(), "LipidExpert_Analytical_Report.xlsx")

    except Exception as e:
        st.error(f"Execution Error: {e}")
