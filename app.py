# ==========================================
# 3. DASHBOARD E RELATÓRIO COMPARATIVO
# ==========================================
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
        
        if len(meses_disponiveis) < 2:
            st.warning("São necessários lançamentos em pelo menos dois meses diferentes para montar o comparativo de períodos.")
            st.markdown("### Histórico de Lançamentos:")
            
            # --- LISTAGEM COM BOTÃO DE EXCLUSÃO (LIXEIRA) ---
            # Cabeçalho da tabela
            h1, h2, h3, h4, h5, h6, h7 = st.columns([0.6, 2, 1.2, 1, 1.3, 1.2, 0.8])
            h1.markdown("**ID**")
            h2.markdown("**Produto**")
            h3.markdown("**Tipo**")
            h4.markdown("**Qtd**")
            h5.markdown("**Preço Unit.**")
            h6.markdown("**Mês/Ano**")
            h7.markdown("**Ação**")
            st.divider()

            for idx, row in df_mov.iterrows():
                c1, c2, c3, c4, c5, c6, c7 = st.columns([0.6, 2, 1.2, 1, 1.3, 1.2, 0.8])
                c1.write(f"#{row['ID']}")
                c2.write(row['Produto'])
                
                # Cor para entrada/saída
                cor_tipo = "🟢" if row['Tipo'] == "ENTRADA" else "🔴"
                c3.write(f"{cor_tipo} {row['Tipo']}")
                
                c4.write(str(row['Quantidade']))
                c5.write(f"R$ {row['Preço_Unitario']:.2f}")
                c6.write(row['Mes_Ano'])
                
                # Botão de exclusão para cada linha
                if c7.button("🗑️", key=f"del_mov_{row['ID']}", help=f"Excluir lançamento #{row['ID']}"):
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        # Reverter o estoque ao excluir
                        if row['Tipo'] == "ENTRADA":
                            cursor.execute("UPDATE produtos SET quantidade_estoque = quantidade_estoque - ? WHERE id = ?", (row['Quantidade'], row['produto_id']))
                        else:
                            cursor.execute("UPDATE produtos SET quantidade_estoque = quantidade_estoque + ? WHERE id = ?", (row['Quantidade'], row['produto_id']))
                        
                        # Deletar registro de movimentação
                        cursor.execute("DELETE FROM movimentacoes_estoque WHERE id = ?", (row['ID'],))
                        conn.commit()
                    
                    st.success(f"Lançamento #{row['ID']} excluído e estoque reajustado!")
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            
            # Preparar dataframe limpo para exportação
            df_export = df_mov.drop(columns=['produto_id'])
            excel_historico = gerar_excel_estilizado_bytes(df_export, nome_aba="Histórico")
            st.download_button(
                label="📥 Baixar Histórico Geral (.xlsx)",
                data=excel_historico,
                file_name=f"historico_movimentacoes_{datetime.now().strftime('%Y_%m_%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            col1, col2 = st.columns(2)
            with col1:
                mes_atual = st.selectbox("Selecione o Mês Recente (Atual)", meses_disponiveis, index=0)
            with col2:
                mes_anterior = st.selectbox("Selecione o Mês Base (Anterior)", meses_disponiveis, index=1 if len(meses_disponiveis) > 1 else 0)

            df_atual = df_mov[df_mov['Mes_Ano'] == mes_atual].groupby('Produto').agg(qtd_atual=('Quantidade', 'sum'), preco_atual=('Preço_Unitario', 'mean')).reset_index()
            df_ant = df_mov[df_mov['Mes_Ano'] == mes_anterior].groupby('Produto').agg(qtd_ant=('Quantidade', 'sum'), preco_ant=('Preço_Unitario', 'mean')).reset_index()

            df_comp = pd.merge(df_atual, df_ant, on='Produto', how='outer').fillna(0)
            df_comp['Diferença Qtd'] = df_comp['qtd_atual'] - df_comp['qtd_ant']
            df_comp['Diferença Preço'] = df_comp['preco_atual'] - df_comp['preco_ant']

            df_comp.rename(columns={
                'qtd_ant': f'Qtd ({mes_anterior})', 
                'qtd_atual': f'Qtd ({mes_atual})', 
                'preco_ant': f'Preço ({mes_anterior})', 
                'preco_atual': f'Preço ({mes_atual})'
            }, inplace=True)

            st.subheader("📌 Indicadores de Variação")
            m1, m2, m3 = st.columns(3)
            total_dif_qtd = df_comp['Diferença Qtd'].sum()
            media_dif_preco = df_comp['Diferença Preço'].mean()
            
            m1.metric("Variação de Volume", f"{total_dif_qtd:+} un")
            m2.metric("Variação Média de Preço", f"R$ {media_dif_preco:+.2f}")
            m3.metric("Itens Analisados", len(df_comp))

            st.divider()
            st.subheader("📋 Tabela Analítica")
            st.dataframe(df_comp, use_container_width=True)

            st.divider()
            st.subheader("📄 Emissão de Documentos e Planilhas")
            
            exp_col1, exp_col2 = st.columns(2)
            
            with exp_col1:
                excel_comparativo = gerar_excel_estilizado_bytes(df_comp, nome_aba="Relatório Comparativo")
                st.download_button(
                    label="📊 Baixar Planilha Formatada (.xlsx)",
                    data=excel_comparativo,
                    file_name=f"relatorio_estoque_{mes_anterior}_vs_{mes_atual}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with exp_col2:
                pdf_data = gerar_pdf_bytes(df_comp, mes_atual, mes_anterior)
                st.download_button(
                    label="📄 Baixar Relatório em PDF",
                    data=pdf_data,
                    file_name=f"relatorio_gestao_compras_{mes_anterior}_vs_{mes_atual}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
