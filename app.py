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
        background-color
