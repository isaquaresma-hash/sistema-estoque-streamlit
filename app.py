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
# CONFIGURAÇÃO DA PÁGINA E ESTILOS CSS
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

# CSS Totalmente Reformulado e Limpo
CUSTOM_CSS = """
<style>
    /* Imagem de Fundo de Armazém em tela cheia */
    .stApp {
        background: url("https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1920&q=80") no-repeat center center fixed;
        background-size: cover;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(245, 248, 252, 0.96) !important;
        border-right: 1px solid #D7E3F1;
    }
    
    [data-testid="stSidebar"] * {
        color: #103965 !important;
    }

    /* Caixa do Cartão Branco de Login */
    div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        padding: 2.2rem 2rem 1.8rem 2rem !important;
        border-radius: 24px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25) !important;
    }

    /* Logo Ajustado Dentro do Cartão */
    .login-logo-img {
        max-width: 260px;
        width: 100%;
        height: auto;
        display: block;
        margin: 0 auto 1.2rem auto;
    }

    /* Textos do Cabeçalho do Login */
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

    /* Estilização dos Rótulos (Labels) */
    div[data-testid="stForm"] label {
        color: #1E293B !important;
        font-weight: 700 !important;
        font-size: 0.88rem !important;
        margin-bottom: 0.2rem !important;
    }

    /* Estilização dos Inputs de Texto e Senha */
    .stTextInput input {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
        color: #1E293B !important;
        padding: 0.6rem 0.9rem !important;
        font-size: 0.95rem !important;
    }

    .stTextInput input:focus {
        border-color: #0D47A1 !important;
        box-shadow: 0 0 0 2px rgba(13, 71, 161, 0.15) !important;
    }

    /* Botão Azul-Marinho Integrado ao Formulário */
    .stButton>button {
        background-color: #0D47A1 !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.7rem 1.2rem !important;
        border: none !important;
        transition: all 0.2s ease !important;
        font-size: 0.95rem !important;
        text-transform: none !important;
        margin-top: 0.5rem !important;
    }

    .stButton>button:hover {
        background-color: #0A3880 !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(13, 71, 161, 0.3);
    }

    .secure-footer {
        text-align: center;
        color: #94A3B8;
        font-size: 0.8rem;
        margin-top: 1rem;
        font-weight: 500;
    }

    /* Perfil na Sidebar */
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

    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #0D47A1 !important;
        font-weight: 800;
    }
    
    hr {
        border-color: #D7E3F1 !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

DB_NAME = "estoque_compras.db"

# ==========================================
# BANCO DE DADOS E CRIPTOGRAFIA
# ==========================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'operador'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            codigo_barras TEXT,
            preco_custo REAL NOT NULL,
            quantidade_estoque INTEGER NOT NULL DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            tipo TEXT CHECK(tipo IN ('ENTRADA', 'SAIDA')),
            quantidade INTEGER NOT NULL,
            preco_unitario REAL NOT NULL,
            data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        )
    """)
    
    # Usuários Padrão
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)",
            ("Administrador", "admin", hash_password("admin123"), "admin")
        )

    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'roze.peres@fnp.org.br'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)",
            ("Roze Peres", "roze.peres@fnp.org.br", hash_password("fnp2026"),
