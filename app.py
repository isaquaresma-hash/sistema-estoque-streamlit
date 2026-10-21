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
# ESTILIZAÇÃO CSS (BLOCO HORIZONTAL UNIFICADO)
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

        /* Moldura Horizontal Unificada */
        .login-horizontal-box {
            display: flex;
            flex-direction: row;
            width: 780px;
            max-width: 92vw;
            background: #FFFFFF;
            border-radius: 18px;
            box-shadow: 0 12px 36px rgba(0, 33, 113, 0.08);
            border: 1px solid #E2E8F0;
            overflow: hidden;
            margin: auto;
        }

        /* Coluna da Esquerda (Marca / Logo) */
        .login-left-brand {
            flex: 1;
            background-color: #FAFCFF;
            border-right: 1px solid #EDF2F7;
            padding: 2.2rem 1.8rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        .login-left-brand img {
            max-width: 200px;
            width: 100%;
            height: auto;
            margin-bottom: 1rem;
        }

        .login-left-brand h3 {
            color: #0D47A1;
            font-size: 1.1rem;
            font-weight: 700;
            margin: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        /* Coluna da Direita (Campos do Formulário) */
        .login-right-form {
            flex: 1.2;
            padding: 2.2rem 2.2rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .login-title {
            color: #0D1B2A;
            font-size: 1.35rem;
            font-weight: 800;
            margin: 0 0 0.25rem 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .login-sub {
            color: #64748B;
            font-size: 0.85rem;
            margin-bottom: 1.2rem;
            font-weight: 500;
        }

        /* Reset do stForm para integrar perfeitamente dentro da coluna direita */
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
            border-radius: 8px !important;
            border: none !important;
            padding: 0.65rem 1rem !important;
            margin-top: 0.8rem !important;
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
    logo_img_html = f"<img src='data:image/png;base64,{img_base64}' alt='Logo FNP'>" if img_base64 else "<h4>📦</h4>"
    
    st.markdown(f"""
        <div class="login-horizontal-box">
            <div class="login-left-brand">
                {logo_img_html}
                <h3>Gestão de Compras & Estoque</h3>
            </div>
            <div class="login-right-form">
                <p class="login-title">Bem-vindo(a)!</p>
                <p class="login-sub">Acesse sua conta para continuar.</p>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("✉️ E-mail ou Usuário", placeholder="usuario@fnp.org.br")
        password = st.text_input("🔒 Senha", type="password", placeholder="••••••••")
        
        submit_login = st.form_submit_button("➔ Acessar Sistema", use_container_width=True)
        
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
                st.error("Credenciais inválidas. Verifique o usuário e a senha fornecidos.")

    st.markdown("""
                <p style="text-align:center; color:#94A3B8; font-size:0.78rem; margin-top:0.8rem;">🔒 Conexão segura</p>
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
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, alignment=2, textColor=colors.gray)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8)
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.white)

    story.append(Paragraph("<b>RELATÓRIO DE GESTÃO DE COMPRAS E ESTOQUE</b>", title_style))
    story.append(Paragraph(f"Período Analisado: {mes_anterior} vs {mes_atual} | Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))
    story.append(Spacer(1, 15))

    headers = [Paragraph("<b>Produto</b>", cell_bold), Paragraph(f"<b>Qtd ({mes_anterior})</b>", cell_bold), Paragraph(f"<b>Qtd ({mes_atual})</b>", cell_bold), Paragraph("<b>Dif. Qtd</b>", cell_bold), Paragraph(f"<b>Preço ({mes_atual})</b>", cell_bold), Paragraph("<b>Dif. Preço</b>", cell_bold)]
    
    table_data = [headers]

    for _, row in df_comparativo.iterrows():
        dif_qtd = row['Diferença Qtd']
        dif_qtd_str = f"+{dif_qtd}" if dif_qtd > 0 else str(dif_qtd)
        
        dif_preco = row['Diferença Preço']
        dif_preco_str = f"+R$ {dif_preco:.2f}" if dif_preco > 0 else f"R$ {dif_preco:.2f}"

        table_data.append([Paragraph(str(row['Produto']), cell_style), Paragraph(str(int(row[f'Qtd ({mes_anterior})'])), cell_style), Paragraph(str(int(row[f'Qtd ({mes_atual})'])), cell_style), Paragraph(dif_qtd_str, cell_style), Paragraph(f"R$ {row[f'Preço ({mes_atual})']:.2f}", cell_style), Paragraph(dif_preco_str, cell_style)])

    table = Table(table_data, colWidths=[150, 80, 80, 70, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D47A1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D7E3F1')),
    ]))
    
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ==========================================
# 1. GESTÃO DE PRODUTOS
# ==========================================
if menu == "📦 Gestão de Produtos":
    st.subheader("📦 Cadastro e Alteração de Produtos")
    st.caption("Cadastre novos produtos e atualize os preços de custo base.")
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Novo Produto", "✏️ Editar Produto / Valor"])
    
    with tab1:
        with st.form("form_cadastro"):
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome do Produto")
                preco_custo = st.number_input("Preço de Custo (R$)", min_value=0.01, format="%.2f")
            with c2:
                codigo = st.text_input("Código / Referência (Opcional)")
                qtd_inicial = st.number_input("Estoque Inicial", min_value=0, step=1)
            
            submitted = st.form_submit_button("💾 Salvar Produto")
            if submitted:
                if nome.strip() == "":
                    st.error("O campo 'Nome do Produto' é obrigatório.")
                else:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO produtos (nome, codigo_barras, preco_custo, quantidade_estoque) VALUES (?, ?, ?, ?)", (nome.strip(), codigo.strip(), preco_custo, qtd_inicial))
                        prod_id = cursor.lastrowid
                        
                        if qtd_inicial > 0:
                            cursor.execute("INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, preco_unitario) VALUES (?, 'ENTRADA', ?, ?)", (prod_id, qtd_inicial, preco_custo))
                        conn.commit()
                        conn.close()
                        st.success(f"Produto '{nome}' cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("Já existe um produto registrado com este nome.")

    with tab2:
        conn = sqlite3.connect(DB_NAME)
        produtos_df = pd.read_sql_query("SELECT id, nome, preco_custo, quantidade_estoque FROM produtos", conn)
        conn.close()
        
        if not produtos_df.empty:
            prod_selecionado = st.selectbox("Selecione o Produto para Alteração", produtos_df['nome'].tolist())
            dados_prod = produtos_df[produtos_df['nome'] == prod_selecionado].iloc[0]
            
            with st.form("form_editar"):
                c1, c2 = st.columns(2)
                with c1:
                    novo_nome = st.text_input("Nome", value=dados_prod['nome'])
                with c2:
                    novo_preco = st.number_input("Preço de Custo (R$)", min_value=0.01, value=float(dados_prod['preco_custo']), format="%.2f")
                
                if st.form_submit_button("🔄 Atualizar Informações"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE produtos SET nome = ?, preco_custo = ? WHERE id = ?", (novo_nome, novo_preco, int(dados_prod['id'])))
                    conn.commit()
                    conn.close()
                    st.success("Dados do produto atualizados com sucesso!")
                    st.rerun()
        else:
            st.info("Nenhum produto cadastrado no banco de dados.")

# ==========================================
# 2. MOVIMENTAÇÃO DE ESTOQUE
# ==========================================
elif menu == "🔄 Movimentação de Estoque":
    st.subheader("🔄 Movimentações de Compras & Estoque")
    st.caption("Registro de compras (entradas) e saídas operacionais.")
    
    conn = sqlite3.connect(DB_NAME)
    produtos_df = pd.read_sql_query("SELECT id, nome, preco_custo, quantidade_estoque FROM produtos", conn)
    conn.close()
    
    if produtos_df.empty:
        st.warning("Nenhum produto disponível no catálogo. Cadastre produtos antes de realizar movimentações.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            prod_nome = st.selectbox("Selecione o Produto", produtos_df['nome'].tolist())
            prod_info = produtos_df
