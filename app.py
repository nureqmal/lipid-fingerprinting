import streamlit as st
import pandas as pd
import io

# Setup Page
st.set_page_config(page_title="GCMS Lipid Fingerprint Pro", layout="wide")
st.title("🧪 GCMS Lipidomics: Final Validation Module")
st.markdown("""
### PhD Standard Data Cleaning & Subtraction
- **Full Traceability**: Row 0 (Data file name) until Row 8 are strictly preserved.
- **Subtraction Mapping**: Compounds found in the blank are highlighted in the Raw Sample table.
- **Red/Yellow Formatting**: Review status (Red) and Subtracted status (Yellow) are color-coded in Excel.
""")

def original_cleaning_procedure(file):
    # 1. PRESERVE ORIGINAL HEADER (Rows 0-8) - Strictly from the very top
    # Use header=None to ensure we don't miss the first row
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    df_header = df_full_raw.iloc[0:9, :].copy() # Take rows 0 to 8
    
    # 2. READ MAIN DATA (Starting from row 9)
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip() 

    # STEP 1: Basic Cleaning
    df_clean = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df_clean['Quality'] = pd.to_numeric(df_clean['Quality'], errors='coerce')
    df_clean = df_clean[df_clean['Quality'] >= 80]

    # STEP 2: Expert Classification
    blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
    contaminants = ['iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene', 'benzothiophene', 'naphthalene', 'benzene,']

    def classify_compound(name):
        name_lower = str(name).lower()
        if any(x in name_lower for x in blacklist): return "Discard (Artifact/Bleed)"
        if any(x in name_lower for x in contaminants): return "Review (Potential Contaminant)"
        return "Clean (Lipid/Oxidation Product)"

    df_clean['Chemical_Status'] = df_clean['Hit Name'].apply(classify_compound)
    df_clean = df_clean[df_clean['Chemical_Status'] != "Discard (Artifact/Bleed)"]

    # STEP 3: Deduplication
    df_clean = df_clean.sort_values(by='Area (Ab*s)', ascending=False)
    df_clean = df_clean.drop_duplicates(subset=['Hit Name'], keep='first')
    df_clean = df_clean.sort_values(by='RT (min)')
    
    return df_header, df_clean

# --- UPLOAD FILES ---
col1, col2 = st.columns(2)
with col1:
    sample_file = st.file_uploader("Upload SAMPLE MSRep.xlsx", type=['xlsx'])
with col2:
    blank_file = st.file_uploader("Upload BLANK MSRep.xlsx", type=['xlsx'])

if sample_file and blank_file:
    try:
        sample_header, df_sample = original_cleaning_procedure(sample_file)
        blank_header, df_blank = original_cleaning_procedure(blank_file)

        # --- SUBTRACTION MAPPING ---
        blank_map = dict(zip(df_blank['Hit Name'], df_blank['Area (Ab*s)']))
        df_sample['Is_In_Blank?'] = df_sample['Hit Name'].apply(lambda x: "YES" if x in blank_map else "NO")

        # Create Final Subtracted Data
        df_final = df_sample.copy()
        df_final['Area (Ab*s)'] = df_final.apply(lambda r: max(0, r['Area (Ab*s)'] - blank_map.get(r['Hit Name'], 0)), axis=1)
        df_final = df_final[df_final['Area (Ab*s)'] > 0]
        
        # Add Remark to Final Header
        final_header = sample_header.copy()
        final_header.iloc[0,0] = str(final_header.iloc[0,0]) + " (BLANK SUBTRACTED)"

        # --- UI TABS ---
        t1, t2, t3 = st.tabs(["1. Cleaned Blank", "2. Sample (Raw Cleaned)", "3. Final Result"])
        with t1: st.dataframe(df_blank)
        with t2: st.dataframe(df_sample.style.apply(lambda x: ['background: #FFFFE0' if x['Is_In_Blank?'] == 'YES' else '' for _ in x], axis=1))
        with t3: st.dataframe(df_final)

        # --- EXCEL EXPORT ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            sheet = 'Fingerprint_Report'
            # Table 1: Blank
            blank_header.to_excel(writer, sheet_name=sheet, startrow=1, index=False, header=False)
            df_blank.to_excel(writer, sheet_name=sheet, startrow=10, index=False)
            
            # Table 2: Sample
            s2 = len(df_blank) + 15
            sample_header.to_excel(writer, sheet_name=sheet, startrow=s2+1, index=False, header=False)
            df_sample.to_excel(writer, sheet_name=sheet, startrow=s2+10, index=False)
            
            # Table 3: Final
            s3 = s2 + len(df_sample) + 15
            final_header.to_excel(writer, sheet_name=sheet, startrow=s3+1, index=False, header=False)
            df_final.to_excel(writer, sheet_name=sheet, startrow=s3+10, index=False)

            # Labels & Formats
            wb, ws = writer.book, writer.sheets[sheet]
            bold = wb.add_format({'bold': True, 'font_size': 14, 'bg_color': '#D3D3D3'})
            red = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            yellow = wb.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})

            ws.write(0, 0, "TABLE 1: CLEANED SOLVENT BLANK DATA", bold)
            ws.write(s2, 0, "TABLE 2: CLEANED RAW SAMPLE DATA (SUBTRACTION TRACKER)", bold)
            ws.write(s3, 0, "TABLE 3: FINAL SUBTRACTED LIPID PROFILE", bold)

            # Apply conditional colors
            ws.conditional_format(0, 0, 5000, 30, {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': red})
            ws.conditional_format(0, 0, 5000, 30, {'type': 'cell', 'criteria': 'equal to', 'value': '"YES"', 'format': yellow})

        st.download_button("📥 Download PhD Validation Report", output.getvalue(), "GCMS_Final_Triple_Report.xlsx")

    except Exception as e:
        st.error(f"Error: {e}")
