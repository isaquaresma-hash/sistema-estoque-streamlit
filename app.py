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
# ESTILIZAÇÃO CSS CUSTOMIZADA (EXATA AO MODELO)
# ==========================================
css_code = """<style>
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid='stAppViewContainer'] { background-color: #F8FAFC !important; }
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1000px !important;
    }
    [data-testid='stSidebar'] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid='stSidebar'] * { color: #1E293B !important; }
    [data-testid="stElementToolbar"] { display: none !important; }
    
    /* Container Principal da Tela estilo Card */
    .main-card-wrapper {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        padding: 2.5rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.02);
    }

    /* Cartão do Item (Papel A4, Caneta Azul, etc.) */
    .item-card-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }
    .item-card-box:hover {
        border-color: #CBD5E1;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    .item-title-text {
        font-size: 1.2rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0 0 0.3rem 0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .item-sub-text {
        font-size: 0.92rem;
        color: #64748B;
        margin: 0;
        font-weight: 500;
    }

    /* Botão Principal Estilo Modelo (+ Novo material) */
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border-radius: 30px !important;
        padding: 0.55rem 1.4rem !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border: none !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #1E293B !important;
    }

    /* Botão Editar (Estilo Cápsula Branca) */
    .btn-edit-capsule button {
        background-color: #FFFFFF !important;
        color: #334155 !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 25px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.4rem 1.1rem !important;
    }
    .btn-edit-capsule button:hover {
        background-color: #F8FAFC !important;
        border-color: #CBD5E1 !important;
    }

    /* Botão Lixeira (Circulo com borda avermelhada) */
    .btn-trash-circle button {
        background-color: #FFFFFF !important;
        color: #EF4444 !important;
        border: 1px solid #FEE2E2 !important;
        border-radius: 50% !important;
        width: 42px !important;
        height: 42px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .btn-trash-circle button:hover {
        background-color: #FEF2F2 !important;
        border-color: #FCA5A5 !important;
    }

    /* Card de Perfil Sidebar */
    .user-profile-card {
        background-color: #0F172A;
        color: #FFFFFF;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1.2rem;
        border-left: 5px solid #2563EB;
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

        # Cadastra Dados Iniciais de Exemplo conforme o modelo se estiver vazio[cite: 3]
        cursor.execute("SELECT COUNT(*) FROM materiais")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO materiais (codigo, descricao, categoria, unidade, quantidade_estoque, preco_custo) VALUES ('MAT-01', 'Papel A4', 'escritório', 'Resma', 35, 25.0)")[cite: 3]
            cursor.execute("INSERT INTO materiais (codigo, descricao, categoria, unidade, quantidade_estoque, preco_custo) VALUES ('MAT-02', 'Caneta azul', 'escritório', 'Unidade', 120, 2.50)")[cite: 3]
            cursor.execute("INSERT INTO materiais (codigo, descricao, categoria, unidade, quantidade_estoque, preco_custo) VALUES ('MAT-03', 'Detergente', 'limpeza', 'Frasco', 18, 4.80)")[cite: 3]

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
                st.markdown("<h3 style='text-align:center; color:#0F172A;'>SISTEMA DE COMPRAS E ESTOQUE</h3>", unsafe_allow_html=True)
                
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
        
        header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
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
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=12, alignment=1, spaceAfter=8, textColor=colors.HexColor('#0F172A'))
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
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
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

menu_opcao = st.sidebar.radio("Navegação do Sistema", list(menu_map.keys()), index=4)

# ==========================================
# 05. CATÁLOGO DE MATERIAIS (REFEITO IDÊNTICO À IMAGEM)[cite: 3]
# ==========================================
if menu_opcao == "05. Catálogo de Materiais":
    
    if "modo_material" not in st.session_state:
        st.session_state["modo_material"] = "lista"
    if "material_edicao" not in st.session_state:
        st.session_state["material_edicao"] = None

    # ESTRUTURA DO CARD PRINCIPAL[cite: 3]
    st.markdown("<div class='main-card-wrapper'>", unsafe_allow_html=True)

    # 1. Cabeçalho: Título + Botão Preto Arredondado "+ Novo material"[cite: 3]
    col_tit, col_act = st.columns([0.72, 0.28])
    with col_tit:
        st.markdown("<h2 style='margin:0; font-weight:800; color:#0F172A; font-size:1.6rem;'>Cadastro de materiais</h2>", unsafe_allow_html=True)[cite: 3]
        st.markdown("<p style='color:#64748B; font-size:0.95rem; margin-top:0.2rem; margin-bottom:1.8rem;'>Gerencie os itens do estoque</p>", unsafe_allow_html=True)[cite: 3]
    
    with col_act:
        if st.session_state["modo_material"] == "lista":
            if st.button("+ Novo material", type="primary", use_container_width=True):[cite: 3]
                st.session_state["material_edicao"] = None
                st.session_state["modo_material"] = "formulario"
                st.rerun()
        else:
            if st.button("⬅️ Voltar à Lista", use_container_width=True):
                st.session_state["modo_material"] = "lista"
                st.rerun()

    st.markdown("<hr style='border:0; border-top:1px solid #F1F5F9; margin-bottom:1.5rem;'>", unsafe_allow_html=True)

    # 2. Formulário de Cadastro/Edição
    if st.session_state["modo_material"] == "formulario":
        mat_edit = st.session_state["material_edicao"]
        st.subheader("Formulário de Material" if not mat_edit else "Editar Material")
        
        with st.form("form_material_custom"):
            c1, c2, c3 = st.columns(3)
            with c1:
                codigo = st.text_input("Código / SKU*", value=mat_edit['codigo'] if mat_edit else "")
                descricao = st.text_input("Nome do Material*", value=mat_edit['descricao'] if mat_edit else "")
                categoria = st.text_input("Categoria*", value=mat_edit['categoria'] if mat_edit else "escritório")[cite: 3]
            with c2:
                unidade = st.text_input("Unidade (Ex: Resma, Unidade, Frasco)*", value=mat_edit['unidade'] if mat_edit else "Unidade")[cite: 3]
                marca = st.text_input("Marca de Referência", value=mat_edit['marca_ref'] if mat_edit else "")
                preco_custo = st.number_input("Preço de Custo (R$)", min_value=0.0, format="%.2f", value=float(mat_edit['preco_custo']) if mat_edit else 0.0)
            with c3:
                est_min = st.number_input("Estoque Mínimo", min_value=1, value=int(mat_edit['estoque_minimo']) if mat_edit else 5)
                localizacao = st.text_input("Localização Física", value=mat_edit['localizacao'] if mat_edit else "")
                qtd_inicial = st.number_input("Saldo em Estoque", min_value=0, value=int(mat_edit['quantidade_estoque']) if mat_edit else 0)

            if st.form_submit_button("💾 Salvar Material"):
                if not codigo.strip() or not descricao.strip():
                    st.error("Preencha os campos obrigatórios.")
                else:
                    try:
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            if mat_edit:
                                cursor.execute("""
                                    UPDATE materiais 
                                    SET codigo = ?, descricao = ?, categoria = ?, unidade = ?, marca_ref = ?, preco_custo = ?, estoque_minimo = ?, localizacao = ?, quantidade_estoque = ?
                                    WHERE id = ?
                                """, (codigo.strip(), descricao.strip(), categoria.strip(), unidade.strip(), marca, preco_custo, est_min, localizacao, qtd_inicial, mat_edit['id']))
                            else:
                                cursor.execute("""
                                    INSERT INTO materiais (codigo, descricao, categoria, unidade, marca_ref, preco_custo, quantidade_estoque, estoque_minimo, localizacao)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (codigo.strip(), descricao.strip(), categoria.strip(), unidade.strip(), marca, preco_custo, qtd_inicial, est_min, localizacao))
                            conn.commit()
                        st.success("Material salvo com sucesso!")
                        st.session_state["modo_material"] = "lista"
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("O código de material já existe.")

    # 3. Lista de Itens no Formato Exato do Protótipo[cite: 3]
    else:
        # Barra de Pesquisa com Ícone de Lupa[cite: 3]
        busca_termo = st.text_input("🔍", placeholder="Buscar material pelo nome...").strip().lower()[cite: 3]
        
        st.markdown("<br>", unsafe_allow_html=True)

        with sqlite3.connect(DB_NAME) as conn:
            query = "SELECT id, codigo, descricao, categoria, unidade, quantidade_estoque, preco_custo, estoque_minimo, marca_ref, localizacao FROM materiais"
            df_m = pd.read_sql_query(query, conn)

        if df_m.empty:
            st.info("Nenhum material cadastrado.")
        else:
            if busca_termo:
                df_m = df_m[df_m['descricao'].str.lower().str.contains(busca_termo) | df_m['categoria'].str.lower().str.contains(busca_termo)]

            if df_m.empty:
                st.warning("Nenhum material encontrado com o termo informado.")
            else:
                for _, row in df_m.iterrows():
                    st.markdown("<div class='item-card-box'>", unsafe_allow_html=True)[cite: 3]
                    
                    c_info, c_btn1, c_btn2 = st.columns([0.72, 0.18, 0.10])
                    
                    with c_info:
                        # Formatação do texto idêntica à imagem (Ex: "Material de escritório · Resma · Saldo: 35")[cite: 3]
                        cat_formatted = str(row['categoria']).strip()
                        if not cat_formatted.lower().startswith("material"):
                            cat_text = f"Material de {cat_formatted.lower()}"
                        else:
                            cat_text = cat_formatted
                            
                        st.markdown(f"""
                            <p class='item-title-text'>{row['descricao']}</p>
                            <p class='item-sub-text'>{cat_text} · {row['unidade']} · Saldo: {row['quantidade_estoque']}</p>
                        """, unsafe_allow_html=True)[cite: 3]

                    with c_btn1:
                        st.markdown("<div class='btn-edit-capsule'>", unsafe_allow_html=True)
                        if st.button("✏️ Editar", key=f"edit_{row['id']}", use_container_width=True):[cite: 3]
                            st.session_state["material_edicao"] = row.to_dict()
                            st.session_state["modo_material"] = "formulario"
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

                    with c_btn2:
                        st.markdown("<div class='btn-trash-circle'>", unsafe_allow_html=True)
                        if st.button("🗑️", key=f"del_{row['id']}", help="Excluir material"):[cite: 3]
                            try:
                                with sqlite3.connect(DB_NAME) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM materiais WHERE id = ?", (row['id'],))
                                    conn.commit()
                                st.success("Removido com sucesso!")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Não é possível excluir itens com histórico de movimentação.")
                        st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# OUTROS MÓDULOS
