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

# Verificar estado de autenticação
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

# ==========================================
# ESTILIZAÇÃO CSS (DESIGN MODERNO SPLIT-SCREEN)
# ==========================================
if not st.session_state["usuario_logado"]:
    css_code = """<style>
        header[data-testid="stHeader"] {
            display: none !important;
        }
        
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #EEF2F6 !important;
            height: 100vh !important;
            overflow: hidden !important;
        }

        .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
            height: 100vh !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* Card Principal Unificado */
        .login-card {
            display: flex;
            flex-direction: row;
            background: #FFFFFF;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(13, 71, 161, 0.08);
            width: 820px;
            max-width: 92vw;
            overflow: hidden;
            border: 1px solid #E2E8F0;
        }

        /* Coluna da Esquerda - Banner Institucional */
        .login-banner {
            flex: 1;
            background: linear-gradient(135deg, #0D47A1 0%, #002171 100%);
            padding: 2.5rem 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: #FFFFFF;
            text-align: center;
        }

        .login-banner img {
            max-width: 220px;
            width: 100%;
            height: auto;
            margin-bottom: 1.5rem;
            filter: drop-shadow(0 4px 10px rgba(0,0,0,0.15));
            background: #FFFFFF;
            padding: 12px;
            border-radius: 12px;
        }

        .login-banner h2 {
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: #FFFFFF !important;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .login-banner p {
            font-size: 0.88rem;
            color: #E3F2FD !important;
            margin: 0;
            line-height: 1.4;
        }

        /* Coluna da Direita - Formulário */
        .login-form-area {
            flex: 1.1;
            padding: 2.5rem 2.2rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            background: #FFFFFF;
        }

        .login-title {
            font-size: 1.5rem;
            font-weight: 800;
            color: #0D1B2A;
            margin-bottom: 0.2rem;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .login-subtitle {
            font-size: 0.88rem;
            color: #64748B;
            margin-bottom: 1.8rem;
        }

        div[data-testid='stForm'] {
            border: none !important;
            padding: 0 !important;
            box-shadow: none !important;
            background: transparent !important;
        }

        div[data-testid='stForm'] button[kind='secondaryFormSubmit'] {
            background-color: #0D47A1 !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border-radius: 10px !important;
            border: none !important;
            padding: 0.75rem 1rem !important;
            margin-top: 1.2rem !important;
            width: 100% !important;
            font-size: 0.95rem !important;
            transition: all 0.2s ease-in-out;
        }

        div[data-testid='stForm'] button[kind='secondaryFormSubmit']:hover {
            background-color: #002171 !important;
            box-shadow: 0 4px 12px rgba(13, 71, 161, 0.25) !important;
        }
    </style>"""
else:
    css_code = """<style>
        header[data-testid="stHeader"] {
            display: none !important;
        }
        
        [data-testid='stAppViewContainer'] {
            background-color: #F0F4F9 !important;
        }

        .main .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            max-width: 1200px !important;
        }

        [data-testid='stSidebar'] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #D7E3F1;
        }
        [data-testid='stSidebar'] * {
            color: #103965 !important;
        }

        div[data-testid='stForm'] {
            background-color: #FFFFFF !important;
            border-radius: 16px !important;
            border: 1px solid #E2E8F0 !important;
            padding: 1.8rem !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04) !important;
        }

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

def login_screen():
    logo_html = f'<img src="data:image/png;base64,{img_base64}" alt="Logo">' if img_base64 else ''
    
    st.markdown(f"""
        <div class="login-card">
            <div class="login-banner">
                {logo_html}
                <h2>Gestão & Suprimentos</h2>
                <p>Controle centralizado de compras, saídas de material e análise operacional.</p>
            </div>
            <div class="login-form-area">
                <div class="login-title">Bem-vindo(a)</div>
                <div class="login-subtitle">Acesse sua conta para continuar</div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("✉️ E-mail ou Usuário", placeholder="usuario@fnp.org.br")
        password = st.text_input("🔒 Senha", type="password", placeholder="••••••••")
        
        submit_login = st.form_submit_button("➔ Entrar no Sistema", use_container_width=True)
        
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
                st.error("Credenciais inválidas. Verifique o usuário e a senha.")

    st.markdown("""
                <p style="text-align:center; color:#94A3B8; font-size:0.78rem; margin-top:1.5rem;">🔒 Conexão segura e encriptada</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

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
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'],
