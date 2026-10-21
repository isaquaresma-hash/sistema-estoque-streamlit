import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import base64
import os
from datetime import datetime, date
from io import BytesIO

from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Sistema Integrado de Compras e Estoque",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "estoque_compras.db"

# ==========================================
# CARREGAMENTO DE LOGO
# ==========================================
def get_base64_of_bin_file(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

img_name = "Sistema de Compras e Estoque.png"
img_base64 = get_base64_of_bin_file(img_name)

# ==========================================
# ESTILIZAÇÃO CSS
# ==========================================
css_code = """<style>
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid='stAppViewContainer'] { background-color: #F0F4F9 !important; }
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px !important;
    }
    [data-testid='stSidebar'] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #D7E3F1;
    }
    [data-testid='stSidebar'] * { color: #103965 !important; }
    [data-testid="stElementToolbar"] { display: none !important; }
    
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 2rem;
    }
    .login-container div[data-testid='stForm'] {
        background-color: #FFFFFF !important;
        padding: 2.5rem !important;
        border-radius: 20px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 12px 35px rgba(0, 33, 113, 0.09) !important;
        width: 100% !important;
    }
    .login-logo-img {
        max-width: 320px;
        width: 100%;
        height: auto;
        display: block;
        margin: 0 auto 1.2rem auto;
    }
    .login-welcome-title {
        color: #0D1B2A;
        font-size: 1.5rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .login-welcome-sub {
        color: #64748B;
        font-size: 0.92rem;
        margin-bottom: 1.5rem;
        font-weight: 500;
    }
    div[data-testid='stForm'] {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        padding: 1.8rem !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04) !important;
    }
    .user-profile-card {
        background-color: #0D47A1;
        color: #FFFFFF;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1.2rem;
        border-left: 5px solid #5A9BE5;
    }
    .user-profile-card p { margin: 0; color: #FFFFFF !important; }
</style>"""
st.markdown(css_code, unsafe_allow_html=True)

# ==========================================
# BANCO DE DADOS E CRIPTOGRAFIA
# ==========================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 1. Usuários
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'solicitante',
                setor TEXT DEFAULT 'Geral',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Catálogo de Materiais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materiais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL,
                unidade TEXT NOT NULL,
                marca_ref TEXT,
                preco_custo REAL NOT NULL DEFAULT 0.0,
                quantidade_estoque INTEGER NOT NULL DEFAULT 0,
                estoque_minimo INTEGER NOT NULL DEFAULT 5,
                localizacao TEXT,
                lote TEXT,
                validade DATE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. Fornecedores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj TEXT UNIQUE NOT NULL,
                razao_social TEXT NOT NULL,
                nome_fantasia TEXT,
                contato_nome TEXT,
                telefone TEXT,
                email TEXT,
                condicoes_comerciais TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 4. Requisições de Compra
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requisicoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solicitante_id INTEGER,
                setor TEXT NOT NULL,
                material_id INTEGER,
                quantidade INTEGER NOT NULL,
                justificativa TEXT NOT NULL,
                prioridade TEXT CHECK(prioridade IN ('Baixa', 'Média', 'Alta', 'Urgente')),
                status TEXT CHECK(status IN ('Pendente', 'Aprovada', 'Rejeitada', 'Em Cotação', 'Atendida')) DEFAULT 'Pendente',
                aprovador_id INTEGER,
                data_aprovacao TIMESTAMP,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(solicitante_id) REFERENCES usuarios(id),
                FOREIGN KEY(material_id) REFERENCES materiais(id),
                FOREIGN KEY(aprovador_id) REFERENCES usuarios(id)
            )
        """)
        
        # 5. Cotações de Compras
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisicao_id INTEGER,
                fornecedor_id INTEGER,
                preco_unitario REAL NOT NULL,
                prazo_entrega_dias INTEGER,
                observacao TEXT,
                selecionado INTEGER DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(requisicao_id) REFERENCES requisicoes(id),
                FOREIGN KEY(fornecedor_id) REFERENCES fornecedores(id)
            )
        """)
        
        # 6. Pedidos de Compra
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos_compra (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisicao_id INTEGER,
                cotacao_id INTEGER,
                fornecedor_id INTEGER,
                material_id INTEGER,
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL,
                valor_total REAL NOT NULL,
                status TEXT CHECK(status IN ('Emitido', 'Em Transporte', 'Concluído', 'Cancelado')) DEFAULT 'Emitido',
                usuario_id INTEGER,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(requisicao_id) REFERENCES requisicoes(id),
                FOREIGN KEY(cotacao_id) REFERENCES cotacoes(id),
                FOREIGN KEY(fornecedor_id) REFERENCES fornecedores(id),
                FOREIGN KEY(material_id) REFERENCES materiais(id),
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        """)
        
        # 7. Recebimentos & Conferência
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recebimentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER,
                numero_nota_fiscal TEXT NOT NULL,
                quantidade_recebida INTEGER NOT NULL,
                tem_divergencia INTEGER DEFAULT 0,
                observacao_divergencia TEXT,
                responsavel_id INTEGER,
                data_recebimento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(pedido_id) REFERENCES pedidos_compra(id),
                FOREIGN KEY(responsavel_id) REFERENCES usuarios(id)
            )
        """)

        # 8. Movimentações e Ajustes de Estoque
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER,
                tipo TEXT CHECK(tipo IN ('ENTRADA', 'SAIDA', 'AJUSTE', 'TRANSFERENCIA')),
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL,
                motivo TEXT,
                usuario_id INTEGER,
                data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(material_id) REFERENCES materiais(id),
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        """)

        # 9. Entregas ao Solicitante
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entregas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisicao_id INTEGER,
                material_id INTEGER,
                quantidade INTEGER NOT NULL,
                setor_destino TEXT NOT NULL,
                responsavel_retirada TEXT NOT NULL,
                usuario_entrega_id INTEGER,
                data_entrega TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(requisicao_id) REFERENCES requisicoes(id),
                FOREIGN KEY(material_id) REFERENCES materiais(id),
                FOREIGN KEY(usuario_entrega_id) REFERENCES usuarios(id)
            )
        """)
        
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (nome, username, senha, role, setor) VALUES (?, ?, ?, ?, ?)",
                           ("Administrador Geral", "admin", hash_password("admin123"), "admin", "TI"))

        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'roze.peres@fnp.org.br'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (nome, username, senha, role, setor) VALUES (?, ?, ?, ?, ?)",
                           ("Roze Peres", "roze.peres@fnp.org.br", hash_password("fnp2026"), "admin", "Diretoria"))

        conn.commit()

