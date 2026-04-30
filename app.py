import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Strict Authentication Suite", layout="wide")
st.title("🧪 LipidExpert: Strict Authentication Suite")
st.markdown("""
---
### System Overview: Strict Exclusion Mode
This suite is configured for **Halal Authentication** standards. To eliminate the risk of false biomarkers, any compound detected in the Solvent Blank will be **entirely excluded** from the sample profile.

### Operational Procedure:
1.  **Metadata Acquisition**: Preservation of original NIST headers (Rows 1–9) for traceability.
2.  **Quality Thresholding**: Minimum NIST Match Factor of **80**.
3.  **Expert Classification**: Artifacts and petroleum-based contaminants are discarded or flagged.
4.  **Peak Deduplication**: Selection of the **Maximum Area** for unique chemical entities.
5.  **Strict Blank Exclusion**: 
    *   Any compound present in the Solvent Blank is deemed "Non-Unique."
    *   These compounds are **completely removed** from the final profile to ensure biomarker integrity.
6.  **Comparative Reporting**: Triple-table validation for Blank, Raw, and Unique-only results.
---
""")

def run_strict_procedure(file):
    # 1. READ FULL DATA
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    
    # 2. EXTRACT HEADER (Rows 0-8)
    df_header = df_full_raw.iloc[0:9, :].copy()
    
    # 3. READ MAIN DATASET (Header at Row 9)
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip() 

    # STEP 1: Basic Cleaning & Quality Filter
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
        # Process Sample and Blank with same strict filters
        sample_header, df_sample = run_strict_procedure(sample_file)
        _, df_blank = run_strict_procedure(blank_file)

        # --- STRICT EXCLUSION LOGIC ---
        blank_compounds = set(df_blank['Hit Name'].unique())
        
        # Mark in Raw Sample
        df_sample['In_Blank?'] = df_sample['Hit Name'].apply(lambda x: "YES" if x in blank_compounds else "NO")

        # Create Final Profile (Keep only compounds NOT in blank)
        df_final = df_sample[df_sample['In_Blank?'] == "NO"].copy()
        
        # Metadata Update
        final_header = sample_header.copy()
        final_header.iloc[0,0] = f"{final_header.iloc[0,0]} (STRICT EXCLUSION: UNIQUE ONLY)"

        # --- UI DISPLAY ---
        st.success("Strict Authentication Analysis Complete.")
        t1, t2, t3 = st.tabs(["1. Solvent Blank Data", "2. Sample Mapping", "3. Final Unique Biomarkers"])
        
        with t1: 
            st.write("Compounds detected in Blank (These will be excluded from Sample)")
            st.dataframe(df_blank)
        with t2: 
            st.info("Yellow rows indicate compounds detected in the blank and will be discarded from the final profile.")
            st.dataframe(df_sample.style.apply(lambda x: ['background: #FFFFE0' if x['In_Blank?'] == 'YES' else '' for _ in x], axis=1))
        with t3: 
            st.write(f"Final Profile: {len(df_final)} Unique Compounds Remaining")
            st.dataframe(df_final.drop(columns=['In_Blank?']))

        # --- PROFESSIONAL EXCEL EXPORT ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            sheet = 'Authentication_Report'
            # Table 1: Blank
            df_blank.to_excel(writer, sheet_name=sheet, startrow=10, index=False)
            
            # Table 2: Sample Raw
            s2 = len(df_blank) + 15
            df_sample.to_excel(writer, sheet_name=sheet, startrow=s2+10, index=False)
            
            # Table 3: Final Unique
            s3 = s2 + len(df_sample) + 15
            final_header.to_excel(writer, sheet_name=sheet, startrow=s3+1, index=False, header=False)
            df_final.drop(columns=['In_Blank?']).to_excel(writer, sheet_name=sheet, startrow=s3+10, index=False)

            # Excel Styling
            wb, ws = writer.book, writer.sheets[sheet]
            title_fmt = wb.add_format({'bold': True, 'font_size': 14, 'bg_color': '#D3D3D3', 'border': 1})
            red_fmt = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            yellow_fmt = wb.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})

            ws.write(0, 0, "TABLE 1: CLEANED SOLVENT BLANK DATA", title_fmt)
            ws.write(s2, 0, "TABLE 2: RAW SAMPLE (EXCLUSION MAPPING)", title_fmt)
            ws.write(s3, 0, "TABLE 3: UNIQUE LIPID FINGERPRINT (FINAL)", title_fmt)

            ws.conditional_format(0, 0, 5000, 30, {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': red_fmt})
            ws.conditional_format(0, 0, 5000, 30, {'type': 'cell', 'criteria': 'equal to', 'value': '"YES"', 'format': yellow_fmt})

        st.download_button("📥 Download Strict Authentication Report", output.getvalue(), "LipidExpert_Unique_Fingerprint.xlsx")

    except Exception as e:
        st.error(f"Execution Error: {e}")
