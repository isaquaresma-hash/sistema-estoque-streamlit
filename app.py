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
# ESTILIZAÇÃO CSS (CONCEITO ORIGINAL COMPACTO E FIXO)
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

        /* Cartão Único e Compacto para todo o Login */
        div[data-testid='stForm'] {
            background-color: #FFFFFF !important;
            padding: 2rem 2.2rem 1.8rem 2.2rem !important;
            border-radius: 18px !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 10px 30px rgba(0, 33, 113, 0.08) !important;
            width: 440px !important;
            max-width: 90vw !important;
            margin: auto !important;
        }

        .login-logo-img {
            max-width: 210px !important;
            width: 100% !important;
            height: auto !important;
            display: block !important;
            margin: 0 auto 1.2rem auto !important;
        }

        .login-welcome-title {
            color: #0D1B2A;
            font-size: 1.35rem;
            font-weight: 800;
            margin: 0 0 0.2rem 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            text-align: center;
        }

        .login-welcome-sub {
            color: #64748B;
            font-size: 0.88rem;
            margin-bottom: 1.4rem;
            font-weight: 500;
            text-align: center;
        }

        div[data-testid='stForm'] button[kind='secondaryFormSubmit'] {
            background-color: #0D47A1 !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 0.65rem 1rem !important;
            margin-top: 1rem !important;
            width: 100% !important;
        }

        div[data-testid='stForm'] button[kind='secondaryFormSubmit']:hover {
            background-color: #002171 !important;
            color: #FFFFFF !important;
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

        div
