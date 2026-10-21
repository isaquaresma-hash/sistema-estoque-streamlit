import io
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def gerar_excel_estilizado(df):
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
        worksheet = writer.sheets['Relatorio']
        
        # 1. Definição do Estilo do Cabeçalho (Verde escuro com texto branco em negrito)
        header_fill = PatternFill(start_color="003319", end_color="003319", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        # Estilo das Células de Dados
        data_font = Font(name="Calibri", size=11)
        data_alignment = Alignment(horizontal="left", vertical="center")
        center_alignment = Alignment(horizontal="center", vertical="center")
        
        # Borda inferior fina para os dados
        thin_border = Border(bottom=Side(style='thin', color='E0E0E0'))

        # 2. Aplicar estilo no Cabeçalho
        for col_num in range(1, len(df.columns) + 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
        
        # Ajustar altura da linha do cabeçalho
        worksheet.row_dimensions[1].height = 25

        # 3. Aplicar estilo e alinhamento nas linhas de dados
        for row_num in range(2, len(df) + 2):
            worksheet.row_dimensions[row_num].height = 20
            for col_num in range(1, len(df.columns) + 1):
                cell = worksheet.cell(row=row_num, column=col_num)
                cell.font = data_font
                cell.border = thin_border
                
                # Centralizar colunas curtas (ex: UF, Situação, Ranking)
                header_name = str(worksheet.cell(row=1, column=col_num).value).lower()
                if header_name in ['uf', 'situação', 'situacao', 'ranking', 'tipo']:
                    cell.alignment = center_alignment
                else:
                    cell.alignment = data_alignment

        # 4. Ajustar automaticamente a largura das colunas
        for col in worksheet.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            
            # Define uma largura proporcional com espaço extra
            worksheet.column_dimensions[col_letter].width = max(max_len + 5, 15)

    buffer.seek(0)
    return buffer.getvalue()
