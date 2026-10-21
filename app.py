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
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Gestão de Estoque & Compras",
    page_icon="📦",
    layout="wide"
)

DB_NAME = "estoque_compras.db"

# ==========================================
# BANCO DE DADOS E CRIPTOGRAFIA
# ==========================================
def hash_password(password):
    """Criptografa a senha usando SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Inicializa as tabelas do banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de Usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'operador'
        )
    """)
    
    # Tabela de Produtos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            codigo_barras TEXT,
            preco_custo REAL NOT NULL,
            quantidade_estoque INTEGER NOT NULL DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de Movimentações (Compras e Vendas/Baixas)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            tipo TEXT CHECK(tipo IN ('ENTRADA', 'SAIDA')),
            quantidade INTEGER NOT NULL,
            preco_unitario REAL NOT NULL,
            data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        )
    """)
    
    # Usuário Padrão Admin
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)",
            ("Administrador", "admin", hash_password("admin123"), "admin")
        )

    # Usuário Cadastrado: Roze Peres
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'roze.peres@fnp.org.br'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)",
            ("Roze Peres", "roze.peres@fnp.org.br", hash_password("fnp2026"), "admin")
        )
        
    conn.commit()
    conn.close()

init_db()

# ==========================================
# AUTENTICAÇÃO E SESSÃO
# ==========================================
def verificar_login(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, nome, role FROM usuarios WHERE username = ? AND senha = ?",
        (username.lower().strip(), hash_password(password))
    )
    user = cursor.fetchone()
    conn.close()
    return user

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown("<h2 style='text-align: center;'>🔒 Acesso ao Sistema</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Gestão de Estoque & Compras</p>", unsafe_allow_html=True)
        st.divider()
        
        username = st.text_input("E-mail ou Usuário", placeholder="seu.email@fnp.org.br")
        password = st.text_input("Senha", type="password", placeholder="••••••••")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Entrar no Sistema", type="primary", use_container_width=True):
            user = verificar_login(username, password)
            if user:
                st.session_state["usuario_logado"] = {
                    "id": user[0],
                    "nome": user[1],
                    "role": user[2]
                }
                st.success(f"Bem-vindo(a), {user[1]}!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

def logout():
    st.session_state["usuario_logado"] = None
    st.rerun()

# Bloqueia a execução das telas caso não esteja autenticado
if not st.session_state["usuario_logado"]:
    login_screen()
    st.stop()

# ==========================================
# INTERFACE PRINCIPAL (SESSÃO AUTENTICADA)
# ==========================================
user_info = st.session_state["usuario_logado"]

st.sidebar.markdown(f"👤 **Usuário:** {user_info['nome']}")
st.sidebar.markdown(f"🔑 **Permissão:** {user_info['role'].capitalize()}")
if st.sidebar.button("🔴 Sair / Logout"):
    logout()

st.sidebar.divider()

menu_options = ["📊 Dashboard & Relatórios", "🔄 Movimentação de Estoque"]
if user_info["role"] == "admin":
    menu_options.insert(0, "📦 Gestão de Produtos")
    menu_options.append("👥 Gestão de Usuários")

menu = st.sidebar.radio("Navegação", menu_options)

# ==========================================
# GERADOR DE RELATÓRIO PDF (REPORTLAB)
# ==========================================
def gerar_pdf_bytes(df_comparativo, mes_atual, mes_anterior):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=10)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, alignment=2, textColor=colors.gray)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8)
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')

    story.append(Paragraph("<b>Relatório Comparativo Mensal - Estoque & Compras</b>", title_style))
    story.append(Paragraph(f"Período Comparado: {mes_anterior} vs {mes_atual} | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))
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
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F2F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
    ]))
    
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ==========================================
# 1. GESTÃO DE PRODUTOS (EXCLUSIVO ADMIN)
# ==========================================
if menu == "📦 Gestão de Produtos":
    st.title("📦 Cadastro e Alteração de Produtos")
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Novo Produto", "✏️ Editar Produto / Preço"])
    
    with tab1:
        with st.form("form_cadastro"):
            nome = st.text_input("Nome do Produto")
            codigo = st.text_input("Código de Barras (Opcional)")
            preco_custo = st.number_input("Preço de Custo (R$)", min_value=0.01, format="%.2f")
            qtd_inicial = st.number_input("Estoque Inicial", min_value=0, step=1)
            
            submitted = st.form_submit_button("Salvar Produto")
            if submitted:
                if nome.strip() == "":
                    st.error("O nome do produto é obrigatório!")
                else:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO produtos (nome, codigo_barras, preco_custo, quantidade_estoque) VALUES (?, ?, ?, ?)",
                            (nome.strip(), codigo.strip(), preco_custo, qtd_inicial)
                        )
                        prod_id = cursor.lastrowid
                        
                        if qtd_inicial > 0:
                            cursor.execute(
                                "INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, preco_unitario) VALUES (?, 'ENTRADA', ?, ?)",
                                (prod_id, qtd_inicial, preco_custo)
                            )
                        conn.commit()
                        conn.close()
                        st.success(f"Produto '{nome}' cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("Já existe um produto cadastrado com este nome.")

    with tab2:
        conn = sqlite3.connect(DB_NAME)
        produtos_df = pd.read_sql_query("SELECT id, nome, preco_custo, quantidade_estoque FROM produtos", conn)
        conn.close()
        
        if not produtos_df.empty:
            prod_selecionado = st.selectbox("Selecione o Produto para Alterar", produtos_df['nome'].tolist())
            dados_prod = produtos_df[produtos_df['nome'] == prod_selecionado].iloc[0]
            
            with st.form("form_editar"):
                novo_nome = st.text_input("Nome", value=dados_prod['nome'])
                novo_preco = st.number_input("Preço de Custo (R$)", min_value=0.01, value=float(dados_prod['preco_custo']), format="%.2f")
                
                if st.form_submit_button("Atualizar Dados"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE produtos SET nome = ?, preco_custo = ? WHERE id = ?",
                        (novo_nome, novo_preco, int(dados_prod['id']))
                    )
                    conn.commit()
                    conn.close()
                    st.success("Produto atualizado com sucesso!")
                    st.rerun()
        else:
            st.info("Nenhum produto cadastrado ainda.")

# ==========================================
# 2. MOVIMENTAÇÃO DE ESTOQUE
# ==========================================
elif menu == "🔄 Movimentação de Estoque":
    st.title("🔄 Registro de Entradas e Saídas")
    
    conn = sqlite3.connect(DB_NAME)
    produtos_df = pd.read_sql_query("SELECT id, nome, preco_custo, quantidade_estoque FROM produtos", conn)
    conn.close()
    
    if produtos_df.empty:
        st.warning("Nenhum produto cadastrado no sistema. Cadastre produtos antes de registrar movimentações.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            prod_nome = st.selectbox("Produto", produtos_df['nome'].tolist())
            prod_info = produtos_df[produtos_df['nome'] == prod_nome].iloc[0]
            st.info(f"**Estoque Atual:** {prod_info['quantidade_estoque']} un | **Preço Cadastrado:** R$ {prod_info['preco_custo']:.2f}")

        with col2:
            tipo_mov = st.radio("Tipo de Movimentação", ["ENTRADA (Compra/Aporte)", "SAIDA (Venda/Baixa)"])
            quantidade = st.number_input("Quantidade", min_value=1, step=1)
            preco_unitario = st.number_input("Preço Unitário Praticado (R$)", min_value=0.01, value=float(prod_info['preco_custo']), format="%.2f")

        if st.button("Registrar Movimentação", type="primary"):
            tipo = "ENTRADA" if "ENTRADA" in tipo_mov else "SAIDA"
            
            if tipo == "SAIDA" and quantidade > prod_info['quantidade_estoque']:
                st.error("Quantidade de saída maior do que o estoque disponível!")
            else:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                cursor.execute(
                    "INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                    (int(prod_info['id']), tipo, quantidade, preco_unitario)
                )
                
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
    st.title("📊 Comparativo Mês a Mês & Exportação PDF")
    
    conn = sqlite3.connect(DB_NAME)
    df_mov = pd.read_sql_query("""
        SELECT 
            m.id, p.nome as produto, m.tipo, m.quantidade, m.preco_unitario,
            strftime('%Y-%m', m.data_movimentacao) as mes_ano
        FROM movimentacoes_estoque m
        JOIN produtos p ON p.id = m.produto_id
    """, conn)
    conn.close()

    if df_mov.empty:
        st.info("Ainda não há movimentações registradas no sistema.")
    else:
        meses_disponiveis = sorted(df_mov['mes_ano'].unique(), reverse=True)
        
        if len(meses_disponiveis) < 2:
            st.warning("São necessários dados registrados em pelo menos 2 meses diferentes para realizar a comparação mensal.")
            st.markdown("### Lançamentos Registrados:")
            st.dataframe(df_mov, use_container_width=True)
        else:
            col1, col2 = st.columns(2)
            with col1:
                mes_atual = st.selectbox("Selecione o Mês Atual", meses_disponiveis, index=0)
            with col2:
                mes_anterior = st.selectbox("Selecione o Mês de Comparação", meses_disponiveis, index=1 if len(meses_disponiveis) > 1 else 0)

            # Agregação Mês Atual
            df_atual = df_mov[df_mov['mes_ano'] == mes_atual].groupby('produto').agg(
                qtd_atual=('quantidade', 'sum'),
                preco_atual=('preco_unitario', 'mean')
            ).reset_index()

            # Agregação Mês Anterior
            df_ant = df_mov[df_mov['mes_ano'] == mes_anterior].groupby('produto').agg(
                qtd_ant=('quantidade', 'sum'),
                preco_ant=('preco_unitario', 'mean')
            ).reset_index()

            # Merge e Cálculo das Diferenças
            df_comp = pd.merge(df_atual, df_ant, on='produto', how='outer').fillna(0)
            df_comp['Diferença Qtd'] = df_comp['qtd_atual'] - df_comp['qtd_ant']
            df_comp['Diferença Preço'] = df_comp['preco_atual'] - df_comp['preco_ant']

            df_comp.rename(columns={
                'produto': 'Produto',
                'qtd_ant': f'Qtd ({mes_anterior})',
                'qtd_atual': f'Qtd ({mes_atual})',
                'preco_ant': f'Preço ({mes_anterior})',
                'preco_atual': f'Preço ({mes_atual})'
            }, inplace=True)

            # Cards de Métricas
            st.subheader("📌 Resumo das Variações")
            m1, m2, m3 = st.columns(3)
            total_dif_qtd = df_comp['Diferença Qtd'].sum()
            media_dif_preco = df_comp['Diferença Preço'].mean()
            
            m1.metric("Variação Total de Volume", f"{total_dif_qtd:+} un")
            m2.metric("Variação Média de Preço", f"R$ {media_dif_preco:+.2f}")
            m3.metric("Produtos Analisados", len(df_comp))

            st.divider()
            
            # Tabela Detalhada
            st.subheader("📋 Tabela Comparativa Detalhada")
            st.dataframe(df_comp, use_container_width=True)

            # Botão para Download do PDF
            st.divider()
            st.subheader("📄 Exportar Relatório em PDF")
            
            pdf_data = gerar_pdf_bytes(df_comp, mes_atual, mes_anterior)
            
            st.download_button(
                label="📥 Baixar Relatório Comparativo em PDF",
                data=pdf_data,
                file_name=f"relatorio_comparativo_{mes_anterior}_vs_{mes_atual}.pdf",
                mime="application/pdf",
                type="primary"
            )

# ==========================================
# 4. GESTÃO DE USUÁRIOS (EXCLUSIVO ADMIN)
# ==========================================
elif menu == "👥 Gestão de Usuários":
    st.title("👥 Gerenciamento de Usuários do Sistema")
    
    with st.form("form_novo_usuario"):
        st.subheader("Cadastrar Novo Usuário")
        novo_nome = st.text_input("Nome Completo")
        novo_username = st.text_input("Nome de Usuário / E-mail")
        nova_senha = st.text_input("Senha", type="password")
        novo_role = st.selectbox("Nível de Permissão", ["operador", "admin"])
        
        if st.form_submit_button("Cadastrar Usuário"):
            if not novo_nome or not novo_username or not nova_senha:
                st.error("Preencha todos os campos do formulário!")
            else:
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)",
                        (novo_nome.strip(), novo_username.strip().lower(), hash_password(nova_senha), novo_role)
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Usuário '{novo_username}' criado com sucesso!")
                except sqlite3.IntegrityError:
                    st.error("Este nome de usuário já está cadastrado.")

    st.divider()
    st.subheader("Usuários Cadastrados")
    conn = sqlite3.connect(DB_NAME)
    users_df = pd.read_sql_query("SELECT id, nome, username, role FROM usuarios", conn)
    conn.close()
    st.dataframe(users_df, use_container_width=True)
