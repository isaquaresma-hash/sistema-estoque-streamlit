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

# Função para carregar imagem local do GitHub e converter para Base64
def get_base64_of_bin_file(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

img_name = "Sistema de Compras e Estoque.png"
img_base64 = get_base64_of_bin_file(img_name)

# URL da imagem de fundo de almoxarifado/logística
BG_WAREHOUSE_URL = "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1920&q=80"

# Customização CSS idêntica ao design fornecido
CUSTOM_CSS = f"""
<style>
    /* Imagem de Fundo em tela cheia */
    .stApp {{
        background: url("{BG_WAREHOUSE_URL}") no-repeat center center fixed;
        background-size: cover;
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: rgba(245, 248, 252, 0.96) !important;
        border-right: 1px solid #D7E3F1;
    }}
    
    [data-testid="stSidebar"] * {{
        color: #103965 !important;
    }}

    /* Container Central do Cartão de Login */
    .login-wrapper {{
        display: flex;
        justify-content: center;
        align-items: center;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }}

    /* Cartão de Login Branco com Cantos Arredondados e Detalhes Azuis */
    .login-card-inner {{
        background: #FFFFFF;
        border-radius: 28px;
        padding: 2.5rem 2.2rem 1.8rem 2.2rem;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
        position: relative;
        overflow: hidden;
        max-width: 460px;
        margin: 0 auto;
    }}

    /* Detalhes Decorativos Azuis nos Cantos (Curvas do Design) */
    .login-card-inner::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 110px;
        height: 110px;
        background: radial-gradient(circle at top left, #0D47A1 70%, transparent 71%);
        z-index: 1;
        pointer-events: none;
    }}

    .login-card-inner::after {{
        content: "";
        position: absolute;
        bottom: 0;
        right: 0;
        width: 120px;
        height: 120px;
        background: radial-gradient(circle at bottom right, #0D47A1 70%, transparent 71%);
        z-index: 1;
        pointer-events: none;
    }}

    /* Conteúdo do Login relativo para sobrepor o fundo */
    .login-content {{
        position: relative;
        z-index: 2;
    }}

    .logo-img-login {{
        max-width: 320px;
        width: 100%;
        height: auto;
        display: block;
        margin: 0 auto 1.5rem auto;
    }}

    .welcome-title {{
        color: #0D1B2A;
        font-size: 1.5rem;
        font-weight: 800;
        margin: 0 0 0.2rem 0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }}

    .welcome-sub {{
        color: #8D99AE;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
        font-weight: 500;
    }}

    /* Inputs Estilizados com Fundo Azul-Claro Suave */
    div[data-testid="stForm"] {{
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        box-shadow: none !important;
    }}

    div[data-testid="stForm"] label {{
        color: #1E293B !important;
        font-weight: 700;
        font-size: 0.88rem;
        margin-bottom: 0.3rem;
    }}

    .stTextInput input {{
        background-color: #F1F5F9 !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        color: #1E293B !important;
        padding: 0.65rem 1rem !important;
        font-size: 0.95rem !important;
    }}
