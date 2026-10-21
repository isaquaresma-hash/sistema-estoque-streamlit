                    st.success(f"Lançamento #{int(row['ID'])} excluído e saldo ajustado.")
                    st.rerun()

        st.divider()
        st.subheader("📊 Comparativo entre Períodos")
        meses_disponiveis = sorted(
            [m for m in df_mov["Mes_Ano"].dropna().unique().tolist() if m],
            reverse=True
        )

        if len(meses_disponiveis) < 2:
            st.warning("O comparativo exige lançamentos em pelo menos dois meses diferentes. O histórico acima continua disponível.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                mes_atual = st.selectbox("Selecione o mês mais recente", meses_disponiveis, index=0)
            with col2:
                mes_anterior = st.selectbox("Selecione o mês de comparação", meses_disponiveis, index=1)

            if mes_atual == mes_anterior:
                st.warning("Selecione dois meses diferentes para comparar.")
            else:
                # O comparativo considera entradas e saídas separadamente para não
                # apresentar saídas operacionais como se fossem compras.
                df_periodo = df_mov[df_mov["Mes_Ano"].isin([mes_atual, mes_anterior])].copy()
                df_periodo["Movimentação"] = df_periodo["Tipo"].map({
                    "ENTRADA": "Entradas",
                    "SAIDA": "Saídas"
                })
                resumo = df_periodo.groupby(["Produto", "Mes_Ano", "Movimentação"]).agg(
                    Quantidade=("Quantidade", "sum"),
                    Preço_Médio=("Preço_Unitario", "mean")
                ).reset_index()

                df_periodo["Quantidade_Liquida"] = df_periodo["Quantidade"] * df_periodo["Tipo"].map({"ENTRADA": 1, "SAIDA": -1}).fillna(0)
                qtd_atual = df_periodo[df_periodo["Mes_Ano"] == mes_atual].groupby("Produto")["Quantidade_Liquida"].sum()
                qtd_ant = df_periodo[df_periodo["Mes_Ano"] == mes_anterior].groupby("Produto")["Quantidade_Liquida"].sum()
                preco_atual = df_periodo[
                    (df_periodo["Mes_Ano"] == mes_atual) & (df_periodo["Tipo"] == "ENTRADA")
                ].groupby("Produto")["Preço_Unitario"].mean()
                preco_ant = df_periodo[
                    (df_periodo["Mes_Ano"] == mes_anterior) & (df_periodo["Tipo"] == "ENTRADA")
                ].groupby("Produto")["Preço_Unitario"].mean()

                produtos_periodo = sorted(set(qtd_atual.index) | set(qtd_ant.index) | set(preco_atual.index) | set(preco_ant.index))
                df_comp = pd.DataFrame({"Produto": produtos_periodo})
                df_comp[f"Qtd ({mes_anterior})"] = df_comp["Produto"].map(qtd_ant).fillna(0)
                df_comp[f"Qtd ({mes_atual})"] = df_comp["Produto"].map(qtd_atual).fillna(0)
                df_comp["Diferença Qtd"] = df_comp[f"Qtd ({mes_atual})"] - df_comp[f"Qtd ({mes_anterior})"]
                df_comp[f"Preço ({mes_anterior})"] = df_comp["Produto"].map(preco_ant).fillna(0)
                df_comp[f"Preço ({mes_atual})"] = df_comp["Produto"].map(preco_atual).fillna(0)
                df_comp["Diferença Preço"] = df_comp[f"Preço ({mes_atual})"] - df_comp[f"Preço ({mes_anterior})"]

                st.subheader("📌 Indicadores")
                m1, m2, m3 = st.columns(3)
                m1.metric("Variação líquida do estoque", f"{df_comp['Diferença Qtd'].sum():+.0f} un")
                variacao_preco = df_comp["Diferença Preço"].mean() if not df_comp.empty else 0
                m2.metric("Variação média do preço de entrada", f"R$ {variacao_preco:+.2f}")
                m3.metric("Produtos analisados", len(df_comp))
                st.dataframe(df_comp, use_container_width=True, hide_index=True)

                st.subheader("📄 Exportar relatórios")
                exp_col1, exp_col2 = st.columns(2)
                with exp_col1:
                    excel_comparativo = gerar_excel_estilizado_bytes(df_comp, nome_aba="Relatório Comparativo")
                    st.download_button(
                        "📊 Baixar planilha Excel",
                        data=excel_comparativo,
                        file_name=f"relatorio_estoque_{mes_anterior}_vs_{mes_atual}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                with exp_col2:
                    pdf_data = gerar_pdf_bytes(df_comp, mes_atual, mes_anterior)
                    st.download_button(
                        "📄 Baixar relatório PDF",
                        data=pdf_data,
                        file_name=f"relatorio_gestao_compras_{mes_anterior}_vs_{mes_atual}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

        df_export = df_mov.drop(columns=["produto_id"]).rename(columns={
            "Data_Compra": "Data da Compra",
            "Preço_Unitario": "Preço Unitário",
            "Mes_Ano": "Mês/Ano"
        })
        excel_historico = gerar_excel_estilizado_bytes(df_export, nome_aba="Histórico")
        st.download_button(
            "📥 Baixar histórico completo (.xlsx)",
            data=excel_historico,
            file_name=f"historico_movimentacoes_{datetime.now().strftime('%Y_%m_%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ==========================================
# 4. GESTÃO DE USUÁRIOS
# ==========================================
elif menu == "👥 Gestão de Usuários":
    st.subheader("👥 Controle de Acesso e Usuários")
    st.caption("Gerenciamento de contas e atribuição de permissões no sistema.")
    
    with st.form("form_novo_usuario"):
        st.subheader("Cadastrar Novo Usuário")
        c1, c2 = st.columns(2)
        with c1:
            novo_nome = st.text_input("Nome Completo")
            nova_senha = st.text_input("Senha", type="password")
        with c2:
            novo_username = st.text_input("E-mail / Usuário de Acesso")
            novo_role = st.selectbox("Nível de Permissão", ["operador", "admin"])
        
        submit_user = st.form_submit_button("👤 Cadastrar Usuário")
        if submit_user:
            if not novo_nome.strip() or not novo_username.strip() or not nova_senha:
                st.error("Todos os campos do formulário devem ser preenchidos.")
            elif len(nova_senha) < 8:
                st.error("A senha deve ter pelo menos 8 caracteres.")
            else:
                try:
                    with sqlite3.connect(DB_NAME, timeout=30) as conn:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios (nome, username, senha, role) VALUES (?, ?, ?, ?)", (novo_nome.strip(), novo_username.strip().lower(), hash_password(nova_senha), novo_role))
                        conn.commit()
                    st.success(f"Acesso para '{novo_username}' configurado com sucesso!")
                except sqlite3.IntegrityError:
                    st.error("O e-mail/usuário informado já está cadastrado no sistema.")
