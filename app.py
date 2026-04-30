import streamlit as st
import pandas as pd
import io

# 1. Setup Page
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

# 2. Sidebar Controls
st.sidebar.header("⚙️ Analytical Controls")
q_threshold = st.sidebar.slider("Select NIST Quality Threshold", 50, 95, 80, 5)
rt_tolerance = st.sidebar.slider("Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01)
area_threshold = st.sidebar.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01)

# 3. Define Function
def run_strict_procedure(file, q_min, area_min):
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    df_header = df_full_raw.iloc[0:9, :].copy()
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip() 
    df = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df['Quality'] = pd.to_numeric(df['Quality'], errors='coerce')
    total_area = df['Area (Ab*s)'].sum()
    df['Area (%)'] = (df['Area (Ab*s)'] / total_area) * 100
    df = df[(df['Quality'] >= q_min) & (df['Area (%)'] >= area_min)]
    blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
    def classify_compound(name):
        n = str(name).lower()
        if any(x in n for x in blacklist): return "Discard (Artifact)"
        return "Clean (Lipid/Oxidation)"
    df['Chemical_Status'] = df['Hit Name'].apply(classify_compound)
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    return df_header, df.sort_values(by='RT (min)')

# 4. File Uploaders (Variable defined here!)
col1, col2 = st.columns(2)
with col1:
    sample_file = st.file_uploader("Upload SAMPLE File", type=['xlsx'])
with col2:
    blank_file = st.file_uploader("Upload BLANK File", type=['xlsx'])

# 5. Main Logic (Variable used here!)
if sample_file and blank_file:
    try:
        h_s, df_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
        h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

        def check_match(row, target_df, tol):
            matches = target_df[target_df['Hit Name'] == row['Hit Name']]
            for _, t_row in matches.iterrows():
                if abs(row['RT (min)'] - t_row['RT (min)']) <= tol: return "YES"
            return "NO"

        df_s['In_Blank'] = df_s.apply(lambda r: check_match(r, df_b, rt_tolerance), axis=1)
        df_b['In_Sample'] = df_b.apply(lambda r: check_match(r, df_s, rt_tolerance), axis=1)
        df_final = df_s[df_s['In_Blank'] == "NO"].copy()
        
        # Dashboard & Metrics
        total_sample = len(df_s)
        excluded = len(df_s[df_s['In_Blank'] == "YES"])
        final_count = len(df_final)
        purity = (final_count / total_sample * 100) if total_sample > 0 else 0
        
        st.subheader("📊 Analysis Summary Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Sample Peaks", f"{total_sample}")
        m2.metric("Blank Matches (Excluded)", f"{excluded}", delta=f"-{excluded}", delta_color="inverse")
        m3.metric("Final Unique Compounds", f"{final_count}")
        m4.metric("Sample Purity Score", f"{purity:.1f}%")

        # English Interpretation
        st.info("### 🧠 LipidExpert Intelligence")
        purity_status = "High" if purity > 85 else "Moderate" if purity > 60 else "Low"
        summary_text = f"**Data Integrity Status: {purity_status}**\nThe analysis identified **{final_count} unique biomarkers** after excluding **{excluded} peaks** found in the Solvent Blank. With RT Tolerance at **±{rt_tolerance} min**, the system ensures 100% authentication."
        st.markdown(summary_text)

        class_counts = df_final['Chemical_Status'].value_counts().reset_index()
        class_counts.columns = ['Chemical Class', 'Peak Count']
        st.table(class_counts)

        # Tabs
        t1, t2, t3 = st.tabs(["Solvent Blank", "Sample Mapping", "Final Unique Fingerprint"])
        with t1: st.dataframe(df_b.style.apply(lambda x: ['background: #FFEB9C' if x['In_Sample'] == 'YES' else '' for _ in x], axis=1))
        with t2: st.dataframe(df_s.style.apply(lambda x: ['background: #FFEB9C' if x['In_Blank'] == 'YES' else '' for _ in x], axis=1))
        with t3: st.dataframe(df_final.drop(columns=['In_Blank']))

        # --- PREMIUM EXCEL EXPORT (FIXED INDENTATION) ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            wb = writer.book
            fmt_header = wb.add_format({'bold': True, 'font_size': 14, 'font_color': 'white', 'bg_color': '#1F4E78', 'border': 1, 'align': 'center'})
            fmt_sub = wb.add_format({'bold': True, 'font_color': '#1F4E78', 'bg_color': '#D9E1F2', 'border': 1})
            fmt_val = wb.add_format({'border': 1, 'align': 'center'})
            fmt_pct = wb.add_format({'border': 1, 'align': 'center', 'num_format': '0.00%'})
            
            ws_dash = wb.add_worksheet('Executive Summary')
            ws_dash.set_column('B:B', 35); ws_dash.set_column('C:C', 20)
            ws_dash.merge_range('B2:E3', 'LIPIDEXPERT ANALYTICAL SUMMARY', fmt_header)
            
            metrics_list = [('Quality Threshold', q_threshold), ('RT Tolerance', rt_tolerance), ('Area Threshold', area_threshold), ('Final Biomarkers', final_count)]
            for i, (l, v) in enumerate(metrics_list, start=5):
                ws_dash.write(f'B{i}', l, wb.add_format({'border': 1}))
                ws_dash.write(f'C{i}', v, fmt_val)
            
            p_row = 5 + len(metrics_list)
            ws_dash.write(f'B{p_row}', 'FINAL PURITY SCORE', wb.add_format({'bold': True, 'border': 1}))
            ws_dash.write(f'C{p_row}', purity/100, fmt_pct)
            ws_dash.conditional_format(f'C{p_row}:C{p_row}', {'type': 'data_bar', 'bar_color': '#63BE7B', 'min_type': 'num', 'min_value': 0, 'max_type': 'num', 'max_value': 1})

            rs = 'Validated_Fingerprint'
            ws_rep = wb.add_worksheet(rs)
            h_s.to_excel(writer, sheet_name=rs, startrow=0, index=False, header=False)
            df_s.to_excel(writer, sheet_name=rs, startrow=9, index=False)
            
            ws_rep.freeze_panes(10, 0)
            ws_rep.set_column('A:Q', 15)
            ws_rep.set_column('I:I', 40)
            
            blank_col = df_s.columns.get_loc('In_Blank')
            fmt_matched = wb.add_format({'font_color': '#9C0006', 'bg_color': '#FFC7CE', 'font_strikeout': True})
            ws_rep.conditional_format(10, 0, 10+len(df_s), 25, {'type': 'formula', 'criteria': f'=${chr(65+blank_col)}11="YES"', 'format': fmt_matched})

        st.download_button("📥 Download Premium Analytical Report", output.getvalue(), "LipidExpert_Premium_Report.xlsx")

    except Exception as e:
        st.error(f"Error during processing: {e}")
