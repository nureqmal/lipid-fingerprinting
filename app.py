import streamlit as st
import pandas as pd
import io

# Setup Page
st.set_page_config(page_title="GCMS Lipid Fingerprint Pro", layout="wide")
st.title("🧪 GCMS Lipidomics: Final Validation Module")
st.markdown("""
### PhD Standard Data Cleaning & Subtraction
1. **Full Metadata**: Each table retains its original NIST header for traceability.
2. **Subtraction Mapping**: Compounds found in the blank are highlighted in the Raw Sample table.
3. **Chemical Integrity**: Artifacts and Halogens are labeled and color-coded.
""")

# --- HELPER FUNCTION: THE ORIGINAL PROCEDURE ---
def original_cleaning_procedure(file):
    # 1. PRESERVE ORIGINAL HEADER (Rows 1-8)
    df_header = pd.read_excel(file, sheet_name='LibRes', header=None, nrows=8)
    
    # 2. READ MAIN DATA (Starting from row 9)
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip() 

    # STEP 1: Remove rows without physical data (RT/Area)
    df_clean = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()

    # STEP 2: Filter Quality >= 80
    df_clean['Quality'] = pd.to_numeric(df_clean['Quality'], errors='coerce')
    df_clean = df_clean[df_clean['Quality'] >= 80]

    # STEP 3: EXPERT CLASSIFICATION LOGIC
    blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
    contaminants = ['iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene', 'benzothiophene', 'naphthalene', 'benzene,']

    def classify_compound(name):
        name_lower = str(name).lower()
        if any(x in name_lower for x in blacklist):
            return "Discard (Artifact/Bleed)"
        if any(x in name_lower for x in contaminants):
            return "Review (Potential Contaminant)"
        return "Clean (Lipid/Oxidation Product)"

    df_clean['Chemical_Status'] = df_clean['Hit Name'].apply(classify_compound)
    df_clean = df_clean[df_clean['Chemical_Status'] != "Discard (Artifact/Bleed)"]

    # STEP 4: DEDUPLICATION (Peak Picking - Max Area)
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
        # Run original procedure on BOTH files
        sample_header, df_sample = original_cleaning_procedure(sample_file)
        blank_header, df_blank = original_cleaning_procedure(blank_file)

        # --- SUBTRACTION MAPPING ---
        blank_compounds = df_blank['Hit Name'].unique()
        blank_map = dict(zip(df_blank['Hit Name'], df_blank['Area (Ab*s)']))
        
        # Mark Raw Sample: Which one will be subtracted?
        df_sample['Is_In_Blank?'] = df_sample['Hit Name'].apply(lambda x: "YES" if x in blank_compounds else "NO")

        # Create Final Subtracted Data
        df_final = df_sample.copy()
        def do_subtraction(row):
            b_area = blank_map.get(row['Hit Name'], 0)
            diff = row['Area (Ab*s)'] - b_area
            return diff if diff > 0 else 0

        df_final['Area (Ab*s)'] = df_final.apply(do_subtraction, axis=1)
        df_final = df_final[df_final['Area (Ab*s)'] > 0]
        
        # Add Remark to Final Header
        final_header = sample_header.copy()
        final_header.iloc[0,0] = str(final_header.iloc[0,0]) + " (BLANK SUBTRACTED)"

        # --- UI DISPLAY ---
        st.success("Processing Complete!")
        tab1, tab2, tab3 = st.tabs(["1. Cleaned Blank", "2. Sample (Highlighting Subtractions)", "3. Final Subtracted Result"])
        
        with tab1:
            st.dataframe(df_blank)
        with tab2:
            st.info("Yellow rows (if any) indicate compounds also found in the blank.")
            st.dataframe(df_sample.style.apply(lambda x: ['background: #FFFFE0' if x['Is_In_Blank?'] == 'YES' else '' for _ in x], axis=1))
        with tab3:
            st.dataframe(df_final)

        # --- EXCEL EXPORT ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            sheet = 'Validation_Report'
            df_blank.to_excel(writer, sheet_name=sheet, startrow=9, index=False)
            blank_header.to_excel(writer, sheet_name=sheet, startrow=0, index=False, header=False)
            
            start_row_sample = len(df_blank) + 12
            df_sample.to_excel(writer, sheet_name=sheet, startrow=start_row_sample + 9, index=False)
            sample_header.to_excel(writer, sheet_name=sheet, startrow=start_row_sample, index=False, header=False)
            
            start_row_final = start_row_sample + len(df_sample) + 12
            df_final.to_excel(writer, sheet_name=sheet, startrow=start_row_final + 9, index=False)
            final_header.to_excel(writer, sheet_name=sheet, startrow=start_row_final, index=False, header=False)

            # Formats
            workbook = writer.book
            worksheet = writer.sheets[sheet]
            bold = workbook.add_format({'bold': True, 'font_size': 14})
            red_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            yellow_fmt = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})

            # Labels
            worksheet.write(0, 0, "TABLE 1: CLEANED BLANT DATA", bold)
            worksheet.write(start_row_sample, 0, "TABLE 2: RAW SAMPLE (BEFORE SUBTRACTION)", bold)
            worksheet.write(start_row_final, 0, "TABLE 3: FINAL LIPID PROFILE (SUBTRACTED)", bold)

            # Formatting Review Status
            status_idx = len(df_final.columns) - 1 # Chemical_Status usually last or near last
            worksheet.conditional_format(0, 0, 2000, 20, {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': red_fmt})
            worksheet.conditional_format(0, 0, 2000, 20, {'type': 'cell', 'criteria': 'equal to', 'value': '"YES"', 'format': yellow_fmt})

        st.download_button("📥 Download Final Triple-Validation Report", output.getvalue(), "GCMS_PhD_Final_Report.xlsx")

    except Exception as e:
        st.error(f"Error: {e}")
