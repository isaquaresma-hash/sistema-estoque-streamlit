import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import hmac
import secrets
import base64
import os
from datetime import datetime, date
from io import BytesIO
from xml.sax.saxutils import escape

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
# ESTILIZAÇÃO CSS MEHORADA
# ==========================================
css_code = """<style>
    /* Ocultar o cabeçalho superior nativo do Streamlit */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    [data-testid='stAppViewContainer'] {
        background-color: #F8FAFC !important;
    }

    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1200px !important;
    }

    /* Sidebar */
    [data-testid='stSidebar'] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid='stSidebar'] * {
        color: #103965 !important;
    }

    /* Ocultar a barra de ferramentas flutuante */
    [data-testid="stElementToolbar"] {
        display: none !important;
    }

    /* Container de Login e Cards */
    div[data-testid='stForm'], .custom-card {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        padding: 1.5rem !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03) !important;
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

    /* Estilização de Botões de Ação */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
</style>"""
st.markdown(css_code, unsafe_allow_html=True)

DB_NAME = "estoque_compras.db"

# ==========================================
# BANCO DE DADOS E CRIPTOGRAFIA
# ==========================================
def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return "pbkdf2_sha256$310000$" + salt.hex() + "$" + digest.hex()

def verificar_senha(password, senha_salva):
    if not senha_salva:
        return False
    if senha_salva.startswith("pbkdf2_sha256$"):
        try:
            _, iteracoes, salt_hex, digest_hex = senha_salva.split("$", 3)
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iteracoes)
            ).hex()
            return hmac.compare_digest(digest, digest_hex)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), senha_salva)

def inteiro_seguro(valor, padrao=0):
    try:
        if valor is None or pd.isna(valor):
            return padrao
        texto = str(valor).strip()
        if not texto:
            return padrao
        numero = float(texto.replace(",", "."))
        if not numero == numero or numero in (float("inf"), float("-inf")):
            return padrao
        return int(numero)
    except (TypeError, ValueError, OverflowError):
        return padrao

def mesclar_produtos_duplicados_db(cursor):
    """Detecta produtos duplicados sem diferenciar maiúsculas/minúsculas e une em um só."""
    cursor.execute("SELECT id, LOWER(nome) as nome_lower, nome, quantidade_estoque FROM produtos ORDER BY id ASC")
    produtos = cursor.fetchall()
    
    agrupados = {}
    for pid, nome_lower, nome_orig, qtd in produtos:
        if nome_lower not in agrupados:
            agrupados[nome_lower] = []
        agrupados[nome_lower].append((pid, nome_orig, inteiro_seguro(qtd)))
        
    for nome_lower, lista in agrupados.items():
        if len(lista) > 1:
            # Mantém o primeiro registro registrado (ID principal) e ajusta o nome para Title Case
            id_principal, _, _ = lista[0]
            nome_formatado = lista[0][1].strip().title()
            
            total_estoque = sum(item[2] for item in lista)
            
            # Atualiza produto principal com nome formatado e soma do estoque
            cursor.execute("UPDATE produtos SET nome = ?, quantidade_estoque = ? WHERE id = ?", 
                           (nome_formatado, total_estoque, id_principal))
            
            # Reatribui movimentações dos produtos duplicados para o ID principal
            for pid_duplicado, _, _ in lista[1:]:
                cursor.execute("UPDATE movimentacoes_estoque SET produto_id = ? WHERE produto_id = ?", 
                               (id_principal, pid_duplicado))
                cursor.execute("DELETE FROM produtos WHERE id = ?", (pid_duplicado,))

