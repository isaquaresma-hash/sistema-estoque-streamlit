def gerar_excel_estilizado(df):
    """Gera uma planilha Excel .xlsx profissional com colunas bem formatadas e cabeçalho em azul."""
    buffer = io.BytesIO()
    
    # 1. Renomear e selecionar colunas de forma limpa e legível (caso existam no DF)
    col_map = {
        'id': 'ID',
        'produto': 'Produto',
        'tipo': 'Tipo de Lançamento',
        'quantidade': 'Quantidade',
        'preco_unitario': 'Preço Unitário (R$)',
        'mes_ano': 'Mês/Ano',
        'Diferença Qtd': 'Diferença de Qtd',
        'Diferença Preço': 'Diferença de Preço (R$)'
    }
    
    # Cria uma cópia com nomes amigáveis para o relatório
    df_export = df.rename(columns=col_map).copy()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Relatório')
        worksheet = writer.sheets['Relatório']
        
        # 2. Estilos visuais no padrão azul solicitado (#0D47A1)
        header_fill = PatternFill(start_color="0D47A1", end_color="0D47A1", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        # Estilos dos dados
        data_font = Font(name="Calibri", size=11)
        left_alignment = Alignment(horizontal="left", vertical="center")
        center_alignment = Alignment(horizontal="center", vertical="center")
        right_alignment = Alignment(horizontal="right", vertical="center")
        
        # Borda inferior suave entre as linhas
        thin_border = Border(
            bottom=Side(style='thin', color='E0E0E0'),
            left=Side(style='thin', color='F0F0F0'),
            right=Side(style='thin', color='F0F0F0')
        )

        # 3. Aplicar cabeçalho azul em cada coluna da linha 1
        for col_num in range(1, len(df_export.columns) + 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            
        worksheet.row_dimensions[1].height = 28

        # 4. Formatar células de dados e alinhamentos
        for row_num in range(2, len(df_export) + 2):
            worksheet.row_dimensions[row_num].height = 22
            for col_num in range(1, len(df_export.columns) + 1):
                cell = worksheet.cell(row=row_num, column=col_num)
                cell.font = data_font
                cell.border = thin_border
                
                # Regras de alinhamento e formatação de valores
                val = cell.value
                if isinstance(val, (int, float)):
                    # Se for coluna de preço, aplica formatação monetária R$
                    col_name = str(worksheet.cell(row=1, column=col_num).value)
                    if 'R$' in col_name or 'Preço' in col_name:
                        cell.number_format = 'R$ #,##0.00'
                        cell.alignment = right_alignment
                    else:
                        cell.alignment = center_alignment
                elif str(val).isupper() or len(str(val)) <= 10:
                    cell.alignment = center_alignment
                else:
                    cell.alignment = left_alignment

        # 5. Ajuste automático e individual de largura de cada coluna
        for col in worksheet.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            
            worksheet.column_dimensions[col_letter].width = max(max_len + 6, 16)

    buffer.seek(0)
    return buffer.getvalue()
