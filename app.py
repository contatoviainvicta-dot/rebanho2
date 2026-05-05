"""
Sistema de Gestão Pecuária — app principal.
Execute com:  streamlit run app.py
"""

import streamlit as st
import pandas as pd

from database import (
    inicializar_banco,
    adicionar_lote, listar_lotes, obter_lote,
    adicionar_animal, listar_animais, listar_animais_por_lote, contar_animais_no_lote,
    adicionar_pesagem, listar_pesagens,
    adicionar_ocorrencia, listar_ocorrencias,
)

# Garante que as tabelas existam antes de qualquer operação
inicializar_banco()

# ---------------------------------------------------------------------------
# SIDEBAR / MENU
# ---------------------------------------------------------------------------
menu = st.sidebar.selectbox(
    "Menu",
    [
        "Cadastrar Lote",
        "Dashboard Sanitário",
        "Cadastrar Animal",
        "Registrar Pesagem",
        "Analisar por Lote",
        "Analisar Animal",
        "Ocorrências Adversas",
        "Painel de Decisão",
        "Pesquisar Ocorrências",
        "Dashboard Executivo",
    ],
)

# ===========================================================================
# CADASTRAR LOTE
# ===========================================================================
if menu == "Cadastrar Lote":
    st.subheader("Novo Lote")

    nome = st.text_input("Nome do lote")
    descricao = st.text_area("Descrição")
    data = st.date_input("Data de entrada")
    qtd_comprada = st.number_input("Quantidade comprada", min_value=0, step=1)
    qtd_recebida = st.number_input("Quantidade recebida", min_value=0, step=1)
    transporte = st.text_input("Transportadora")
    preco_por_animal = st.number_input("Preço por animal (R$)", min_value=0.0)

    tipo_alimentacao = st.selectbox(
        "Tipo de alimentação",
        ["Pasto", "Confinamento", "Semi-confinamento"],
    )
    tipo_dieta = st.selectbox(
        "Tipo de dieta",
        ["Capim", "Ração", "Silagem", "Misto"],
    )

    custo_total = preco_por_animal * qtd_comprada
    st.info(f"💰 Custo total estimado: R$ {custo_total:.2f}")

    if st.button("Salvar Lote"):
        if not nome:
            st.error("Informe o nome do lote")
        elif qtd_recebida > qtd_comprada:
            st.error("Quantidade recebida não pode ser maior que a comprada")
        elif qtd_recebida == 0:
            st.error("Informe a quantidade recebida")
        else:
            adicionar_lote(nome, descricao, str(data), qtd_comprada, qtd_recebida, transporte)
            st.success("Lote criado com sucesso!")

