import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="GCMS Pro: Blank Subtractor", layout="wide")
st.title("🧪 GCMS Lipidomics: Blank Subtraction Module")

st.markdown("""
### Analytical Workflow:
1. Upload your **Sample** file and your **Blank** file (n-Hexane/EtOAc).
2. The system will subtract the Area of common compounds found in the Blank from the Sample.
3. Quality filtering and artifact labeling will still be applied.
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
    df = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df['Quality'] = pd.to_numeric(df['Quality'], errors='coerce')
    df['Area (Ab*s)'] = pd.to_numeric(df['Area (Ab*s)'], errors='coerce')
    # Deduplicate early
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'])
    return header, df

if sample_file and blank_file:
    try:
        sample_header, sample_df = process_gcms(sample_file)
        _, blank_df = process_gcms(blank_file)

        # --- BLANK SUBTRACTION LOGIC ---
        st.info("Performing Blank Subtraction...")
        
        # Create a dictionary of blank areas for mapping { 'Compound Name': Area }
        blank_map = dict(zip(blank_df['Hit Name'], blank_df['Area (Ab*s)']))

        def subtract_area(row):
            compound = row['Hit Name']
            sample_area = row['Area (Ab*s)']
            blank_area = blank_map.get(compound, 0) # Default 0 if not in blank
            
            final_area = sample_area - blank_area
            return final_area if final_area > 0 else 0

        sample_df['Original_Area'] = sample_df['Area (Ab*s)']
        sample_df['Area (Ab*s)'] = sample_df.apply(subtract_area, axis=1)

        # Remove compounds that were reduced to 0 (fully present in blank)
        sample_df = sample_df[sample_df['Area (Ab*s)'] > 0]

        # --- REMAINING FILTERS ---
        sample_df = sample_df[sample_df['Quality'] >= 80]

        # Classification
        blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate']
        contaminants = ['iodo', 'chloro', 'bromo', 'fluoro', 'thiophene', 'benzothiophene', 'naphthalene', 'benzene,']

        def classify(name):
            name_l = str(name).lower()
            if any(x in name_l for x in blacklist): return "Discard (Artifact)"
            if any(x in name_l for x in contaminants): return "Review (Contaminant)"
            return "Clean (Lipid)"

        sample_df['Chemical_Status'] = sample_df['Hit Name'].apply(classify)
        sample_df = sample_df[sample_df['Chemical_Status'] != "Discard (Artifact)"]
        sample_df = sample_df.sort_values(by='RT (min)')

        # --- RESULTS ---
        st.success(f"Subtraction Complete. {len(sample_df)} unique compounds remaining.")
        st.dataframe(sample_df[['Hit Name', 'RT (min)', 'Original_Area', 'Area (Ab*s)', 'Chemical_Status']])

        # --- DOWNLOAD ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            sample_header.to_excel(writer, index=False, header=False, sheet_name='Clean_Data')
            sample_df.to_excel(writer, index=False, startrow=9, sheet_name='Clean_Data')
            
            workbook = writer.book
            worksheet = writer.sheets['Clean_Data']
            red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            status_col_idx = len(sample_df.columns) - 1
            worksheet.conditional_format(10, status_col_idx, 500, status_col_idx,
                                         {'type': 'cell', 'criteria': 'equal to', 
                                          'value': '"Review (Contaminant)"', 'format': red_format})

        st.download_button("📥 Download Adjusted Report", output.getvalue(), "GCMS_Blank_Subtracted.xlsx")

    except Exception as e:
        st.error(f"Error: {e}")