def init_db():
    with sqlite3.connect(DB_NAME, timeout=30) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, username TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'operador')")
        cursor.execute("CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL COLLATE NOCASE, codigo_barras TEXT, preco_custo REAL NOT NULL, quantidade_estoque INTEGER NOT NULL DEFAULT 0, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("CREATE TABLE IF NOT EXISTS movimentacoes_estoque (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER, tipo TEXT CHECK(tipo IN ('ENTRADA', 'SAIDA')), quantidade INTEGER NOT NULL, preco_unitario REAL NOT NULL, data_compra DATE, data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(produto_id) REFERENCES produtos(id))")

        # Corrige registros com saldos inválidos e funde duplicados por caixa alta/baixa
        cursor.execute("SELECT id, quantidade_estoque FROM produtos")
        for produto_id, quantidade_db in cursor.fetchall():
            quantidade_corrigida = inteiro_seguro(quantidade_db)
            if quantidade_db != quantidade_corrigida:
                cursor.execute("UPDATE produtos SET quantidade_estoque = ? WHERE id = ?", (quantidade_corrigida, produto_id))
        
        mesclar_produtos_duplicados_db(cursor)

        cursor.execute("PRAGMA table_info(movimentacoes_estoque)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'data_compra' not in columns:
            cursor.execute("ALTER TABLE movimentacoes_estoque ADD COLUMN data_compra DATE")
            cursor.execute("UPDATE movimentacoes_estoque SET data_compra = DATE(data_movimentacao) WHERE data_compra IS NULL")

        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)", ("Administrador", "admin", hash_password("admin123"), "admin"))

        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'roze.peres@fnp.org.br'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)", ("Roze Peres", "roze.peres@fnp.org.br", hash_password("fnp2026"), "admin"))
        conn.commit()

init_db()

# ==========================================
# AUTENTICAÇÃO E SESSÃO
# ==========================================
def verificar_login(username, password):
    username = (username or "").strip().lower()
    with sqlite3.connect(DB_NAME, timeout=30) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, role, senha FROM usuarios WHERE username = ?", (username,))
        user = cursor.fetchone()
        if not user or not verificar_senha(password, user[3]):
            return None
        if not user[3].startswith("pbkdf2_sha256$"):
            cursor.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (hash_password(password), user[0]))
            conn.commit()
        return user[0], user[1], user[2]

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def login_screen():
    col1, col2, col3 = st.columns([0.8, 1.4, 0.8])
    with col2:
        with st.form("login_form"):
            if img_base64:
                st.markdown(f"<img src='data:image/png;base64,{img_base64}' style='max-width:280px; width:100%; display:block; margin:0 auto 1rem auto;'>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='text-align:center; color:#0D47A1; margin-bottom:1rem;'>SISTEMA DE GESTÃO DE COMPRAS E ESTOQUE</h3>", unsafe_allow_html=True)
                
            st.markdown("<h3 style='color:#0D1B2A; margin-bottom:0.2rem;'>Bem-vindo(a)!</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color:#64748B; font-size:0.9rem; margin-bottom:1.5rem;'>Faça login para acessar o sistema.</p>", unsafe_allow_html=True)
            
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

def logout():
    st.session_state["usuario_logado"] = None
    st.rerun()

if not st.session_state["usuario_logado"]:
    login_screen()
    st.stop()