init_db()

# ==========================================
# AUTENTICAÇÃO E SESSÃO
# ==========================================
def verificar_login(username, password):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, role, setor FROM usuarios WHERE username = ? AND senha = ?", 
                       (username.lower().strip(), hash_password(password)))
        return cursor.fetchone()

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def login_screen():
    col1, col2, col3 = st.columns([0.8, 1.4, 0.8])
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        with st.form("login_form"):
            if img_base64:
                st.markdown(f"<img src='data:image/png;base64,{img_base64}' class='login-logo-img' alt='Logo'>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='text-align:center; color:#0D47A1;'>SISTEMA DE COMPRAS E ESTOQUE</h3>", unsafe_allow_html=True)
                
            st.markdown("<p class='login-welcome-title'>Acesso ao Sistema</p>", unsafe_allow_html=True)
            st.markdown("<p class='login-welcome-sub'>Informe suas credenciais para continuar.</p>", unsafe_allow_html=True)
            
            username = st.text_input("✉️ E-mail ou Usuário", placeholder="usuario@empresa.org.br")
            password = st.text_input("🔒 Senha", type="password", placeholder="••••••••")
            
            submit_login = st.form_submit_button("➔ Entrar no Sistema", use_container_width=True)
            
            if submit_login:
                user = verificar_login(username, password)
                if user:
                    st.session_state["usuario_logado"] = {
                        "id": user[0],
                        "nome": user[1],
                        "role": user[2],
                        "setor": user[3]
                    }
                    st.success(f"Bem-vindo(a), {user[1]}!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas. Verifique usuário e senha.")
        st.markdown("</div>", unsafe_allow_html=True)