# ===========================================================================
# DASHBOARD SANITÁRIO
# ===========================================================================
elif menu == "Dashboard Sanitário":
    st.subheader("🦠 Dashboard Sanitário")

    # --- Seleção de lote ---
    lotes = listar_lotes()
    opcoes = ["Todos os lotes"]
    dict_lotes = {}
    for l in lotes:
        nome_opcao = f"{l[1]} (ID {l[0]})"
        opcoes.append(nome_opcao)
        dict_lotes[nome_opcao] = l[0]

    escolha = st.selectbox("Selecione o lote para análise", opcoes)

    if escolha == "Todos os lotes":
        animais = listar_animais()
    else:
        lote_id = dict_lotes[escolha]
        animais = listar_animais_por_lote(lote_id)

    # --- Coletar ocorrências ---
    todas_ocorrencias = []
    for animal in animais:
        oc = listar_ocorrencias(animal[0])
        todas_ocorrencias.extend(oc)

    df_oc = pd.DataFrame(
        todas_ocorrencias,
        columns=["id", "animal_id", "data", "tipo", "descricao",
                 "gravidade", "custo", "dias_recuperacao", "status"],
    )

    # --- Métricas ---
    total_animais = len(animais)
    if total_animais > 0 and len(df_oc) > 0:
        animais_com_oc = df_oc["animal_id"].nunique()
        incidencia = (animais_com_oc / total_animais) * 100
    else:
        incidencia = 0

    st.metric("📊 Incidência (%)", f"{incidencia:.2f}%")

    # --- Gráficos de ocorrências ---
    if len(df_oc) > 0:
        st.subheader("📊 Ocorrências por tipo")
        st.bar_chart(df_oc["tipo"].value_counts())

        st.subheader("🚨 Gravidade")
        st.bar_chart(df_oc["gravidade"].value_counts())

    # --- Incidência por lote ---
    st.subheader("🐄 Incidência por lote (%)")
    dados_lote = []
    for lote in lotes:
        lote_id_temp = lote[0]
        nome_lote = lote[1]
        animais_lote = listar_animais_por_lote(lote_id_temp)
        total = len(animais_lote)
        ids_animais = [a[0] for a in animais_lote]

        if len(df_oc) > 0:
            oc_lote = df_oc[df_oc["animal_id"].isin(ids_animais)]
            doentes = oc_lote["animal_id"].nunique()
        else:
            doentes = 0

        incidencia_lote = (doentes / total) * 100 if total > 0 else 0
        dados_lote.append((nome_lote, incidencia_lote))

    if dados_lote:
        df_lote = pd.DataFrame(dados_lote, columns=["Lote", "Incidência (%)"]).set_index("Lote")
        st.bar_chart(df_lote)

    # --- Incidência por tipo ---
    st.subheader("🦠 Incidência por tipo (%)")
    dados_tipo = []
    if total_animais > 0 and len(df_oc) > 0:
        for tipo in df_oc["tipo"].unique():
            df_tipo_filtro = df_oc[df_oc["tipo"] == tipo]
            doentes = df_tipo_filtro["animal_id"].nunique()
            incidencia_tipo = (doentes / total_animais) * 100
            dados_tipo.append((tipo, incidencia_tipo))

        df_tipo_chart = pd.DataFrame(dados_tipo, columns=["Tipo", "Incidência (%)"]).set_index("Tipo")
        st.bar_chart(df_tipo_chart)

    # --- Curva Epidêmica ---
    # FIX: estava dentro de um loop; agora no nível correto do bloco
    st.subheader("📈 Curva Epidêmica")
    if len(df_oc) > 0:
        df_oc["data"] = pd.to_datetime(df_oc["data"])
        curva_tipo = df_oc.groupby(["data", "tipo"]).size().unstack(fill_value=0)
        st.line_chart(curva_tipo)
        # FIX: removido gráfico duplicado (curva total era redundante)
    else:
        st.info("Sem dados suficientes para curva epidêmica")

    # --- Alertas por lote (usando %) ---
    # FIX: removido bloco duplicado de alertas; unificado em um único conjunto
    st.subheader("🚨 Alertas Sanitários")
    for nome, inc in dados_lote:
        if inc > 20:
            st.error(f"🔴 {nome}: alta incidência ({inc:.1f}%)")
        elif inc > 5:
            st.warning(f"🟡 {nome}: incidência moderada ({inc:.1f}%)")
        else:
            st.success(f"🟢 {nome}: controle adequado ({inc:.1f}%)")

    # --- Alertas por tipo ---
    # FIX: `else` estava fora do loop (bug de indentação)
    st.subheader("🚨 Alertas por tipo")
    for tipo, inc in dados_tipo:
        if inc > 20:
            st.error(f"🔴 {tipo}: alta incidência ({inc:.1f}%)")
        elif inc > 5:
            st.warning(f"🟡 {tipo}: incidência moderada ({inc:.1f}%)")
        else:
            st.success(f"🟢 {tipo}: controle adequado ({inc:.1f}%)")

    # --- Correlação GMD x Ocorrências ---
    # FIX: estava indentado dentro do loop de alertas (bug crítico de indentação)
    # FIX: substituído st.session_state.ocorrencias por listar_ocorrencias()
    st.subheader("📉 Correlação: GMD x Ocorrências")
    dados_correlacao = []
    for animal in listar_animais():
        animal_id = animal[0]
        nome_animal = animal[1]
        pesagens = listar_pesagens(animal_id)

        if len(pesagens) > 1:
            df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
            df["Data"] = pd.to_datetime(df["Data"])
            df = df.sort_values("Data")

            peso_inicial = df["Peso"].iloc[0]
            peso_final = df["Peso"].iloc[-1]
            dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days

            if dias > 0:
                gmd_corr = (peso_final - peso_inicial) / dias
                qtd_oc = len(listar_ocorrencias(animal_id))  # FIX: não usa session_state
                dados_correlacao.append((nome_animal, gmd_corr, qtd_oc))

    if dados_correlacao:
        df_corr = pd.DataFrame(dados_correlacao, columns=["Animal", "GMD", "Ocorrencias"])
        st.dataframe(df_corr)

        st.subheader("📊 Dispersão (GMD x Ocorrências)")
        st.scatter_chart(df_corr, x="Ocorrencias", y="GMD")

        st.subheader("🧠 Interpretação")
        media_gmd = df_corr["GMD"].mean()
        for _, row in df_corr.iterrows():
            if row["Ocorrencias"] > 0 and row["GMD"] < media_gmd:
                st.error(f"🔴 {row['Animal']}: baixo GMD associado a ocorrência")
            elif row["Ocorrencias"] > 0:
                st.warning(f"🟡 {row['Animal']}: ocorrência sem impacto aparente")
            elif row["GMD"] < media_gmd:
                st.warning(f"🟠 {row['Animal']}: baixo GMD sem ocorrência registrada")
            else:
                st.success(f"🟢 {row['Animal']}: bom desempenho e saudável")
    else:
        st.info("Sem dados suficientes para correlação")

# ===========================================================================
# CADASTRAR ANIMAL
# ===========================================================================
elif menu == "Cadastrar Animal":
    st.subheader("Novo Animal")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Cadastre um lote primeiro")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        escolha = st.selectbox("Lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha]

        lote = obter_lote(lote_id)
        qtd_recebida = lote[5]
        total_animais = contar_animais_no_lote(lote_id)

        st.info(f"🐄 Animais cadastrados: {total_animais} / {qtd_recebida}")

        if total_animais >= qtd_recebida:
            st.error("⚠️ Limite do lote atingido")
        else:
            identificacao = st.text_input("Identificação do animal")
            idade = st.number_input("Idade (meses)", 0, 240)

            if st.button("Salvar Animal"):
                if not identificacao:
                    st.error("Informe a identificação")
                else:
                    adicionar_animal(identificacao, idade, lote_id)
                    st.success("Animal cadastrado com sucesso!")

