# --- EXCEL EXPORT (THE COMPLETE MASTERPIECE) ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            wb = writer.book
            header_fmt = wb.add_format({'bold': True, 'font_size': 16, 'bg_color': '#2E75B6', 'font_color': 'white', 'border': 1, 'align': 'center'})
            label_fmt = wb.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
            val_fmt = wb.add_format({'border': 1, 'align': 'center'})
            yellow_fmt = wb.add_format({'bg_color': '#FFEB9C', 'border': 1})
            navy_fmt = wb.add_format({'bg_color': '#002060', 'font_color': 'white', 'border': 1})
            pink_fmt = wb.add_format({'bg_color': '#FFC0CB', 'border': 1})

            # 1. DASHBOARD
            ws_dash = wb.add_worksheet('Dashboard')
            ws_dash.merge_range('B2:E2', 'LIPIDEXPERT ANALYTICAL SUMMARY', header_fmt)
            metrics_list = [('Quality Threshold', q_threshold), ('RT Tolerance', rt_tolerance), ('Area Threshold', area_threshold), ('Final Biomarkers', final_count), ('Purity Score', f"{purity:.2f}%")]
            for i, (l, v) in enumerate(metrics_list, start=4):
                ws_dash.write(f'B{i}', l, label_fmt); ws_dash.write(f'C{i}', v, val_fmt)
            
            # --- SEMUA LEGEND ADA KAT SINI ---
            ws_dash.write('B10', 'COLOR LEGEND / GUIDELINE:', wb.add_format({'bold': True, 'underline': True}))
            
            # Legend Kuning (Direct Blank Match)
            ws_dash.write('B11', 'Yellow Row', yellow_fmt)
            ws_dash.write('C11', 'Matched in Blank (Excluded from Final Fingerprint)', wb.add_format({'font_size': 10}))
            
            # Legend Biru Pekat (RT Shift)
            ws_dash.write('B12', 'Navy Blue RT Cell', navy_fmt)
            ws_dash.write('C12', 'RT Shift Detected (Retained - Distinct Analyte or Isomer)', wb.add_format({'font_size': 10}))
            
            # Legend Pink (Potential Contaminant)
            ws_dash.write('B13', 'Pink Cell', pink_fmt)
            ws_dash.write('C13', 'Potential Contaminant (Requires Manual Review of MS Spectrum)', wb.add_format({'font_size': 10, 'italic': True}))
            
            ws_dash.set_column('B:B', 30); ws_dash.set_column('C:C', 85)

            # 2. ANALYTICAL REPORT
            rs = 'Analytical_Report'
            ws_rep = wb.add_worksheet(rs)
            h_b.to_excel(writer, sheet_name=rs, startrow=2, index=False, header=False)
            df_b.to_excel(writer, sheet_name=rs, startrow=11, index=False, header=False)
            s2 = len(df_b) + 16
            h_s.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
            df_s.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
            s3 = s2 + len(df_s) + 15
            fh = h_s.copy(); fh.iloc[0,0] = f"{fh.iloc[0,0]} (CORRECTED UNIQUE)"
            fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
            df_final.drop(columns=['In_Blank', 'RT_Diff']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)

            # Conditional Formatting Logic
            rt_col_idx = df_s.columns.get_loc('RT (min)')
            status_col_idx = df_s.columns.get_loc('Chemical_Status')
            blank_col_idx = df_s.columns.get_loc('In_Blank')

            for start, limit in [(11, len(df_b)), (s2+10, len(df_s)), (s3+10, len(df_final))]:
                ws_rep.conditional_format(start, status_col_idx, start + limit, status_col_idx, {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': pink_fmt})

            # Highlight Yellow Row (Match) & Navy Cell (Shift)
            ws_rep.conditional_format(s2+10, 0, s2+10+len(df_s), len(df_s.columns)-1, {'type': 'formula', 'criteria': f'=${chr(65 + blank_col_idx)}{s2+11}="YES"', 'format': yellow_fmt})
            ws_rep.conditional_format(s2+10, rt_col_idx, s2+10+len(df_s), rt_col_idx, {'type': 'formula', 'criteria': f'=${chr(65 + blank_col_idx)}{s2+11}="RT_SHIFT_DETECTED"', 'format': navy_fmt})

            # Sync Blue Cell in Blank Section
            for i, row in df_b.iterrows():
                if any((df_s['Hit Name'] == row['Hit Name']) & (df_s['In_Blank'] == "RT_SHIFT_DETECTED")):
                    ws_rep.write(11 + i, rt_col_idx, row['RT (min)'], navy_fmt)

            # 3. PCA READY DATA
            ws_pca = wb.add_worksheet('PCA_Ready_Data')
            pca_compounds, pca_areas = df_final['Hit Name'].tolist(), df_final['Area (Ab*s)'].tolist()
            ws_pca.write(0, 0, 'Compound', wb.add_format({'bold': True, 'bg_color': '#E2EFDA'})); ws_pca.write(1, 0, 'Area')
            for col, (n, a) in enumerate(zip(pca_compounds, pca_areas), start=1):
                ws_pca.write(0, col, n); ws_pca.write(1, col, a)

        st.download_button("📥 Download Final Report", output.getvalue(), "LipidExpert_Expert_Report.xlsx")
