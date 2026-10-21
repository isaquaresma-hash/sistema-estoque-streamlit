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
# ESTILIZAÇÃO CSS (BLOCO HORIZONTAL AMPLIADO)
# ==========================================
if not st.session_state["usuario_logado"]:
    css_code = """<style>
        header[data-testid="stHeader"] {
            display: none !important;
        }
        
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #F0F4F9 !important;
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

        /* Moldura Horizontal Unificada Expandida (1000px) */
        .login-horizontal-box {
            display: flex;
            flex-direction: row;
            width: 1000px;
            max-width: 95vw;
            background: #FFFFFF;
            border-radius: 20px;
            box-shadow: 0 16px 48px rgba(0, 33, 113, 0.10);
            border: 1px solid #E2E8F0;
            overflow: hidden;
            margin: auto;
        }

        /* Coluna da Esquerda (Marca / Logo Expandidos) */
        .login-left-brand {
            flex: 1.1;
            background-color: #FAFCFF;
            border-right: 1px solid #EDF2F7;
            padding: 3rem 2.5rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        .login-left-brand img {
            max-width: 280px;
            width: 100%;
            height: auto;
            margin-bottom: 1.2rem;
        }

        .login-left-brand h3 {
            color: #0D47A1;
            font-size: 1.25rem;
            font-weight: 700;
            margin: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        /* Coluna da Direita (Campos do Formulário Expandidos) */
        .login-right-form {
            flex: 1.3;
            padding: 3rem 3rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .login-title {
            color: #0D1B2A;
            font-size: 1.6rem;
            font-weight: 800;
            margin: 0 0 0.3rem 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .login-sub {
            color: #64748B;
            font-size: 0.95rem;
            margin