def logout():
    st.session_state["usuario_logado"] = None
    st.rerun()

if not st.session_state["usuario_logado"]:
    login_screen()
    st.stop()

# ==========================================
# UTILITÁRIOS DE EXPORTAÇÃO
# ==========================================
def gerar_excel_estilizado_bytes(df_exportar, nome_aba="Relatório"):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_exportar.to_excel(writer, index=False, sheet_name=nome_aba)
        worksheet = writer.sheets[nome_aba]
        
        header_fill = PatternFill(start_color="0D47A1", end_color="0D47A1", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        thin_border = Border(bottom=Side(style='thin', color='E0E0E0'), left=Side(style='thin', color='F0F0F0'), right=Side(style='thin', color='F0F0F0'))
        
        for col_num, col_name in enumerate(df_exportar.columns, 1):
            col_letter = get_column_letter(col_num)
            cell = worksheet.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
            is_moeda = any(term in str(col_name).lower() for term in ["preço", "custo", "valor", "total"])
            
            for row_num in range(2, len(df_exportar) + 2):
                data_cell = worksheet.cell(row=row_num, column=col_num)
                data_cell.border = thin_border
                val = data_cell.value
                if isinstance(val, (int, float)):
                    if is_moeda:
                        data_cell.number_format = 'R$ #,##0.00'
                        data_cell.alignment = Alignment(horizontal="right", vertical="center")
                    else:
                        data_cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    data_cell.alignment = Alignment(horizontal="left", vertical="center")

            max_len = max(len(str(col_name)), max([len(str(worksheet.cell(row=r, column=col_num).value or '')) for r in range(2, len(df_exportar) + 2)], default=0))
            worksheet.column_dimensions[col_letter].width = max(max_len + 4, 12)
            
    return buffer.getvalue()

def gerar_pdf_generic_bytes(titulo, df_dados):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=12, alignment=1, spaceAfter=8, textColor=colors.HexColor('#0D47A1'))
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=8, alignment=2, textColor=colors.gray)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=7)
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', textColor=colors.white)

    story.append(Paragraph(f"<b>{titulo.upper()}</b>", title_style))
    story.append(Paragraph(f"Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))
    story.append(Spacer(1, 10))

    headers = [Paragraph(f"<b>{col}</b>", cell_bold) for col in df_dados.columns]
    table_data = [headers]

    for _, row in df_dados.iterrows():
        linha = [Paragraph(str(val), cell_style) for val in row.values]
        table_data.append(linha)

    col_widths = [int(540 / len(df_dados.columns))] * len(df_dados.columns)
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D47A1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D7E3F1')),
    ]))
    
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ==========================================
# NAVEGAÇÃO LATERAL (8 MÓDULOS)
# ==========================================
user_info = st.session_state["usuario_logado"]

