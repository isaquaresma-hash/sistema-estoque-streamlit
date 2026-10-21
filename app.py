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
# ESTILIZAÇÃO CSS
# ==========================================
css_code = """<style>
    /* Ocultar o cabeçalho superior nativo do Streamlit */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    [data-testid='stAppViewContainer'] {
        background-color: #F0F4F9 !important;
    }

    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
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

    /* Ocultar a barra de ferramentas flutuante sobre tabelas/dataframes */
    [data-testid="stElementToolbar"] {
        display: none !important;
    }

    /* Container de Login */
    div[data-testid='stForm'] {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        padding: 2rem !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
    }

    div[data-testid='stForm'] input {
        color: #1E293B !important;
        background-color: #FFFFFF !important;
    }

    div[data-testid='stForm'] label {
        color: #0F172A !important;
        font-weight: 600 !important;
    }

    div[data-testid='stForm'] button[kind='secondaryFormSubmit'] {
        background-color: #0D47A1 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 0.7rem 1.5rem !important;
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
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, username TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'operador')")
        cursor.execute("CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL, codigo_barras TEXT, preco_custo REAL NOT NULL, quantidade_estoque INTEGER NOT NULL DEFAULT 0, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("CREATE TABLE IF NOT EXISTS movimentacoes_estoque (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER, tipo TEXT CHECK(tipo IN ('ENTRADA', 'SAIDA')), quantidade INTEGER NOT NULL, preco_unitario REAL NOT NULL, data_compra DATE, data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(produto_id) REFERENCES produtos(id))")
        
        # Migração: adiciona a coluna data_compra caso a tabela já existisse
        cursor.execute("PRAGMA table_info(movimentacoes_estoque)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'data_compra' not in columns:
            cursor.execute("ALTER TABLE movimentacoes_estoque ADD COLUMN data_compra DATE")
            cursor.execute("UPDATE movimentacoes_estoque SET data_compra = DATE(data_movimentacao) WHERE data_compra IS NULL")

        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)", ("Administrador", "admin", hash_password("admin123"), "admin"))

        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'roze.peres@fnp.org.br'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)", ("Roze Peres", "roze.peres@fnp.org.br", hash_password("fnp2026"), "admin"))
        conn.commit()

init_db()

# ==========================================
# AUTENTICAÇÃO E SESSÃO
# ==========================================
def verificar_login(username, password):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, role FROM usuarios WHERE username = ? AND senha = ?", (username.lower().strip(), hash_password(password)))
        return cursor.fetchone()

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def login_screen():
    col1, col2, col3 = st.columns([0.8, 1.4, 0.8])
    
    with col2:
        with st.form("login_form"):
            if img_base64:
                st.markdown(f"<img src='data:image/png;base64,{img_base64}' style='max-width:280px; width:100%; display:block; margin:0 auto 1rem auto;'>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='text-align
