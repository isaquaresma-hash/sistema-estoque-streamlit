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
        
        # Cargas Iniciais Padrão
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
# UTILITÁRIOS DE EXPORTAÇÃO (EXCEL & PDF)
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
# INTERFACE PRINCIPAL & MENU LATERAL
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
# MÓDULO 01: PAINEL DE CONTROLE (DASHBOARD)
# ==========================================
if menu_opcao == "01. Painel de Controle":
    st.title("📊 Painel de Controle")
    st.caption("Visão geral estratégica, alertas críticos e pendências operacionais.")

    with sqlite3.connect(DB_NAME) as conn:
        total_materiais = pd.read_sql_query("SELECT COUNT(*) FROM materiais", conn).iloc[0, 0]
        pedidos_andamento = pd.read_sql_query("SELECT COUNT(*) FROM pedidos_compra WHERE status IN ('Emitido', 'Em Transporte')", conn).iloc[0, 0]
        abaixo_minimo = pd.read_sql_query("SELECT COUNT(*) FROM materiais WHERE quantidade_estoque <= estoque_minimo", conn).iloc[0, 0]
        req_pendentes = pd.read_sql_query("SELECT COUNT(*) FROM requisicoes WHERE status = 'Pendente'", conn).iloc[0, 0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Itens Cadastrados", f"{total_materiais}", help="Total de materiais no catálogo")
    c2.metric("Pedidos em Andamento", f"{pedidos_andamento}", help="Pedidos emitidos ou em transporte")
    c3.metric("Itens Abaixo do Mínimo", f"{abaixo_minimo}", delta="- Alerta de Reposição" if abaixo_minimo > 0 else "Estoque OK", delta_color="inverse")
    c4.metric("Solicitações Pendentes", f"{req_pendentes}", help="Aguardando aprovação da gestão")

    st.divider()

    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.subheader("🚨 Alertas de Estoque Mínimo & Validades")
        with sqlite3.connect(DB_NAME) as conn:
            df_alertas = pd.read_sql_query("""
                SELECT codigo, descricao, quantidade_estoque, estoque_minimo, validade 
                FROM materiais 
                WHERE quantidade_estoque <= estoque_minimo OR validade <= DATE('now', '+30 days')
            """, conn)
        
        if not df_alertas.empty:
            st.dataframe(df_alertas, use_container_width=True)
        else:
            st.success("Nenhum alerta crítico de estoque no momento.")

        st.subheader("⏳ Pendências de Compras & Aprovações")
        with sqlite3.connect(DB_NAME) as conn:
            df_pendencias = pd.read_sql_query("""
                SELECT r.id as Req_ID, m.descricao as Material, r.quantidade, r.prioridade, r.status
                FROM requisicoes r
                JOIN materiais m ON m.id = r.material_id
                WHERE r.status IN ('Pendente', 'Em Cotação')
            """, conn)
        st.dataframe(df_pendencias, use_container_width=True)

    with col_dir:
        st.subheader("💰 Resumo Financeiro de Compras (Mês Atual)")
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
            st.info("Nenhuma compra efetuada no mês corrente.")

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
# MÓDULO 02: REQUIÇÕES DE COMPRA
# ==========================================
elif menu_opcao == "02. Requisições de Compra":
    st.title("📋 Requisições de Compra")
    st.caption("Abertura de solicitações, justificativas e esteira de aprovação.")

    tab1, tab2 = st.tabs(["➕ Nova Solicitação", "🔍 Minhas & Todas Solicitações"])

    with tab1:
        with sqlite3.connect(DB_NAME) as conn:
            df_mats = pd.read_sql_query("SELECT id, codigo, descricao, quantidade_estoque FROM materiais", conn)

        if df_mats.empty:
            st.warning("Nenhum material cadastrado no catálogo. Cadastre materiais primeiro.")
        else:
            with st.form("form_nova_req"):
                c1, c2 = st.columns(2)
                with c1:
                    mat_selecionado = st.selectbox("Selecione o Material", df_mats['descricao'].tolist())
                    mat_row = df_mats[df_mats['descricao'] == mat_selecionado].iloc[0]
                    st.info(f"Código: **{mat_row['codigo']}** | Saldo em estoque: **{mat_row['quantidade_estoque']}**")
                    quantidade = st.number_input("Quantidade Necessária", min_value=1, step=1)
                with c2:
                    prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Urgente"])
                    setor = st.text_input("Setor Solicitante", value=user_info['setor'])
                
                justificativa = st.text_area("Justificativa Detalhada da Necessidade")
                
                if st.form_submit_button("🚀 Enviar Requisição"):
                    if not justificativa.strip():
                        st.error("A justificativa é obrigatória.")
                    else:
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO requisicoes (solicitante_id, setor, material_id, quantidade, justificativa, prioridade)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (user_info['id'], setor, int(mat_row['id']), quantidade, justificativa.strip(), prioridade))
                            conn.commit()
                        st.success("Requisição aberta com sucesso!")
                        st.rerun()

    with tab2:
        with sqlite3.connect(DB_NAME) as conn:
            query = """
                SELECT r.id, u.nome as Solicitante, r.setor, m.descricao as Material, r.quantidade, 
                       r.prioridade, r.justificativa, r.status, r.criado_em 
                FROM requisicoes r
                JOIN usuarios u ON u.id = r.solicitante_id
                JOIN materiais m ON m.id = r.material_id
                ORDER BY r.id DESC
            """
            df_reqs = pd.read_sql_query(query, conn)

        st.dataframe(df_reqs, use_container_width=True)

        if user_info['role'] == 'admin':
            st.divider()
            st.subheader("⚡ Painel de Aprovação (Gestão)")
            
            reqs_pendentes = df_reqs[df_reqs['status'] == 'Pendente']
            if not reqs_pendentes.empty:
                req_id_aprov = st.selectbox("Selecione a Requisição para Avaliar", reqs_pendentes['id'].tolist())
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Aprovar Solicitação", use_container_width=True):
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE requisicoes 
                                SET status = 'Aprovada', aprovador_id = ?, data_aprovacao = CURRENT_TIMESTAMP 
                                WHERE id = ?
                            """, (user_info['id'], req_id_aprov))
                            conn.commit()
                        st.success(f"Requisição #{req_id_aprov} APROVADA!")
                        st.rerun()
                with c2:
                    if st.button("❌ Rejeitar Solicitação", use_container_width=True):
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE requisicoes 
                                SET status = 'Rejeitada', aprovador_id = ?, data_aprovacao = CURRENT_TIMESTAMP 
                                WHERE id = ?
                            """, (user_info['id'], req_id_aprov))
                            conn.commit()
                        st.warning(f"Requisição #{req_id_aprov} REJEITADA.")
                        st.rerun()
            else:
                st.info("Nenhuma requisição pendente de aprovação.")

