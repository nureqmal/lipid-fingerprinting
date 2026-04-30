import streamlit as st
import pandas as pd
import io

# Setup Page
st.set_page_config(page_title="GCMS Lipid Fingerprint Pro", layout="wide")
st.title("🧪 GCMS Lipid Fingerprinting Automator")
st.markdown("""
### Data Integrity & Automation Module (Blank Subtraction Version)
This application automates the cleaning and blank subtraction process:
1. **Quality Control**: Both Sample and Blank must meet a minimum NIST Match Factor of 80.
2. **Expert Labeling**: Categorizes *Artifacts*, *Halogens*, and *Petroleum Contaminants*.
3. **Blank Subtraction**: Subtracts Blank Area from Sample Area for identical compounds.
4. **Triple Validation**: Provides data for Blank, Raw Sample, and Final Subtracted Result.
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

    # STEP 4: FILTER OUT DISCARDED ARTIFACTS
    df_clean = df_clean[df_clean['Chemical_Status'] != "Discard (Artifact/Bleed)"]

    # STEP 5: DEDUPLICATION (Peak Picking - Max Area)
    df_clean = df_clean.sort_values(by='Area (Ab*s)', ascending=False)
    df_clean = df_clean.drop_duplicates(subset=['Hit Name'], keep='first')

    # STEP 6: SORT BY RETENTION TIME
    df_clean = df_clean.sort_values(by='RT (min)')
    
    return df_header, df_clean

# --- UPLOAD FILES ---
col1, col2 = st.columns(2)
with col1:
    sample_file = st.file_uploader("Upload your SAMPLE MSRep.xlsx", type=['xlsx'])
with col2:
    blank_file = st.file_uploader("Upload your BLANK MSRep.xlsx", type=['xlsx'])

if sample_file and blank_file:
    try:
        # Run original procedure on BOTH files
        sample_header, df_sample = original_cleaning_procedure(sample_file)
        _, df_blank = original_cleaning_procedure(blank_file)

        # --- BLANK SUBTRACTION LOGIC ---
        blank_map = dict(zip(df_blank['Hit Name'], df_blank['Area (Ab*s)']))
        
        df_final = df_sample.copy()
        df_final['Original_Area'] = df_final['Area (Ab*s)']
        
        def do_subtraction(row):
            b_area = blank_map.get(row['Hit Name'], 0)
            diff = row['Area (Ab*s)'] - b_area
            return diff if diff > 0 else 0

        df_final['Area (Ab*s)'] = df_final.apply(do_subtraction, axis=1)
        df_final = df_final[df_final['Area (Ab*s)'] > 0] # Remove if area becomes 0

        # --- DISPLAY RESULTS IN TABS ---
        st.success(f"Success! Processed Sample and Blank according to your PhD procedure.")
        
        tab1, tab2, tab3 = st.tabs(["1. Solvent Blank (Cleaned)", "2. Raw Sample (Cleaned)", "3. Final Subtracted Result"])
        
        with tab1:
            st.dataframe(df_blank[['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Quality', 'Chemical_Status']])
        with tab2:
            st.dataframe(df_sample[['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Quality', 'Chemical_Status']])
        with tab3:
            st.dataframe(df_final[['Hit Name', 'RT (min)', 'Original_Area', 'Area (Ab*s)', 'Quality', 'Chemical_Status']])

        # --- DOWNLOAD PROCESS WITH COLOR FORMATTING ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Create the Triple-Validation Report in one sheet
            sheet_name = 'Fingerprint_Data'
            bold_fmt = writer.book.add_format({'bold': True, 'font_size': 12})
            red_fmt = writer.book.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})

            # Table 1: Blank
            pd.DataFrame([["TABLE 1: CLEANED SOLVENT BLANK DATA"]]).to_excel(writer, index=False, header=False, sheet_name=sheet_name, startrow=0)
            df_blank.to_excel(writer, index=False, sheet_name=sheet_name, startrow=1)

            # Table 2: Raw Sample
            start_row_2 = len(df_blank) + 4
            pd.DataFrame([["TABLE 2: CLEANED RAW SAMPLE DATA"]]).to_excel(writer, index=False, header=False, sheet_name=sheet_name, startrow=start_row_2)
            df_sample.to_excel(writer, index=False, sheet_name=sheet_name, startrow=start_row_2 + 1)

            # Table 3: Final Subtracted Result
            start_row_3 = start_row_2 + len(df_sample) + 4
            pd.DataFrame([["TABLE 3: FINAL SUBTRACTED LIPID PROFILE"]]).to_excel(writer, index=False, header=False, sheet_name=sheet_name, startrow=start_row_3)
            sample_header.to_excel(writer, index=False, header=False, sheet_name=sheet_name, startrow=start_row_3 + 1)
            df_final.to_excel(writer, index=False, sheet_name=sheet_name, startrow=start_row_3 + 10)

            # Applying Formats
            worksheet = writer.sheets[sheet_name]
            worksheet.write(0, 0, "TABLE 1: CLEANED SOLVENT BLANK DATA", bold_fmt)
            worksheet.write(start_row_2, 0, "TABLE 2: CLEANED RAW SAMPLE DATA", bold_fmt)
            worksheet.write(start_row_3, 0, "TABLE 3: FINAL SUBTRACTED LIPID PROFILE", bold_fmt)
            
            # Highlight 'Review' status in Red (Last column)
            status_col_idx = len(df_final.columns) - 1
            worksheet.conditional_format(0, status_col_idx, 1000, status_col_idx,
                                         {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': red_fmt})

        st.download_button(
            label="📥 Download Professional Triple-Validation Report",
            data=output.getvalue(),
            file_name="GCMS_Lipid_Final_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Technical Error: {e}")
