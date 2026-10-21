# ==========================================
# 2. MOVIMENTAÇÃO DE ESTOQUE
# ==========================================
elif menu == "🔄 Movimentação de Estoque":
    st.subheader("🔄 Movimentações de Compras & Estoque")
    st.caption("Registro de compras (entradas) e saídas operacionais.")
    
    with sqlite3.connect(DB_NAME) as conn:
        # Traz os produtos ordenados e sem o item duplicado em minúsculo se houver equivalência
        produtos_df = pd.read_sql_query(
            "SELECT id, nome, preco_custo, quantidade_estoque FROM produtos WHERE nome != 'sabão' ORDER BY nome COLLATE NOCASE", 
            conn
        )
    
    if produtos_df.empty:
        st.warning("Nenhum produto disponível no catálogo. Cadastre produtos antes de realizar movimentações.")
    else:
        col1, col2 = st.columns([1.1, 0.9])
        with col1:
            lista_produtos = produtos_df['nome'].tolist()
            prod_nome = st.selectbox("Selecione o Produto", lista_produtos)
            prod_info = produtos_df[produtos_df['nome'] == prod_nome].iloc[0]
            
            saldo_atual = inteiro_seguro(prod_info['quantidade_estoque'])
            preco_base = float(prod_info['preco_custo'])
            valor_total_estoque = saldo_atual * preco_base
            
            st.markdown(f"""
            <div style='background-color:#EBF3FA; padding:1rem; border-radius:12px; border-left:6px solid #0D47A1; margin-bottom:1rem;'>
                <p style='margin:0; font-size:0.85rem; color:#475569;'>Informações do Item Selecionado</p>
                <h4 style='margin:0.2rem 0; color:#0D1B2A;'>📦 {prod_info['nome']}</h4>
                <p style='margin:0; font-size:1rem; color:#0D47A1;'>
                    <b>Estoque Atual:</b> <span style='font-size:1.2rem; color:#002171;'>{saldo_atual}</span> unidades | 
                    <b>Preço Base:</b> R$ {preco_base:.2f} | 
                    <b>Valor Total em Estoque:</b> R$ {valor_total_estoque:.2f}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if saldo_atual > 0:
                with st.expander("🚨 Zerar Estoque deste Produto"):
                    st.warning(f"Atenção: Esta ação vai dar baixa em todas as **{saldo_atual}** unidades do produto **{prod_info['nome']}**.")
                    if st.button("🔴 Confirmar Zerar Estoque", use_container_width=True):
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, preco_unitario, data_compra) VALUES (?, 'SAIDA', ?, ?, ?)",
                                (int(prod_info['id']), saldo_atual, preco_base, str(date.today()))
                            )
                            cursor.execute("UPDATE produtos SET quantidade_estoque = 0 WHERE id = ?", (int(prod_info['id']),))
                            conn.commit()
                        st.success(f"Estoque do produto '{prod_info['nome']}' zerado com sucesso!")
                        st.rerun()
            else:
                st.caption("ℹ️ Este produto já se encontra com estoque zerado (0 un).")
                
            st.markdown("<br>", unsafe_allow_html=True)
            data_operacao = st.date_input("📅 Data da Compra / Operação", value=date.today())

        with col2:
            st.markdown("#### Novo Lançamento")
            tipo_mov = st.radio("Tipo de Lançamento", ["ENTRADA (Compra/Aporte)", "SAIDA (Baixa/Consumo)"])
            quantidade = st.number_input("Quantidade", min_value=1, step=1)
            preco_unitario = st.number_input("Preço Unitário da Operação (R$)", min_value=0.01, value=float(prod_info['preco_custo']), format="%.2f")

            if st.button("💾 Registrar Operação", use_container_width=True):
                tipo = "ENTRADA" if "ENTRADA" in tipo_mov else "SAIDA"
                
                if int(quantidade) < 1:
                    st.error("A quantidade deve ser maior que zero.")
                else:
                    try:
                        with sqlite3.connect(DB_NAME, timeout=30) as conn:
                            conn.execute("PRAGMA foreign_keys = ON")
                            cursor = conn.cursor()
                            cursor.execute(
                                "SELECT quantidade_estoque FROM produtos WHERE id = ?",
                                (int(prod_info['id']),)
                            )
                            saldo_result = cursor.fetchone()
                            if saldo_result is None:
                                raise ValueError("O produto selecionado não existe mais no banco de dados.")
                            saldo_banco = inteiro_seguro(saldo_result[0])
                            if tipo == "SAIDA" and int(quantidade) > saldo_banco:
                                raise ValueError("A quantidade solicitada excede o saldo atual em estoque.")
                            nova_qtd = saldo_banco + int(quantidade) if tipo == "ENTRADA" else saldo_banco - int(quantidade)
                            cursor.execute(
                                "INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, preco_unitario, data_compra) VALUES (?, ?, ?, ?, ?)",
                                (int(prod_info['id']), tipo, int(quantidade), float(preco_unitario), str(data_operacao))
                            )
                            cursor.execute("UPDATE produtos SET quantidade_estoque = ? WHERE id = ?", (nova_qtd, int(prod_info['id'])))
                            conn.commit()
                        st.success(f"Movimentação registrada com sucesso para o dia {data_operacao.strftime('%d/%m/%Y')}!")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