# ==========================================
# MÓDULO 03: GESTÃO DE COMPRAS
# ==========================================
elif menu_opcao == "03. Gestão de Compras":
    st.title("🛍️ Gestão de Compras")
    st.caption("Cotações de fornecedores, comparativos e emissão de Pedidos de Compra.")

    tab1, tab2, tab3 = st.tabs(["📑 Registrar Cotação", "⚖️ Comparativo & Emitir Pedido", "📦 Pedidos Emitidos"])

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
            st.info("Nenhuma requisição aprovada aguardando cotação.")
        elif df_fornecedores.empty:
            st.warning("Nenhum fornecedor cadastrado. Cadastre fornecedores no Módulo 06.")
        else:
            with st.form("form_cotacao"):
                req_sel = st.selectbox("Selecione a Requisição Aprovada", df_req_aprovadas['id'].tolist(), 
                                      format_func=lambda x: f"Req #{x} - {df_req_aprovadas[df_req_aprovadas['id']==x]['Material'].values[0]}")
                forn_sel = st.selectbox("Fornecedor Cotação", df_fornecedores['razao_social'].tolist())
                forn_id = df_fornecedores[df_fornecedores['razao_social'] == forn_sel]['id'].values[0]
                
                c1, c2 = st.columns(2)
                with c1:
                    preco_unit = st.number_input("Preço Unitário Cotado (R$)", min_value=0.01, format="%.2f")
                with c2:
                    prazo_dias = st.number_input("Prazo de Entrega (em Dias)", min_value=1, step=1)
                    
                obs = st.text_input("Observações Comerciais")
                
                if st.form_submit_button("💾 Salvar Cotação"):
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO cotacoes (requisicao_id, fornecedor_id, preco_unitario, prazo_entrega_dias, observacao)
                            VALUES (?, ?, ?, ?, ?)
                        """, (req_sel, int(forn_id), preco_unit, prazo_dias, obs))
                        cursor.execute("UPDATE requisicoes SET status = 'Em Cotação' WHERE id = ?", (req_sel,))
                        conn.commit()
                    st.success("Cotação inserida com sucesso!")
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
            st.info("Não há cotações pendentes de análise para emissão de pedido.")
        else:
            st.subheader("💡 Mapa Comparativo de Preços")
            st.dataframe(df_cotacoes, use_container_width=True)

            cotacao_vencedora_id = st.selectbox("Selecione a Cotação Vencedora", df_cotacoes['Cotacao_ID'].tolist())
            
            if st.button("🛒 Gerar Pedido de Compra Oficial"):
                cot_row = df_cotacoes[df_cotacoes['Cotacao_ID'] == cotacao_vencedora_id].iloc[0]
                
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
                st.success(f"Pedido de Compra gerado com sucesso! (Vincular ao recebimento posteriormente)")
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
# MÓDULO 04: CONTROLE DE ESTOQUE
# ==========================================
elif menu_opcao == "04. Controle de Estoque":
    st.title("📦 Controle de Estoque")
    st.caption("Conferência de recebimentos, saídas operacionais e ajustes de inventário.")

    tab1, tab2, tab3 = tab_conferência, tab_saida, tab_ajuste = st.tabs([
        "📥 Conferência e Recebimento", "📤 Saída / Entrega ao Solicitante", "🛠️ Ajuste de Inventário"
    ])

    with tab1:
        st.subheader("Recebimento Físico e Fiscal (Conferência)")
        with sqlite3.connect(DB_NAME) as conn:
            df_pedidos_pendentes = pd.read_sql_query("""
                SELECT p.id as Pedido_ID, m.id as Material_ID, m.descricao as Material, 
                       p.quantidade, p.preco_unitario, f.razao_social as Fornecedor
                FROM pedidos_compra p
                JOIN materiais m ON m.id = p.material_id
                JOIN fornecedores f ON f.id = p.fornecedor_id
                WHERE p.status IN ('Emitido', 'Em Transporte')
            """, conn)

        if df_pedidos_pendentes.empty:
            st.info("Nenhum pedido de compra aguardando recebimento/conferência.")
        else:
            with st.form("form_recebimento"):
                ped_id_sel = st.selectbox("Selecione o Pedido em Trânsito", df_pedidos_pendentes['Pedido_ID'].tolist())
                ped_row = df_pedidos_pendentes[df_pedidos_pendentes['Pedido_ID'] == ped_id_sel].iloc[0]
                
                st.info(f"Item: **{ped_row['Material']}** | Qtd Pedida: **{ped_row['quantidade']}**")
                
                c1, c2 = st.columns(2)
                with c1:
                    nota_fiscal = st.text_input("Número da Nota Fiscal (NF-e)")
                    qtd_recebida = st.number_input("Quantidade Conferida e Entregue", min_value=1, value=int(ped_row['quantidade']))
                with c2:
                    divergencia = st.checkbox("Existe Divergência?")
                    obs_div = st.text_area("Observações de Divergência/Qualidade") if divergencia else ""

                if st.form_submit_button("✅ Concluir Conferência & Dar Entrada"):
                    if not nota_fiscal.strip():
                        st.error("Número da Nota Fiscal é obrigatório.")
                    else:
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            # 1. Registra Recebimento
                            cursor.execute("""
                                INSERT INTO recebimentos (pedido_id, numero_nota_fiscal, quantidade_recebida, tem_divergencia, observacao_divergencia, responsavel_id)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (ped_id_sel, nota_fiscal, qtd_recebida, 1 if divergencia else 0, obs_div, user_info['id']))
                            
                            # 2. Atualiza Saldo do Estoque
                            cursor.execute("UPDATE materiais SET quantidade_estoque = quantidade_estoque + ? WHERE id = ?", (qtd_recebida, int(ped_row['Material_ID'])))
                            
                            # 3. Registra Movimentação de Entrada
                            cursor.execute("""
                                INSERT INTO movimentacoes_estoque (material_id, tipo, quantidade, preco_unitario, motivo, usuario_id)
                                VALUES (?, 'ENTRADA', ?, ?, ?, ?)
                            """, (int(ped_row['Material_ID']), qtd_recebida, float(ped_row['preco_unitario']), f"NF: {nota_fiscal}", user_info['id']))
                            
                            # 4. Atualiza Status do Pedido
                            cursor.execute("UPDATE pedidos_compra SET status = 'Concluído' WHERE id = ?", (ped_id_sel,))
                            conn.commit()
                        st.success("Recebimento concluído com sucesso e saldo atualizado!")
                        st.rerun()

    with tab2:
        st.subheader("Dar Saída / Entregar ao Solicitante")
        with sqlite3.connect(DB_NAME) as conn:
            df_mats = pd.read_sql_query("SELECT id, descricao, quantidade_estoque, preco_custo FROM materiais WHERE quantidade_estoque > 0", conn)
            
        if df_mats.empty:
            st.warning("Nenhum material disponível em estoque para dar saída.")
        else:
            with st.form("form_saida"):
                c1, c2 = st.columns(2)
                with c1:
                    mat_sel = st.selectbox("Selecione o Material para Baixa", df_mats['descricao'].tolist())
                    mat_row = df_mats[df_mats['descricao'] == mat_sel].iloc[0]
                    st.info(f"Saldo Atual: **{mat_row['quantidade_estoque']}** unidades")
                    qtd_saida = st.number_input("Quantidade de Saída", min_value=1, max_value=int(mat_row['quantidade_estoque']))
                with c2:
                    setor_destino = st.text_input("Setor de Destino")
                    responsavel_retirada = st.text_input("Responsável pela Retirada")

                if st.form_submit_button("📤 Confirmar Saída"):
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        # Atualiza Saldo
                        cursor.execute("UPDATE materiais SET quantidade_estoque = quantidade_estoque - ? WHERE id = ?", (qtd_saida, int(mat_row['id'])))
                        # Movimentação
                        cursor.execute("""
                            INSERT INTO movimentacoes_estoque (material_id, tipo, quantidade, preco_unitario, motivo, usuario_id)
                            VALUES (?, 'SAIDA', ?, ?, ?, ?)
                        """, (int(mat_row['id']), qtd_saida, float(mat_row['preco_custo']), f"Entregue para {responsavel_retirada} ({setor_destino})", user_info['id']))
                        # Registro de Entrega
                        cursor.execute("""
                            INSERT INTO entregas (material_id, quantidade, setor_destino, responsavel_retirada, usuario_entrega_id)
                            VALUES (?, ?, ?, ?, ?)
                        """, (int(mat_row['id']), qtd_saida, setor_destino, responsavel_retirada, user_info['id']))
                        conn.commit()
                    st.success("Baixa em estoque realizada com sucesso!")
                    st.rerun()

    with tab3:
        st.subheader("Ajuste Manual e Inventário")
        st.warning("⚠️ Ajustes de saldo exigem obrigatoriamente justificativa para auditoria.")
        with sqlite3.connect(DB_NAME) as conn:
            df_mats_all = pd.read_sql_query("SELECT id, descricao, quantidade_estoque, preco_custo FROM materiais", conn)
            
        with st.form("form_ajuste"):
            mat_ajuste_sel = st.selectbox("Material para Ajuste", df_mats_all['descricao'].tolist())
            mat_aj_row = df_mats_all[df_mats_all['descricao'] == mat_ajuste_sel].iloc[0]
            
            c1, c2 = st.columns(2)
            with c1:
                novo_saldo = st.number_input("Novo Saldo Apurado (Físico)", min_value=0, value=int(mat_aj_row['quantidade_estoque']))
            with c2:
                motivo_ajuste = st.text_input("Motivo do Ajuste / Divergência de Inventário")
                
            if st.form_submit_button("🛠️ Aplicar Ajuste"):
                if not motivo_ajuste.strip():
                    st.error("A justificativa é obrigatória para efetuar ajustes.")
                else:
                    diferenca = novo_saldo - mat_aj_row['quantidade_estoque']
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE materiais SET quantidade_estoque = ? WHERE id = ?", (novo_saldo, int(mat_aj_row['id'])))
                        cursor.execute("""
                            INSERT INTO movimentacoes_estoque (material_id, tipo, quantidade, preco_unitario, motivo, usuario_id)
                            VALUES (?, 'AJUSTE', ?, ?, ?, ?)
                        """, (int(mat_aj_row['id']), diferenca, float(mat_aj_row['preco_custo']), motivo_ajuste, user_info['id']))
                        conn.commit()
                    st.success("Inventário ajustado e registrado no histórico de auditoria!")
                    st.rerun()

# ==========================================
# MÓDULO 05: CATÁLOGO DE MATERIAIS
# ==========================================
elif menu_opcao == "05. Catálogo de Materiais":
    st.title("📦 Catálogo de Materiais")
    st.caption("Cadastro padronizado, categorias, parâmetros de estoque mínimo e dados físicos.")

    tab1, tab2 = st.tabs(["➕ Cadastrar Material", "📋 Materiais Cadastrados"])

    with tab1:
        with st.form("form_cad_material"):
            c1, c2, c3 = st.columns(3)
            with c1:
                codigo = st.text_input("Código / SKU*", placeholder="MAT-001")
                descricao = st.text_input("Descrição Completa*")
                categoria = st.selectbox("Categoria", ["Escritório", "Informática", "Manutenção", "Limpeza", "EPIs", "Outros"])
            with c2:
                unidade = st.selectbox("Unidade de Medida", ["UN", "CX", "KG", "L", "PCT", "M"])
                marca_ref = st.text_input("Marca de Referência")
