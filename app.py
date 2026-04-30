import streamlit as st
import pandas as pd
import io

# Setup Page
st.set_page_config(page_title="GCMS Lipid Fingerprint Pro", layout="wide")
st.title("🧪 GCMS Lipid Fingerprinting Automator")
st.markdown("""
### Data Integrity & Automation Module
This application automates the cleaning process for GC-MS lipidomic data:
1. **Header Preservation**: Retains original file metadata (Sample Name, Method, etc.).
2. **Quality Control**: Filters for a minimum NIST Match Factor of 80.
3. **Advanced Chemical Labeling**: Categorizes *Instrument Artifacts*, *Halogens*, and *Petroleum Contaminants*.
4. **Peak Deduplication**: Selects the peak with the **Maximum Area** for each unique compound.
""")

# --- UPLOAD FILE ---
uploaded_file = st.file_uploader("Upload your MSRep.xlsx file", type=['xlsx'])

if uploaded_file:
    try:
        # 1. PRESERVE ORIGINAL HEADER (Rows 1-8)
        df_header = pd.read_excel(uploaded_file, sheet_name='LibRes', header=None, nrows=8)
        
        # 2. READ MAIN DATA (Starting from row 9)
        df = pd.read_excel(uploaded_file, sheet_name='LibRes', header=8)
        df.columns = df.columns.str.strip() 

        # --- CLEANING PROCESS ---

        # STEP 1: Remove rows without physical data (RT/Area)
        df_clean = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()

        # STEP 2: Filter Quality >= 80
        df_clean['Quality'] = pd.to_numeric(df_clean['Quality'], errors='coerce')
        df_clean = df_clean[df_clean['Quality'] >= 80]

        # STEP 3: EXPERT CLASSIFICATION LOGIC
        blacklist = [
            'siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 
            'plasticizer', 'adipate', 'column bleed'
        ]
        
        contaminants = [
            'iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 
            'thiophene', 'benzothiophene', 
            'naphthalene', 'benzene,' 
        ]

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

        # STEP 5: DEDUPLICATION (Peak Picking)
        df_clean = df_clean.sort_values(by='Area (Ab*s)', ascending=False)
        df_clean = df_clean.drop_duplicates(subset=['Hit Name'], keep='first')

        # STEP 6: SORT BY RETENTION TIME
        df_clean = df_clean.sort_values(by='RT (min)')

        # --- DISPLAY RESULTS ---
        st.success(f"Success! Found {len(df_clean)} unique compounds.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("### Compound Status Summary:")
            st.write(df_clean['Chemical_Status'].value_counts())
        
        with col2:
            st.info("The 'Review' status indicates compounds that may be non-natural biomarkers or contaminants. Inspect these before finalizing your PCA model.")

        st.write("### Cleaned Data Preview")
        st.dataframe(df_clean)

        # --- DOWNLOAD PROCESS WITH COLOR FORMATTING ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write Header
            df_header.to_excel(writer, index=False, header=False, sheet_name='Fingerprint_Data')
            
            # Write Main Data
            df_clean.to_excel(writer, index=False, startrow=9, sheet_name='Fingerprint_Data')
            
            # Get xlsxwriter objects for formatting
            workbook  = writer.book
            worksheet = writer.sheets['Fingerprint_Data']
            
            # Define the red format for 'Review' cells
            red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            
            # Apply conditional formatting to the 'Chemical_Status' column
            # We assume Chemical_Status is the last column. Let's calculate its index.
            status_col_idx = len(df_clean.columns) - 1
            
            # Apply formatting from row 11 (index 10) to the end of data
            worksheet.conditional_format(10, status_col_idx, 10 + len(df_clean), status_col_idx,
                                         {'type':     'cell',
                                          'criteria': 'equal to',
                                          'value':    '"Review (Potential Contaminant)"',
                                          'format':   red_format})
        
        st.download_button(
            label="📥 Download Professional Lipid Report",
            data=output.getvalue(),
            file_name="GCMS_Lipid_Analysis_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Technical Error: {e}")