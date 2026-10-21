import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import base64
import os
from datetime import datetime, date
from io import BytesIO

from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Sistema Integrado de Compras e Estoque",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "estoque_compras.db"

# ==========================================
# CARREGAMENTO DE LOGO
# ==========================================
def get_base64_of_bin_file(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

img_name = "Sistema de Compras e Estoque.png"
img_base64 = get_base64_of_bin_file(img_name)

# ==========================================
# ESTILIZAÇÃO CSS (Inspirada no Layout Visual)
# ==========================================
css_code = """<style>
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid='stAppViewContainer'] { background-color: #F8FAFC !important; }
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px !important;
    }
    [data-testid='stSidebar'] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid='stSidebar'] * { color: #1E293B !important; }
    [data-testid="stElementToolbar"] { display: none !important; }
    
    /* Login Container */
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 2rem;
    }
    .login-container div[data-testid='stForm'] {
        background-color: #FFFFFF !important;
        padding: 2.5rem !important;
        border-radius: 20px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 12px 35px rgba(0, 33, 113, 0.09) !important;
        width: 100% !important;
    }
    .login-logo-img {
        max-width: 320px;
        width: 100%;
        height: auto;
        display: block;
        margin: 0 auto 1.2rem auto;
    }
    .login-welcome-title {
        color: #0F172A;
        font-size: 1.5rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .login-welcome-sub {
        color: #64748B;
        font-size: 0.92rem;
        margin-bottom: 1.5rem;
        font-weight: 500;
    }
    
    /* Card de Perfil */
    .user-profile-card {
        background-color: #0F172A;
        color: #FFFFFF;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1.2rem;
        border-left: 5px solid #2563EB;
    }
    .user-profile-card p { margin: 0; color: #FFFFFF !important; }

    /* Cartões Visuais dos Módulos */
    .module-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
    }
    .module-icon {
        background-color: #1E293B;
        color: #FFFFFF;
        width: 48px;
        height: 48px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        margin-right: 1.2rem;
        flex-shrink: 0;
    }
    .module-title {
        color: #0F172A;
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0 0 0.2rem 0;
    }
    .module-desc {
        color: #64748B;
        font-size: 0.88rem;
        margin: 0;
    }
</style>"""
st.markdown(css_code, unsafe_allow_html=True)

# ==========================================
# BANCO DE DADOS E CRIPTOGRAFIA
# ==========================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 1. Usuários
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'solicitante',
                setor TEXT DEFAULT 'Geral',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Catálogo de Materiais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materiais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL,
                unidade TEXT NOT NULL,
                marca_ref TEXT,
                preco_custo REAL NOT NULL DEFAULT 0.0,
                quantidade_estoque INTEGER NOT NULL DEFAULT 0,
                estoque_minimo INTEGER NOT NULL DEFAULT 5,
                localizacao TEXT,
                lote TEXT,
                validade DATE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. Fornecedores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj TEXT UNIQUE NOT NULL,
                razao_social TEXT NOT NULL,
                nome_fantasia TEXT,
                contato_nome TEXT,
                telefone TEXT,
                email TEXT,
                condicoes_comerciais TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 4. Requisições de Compra
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requisicoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solicitante_id INTEGER,
                setor TEXT NOT NULL,
                material_id INTEGER,
                quantidade INTEGER NOT NULL,
                justificativa TEXT NOT NULL,
                prioridade TEXT CHECK(prioridade IN ('Baixa', 'Média', 'Alta', 'Urgente')),
                status TEXT CHECK(status IN ('Pendente', 'Aprovada', 'Rejeitada', 'Em Cotação', 'Atendida')) DEFAULT 'Pendente',
                aprovador_id INTEGER,
                data_aprovacao TIMESTAMP,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(solicitante_id) REFERENCES usuarios(id),
                FOREIGN KEY(material_id) REFERENCES materiais(id),
                FOREIGN KEY(aprovador_id) REFERENCES usuarios(id)
            )
        """)
        
        # 5. Cotações de Compras
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisicao_id INTEGER,
                fornecedor_id INTEGER,
                preco_unitario REAL NOT NULL,
                prazo_entrega_dias INTEGER,
                observacao TEXT,
                selecionado INTEGER DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(requisicao_id) REFERENCES requisicoes(id),
                FOREIGN KEY(fornecedor_id) REFERENCES fornecedores(id)
            )
        """)
        
        # 6. Pedidos de Compra
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos_compra (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisicao_id INTEGER,
                cotacao_id INTEGER,
                fornecedor_id INTEGER,
                material_id INTEGER,
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL,
                valor_total REAL NOT NULL,
                status TEXT CHECK(status IN ('Emitido', 'Em Transporte', 'Concluído', 'Cancelado')) DEFAULT 'Emitido',
                usuario_id INTEGER,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(requisicao_id) REFERENCES requisicoes(id),
                FOREIGN KEY(cotacao_id) REFERENCES cotacoes(id),
                FOREIGN KEY(fornecedor_id) REFERENCES fornecedores(id),
                FOREIGN KEY(material_id) REFERENCES materiais(id),
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        """)
        
        # 7. Recebimentos & Conferência
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recebimentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER,
                numero_nota_fiscal TEXT NOT NULL,
                quantidade_recebida INTEGER NOT NULL,
                tem_divergencia INTEGER DEFAULT 0,
                observacao_divergencia TEXT,
                responsavel_id INTEGER,
                data_recebimento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(pedido_id) REFERENCES pedidos_compra(id),
                FOREIGN KEY(responsavel_id) REFERENCES usuarios(id)
            )
        """)

        # 8. Movimentações e Ajustes de Estoque
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER,
                tipo TEXT CHECK(tipo IN ('ENTRADA', 'SAIDA', 'AJUSTE', 'TRANSFERENCIA')),
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL,
                motivo TEXT,
                usuario_id INTEGER,
                data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(material_id) REFERENCES materiais(id),
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        """)

        # 9. Entregas ao Solicitante
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entregas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisicao_id INTEGER,
                material_id INTEGER,
                quantidade INTEGER NOT NULL,
                setor_destino TEXT NOT NULL,
                responsavel_retirada TEXT NOT NULL,
                usuario_entrega_id INTEGER,
                data_entrega TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(requisicao_id) REFERENCES requisicoes(id),
                FOREIGN KEY(material_id) REFERENCES materiais(id),
                FOREIGN KEY(usuario_entrega_id) REFERENCES usuarios(id)
            )
        """)
        
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (nome, username, senha, role, setor) VALUES (?, ?, ?, ?, ?)",
                           ("Administrador Geral", "admin", hash_password("admin123"), "admin", "TI"))

        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'roze.peres@fnp.org.br'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (nome, username, senha, role, setor) VALUES (?, ?, ?, ?, ?)",
                           ("Roze Peres", "roze.peres@fnp.org.br", hash_password("fnp2026"), "admin", "Diretoria"))

        conn.commit()

