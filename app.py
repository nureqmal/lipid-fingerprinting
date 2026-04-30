import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: GC-MS Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: GC-MS Analytical Suite")
st.markdown("""
---
### System Overview
LipidExpert is a specialized tool designed to automate the cleaning, validation, and blank subtraction of GC-MS lipidomic data. This suite ensures data integrity by filtering out non-lipid artifacts and providing full traceability of the analytical process.

### Operational Procedure:
1.  **Metadata Acquisition**: The system strictly preserves the original NIST header (Rows 1–9) for each data source to ensure sample traceability.
2.  **Quality Thresholding**: Compounds are filtered based on a minimum NIST Match Factor (Quality) of **80**.
3.  **Expert Classification**:
    *   **Artifacts**: Known instrument/solvent bleeding (e.g., siloxanes, phthalates) are automatically discarded.
    *   **Contaminants**: Potential external pollutants (e.g., halogens, petroleum-based sulfur like benzothiophenes) are flagged for manual review.
    *   **Target Compounds**: Natural lipids and their thermal oxidation products (alkanes, alkenes, aldehydes) are retained.
4.  **Peak Deduplication**: For multiple hits or recurring peaks, the system selects the entry with the **Maximum Area** for each unique compound name.
5.  **Blank Subtraction**: 
    *   The system maps identical compounds between the Sample and the Solvent Blank.
    *   **Final Area = Sample Area - Blank Area**.
    *   Compounds reduced to zero or negative area are removed from the final profile.
6.  **Comparative Reporting**: Generates a triple-table validation report for full transparency.
---
""")

def run_analytical_procedure(file):
    # 1. READ FULL DATA (Including the very first row)
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    
    # 2. EXTRACT HEADER (Rows 0-8)
    # This ensures 'Data file Name' and other metadata are captured
    df_header = df_full_raw.iloc[0:9, :].copy()
    
    # 3. READ MAIN DATASET (Header at Row 9)
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip() 

    # STEP 1: Basic Data Cleaning
    df_clean = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df_clean['Quality'] = pd.to_numeric(df_clean['Quality'], errors='coerce')
    df_clean = df_clean[df_clean['Quality'] >= 80]

    # STEP 2: Expert Chemical Classification
    blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
    contaminants = ['iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene', 'benzothiophene', 'naphthalene', 'benzene,']

    def classify_compound(name):
        name_lower = str(name).lower()
        if any(x in name_lower for x in blacklist): return "Discard (Artifact/Bleed)"
        if any(x in name_lower for x in contaminants): return "Review (Potential Contaminant)"
        return "Clean (Lipid/Oxidation Product)"

    df_clean['Chemical_Status'] = df_clean['Hit Name'].apply(classify_compound)
    # Remove Discarded Artifacts
    df_clean = df_clean[df_clean['Chemical_Status'] != "Discard (Artifact/Bleed)"]

    # STEP 3: Deduplication (Peak Picking)
    df_clean = df_clean.sort_values(by='Area (Ab*s)', ascending=False)
    df_clean = df_clean.drop_duplicates(subset=['Hit Name'], keep='first')
    df_clean = df_clean.sort_values(by='RT (min)')
    
    return df_header, df_clean

# --- FILE UPLOADS ---
col1, col2 = st.columns(2)
with col1:
    sample_file = st.file_uploader("Upload SAMPLE File", type=['xlsx'])
with col2:
    blank_file = st.file_uploader("Upload BLANK File (Solvent)", type=['xlsx'])

if sample_file and blank_file:
    try:
        # Run Procedure
        sample_header, df_sample = run_analytical_procedure(sample_file)
        blank_header, df_blank = run_analytical_procedure(blank_file)

        # --- BLANK SUBTRACTION LOGIC ---
        blank_map = dict(zip(df_blank['Hit Name'], df_blank['Area (Ab*s)']))
        df_sample['Subtracted?'] = df_sample['Hit Name'].apply(lambda x: "YES" if x in blank_map else "NO")

        # Compute Final Subtracted Data
        df_final = df_sample.copy()
        df_final['Area (Ab*s)'] = df_final.apply(lambda r: max(0, r['Area (Ab*s)'] - blank_map.get(r['Hit Name'], 0)), axis=1)
        df_final = df_final[df_final['Area (Ab*s)'] > 0]
        
        # Add Remark to Header 0 (Metadata Tracking)
        final_header = sample_header.copy()
        final_header.iloc[0,0] = f"{final_header.iloc[0,0]} (CORRECTED: BLANK SUBTRACTED)"

        # --- UI DISPLAY ---
        st.success("Analytical Process Complete.")
        t1, t2, t3 = st.tabs(["1. Solvent Blank Data", "2. Raw Sample (Pre-Subtraction)", "3. Corrected Final Profile"])
        
        with t1: 
            st.write("Cleaned data detected in Solvent Blank")
            st.dataframe(df_blank)
        with t2: 
            st.info("Note: Yellow-highlighted rows are compounds identified in the blank.")
            st.dataframe(df_sample.style.apply(lambda x: ['background: #FFFFE0' if x['Subtracted?'] == 'YES' else '' for _ in x], axis=1))
        with t3: 
            st.write("Final Profile after Blank Subtraction and Filtering")
            st.dataframe(df_final)

        # --- PROFESSIONAL EXCEL EXPORT ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            sheet = 'Analytical_Report'
            # Table 1: Blank
            blank_header.to_excel(writer, sheet_name=sheet, startrow=1, index=False, header=False)
            df_blank.to_excel(writer, sheet_name=sheet, startrow=10, index=False)
            
            # Table 2: Raw Sample
            s2 = len(df_blank) + 15
            sample_header.to_excel(writer, sheet_name=sheet, startrow=s2+1, index=False, header=False)
            df_sample.to_excel(writer, sheet_name=sheet, startrow=s2+10, index=False)
            
            # Table 3: Final Corrected
            s3 = s2 + len(df_sample) + 15
            final_header.to_excel(writer, sheet_name=sheet, startrow=s3+1, index=False, header=False)
            df_final.to_excel(writer, sheet_name=sheet, startrow=s3+10, index=False)

            # Excel Styling
            wb, ws = writer.book, writer.sheets[sheet]
            title_fmt = wb.add_format({'bold': True, 'font_size': 14, 'bg_color': '#D3D3D3', 'border': 1})
            red_fmt = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            yellow_fmt = wb.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})

            ws.write(0, 0, "TABLE 1: CLEANED SOLVENT BLANK DATA", title_fmt)
            ws.write(s2, 0, "TABLE 2: RAW SAMPLE DATA (SUBTRACTION MAPPING)", title_fmt)
            ws.write(s3, 0, "TABLE 3: CORRECTED FINAL LIPID PROFILE", title_fmt)

            # Conditional Formatting for Review and Subtraction
            ws.conditional_format(0, 0, 5000, 30, {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': red_fmt})
            ws.conditional_format(0, 0, 5000, 30, {'type': 'cell', 'criteria': 'equal to', 'value': '"YES"', 'format': yellow_fmt})

        st.download_button("📥 Download Analytical Report", output.getvalue(), "LipidExpert_Analytical_Report.xlsx")

    except Exception as e:
        st.error(f"Execution Error: {e}")
