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

# ==========================================
# ESTILIZAÇÃO CSS (MARCA D'ÁGUA PÓS-LOGIN E LOGIN LIMPO)
# ==========================================
if img_base64:
    bg_style = f"""
    [data-testid="stAppViewContainer"] {{
        background-image: linear-gradient(rgba(240, 244, 249, 0.88), rgba(240, 244, 249, 0.88)), url('data:image/png;base64,{img_base64}') !important;
        background-repeat: no-repeat !important;
        background-position: center center !important;
        background-size: 60% auto !important;
        background-attachment: fixed !important;
    }}
    """
else:
    bg_style = """
    [data-testid="stAppViewContainer"] {
        background-color: #F0F4F9 !important;
    }
    """

css_code = f"""<style>
    {bg_style}

    /* Transparência suave nos blocos para revelar a marca d'água */
    .main .block-container {{
        background-color: transparent !important;
        padding-top: 2rem !important;
    }}

    /* Sidebar */
    [data-testid='stSidebar'] {{
        background-color: #FFFFFF !important;
        border-right: 1px solid #D7E3F1;
    }}
    [data-testid='stSidebar'] * {{
        color: #103965 !important;
    }}

    /* Estilo do Cartão de LOGIN limpo (sem bordas decorativas azuis) */
    .login-container div[data-testid='stForm'] {{
        background-color: #FFFFFF !important;
        padding: 2.2rem 2rem 1.8rem 2rem !important;
        border-radius: 20px !important;
        border: 1px solid #E2E8F0 !important;
        position: relative !important;
        overflow: hidden !important;
        box-shadow: 0 10px 30px rgba(0, 33, 113, 0.08) !important;
    }}

    .login-logo-img {{
        max-width: 260px;
        width: 100%;
        height: auto;
        display: block;
        margin: 0 auto 1rem auto;
        position: relative;
        z-index: 2;
    }}

    .login-welcome-title {{
        color: #0D1B2A;
        font-size: 1.4rem;
        font-weight: 800;
        margin: 0 0 0.2rem 0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        position: relative;
        z-index: 2;
    }}

    .login-welcome-sub {{
        color: #64748B;
        font-size: 0.88rem;
        margin-bottom: 1.2rem;
        font-weight: 500;
        position: relative;
        z-index: 2;
    }}

    /* Formulários internos translúcidos */
    div[data-testid='stForm'] {{
        background-color: rgba(255, 255, 255, 0.92) !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
    }}

    .user-profile-card {{
        background-color: #0D47A1;
        color: #FFFFFF;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1.2rem;
        border-left: 5px solid #5A9BE5;
    }}

    .user-profile-card p {{
        margin: 0;
        color: #FFFFFF !important;
    }}
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

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        with st.form("login_form"):
            if img_base64:
                st.markdown(f"<img src='data:image/png;base64,{img_base64}' class='login-logo-img' alt='Logo FNP'>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='text-align:center; color:#0D47A1; margin-bottom:1rem;'>SISTEMA DE GESTÃO DE COMPRAS E ESTOQUE</h3>", unsafe_allow_html=True)
                
            st.markdown("<p class='login-welcome-title'>Bem-vindo(a)!</p>", unsafe_allow_html=True)
            st.markdown("<p class='login-welcome-sub'>Faça login para acessar o sistema.</p>", unsafe_allow_html=True)
            
            username = st.text_input("✉️ E-mail ou Usuário", placeholder="usuario@fnp.org.br")
            password = st.text_input("🔒 Senha", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            
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
            
            st.markdown("<p class='secure-footer' style='text-align:center; color:#94A3B8; font-size:0.8rem; margin-top:1rem;'>🔒 Acesso seguro</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

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

    headers = [
        Paragraph("<b>Produto</b>", cell_bold),
        Paragraph(f"<b>Qtd ({mes_anterior})</b>", cell_bold),
        Paragraph(f"<b>Qtd ({mes_atual})</b>", cell_bold),
        Paragraph("<b>Dif. Qtd</b>", cell_bold),
        Paragraph(f"<b>Preço ({mes_atual})</b>", cell_bold),
        Paragraph("<b>Dif. Preço</b>", cell_bold)
    ]
    
    table_data = [headers]

    for _, row in df_comparativo.iterrows():
        dif_qtd = row['Diferença Qtd']
        dif_qtd_str = f"+{dif_qtd}" if dif_qtd > 0 else str(dif_qtd)
        
        dif_preco = row['Diferença Preço']
        dif_preco_str = f"+R$ {dif_preco:.2f}" if dif_preco > 0 else f"R$ {dif_preco:.2f}"

        table_data.append([
            Paragraph(str(row['Produto']), cell_style),
            Paragraph(str(int(row[f'Qtd ({mes_anterior})'])), cell_style),
            Paragraph(str(int(row[f'Qtd ({mes_atual})'])), cell_style),
            Paragraph(dif_qtd_str, cell_style),
            Paragraph(f"R$ {row[f'Preço ({mes_atual})']:.2f}", cell_style),
            Paragraph(dif_preco_str, cell_style)
        ])

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
            nome = st.text_input("Nome do Produto")
            codigo = st.text_input("Código / Referência (Opcional)")
            preco_custo = st.number_input("Preço de Custo (R$)", min_value=0.01, format="%.2f")
            qtd_inicial = st.number_input("Estoque Inicial", min_value=0, step=1)
            
            submitted = st.form_submit_button("Salvar Produto")
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
                novo_nome = st.text_input("Nome", value=dados_prod['nome'])
                novo_preco = st.number_input("Preço de Custo (R$)", min_value=0.01, value=float(dados_prod['preco_custo']), format="%.2f")
                
                if st.form_submit_button("Atualizar Informações"):
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
            prod_info = produtos_df[produtos_df['nome'] == prod_nome].iloc[0]
            st.info(f"**Estoque Atual:** {prod_info['quantidade_estoque']} unidades | **Preço Base:** R$ {prod_info['preco_custo']:.2f}")

        with col2:
            tipo_mov = st.radio("Tipo de Lançamento", ["ENTRADA (Compra/Aporte)", "SAIDA (Baixa/Consumo)"])
            quantidade = st.number_input("Quantidade", min_value=1, step=1)
            preco_unitario = st.number_input("Preço Unitário da Operação (R$)", min_value=0.01, value=float(prod_info['preco_custo']), format="%.2f")

        if st.button("Registrar Operação"):
            tipo = "ENTRADA" if "ENTRADA" in tipo_mov else "SAIDA"
            
            if tipo == "SAIDA" and quantidade > prod_info['quantidade_estoque']:
                st.error("Operação cancelada: a quantidade solicitada excede o saldo em estoque.")
            else:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                cursor.execute("INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, preco_unitario) VALUES (?, ?, ?, ?)", (int(prod_info['id']), tipo, quantidade, preco_unitario))
                
                nova_qtd = prod_info['quantidade_estoque'] + quantidade if tipo == "ENTRADA" else prod_info['quantidade_estoque'] - quantidade
                cursor.execute("UPDATE produtos SET quantidade_estoque = ? WHERE id = ?", (nova_qtd, int(prod_info['id'])))
                
                conn.commit()
                conn.close()
                st.success("Movimentação registrada com sucesso!")
                st.rerun()

# ==========================================
# 3. DASHBOARD E RELATÓRIO COMPARATIVO
# ==========================================
elif menu == "📊 Dashboard & Relatórios":
    st.subheader("📊 Painel Comparativo & Exportação PDF")
    st.caption("Comparação periódica de volume de compras e variações de valor.")
    
    conn = sqlite3.connect(DB_NAME)
    df_mov = pd.read_sql_query("SELECT m.id, p.nome as produto, m.tipo, m.quantidade, m.preco_unitario, strftime('%Y-%m', m.data_movimentacao) as mes_ano FROM movimentacoes_estoque m JOIN produtos p ON p.id = m.produto_id", conn)
    conn.close()

    if df_mov.empty:
        st.info("Ainda não há lançamentos registrados para gerar comparativos.")
    else:
        meses_disponiveis = sorted(df_mov['mes_ano'].unique(), reverse=True)
        
        if len(meses_disponiveis) < 2:
            st.warning("São necessários lançamentos em pelo menos dois meses diferentes para montar o comparativo de períodos.")
            st.markdown("### Histórico de Lançamentos:")
            st.dataframe(df_mov, use_container_width=True)
        else:
            col1, col2 = st.columns(2)
            with col1:
                mes_atual = st.selectbox("Selecione o Mês Recente (Atual)", meses_disponiveis, index=0)
            with col2:
                mes_anterior = st.selectbox("Selecione o Mês Base (Anterior)", meses_disponiveis, index=1 if len(meses_disponiveis) > 1 else 0)

            df_atual = df_mov[df_mov['mes_ano'] == mes_atual].groupby('produto').agg(qtd_atual=('quantidade', 'sum'), preco_atual=('preco_unitario', 'mean')).reset_index()
            df_ant = df_mov[df_mov['mes_ano'] == mes_anterior].groupby('produto').agg(qtd_ant=('quantidade', 'sum'), preco_ant=('preco_unitario', 'mean')).reset_index()

            df_comp = pd.merge(df_atual, df_ant, on='produto', how='outer').fillna(0)
            df_comp['Diferença Qtd'] = df_comp['qtd_atual'] - df_comp['qtd_ant']
            df_comp['Diferença Preço'] = df_comp['preco_atual'] - df_comp['preco_ant']

            df_comp.rename(columns={'produto': 'Produto', 'qtd_ant': f'Qtd ({mes_anterior})', 'qtd_atual': f'Qtd ({mes_atual})', 'preco_ant': f'Preço ({mes_anterior})', 'preco_atual': f'Preço ({mes_atual})'}, inplace=True)

            st.subheader("📌 Indicadores de Variação")
            m1, m2, m3 = st.columns(3)
            total_dif_qtd = df_comp['Diferença Qtd'].sum()
            media_dif_preco = df_comp['Diferença Preço'].mean()
            
            m1.metric("Variação de Volume", f"{total_dif_qtd:+} un")
            m2.metric("Variação Média de Preço", f"R$ {media_dif_preco:+.2f}")
            m3.metric("Itens Analisados", len(df_comp))

            st.divider()
            st.subheader("📋 Tabela Analítica")
            st.dataframe(df_comp, use_container_width=True)

            st.divider()
            st.subheader("📄 Emissão de Documento Oficial")
            pdf_data = gerar_pdf_bytes(df_comp, mes_atual, mes_anterior)
            st.download_button(label="📥 Baixar Relatório Comparativo em PDF", data=pdf_data, file_name=f"relatorio_gestao_compras_{mes_anterior}_vs_{mes_atual}.pdf", mime="application/pdf")

# ==========================================
# 4. GESTÃO DE USUÁRIOS
# ==========================================
elif menu == "👥 Gestão de Usuários":
    st.subheader("👥 Controle de Acesso e Usuários")
    st.caption("Gerenciamento de contas e atribuição de permissões no sistema.")
    
    with st.form("form_novo_usuario"):
        st.subheader("Cadastrar Novo Usuário")
        novo_nome = st.text_input("Nome Completo")
        novo_username = st.text_input("E-mail / Usuário de Acesso")
        nova_senha = st.text_input("Senha", type="password")
        novo_role = st.selectbox("Nível de Permissão", ["operador", "admin"])
        
        submit_user = st.form_submit_button("Cadastrar Usuário")
        if submit_user:
            if not novo_nome or not novo_username or not nova_senha:
                st.error("Todos os campos do formulário devem ser preenchidos.")
            else:
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)", (novo_nome.strip(), novo_username.strip().lower(), hash_password(nova_senha), novo_role))
                    conn.commit()
                    conn.close()
                    st.success(f"Acesso para '{novo_username}' configurado com sucesso!")
                except sqlite3.IntegrityError:
                    st.error("O e-mail/usuário informado já está cadastrado no sistema.")

    st.divider()
    st.subheader("Usuários Ativos")
    conn = sqlite3.connect(DB_NAME)
    users_df = pd.read_sql_query("SELECT id, nome, username, role FROM usuarios", conn)
    conn.close()
    st.dataframe(users_df, use_container_width=True)