st.sidebar.markdown(f"""
<div class='user-profile-card'>
    <p style='font-size: 0.95rem; font-weight: 700;'>👤 {user_info['nome']}</p>
    <p style='font-size: 0.8rem; opacity: 0.9;'>Setor: <b>{user_info['setor']}</b></p>
    <p style='font-size: 0.8rem; opacity: 0.9;'>Perfil: <b>{user_info['role'].upper()}</b></p>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
    logout()

st.sidebar.divider()

menu_map = {
    "01. Painel de Controle": "01. Painel de Controle",
    "02. Requisições de Compra": "02. Requisições de Compra",
    "03. Gestão de Compras": "03. Gestão de Compras",
    "04. Controle de Estoque": "04. Controle de Estoque",
    "05. Catálogo de Materiais": "05. Catálogo de Materiais",
    "06. Fornecedores": "06. Fornecedores",
    "07. Documentos & Entregas": "07. Documentos & Entregas",
    "08. Relatórios e Indicadores": "08. Relatórios e Indicadores"
}

if user_info["role"] == "admin":
    menu_map["👥 Gestão de Usuários"] = "👥 Gestão de Usuários"

menu_opcao = st.sidebar.radio("Navegação do Sistema", list(menu_map.keys()))

# ==========================================
# 01. PAINEL DE CONTROLE
# ==========================================
if menu_opcao == "01. Painel de Controle":
    st.title("📊 Painel de Controle")
    st.caption("Visão rápida de estoque, compras, pendências e visão financeira.")

    with sqlite3.connect(DB_NAME) as conn:
        total_materiais = pd.read_sql_query("SELECT COUNT(*) FROM materiais", conn).iloc[0, 0]
        pedidos_andamento = pd.read_sql_query("SELECT COUNT(*) FROM pedidos_compra WHERE status IN ('Emitido', 'Em Transporte')", conn).iloc[0, 0]
        abaixo_minimo = pd.read_sql_query("SELECT COUNT(*) FROM materiais WHERE quantidade_estoque <= estoque_minimo", conn).iloc[0, 0]
        req_pendentes = pd.read_sql_query("SELECT COUNT(*) FROM requisicoes WHERE status = 'Pendente'", conn).iloc[0, 0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estoque", f"{total_materiais}", "Itens cadastrados")
    c2.metric("Compras", f"{pedidos_andamento}", "Pedidos em andamento")
    c3.metric("Atenção", f"{abaixo_minimo}", "Itens abaixo do mínimo", delta_color="inverse")
    c4.metric("Solicitações", f"{req_pendentes}", "Aguardando aprovação")

    st.divider()
    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.subheader("🚨 Alertas de Reposição & Validade")
        with sqlite3.connect(DB_NAME) as conn:
            df_alertas = pd.read_sql_query("""
                SELECT codigo, descricao, quantidade_estoque, estoque_minimo, validade 
                FROM materiais 
                WHERE quantidade_estoque <= estoque_minimo OR validade <= DATE('now', '+30 days')
            """, conn)
        if not df_alertas.empty:
            st.dataframe(df_alertas, use_container_width=True)
        else:
            st.success("Sem alertas críticos no momento.")

        st.subheader("⏳ Pendências de Compras")
        with sqlite3.connect(DB_NAME) as conn:
            df_pendencias = pd.read_sql_query("""
                SELECT r.id as Req_ID, m.descricao as Material, r.quantidade, r.prioridade, r.status
                FROM requisicoes r
                JOIN materiais m ON m.id = r.material_id
                WHERE r.status IN ('Pendente', 'Em Cotação')
            """, conn)
        st.dataframe(df_pendencias, use_container_width=True)

    with col_dir:
        st.subheader("💰 Resumo Financeiro (Compras no Mês)")
        with sqlite3.connect(DB_NAME) as conn:
            df_gastos = pd.read_sql_query("""
                SELECT m.categoria, SUM(p.valor_total) as Total_Gasto
                FROM pedidos_compra p
                JOIN materiais m ON m.id = p.material_id
                WHERE strftime('%Y-%m', p.criado_em) = strftime('%Y-%m', 'now')
                GROUP BY m.categoria
            """, conn)
        if not df_gastos.empty:
            st.bar_chart(df_gastos.set_index('categoria'))
        else:
            st.info("Nenhuma compra efetuada este mês.")

        st.subheader("🔄 Últimas Movimentações")
        with sqlite3.connect(DB_NAME) as conn:
            df_movs = pd.read_sql_query("""
                SELECT m.descricao as Material, mov.tipo, mov.quantidade, mov.data_movimentacao 
                FROM movimentacoes_estoque mov
                JOIN materiais m ON m.id = mov.material_id
                ORDER BY mov.data_movimentacao DESC LIMIT 5
            """, conn)
        st.dataframe(df_movs, use_container_width=True)

# ==========================================
# 02. REQUIÇÕES DE COMPRA
# ==========================================
elif menu_opcao == "02. Requisições de Compra":
    st.title("📋 Requisições de Compra")
    st.caption("Abertura, justificativas e aprovação de solicitações.")

    tab1, tab2 = st.tabs(["➕ Nova Solicitação", "🔍 Gestão de Solicitações"])

    with tab1:
        with sqlite3.connect(DB_NAME) as conn:
            df_mats = pd.read_sql_query("SELECT id, codigo, descricao, quantidade_estoque FROM materiais", conn)

        if df_mats.empty:
            st.warning("Cadastre materiais no módulo Catálogo de Materiais primeiro.")
        else:
            with st.form("form_nova_req"):
                c1, c2 = st.columns(2)
                with c1:
                    mat_selecionado = st.selectbox("Material", df_mats['descricao'].tolist())
                    mat_row = df_mats[df_mats['descricao'] == mat_selecionado].iloc[0]
                    st.info(f"Código: **{mat_row['codigo']}** | Saldo atual: **{mat_row['quantidade_estoque']}**")
                    quantidade = st.number_input("Quantidade Solicitação", min_value=1, step=1)
                with c2:
                    prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Urgente"])
                    setor = st.text_input("Setor Solicitante", value=user_info['setor'])
                
                justificativa = st.text_area("Justificativa")
                
                if st.form_submit_button("🚀 Registrar Solicitação"):
                    if not justificativa.strip():
                        st.error("Informe a justificativa.")
                    else:
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO requisicoes (solicitante_id, setor, material_id, quantidade, justificativa, prioridade)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (user_info['id'], setor, int(mat_row['id']), quantidade, justificativa.strip(), prioridade))
                            conn.commit()
                        st.success("Solicitação gravada!")
                        st.rerun()

    with tab2:
        with sqlite3.connect(DB_NAME) as conn:
            df_reqs = pd.read_sql_query("""
                SELECT r.id, u.nome as Solicitante, r.setor, m.descricao as Material, r.quantidade, 
                       r.prioridade, r.justificativa, r.status, r.criado_em 
                FROM requisicoes r
                JOIN usuarios u ON u.id = r.solicitante_id
                JOIN materiais m ON m.id = r.material_id
                ORDER BY r.id DESC
            """, conn)
        st.dataframe(df_reqs, use_container_width=True)

        if user_info['role'] == 'admin':
            st.divider()
            st.subheader("⚡ Análise e Aprovação")
            reqs_pendentes = df_reqs[df_reqs['status'] == 'Pendente']
            if not reqs_pendentes.empty:
                req_id_aprov = st.selectbox("Aprovar/Rejeitar Solicitação ID", reqs_pendentes['id'].tolist())
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Aprovar Solicitação", use_container_width=True):
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE requisicoes SET status = 'Aprovada', aprovador_id = ?, data_aprovacao = CURRENT_TIMESTAMP WHERE id = ?", (user_info['id'], req_id_aprov))
                            conn.commit()
                        st.success(f"Solicitação #{req_id_aprov} Aprovada.")
                        st.rerun()
                with c2:
                    if st.button("❌ Rejeitar Solicitação", use_container_width=True):
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE requisicoes SET status = 'Rejeitada', aprovador_id = ?, data_aprovacao = CURRENT_TIMESTAMP WHERE id = ?", (user_info['id'], req_id_aprov))
                            conn.commit()
                        st.warning(f"Solicitação #{req_id_aprov} Rejeitada.")
                        st.rerun()

# ==========================================
# 03. GESTÃO DE COMPRAS
# ==========================================
elif menu_opcao == "03. Gestão de Compras":
    st.title("🛍️ Gestão de Compras")
    st.caption("Cotações, comparativos e emissão de Pedidos de Compra.")

    tab1, tab2, tab3 = st.tabs(["📑 Registrar Cotação", "⚖️ Selecionar Cotação & Emitir Pedido", "📦 Pedidos de Compra"])

    with tab1:
        with sqlite3.connect(DB_NAME) as conn:
            df_req_aprovadas = pd.read_sql_query("""
                SELECT r.id, m.descricao as Material, r.quantidade 
                FROM requisicoes r
                JOIN materiais m ON m.id = r.material_id
                WHERE r.status IN ('Aprovada', 'Em Cotação')
            """, conn)
            df_fornecedores = pd.read_sql_query("SELECT id, razao_social FROM fornecedores", conn)

        if df_req_aprovadas.empty:
            st.info("Sem solicitações aprovadas pendentes de cotação.")
        elif df_fornecedores.empty:
            st.warning("Cadastre fornecedores primeiro.")
        else:
            with st.form("form_cotacao"):
                req_sel = st.selectbox("Solicitação Aprovada ID", df_req_aprovadas['id'].tolist())
                forn_sel = st.selectbox("Fornecedor", df_fornecedores['razao_social'].tolist())
                forn_id = df_fornecedores[df_fornecedores['razao_social'] == forn_sel]['id'].values[0]
                
                c1, c2 = st.columns(2)
                with c1:
                    preco_unit = st.number_input("Preço Unitário (R$)", min_value=0.01, format="%.2f")
                with c2:
                    prazo_dias = st.number_input("Prazo de Entrega (Dias)", min_value=1, step=1)
                obs = st.text_input("Observação")

                if st.form_submit_button("💾 Gravar Cotação"):
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO cotacoes (requisicao_id, fornecedor_id, preco_unitario, prazo_entrega_dias, observacao) VALUES (?, ?, ?, ?, ?)", (req_sel, int(forn_id), preco_unit, prazo_dias, obs))
                        cursor.execute("UPDATE requisicoes SET status = 'Em Cotação' WHERE id = ?", (req_sel,))
                        conn.commit()
                    st.success("Cotação adicionada!")
                    st.rerun()

    with tab2:
        with sqlite3.connect(DB_NAME) as conn:
            df_cotacoes = pd.read_sql_query("""
                SELECT c.id as Cotacao_ID, c.requisicao_id, m.id as Material_ID, m.descricao as Material, 
                       f.razao_social as Fornecedor, f.id as Fornecedor_ID, r.quantidade, 
                       c.preco_unitario, (r.quantidade * c.preco_unitario) as Total, c.prazo_entrega_dias
                FROM cotacoes c
                JOIN requisicoes r ON r.id = c.requisicao_id
                JOIN materiais m ON m.id = r.material_id
                JOIN fornecedores f ON f.id = c.fornecedor_id
                WHERE r.status = 'Em Cotação'
            """, conn)

        if df_cotacoes.empty:
            st.info("Sem cotações pendentes de emissão.")
        else:
            st.dataframe(df_cotacoes, use_container_width=True)
            cot_vencedora = st.selectbox("Selecione Cotação para Pedido", df_cotacoes['Cotacao_ID'].tolist())
            
            if st.button("🛒 Emitir Pedido de Compra"):
                cot_row = df_cotacoes[df_cotacoes['Cotacao_ID'] == cot_vencedora].iloc[0]
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO pedidos_compra (requisicao_id, cotacao_id, fornecedor_id, material_id, quantidade, preco_unitario, valor_total, usuario_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (int(cot_row['requisicao_id']), int(cot_row['Cotacao_ID']), int(cot_row['Fornecedor_ID']), 
                          int(cot_row['Material_ID']), int(cot_row['quantidade']), float(cot_row['preco_unitario']), 
                          float(cot_row['Total']), user_info['id']))
                    cursor.execute("UPDATE requisicoes SET status = 'Atendida' WHERE id = ?", (int(cot_row['requisicao_id']),))
                    conn.commit()
                st.success("Pedido de compra emitido com sucesso!")
                st.rerun()

    with tab3:
        with sqlite3.connect(DB_NAME) as conn:
            df_pedidos = pd.read_sql_query("""
                SELECT p.id as Pedido_ID, m.descricao as Material, f.razao_social as Fornecedor, 
                       p.quantidade, p.preco_unitario, p.valor_total, p.status, p.criado_em 
                FROM pedidos_compra p
                JOIN materiais m ON m.id = p.material_id
                JOIN fornecedores f ON f.id = p.fornecedor_id
                ORDER BY p.id DESC
            """, conn)
        st.dataframe(df_pedidos, use_container_width=True)

# ==========================================
# 04. CONTROLE DE ESTOQUE
# ==========================================
elif menu_opcao == "04. Controle de Estoque":
    st.title("📦 Controle de Estoque")
    st.caption("Recebimento com conferência, saídas vinculadas e inventários.")

    tab1, tab2, tab3 = st.tabs(["📥 Recebimento & Conferência", "📤 Entrega / Saída", "🛠️ Ajustes & Inventário"])

    with tab1:
        with sqlite3.connect(DB_NAME) as conn:
            df_pedidos_trans = pd.read_sql_query("""
                SELECT p.id as Pedido_ID, m.id as Material_ID, m.descricao as Material, 
                       p.quantidade, p.preco_unitario, f.razao_social as Fornecedor
                FROM pedidos_compra p
                JOIN materiais m ON m.id = p.material_id
                JOIN fornecedores f ON f.id = p.fornecedor_id
                WHERE p.status IN ('Emitido', 'Em Transporte')
            """, conn)

        if df_pedidos_trans.empty:
            st.info("Nenhum pedido aguardando conferência.")
        else:
            with st.form("form_rec"):
                ped_sel = st.selectbox("Pedido em Trânsito ID", df_pedidos_trans['Pedido_ID'].tolist())
                ped_row = df_pedidos_trans[df_pedidos_trans['Pedido_ID'] == ped_sel].iloc[0]
                
                st.info(f"Item: **{ped_row['Material']}** | Qtd Esperada: **{ped_row['quantidade']}**")
                c1, c2 = st.columns(2)
                with c1:
                    nf = st.text_input("Número Nota Fiscal")
                    qtd_rec = st.number_input("Qtd Conferida", min_value=1, value=int(ped_row['quantidade']))
                with c2:
                    div = st.checkbox("Teve divergência?")
                    obs_div = st.text_area("Observação Divergência") if div else ""

                if st.form_submit_button("✅ Efetuar Entrada no Estoque"):
                    if not nf.strip():
                        st.error("Insira o número da Nota Fiscal.")
                    else:
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO recebimentos (pedido_id, numero_nota_fiscal, quantidade_recebida, tem_divergencia, observacao_divergencia, responsavel_id) VALUES (?, ?, ?, ?, ?, ?)",
                                           (ped_sel, nf, qtd_rec, 1 if div else 0, obs_div, user_info['id']))
                            cursor.execute("UPDATE materiais SET quantidade_estoque = quantidade_estoque + ? WHERE id = ?", (qtd_rec, int(ped_row['Material_ID'])))
                            cursor.execute("INSERT INTO movimentacoes_estoque (material_id, tipo, quantidade, preco_unitario, motivo, usuario_id) VALUES (?, 'ENTRADA', ?, ?, ?, ?)",
                                           (int(ped_row['Material_ID']), qtd_rec, float(ped_row['preco_unitario']), f"NF: {nf}", user_info['id']))
                            cursor.execute("UPDATE pedidos_compra SET status = 'Concluído' WHERE id = ?", (ped_sel,))
                            conn.commit()
                        st.success("Estoque atualizado e recebimento conferido!")
                        st.rerun()

    with tab2:
        with sqlite3.connect(DB_NAME) as conn:
            df_mats_disponiveis = pd.read_sql_query("SELECT id, descricao, quantidade_estoque, preco_custo FROM materiais WHERE quantidade_estoque > 0", conn)

        if df_mats_disponiveis.empty:
            st.warning("Sem estoque disponível para saída.")
        else:
            with st.form("form_saida_mat"):
                c1, c2 = st.columns(2)
                with c1:
                    mat_saida = st.selectbox("Material para Baixa", df_mats_disponiveis['descricao'].tolist())
                    m_row = df_mats_disponiveis[df_mats_disponiveis['descricao'] == mat_saida].iloc[0]
                    qtd_s = st.number_input("Quantidade Baixa", min_value=1, max_value=int(m_row['quantidade_estoque']))
                with c2:
                    setor_dest = st.text_input("Setor de Destino")
                    resp_ret = st.text_input("Responsável Retirada")

                if st.form_submit_button("📤 Registrar Saída"):
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE materiais SET quantidade_estoque = quantidade_estoque - ? WHERE id = ?", (qtd_s, int(m_row['id'])))
                        cursor.execute("INSERT INTO movimentacoes_estoque (material_id, tipo, quantidade, preco_unitario, motivo, usuario_id) VALUES (?, 'SAIDA', ?, ?, ?, ?)",
                                       (int(m_row['id']), qtd_s, float(m_row['preco_custo']), f"Entrega {resp_ret} ({setor_dest})", user_info['id']))
                        cursor.execute("INSERT INTO entregas (material_id, quantidade, setor_destino, responsavel_retirada, usuario_entrega_id) VALUES (?, ?, ?, ?, ?)",
                                       (int(m_row['id']), qtd_s, setor_dest, resp_ret, user_info['id']))
                        conn.commit()
                    st.success("Saída de estoque processada.")
                    st.rerun()

    with tab3:
        with sqlite3.connect(DB_NAME) as conn:
            df_mats_todos = pd.read_sql_query("SELECT id, descricao, quantidade_estoque, preco_custo FROM materiais", conn)

        with st.form("form_ajuste_inv"):
            mat_ajust = st.selectbox("Material para Ajuste", df_mats_todos['descricao'].tolist())
            maj_row = df_mats_todos[df_mats_todos['descricao'] == mat_ajust].iloc[0]
            
            c1, c2 = st.columns(2)
            with c1:
                saldo_apurado = st.number_input("Saldo Físico Real Apurado", min_value=0, value=int(maj_row['quantidade_estoque']))
            with c2:
                motivo = st.text_input("Justificativa Obrigatória de Ajuste")

            if st.form_submit_button("🛠️ Salvar Ajuste"):
                if not motivo.strip():
                    st.error("Informe a justificativa.")
                else:
                    dif = saldo_apurado - maj_row['quantidade_estoque']
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE materiais SET quantidade_estoque = ? WHERE id = ?", (saldo_apurado, int(maj_row['id'])))
                        cursor.execute("INSERT INTO movimentacoes_estoque (material_id, tipo, quantidade, preco_unitario, motivo, usuario_id) VALUES (?, 'AJUSTE', ?, ?, ?, ?)",
                                       (int(maj_row['id']), dif, float(maj_row['preco_custo']), motivo, user_info['id']))
                        conn.commit()
                    st.success("Ajuste registrado.")
                    st.rerun()

# ==========================================
# 05. CATÁLOGO DE MATERIAIS
# ==========================================
elif menu_opcao == "05. Catálogo de Materiais":
    st.title("📦 Catálogo de Materiais")
    st.caption("Cadastro, unidades, lote, validade e estoques mínimos.")

    tab1, tab2 = st.tabs(["➕ Novo Material", "📋 Itens Cadastrados"])

    with tab1:
        with st.form("form_cad_mat"):
            c1, c2, c3 = st
