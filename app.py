import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import base64
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Sistema de Gestão de Compras e Estoque",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar imagem do Logo em Base64
def get_base64_of_bin_file(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

img_name = "Sistema de Compras e Estoque.png"
img_base64 = get_base64_of_bin_file(img_name)

# ==========================================
# ESTILIZAÇÃO CSS (INTERFACE LIMPA E MODERNA)
# ==========================================
css_code = """<style>
    [data-testid='stAppViewContainer'] {
        background-color: #F0F4F9 !important;
    }

    .main .block-container {
        padding-top: 2rem !important;
        max-width: 1200px !important;
    }

    /* Sidebar */
    [data-testid='stSidebar'] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #D7E3F1;
    }
    [data-testid='stSidebar'] * {
        color: #103965 !important;
    }

    /* Cartão de LOGIN */
    .login-container div[data-testid='stForm'] {
        background-color: #FFFFFF !important;
        padding: 2.2rem 2rem 1.8rem 2rem !important;
        border-radius: 20px !important;
        border: 1px solid #E2E8F0 !important;
        position: relative !important;
        overflow: hidden !important;
        box-shadow: 0 10px 30px rgba(0, 33, 113, 0.08) !important;
    }

    .login-logo-img {
        max-width: 260px;
        width: 100%;
        height: auto;
        display: block;
        margin: 0 auto 1rem auto;
    }

    .login-welcome-title {
        color: #0D1B2A;
        font-size: 1.4rem;
        font-weight: 800;
        margin: 0 0 0.2rem 0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    .login-welcome-sub {
        color: #64748B;
        font-size: 0.88rem;
        margin-bottom: 1.2rem;
        font-weight: 500;
    }

    /* Formulários e Cartões Internos Elegantes */
    div[data-testid='stForm'] {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        padding: 1.8rem !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04) !important;
    }

    /* Estilização dos Botões de Ação */
    div[data-testid='stForm'] button[kind='secondaryFormSubmit'] {
        background-color: #0D47A1 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 0.6rem 1.5rem !important;
        margin-top: 0.5rem !important;
    }

    div[data-testid='stForm'] button[kind='secondaryFormSubmit']:hover {
        background-color: #002171 !important;
        color: #FFFFFF !important;
    }

    .user-profile-card {
        background-color: #0D47A1;
        color: #FFFFFF;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1.2rem;
        border-left: 5px solid #5A9BE5;
    }

    .user-profile-card p {
        margin: 0;
        color: #FFFFFF !important;
    }
</style>"""
st.markdown(css_code, unsafe_allow_html=True)

DB_NAME = "estoque_compras.db"

# ==========================================
# BANCO DE DADOS E CRIPTOGRAFIA
# ==========================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, username TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'operador')")
    cursor.execute("CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL, codigo_barras TEXT, preco_custo REAL NOT NULL, quantidade_estoque INTEGER NOT NULL DEFAULT 0, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS movimentacoes_estoque (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER, tipo TEXT CHECK(tipo IN ('ENTRADA', 'SAIDA')), quantidade INTEGER NOT NULL, preco_unitario REAL NOT NULL, data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(produto_id) REFERENCES produtos(id))")
    
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)", ("Administrador", "admin", hash_password("admin123"), "admin"))

    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'roze.peres@fnp.org.br'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)", ("Roze Peres", "roze.peres@fnp.org.br", hash_password("fnp2026"), "admin"))
        
    conn.commit()
    conn.close()

init_db()

# ==========================================
# AUTENTICAÇÃO E SESSÃO
# ==========================================
def verificar_login(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, role FROM usuarios WHERE username = ? AND senha = ?", (username.lower().strip(), hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    return user

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        with st.form("login_form"):
            if img_base64:
                st.markdown(f"<img src='data:image/png;base64,{img_base64}' class='login-logo-img' alt='Logo FNP'>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='text-align:center; color:#0D47A1; margin-bottom:1rem;'>SISTEMA DE GESTÃO DE COMPRAS E ESTOQUE</h3>", unsafe_allow_html=True)
                
            st.markdown("<p class='login-welcome-title'>Bem-vindo(a)!</p>", unsafe_allow_html=True)
            st.markdown("<p class='login-welcome-sub'>Faça login para acessar o sistema.</p>", unsafe_allow_html=True)
            
            username = st.text_input("✉️ E-mail ou Usuário", placeholder="usuario@fnp.org.br")
            password = st.text_input("🔒 Senha", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            
            submit_login = st.form_submit_button("➔ Acessar Sistema", use_container_width=True)
            
            if submit_login:
                user = verificar_login(username, password)
                if user:
                    st.session_state["usuario_logado"] = {
                        "id": user[0],
                        "nome": user[1],
                        "role": user[2]
                    }
                    st.success(f"Autenticado com sucesso. Bem-vindo(a), {user[1]}!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas. Verifique o usuário e a senha fornecidos.")
            
            st.markdown("<p class='secure-footer' style='text-align:center; color:#94A3B8; font-size:0.8rem; margin-top:1rem;'>🔒 Acesso seguro</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

def logout():
    st.session_state["usuario_logado"] = None
    st.rerun()

if not st.session_state["usuario_logado"]:
    login_screen()
    st.stop()

# ==========================================
# INTERFACE PRINCIPAL (SESSÃO AUTENTICADA)
# ==========================================
user_info = st.session_state["usuario_logado"]

st.sidebar.markdown(f"<div class='user-profile-card'><p style='font-size: 0.95rem; font-weight: 700;'>👤 {user_info['nome']}</p><p style='font-size: 0.8rem; opacity: 0.9;'>Perfil: <b>{user_info['role'].upper()}</b></p></div>", unsafe_allow_html=True)

if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
    logout()

st.sidebar.divider()

menu_options = ["📊 Dashboard & Relatórios", "🔄 Movimentação de Estoque"]
if user_info["role"] == "admin":
    menu_options.insert(0, "📦 Gestão de Produtos")
    menu_options.append("👥 Gestão de Usuários")

menu = st.sidebar.radio("Navegação do Sistema", menu_options)

# ==========================================
# GERADOR DE RELATÓRIO PDF (REPORTLAB)
# ==========================================
def gerar_pdf_bytes(df_comparativo, mes_atual, mes_anterior):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, alignment=1, spaceAfter=8, textColor=colors.HexColor('#0D47A1'))
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, alignment=2, textColor=colors.gray)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8)
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.white)

    story.append(Paragraph("<b>RELATÓRIO DE GESTÃO DE COMPRAS E ESTOQUE</b>", title_style))
    story.append(Paragraph(f"Período Analisado: {mes_anterior} vs {mes_atual} | Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))
    story.append(Spacer(1, 15))

    headers = [
        Paragraph("<b>Produto</b>", cell_bold),
        Paragraph(f"<b>Qtd ({mes_anterior})</b>", cell_bold),
        Paragraph(f"<b>Qtd ({mes_atual})</b>", cell_bold),
        Paragraph("<b>Dif. Qtd</b>", cell_bold),
        Paragraph(f"<b>Preço ({mes_atual})</b>", cell_bold),
        Paragraph("<b>Dif. Preço</b>