# ===========================================================================
# REGISTRAR PESAGEM
# ===========================================================================
elif menu == "Registrar Pesagem":
    st.subheader("Registrar Peso")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Cadastre um lote primeiro")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        escolha_lote = st.selectbox("Selecione o lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha_lote]

        animais = listar_animais_por_lote(lote_id)
        if len(animais) == 0:
            st.warning("Nenhum animal neste lote")
        else:
            dict_animais = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
            escolha_animal = st.selectbox("Selecione o animal", list(dict_animais.keys()))
            animal_id = dict_animais[escolha_animal]

            peso = st.number_input("Peso (kg)", 0.0)
            data = st.date_input("Data")

            if st.button("Salvar Pesagem"):
                if peso <= 0:
                    st.error("Informe um peso válido")
                elif peso > 1000:
                    st.error("Peso muito alto")
                else:
                    adicionar_pesagem(animal_id, peso, str(data))
                    st.success("Pesagem registrada!")

# ===========================================================================
# ANÁLISE POR LOTE
# ===========================================================================
elif menu == "Analisar por Lote":
    st.subheader("Análise por Lote")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        escolha = st.selectbox("Selecione o lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha]

        lote = obter_lote(lote_id)
        animais = listar_animais_por_lote(lote_id)
        st.write(f"🐄 Total: {len(animais)}")

        # --- Parâmetros de custo ---
        st.subheader("💰 Parâmetros de Custo")
        custo_diario = st.number_input("Custo diário por animal (R$)", 0.0, 100.0, 10.0)
        preco_kg = st.number_input("Preço do kg (R$)", 0.0, 50.0, 10.0)

        # --- Período do lote ---
        datas = []
        for animal in animais:
            pesagens = listar_pesagens(animal[0])
            for p in pesagens:
                datas.append(p[3])

        if len(datas) > 1:
            datas_dt = pd.to_datetime(datas)
            dias_lote = (max(datas_dt) - min(datas_dt)).days
        else:
            dias_lote = 0

        numero_animais = len(animais)
        custo_operacional = custo_diario * numero_animais * dias_lote

        st.write(f"📆 Duração do lote: {dias_lote} dias")
        st.write(f"💰 Custo operacional: R$ {custo_operacional:.2f}")

        # --- Ganho total e custo sanitário ---
        ganho_total = 0
        custo_sanitario = 0

        for animal in animais:
            pesagens = listar_pesagens(animal[0])
            if len(pesagens) > 1:
                df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
                df["Data"] = pd.to_datetime(df["Data"])
                df = df.sort_values("Data")
                ganho = df["Peso"].iloc[-1] - df["Peso"].iloc[0]
                if ganho > 0:
                    ganho_total += ganho

            for oc in listar_ocorrencias(animal[0]):
                if oc[6] is not None:
                    custo_sanitario += oc[6]

        receita = ganho_total * preco_kg
        lucro = receita - (custo_operacional + custo_sanitario)

        # --- Resultado econômico ---
        st.subheader("💰 Resultado Econômico")
        st.write(f"📈 Receita estimada: R$ {receita:.2f}")
        st.write(f"💸 Custo operacional: R$ {custo_operacional:.2f}")
        st.write(f"💊 Custo sanitário: R$ {custo_sanitario:.2f}")

        if lucro > 0:
            st.success(f"🟢 Lucro: R$ {lucro:.2f}")
        else:
            st.error(f"🔴 Prejuízo: R$ {lucro:.2f}")

        lucro_por_animal = lucro / len(animais) if len(animais) > 0 else 0
        st.metric("💰 Lucro por animal", f"R$ {lucro_por_animal:.2f}")
        st.metric("💊 Custo sanitário total", f"R$ {custo_sanitario:.2f}")

        # --- Eficiência econômica ---
        if ganho_total > 0:
            custo_kg = custo_operacional / ganho_total
            st.subheader("💰 Eficiência Econômica")
            st.write(f"⚖️ Ganho total: {ganho_total:.2f} kg")
            st.write(f"💸 Custo por kg: R$ {custo_kg:.2f}")
        else:
            st.info("Sem ganho suficiente para cálculo")

        # --- Ranking econômico ---
        ranking_economico = []
        for animal in animais:
            animal_id = animal[0]
            nome_animal = animal[1]
            pesagens = listar_pesagens(animal_id)

            if len(pesagens) > 1:
                df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
                df["Data"] = pd.to_datetime(df["Data"])
                df = df.sort_values("Data")

                peso_inicial = df["Peso"].iloc[0]
                peso_final = df["Peso"].iloc[-1]
                dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days

                if dias > 0:
                    ganho = peso_final - peso_inicial
                    if ganho > 0:
                        custo_animal = custo_diario * dias
                        custo_por_kg = custo_animal / ganho
                        ranking_economico.append((nome_animal, custo_por_kg))

        ranking_economico.sort(key=lambda x: x[1])

        if ranking_economico:
            st.subheader("💰 Ranking Econômico (R$/kg)")
            for i, (nome, custo) in enumerate(ranking_economico, start=1):
                st.write(f"{i}º - {nome} → R$ {custo:.2f}/kg")

            melhor = ranking_economico[0]
            pior = ranking_economico[-1]
            st.success(f"🥇 Mais eficiente: {melhor[0]} (R$ {melhor[1]:.2f}/kg)")
            st.warning(f"⚠️ Menos eficiente: {pior[0]} (R$ {pior[1]:.2f}/kg)")

            st.subheader("🚨 Alertas Econômicos")
            for nome, custo in ranking_economico:
                if custo > 15:
                    st.error(f"🔴 {nome} com custo muito alto (R$ {custo:.2f}/kg)")
                elif custo > 10:
                    st.warning(f"🟡 {nome} com custo moderado (R$ {custo:.2f}/kg)")
        else:
            st.info("Sem dados suficientes para ranking econômico")

        # --- GMD médio do lote ---
        gmds = []
        for animal in animais:
            pesagens = listar_pesagens(animal[0])
            if len(pesagens) > 1:
                df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
                df["Data"] = pd.to_datetime(df["Data"])
                df = df.sort_values("Data")

                peso_inicial = df["Peso"].iloc[0]
                peso_final = df["Peso"].iloc[-1]
                dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days

                if dias > 0:
                    gmd = (peso_final - peso_inicial) / dias
                    if 0 <= gmd <= 2:
                        gmds.append(gmd)

        if gmds:
            gmd_medio = sum(gmds) / len(gmds)
            st.subheader("📈 Desempenho Zootécnico")
            st.write(f"🚀 GMD médio do lote: {gmd_medio:.3f} kg/dia")
            if gmd_medio < 0.5:
                st.warning("⚠️ Lote com baixo desempenho")
            else:
                st.success("✅ Bom desempenho")
        else:
            st.info("Sem dados suficientes para GMD do lote")

        # --- Ranking de GMD por animal ---
        ranking_gmd = []
        for animal in animais:
            animal_id = animal[0]
            nome_animal = animal[1]
            pesagens = listar_pesagens(animal_id)

            if len(pesagens) > 1:
                df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
                df["Data"] = pd.to_datetime(df["Data"])
                df = df.sort_values("Data")

                peso_inicial = df["Peso"].iloc[0]
                peso_final = df["Peso"].iloc[-1]
                dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days

                if dias > 0:
                    gmd = (peso_final - peso_inicial) / dias
                    if 0 <= gmd <= 2:
                        ranking_gmd.append((nome_animal, gmd))

        ranking_gmd.sort(key=lambda x: x[1], reverse=True)

        if ranking_gmd:
            st.subheader("🏆 Ranking de GMD (Animal)")
            for i, (nome, gmd) in enumerate(ranking_gmd, start=1):
                st.write(f"{i}º - {nome} → {gmd:.3f} kg/dia")
            melhor = ranking_gmd[0]
            pior = ranking_gmd[-1]
            st.success(f"🥇 Melhor: {melhor[0]} ({melhor[1]:.3f} kg/dia)")
            st.warning(f"⚠️ Pior: {pior[0]} ({pior[1]:.3f} kg/dia)")
        else:
            st.info("Sem dados suficientes para ranking de GMD")

        # --- Ranking de GMD entre lotes (único, sem duplicata) ---
        # FIX: código duplicado removido; mantida única versão com gráfico
        ranking_lotes = []
        todos_lotes = listar_lotes()

        for lote_item in todos_lotes:
            lote_id_temp = lote_item[0]
            nome_lote = lote_item[1]
            animais_lote = listar_animais_por_lote(lote_id_temp)
            gmds_lote = []

            for animal in animais_lote:
                pesagens = listar_pesagens(animal[0])
                if len(pesagens) > 1:
                    df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
                    df["Data"] = pd.to_datetime(df["Data"])
                    df = df.sort_values("Data")

                    peso_inicial = df["Peso"].iloc[0]
                    peso_final = df["Peso"].iloc[-1]
                    dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days

                    if dias > 0:
                        gmd = (peso_final - peso_inicial) / dias
                        if 0 <= gmd <= 2:
                            gmds_lote.append(gmd)

            if gmds_lote:
                gmd_medio_lote = sum(gmds_lote) / len(gmds_lote)
                ranking_lotes.append((nome_lote, gmd_medio_lote))

        ranking_lotes.sort(key=lambda x: x[1], reverse=True)

        if ranking_lotes:
            st.subheader("📊 Ranking de GMD entre Lotes")
            for i, (nome, gmd) in enumerate(ranking_lotes, start=1):
                st.write(f"{i}º - {nome} → {gmd:.3f} kg/dia")

            df_lotes = pd.DataFrame(ranking_lotes, columns=["Lote", "GMD"]).set_index("Lote")
            st.bar_chart(df_lotes)

            melhor = ranking_lotes[0]
            pior = ranking_lotes[-1]
            st.success(f"🥇 Melhor lote: {melhor[0]} ({melhor[1]:.3f})")
            st.warning(f"⚠️ Pior lote: {pior[0]} ({pior[1]:.3f})")

            # --- Classificação dos lotes ---
            st.subheader("🧠 Classificação dos Lotes")
            for nome, gmd in ranking_lotes:
                if gmd >= 1.0:
                    st.success(f"🟢 {nome}: Excelente desempenho ({gmd:.3f} kg/dia)")
                elif gmd >= 0.7:
                    st.info(f"🔵 {nome}: Bom desempenho ({gmd:.3f} kg/dia)")
                elif gmd >= 0.5:
                    st.warning(f"🟡 {nome}: Desempenho moderado ({gmd:.3f} kg/dia)")
                else:
                    st.error(f"🔴 {nome}: Baixo desempenho ({gmd:.3f} kg/dia)")

            # --- Análise comparativa ---
            if len(ranking_lotes) > 1:
                diferenca = ranking_lotes[0][1] - ranking_lotes[-1][1]
                st.subheader("📊 Análise Comparativa")
                st.write(f"📈 Diferença entre melhor e pior lote: {diferenca:.3f} kg/dia")
                if diferenca > 0.5:
                    st.error("🚨 Alta variabilidade entre lotes → possível problema de manejo")
                elif diferenca > 0.2:
                    st.warning("⚠️ Diferença moderada entre lotes")
                else:
                    st.success("✅ Lotes com desempenho homogêneo")

            # --- Recomendações ---
            st.subheader("🧾 Recomendações de Manejo")
            for nome, gmd in ranking_lotes:
                if gmd < 0.5:
                    st.error(f"🔴 {nome}: Avaliar sanidade, nutrição e manejo URGENTE")
                elif gmd < 0.7:
                    st.warning(f"🟡 {nome}: Ajustar dieta e monitorar ganho")
                else:
                    st.success(f"🟢 {nome}: Manter manejo atual")

            # --- Score de eficiência ---
            ranking_score = []
            for lote_item in todos_lotes:
                lote_id_temp = lote_item[0]
                nome_lote = lote_item[1]
                animais_lote = listar_animais_por_lote(lote_id_temp)
                gmds_l = []
                ganho_t = 0
                dias_t = 0

                for animal in animais_lote:
                    pesagens = listar_pesagens(animal[0])
                    if len(pesagens) > 1:
                        df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
                        df["Data"] = pd.to_datetime(df["Data"])
                        df = df.sort_values("Data")

                        p_ini = df["Peso"].iloc[0]
                        p_fin = df["Peso"].iloc[-1]
                        dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days

                        if dias > 0:
                            ganho = p_fin - p_ini
                            if ganho > 0:
                                gmd = ganho / dias
                                gmds_l.append(gmd)
                                ganho_t += ganho
                                dias_t += dias

                if gmds_l and ganho_t > 0:
                    gmd_m = sum(gmds_l) / len(gmds_l)
                    custo_t = custo_diario * dias_t
                    custo_pk = custo_t / ganho_t
                    score = gmd_m / custo_pk
                    ranking_score.append((nome_lote, score, gmd_m, custo_pk))

            ranking_score.sort(key=lambda x: x[1], reverse=True)

            if ranking_score:
                st.subheader("🏆 Ranking Final de Eficiência")
                for i, (nome, score, gmd, custo) in enumerate(ranking_score, start=1):
                    st.write(
                        f"{i}º - {nome} → Score: {score:.4f} | "
                        f"GMD: {gmd:.3f} | Custo/kg: R$ {custo:.2f}"
                    )
                melhor = ranking_score[0]
                pior = ranking_score[-1]
                st.success(f"🥇 Melhor lote: {melhor[0]} (Score {melhor[1]:.4f})")
                st.error(f"🔴 Pior lote: {pior[0]} (Score {pior[1]:.4f})")
            else:
                st.info("Sem dados suficientes para cálculo do score")
        else:
            st.info("Sem dados suficientes para comparação entre lotes")

# ===========================================================================
# ANÁLISE INDIVIDUAL DO ANIMAL
# ===========================================================================
elif menu == "Analisar Animal":
    st.subheader("🐄 Análise do Animal")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        escolha_lote = st.selectbox("Selecione o lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha_lote]

        animais = listar_animais_por_lote(lote_id)
        if len(animais) == 0:
            st.warning("Nenhum animal neste lote")
        else:
            dict_animais = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
            escolha_animal = st.selectbox("Selecione o animal", list(dict_animais.keys()))
            animal_id = dict_animais[escolha_animal]

            pesagens = listar_pesagens(animal_id)

            # FIX: inicializar gmd antes de usar em bloco posterior
            gmd = None

            if len(pesagens) > 0:
                df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
                df["Data"] = pd.to_datetime(df["Data"])
                df = df.sort_values("Data")

                st.subheader("📊 Histórico de Peso")
                st.dataframe(df)
                st.line_chart(df.set_index("Data")["Peso"])

                if len(df) > 1:
                    peso_inicial = df["Peso"].iloc[0]
                    peso_final = df["Peso"].iloc[-1]
                    dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days

                    if dias > 0:
                        gmd = (peso_final - peso_inicial) / dias
                        st.subheader("🚀 Desempenho")
                        st.write(f"⚖️ Ganho total: {peso_final - peso_inicial:.2f} kg")
                        st.write(f"📆 Período: {dias} dias")
                        st.write(f"📈 GMD: {gmd:.3f} kg/dia")

                        if gmd < 0:
                            st.error("🚨 Perda de peso — possível doença")
                        elif gmd > 2:
                            st.error("🚨 GMD irreal — revisar dados")
                        elif gmd < 0.5:
                            st.warning("⚠️ GMD baixo")
                        else:
                            st.success("✅ Bom desempenho")
                    else:
                        st.info("Intervalo de datas insuficiente")
            else:
                st.info("Sem pesagens registradas")

            ocorrencias = listar_ocorrencias(animal_id)
            st.subheader("🚨 Ocorrências do Animal")

            if len(ocorrencias) > 0:
                df_oc = pd.DataFrame(
                    ocorrencias,
                    columns=["id", "animal_id", "data", "tipo", "descricao",
                             "gravidade", "custo", "dias_recuperacao", "status"],
                )
                df_oc["data"] = pd.to_datetime(df_oc["data"])
                st.dataframe(df_oc)

                for _, row in df_oc.iterrows():
                    if row["gravidade"] == "Alta":
                        st.error(f"🔴 {row['tipo']} - {row['descricao']}")
                    elif row["gravidade"] == "Média":
                        st.warning(f"🟡 {row['tipo']} - {row['descricao']}")
                    else:
                        st.info(f"🔵 {row['tipo']} - {row['descricao']}")
            else:
                st.success("✅ Nenhuma ocorrência registrada")

            # FIX: verificação explícita de gmd is not None (mais robusto que locals())
            if len(pesagens) > 1 and gmd is not None:
                if gmd < 0.5 and len(ocorrencias) > 0:
                    st.error("🚨 Alto risco: baixo desempenho + ocorrência")
                elif gmd < 0.5:
                    st.warning("⚠️ Baixo desempenho")
                elif len(ocorrencias) > 0:
                    st.warning("⚠️ Histórico clínico — monitorar")
                else:
                    st.success("✅ Animal saudável e produtivo")

# ===========================================================================
# OCORRÊNCIAS ADVERSAS
# ===========================================================================
elif menu == "Ocorrências Adversas":
    st.subheader("🚨 Registrar Ocorrência")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        escolha_lote = st.selectbox("Selecione o lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha_lote]

        animais = listar_animais_por_lote(lote_id)
        if len(animais) == 0:
            st.warning("Nenhum animal neste lote")
        else:
            dict_animais = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
            escolha_animal = st.selectbox("Selecione o animal", list(dict_animais.keys()))
            animal_id = dict_animais[escolha_animal]

            with st.form("form_ocorrencia"):
                data = st.date_input("Data")
                tipo = st.selectbox("Tipo", ["Doença", "Lesão", "Medicamento", "Outros"])
                descricao = st.text_area("Descrição")
                gravidade = st.selectbox("Gravidade", ["Baixa", "Média", "Alta"])
                custo = st.number_input("💰 Custo do tratamento (R$)", 0.0)
                dias = st.number_input("⏱️ Dias de recuperação", 0)
                status = st.selectbox("Status", ["Em tratamento", "Resolvido"])
                submitted = st.form_submit_button("Salvar Ocorrência")

                if submitted:
                    adicionar_ocorrencia(animal_id, str(data), tipo, descricao,
                                         gravidade, custo, dias, status)
                    st.success("Ocorrência registrada com sucesso!")

# ===========================================================================
# PAINEL DE DECISÃO
# ===========================================================================
elif menu == "Painel de Decisão":
    st.title("📊 Painel de Decisão")

    preco_kg = st.number_input("Preço do kg (R$)", 0.0, 50.0, 10.0)
    custo_diario = st.number_input("Custo diário por animal (R$)", 0.0, 100.0, 10.0)

    opcao = st.selectbox("Modo de análise", ["Todos os lotes", "Selecionar lote específico"])
    lotes = listar_lotes()

    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado")
        st.stop()

    dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}

    if opcao == "Selecionar lote específico":
        escolha = st.selectbox("Escolha o lote", list(dict_lotes.keys()))
        lote_id_escolhido = dict_lotes[escolha]
        st.info(f"📊 Analisando apenas: {escolha}")
        lotes_para_analise = [l for l in lotes if l[0] == lote_id_escolhido]
    else:
        lotes_para_analise = lotes

    dados_lotes = []
    for lote in lotes_para_analise:
        lote_id = lote[0]
        nome_lote = lote[1]
        animais = listar_animais_por_lote(lote_id)

        ganho_total = 0
        custo_sanitario = 0
        dias_total = 0

        for animal in animais:
            animal_id = animal[0]
            pesagens = listar_pesagens(animal_id)

            if len(pesagens) > 1:
                df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
                df["Data"] = pd.to_datetime(df["Data"])
                df = df.sort_values("Data")
                ganho = df["Peso"].iloc[-1] - df["Peso"].iloc[0]
                dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days
                if ganho > 0 and dias > 0:
                    ganho_total += ganho
                    dias_total += dias

            for oc in listar_ocorrencias(animal_id):
                if oc[6] is not None:
                    custo_sanitario += oc[6]

        numero_animais = len(animais)
        custo_operacional = custo_diario * numero_animais * dias_total
        receita = ganho_total * preco_kg
        lucro = receita - (custo_operacional + custo_sanitario)
        dados_lotes.append((nome_lote, lucro, receita, custo_operacional, custo_sanitario))

    df_decisao = pd.DataFrame(
        dados_lotes,
        columns=["Lote", "Lucro", "Receita", "Custo Operacional", "Custo Sanitário"],
    ).sort_values(by="Lucro", ascending=False)

    st.subheader("📈 Visão Geral")
    if len(df_decisao) > 0:
        total_lucro = df_decisao["Lucro"].sum()
        st.metric("💰 Lucro total", f"R$ {total_lucro:.2f}")
        melhor = df_decisao.iloc[0]
        pior = df_decisao.iloc[-1]
        st.success(f"🥇 Melhor lote: {melhor['Lote']} (R$ {melhor['Lucro']:.2f})")
        st.error(f"🔴 Pior lote: {pior['Lote']} (R$ {pior['Lucro']:.2f})")
    else:
        st.warning("Nenhum lote com dados suficientes")
        st.stop()

    st.subheader("📊 Ranking de Lotes")
    st.dataframe(df_decisao)

    st.subheader("📉 Lucro por lote")
    st.bar_chart(df_decisao.set_index("Lote")["Lucro"])

    st.subheader("🚨 Alertas de Decisão")
    for _, row in df_decisao.iterrows():
        if row["Lucro"] < 0:
            st.error(f"🔴 {row['Lote']}: prejuízo → revisar manejo urgente")
        elif row["Custo Sanitário"] > row["Receita"] * 0.2:
            st.warning(f"🟡 {row['Lote']}: custo sanitário elevado")
        else:
            st.success(f"🟢 {row['Lote']}: operação saudável")

# ===========================================================================
# PESQUISAR OCORRÊNCIAS
# ===========================================================================
elif menu == "Pesquisar Ocorrências":
    st.title("🔎 Pesquisa de Ocorrências")

    lotes = listar_lotes()
    dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}

    escolha_lote = st.selectbox("Filtrar por lote", ["Todos"] + list(dict_lotes.keys()))
    tipo = st.selectbox("Tipo", ["Todos", "Doença", "Lesão", "Medicamento", "Outros"])
    gravidade = st.selectbox("Gravidade", ["Todas", "Baixa", "Média", "Alta"])

    todas_ocorrencias = []
    if escolha_lote == "Todos":
        animais = listar_animais()
    else:
        lote_id = dict_lotes[escolha_lote]
        animais = listar_animais_por_lote(lote_id)

    for animal in animais:
        oc = listar_ocorrencias(animal[0])
        todas_ocorrencias.extend(oc)

    df_oc = pd.DataFrame(
        todas_ocorrencias,
        columns=["id", "animal_id", "data", "tipo", "descricao",
                 "gravidade", "custo", "dias_recuperacao", "status"],
    )

    # FIX: filtros e exibição no mesmo nível de indentação (sem elif perdido)
    if len(df_oc) > 0:
        if tipo != "Todos":
            df_oc = df_oc[df_oc["tipo"] == tipo]
        if gravidade != "Todas":
            df_oc = df_oc[df_oc["gravidade"] == gravidade]
        df_oc["data"] = pd.to_datetime(df_oc["data"])
        df_oc = df_oc.sort_values(by="data", ascending=False)

    st.subheader("📊 Resultados")
    if len(df_oc) > 0:
        st.dataframe(df_oc)

        custo_total = df_oc["custo"].fillna(0).sum()
        st.metric("💰 Custo total", f"R$ {custo_total:.2f}")

        st.subheader("📊 Ocorrências por tipo")
        st.bar_chart(df_oc["tipo"].value_counts())

        if len(df_oc) >= 10:
            st.error("🚨 Alta incidência de ocorrências")
        elif len(df_oc) >= 5:
            st.warning("⚠️ Incidência moderada")
        else:
            st.success("✅ Baixa incidência")

        custo_por_tipo = df_oc.groupby("tipo")["custo"].sum()
        if len(custo_por_tipo) > 0:
            tipo_mais_caro = custo_por_tipo.idxmax()
            valor_mais_caro = custo_por_tipo.max()
            st.warning(
                f"💸 Maior impacto econômico: {tipo_mais_caro} (R$ {valor_mais_caro:.2f})"
            )
    else:
        st.info("Nenhuma ocorrência encontrada com esses filtros")

# ===========================================================================
# ALERTAS INTELIGENTES — FIX: agora dentro do elif correto, não solto no topo
# ===========================================================================
    st.subheader("🧠 Alertas Inteligentes")
    for lote in listar_lotes():
        lote_id = lote[0]
        nome_lote = lote[1]
        animais = listar_animais_por_lote(lote_id)
        total_animais = len(animais)
        if total_animais == 0:
            continue

        todas_oc_lote = []
        gmds = []
        custo_total_lote = 0

        for animal in animais:
            animal_id = animal[0]
            oc = listar_ocorrencias(animal_id)
            todas_oc_lote.extend(oc)
            for o in oc:
                if o[6] is not None:
                    custo_total_lote += o[6]

            pesagens = listar_pesagens(animal_id)
            if len(pesagens) > 1:
                df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
                df["Data"] = pd.to_datetime(df["Data"])
                df = df.sort_values("Data")
                ganho = df["Peso"].iloc[-1] - df["Peso"].iloc[0]
                dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days
                if dias > 0:
                    gmd = ganho / dias
                    if 0 <= gmd <= 2:
                        gmds.append(gmd)

        incidencia = 0
        if todas_oc_lote:
            animais_doentes = len(set([o[1] for o in todas_oc_lote]))
            incidencia = (animais_doentes / total_animais) * 100

        gmd_medio = sum(gmds) / len(gmds) if gmds else 0

        if incidencia > 20 and gmd_medio < 0.5:
            st.error(
                f"🔴 {nome_lote}: Alta incidência ({incidencia:.1f}%) + baixo GMD "
                f"({gmd_medio:.2f}) → possível problema sanitário grave"
            )
        elif custo_total_lote > 1000:
            st.warning(f"🟡 {nome_lote}: Custo sanitário elevado (R$ {custo_total_lote:.2f})")
        elif len(todas_oc_lote) >= 5:
            st.warning(f"🟠 {nome_lote}: Aumento de ocorrências → monitorar possível surto")
        else:
            st.success(
                f"🟢 {nome_lote}: Situação controlada "
                f"(Incidência {incidencia:.1f}%, GMD {gmd_medio:.2f})"
            )

# ===========================================================================
# DASHBOARD EXECUTIVO
# ===========================================================================
elif menu == "Dashboard Executivo":
    st.title("📊 Dashboard Executivo")

    preco_kg = st.number_input("Preço do kg (R$)", 0.0, 50.0, 10.0)
    custo_diario = st.number_input("Custo diário por animal (R$)", 0.0, 100.0, 10.0)

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado")
        st.stop()

    dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    escolha = st.selectbox("Selecione o lote", list(dict_lotes.keys()))
    lote_id = dict_lotes[escolha]

    animais = listar_animais_por_lote(lote_id)
    if len(animais) == 0:
        st.warning("Nenhum animal no lote")
        st.stop()

    ganho_total = 0
    custo_sanitario = 0
    dias_total = 0
    animais_com_oc = set()
    gmds = []

    for animal in animais:
        animal_id = animal[0]
        pesagens = listar_pesagens(animal_id)

        if len(pesagens) > 1:
            df = pd.DataFrame(pesagens, columns=["ID", "Animal", "Peso", "Data"])
            df["Data"] = pd.to_datetime(df["Data"])
            df = df.sort_values("Data")
            ganho = df["Peso"].iloc[-1] - df["Peso"].iloc[0]
            dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days
            if ganho > 0 and dias > 0:
                ganho_total += ganho
                dias_total += dias
                gmd = ganho / dias
                if 0 <= gmd <= 2:
                    gmds.append(gmd)

        ocorrencias = listar_ocorrencias(animal_id)
        if len(ocorrencias) > 0:
            animais_com_oc.add(animal_id)
        for oc in ocorrencias:
            if oc[6] is not None:
                custo_sanitario += oc[6]

    numero_animais = len(animais)
    custo_operacional = custo_diario * numero_animais * dias_total
    receita = ganho_total * preco_kg
    lucro = receita - (custo_operacional + custo_sanitario)

    incidencia = (len(animais_com_oc) / numero_animais) * 100 if numero_animais > 0 else 0
    gmd_medio = sum(gmds) / len(gmds) if gmds else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Lucro", f"R$ {lucro:.2f}")
    col2.metric("🦠 Incidência", f"{incidencia:.2f}%")
    col3.metric("📈 GMD", f"{gmd_medio:.3f} kg/dia")

    st.subheader("🚨 Status do Lote")
    if lucro < 0:
        st.error("🔴 Prejuízo → ação imediata necessária")
    elif incidencia > 20:
        st.error("🔴 Alta incidência sanitária")
    elif gmd_medio < 0.5:
        st.warning("🟡 Baixo desempenho produtivo")
    elif custo_sanitario > receita * 0.2:
        st.warning("🟡 Custo sanitário elevado")
    else:
        st.success("🟢 Lote saudável e lucrativo")

    st.subheader("📋 Resumo")
    st.write(f"🐄 Animais: {numero_animais}")
    st.write(f"⚖️ Ganho total: {ganho_total:.2f} kg")
    st.write(f"💸 Custo sanitário: R$ {custo_sanitario:.2f}")