# ==========================================
# INTERFACE PRINCIPAL
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
# RELATÓRIOS EXCEL / PDF
# ==========================================
def gerar_excel_estilizado_bytes(df_exportar, nome_aba="Relatório"):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_exportar.to_excel(writer, index=False, sheet_name=nome_aba)
        workbook = writer.book
        worksheet = writer.sheets[nome_aba]
        
        header_fill = PatternFill(start_color="0D47A1", end_color="0D47A1", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        thin_border = Border(
            bottom=Side(style='thin', color='E0E0E0'),
            left=Side(style='thin', color='F0F0F0'),
            right=Side(style='thin', color='F0F0F0')
        )
        
        colunas_lista = list(df_exportar.columns)
        for col_num, col_name in enumerate(colunas_lista, 1):
            col_letter = get_column_letter(col_num)
            cell = worksheet.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
            nome_col_lower = str(col_name).lower()
            is_moeda = ("preço" in nome_col_lower or "custo" in nome_col_lower or "valor" in nome_col_lower or "diferença preço" in nome_col_lower)
            
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

            max_len = max(
                len(str(col_name)),
                max([len(str(worksheet.cell(row=r, column=col_num).value or '')) for r in range(2, len(df_exportar) + 2)], default=0)
            )
            worksheet.column_dimensions[col_letter].width = max(max_len + 5, 14)

    return buffer.getvalue()

def gerar_pdf_bytes(df_comparativo, mes_atual, mes_anterior):
    buffer = BytesIO()
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
            Paragraph(escape(str(row['Produto'])), cell_style),
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
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Novo Produto", "✏️ Editar Produto / Valor", "🗑️ Excluir Produto"])
    
    with tab1:
        with st.form("form_cadastro"):
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome do Produto")
                preco_custo = st.number_input("Preço de Custo (R$)", min_value=0.01, format="%.2f")
            with c2:
                codigo = st.text_input("Código / Referência (Opcional)")
                qtd_inicial = st.number_input("Estoque Inicial", min_value=0, step=1)
            
            data_compra_inicial = st.date_input("📅 Data de Aquisição / Entrada Inicial", value=date.today())
            
            submitted = st.form_submit_button("💾 Salvar Produto")
            if submitted:
                nome_formatado = nome.strip().title()
                if not nome_formatado:
                    st.error("O campo 'Nome do Produto' é obrigatório.")
                else:
                    try:
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO produtos (nome, codigo_barras, preco_custo, quantidade_estoque) VALUES (?, ?, ?, ?)", (nome_formatado, codigo.strip(), preco_custo, qtd_inicial))
                            prod_id = cursor.lastrowid
                            
                            if qtd_inicial > 0:
                                cursor.execute("INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, preco_unitario, data_compra) VALUES (?, 'ENTRADA', ?, ?, ?)", (prod_id, qtd_inicial, preco_custo, str(data_compra_inicial)))
                            conn.commit()
                        st.success(f"Produto '{nome_formatado}' cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("Já existe um produto registrado com este nome.")

    with tab2:
        with sqlite3.connect(DB_NAME) as conn:
            produtos_df = pd.read_sql_query("SELECT id, nome, preco_custo, quantidade_estoque FROM produtos ORDER BY nome ASC", conn)
        
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
                    nome_edit_formatado = novo_nome.strip().title()
                    if not nome_edit_formatado:
                        st.error("O nome do produto é obrigatório.")
                    else:
                        try:
                            with sqlite3.connect(DB_NAME) as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "UPDATE produtos SET nome = ?, preco_custo = ? WHERE id = ?",
                                    (nome_edit_formatado, novo_preco, int(dados_prod["id"]))
                                )
                                conn.commit()
                            st.success("Dados do produto atualizados com sucesso!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Já existe outro produto cadastrado com esse nome.")
        else:
            st.info("Nenhum produto cadastrado no banco de dados.")

    with tab3:
        st.warning("Por segurança, só é possível excluir produtos que não tenham movimentações registradas.")
        with sqlite3.connect(DB_NAME) as conn:
            produtos_excluir = pd.read_sql_query(
                "SELECT p.id, p.nome, p.quantidade_estoque FROM produtos p "
                "WHERE NOT EXISTS (SELECT 1 FROM movimentacoes_estoque m WHERE m.produto_id = p.id) "
                "ORDER BY p.nome",
                conn
            )
        if produtos_excluir.empty:
            st.info("Não há produtos sem histórico disponíveis para exclusão.")
        else:
            nome_excluir = st.selectbox("Selecione o produto que deseja excluir", produtos_excluir["nome"].tolist(), key="produto_para_excluir")
            dados_excluir = produtos_excluir[produtos_excluir["nome"] == nome_excluir].iloc[0]
            st.write(f"Estoque atual: **{inteiro_seguro(dados_excluir['quantidade_estoque'])}** unidade(s)")
            confirmar_exclusao = st.checkbox("Confirmo que desejo excluir este produto permanentemente.", key="confirmar_exclusao_produto")
            if st.button("🗑️ Excluir produto", disabled=not confirmar_exclusao):
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("DELETE FROM produtos WHERE id = ?", (int(dados_excluir["id"]),))
                    conn.commit()
                st.success("Produto excluído com sucesso.")
                st.rerun()

# ==========================================
# 2. MOVIMENTAÇÃO DE ESTOQUE (REORGANIZADO & RE-ESTILIZADO)
# ==========================================
elif menu == "🔄 Movimentação de Estoque":
    st.subheader("🔄 Movimentações de Compras & Estoque")
    st.caption("Registro de compras (entradas) e saídas operacionais.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    with sqlite3.connect(DB_NAME) as conn:
        produtos_df = pd.read_sql_query("SELECT id, nome, preco_custo, quantidade_estoque FROM produtos ORDER BY nome ASC", conn)
    
    if produtos_df.empty:
        st.warning("Nenhum produto disponível no catálogo. Cadastre produtos antes de realizar movimentações.")
    else:
        # Divide a interface em dois painéis organizados visualmente
        col_esq, col_dir = st.columns([1.1, 0.9], gap="large")
        
        with col_esq:
            st.markdown("##### 1. Seleção e Resumo do Item")
            prod_nome = st.selectbox("Selecione o Produto", produtos_df['nome'].tolist())
            prod_info = produtos_df[produtos_df['nome'] == prod
