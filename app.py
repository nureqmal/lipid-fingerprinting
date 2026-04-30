import streamlit as st
import pandas as pd
import io

# Setup Page
st.set_page_config(page_title="GCMS Lipidomics Pro", layout="wide")
st.title("🧪 GCMS Lipidomics: Triple-Validation Module")

st.markdown("""
### Analytical Workflow:
This module performs blank subtraction and provides three separate tables for full transparency:
1. **Solvent Blank Data**: Compounds detected in the solvent.
2. **Raw Sample Data**: Initial compounds detected in the sample (Cleaned from artifacts).
3. **Final Subtracted Data**: The "True" lipid profile after blank subtraction.
""")

# --- FILE UPLOADS ---
col_a, col_b = st.columns(2)
with col_a:
    sample_file = st.file_uploader("Upload SAMPLE File (MSRep.xlsx)", type=['xlsx'])
with col_b:
    blank_file = st.file_uploader("Upload BLANK File (MSRep.xlsx)", type=['xlsx'])

def process_gcms(file):
    # Read header and data
    header = pd.read_excel(file, sheet_name='LibRes', header=None, nrows=8)
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip()
    
    # Cleaning basics
    df = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df['Quality'] = pd.to_numeric(df['Quality'], errors='coerce')
    df['Area (Ab*s)'] = pd.to_numeric(df['Area (Ab*s)'], errors='coerce')
    
    # Deduplicate: Keep highest area for each compound
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'])
    
    # Artifact Filtering
    blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'naphthalene', 'benzene,']
    halogens = ['iodo', 'chloro', 'bromo', 'fluoro', 'thiophene', 'benzothiophene']
    
    def classify(name):
        name_l = str(name).lower()
        if any(x in name_l for x in blacklist): return "Discard (Artifact)"
        if any(x in name_l for x in halogens): return "Review (Contaminant)"
        return "Clean (Lipid)"

    df['Chemical_Status'] = df['Hit Name'].apply(classify)
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    
    return header, df

if sample_file and blank_file:
    try:
        sample_header, sample_df_raw = process_gcms(sample_file)
        _, blank_df = process_gcms(blank_file)

        # 1. PREPARE BLANK TABLE (For display)
        blank_display = blank_df[['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Quality']].sort_values('RT (min)')

        # 2. PREPARE RAW SAMPLE TABLE (Filtered but not subtracted)
        sample_raw_display = sample_df_raw[['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Quality', 'Chemical_Status']].sort_values('RT (min)')

        # 3. BLANK SUBTRACTION LOGIC
        blank_map = dict(zip(blank_df['Hit Name'], blank_df['Area (Ab*s)']))

        sample_subtracted = sample_df_raw.copy()
        
        def subtract_logic(row):
            b_area = blank_map.get(row['Hit Name'], 0)
            res = row['Area (Ab*s)'] - b_area
            return res if res > 0 else 0

        sample_subtracted['Area (Ab*s)'] = sample_subtracted.apply(subtract_logic, axis=1)
        # Only keep rows with area > 0 after subtraction
        sample_subtracted = sample_subtracted[sample_subtracted['Area (Ab*s)'] > 0]
        sample_subtracted = sample_subtracted.sort_values('RT (min)')

        # --- UI DISPLAY ---
        st.success("Analysis Complete!")
        
        tab1, tab2, tab3 = st.tabs(["1. Solvent Blank", "2. Raw Sample", "3. Final Subtracted Result"])
        
        with tab1:
            st.write("### Compounds detected in Blank")
            st.dataframe(blank_display)
            
        with tab2:
            st.write("### Raw Compounds detected in Sample (Filtered)")
            st.dataframe(sample_raw_display)
            
        with tab3:
            st.write("### Final Corrected Lipid Profile")
            st.dataframe(sample_subtracted[['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Quality', 'Chemical_Status']])

        # --- EXCEL EXPORT (The "Pro" Look) ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Table 1: Blank
            st.write("") # Spacer
            pd.DataFrame([["TABLE 1: SOLVENT BLANK DATA"]]).to_excel(writer, index=False, header=False, sheet_name='Triple_Validation', startrow=0)
            blank_display.to_excel(writer, index=False, sheet_name='Triple_Validation', startrow=1)

            # Table 2: Raw Sample
            start_row_2 = len(blank_display) + 4
            pd.DataFrame([["TABLE 2: RAW SAMPLE DATA (BEFORE SUBTRACTION)"]]).to_excel(writer, index=False, header=False, sheet_name='Triple_Validation', startrow=start_row_2)
            sample_raw_display.to_excel(writer, index=False, sheet_name='Triple_Validation', startrow=start_row_2 + 1)

            # Table 3: Final Subtracted (With Sample Header info)
            start_row_3 = start_row_2 + len(sample_raw_display) + 4
            pd.DataFrame([["TABLE 3: FINAL SUBTRACTED LIPID PROFILE"]]).to_excel(writer, index=False, header=False, sheet_name='Triple_Validation', startrow=start_row_3)
            # Put original header info above the final table
            sample_header.to_excel(writer, index=False, header=False, sheet_name='Triple_Validation', startrow=start_row_3 + 1)
            sample_subtracted.to_excel(writer, index=False, sheet_name='Triple_Validation', startrow=start_row_3 + 10)
            
            # Formatting
            workbook = writer.book
            worksheet = writer.sheets['Triple_Validation']
            red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            bold_format = workbook.add_format({'bold': True, 'font_size': 12})
            
            # Title formatting
            worksheet.write(0, 0, "TABLE 1: SOLVENT BLANK DATA", bold_format)
            worksheet.write(start_row_2, 0, "TABLE 2: RAW SAMPLE DATA (BEFORE SUBTRACTION)", bold_format)
            worksheet.write(start_row_3, 0, "TABLE 3: FINAL SUBTRACTED LIPID PROFILE", bold_format)

        st.download_button("📥 Download Triple-Validation Report", output.getvalue(), "GCMS_Final_Validation_Report.xlsx")

    except Exception as e:
        st.error(f"Error: {e}")
