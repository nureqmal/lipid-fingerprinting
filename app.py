import streamlit as st
import pandas as pd
import io
import matplotlib.pyplot as plt

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

# --- SIDEBAR CONTROL (Point No. 4) ---
st.sidebar.header("⚙️ Analytical Controls")
q_threshold = st.sidebar.slider(
    "Select NIST Quality Threshold", 
    min_value=50, 
    max_value=95, 
    value=80, 
    step=5,
    help="Higher values ensure better identification certainty but may reduce the number of peaks."
)

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1.  **Metadata Preservation**: Captures and retains original NIST headers (Rows 1–9).
2.  **Dynamic Quality Thresholding**: Currently filtering peaks with NIST Quality **≥ {q_threshold}**.
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
    
    # Apply Dynamic Threshold
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
        # Use the q_threshold from the slider
        sample_header, df_sample = run_strict_procedure(sample_file, q_threshold)
        blank_header, df_blank = run_strict_procedure(blank_file, q_threshold)

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
        
        # --- CALCULATE METRICS ---
        total_sample = len(df_sample)
        excluded = len(df_sample[df_sample['Matched_In_Blank?'] == "YES"])
        final_count = len(df_final)
        purity = (final_count / total_sample * 100) if total_sample > 0 else 0
        
        # --- UI DASHBOARD ---
        st.subheader("📊 Analysis Summary Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Sample Peaks", f"{total_sample}")
        m2.metric("Blank Matches (Excluded)", f"{excluded}", delta=f"-{excluded}", delta_color="inverse")
        m3.metric("Final Unique Compounds", f"{final_count}")
        m4.metric("Sample Purity Score", f"{purity:.1f}%")
        
        # --- NEW: VISUALIZATION (Point No. 3) ---
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Chemical Class Distribution")
            if not df_final.empty:
                class_counts = df_final['Chemical_Status'].value_counts()
                fig, ax = plt.subplots()
                ax.pie(class_counts, labels=class_counts.index, autopct='%1.1f%%', startangle=90, colors=['#66b3ff','#ff9999'])
                ax.axis('equal')
                st.pyplot(fig)
        with c2:
            st.write("### Quality Score Distribution")
            if not df_final.empty:
                fig2, ax2 = plt.subplots()
                ax2.hist(df_final['Quality'], bins=10, color='skyblue', edgecolor='black')
                ax2.set_xlabel("NIST Quality Score")
                ax2.set_ylabel("Frequency")
                st.pyplot(fig2)

        st.markdown("---")

        # --- TABS & EXCEL EXPORT (Same as before but with added Charts in Excel if needed) ---
        t1, t2, t3 = st.tabs(["1. Solvent Blank Data", "2. Sample Mapping", "3. Final Unique Fingerprint"])
        with t1: st.dataframe(df_blank.style.apply(lambda x: ['background: #FFEB9C' if x['Matched_In_Sample?'] == 'YES' else '' for _ in x], axis=1))
        with t2: st.dataframe(df_sample.style.apply(lambda x: ['background: #FFEB9C' if x['Matched_In_Blank?'] == 'YES' else '' for _ in x], axis=1))
        with t3: st.dataframe(df_final.drop(columns=['Matched_In_Blank?']))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # DASHBOARD SHEET
            ws_dash = writer.book.add_worksheet('Dashboard')
            header_fmt = writer.book.add_format({'bold': True, 'font_size': 18, 'bg_color': '#2E75B6', 'font_color': 'white', 'align': 'center'})
            ws_dash.merge_range('B2:E2', 'LIPIDEXPERT ANALYTICAL SUMMARY', header_fmt)
            ws_dash.write('B4', 'Metric', writer.book.add_format({'bold': True}))
            ws_dash.write('C4', 'Value', writer.book.add_format({'bold': True}))
            ws_dash.write('B5', 'Quality Threshold Used'); ws_dash.write('C5', q_threshold)
            ws_dash.write('B6', 'Total Sample Peaks'); ws_dash.write('C6', total_sample)
            ws_dash.write('B7', 'Blank Matches Purged'); ws_dash.write('C7', excluded)
            ws_dash.write('B8', 'Final Unique Biomarkers'); ws_dash.write('C8', final_count)
            ws_dash.write('B9', 'Purity Score'); ws_dash.write('C9', f"{purity:.2f}%")

            # REPORT SHEET (Same 3-table logic)
            report_sheet = 'Analytical_Report'
            # (Insert Table 1, 2, 3 logic here - omitted for brevity but remains the same as previous)
            # ... [Code Table 1, 2, 3 remains identical] ...
            
            # (Self-correction: I will keep the full table logic to ensure your code works 100%)
            blank_header.to_excel(writer, sheet_name=report_sheet, startrow=1, index=False, header=False)
            df_blank.to_excel(writer, sheet_name=report_sheet, startrow=10, index=False, header=False)
            s2_start = len(df_blank) + 15
            sample_header.to_excel(writer, sheet_name=report_sheet, startrow=s2_start + 1, index=False, header=False)
            df_sample.to_excel(writer, sheet_name=report_sheet, startrow=s2_start + 10, index=False, header=False)
            s3_start = s2_start + len(df_sample) + 15
            # final_header setup
            f_h = sample_header.copy(); f_h.iloc[0,0] = f"{f_h.iloc[0,0]} (UNIQUE PROFILE)"
            f_h.to_excel(writer, sheet_name=report_sheet, startrow=s3_start + 1, index=False, header=False)
            df_final.drop(columns=['Matched_In_Blank?']).to_excel(writer, sheet_name=report_sheet, startrow=s3_start + 10, index=False, header=False)

        st.download_button("📥 Download Analytical Report", output.getvalue(), "LipidExpert_Analytical_Report.xlsx")

    except Exception as e:
        st.error(f"Error: {e}")
