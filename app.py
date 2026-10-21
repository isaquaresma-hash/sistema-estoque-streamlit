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
    page_title="Sistema de Gestão de Compras e Estoque",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Customização CSS com a Paleta Exata da Imagem
CUSTOM_CSS = """
<style>
    /* Fundo Geral da Aplicação: Branco #FFFFFF */
    .stApp {
        background-color: #FFFFFF;
        color: #103965;
    }
    
    /* Sidebar: Cinza-azulado suave #F5F8FC */
    [data-testid="stSidebar"] {
        background-color: #F5F8FC !important;
        border-right: 1px solid #D7E3F1;
    }
    
    /* Textos na Sidebar */
    [data-testid="stSidebar"] * {
        color: #103965 !important;
    }

    /* Banner do Topo/Cabeçalho Inspirado na Imagem */
    .banner-header {
        background-color: #F5F8FC;
        border: 1px solid #D7E3F1;
        padding: 2rem 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(16, 57, 101, 0.05);
    }
    .banner-subhead {
        color: #103965;
        font-size: 1.1rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        margin: 0;
        text-transform: uppercase;
    }
    .banner-main-title {
        color: #103965;
        font-size: 2.2rem;
        font-weight: 900;
        line-height: 1.1;
        letter-spacing: 0.02em;
        margin: 0.3rem 0;
        text-transform: uppercase;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .banner-badge {
        display: inline-block;
        background-color: #5A9BE5;
        color: #FFFFFF;
        font-weight: 700;
        padding: 0.4rem 1.5rem;
        border-radius: 20px;
        font-size: 1rem;
        letter-spacing: 0.08em;
        margin-top: 0.5rem;
    }

    /* Cards e Containers de Conteúdo em Cinza-Azulado #F5F8FC */
    .login-container, div[data-testid="stForm"] {
        background-color: #F5F8FC !important;
        padding: 2.5rem 2rem;
        border-radius: 12px;
        border: 1px solid #D7E3F1;
        box-shadow: 0 4px 15px rgba(16, 57, 101, 0.06);
    }

    /* Rótulos e Texto de Inputs */
    div[data-testid="stForm"] label, .login-container label {
        color: #103965 !important;
        font-weight: 700;
    }

    /* Botões em Azul-Claro #5A9BE5 */
    .stButton>button {
        background-color: #5A9BE5 !important;
        color: #FFFFFF !important
