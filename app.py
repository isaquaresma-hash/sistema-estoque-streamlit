# ==========================================
# INTERFACE PRINCIPAL - MENU E PÁGINAS
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
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO produtos (nome, codigo_barras, preco_custo, quantidade_estoque) VALUES (?, ?, ?, ?)", (nome.strip(), codigo.strip(), preco_custo, qtd_inicial))
                            prod_id = cursor.lastrowid
                            
                            if qtd_inicial > 0:
                                cursor.execute("INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, preco_unitario) VALUES (?, 'ENTRADA', ?, ?)", (prod_id, qtd_inicial, preco_custo))
                            conn.commit()
                        st.success(f"Produto '{nome}' cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("Já existe um produto registrado com este nome.")

    with tab2:
        with sqlite3.connect(DB_NAME) as conn:
            produtos_df = pd.read_sql_query("SELECT id, nome, preco_custo, quantidade_estoque FROM produtos", conn)
        
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
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE produtos SET nome = ?, preco_custo = ? WHERE id = ?", (novo_nome, novo_preco, int(dados_prod['id'])))
                        conn.commit()
                    st.success("Dados do produto atualizados com sucesso!")
                    st.rerun()
        else:
            st.info("Nenhum produto cadastrado no banco de dados.")

elif menu == "🔄 Movimentação de Estoque":
    st.subheader("🔄 Movimentações de Compras & Estoque")
    st.caption("Registro de compras (entradas) e saídas operacionais.")
    
    with sqlite3.connect(DB_NAME) as conn:
        produtos_df = pd.read_sql_query("SELECT id, nome, preco_custo, quantidade_estoque FROM produtos", conn)
    
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
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, preco_unitario) VALUES (?, ?, ?, ?)", (int(prod_info['id']), tipo, quantidade, preco_unitario))
                    
                    nova_qtd = prod_info['quantidade_estoque'] + quantidade if tipo == "ENTRADA" else prod_info['quantidade_estoque'] - quantidade
                    cursor.execute("UPDATE produtos SET quantidade_estoque = ? WHERE id = ?", (nova_qtd, int(prod_info['id'])))
                    conn.commit()
                st.success("Movimentação registrada com sucesso!")
                st.rerun()

elif menu == "📊 Dashboard & Relatórios":
    st.subheader("📊 Painel Comparativo & Exportação")
    st.caption("Comparação periódica de volume de compras e variações de valor.")
    
    with sqlite3.connect(DB_NAME) as conn:
        df_mov = pd.read_sql_query(
            "SELECT m.id as ID, m.produto_id, p.nome as Produto, m.tipo as Tipo, "
            "m.quantidade as Quantidade, m.preco_unitario as Preço_Unitario, "
            "strftime('%Y-%m', m.data_movimentacao) as Mes_Ano "
            "FROM movimentacoes_estoque m "
            "JOIN produtos p ON p.id = m.produto_id "
            "ORDER BY m.id DESC", conn
        )

    if df_mov.empty:
        st.info("Ainda não há lançamentos registrados para gerar comparativos.")
    else:
        meses_disponiveis = sorted(df_mov['Mes_Ano'].unique(), reverse=True)
        
        if len(meses_disponiveis) < 2
