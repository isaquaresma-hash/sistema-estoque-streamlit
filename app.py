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

# Estilização CSS limpa (sem imagem extra por trás/em cima)
css_code = "<style>.stApp { background-color: #EBF2FA !important; } [data-testid='stSidebar'] { background-color: #FFFFFF !important; border-right: 1px solid #D7E3F1; } [data-testid='stSidebar'] * { color: #103965 !important; } div[data-testid='stForm'] { background-color: #FFFFFF !important; padding: 2.2rem 2rem 1.8rem 2rem !important; border-radius: 28px !important; border: 1px solid #E2E8F0 !important; position: relative !important; overflow: hidden !important; box-shadow: 0 15px 35px rgba(0, 33, 113, 0.12) !important; } div[data-testid='stForm']::before { content: ''; position: absolute; top: 0; left: 0; width: 130px; height: 130px; background: radial-gradient(circle at top left, #0D47A1 65%, #002171 85%, transparent 86%); pointer-events: none; z-index: 1; } div[data-testid='stForm']::after { content: ''; position: absolute; bottom: 0; right: 0; width: 140px; height: 140px; background: radial-gradient(circle at bottom right, #0D47A1 65%, #002171 85%, transparent 86%); pointer-events: none; z-index: 1; } .login-logo-img { max-width: 260px; width: 100%; height: auto; display: block; margin: 0 auto 1rem auto; position: relative; z-index: 2; } .login-welcome-title { color: #0D1B2A; font-size: 1.4rem; font-weight: 800; margin: 0 0 0.2rem 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; position: relative; z-index: 2; } .login-welcome-sub { color: #64748B; font-size: 0.88rem; margin-bottom: 1.2rem; font-weight: 500; position: relative; z-index: 2; } div[data-testid='stForm'] label { color: #1E293B !important; font-weight: 700 !important; font-size: 0.88rem !important; position: relative; z-index: 2; } .stTextInput input { background-color: #F8FAFC !important; border: 1px solid #CBD5E1 !important; border-radius: 10px !important; color: #1E293B !important; padding: 0.65rem 0.9rem !important; position: relative; z-index: 2; } .stButton>button { background-color: #0D47A1 !important; color: #FFFFFF !important; border-radius: 10px !important; font-weight: 700 !important; padding: 0.7rem 1.2rem !important; border: none !important; position: relative; z-index: 2; width: 100% !important; } .secure-footer { text-align: center; color: #94A3B8; font-size: 0.8rem; margin-top: 1rem; position: relative; z-index: 2; } .user-profile-card { background-color: #0D47A1; color: #FFFFFF; padding: 1rem; border-radius: 10px; margin-bottom: 1.2rem; border-left: 5px solid #5A9BE5; } .user-profile-card p { margin: 0; color: #FFFFFF !important; }</style>"
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
    user =