# ==========================================
elif menu_opcao == "01. Painel de Controle":
    st.subheader("01. Painel de controle")
    st.caption("Indicadores, alertas, pendências e resumo financeiro.")
    # (Visão mantida)

elif menu_opcao == "02. Requisições de Compra":
    st.subheader("02. Requisições de compra")
    st.caption("Solicitações, justificativas, prioridades e aprovações.")
    # (Visão mantida)

elif menu_opcao == "03. Gestão de Compras":
    st.subheader("03. Gestão de compras")
    st.caption("Cotações, pedidos, valores e acompanhamento de entregas.")
    # (Visão mantida)

elif menu_opcao == "04. Controle de Estoque":
    st.subheader("04. Controle de estoque")
    st.caption("Entradas, saídas, saldo, transferências e inventário.")
    # (Visão mantida)

elif menu_opcao == "06. Fornecedores":
    st.subheader("06. Fornecedores")
    st.caption("Cadastro, histórico de preços, prazos e desempenho.")
    # (Visão mantida)

elif menu_opcao == "07. Documentos & Entregas":
    st.subheader("07. Documentos e aprovações")
    st.caption("Notas fiscais, comprovantes, autorizações e histórico.")
    # (Visão mantida)

elif menu_opcao == "08. Relatórios e Indicadores":
    st.subheader("08. Relatórios e indicadores")
    st.caption("Consumo, gastos, economia, giro e previsões de reposição.")
    # (Visão mantida)

elif menu_opcao == "👥 Gestão de Usuários" and user_info["role"] == "admin":
    st.title("👥 Controle de Acesso")
    st.caption("Cadastro e gestão de usuários.")
    # (Visão mantida)
