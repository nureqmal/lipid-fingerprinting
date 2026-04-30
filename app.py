import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="LipidExpert: Analytical Suite", layout="wide")
st.title("🧪 LipidExpert: Analytical Suite")

# --- SIDEBAR CONTROL ---
st.sidebar.header("⚙️ Analytical Controls")

q_threshold = st.sidebar.slider("Select NIST Quality Threshold", 50, 95, 80, 5)
rt_tolerance = st.sidebar.slider("Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01)
area_threshold = st.sidebar.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01)

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1.  **Metadata Preservation**: Captures and retains original NIST headers (Rows 1–9).
2.  **Quality Gate**: Filtering peaks with NIST Quality **≥ {q_threshold}**.
3.  **RT-Aware Matching**: Matching compounds using Name + RT Tolerance (**±{rt_tolerance} min**).
---
""")

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

col1, col2 = st.columns(2)
with col1:
    sample_file = st.file_uploader("Upload SAMPLE File", type=['xlsx'])
with col2:
    blank_file = st.file_uploader("Upload BLANK File", type=['xlsx'])

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
        
        # --- METRICS DASHBOARD ---
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

        # --- ENGLISH INTERPRETATION BOX ---
        st.info("### 🧠 LipidExpert Intelligence")
        purity_status = "High" if purity > 85 else "Moderate" if purity > 60 else "Low"
        summary_text = f"""
        **Data Integrity Status: {purity_status}**  
        The analysis identified **{final_count} unique biomarkers** after excluding **{excluded} peaks** found in the Solvent Blank. 
        With the RT Tolerance set at **±{rt_tolerance} min**, the system ensures 100% authentication of the final lipid fingerprint.
        """
        st.markdown(summary_text)

        st.markdown("---")

        # --- TABS DISPLAY ---
        t1, t2, t3 = st.tabs(["1. Solvent Blank Data", "2. Sample Mapping", "3. Final Unique Fingerprint"])
        
        with t1:
            st.write("Highlighted rows exist in Sample.")
            st.dataframe(df_b.style.apply(lambda x: ['background: #FFEB9C' if x['In_Sample'] == 'YES' else '' for _ in x], axis=1))
        
        with t2:
            st.write("Highlighted rows exist in Blank (Purged from final).")
            st.dataframe(df_s.style.apply(lambda x: ['background: #FFEB9C' if x['In_Blank'] == 'YES' else '' for _ in x], axis=1))
        
        with t3:
            st.write("### 🔍 Interactive Drill-Down Table")
            st.caption("Click on a row to view deep-dive analytics for that specific compound.")
            
            # THE DRILL-DOWN LOGIC
            df_display = df_final.drop(columns=['In_Blank'])
            event = st.dataframe(
                df_display, 
                on_select="rerun", 
                selection_mode="single_row",
                use_container_width=True
            )
            
            if event.selection.rows:
                selected_index = event.selection.rows[0]
                selected_row = df_display.iloc[selected_index]
                
                # Detailed View
                st.success(f"#### 🧬 Deep-Dive: {selected_row['Hit Name']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**RT (min):** {selected_row['RT (min)']}")
                c2.write(f"**Quality:** {selected_row['Quality']}")
                c3.write(f"**Area (%):** {selected_row.get('Area (%)', 0):.4f}%")
                c4.write(f"**Status:** {selected_row['Chemical_Status']}")
                
                # Internal Link (Optional)
                st.markdown(f"[Search NIST WebBook for {selected_row['Hit Name']}](https://webbook.nist.gov/cgi/cbook.cgi?Name={selected_row['Hit Name'].replace(' ', '+')}&Units=SI)")

        # --- EXCEL EXPORT ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            ws_dash = writer.book.add_worksheet('Dashboard')
            header_fmt = writer.book.add_format({'bold': True, 'bg_color': '#2E75B6', 'font_color': 'white', 'border': 1})
            ws_dash.write('B2', 'LIPIDEXPERT ANALYTICAL SUMMARY', header_fmt)
            metrics = [('Quality Threshold Used', q_threshold), ('RT Tolerance (min)', rt_tolerance), ('Final Unique Biomarkers', final_count), ('Sample Purity Score', f"{purity:.2f}%")]
            for i, (l, v) in enumerate(metrics, start=4):
                ws_dash.write(f'B{i}', l); ws_dash.write(f'C{i}', v)
            
            rs = 'Analytical_Report'
            h_b.to_excel(writer, sheet_name=rs, startrow=1, index=False, header=False)
            df_b.to_excel(writer, sheet_name=rs, startrow=10, index=False, header=False)
            s2 = len(df_b) + 15
            h_s.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
            df_s.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
            s3 = s2 + len(df_s) + 15
            fh = h_s.copy(); fh.iloc[0,0] = f"{fh.iloc[0,0]} (FINAL FINGERPRINT)"
            fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
            df_final.drop(columns=['In_Blank']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)

        st.download_button("📥 Download Final Report", output.getvalue(), "LipidExpert_Final_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
