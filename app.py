import streamlit as st
import sqlite3
import pandas as pd
import hashlib
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
    page_title="Gestão de Compras",
    page_icon="🧺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Customização CSS com base na Paleta de Cores (Azul Turquesa #1CA9C9, Azul Marinho #0F1B38 e Amarelo #FFC107)
CUSTOM_CSS = """
<style>
    /* Fundo geral da aplicação em Azul Turquesa / Ciano da imagem */
    .stApp {
        background-color: #1CA9C9;
    }
    
    /* Barra lateral no mesmo tom Turquesa com borda */
    [data-testid="stSidebar"] {
        background-color: #1693B0 !important;
        border-right: 2px solid #0F1B38;
    }
    
    /* Textos principais na sidebar */
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }

    /* Banner do Topo/Cabeçalho em Azul Marinho Fechado com detalhes Amarelos */
    .banner-header {
        background-color: #0F1B38;
        color: #FFFFFF;
        padding: 2rem 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
        border: 2px solid #FFC107;
        box-shadow: 0 10px 25px rgba(15, 27, 56, 0.4);
    }
    .banner-icon {
        font-size: 3.5rem;
        line-height: 1;
        margin-bottom: 0.5rem;
    }
    .banner-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #FFFFFF;
        margin: 0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .banner-subtitle {
        color: #FFC107;
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 0.3rem;
        letter-spacing: 0.05em;
    }
    
    /* Card/Container de Conteúdo e Formulários em Azul Escuro */
    .login-container, div[data-testid="stForm"] {
        background-color: #0F1B38 !important;
        padding: 2rem;
        border-radius: 12px;
        border: 2px solid #1693B0;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
    }

    /* Labels e textos de campos sobre fundo escuro */
    div[data-testid="stForm"] label, .login-container label {
        color: #FFFFFF !important;
        font-weight: 600;
    }
    
    /* Botões em Amarelo Ouro / Destaque da Imagem */
    .stButton>button {
        background-color: #FFC107 !important;
        color: #0F1B38 !important;
        border-radius: 8px !important;
        font-weight: 800 !important;
        padding: 0.6rem 1.2rem !important;
        border: none !important;
        transition: all 0.2s ease !important;
        text-transform: uppercase;
    }
    .stButton>button:hover {
        background-color: #E6A100 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
    }
    
    /* Card do Perfil na Sidebar */
    .user-profile-card {
        background: #0F1B38;
        color: white;
        padding: 1.2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        border-left: 5px solid #FFC107;
    }
    .user-profile-card p {
        margin: 0;
    }

    /* Ajustes em títulos principais fora dos cards */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #0F1B38 !important;
        font-weight: 800;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

DB_NAME = "estoque_compras.db"

# ==========================================
# BANCO DE DADOS E CRIPTOGRAFIA
# ==========================================
def hash_password(password):
    """Criptografa a senha usando SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Inicializa as tabelas do banco de dados SQLite."""
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
    
    # Usuário Padrão Admin
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)",
            ("Administrador", "admin", hash_password("admin123"), "admin")
        )

    # Usuário Cadastrado: Roze Peres
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'roze.peres@fnp.org.br'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)",
            ("Roze Peres", "roze.peres@fnp.org.br", hash_password("fnp2026"), "admin")
        )
        
    conn.commit()
    conn.close()

init_db()

# ==========================================
# AUTENTICAÇÃO E SESSÃO
# ==========================================
def verificar_login(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, nome, role FROM usuarios WHERE username = ? AND senha = ?",
        (username.lower().strip(), hash_password(password))
    )
    user = cursor.fetchone()
    conn.close()
    return user

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def login_screen():
    col1, col2, col3 = st.columns([1, 1.3, 1])
    
    with col2:
        st.markdown("""
            <div class='banner-header'>
                <div class='banner-icon'>🧺</div>
                <h1 class='banner-title'>GESTÃO de COMPRAS</h1>
                <p class='banner-subtitle'>SISTEMA DE CONTROLE DE ESTOQUE & SUPRIMENTOS</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("E-mail ou Usuário", placeholder="usuario@fnp.org.br")
            password = st.text_input("Senha", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            submit_login =
