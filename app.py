# ==========================================
# 05. CATÁLOGO DE MATERIAIS (REFEITO IDÊNTICO À IMAGEM)
# ==========================================
elif menu_opcao == "05. Catálogo de Materiais":
    
    if "modo_material" not in st.session_state:
        st.session_state["modo_material"] = "lista"
    if "material_edicao" not in st.session_state:
        st.session_state["material_edicao"] = None

    # ESTRUTURA DO CARD PRINCIPAL
    st.markdown("<div class='main-card-wrapper'>", unsafe_allow_html=True)

    # 1. Cabeçalho: Título + Botão Preto Arredondado "+ Novo material"
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

    # 2. Formulário de Cadastro/Edição
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

    # 3. Lista de Itens no Formato Exato do Protótipo
    else:
        # Barra de Pesquisa com Ícone de Lupa
        busca_termo = st.text_input("🔍", placeholder="Buscar material pelo nome...").strip().lower()
        
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
