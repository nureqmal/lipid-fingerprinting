# --- PREMIUM EXCEL EXPORT ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            wb = writer.book
            
            # --- 1. DEFINE PREMIUM FORMATS ---
            fmt_header = wb.add_format({'bold': True, 'font_size': 14, 'font_color': 'white', 'bg_color': '#1F4E78', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            fmt_sub = wb.add_format({'bold': True, 'font_color': '#1F4E78', 'bg_color': '#D9E1F2', 'border': 1, 'align': 'left'})
            fmt_val = wb.add_format({'border': 1, 'align': 'center'})
            fmt_pct = wb.add_format({'border': 1, 'align': 'center', 'num_format': '0.00%'})
            fmt_clean = wb.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'}) # Green for Clean
            fmt_review = wb.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700'}) # Yellow for Review
            fmt_zebra = wb.add_format({'bg_color': '#F2F2F2'})
            
            # --- 2. DASHBOARD SHEET ---
            ws_dash = wb.add_worksheet('Executive Summary')
            ws_dash.set_column('B:B', 35)
            ws_dash.set_column('C:C', 20)
            
            # Header Title
            ws_dash.merge_range('B2:E3', 'LIPIDEXPERT ANALYTICAL INTELLIGENCE REPORT', fmt_header)
            
            # Performance Section
            ws_dash.write('B5', 'OVERALL DATA PERFORMANCE', fmt_sub)
            ws_dash.write('C5', 'VALUE', fmt_sub)
            
            metrics = [
                ('Quality Threshold (NIST)', q_threshold),
                ('Retention Time Tolerance', f"± {rt_tolerance} min"),
                ('Noise Filter (Area %)', f"{area_threshold}%"),
                ('Total Peaks Analyzed', total_sample),
                ('Solvent Blank Matches', excluded),
                ('Final Validated Biomarkers', final_count)
            ]
            for i, (l, v) in enumerate(metrics, start=6):
                ws_dash.write(f'B{i}', l, wb.add_format({'border': 1}))
                ws_dash.write(f'C{i}', v, fmt_val)
            
            # Purity Score with Data Bar
            purity_row = 6 + len(metrics)
            ws_dash.write(f'B{purity_row}', 'FINAL SAMPLE PURITY SCORE', wb.add_format({'bold': True, 'border': 1, 'bg_color': '#E2EFDA'}))
            ws_dash.write(f'C{purity_row}', purity/100, fmt_pct)
            ws_dash.conditional_format(f'C{purity_row}:C{purity_row}', {'type': 'data_bar', 'bar_color': '#63BE7B', 'min_type': 'num', 'min_value': 0, 'max_type': 'num', 'max_value': 1})

            # Class Distribution Table
            dist_row = purity_row + 2
            ws_dash.write(f'B{dist_row}', 'CHEMICAL CLASS DISTRIBUTION', fmt_sub)
            ws_dash.write(f'C{dist_row}', 'COUNT', fmt_sub)
            for i, (row) in enumerate(class_counts.values, start=dist_row + 1):
                ws_dash.write(f'B{i}', row[0], wb.add_format({'border': 1}))
                ws_dash.write(f'C{i}', row[1], fmt_val)

            # --- 3. ANALYTICAL REPORT SHEET ---
            rs = 'Validated_Fingerprint'
            ws_rep = wb.add_worksheet(rs)
            
            # Metadata Section (Rows 1-9)
            h_s.to_excel(writer, sheet_name=rs, startrow=0, index=False, header=False)
            
            # Data Section (Headers on Row 10)
            df_s.to_excel(writer, sheet_name=rs, startrow=9, index=False)
            
            # Formatting the Data Table
            ws_rep.freeze_panes(10, 0) # Freeze headers
            ws_rep.set_column('A:Q', 15) # Default width
            ws_rep.set_column('I:I', 40) # Hit Name wider
            
            # Header Format for Data
            data_header_fmt = wb.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1, 'align': 'center'})
            for col_num, value in enumerate(df_s.columns.values):
                ws_rep.write(9, col_num, value, data_header_fmt)

            # Conditional Formatting for Status
            # Find column index for Chemical_Status and In_Blank
            status_col = df_s.columns.get_loc('Chemical_Status')
            blank_col = df_s.columns.get_loc('In_Blank')
            
            last_row = 9 + len(df_s)
            
            # 1. Highlight Matched In Blank (Yellow Strike)
            fmt_matched = wb.add_format({'font_color': '#9C0006', 'bg_color': '#FFC7CE', 'font_strikeout': True})
            ws_rep.conditional_format(10, 0, last_row, len(df_s.columns)-1, {
                'type': 'formula',
                'criteria': f'=${chr(65 + blank_col)}11="YES"',
                'format': fmt_matched
            })
            
            # 2. Highlight Clean Lipids (Green)
            ws_rep.conditional_format(10, status_col, last_row, status_col, {
                'type': 'cell',
                'criteria': 'equal to',
                'value': '"Clean (Lipid/Oxidation)"',
                'format': fmt_clean
            })

        st.download_button("📥 Download Premium Analytical Report", output.getvalue(), "LipidExpert_Premium_Report.xlsx")