init_db()

# ==========================================
# AUTENTICAÇÃO E SESSÃO
# ==========================================
def verificar_login(username, password):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, role, setor FROM usuarios WHERE username = ? AND senha = ?", 
                       (username.lower().strip(), hash_password(password)))
        return cursor.fetchone()

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def login_screen():
    col1, col2, col3 = st.columns([0.8, 1.4, 0.8])
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        with st.form("login_form"):
            if img_base64:
                st.markdown(f"<img src='data:image/png;base64,{img_base64}' class='login-logo-img' alt='Logo'>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='text-align:center; color:#0F172A;'>SISTEMA DE COMPRAS E ESTOQUE</h3>", unsafe_allow_html=True)
                
            st.markdown("<p class='login-welcome-title'>Acesso ao Sistema</p>", unsafe_allow_html=True)
            st.markdown("<p class='login-welcome-sub'>Informe suas credenciais para continuar.</p>", unsafe_allow_html=True)
            
            username = st.text_input("✉️ E-mail ou Usuário", placeholder="usuario@empresa.org.br")
            password = st.text_input("🔒 Senha", type="password", placeholder="••••••••")
            
            submit_login = st.form_submit_button("➔ Entrar no Sistema", use_container_width=True)
            
            if submit_login:
                user = verificar_login(username, password)
                if user:
                    st.session_state["usuario_logado"] = {
                        "id": user[0],
                        "nome": user[1],
                        "role": user[2],
                        "setor": user[3]
                    }
                    st.success(f"Bem-vindo(a), {user[1]}!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas. Verifique usuário e senha.")
        st.markdown("</div>", unsafe_allow_html=True)

