
"""
Sistema de Gestão Pecuária — app principal.
Execute com:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

from database import (
    inicializar_banco,
    # funções originais
    adicionar_lote, listar_lotes, obter_lote,
    adicionar_animal, listar_animais, listar_animais_por_lote, contar_animais_no_lote,
    adicionar_pesagem, listar_pesagens,
    adicionar_ocorrencia, listar_ocorrencias,
    # usuários / auth
    criar_usuario, autenticar_usuario, listar_usuarios, usuario_existe, alterar_senha,
    # fazendas
    adicionar_fazenda, listar_fazendas,
    # calendário sanitário
    adicionar_vacina_agenda, registrar_vacina_realizada,
    listar_vacinas_agenda, listar_vacinas_pendentes,
    # medicamentos
    adicionar_medicamento, listar_medicamentos, registrar_uso_medicamento,
    listar_medicamentos_criticos,
    # reprodução
    adicionar_reproducao, atualizar_reproducao, listar_reproducao,
    listar_partos_previstos, taxa_prenhez_lote,
    # piquetes
    adicionar_piquete, listar_piquetes, alocar_lote_piquete,
    liberar_piquete, historico_piquete,
    # trial / plano
    obter_status_plano, converter_para_pago, listar_usuarios_trial_expirando,
    # prontuário / abate
    atualizar_animal_detalhes, obter_animal, calcular_previsao_abate,
)
from exports import gerar_excel_lote, gerar_excel_sanitario, gerar_pdf_relatorio
from notifications import (
    email_boas_vindas, email_trial_expirando, email_trial_expirado,
    email_vacina_pendente, email_medicamento_critico,
    email_parto_previsto, email_abate_previsto, email_configurado,
)

inicializar_banco()

# ===========================================================================
# AUTENTICAÇÃO
# ===========================================================================
if "usuario" not in st.session_state:
    st.session_state.usuario = None

def _tela_login():
    st.title("🐄 Sistema de Gestão Pecuária")
    st.subheader("Acesso ao sistema")

    if not usuario_existe():
        st.info("Nenhum usuário cadastrado. Crie o primeiro acesso abaixo.")
        with st.form("form_primeiro_usuario"):
            nome  = st.text_input("Seu nome")
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            perfil = st.selectbox("Perfil", ["veterinario", "fazendeiro", "admin"])
            if st.form_submit_button("Criar conta"):
                if nome and email and senha:
                    from database import ativar_trial
                    uid = criar_usuario(nome, email, senha, perfil)
                    ativar_trial(uid)
                    email_boas_vindas(email, nome)
                    st.success("Conta criada! Você tem 30 dias de trial gratuito. Faça login.")
                    st.rerun()
                else:
                    st.error("Preencha todos os campos.")
        return

    with st.form("form_login"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            u = autenticar_usuario(email, senha)
            if u:
                st.session_state.usuario = u
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")

if st.session_state.usuario is None:
    _tela_login()
    st.stop()

# ---------------------------------------------------------------------------
# SIDEBAR — usuário logado
# ---------------------------------------------------------------------------
u = st.session_state.usuario
st.sidebar.markdown(f"👤 **{u['nome']}**  \n*{u['perfil']}*")
if st.sidebar.button("Sair"):
    st.session_state.usuario = None
    st.rerun()

# --- Banner de trial na sidebar ---
_status_plano = obter_status_plano(u["id"])
if _status_plano["plano"] == "trial":
    _dr = _status_plano["dias_restantes"]
    if _dr <= 3:
        st.sidebar.error(f"🔴 Trial: {_dr} dia(s) restante(s)!")
    elif _dr <= 7:
        st.sidebar.warning(f"⚠️ Trial: {_dr} dias restantes")
        if email_configurado():
            email_trial_expirando(u["email"], u["nome"], _dr)
    else:
        st.sidebar.info(f"🕐 Trial: {_dr} dias restantes")
elif _status_plano["plano"] == "expirado":
    st.sidebar.error("🔴 Trial expirado — somente leitura")
    if email_configurado():
        email_trial_expirado(u["email"], u["nome"])
else:
    st.sidebar.success("✅ Plano ativo")

st.sidebar.divider()

# Alertas rápidos na sidebar
_pendentes = listar_vacinas_pendentes()
_criticos  = listar_medicamentos_criticos()
_partos    = listar_partos_previstos()
if _pendentes:
    st.sidebar.warning(f"💉 {len(_pendentes)} vacina(s) pendente(s)")
if _criticos:
    st.sidebar.error(f"💊 {len(_criticos)} medicamento(s) em alerta")
if _partos:
    st.sidebar.info(f"🐄 {len(_partos)} parto(s) previstos em 30 dias")

st.sidebar.divider()

menu = st.sidebar.selectbox(
    "Menu",
    [
        # ── originais ──────────────────────────────
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
        # ── novos ──────────────────────────────────
        "── Novos Módulos ──",
        "Calendário Sanitário",
        "Estoque de Medicamentos",
        "Controle Reprodutivo",
        "Mapa de Piquetes",
        "Exportar Relatórios",
        "Previsão de Abate",
        "Prontuário do Animal",
        "Notificações",
        "Administração",
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

# ===========================================================================
# SEPARADOR DE MENU (item não clicável)
# ===========================================================================
elif menu == "── Novos Módulos ──":
    st.info("Selecione um módulo no menu lateral.")

# ===========================================================================
# CALENDÁRIO SANITÁRIO
# ===========================================================================
elif menu == "Calendário Sanitário":
    st.title("💉 Calendário Sanitário")

    tab1, tab2, tab3 = st.tabs(["📋 Agenda", "➕ Agendar Vacina", "✅ Registrar Realização"])

    with tab1:
        st.subheader("Agenda de Vacinas")
        lotes = listar_lotes()
        opcoes = ["Todos os lotes"] + [f"{l[1]} (ID {l[0]})" for l in lotes]
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        filtro = st.selectbox("Filtrar por lote", opcoes, key="cal_filtro")

        lote_id_fil = dict_lotes.get(filtro) if filtro != "Todos os lotes" else None
        vacinas = listar_vacinas_agenda(lote_id_fil)

        if vacinas:
            df_v = pd.DataFrame(vacinas, columns=["ID","Lote ID","Vacina","Previsto","Realizado","Status","Observação"])
            df_v["Previsto"] = pd.to_datetime(df_v["Previsto"]).dt.strftime("%d/%m/%Y")
            df_v["Realizado"] = pd.to_datetime(df_v["Realizado"], errors="coerce").dt.strftime("%d/%m/%Y")

            hoje = date.today()
            for _, row in df_v.iterrows():
                try:
                    dt_prev = datetime.strptime(row["Previsto"], "%d/%m/%Y").date()
                    atrasado = dt_prev < hoje and row["Status"] == "pendente"
                except Exception:
                    atrasado = False
                if row["Status"] == "realizado":
                    st.success(f"✅ {row['Vacina']} — Lote {row['Lote ID']} — Realizado em {row['Realizado']}")
                elif atrasado:
                    st.error(f"🔴 ATRASADA: {row['Vacina']} — Previsto {row['Previsto']}")
                else:
                    st.warning(f"🟡 Pendente: {row['Vacina']} — Previsto {row['Previsto']}")

            st.dataframe(df_v, use_container_width=True)

            # Exportar
            vacinas_todas = listar_vacinas_agenda()
            meds = listar_medicamentos()
            xls = gerar_excel_sanitario(vacinas_todas, meds)
            st.download_button("⬇️ Exportar Excel", xls,
                               "agenda_sanitaria.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("Nenhuma vacina agendada.")

    with tab2:
        st.subheader("Agendar Vacina / Medicação")
        lotes = listar_lotes()
        if not lotes:
            st.warning("Cadastre um lote primeiro.")
        else:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            with st.form("form_vacina"):
                lote_sel = st.selectbox("Lote", list(dict_l.keys()))
                nome_vac = st.text_input("Nome da vacina / procedimento")
                data_prev = st.date_input("Data prevista", value=date.today() + timedelta(days=7))
                obs = st.text_area("Observação")
                if st.form_submit_button("Agendar"):
                    if nome_vac:
                        adicionar_vacina_agenda(dict_l[lote_sel], nome_vac, str(data_prev), obs)
                        st.success("Vacina agendada!")
                        st.rerun()
                    else:
                        st.error("Informe o nome da vacina.")

    with tab3:
        st.subheader("Registrar Vacina Realizada")
        pendentes = listar_vacinas_pendentes()
        if not pendentes:
            st.success("Nenhuma vacina pendente.")
        else:
            df_p = pd.DataFrame(pendentes,
                                columns=["ID","Lote ID","Lote","Vacina","Previsto","Status","Obs"])
            opcoes_v = {f"{r['Vacina']} — {r['Lote']} (prev. {r['Previsto']})": r["ID"]
                        for _, r in df_p.iterrows()}
            with st.form("form_real"):
                sel = st.selectbox("Vacina", list(opcoes_v.keys()))
                data_real = st.date_input("Data de realização", value=date.today())
                if st.form_submit_button("Confirmar Realização"):
                    registrar_vacina_realizada(opcoes_v[sel], str(data_real))
                    st.success("Registrado!")
                    st.rerun()

# ===========================================================================
# ESTOQUE DE MEDICAMENTOS
# ===========================================================================
elif menu == "Estoque de Medicamentos":
    st.title("💊 Estoque de Medicamentos")

    tab1, tab2, tab3 = st.tabs(["📦 Estoque Atual", "➕ Cadastrar", "💉 Registrar Uso"])

    with tab1:
        meds = listar_medicamentos()
        criticos = listar_medicamentos_criticos()

        if criticos:
            st.error(f"🚨 {len(criticos)} medicamento(s) em alerta de estoque ou validade:")
            for m in criticos:
                motivo = "estoque baixo" if m[3] <= m[4] else f"vence em {m[5]}"
                st.warning(f"⚠️ {m[1]} — {m[3]:.1f} {m[2]} ({motivo})")

        if meds:
            df_m = pd.DataFrame(meds,
                                columns=["ID","Nome","Unidade","Estoque Atual",
                                         "Estoque Mínimo","Validade","Custo Unit. R$"])
            st.dataframe(df_m, use_container_width=True)

            col1, col2 = st.columns(2)
            valor_total = sum(m[3] * m[6] for m in meds)
            col1.metric("💰 Valor total em estoque", f"R$ {valor_total:.2f}")
            col2.metric("📦 Itens cadastrados", len(meds))

            # Exportar
            vacinas_todas = listar_vacinas_agenda()
            xls = gerar_excel_sanitario(vacinas_todas, meds)
            st.download_button("⬇️ Exportar Excel", xls,
                               "estoque_medicamentos.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("Nenhum medicamento cadastrado.")

    with tab2:
        with st.form("form_med"):
            nome_m = st.text_input("Nome do medicamento")
            unid   = st.selectbox("Unidade", ["dose","mL","g","comprimido","frasco","kg"])
            estq   = st.number_input("Estoque inicial", 0.0, step=1.0)
            est_min = st.number_input("Estoque mínimo (alerta)", 0.0, step=1.0)
            valid  = st.date_input("Validade")
            custo  = st.number_input("Custo unitário (R$)", 0.0)
            if st.form_submit_button("Cadastrar"):
                if nome_m:
                    adicionar_medicamento(nome_m, unid, estq, est_min, str(valid), custo)
                    st.success("Medicamento cadastrado!")
                    st.rerun()
                else:
                    st.error("Informe o nome.")

    with tab3:
        meds = listar_medicamentos()
        lotes = listar_lotes()
        if not meds:
            st.warning("Cadastre medicamentos primeiro.")
        elif not lotes:
            st.warning("Cadastre um lote primeiro.")
        else:
            dict_m = {f"{m[1]} ({m[3]:.1f} {m[2]})": m[0] for m in meds}
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            with st.form("form_uso"):
                med_sel  = st.selectbox("Medicamento", list(dict_m.keys()))
                lote_sel = st.selectbox("Lote", list(dict_l.keys()))
                animais  = listar_animais_por_lote(dict_l[lote_sel])
                dict_a   = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
                anim_sel = st.selectbox("Animal", list(dict_a.keys()) if dict_a else ["—"])
                qtd_uso  = st.number_input("Quantidade utilizada", 0.01, step=0.5)
                data_uso = st.date_input("Data")
                if st.form_submit_button("Registrar Uso") and dict_a:
                    registrar_uso_medicamento(
                        dict_m[med_sel], dict_a[anim_sel], str(data_uso), qtd_uso
                    )
                    st.success("Uso registrado e estoque atualizado!")
                    st.rerun()

# ===========================================================================
# CONTROLE REPRODUTIVO
# ===========================================================================
elif menu == "Controle Reprodutivo":
    st.title("🐄 Controle Reprodutivo")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Indicadores", "➕ Registrar Cobertura", "✏️ Atualizar Diagnóstico", "🗓️ Partos Previstos"]
    )

    with tab1:
        lotes = listar_lotes()
        if not lotes:
            st.warning("Nenhum lote cadastrado.")
        else:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            lote_sel = st.selectbox("Lote", list(dict_l.keys()), key="rep_lote")
            lote_id = dict_l[lote_sel]

            tp = taxa_prenhez_lote(lote_id)
            col1, col2, col3 = st.columns(3)
            col1.metric("🐄 Animais com registro", tp["total"])
            col2.metric("✅ Gestações confirmadas", tp["positivas"])
            col3.metric("📊 Taxa de prenhez", f"{tp['taxa']:.1f}%")

            animais = listar_animais_por_lote(lote_id)
            dados = []
            for a in animais:
                repros = listar_reproducao(a[0])
                if repros:
                    r = repros[0]
                    dados.append({
                        "Animal": a[1],
                        "Tipo": r[3],
                        "Data Cio": r[2] or "—",
                        "Diagnóstico": r[4] or "—",
                        "Resultado": r[5],
                        "Parto Previsto": r[6] or "—",
                        "Parto Real": r[7] or "—",
                    })
            if dados:
                st.dataframe(pd.DataFrame(dados), use_container_width=True)
            else:
                st.info("Nenhum registro reprodutivo neste lote.")

    with tab2:
        lotes = listar_lotes()
        if not lotes:
            st.warning("Nenhum lote cadastrado.")
        else:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            with st.form("form_cobertura"):
                lote_s = st.selectbox("Lote", list(dict_l.keys()))
                animais = listar_animais_por_lote(dict_l[lote_s])
                dict_a  = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
                anim_s  = st.selectbox("Animal", list(dict_a.keys()) if dict_a else ["—"])
                tipo_c  = st.selectbox("Tipo de cobertura", ["IATF","Monta Natural","TE"])
                data_cio = st.date_input("Data do cio / IATF")
                obs_r    = st.text_area("Observação")
                if st.form_submit_button("Registrar") and dict_a:
                    adicionar_reproducao(dict_a[anim_s], tipo_c,
                                         data_cio=str(data_cio), observacao=obs_r)
                    st.success("Cobertura registrada!")
                    st.rerun()

    with tab3:
        lotes = listar_lotes()
        if lotes:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            lote_s = st.selectbox("Lote", list(dict_l.keys()), key="rep_upd_lote")
            animais = listar_animais_por_lote(dict_l[lote_s])
            dict_a  = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
            if dict_a:
                anim_s = st.selectbox("Animal", list(dict_a.keys()), key="rep_upd_anim")
                repros = listar_reproducao(dict_a[anim_s])
                if repros:
                    r = repros[0]
                    st.info(f"Último registro: tipo={r[3]}, resultado atual={r[5]}")
                    with st.form("form_diag"):
                        resultado  = st.selectbox("Resultado diagnóstico",
                                                   ["pendente","positivo","negativo"])
                        data_diag  = st.date_input("Data do diagnóstico")
                        parto_prev = st.date_input("Parto previsto (se positivo)",
                                                    value=date.today() + timedelta(days=283))
                        if st.form_submit_button("Salvar Diagnóstico"):
                            atualizar_reproducao(r[0], resultado,
                                                  data_diagnostico=str(data_diag),
                                                  data_parto_previsto=str(parto_prev)
                                                  if resultado == "positivo" else None)
                            st.success("Diagnóstico atualizado!")
                            st.rerun()
                else:
                    st.info("Sem registros reprodutivos para este animal.")

    with tab4:
        partos = listar_partos_previstos()
        if partos:
            st.warning(f"🗓️ {len(partos)} parto(s) previstos nos próximos 30 dias:")
            df_p = pd.DataFrame(partos,
                                columns=["ID","Animal","Lote","Parto Previsto","Tipo"])
            st.dataframe(df_p, use_container_width=True)
        else:
            st.success("Nenhum parto previsto para os próximos 30 dias.")

# ===========================================================================
# MAPA DE PIQUETES
# ===========================================================================
elif menu == "Mapa de Piquetes":
    st.title("🌿 Mapa de Piquetes e Pastagens")

    tab1, tab2, tab3 = st.tabs(["📋 Piquetes", "➕ Cadastrar", "🔄 Alocar / Liberar"])

    with tab1:
        piquetes = listar_piquetes()
        if piquetes:
            df_pq = pd.DataFrame(piquetes,
                                  columns=["ID","Fazenda ID","Nome","Área (ha)","Cap. UA"])
            st.dataframe(df_pq, use_container_width=True)

            col1, col2 = st.columns(2)
            col1.metric("🌿 Total de piquetes", len(piquetes))
            area_total = sum(p[3] for p in piquetes)
            col2.metric("📐 Área total (ha)", f"{area_total:.1f}")

            st.subheader("📜 Histórico de ocupação")
            dict_pq = {f"{p[2]} (ID {p[0]})": p[0] for p in piquetes}
            sel_pq = st.selectbox("Piquete", list(dict_pq.keys()))
            hist = historico_piquete(dict_pq[sel_pq])
            if hist:
                df_h = pd.DataFrame(hist, columns=["ID","Lote","Entrada","Saída"])
                st.dataframe(df_h, use_container_width=True)
            else:
                st.info("Nenhum histórico para este piquete.")
        else:
            st.info("Nenhum piquete cadastrado.")

    with tab2:
        with st.form("form_piquete"):
            nome_pq = st.text_input("Nome do piquete")
            area    = st.number_input("Área (ha)", 0.0, step=0.5)
            cap_ua  = st.number_input("Capacidade (UA)", 0.0, step=1.0)
            if st.form_submit_button("Cadastrar"):
                if nome_pq:
                    adicionar_piquete(nome_pq, area, cap_ua)
                    st.success("Piquete cadastrado!")
                    st.rerun()
                else:
                    st.error("Informe o nome.")

    with tab3:
        piquetes = listar_piquetes()
        lotes    = listar_lotes()
        if not piquetes or not lotes:
            st.warning("Cadastre piquetes e lotes primeiro.")
        else:
            dict_pq = {f"{p[2]} (ID {p[0]})": p[0] for p in piquetes}
            dict_l  = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Alocar lote")
                with st.form("form_alocar"):
                    pq_sel  = st.selectbox("Piquete", list(dict_pq.keys()), key="al_pq")
                    lt_sel  = st.selectbox("Lote", list(dict_l.keys()), key="al_lt")
                    dt_ent  = st.date_input("Data de entrada", key="al_dt")
                    if st.form_submit_button("Alocar"):
                        alocar_lote_piquete(dict_pq[pq_sel], dict_l[lt_sel], str(dt_ent))
                        st.success("Lote alocado!")
                        st.rerun()
            with col2:
                st.subheader("Liberar piquete")
                with st.form("form_liberar"):
                    pq_sel2 = st.selectbox("Piquete", list(dict_pq.keys()), key="lib_pq")
                    dt_said = st.date_input("Data de saída", key="lib_dt")
                    if st.form_submit_button("Liberar"):
                        liberar_piquete(dict_pq[pq_sel2], str(dt_said))
                        st.success("Piquete liberado!")
                        st.rerun()

# ===========================================================================
# EXPORTAR RELATÓRIOS
# ===========================================================================
elif menu == "Exportar Relatórios":
    st.title("📄 Exportar Relatórios")

    lotes = listar_lotes()
    if not lotes:
        st.warning("Nenhum lote cadastrado.")
        st.stop()

    dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    lote_sel = st.selectbox("Selecione o lote", list(dict_l.keys()))
    lote_id  = dict_l[lote_sel]
    nome_lote = lote_sel.split(" (ID")[0]

    animais = listar_animais_por_lote(lote_id)
    pesagens_dict    = {a[0]: listar_pesagens(a[0])    for a in animais}
    ocorrencias_dict = {a[0]: listar_ocorrencias(a[0]) for a in animais}

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Excel — Dados do Lote")
        st.write("Abas: Resumo, Animais, Pesagens, Ocorrências")
        if st.button("Gerar Excel"):
            xls = gerar_excel_lote(nome_lote, animais, pesagens_dict, ocorrencias_dict)
            st.download_button(
                "⬇️ Baixar Excel",
                xls,
                f"lote_{nome_lote.replace(' ','_')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    with col2:
        st.subheader("📋 PDF — Relatório do Lote")
        st.write("Resumo + tabelas de animais, pesagens e ocorrências")
        if st.button("Gerar PDF"):
            df_anim = pd.DataFrame(animais, columns=["ID","Identificação","Idade","Lote ID"])

            todos_pesos = [p for ps in pesagens_dict.values() for p in ps]
            df_peso = pd.DataFrame(todos_pesos,
                                    columns=["ID","Animal ID","Peso (kg)","Data"]) if todos_pesos else pd.DataFrame()

            todos_oc = [o for ocs in ocorrencias_dict.values() for o in ocs]
            df_oc = pd.DataFrame(todos_oc,
                                  columns=["ID","Animal ID","Data","Tipo","Descrição",
                                           "Gravidade","Custo","Dias","Status"]) if todos_oc else pd.DataFrame()

            secoes = [
                {"titulo": "Animais do lote",  "df": df_anim},
                {"titulo": "Histórico de pesagens", "df": df_peso},
                {"titulo": "Ocorrências registradas", "df": df_oc},
            ]
            pdf = gerar_pdf_relatorio(f"Relatório — {nome_lote}", secoes)
            st.download_button(
                "⬇️ Baixar PDF",
                pdf,
                f"relatorio_{nome_lote.replace(' ','_')}.pdf",
                "application/pdf",
            )

    st.divider()
    st.subheader("💊 Excel — Calendário Sanitário e Medicamentos")
    if st.button("Gerar Excel Sanitário"):
        vacinas = listar_vacinas_agenda()
        meds    = listar_medicamentos()
        xls = gerar_excel_sanitario(vacinas, meds)
        st.download_button(
            "⬇️ Baixar Excel Sanitário",
            xls,
            "sanitario.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ===========================================================================
# ADMINISTRAÇÃO
# ===========================================================================
elif menu == "Administração":
    st.title("⚙️ Administração")

    # Só admin vê tudo; outros veem apenas alterar senha
    is_admin = u["perfil"] == "admin"

    tab1, tab2 = st.tabs(["👤 Usuários", "🔑 Alterar Minha Senha"])

    with tab1:
        if not is_admin:
            st.warning("Acesso restrito a administradores.")
        else:
            st.subheader("Usuários cadastrados")
            usuarios = listar_usuarios()
            if usuarios:
                df_u = pd.DataFrame(usuarios,
                                     columns=["ID","Nome","E-mail","Perfil","Fazenda ID"])
                st.dataframe(df_u, use_container_width=True)

            st.subheader("Criar novo usuário")
            with st.form("form_novo_user"):
                n_nome   = st.text_input("Nome")
                n_email  = st.text_input("E-mail")
                n_senha  = st.text_input("Senha", type="password")
                n_perfil = st.selectbox("Perfil", ["fazendeiro","veterinario","admin"])
                if st.form_submit_button("Criar"):
                    if n_nome and n_email and n_senha:
                        try:
                            criar_usuario(n_nome, n_email, n_senha, n_perfil)
                            st.success("Usuário criado!")
                            st.rerun()
                        except Exception:
                            st.error("E-mail já cadastrado.")
                    else:
                        st.error("Preencha todos os campos.")

    with tab2:
        with st.form("form_senha"):
            senha_atual = st.text_input("Senha atual", type="password")
            nova_senha  = st.text_input("Nova senha", type="password")
            conf_senha  = st.text_input("Confirmar nova senha", type="password")
            if st.form_submit_button("Alterar Senha"):
                if not autenticar_usuario(u["email"], senha_atual):
                    st.error("Senha atual incorreta.")
                elif nova_senha != conf_senha:
                    st.error("As senhas não coincidem.")
                elif len(nova_senha) < 6:
                    st.error("Senha deve ter ao menos 6 caracteres.")
                else:
                    alterar_senha(u["id"], nova_senha)
                    st.success("Senha alterada com sucesso!")

# ===========================================================================
# PREVISÃO DE ABATE
# ===========================================================================
elif menu == "Previsão de Abate":
    st.title("🥩 Previsão de Abate")

    lotes = listar_lotes()
    if not lotes:
        st.warning("Nenhum lote cadastrado.")
        st.stop()

    dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    lote_sel = st.selectbox("Selecione o lote", list(dict_l.keys()))
    lote_id  = dict_l[lote_sel]
    animais  = listar_animais_por_lote(lote_id)

    if not animais:
        st.warning("Nenhum animal neste lote.")
        st.stop()

    st.info("💡 Defina o peso alvo em **Prontuário do Animal** para cada animal antes de usar esta tela.")

    preco_kg = st.number_input("Preço do kg no abate (R$)", 0.0, 100.0, 20.0)

    resultados = []
    prontos_email = []

    for a in animais:
        prev = calcular_previsao_abate(a[0])
        if "erro" not in prev:
            resultados.append({
                "Animal": a[1],
                "Peso Atual (kg)": prev["peso_atual"],
                "Peso Alvo (kg)": prev["peso_alvo"],
                "GMD (kg/dia)": prev["gmd"],
                "Dias Restantes": prev["dias_restantes"],
                "Data Prevista": prev["data_prevista"],
                "Receita Estimada (R$)": round(prev["peso_alvo"] * preco_kg, 2),
                "Confiança": prev["confianca"],
            })
            if prev["dias_restantes"] <= 30:
                prontos_email.append({
                    "animal": a[1], "lote": lote_sel.split(" (ID")[0],
                    "peso_atual": prev["peso_atual"], "peso_alvo": prev["peso_alvo"],
                    "data_prevista": prev["data_prevista"],
                })

    if resultados:
        df_prev = pd.DataFrame(resultados).sort_values("Dias Restantes")
        st.dataframe(df_prev, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("🐄 Animais analisados", len(resultados))
        col2.metric("⏳ Prontos em ≤30 dias", len(prontos_email))
        receita_total = sum(r["Receita Estimada (R$)"] for r in resultados)
        col3.metric("💰 Receita total estimada", f"R$ {receita_total:,.2f}")

        # Gráfico de barras: dias restantes por animal
        df_chart = df_prev.set_index("Animal")[["Dias Restantes"]]
        st.subheader("📊 Dias até o peso de abate por animal")
        st.bar_chart(df_chart)

        # Alertas
        st.subheader("🚨 Alertas")
        for r in resultados:
            if r["Dias Restantes"] == 0:
                st.success(f"✅ {r['Animal']}: já atingiu o peso alvo!")
            elif r["Dias Restantes"] <= 15:
                st.warning(f"🟡 {r['Animal']}: {r['Dias Restantes']} dias — prepare o abate")
            elif r["Confiança"] == "baixa":
                st.info(f"ℹ️ {r['Animal']}: previsão com baixa confiança (poucas pesagens)")

        # Notificação por e-mail
        if prontos_email and email_configurado():
            if st.button("📧 Enviar alerta de abate por e-mail"):
                ok, msg = email_abate_previsto(u["email"], u["nome"], prontos_email)
                st.success(msg) if ok else st.warning(msg)
    else:
        st.info("Nenhum animal com peso alvo definido e pesagens suficientes.\n\nDefina o peso alvo em **Prontuário do Animal**.")

# ===========================================================================
# PRONTUÁRIO DO ANIMAL
# ===========================================================================
elif menu == "Prontuário do Animal":
    st.title("📋 Prontuário do Animal")

    lotes = listar_lotes()
    if not lotes:
        st.warning("Nenhum lote cadastrado.")
        st.stop()

    dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    lote_sel = st.selectbox("Lote", list(dict_l.keys()))
    animais  = listar_animais_por_lote(dict_l[lote_sel])

    if not animais:
        st.warning("Nenhum animal neste lote.")
        st.stop()

    dict_a   = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
    anim_sel = st.selectbox("Animal", list(dict_a.keys()))
    animal_id = dict_a[anim_sel]

    det = obter_animal(animal_id)

    tab1, tab2, tab3 = st.tabs(["📋 Dados", "⚖️ Pesagens", "🚨 Ocorrências"])

    with tab1:
        st.subheader("Informações do Animal")
        with st.form("form_prontuario"):
            col1, col2 = st.columns(2)
            with col1:
                peso_alvo = st.number_input("Peso alvo de abate (kg)",
                                             0.0, 1000.0,
                                             float(det[7]) if det else 0.0)
                sexo = st.selectbox("Sexo", ["indefinido","macho","fêmea"],
                                    index=["indefinido","macho","fêmea"].index(
                                        det[4] if det and det[4] in ["indefinido","macho","fêmea"] else "indefinido"))
                raca = st.text_input("Raça", value=det[5] if det else "")
            with col2:
                obs = st.text_area("Observações clínicas",
                                   value=det[8] if det else "", height=120)

            if st.form_submit_button("💾 Salvar Prontuário"):
                atualizar_animal_detalhes(animal_id,
                                          peso_alvo=peso_alvo,
                                          observacoes=obs)
                st.success("Prontuário atualizado!")
                st.rerun()

        # Previsão de abate inline
        if det and det[7] > 0:
            prev = calcular_previsao_abate(animal_id)
            if "erro" not in prev:
                st.divider()
                st.subheader("🥩 Previsão de Abate")
                c1, c2, c3 = st.columns(3)
                c1.metric("GMD atual", f"{prev['gmd']:.3f} kg/dia")
                c2.metric("Dias restantes", prev["dias_restantes"])
                c3.metric("Data prevista", prev["data_prevista"])
                if prev["confianca"] == "baixa":
                    st.caption("⚠️ Confiança baixa — registre mais pesagens para melhorar a previsão.")

    with tab2:
        pesagens = listar_pesagens(animal_id)
        if pesagens:
            df_p = pd.DataFrame(pesagens, columns=["ID","Animal","Peso","Data"])
            df_p["Data"] = pd.to_datetime(df_p["Data"])
            df_p = df_p.sort_values("Data")
            st.line_chart(df_p.set_index("Data")["Peso"])
            st.dataframe(df_p, use_container_width=True)
        else:
            st.info("Nenhuma pesagem registrada.")

    with tab3:
        ocs = listar_ocorrencias(animal_id)
        if ocs:
            df_oc = pd.DataFrame(ocs, columns=["ID","Animal ID","Data","Tipo",
                                                "Descrição","Gravidade","Custo",
                                                "Dias Rec.","Status"])
            st.dataframe(df_oc, use_container_width=True)
            custo_total = sum(o[6] for o in ocs if o[6])
            st.metric("💊 Custo total de tratamentos", f"R$ {custo_total:.2f}")
        else:
            st.success("✅ Nenhuma ocorrência registrada.")

        # Histórico reprodutivo
        repros = listar_reproducao(animal_id)
        if repros:
            st.subheader("🐄 Histórico Reprodutivo")
            df_r = pd.DataFrame(repros, columns=["ID","Animal","Cio","Tipo",
                                                   "Diagnóstico","Resultado",
                                                   "Parto Previsto","Parto Real","Obs"])
            st.dataframe(df_r, use_container_width=True)

# ===========================================================================
# NOTIFICAÇÕES
# ===========================================================================
elif menu == "Notificações":
    st.title("📧 Central de Notificações")

    if not email_configurado():
        st.warning("⚠️ E-mail não configurado.")
        st.markdown("""
        Para ativar as notificações, crie o arquivo `.streamlit/secrets.toml` com:
        ```toml
        [email]
        smtp_host     = "smtp.gmail.com"
        smtp_port     = 587
        smtp_user     = "seu@gmail.com"
        smtp_password = "senha_app_google"
        remetente     = "Gestão Pecuária <seu@gmail.com>"
        ```
        Para Gmail, use uma **Senha de App** (não a senha da conta).
        [Como criar →](https://support.google.com/accounts/answer/185833)
        """)
        st.stop()

    st.success("✅ E-mail configurado e pronto para envio.")

    st.subheader("📤 Enviar alertas agora")

    col1, col2 = st.columns(2)

    with col1:
        # Vacinas pendentes
        pendentes = listar_vacinas_pendentes()
        st.metric("💉 Vacinas pendentes", len(pendentes))
        if pendentes and st.button("Enviar alerta de vacinas"):
            vacs = [{"lote": v[2], "vacina": v[3], "data_prevista": v[4]}
                    for v in pendentes]
            ok, msg = email_vacina_pendente(u["email"], u["nome"], vacs)
            st.success(msg) if ok else st.error(msg)

        # Partos previstos
        partos = listar_partos_previstos()
        st.metric("🐄 Partos previstos (30d)", len(partos))
        if partos and st.button("Enviar alerta de partos"):
            pts = [{"animal": p[1], "lote": p[2], "data_parto_previsto": p[3]}
                   for p in partos]
            ok, msg = email_parto_previsto(u["email"], u["nome"], pts)
            st.success(msg) if ok else st.error(msg)

    with col2:
        # Medicamentos críticos
        criticos = listar_medicamentos_criticos()
        st.metric("💊 Medicamentos em alerta", len(criticos))
        if criticos and st.button("Enviar alerta de medicamentos"):
            meds = [{"nome": m[1], "estoque_atual": m[3],
                     "unidade": m[2], "validade": m[5] or ""}
                    for m in criticos]
            ok, msg = email_medicamento_critico(u["email"], u["nome"], meds)
            st.success(msg) if ok else st.error(msg)

        # Trial expirando (só admin)
        if u["perfil"] == "admin":
            expirando = listar_usuarios_trial_expirando(dias=7)
            st.metric("⏳ Trials expirando (7d)", len(expirando))
            if expirando and st.button("Enviar avisos de trial"):
                enviados = 0
                for usr in expirando:
                    from datetime import date as _dtoday
                    dias = (_dtoday.fromisoformat(usr[3]) - _dtoday.today()).days if usr[3] else 0
                    ok, _ = email_trial_expirando(usr[2], usr[1], dias)
                    if ok: enviados += 1
                st.success(f"Avisos enviados: {enviados}/{len(expirando)}")

    st.divider()

    # Administração do plano (só admin)
    if u["perfil"] == "admin":
        st.subheader("⚙️ Gestão de Planos")
        usuarios = listar_usuarios()
        if usuarios:
            df_u = pd.DataFrame(usuarios, columns=["ID","Nome","E-mail","Perfil","Fazenda"])
            st.dataframe(df_u, use_container_width=True)

            with st.form("form_converter"):
                uid_conv = st.number_input("ID do usuário para converter para PAGO", 1, step=1)
                if st.form_submit_button("Converter para plano pago"):
                    converter_para_pago(int(uid_conv))
                    st.success(f"Usuário {uid_conv} convertido para plano pago!")
                    st.rerun()
