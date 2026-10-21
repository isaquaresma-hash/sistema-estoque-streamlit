import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import base64
import os
from datetime import datetime
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

def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False, timeout=15)

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
# ESTILIZAÇÃO CSS CUSTOMIZADA
# ==========================================
css_code = """<style>
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid='stAppViewContainer'] { background-color: #F8FAFC !important; }
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1000px !important;
    }
    [data-testid='stSidebar'] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid='stSidebar'] * { color: #1E293B !important; }
    [data-testid="stElementToolbar"] { display: none !important; }
    
    .main-card-wrapper {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        padding: 2.5rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.02);
    }

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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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

        cursor.execute("PRAGMA table_info(usuarios)")
        colunas_existentes = [col[1] for col in cursor.fetchall()]
        if "role" not in colunas_existentes:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN role TEXT NOT NULL DEFAULT 'solicitante'")
        if "setor" not in colunas_existentes:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN setor TEXT DEFAULT 'Geral'")
        
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
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

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
        
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (nome, username, senha, role, setor) VALUES (?, ?, ?, ?, ?)",
                           ("Administrador Geral", "admin", hash_password("admin123"), "admin", "TI"))

        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'roze.peres@fnp.org.br'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (nome, username, senha, role, setor) VALUES (?, ?, ?, ?, ?)",
                           ("Roze Peres", "roze.peres@fnp.org.br", hash_password("fnp2026"), "admin", "Diretoria"))

        cursor.execute("SELECT COUNT(*) FROM materiais")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO materiais (codigo, descricao, categoria, unidade, quantidade_estoque, preco_custo) VALUES ('MAT-01', 'Papel A4', 'escritório', 'Resma', 35, 25.0)")
            cursor.execute("INSERT INTO materiais (codigo, descricao, categoria, unidade, quantidade_estoque, preco_custo) VALUES ('MAT-02', 'Caneta azul', 'escritório', 'Unidade', 120, 2.50)")
            cursor.execute("INSERT INTO materiais (codigo, descricao, categoria, unidade, quantidade_estoque, preco_custo) VALUES ('MAT-03', 'Detergente', 'limpeza', 'Frasco', 18, 4.80)")

        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao inicializar o banco de dados: {e}")

# Executa o banco de dados
init_db()

# ==========================================
# AUTENTICAÇÃO E SESSÃO
# ==========================================
def verificar_login(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, role, setor FROM usuarios WHERE username = ? AND senha = ?", 
                       (username.lower().strip(), hash_password(password)))
        resultado = cursor.fetchone()
        conn.close()
        return resultado
    except Exception as e:
        st.error(f"Erro ao verificar login: {e}")
        return None

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def login_screen():
    col1, col2, col3 = st.columns([0.8, 1.4, 0.8])
    with col2:
        st.markdown("<h3 style='text-align:center; color:#0F172A;'>SISTEMA DE COMPRAS E ESTOQUE</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#64748B;'>Informe suas credenciais para acessar.</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("✉️ E-mail ou Usuário", placeholder="usuario@empresa.org.br")
            password = st.text_input("🔒 Senha", type="password", placeholder="••••••••")
            submit_login = st.form_submit_button("➔ Entrar no Sistema", use_container_width=True)
            
            if submit_login:
                if not username or not password:
                    st.warning("Por favor, preencha o usuário e a senha.")
                else:
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

def logout():
    st.session_state["usuario_logado"] = None
    st.rerun()

# Se não estiver logado, exibe a tela de login
if not st.session_state["usuario_logado"]:
    login_screen()
    st.stop()

# ==========================================
# NAVEGAÇÃO LATERAL (SÓ EXIBIDA APÓS LOGIN)
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
# 05. CATÁLOGO DE MATERIAIS
# ==========================================
if menu_opcao == "05. Catálogo de Materiais":
    if "modo_material" not in st.session_state:
        st.session_state["modo_material"] = "lista"
    if "material_edicao" not in st.session_state:
        st.session_state["material_edicao"] = None

    st.markdown("<div class='main-card-wrapper'>", unsafe_allow_html=True)

    col_tit, col_act = st.columns([0.72, 0.28])
    with col_tit:
        st.markdown("<h2 style='margin:0; font-weight:800; color:#0F172A; font-size:1.6rem;'>Cadastro de materiais</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color:#64748B; font-size:0.95rem; margin-top:0.2rem; margin-bottom:1.8rem;'>Gerencie os itens do estoque</p>", unsafe_allow_html=True)
    
    with col_act:
        if st.session_state["modo_material"] == "lista":
            if st.button("+ Novo material", type="primary", use_container_width=True):
                st.session_state["material_edicao"] = None
                st.session_state["modo_material"] = "formulario"
                st.rerun()
        else:
            if st.button("⬅️ Voltar à Lista", use_container_width=True):
                st.session_state["modo_material"] = "lista"
                st.rerun()

    st.markdown("<hr style='border:0; border-top:1px solid #F1F5F9; margin-bottom:1.5rem;'>", unsafe_allow_html=True)

    if st.session_state["modo_material"] == "formulario":
        mat_edit = st.session_state["material_edicao"]
        st.subheader("Formulário de Material" if not mat_edit else "Editar Material")
        
        with st.form("form_material_custom"):
            c1, c2, c3 = st.columns(3)
            with c1:
                codigo = st.text_input("Código / SKU*", value=mat_edit['codigo'] if mat_edit else "")
                descricao = st.text_input("Nome do Material*", value=mat_edit['descricao'] if mat_edit else "")
                categoria = st.text_input("Categoria*", value=mat_edit['categoria'] if mat_edit else "escritório")
            with c2:
                unidade = st.text_input("Unidade (Ex: Resma, Unidade, Frasco)*", value=mat_edit['unidade'] if mat_edit else "Unidade")
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
                        conn = get_db_connection()
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
                        conn.close()
                        st.success("Material salvo com sucesso!")
                        st.session_state["modo_material"] = "lista"
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("O código de material já existe.")

    else:
        busca_termo = st.text_input("🔍", placeholder="Buscar material pelo nome...").strip().lower()
        st.markdown("<br>", unsafe_allow_html=True)

        try:
            conn = get_db_connection()
            query = "SELECT id, codigo, descricao, categoria, unidade, quantidade_estoque, preco_custo, estoque_minimo, marca_ref, localizacao FROM materiais"
            df_m = pd.read_sql_query(query, conn)
            conn.close()

            if df_m.empty:
                st.info("Nenhum material cadastrado.")
            else:
                if busca_termo:
                    df_m = df_m[df_m['descricao'].str.lower().str.contains(busca_termo) | df_m['categoria'].str.lower().str.contains(busca_termo)]

                if df_m.empty:
                    st.warning("Nenhum material encontrado com o termo informado.")
                else:
                    for _, row in df_m.iterrows():
                        st.markdown("<div class='item-card-box'>", unsafe_allow_html=True)
                        c_info, c_btn1, c_btn2 = st.columns([0.72, 0.18, 0.10])
                        
                        with c_info:
                            cat_formatted = str(row['categoria']).strip()
                            if not cat_formatted.lower().startswith("material"):
                                cat_text = f"Material de {cat_formatted.lower()}"
                            else:
                                cat_text = cat_formatted
                                
                            st.markdown(f"""
                                <p class='item-title-text'>{row['descricao']}</p>
                                <p class='item-sub-text'>{cat_text} · {row['unidade']} · Saldo: {row['quantidade_estoque']}</p>
                            """, unsafe_allow_html=True)

                        with c_btn1:
                            st.markdown("<div class='btn-edit-capsule'>", unsafe_allow_html=True)
                            if st.button("✏️ Editar", key=f"edit_{row['id']}", use_container_width=True):
                                st.session_state["material_edicao"] = row.to_dict()
                                st.session_state["modo_material"] = "formulario"
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)

                        with c_btn2:
                            st.markdown("<div class='btn-trash-circle'>", unsafe_allow_html=True)
                            if st.button("🗑️", key=f"del_{row['id']}", help="Excluir material"):
                                try:
                                    conn = get_db_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM materiais WHERE id = ?", (row['id'],))
                                    conn.commit()
                                    conn.close()
                                    st.success("Removido com sucesso!")
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    st.error("Não é possível excluir itens com histórico de movimentação.")
                            st.markdown("</div>", unsafe_allow_html=True)

                        st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Erro ao carregar materiais: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# OUTROS MÓDULOS
# ==========================================
elif menu_opcao == "01. Painel de Controle":
    st.subheader("01. Painel de controle")
    st.caption("Indicadores, alertas, pendências e resumo financeiro.")

elif menu_opcao == "02. Requisições de Compra":
    st.subheader("02. Requisições de compra")
    st.caption("Solicitações, justificativas, prioridades e aprovações.")

elif menu_opcao == "03. Gestão de Compras":
    st.subheader("03. Gestão de compras")
    st.caption("Cotações, pedidos, valores e acompanhamento de entregas.")

elif menu_opcao == "04. Controle de Estoque":
    st.subheader("04. Controle de estoque")
    st.caption("Entradas, saídas, saldo, transferências e inventário.")

elif menu_opcao == "06. Fornecedores":
    st.subheader("06. Fornecedores")
    st.caption("Cadastro, histórico de preços, prazos e desempenho.")

elif menu_opcao == "07. Documentos & Entregas":
    st.subheader("07. Documentos e aprovações")
    st.caption("Notas fiscais, comprovantes, autorizações e histórico.")

elif menu_opcao == "08. Relatórios e Indicadores":
    st.subheader("08. Relatórios e indicadores")
    st.caption("Consumo, gastos, economia, giro e previsões de reposição.")

elif menu_opcao == "👥 Gestão de Usuários" and user_info["role"] == "admin":
    st.title("👥 Controle de Acesso")
    st.caption("Cadastro e gestão de usuários.")