def logout():
    st.session_state["usuario_logado"] = None
    st.rerun()

if not st.session_state["usuario_logado"]:
    login_screen()
    st.stop()

# ==========================================
# UTILITÁRIOS DE EXPORTAÇÃO
# ==========================================
def gerar_excel_estilizado_bytes(df_exportar, nome_aba="Relatório"):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_exportar.to_excel(writer, index=False, sheet_name=nome_aba)
        worksheet = writer.sheets[nome_aba]
        
        header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        thin_border = Border(bottom=Side(style='thin', color='E0E0E0'), left=Side(style='thin', color='F0F0F0'), right=Side(style='thin', color='F0F0F0'))
        
        for col_num, col_name in enumerate(df_exportar.columns, 1):
            col_letter = get_column_letter(col_num)
            cell = worksheet.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
            is_moeda = any(term in str(col_name).lower() for term in ["preço", "custo", "valor", "total"])
            
            for row_num in range(2, len(df_exportar) + 2):
                data_cell = worksheet.cell(row=row_num, column=col_num)
                data_cell.border = thin_border
                val = data_cell.value
                if isinstance(val, (int, float)):
                    if is_moeda:
                        data_cell.number_format = 'R$ #,##0.00'
                        data_cell.alignment = Alignment(horizontal="right", vertical="center")
                    else:
                        data_cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    data_cell.alignment = Alignment(horizontal="left", vertical="center")

            max_len = max(len(str(col_name)), max([len(str(worksheet.cell(row=r, column=col_num).value or '')) for r in range(2, len(df_exportar) + 2)], default=0))
            worksheet.column_dimensions[col_letter].width = max(max_len + 4, 12)
            
    return buffer.getvalue()

def gerar_pdf_generic_bytes(titulo, df_dados):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=12, alignment=1, spaceAfter=8, textColor=colors.HexColor('#0F172A'))
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=8, alignment=2, textColor=colors.gray)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=7)
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', textColor=colors.white)

    story.append(Paragraph(f"<b>{titulo.upper()}</b>", title_style))
    story.append(Paragraph(f"Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))
    story.append(Spacer(1, 10))

    headers = [Paragraph(f"<b>{col}</b>", cell_bold) for col in df_dados.columns]
    table_data = [headers]

    for _, row in df_dados.iterrows():
        linha = [Paragraph(str(val), cell_style) for val in row.values]
        table_data.append(linha)

    col_widths = [int(540 / len(df_dados.columns))] * len(df_dados.columns)
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ==========================================
# NAVEGAÇÃO LATERAL (8 MÓDULOS)
# ==========================================
user_info = st.session_state["usuario_logado"]

st.sidebar.markdown(f"""
<div class='user-profile-card'>
    <p style='font-size: 0.95rem; font-weight: 700;'>👤 {user_info['nome']}</p>
    <p style='font-size: 0.8rem; opacity: 0.9;'>Setor: <b>{user_info['setor']}</b></p>
    <p style='font-size: 0.8rem; opacity: 0.9;'>Perfil: <b>{user_info['role'].upper()}</b></p>
</div>
""", unsafe_allow_
