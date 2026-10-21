
            c5.write(f"R$ {float(row['Preço_Unitario']):.2f}")

            try:

                data_formatada = datetime.strptime(str(row["Data_Compra"])[:10], "%Y-%m-%d").strftime("%d/%m/%Y")

            except (ValueError, TypeError):

                data_formatada = str(row["Data_Compra"])

            c6.write(data_formatada)

            if c7.button("🗑️", key=f"del_mov_{int(row['ID'])}", help=f"Excluir lançamento #{int(row['ID'])}"):

                erro_exclusao = None

                with sqlite3.connect(DB_NAME, timeout=30) as conn:

                    conn.execute("PRAGMA foreign_keys = ON")

                    cursor = conn.cursor()

                    cursor.execute(

                        "SELECT tipo, quantidade, produto_id FROM movimentacoes_estoque WHERE id = ?",

                        (int(row["ID"]),)

                    )

                    mov = cursor.fetchone()

                    if not mov:

                        erro_exclusao = "Este lançamento já foi excluído ou não existe."

                    else:

                        tipo_excluido, qtd_excluida, produto_id = mov

                        cursor.execute("SELECT quantidade_estoque FROM produtos WHERE id = ?", (produto_id,))

                        saldo_result = cursor.fetchone()

                        if not saldo_result:

                            erro_exclusao = "O produto associado a este lançamento não foi encontrado."

                        else:

                            saldo = inteiro_seguro(saldo_result[0])

                            novo_saldo = saldo - int(qtd_excluida) if tipo_excluido == "ENTRADA" else saldo + int(qtd_excluida)

                            if novo_saldo < 0:

                                erro_exclusao = (

                                    "Não é possível excluir esta entrada porque o saldo atual não comporta "

                                    "a reversão. Confira as movimentações posteriores."

                                )

                            else:

                                cursor.execute(
                                    "UPDATE produtos SET quantidade_estoque = ? WHERE id = ?",
                                    (novo_saldo, produto_id),
                                )
                                cursor.execute("DELETE FROM movimentacoes_estoque WHERE id = ?", (int(row["ID"]),))
                                conn.commit()

                if erro_exclusao:
                    st.error(erro_exclusao)
                else:
                    st.success("Lançamento excluído e saldo do estoque ajustado.")
                    st.rerun()

        st.divider()
        st.subheader("📈 Comparativo Mensal")

        df_comparativo_base = df_mov.copy()
        df_comparativo_base["Data_Compra"] = pd.to_datetime(df_comparativo_base["Data_Compra"], errors="coerce")
        df_comparativo_base = df_comparativo_base.dropna(subset=["Data_Compra"])

        if df_comparativo_base.empty:
            st.info("Não há datas válidas suficientes para gerar o comparativo mensal.")
        else:
            meses_disponiveis = sorted(df_comparativo_base["Data_Compra"].dt.to_period("M").astype(str).unique().tolist())
            if len(meses_disponiveis) >= 2:
                col_mes1, col_mes2 = st.columns(2)
                with col_mes1:
                    mes_anterior = st.selectbox("Mês de comparação", meses_disponiveis, index=max(0, len(meses_disponiveis) - 2))
                with col_mes2:
                    mes_atual = st.selectbox("Mês atual", meses_disponiveis, index=len(meses_disponiveis) - 1)
            else:
                mes_anterior = meses_disponiveis[0]
                mes_atual = meses_disponiveis[0]
                st.caption("Há registros de apenas um mês. O comparativo usará o mesmo mês nas duas colunas.")

            df_comparativo_base["Mes_Ano"] = df_comparativo_base["Data_Compra"].dt.to_period("M").astype(str)
            df_comparativo_base["Valor_Total"] = df_comparativo_base["Quantidade"].astype(float) * df_comparativo_base["Preço_Unitario"].astype(float)

            def resumo_mes(mes):
                dados = df_comparativo_base[df_comparativo_base["Mes_Ano"] == mes].copy()
                dados["Qtd_Ajustada"] = dados.apply(lambda r: r["Quantidade"] if r["Tipo"] == "ENTRADA" else -r["Quantidade"], axis=1)
                return dados.groupby("Produto", as_index=False).agg(Quantidade=("Qtd_Ajustada", "sum"), Preco_Medio=("Preço_Unitario", "mean"))

            resumo_anterior = resumo_mes(mes_anterior).rename(columns={"Quantidade": "Qtd_Anterior", "Preco_Medio": "Preco_Anterior"})
            resumo_atual = resumo_mes(mes_atual).rename(columns={"Quantidade": "Qtd_Atual", "Preco_Medio": "Preco_Atual"})
            df_comp = pd.merge(resumo_anterior, resumo_atual, on="Produto", how="outer").fillna(0)
            df_comp["Diferença Qtd"] = df_comp["Qtd_Atual"] - df_comp["Qtd_Anterior"]
            df_comp["Diferença Preço"] = df_comp["Preco_Atual"] - df_comp["Preco_Anterior"]
            df_comp = df_comp.rename(columns={"Qtd_Anterior": f"Qtd ({mes_anterior})", "Qtd_Atual": f"Qtd ({mes_atual})", "Preco_Atual": f"Preço ({mes_atual})"})
            colunas_relatorio = ["Produto", f"Qtd ({mes_anterior})", f"Qtd ({mes_atual})", "Diferença Qtd", f"Preço ({mes_atual})", "Diferença Preço"]
            df_comp = df_comp[colunas_relatorio].sort_values("Produto")
            st.dataframe(df_comp, use_container_width=True, hide_index=True)

            c_excel, c_pdf = st.columns(2)
            with c_excel:
                st.download_button(
                    "📥 Baixar relatório Excel",
                    data=gerar_excel_estilizado_bytes(df_comp, "Comparativo"),
                    file_name=f"comparativo_estoque_{mes_anterior}_vs_{mes_atual}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
