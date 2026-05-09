# Sistema de Gestao Pecuaria -- app principal.
# Execute com:  streamlit run app.py



import os as _os
if not _os.path.exists('database.py'):
    exec(open('setup_files.py').read())

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
try:
    from exports import gerar_excel_lote, gerar_excel_sanitario, gerar_pdf_relatorio
    _EXPORTS_OK = True
except ImportError:
    _EXPORTS_OK = False
    def gerar_excel_lote(*a, **k): return b""
    def gerar_excel_sanitario(*a, **k): return b""
    def gerar_pdf_relatorio(*a, **k): return b"" 
try:
    from notifications import (
        email_boas_vindas, email_trial_expirando, email_trial_expirado,
        email_vacina_pendente, email_medicamento_critico,
        email_parto_previsto, email_abate_previsto, email_configurado,
        _enviar, _template,
    )
    _NOTIF_OK = True
except ImportError:
    _NOTIF_OK = False
    def email_boas_vindas(*a, **k): return (False, "notifications.py não encontrado")
    def email_trial_expirando(*a, **k): return (False, "")
    def email_trial_expirado(*a, **k): return (False, "")
    def email_vacina_pendente(*a, **k): return (False, "")
    def email_medicamento_critico(*a, **k): return (False, "")
    def email_parto_previsto(*a, **k): return (False, "")
    def email_abate_previsto(*a, **k): return (False, "")
    def email_configurado(): return False
    def _enviar(*a, **k): return (False, "")
    def _template(*a, **k): return "" 
try:
    from cepea import cotacao_com_cache, historico_grafico
    _CEPEA_OK = True
except ImportError:
    _CEPEA_OK = False
    def cotacao_com_cache(_db): return dict(preco=0.0, data="", fonte="", sucesso=False, msg="módulo cepea.py não encontrado")
    def historico_grafico(c): return dict(datas=[], precos=[])

try:
    from backup import gerar_backup_zip, gerar_backup_sqlite, nome_arquivo_backup
    _BACKUP_OK = True
except ImportError:
    _BACKUP_OK = False
    def gerar_backup_zip(p): return b""
    def gerar_backup_sqlite(p): return b""
    def nome_arquivo_backup(ext="zip"): return f"backup.{ext}" 
from database import (
    registrar_morte, listar_mortalidade, taxa_mortalidade_lote,
    registrar_auditoria, listar_auditoria,
    registrar_gta, listar_gta, registrar_sisbov, obter_sisbov,
    calcular_score_saude,
    registrar_venda_lote, calcular_margem_lote, listar_vendas_lote,
    salvar_cotacao, listar_cotacoes, obter_ultima_cotacao,
    calcular_gmd_temporal,
    importar_pesagens_csv, importar_animais_csv,
    verificar_carencia,
    atualizar_qtd_lote, resumo_lote,
)

inicializar_banco()

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão Pecuária",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
# SIDEBAR -- usuário logado
# ---------------------------------------------------------------------------
u = st.session_state.usuario

# --- Cabeçalho do usuário ---
with st.sidebar:
    col_icon, col_info = st.columns([1, 3])
    with col_icon:
        perfil_emoji = {"admin": "⚙️", "veterinario": "🩺", "fazendeiro": "🌾"}.get(u["perfil"], "👤")
        st.markdown(f"<div style='font-size:28px;padding-top:4px'>{perfil_emoji}</div>",
                    unsafe_allow_html=True)
    with col_info:
        st.markdown(f"**{u['nome']}**")
        st.caption(u["perfil"].capitalize())
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.usuario = None
        st.rerun()

# --- Banner de trial ---
_status_plano = obter_status_plano(u["id"])
with st.sidebar:
    if _status_plano["plano"] == "trial":
        _dr = _status_plano["dias_restantes"]
        if _dr <= 3:
            st.error(f"🔴 Trial: {_dr} dia(s) restante(s)!")
        elif _dr <= 7:
            st.warning(f"⚠️ Trial expira em {_dr} dias")
            if email_configurado():
                email_trial_expirando(u["email"], u["nome"], _dr)
        else:
            pct = int((_dr / 30) * 100)
            st.progress(pct / 100, text=f"🕐 Trial: {_dr}/30 dias")
    elif _status_plano["plano"] == "expirado":
        st.error("🔴 Trial expirado")
        if email_configurado():
            email_trial_expirado(u["email"], u["nome"])
    else:
        st.success("✅ Plano ativo")

# --- Alertas rápidos compactos ---
_pendentes = listar_vacinas_pendentes()
_criticos  = listar_medicamentos_criticos()
_partos    = listar_partos_previstos()
with st.sidebar:
    alertas = []
    if _pendentes: alertas.append(f"💉 {len(_pendentes)} vacina(s)")
    if _criticos:  alertas.append(f"💊 {len(_criticos)} med. crítico(s)")
    if _partos:    alertas.append(f"🐄 {len(_partos)} parto(s) em 30d")
    if alertas:
        st.warning("**Alertas:** " + " · ".join(alertas))

st.sidebar.divider()

# --- MENU REORGANIZADO EM GRUPOS ---
with st.sidebar:
    st.caption("NAVEGAÇÃO")

menu = st.sidebar.selectbox(
    "Ir para",
    [
        # ── INÍCIO ─────────────────────────────────
        "🏠  Início",
        "🔍  Buscar Animal",
        # ── CADASTROS ──────────────────────────────
        "─── Cadastros ───",
        "📦  Cadastrar Lote",
        "🐄  Cadastrar Animal",
        "⚖️  Registrar Pesagem",
        "🚨  Registrar Ocorrência",
        "💀  Registrar Morte",
        "📥  Importar Dados (CSV)",
        # ── ANÁLISE ────────────────────────────────
        "─── Análise ───",
        "📊  Dashboard Sanitário",
        "📈  Analisar por Lote",
        "🐄  Analisar Animal",
        "💯  Score de Saúde",
        "📉  GMD ao Longo do Tempo",
        "🔀  Comparativo de Lotes",
        "💰  Painel de Decisão",
        "📊  Dashboard Executivo",
        "🔎  Pesquisar Ocorrências",
        # ── GESTÃO ─────────────────────────────────
        "─── Gestão ───",
        "💉  Calendário Sanitário",
        "💊  Estoque de Medicamentos",
        "🐄  Controle Reprodutivo",
        "🌿  Mapa de Piquetes",
        "🥩  Previsão de Abate",
        "📋  Prontuário do Animal",
        "💰  Margem Real do Lote",
        "📈  Cotação Cepea",
        # ── RASTREABILIDADE ────────────────────────
        "─── Rastreabilidade ───",
        "📄  Rastreabilidade GTA",
        # ── RELATÓRIOS ─────────────────────────────
        "─── Relatórios ───",
        "📄  Exportar Relatórios",
        "💾  Backup do Sistema",
        # ── SISTEMA ────────────────────────────────
        "─── Sistema ───",
        "📧  Notificações",
        "📜  Log de Auditoria",
        "⚙️  Administração",
    ],
    label_visibility="collapsed",
)

# Navegação programática (ações rápidas do Home)
if "_nav" in st.session_state and st.session_state["_nav"]:
    _destino = st.session_state.pop("_nav")
    # Encontrar a chave do menu_map que aponta para o destino
    _chave = next((k for k, v in _menu_map.items() if v == _destino), None)
    if _chave:
        st.session_state["_menu_key"] = _chave

# Normalizar menu: remover emoji + espaços para manter compatibilidade
import re as _re
_menu_map = {
    "🏠  Início":                   "Home Dashboard",
    "🔍  Buscar Animal":             "Busca de Animal",
    "📦  Cadastrar Lote":            "Cadastrar Lote",
    "🐄  Cadastrar Animal":          "Cadastrar Animal",
    "⚖️  Registrar Pesagem":         "Registrar Pesagem",
    "🚨  Registrar Ocorrência":      "Ocorrências Adversas",
    "💀  Registrar Morte":           "Mortalidade",
    "📥  Importar Dados (CSV)":      "Importar Dados",
    "📊  Dashboard Sanitário":       "Dashboard Sanitário",
    "📈  Analisar por Lote":         "Analisar por Lote",
    "🐄  Analisar Animal":           "Analisar Animal",
    "💯  Score de Saúde":            "Score de Saúde",
    "📉  GMD ao Longo do Tempo":     "GMD ao Longo do Tempo",
    "🔀  Comparativo de Lotes":      "Comparativo de Lotes",
    "💰  Painel de Decisão":         "Painel de Decisão",
    "📊  Dashboard Executivo":       "Dashboard Executivo",
    "🔎  Pesquisar Ocorrências":     "Pesquisar Ocorrências",
    "💉  Calendário Sanitário":      "Calendário Sanitário",
    "💊  Estoque de Medicamentos":   "Estoque de Medicamentos",
    "🐄  Controle Reprodutivo":      "Controle Reprodutivo",
    "🌿  Mapa de Piquetes":          "Mapa de Piquetes",
    "🥩  Previsão de Abate":         "Previsão de Abate",
    "📋  Prontuário do Animal":      "Prontuário do Animal",
    "💰  Margem Real do Lote":       "Margem Real do Lote",
    "📈  Cotação Cepea":             "Cotação Cepea",
    "📄  Rastreabilidade GTA":       "Rastreabilidade GTA",
    "📄  Exportar Relatórios":       "Exportar Relatórios",
    "💾  Backup do Sistema":         "Backup do Sistema",
    "📧  Notificações":              "Notificações",
    "📜  Log de Auditoria":          "Log de Auditoria",
    "⚙️  Administração":             "Administração",
}
# separadores viram None → página em branco
menu = _menu_map.get(menu, None)

# ---------------------------------------------------------------------------
# Helper: cabeçalho padronizado de página
# ---------------------------------------------------------------------------
def _page_header(icone: str, titulo: str, subtitulo: str = ""):
    '''Renderiza cabeçalho limpo e padronizado em todas as telas.'''
    st.markdown(f"## {icone} {titulo}")
    if subtitulo:
        st.caption(subtitulo)
    st.divider()

# ===========================================================================
# SEPARADORES (menu=None quando usuário clica num grupo)
# ===========================================================================
if menu is None:
    st.info("👈 Selecione uma opção no menu lateral.")
    st.stop()

# ===========================================================================
# CADASTRAR LOTE
# ===========================================================================
elif menu == "Cadastrar Lote":
    _page_header("📦", "Cadastrar Lote", "Registre um novo lote de animais")

    col_form, col_info = st.columns([2, 1])

    with col_form:
        with st.form("form_cadastrar_lote"):
            st.markdown("#### 📋 Dados do lote")
            c1, c2 = st.columns(2)
            with c1:
                nome         = st.text_input("Nome do lote *")
                data         = st.date_input("Data de entrada")
                qtd_comprada = st.number_input("Qtd comprada", min_value=0, step=1)
                transporte   = st.text_input("Transportadora")
            with c2:
                descricao     = st.text_area("Descrição", height=70)
                qtd_recebida  = st.number_input("Qtd recebida", min_value=0, step=1)
                preco_por_animal = st.number_input("Preço por animal (R$)", min_value=0.0)

            st.markdown("#### 🌿 Manejo")
            c3, c4 = st.columns(2)
            with c3:
                tipo_alimentacao = st.selectbox("Alimentação",
                    ["Pasto", "Confinamento", "Semi-confinamento"])
            with c4:
                tipo_dieta = st.selectbox("Dieta",
                    ["Capim", "Ração", "Silagem", "Misto"])

            salvar = st.form_submit_button("💾 Salvar Lote", use_container_width=True,
                                            type="primary")

        if salvar:
            if not nome:
                st.error("Informe o nome do lote")
            elif qtd_recebida > qtd_comprada:
                st.error("Quantidade recebida não pode ser maior que a comprada")
            elif qtd_recebida == 0:
                st.error("Informe a quantidade recebida")
            else:
                lid = adicionar_lote(nome, descricao, str(data),
                                     qtd_comprada, qtd_recebida, transporte)
                registrar_auditoria(u["id"], "criar_lote", "lotes", lid, nome)
                st.success(f"✅ Lote **{nome}** criado com sucesso!")
                st.balloons()

    with col_info:
        st.markdown("#### 💡 Dicas")
        st.info("**Nome:** use algo fácil de identificar, ex: *Lote Nelore Jan/25*")
        st.info("**Qtd recebida:** pode ser menor que a comprada se houve perdas no transporte")
        st.info("**Preço por animal:** usado para calcular a margem real na hora da venda")
        if "preco_por_animal" in dir() and qtd_comprada > 0:
            custo_total = preco_por_animal * qtd_comprada
            st.metric("💰 Custo total estimado", f"R$ {custo_total:,.2f}")

# ===========================================================================
# DASHBOARD SANITÁRIO
# ===========================================================================
elif menu == "Dashboard Sanitário":
    _page_header("🦠", "Dashboard Sanitário", "Incidências, curva epidêmica e alertas")

    lotes = listar_lotes()
    opcoes = ["Todos os lotes"]
    dict_lotes = {}
    for l in lotes:
        nome_opcao = f"{l[1]} (ID {l[0]})"
        opcoes.append(nome_opcao)
        dict_lotes[nome_opcao] = l[0]

    escolha = st.selectbox("Filtrar por lote", opcoes)

    if escolha == "Todos os lotes":
        animais = listar_animais()
    else:
        lote_id = dict_lotes[escolha]
        animais = listar_animais_por_lote(lote_id)

    # Coletar ocorrências
    todas_ocorrencias = []
    for animal in animais:
        oc = listar_ocorrencias(animal[0])
        todas_ocorrencias.extend(oc)

    df_oc = pd.DataFrame(
        todas_ocorrencias,
        columns=["id","animal_id","data","tipo","descricao",
                 "gravidade","custo","dias_recuperacao","status"],
    ) if todas_ocorrencias else pd.DataFrame(
        columns=["id","animal_id","data","tipo","descricao",
                 "gravidade","custo","dias_recuperacao","status"])

    total_animais = len(animais)
    animais_com_oc = df_oc["animal_id"].nunique() if len(df_oc) > 0 else 0
    incidencia     = (animais_com_oc / total_animais * 100) if total_animais > 0 else 0
    custo_total_oc = df_oc["custo"].fillna(0).sum() if len(df_oc) > 0 else 0

    # --- KPIs ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🐄 Animais analisados", total_animais)
    k2.metric("🦠 Com ocorrência",     animais_com_oc)
    k3.metric("📊 Incidência",         f"{incidencia:.1f}%",
              delta="⚠️ Alta" if incidencia > 20 else None,
              delta_color="inverse" if incidencia > 20 else "normal")
    k4.metric("💊 Custo sanitário",    f"R$ {custo_total_oc:.2f}")

    st.divider()

    if len(df_oc) > 0:
        tab_graf, tab_lote, tab_curva, tab_corr, tab_alerta = st.tabs([
            "📊 Gráficos", "🐄 Por Lote", "📈 Curva Epidêmica",
            "📉 Correlação GMD", "🚨 Alertas"
        ])

        with tab_graf:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Ocorrências por tipo")
                st.bar_chart(df_oc["tipo"].value_counts())
            with c2:
                st.subheader("Por gravidade")
                st.bar_chart(df_oc["gravidade"].value_counts())

        with tab_lote:
            dados_lote = []
            for lote in lotes:
                lid_t = lote[0]
                animais_lote = listar_animais_por_lote(lid_t)
                total = len(animais_lote)
                ids   = [a[0] for a in animais_lote]
                oc_lt = df_oc[df_oc["animal_id"].isin(ids)] if len(df_oc) > 0 else pd.DataFrame()
                doentes = oc_lt["animal_id"].nunique() if len(oc_lt) > 0 else 0
                inc_l   = (doentes / total * 100) if total > 0 else 0
                dados_lote.append((lote[1], inc_l))
            df_lt = pd.DataFrame(dados_lote, columns=["Lote","Incidência (%)"]).set_index("Lote")
            st.bar_chart(df_lt)

            dados_tipo = []
            if total_animais > 0:
                for tipo in df_oc["tipo"].unique():
                    d_tp = df_oc[df_oc["tipo"] == tipo]["animal_id"].nunique()
                    dados_tipo.append((tipo, d_tp / total_animais * 100))
            if dados_tipo:
                df_tp = pd.DataFrame(dados_tipo, columns=["Tipo","Incidência (%)"]).set_index("Tipo")
                st.subheader("Por tipo (%)")
                st.bar_chart(df_tp)

        with tab_curva:
            df_oc["data"] = pd.to_datetime(df_oc["data"])
            curva_tipo = df_oc.groupby(["data","tipo"]).size().unstack(fill_value=0)
            st.line_chart(curva_tipo)

        with tab_corr:
            dados_corr = []
            for animal in listar_animais():
                ps = listar_pesagens(animal[0])
                if len(ps) > 1:
                    df_p = pd.DataFrame(ps, columns=["ID","Animal","Peso","Data"])
                    df_p["Data"] = pd.to_datetime(df_p["Data"])
                    df_p = df_p.sort_values("Data")
                    dias = (df_p["Data"].iloc[-1] - df_p["Data"].iloc[0]).days
                    if dias > 0:
                        g = (df_p["Peso"].iloc[-1] - df_p["Peso"].iloc[0]) / dias
                        qtd = len(listar_ocorrencias(animal[0]))
                        dados_corr.append((animal[1], round(g,3), qtd))
            if dados_corr:
                df_c = pd.DataFrame(dados_corr, columns=["Animal","GMD","Ocorrencias"])
                st.scatter_chart(df_c, x="Ocorrencias", y="GMD")
                media_g = df_c["GMD"].mean()
                for _, row in df_c.iterrows():
                    if row["Ocorrencias"] > 0 and row["GMD"] < media_g:
                        st.error(f"🔴 {row['Animal']}: baixo GMD + ocorrência")
                    elif row["Ocorrencias"] > 0:
                        st.warning(f"🟡 {row['Animal']}: ocorrência sem impacto aparente")
                    elif row["GMD"] < media_g:
                        st.warning(f"🟠 {row['Animal']}: baixo GMD sem ocorrência")
                    else:
                        st.success(f"🟢 {row['Animal']}: bom desempenho e saudável")
            else:
                st.info("Sem dados suficientes para correlação")

        with tab_alerta:
            # Alertas por lote
            st.subheader("Por lote")
            for nome, inc in dados_lote:
                if inc > 20:   st.error(f"🔴 {nome}: alta incidência ({inc:.1f}%)")
                elif inc > 5:  st.warning(f"🟡 {nome}: incidência moderada ({inc:.1f}%)")
                else:          st.success(f"🟢 {nome}: controle adequado ({inc:.1f}%)")

            if dados_tipo:
                st.subheader("Por tipo")
                for tipo, inc in dados_tipo:
                    if inc > 20:  st.error(f"🔴 {tipo}: alta incidência ({inc:.1f}%)")
                    elif inc > 5: st.warning(f"🟡 {tipo}: incidência moderada ({inc:.1f}%)")
                    else:         st.success(f"🟢 {tipo}: controle adequado ({inc:.1f}%)")

            # Alertas inteligentes
            st.subheader("🧠 Alertas Inteligentes")
            for lote in listar_lotes():
                lid_a   = lote[0]
                nom_a   = lote[1]
                anim_a  = listar_animais_por_lote(lid_a)
                tot_a   = len(anim_a)
                if tot_a == 0: continue
                ocs_a, gmds_a, custo_a = [], [], 0
                for an in anim_a:
                    oc_a = listar_ocorrencias(an[0])
                    ocs_a.extend(oc_a)
                    custo_a += sum(o[6] for o in oc_a if o[6])
                    ps_a = listar_pesagens(an[0])
                    if len(ps_a) > 1:
                        df_a = pd.DataFrame(ps_a, columns=["ID","Animal","Peso","Data"])
                        df_a["Data"] = pd.to_datetime(df_a["Data"])
                        df_a = df_a.sort_values("Data")
                        d_a  = (df_a["Data"].iloc[-1]-df_a["Data"].iloc[0]).days
                        if d_a > 0:
                            g_a = (df_a["Peso"].iloc[-1]-df_a["Peso"].iloc[0])/d_a
                            if 0 <= g_a <= 2: gmds_a.append(g_a)
                inc_a  = (len(set(o[1] for o in ocs_a))/tot_a*100) if ocs_a else 0
                gmd_a  = sum(gmds_a)/len(gmds_a) if gmds_a else 0
                if inc_a > 20 and gmd_a < 0.5:
                    st.error(f"🔴 {nom_a}: incidência {inc_a:.1f}% + GMD {gmd_a:.2f} -- problema grave")
                elif custo_a > 1000:
                    st.warning(f"🟡 {nom_a}: custo sanitário elevado R$ {custo_a:.2f}")
                elif len(ocs_a) >= 5:
                    st.warning(f"🟠 {nom_a}: {len(ocs_a)} ocorrências -- monitorar surto")
                else:
                    st.success(f"🟢 {nom_a}: controlado (inc {inc_a:.1f}%, GMD {gmd_a:.2f})")
    else:
        st.info("Nenhuma ocorrência registrada ainda.")
        st.caption("Registre ocorrências em **Cadastros → Registrar Ocorrência**.")


# ===========================================================================
# CADASTRAR ANIMAL
# ===========================================================================
elif menu == "Cadastrar Animal":
    _page_header("🐄", "Cadastrar Animal", "Vincule um animal a um lote")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado.")
        st.info("👈 Vá em **Cadastros → Cadastrar Lote** primeiro.")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        col_sel, col_info = st.columns([2, 1])

        with col_sel:
            escolha = st.selectbox("Selecione o lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha]
        lote    = obter_lote(lote_id)
        qtd_recebida  = lote[5]
        total_animais = contar_animais_no_lote(lote_id)
        vagas = max(0, qtd_recebida - total_animais)

        with col_info:
            st.metric("🐄 Cadastrados / Capacidade",
                      f"{total_animais} / {qtd_recebida}",
                      delta=f"{vagas} vaga(s)" if vagas > 0 else "Lote cheio",
                      delta_color="normal" if vagas > 0 else "inverse")

        if total_animais >= qtd_recebida:
            st.error("⚠️ Limite do lote atingido. Aumente a capacidade em Cadastrar Lote.")
        else:
            with st.form("form_cadastrar_animal"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    identificacao = st.text_input("Identificação / Brinco *",
                                                   placeholder="Ex: BOI-001")
                with c2:
                    idade = st.number_input("Idade (meses)", 0, 240, value=24)
                with c3:
                    peso_entrada = st.number_input("Peso de entrada (kg)", 0.0, value=0.0)

                c4, c5, c6 = st.columns(3)
                with c4:
                    raca = st.text_input("Raça", placeholder="Ex: Nelore")
                with c5:
                    sexo = st.selectbox("Sexo", ["indefinido", "macho", "fêmea"])
                with c6:
                    peso_alvo = st.number_input("Peso alvo abate (kg)", 0.0, value=0.0)

                salvar = st.form_submit_button("💾 Cadastrar Animal",
                                               use_container_width=True, type="primary")

            if salvar:
                if not identificacao:
                    st.error("Informe a identificação do animal")
                else:
                    aid = adicionar_animal(identificacao, idade, lote_id)
                    if peso_alvo > 0 or raca or sexo != "indefinido" or peso_entrada > 0:
                        atualizar_animal_detalhes(aid, peso_alvo=peso_alvo if peso_alvo > 0 else None,
                                                  observacoes=None)
                    registrar_auditoria(u["id"], "cadastro_animal", "animais", aid, identificacao)
                    st.success(f"✅ **{identificacao}** cadastrado no lote **{lote[1]}**!")
                    st.rerun()

# ===========================================================================
# REGISTRAR PESAGEM
# ===========================================================================
elif menu == "Registrar Pesagem":
    _page_header("⚖️", "Registrar Pesagem", "Registre o peso atual de um animal")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado.")
        st.info("👈 Vá em **Cadastros → Cadastrar Lote** primeiro.")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}

        col_a, col_b = st.columns([1, 1])
        with col_a:
            escolha_lote = st.selectbox("Lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha_lote]
        animais = listar_animais_por_lote(lote_id)

        if len(animais) == 0:
            st.warning("Nenhum animal neste lote.")
        else:
            dict_animais = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
            with col_b:
                escolha_animal = st.selectbox("Animal", list(dict_animais.keys()))
            animal_id = dict_animais[escolha_animal]

            # Mostrar última pesagem do animal para referência
            pesagens_ant = listar_pesagens(animal_id)
            if pesagens_ant:
                ult = pesagens_ant[-1]
                det = obter_animal(animal_id)
                c1, c2, c3 = st.columns(3)
                c1.metric("⚖️ Último peso", f"{ult[2]:.1f} kg", f"em {ult[3]}")
                if det and det[7] > 0:
                    falta = det[7] - ult[2]
                    c2.metric("🎯 Peso alvo", f"{det[7]:.0f} kg",
                              f"faltam {falta:.1f} kg" if falta > 0 else "✅ atingido!")
                if len(pesagens_ant) >= 2:
                    df_p = pd.DataFrame(pesagens_ant, columns=["id","aid","peso","data"])
                    df_p["data"] = pd.to_datetime(df_p["data"])
                    df_p = df_p.sort_values("data")
                    dias = (df_p["data"].iloc[-1] - df_p["data"].iloc[0]).days
                    if dias > 0:
                        gmd_ref = (df_p["peso"].iloc[-1] - df_p["peso"].iloc[0]) / dias
                        c3.metric("📈 GMD atual", f"{gmd_ref:.3f} kg/dia")
                st.divider()

            with st.form("form_pesagem"):
                cp1, cp2 = st.columns(2)
                with cp1:
                    peso = st.number_input("Peso (kg) *", 0.0, 1000.0, step=0.5)
                with cp2:
                    data_p = st.date_input("Data da pesagem")
                salvar_p = st.form_submit_button("💾 Salvar Pesagem",
                                                  use_container_width=True, type="primary")

            if salvar_p:
                if peso <= 0:
                    st.error("Informe um peso válido (maior que zero)")
                elif peso > 1000:
                    st.error("Peso muito alto -- verifique o valor")
                else:
                    adicionar_pesagem(animal_id, peso, str(data_p))
                    registrar_auditoria(u["id"], "pesagem", "pesagens",
                                        animal_id, f"{peso}kg em {data_p}")
                    st.success(f"✅ Pesagem de **{peso:.1f} kg** registrada!")
                    st.rerun()

# ===========================================================================
# ANÁLISE POR LOTE
# ===========================================================================
elif menu == "Analisar por Lote":
    _page_header("📈", "Análise por Lote", "Desempenho econômico e zootécnico")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        escolha = st.selectbox("Selecione o lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha]

        lote = obter_lote(lote_id)
        animais = listar_animais_por_lote(lote_id)

        # --- Resumo consistente do lote ---
        rs = resumo_lote(lote_id)
        col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns(5)
        col_r1.metric("🐄 Animais ativos",   rs["ativos"])
        col_r2.metric("💀 Mortes",           rs["mortos"])
        col_r3.metric("📄 GTAs emitidas",    rs["gtas_emitidas"])
        col_r4.metric("🚨 Ocorrências",      rs["ocorrencias"])
        col_r5.metric("💉 Vacinas pendentes",rs["vacinas_pendentes"])
        st.divider()

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

        st.metric("📆 Duração do lote", f"{dias_lote} dias")
        st.metric("💰 Custo operacional", f"R$ {custo_operacional:,.2f}")

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
        st.metric("📈 Receita estimada", f"R$ {receita:,.2f}")
        st.metric("💸 Custo operacional", f"R$ {custo_operacional:,.2f}")
        st.metric("💊 Custo sanitário", f"R$ {custo_sanitario:,.2f}")

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
            st.metric("⚖️ Ganho total", f"{ganho_total:.2f} kg")
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
            st.metric("🚀 GMD médio do lote", f"{gmd_medio:.3f} kg/dia")
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
    _page_header("🐄", "Análise Individual", "Histórico de peso, ocorrências e alertas do animal")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        ca1, ca2 = st.columns(2)
        with ca1:
            escolha_lote  = st.selectbox("Lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha_lote]
        animais = listar_animais_por_lote(lote_id)

        if len(animais) == 0:
            st.warning("Nenhum animal neste lote")
        else:
            dict_animais = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
            with ca2:
                escolha_animal = st.selectbox("Animal", list(dict_animais.keys()))
            animal_id  = dict_animais[escolha_animal]
            pesagens   = listar_pesagens(animal_id)
            ocorrencias = listar_ocorrencias(animal_id)
            gmd        = None
            sc         = calcular_score_saude(animal_id)

            # KPIs rápidos
            km1, km2, km3, km4 = st.columns(4)
            km1.metric("⚖️ Pesagens",    len(pesagens))
            km2.metric("🚨 Ocorrências", len(ocorrencias))
            km3.metric("💯 Score saúde", f"{sc['score']}/100")
            km4.metric("🏷️ Status",      sc["classificacao"])

            tab_peso, tab_oc, tab_alerta = st.tabs(
                ["📊 Pesagens & GMD", "🚨 Ocorrências", "🔔 Alertas & Diagnóstico"])

            with tab_peso:
                if len(pesagens) > 0:
                    df = pd.DataFrame(pesagens, columns=["ID","Animal","Peso","Data"])
                    df["Data"] = pd.to_datetime(df["Data"])
                    df = df.sort_values("Data")
                    st.line_chart(df.set_index("Data")["Peso"])
                    st.dataframe(df[["Data","Peso"]].rename(columns={"Peso":"Peso (kg)"}),
                                 use_container_width=True)

                    if len(df) > 1:
                        peso_inicial = df["Peso"].iloc[0]
                        peso_final   = df["Peso"].iloc[-1]
                        dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days
                        if dias > 0:
                            gmd = (peso_final - peso_inicial) / dias
                            d1, d2, d3 = st.columns(3)
                            d1.metric("⚖️ Ganho total",  f"{peso_final-peso_inicial:.2f} kg")
                            d2.metric("📆 Período",       f"{dias} dias")
                            d3.metric("📈 GMD",           f"{gmd:.3f} kg/dia")
                            if gmd < 0:
                                st.error("🚨 Perda de peso -- possível doença")
                            elif gmd > 2:
                                st.error("🚨 GMD irreal -- revisar dados")
                            elif gmd < 0.5:
                                st.warning("⚠️ GMD baixo")
                            else:
                                st.success("✅ Bom desempenho")
                else:
                    st.info("Sem pesagens registradas para este animal.")

            with tab_oc:
                if len(ocorrencias) > 0:
                    df_oc = pd.DataFrame(ocorrencias,
                        columns=["id","animal_id","data","tipo","descricao",
                                 "gravidade","custo","dias_recuperacao","status"])
                    df_oc["data"] = pd.to_datetime(df_oc["data"])
                    st.dataframe(df_oc[["data","tipo","gravidade","descricao","custo","status"]],
                                 use_container_width=True)
                    custo_tot = df_oc["custo"].fillna(0).sum()
                    st.metric("💊 Custo total tratamentos", f"R$ {custo_tot:.2f}")
                    for _, row in df_oc.iterrows():
                        if row["gravidade"] == "Alta":
                            st.error(f"🔴 {row['tipo']} -- {row['descricao']}")
                        elif row["gravidade"] == "Média":
                            st.warning(f"🟡 {row['tipo']} -- {row['descricao']}")
                        else:
                            st.info(f"🔵 {row['tipo']} -- {row['descricao']}")
                else:
                    st.success("✅ Nenhuma ocorrência registrada")

            with tab_alerta:
                # Score detalhado
                det = sc["detalhes"]
                sa1, sa2, sa3 = st.columns(3)
                sa1.metric("GMD (pts)",         f"{det['pts_gmd']}/50")
                sa2.metric("Ocorrências (pts)", f"{det['pts_ocorrencias']}/35")
                sa3.metric("Reprodução (pts)",  f"{det['pts_reproducao']}/15")

                # Alerta integrado
                if gmd is not None:
                    if gmd < 0.5 and len(ocorrencias) > 0:
                        st.error("🚨 Alto risco: baixo desempenho + histórico clínico")
                    elif gmd < 0.5:
                        st.warning("⚠️ Baixo GMD -- revisar nutrição e sanidade")
                    elif len(ocorrencias) > 0:
                        st.warning("⚠️ Histórico clínico -- monitorar")
                    else:
                        st.success("✅ Animal saudável e produtivo")

                # Carência
                car = verificar_carencia(animal_id)
                if car["em_carencia"]:
                    st.error(f"💊 Em carência até **{car['liberado_em']}** -- não abater antes!")
                else:
                    st.success("✅ Sem restrição de carência")

# ===========================================================================
# OCORRÊNCIAS ADVERSAS
# ===========================================================================
elif menu == "Ocorrências Adversas":
    _page_header("🚨", "Registrar Ocorrência", "Doenças, lesões e medicações")

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
    _page_header("📊", "Painel de Decisão", "Resultado financeiro por lote")

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
    _page_header("🔎", "Pesquisar Ocorrências", "Filtros por lote, tipo e gravidade")

    lotes = listar_lotes()
    dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}

    # Filtros em linha
    f1, f2, f3 = st.columns(3)
    with f1:
        escolha_lote = st.selectbox("Lote", ["Todos"] + list(dict_lotes.keys()))
    with f2:
        tipo_f = st.selectbox("Tipo", ["Todos","Doença","Lesão","Medicamento","Outros"])
    with f3:
        grav_f = st.selectbox("Gravidade", ["Todas","Baixa","Média","Alta"])

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
        columns=["id","animal_id","data","tipo","descricao",
                 "gravidade","custo","dias_recuperacao","status"],
    ) if todas_ocorrencias else pd.DataFrame(
        columns=["id","animal_id","data","tipo","descricao",
                 "gravidade","custo","dias_recuperacao","status"])

    if len(df_oc) > 0:
        if tipo_f != "Todos":
            df_oc = df_oc[df_oc["tipo"] == tipo_f]
        if grav_f != "Todas":
            df_oc = df_oc[df_oc["gravidade"] == grav_f]
        df_oc["data"] = pd.to_datetime(df_oc["data"])
        df_oc = df_oc.sort_values(by="data", ascending=False)

    st.divider()

    if len(df_oc) > 0:
        # KPIs da pesquisa
        pk1, pk2, pk3, pk4 = st.columns(4)
        pk1.metric("📋 Ocorrências",    len(df_oc))
        pk2.metric("🐄 Animais afetados", df_oc["animal_id"].nunique())
        custo_tot = df_oc["custo"].fillna(0).sum()
        pk3.metric("💰 Custo total",    f"R$ {custo_tot:.2f}")
        altas = len(df_oc[df_oc["gravidade"]=="Alta"])
        pk4.metric("🔴 Gravidade Alta", altas,
                   delta="⚠️" if altas > 0 else None,
                   delta_color="inverse" if altas > 0 else "normal")

        # Nível de incidência
        if len(df_oc) >= 10:
            st.error("🚨 Alta incidência de ocorrências")
        elif len(df_oc) >= 5:
            st.warning("⚠️ Incidência moderada")
        else:
            st.success("✅ Baixa incidência")

        st.divider()
        tab_dados, tab_grafico = st.tabs(["📋 Registros", "📊 Análise"])

        with tab_dados:
            st.dataframe(
                df_oc[["data","tipo","gravidade","descricao","custo","dias_recuperacao","status"]],
                use_container_width=True
            )

        with tab_grafico:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("Por tipo")
                st.bar_chart(df_oc["tipo"].value_counts())
            with col_g2:
                st.subheader("Por gravidade")
                st.bar_chart(df_oc["gravidade"].value_counts())

            custo_por_tipo = df_oc.groupby("tipo")["custo"].sum()
            if len(custo_por_tipo) > 0:
                tipo_caro   = custo_por_tipo.idxmax()
                valor_caro  = custo_por_tipo.max()
                st.warning(f"💸 Maior impacto financeiro: **{tipo_caro}** -- R$ {valor_caro:.2f}")

        # Alertas inteligentes integrados
        st.divider()
        st.subheader("🧠 Alertas Inteligentes")
        for lote in listar_lotes():
            lid_i    = lote[0]
            nom_i    = lote[1]
            anim_i   = listar_animais_por_lote(lid_i)
            tot_i    = len(anim_i)
            if tot_i == 0: continue
            ocs_i, gmds_i, custo_i = [], [], 0
            for an in anim_i:
                oc_i = listar_ocorrencias(an[0])
                ocs_i.extend(oc_i)
                custo_i += sum(o[6] for o in oc_i if o[6])
                ps_i = listar_pesagens(an[0])
                if len(ps_i) > 1:
                    df_i = pd.DataFrame(ps_i, columns=["ID","Animal","Peso","Data"])
                    df_i["Data"] = pd.to_datetime(df_i["Data"])
                    df_i = df_i.sort_values("Data")
                    d_i  = (df_i["Data"].iloc[-1]-df_i["Data"].iloc[0]).days
                    if d_i > 0:
                        g_i = (df_i["Peso"].iloc[-1]-df_i["Peso"].iloc[0])/d_i
                        if 0 <= g_i <= 2: gmds_i.append(g_i)
            inc_i  = (len(set(o[1] for o in ocs_i))/tot_i*100) if ocs_i else 0
            gmd_i  = sum(gmds_i)/len(gmds_i) if gmds_i else 0
            if inc_i > 20 and gmd_i < 0.5:
                st.error(f"🔴 {nom_i}: incidência {inc_i:.1f}% + GMD baixo -- atenção urgente")
            elif custo_i > 1000:
                st.warning(f"🟡 {nom_i}: custo sanitário elevado R$ {custo_i:.2f}")
            elif len(ocs_i) >= 5:
                st.warning(f"🟠 {nom_i}: {len(ocs_i)} ocorrências -- monitorar surto")
            else:
                st.success(f"🟢 {nom_i}: controlado (inc {inc_i:.1f}%, GMD {gmd_i:.2f})")
    else:
        st.info("Nenhuma ocorrência encontrada com os filtros selecionados.")


# ===========================================================================
# DASHBOARD EXECUTIVO
# ===========================================================================
elif menu == "Dashboard Executivo":
    _page_header("📊", "Dashboard Executivo", "KPIs consolidados do lote")

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
    st.metric("🐄 Animais no lote", numero_animais)
    st.metric("⚖️ Ganho total", f"{ganho_total:.2f} kg")
    st.metric("💸 Custo sanitário", f"R$ {custo_sanitario:.2f}")

# ===========================================================================
# SEPARADOR DE MENU (item não clicável)
# ===========================================================================
elif menu == "── Novos Módulos ──":
    pass  # separador obsoleto

# ===========================================================================
# CALENDÁRIO SANITÁRIO
# ===========================================================================
elif menu == "Calendário Sanitário":
    _page_header("💉", "Calendário Sanitário", "Agenda de vacinas e medicações")

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
                    st.success(f"✅ {row['Vacina']} -- Lote {row['Lote ID']} -- Realizado em {row['Realizado']}")
                elif atrasado:
                    st.error(f"🔴 ATRASADA: {row['Vacina']} -- Previsto {row['Previsto']}")
                else:
                    st.warning(f"🟡 Pendente: {row['Vacina']} -- Previsto {row['Previsto']}")

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
            opcoes_v = {f"{r['Vacina']} -- {r['Lote']} (prev. {r['Previsto']})": r["ID"]
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
    _page_header("💊", "Estoque de Medicamentos", "Controle de estoque, validade e uso")

    tab1, tab2, tab3 = st.tabs(["📦 Estoque Atual", "➕ Cadastrar", "💉 Registrar Uso"])

    with tab1:
        meds = listar_medicamentos()
        criticos = listar_medicamentos_criticos()

        if criticos:
            st.error(f"🚨 {len(criticos)} medicamento(s) em alerta de estoque ou validade:")
            for m in criticos:
                motivo = "estoque baixo" if m[3] <= m[4] else f"vence em {m[5]}"
                st.warning(f"⚠️ {m[1]} -- {m[3]:.1f} {m[2]} ({motivo})")

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
                anim_sel = st.selectbox("Animal", list(dict_a.keys()) if dict_a else ["--"])
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
    _page_header("🐄", "Controle Reprodutivo", "IATF, diagnóstico, prenhez e partos")

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
                        "Data Cio": r[2] or "--",
                        "Diagnóstico": r[4] or "--",
                        "Resultado": r[5],
                        "Parto Previsto": r[6] or "--",
                        "Parto Real": r[7] or "--",
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
                anim_s  = st.selectbox("Animal", list(dict_a.keys()) if dict_a else ["--"])
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
    _page_header("🌿", "Mapa de Piquetes", "Alocação de lotes e histórico de ocupação")

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
    _page_header("📄", "Exportar Relatórios", "PDF e Excel do lote, sanitário e estoque")

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
        st.subheader("📊 Excel -- Dados do Lote")
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
        st.subheader("📋 PDF -- Relatório do Lote")
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
            pdf = gerar_pdf_relatorio(f"Relatório -- {nome_lote}", secoes)
            st.download_button(
                label="⬇️ Baixar PDF",
                data=pdf,
                file_name=f"relatorio_{nome_lote.replace(' ','_')}.pdf",
                mime="application/pdf",
                key="dl_pdf_relatorio",
            )

    st.divider()
    st.subheader("💊 Excel -- Calendário Sanitário e Medicamentos")
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
    _page_header("⚙️", "Administração", "Usuários, planos e configurações")

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
    _page_header("🥩", "Previsão de Abate", "Data estimada e receita projetada por GMD")

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
                st.warning(f"🟡 {r['Animal']}: {r['Dias Restantes']} dias -- prepare o abate")
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
    _page_header("📋", "Prontuário do Animal", "Histórico completo: peso, saúde e reprodução")

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
                    st.caption("⚠️ Confiança baixa -- registre mais pesagens para melhorar a previsão.")

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
    _page_header("📧", "Notificações", "Alertas por e-mail e gestão de planos")

    if not email_configurado():
        st.warning("⚠️ E-mail não configurado.")
        st.markdown('''
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
        ''')
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

# ===========================================================================
# SEPARADOR AVANÇADO
# ===========================================================================
elif menu == "── Avançado ──":
    st.info("Selecione um módulo avançado no menu lateral.")

# ===========================================================================
# HOME DASHBOARD
# ===========================================================================
elif menu == "Home Dashboard":
    # Saudação dinâmica
    hora = datetime.now().hour
    saudacao = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    st.markdown(f"## {saudacao}, **{u['nome']}** 👋")
    st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.divider()

    lotes         = listar_lotes()
    animais_todos = listar_animais()
    pendentes     = listar_vacinas_pendentes()
    criticos      = listar_medicamentos_criticos()
    partos        = listar_partos_previstos()

    # --- KPIs ---
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📦 Lotes",            len(lotes))
    k2.metric("🐄 Animais ativos",   len(animais_todos))
    k3.metric("💉 Vacinas pendentes",len(pendentes),
              delta="⚠️" if pendentes else None,
              delta_color="inverse" if pendentes else "normal")
    k4.metric("💊 Meds. críticos",   len(criticos),
              delta="⚠️" if criticos else None,
              delta_color="inverse" if criticos else "normal")
    k5.metric("🐄 Partos em 30d",    len(partos))

    st.divider()

    # --- Cotação + Alertas ---
    col_cot, col_alert = st.columns([1, 2])

    with col_cot:
        st.subheader("💰 Cotação do dia")
        import database as _db_cot
        cot = cotacao_com_cache(_db_cot)
        if cot["sucesso"]:
            st.success(f"**R$ {cot['preco']:.2f} /@**")
            st.caption(f"{cot['data']} · {cot['fonte']}")
        else:
            st.warning("Cotação indisponível")
            with st.form("form_cot_home"):
                pr_h = st.number_input("R$/@", 0.0, 1000.0, 195.0,
                                        label_visibility="collapsed")
                if st.form_submit_button("💾 Salvar cotação"):
                    salvar_cotacao(str(date.today()), pr_h, "manual")
                    st.rerun()

    with col_alert:
        st.subheader("🚨 Alertas")
        if not pendentes and not criticos and not partos:
            st.success("✅ Tudo em ordem! Nenhum alerta crítico hoje.")
        if pendentes:
            with st.expander(f"💉 {len(pendentes)} vacina(s) pendente(s)", expanded=True):
                for v in pendentes[:5]:
                    st.caption(f"• **{v[3]}** -- Lote: {v[2]} -- Previsto: {v[4]}")
        if criticos:
            with st.expander(f"💊 {len(criticos)} medicamento(s) em alerta", expanded=True):
                for m in criticos[:5]:
                    motivo = "estoque baixo" if m[3] <= m[4] else f"vence {m[5]}"
                    st.caption(f"• **{m[1]}** -- {m[3]:.0f} {m[2]} ({motivo})")
        if partos:
            with st.expander(f"🐄 {len(partos)} parto(s) previsto(s)"):
                for p in partos[:5]:
                    st.caption(f"• **{p[1]}** -- Lote: {p[2]} -- {p[3]}")

    st.divider()

    # --- Cards de lotes ---
    st.subheader("📦 Seus lotes")
    if not lotes:
        st.info("Nenhum lote cadastrado. Vá em **Cadastros → Cadastrar Lote**.")
    else:
        ncols = min(3, len(lotes))
        cols_lote = st.columns(ncols)
        for i, l in enumerate(lotes[:6]):
            rs = resumo_lote(l[0])
            ico = "🟢" if rs["ativos"] > 0 else "⚫"
            tags = []
            if rs["mortos"]:           tags.append(f"💀 {rs['mortos']}")
            if rs["vacinas_pendentes"]:tags.append(f"💉 {rs['vacinas_pendentes']}")
            if rs["ocorrencias"]:      tags.append(f"🚨 {rs['ocorrencias']}")
            tag_str = " · ".join(tags) if tags else "✅ sem alertas"
            with cols_lote[i % ncols]:
                linha1 = f"**{ico} {l[1]}**"
                linha2 = f"🐄 {rs['ativos']} ativos · 📅 {l[3]}"
                linha3 = f"_{tag_str}_"
                st.markdown(linha1 + "  \n" + linha2 + "  \n" + linha3)
                st.divider()
        if len(lotes) > 6:
            st.caption(f"... e mais {len(lotes)-6} lote(s).")

    st.divider()

    # --- Ações rápidas ---
    st.subheader("⚡ Ações rápidas")
    qa1, qa2, qa3, qa4 = st.columns(4)
    if qa1.button("➕ Novo Lote",         use_container_width=True):
        st.session_state["_nav"] = "Cadastrar Lote"; st.rerun()
    if qa2.button("⚖️ Registrar Pesagem", use_container_width=True):
        st.session_state["_nav"] = "Registrar Pesagem"; st.rerun()
    if qa3.button("🚨 Nova Ocorrência",   use_container_width=True):
        st.session_state["_nav"] = "Ocorrências Adversas"; st.rerun()
    if qa4.button("📄 Exportar Relatório",use_container_width=True):
        st.session_state["_nav"] = "Exportar Relatórios"; st.rerun()

# ===========================================================================
# BUSCA DE ANIMAL
# ===========================================================================
elif menu == "Busca de Animal":
    _page_header("🔍", "Buscar Animal", "Encontre qualquer animal pelo brinco ou identificação")
    termo = st.text_input("Digite a identificação (brinco, tag, nome...)",
                           placeholder="Ex: BOI-001")
    if termo:
        animais_todos = listar_animais()
        encontrados = [a for a in animais_todos
                       if termo.lower() in a[1].lower()]
        if encontrados:
            st.success(f"{len(encontrados)} animal(is) encontrado(s)")
            for a in encontrados:
                lote = obter_lote(a[3])
                nome_lote = lote[1] if lote else "--"
                with st.expander(f"🐄 {a[1]} -- Lote: {nome_lote}"):
                    det = obter_animal(a[0])
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**ID:** {a[0]}")
                        st.write(f"**Idade:** {a[2]} meses")
                        st.write(f"**Raça:** {det[5] if det else '--'}")
                        st.write(f"**Peso alvo:** {det[7] if det else 0} kg")
                    with col2:
                        ocs = listar_ocorrencias(a[0])
                        ps  = listar_pesagens(a[0])
                        st.write(f"**Pesagens:** {len(ps)}")
                        st.write(f"**Ocorrências:** {len(ocs)}")
                        sc = calcular_score_saude(a[0])
                        st.write(f"**Score saúde:** {sc['score']}/100 ({sc['classificacao']})")
                        car = verificar_carencia(a[0])
                        if car["em_carencia"]:
                            st.warning(f"⚠️ Em carência até {car['liberado_em']}")
                    if st.button(f"Abrir Prontuário", key=f"btn_{a[0]}"):
                        st.session_state["animal_selecionado"] = a[0]
                        st.info("Vá em Prontuário do Animal para ver o histórico completo.")
        else:
            st.warning(f"Nenhum animal encontrado para '{termo}'")

# ===========================================================================
# MORTALIDADE
# ===========================================================================
elif menu == "Mortalidade":
    _page_header("💀", "Mortalidade", "Baixa de animais com causa e custo da perda")
    tab1, tab2 = st.tabs(["📋 Histórico", "➕ Registrar Morte"])

    with tab1:
        lotes = listar_lotes()
        if lotes:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            filtro = st.selectbox("Filtrar por lote", ["Todos"]+list(dict_l.keys()))
            lote_id_f = dict_l.get(filtro) if filtro != "Todos" else None
            morts = listar_mortalidade(lote_id_f)
            if morts:
                df_m = pd.DataFrame(morts, columns=["ID","Animal ID","Animal",
                                                     "Data","Causa","Descrição","Custo Perda"])
                st.dataframe(df_m, use_container_width=True)
                col1,col2 = st.columns(2)
                col1.metric("💀 Total de mortes", len(morts))
                col2.metric("💸 Custo total perdas",
                            f"R$ {sum(m[6] for m in morts if m[6]):.2f}")
                if lote_id_f:
                    tm = taxa_mortalidade_lote(lote_id_f)
                    st.metric("📊 Taxa de mortalidade", f"{tm['taxa']:.1f}%")
            else:
                st.success("✅ Nenhuma morte registrada.")

    with tab2:
        lotes = listar_lotes()
        if not lotes:
            st.warning("Cadastre um lote primeiro.")
        else:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            # selectbox FORA do form para atualizar lista de animais dinamicamente
            lote_sel_m = st.selectbox("Lote", list(dict_l.keys()),
                                       key="morte_lote_sel")
            lote_id_m  = dict_l[lote_sel_m]
            animais_m  = listar_animais_por_lote(lote_id_m)

            if not animais_m:
                st.warning("Nenhum animal neste lote.")
            else:
                dict_a_m = {f"{a[1]} (ID {a[0]})": a[0] for a in animais_m}
                with st.form("form_morte"):
                    anim_sel   = st.selectbox("Animal", list(dict_a_m.keys()))
                    data_morte = st.date_input("Data")
                    causa      = st.selectbox("Causa",
                                  ["Doença","Acidente","Desaparecimento",
                                   "Predador","Outras"])
                    desc_m     = st.text_area("Descrição")
                    custo_p    = st.number_input("Custo da perda (R$)", 0.0)
                    if st.form_submit_button("Registrar Morte"):
                        registrar_morte(dict_a_m[anim_sel], str(data_morte),
                                        causa, desc_m, custo_p)
                        registrar_auditoria(u["id"], "morte_animal",
                                            "animais", dict_a_m[anim_sel],
                                            f"{anim_sel} -- {causa}")
                        st.success("Morte registrada e animal baixado do lote.")
                        st.rerun()

# ===========================================================================
# IMPORTAR DADOS
# ===========================================================================
elif menu == "Importar Dados":
    _page_header("📥", "Importar Dados", "Importe pesagens e animais via planilha CSV")

    lotes = listar_lotes()

    # --- Seleção ou criação de lote ---
    st.subheader("📦 Lote de destino")
    opcao_lote = st.radio("O que deseja fazer?",
                          ["Usar lote existente", "Criar novo lote agora"],
                          horizontal=True, key="import_opcao_lote")

    lote_id = None

    if opcao_lote == "Criar novo lote agora":
        with st.form("form_novo_lote_import"):
            col1, col2 = st.columns(2)
            with col1:
                nome_nl    = st.text_input("Nome do lote *")
                qtd_comp   = st.number_input("Qtd comprada", 0, step=1)
                qtd_rec    = st.number_input("Qtd recebida", 0, step=1)
            with col2:
                data_nl    = st.date_input("Data de entrada")
                transp_nl  = st.text_input("Transportadora")
                desc_nl    = st.text_area("Descrição")
            if st.form_submit_button("✅ Criar lote e continuar"):
                if nome_nl:
                    lote_id = adicionar_lote(nome_nl, desc_nl, str(data_nl),
                                             qtd_comp, qtd_rec, transp_nl)
                    registrar_auditoria(u["id"], "criar_lote", "lotes",
                                        lote_id, nome_nl)
                    st.success(f"Lote '{nome_nl}' criado! Agora faça o upload do CSV abaixo.")
                    st.rerun()
                else:
                    st.error("Informe o nome do lote.")
        # Após criar, pega o lote mais recente
        lotes = listar_lotes()
        if lotes:
            lote_id = lotes[0][0]
            st.info(f"Lote selecionado: **{lotes[0][1]}**")
    else:
        if not lotes:
            st.warning("Nenhum lote cadastrado. Selecione 'Criar novo lote agora'.")
            st.stop()
        dict_l   = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        lote_sel = st.selectbox("Selecione o lote", list(dict_l.keys()),
                                 key="import_lote_sel")
        lote_id  = dict_l[lote_sel]

    if not lote_id:
        st.stop()

    st.divider()
    tab1, tab2 = st.tabs(["⚖️ Importar Pesagens", "🐄 Importar Animais"])

    with tab1:
        st.markdown('''
        **Formato esperado do CSV:**
        ```
        identificacao,peso,data
        BOI-001,310.5,2024-01-15
        BOI-002,295.0,2024-01-15
        ```
        ''')
        arq = st.file_uploader("Selecione o arquivo CSV", type=["csv"], key="csv_pesagens")
        if arq:
            import csv as csv_mod, io as io_mod
            texto = arq.read().decode("utf-8-sig", errors="ignore")
            reader = csv_mod.DictReader(io_mod.StringIO(texto))
            linhas = list(reader)
            st.info(f"{len(linhas)} linha(s) encontradas no arquivo.")
            if st.button("Importar pesagens"):
                res = importar_pesagens_csv(linhas, lote_id)
                registrar_auditoria(u["id"], "import_pesagens", "pesagens",
                                    lote_id, f"{res['importados']} importadas")
                st.success(f"✅ {res['importados']} pesagens importadas | "
                           f"🆕 {res['animais_criados']} animais criados | "
                           f"❌ {res['erros']} erros")
                for msg in res["mensagens"]:
                    st.warning(msg)

    with tab2:
        st.markdown('''
        **Formato esperado do CSV:**
        ```
        identificacao,idade,raca,sexo,peso_entrada,peso_alvo
        BOI-001,24,Nelore,macho,280,450
        ```
        Apenas `identificacao` é obrigatório.
        ''')
        arq2 = st.file_uploader("Selecione o arquivo CSV", type=["csv"], key="csv_animais")
        if arq2:
            import csv as csv_mod, io as io_mod
            texto2 = arq2.read().decode("utf-8-sig", errors="ignore")
            reader2 = csv_mod.DictReader(io_mod.StringIO(texto2))
            linhas2 = list(reader2)
            st.info(f"{len(linhas2)} linha(s) encontradas.")
            if st.button("Importar animais"):
                res2 = importar_animais_csv(linhas2, lote_id)
                registrar_auditoria(u["id"], "import_animais", "animais",
                                    lote_id, f"{res2['importados']} importados")
                st.success(f"✅ {res2['importados']} animais importados | "
                           f"❌ {res2['erros']} erros")
                for msg in res2["mensagens"]:
                    st.warning(msg)

# ===========================================================================
# COTAÇÃO CEPEA
# ===========================================================================
elif menu == "Cotação Cepea":
    _page_header("📈", "Cotação Cepea", "Preço do boi gordo -- ESALQ/Cepea")

    col1, col2 = st.columns([2,1])
    with col1:
        if st.button("🔄 Buscar cotação atual"):
            from cepea import buscar_cotacao_cepea
            with st.spinner("Buscando no Cepea..."):
                res = buscar_cotacao_cepea()
            if res["sucesso"]:
                salvar_cotacao(res["data"], res["preco"], res["fonte"])
                st.success(f"✅ R$ {res['preco']:.2f}/@ -- {res['data']}")
            else:
                st.warning(f"Cepea indisponível: {res['msg']}")

    with col2:
        with st.form("form_cotacao_manual"):
            dt_cot = st.date_input("Data")
            pr_cot = st.number_input("Preço (R$/@)", 0.0, 1000.0, 195.0)
            if st.form_submit_button("Salvar manual"):
                salvar_cotacao(str(dt_cot), pr_cot, "manual")
                st.success("Salvo!"); st.rerun()

    cotacoes = listar_cotacoes(0)  # todas
    if cotacoes:
        ult = cotacoes[-1]
        st.metric("💰 Última cotação", f"R$ {ult[2]:.2f}/@",
                  delta=f"{ult[1]} ({ult[3]})")

        hist = historico_grafico(cotacoes[-60:])  # últimas 60
        if hist["datas"]:
            df_cot = pd.DataFrame({"Data": hist["datas"], "Preço R$/@": hist["precos"]})
            df_cot = df_cot.set_index("Data")
            st.subheader("📊 Histórico de cotações")
            st.line_chart(df_cot)
            st.dataframe(df_cot.tail(10), use_container_width=True)
    else:
        st.info("Nenhuma cotação registrada. Clique em 'Buscar cotação atual' ou insira manualmente.")

# ===========================================================================
# SCORE DE SAÚDE
# ===========================================================================
elif menu == "Score de Saúde":
    _page_header("💯", "Score de Saúde", "Ranking 0-100 por animal (GMD + ocorrências + reprodução)")

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

    scores = []
    for a in animais:
        sc = calcular_score_saude(a[0])
        car = verificar_carencia(a[0])
        scores.append({
            "Animal":       a[1],
            "Score":        sc["score"],
            "Classificação":sc["classificacao"],
            "GMD":          sc["detalhes"]["gmd"],
            "Ocorrências":  sc["detalhes"]["n_ocorrencias"],
            "Pts GMD":      sc["detalhes"]["pts_gmd"],
            "Pts Ocorr.":   sc["detalhes"]["pts_ocorrencias"],
            "Pts Reprod.":  sc["detalhes"]["pts_reproducao"],
            "Em Carência":  "⚠️ Sim" if car["em_carencia"] else "✅ Não",
        })

    df_sc = pd.DataFrame(scores).sort_values("Score", ascending=False)
    st.dataframe(df_sc, use_container_width=True)

    # Métricas resumo
    col1,col2,col3,col4 = st.columns(4)
    col1.metric("🏆 Score médio", f"{df_sc['Score'].mean():.1f}")
    col2.metric("🥇 Melhor animal", df_sc.iloc[0]["Animal"])
    col3.metric("⚠️ Críticos (< 40)", len(df_sc[df_sc["Score"]<40]))
    col4.metric("💊 Em carência", len(df_sc[df_sc["Em Carência"]=="⚠️ Sim"]))

    # Gráfico
    st.bar_chart(df_sc.set_index("Animal")["Score"])

    # Alertas individuais
    st.subheader("🚨 Alertas")
    for _, row in df_sc.iterrows():
        if row["Score"] < 40:
            st.error(f"🔴 {row['Animal']}: Score {row['Score']} -- CRÍTICO")
        elif row["Score"] < 60:
            st.warning(f"🟡 {row['Animal']}: Score {row['Score']} -- Regular")
        if row["Em Carência"] == "⚠️ Sim":
            st.warning(f"💊 {row['Animal']}: em período de carência -- verificar liberação para abate")

# ===========================================================================
# MARGEM REAL DO LOTE
# ===========================================================================
elif menu == "Margem Real do Lote":
    _page_header("💰", "Margem Real do Lote", "Resultado financeiro: compra × venda × custos")

    lotes = listar_lotes()
    if not lotes:
        st.warning("Nenhum lote cadastrado.")
        st.stop()

    dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    lote_sel = st.selectbox("Selecione o lote", list(dict_l.keys()))
    lote_id  = dict_l[lote_sel]

    tab1, tab2 = st.tabs(["📊 Resultado", "➕ Registrar Venda"])

    with tab1:
        mg = calcular_margem_lote(lote_id)
        if mg:
            if not mg["venda_registrada"]:
                st.info("💡 Nenhuma venda registrada ainda. Registre na aba ao lado para ver a margem real.")

            col1,col2,col3 = st.columns(3)
            col1.metric("🛒 Custo de compra", f"R$ {mg['custo_compra']:,.2f}")
            col2.metric("📈 Receita real", f"R$ {mg['receita_real']:,.2f}")
            col3.metric("💊 Custo sanitário", f"R$ {mg['custo_sanitario']:,.2f}")

            cor = "normal" if mg["margem"] >= 0 else "inverse"
            st.metric("💰 Margem líquida",
                      f"R$ {mg['margem']:,.2f}",
                      delta=f"{mg['margem_pct']:.1f}%",
                      delta_color=cor)

            if mg["venda_registrada"]:
                st.success(f"🏭 Frigorífico: {mg['frigorific']} -- Venda: {mg['data_venda']}")

            # Histórico de vendas
            vendas = listar_vendas_lote(lote_id)
            if vendas:
                st.subheader("📋 Histórico de vendas")
                df_v = pd.DataFrame(vendas, columns=["ID","Lote","Data","R$/kg",
                                                      "Peso Total kg","Frigorífico","Obs"])
                st.dataframe(df_v, use_container_width=True)

    with tab2:
        with st.form("form_venda"):
            dt_venda = st.date_input("Data da venda")
            pr_kg    = st.number_input("Preço de venda (R$/kg)", 0.0, 100.0, 22.0)
            peso_tot = st.number_input("Peso total vendido (kg)", 0.0)
            frig     = st.text_input("Frigorífico")
            obs_v    = st.text_area("Observação")
            if st.form_submit_button("Registrar Venda"):
                if peso_tot > 0:
                    registrar_venda_lote(lote_id, str(dt_venda),
                                         pr_kg, peso_tot, frig, obs_v)
                    registrar_auditoria(u["id"], "venda_lote", "vendas_lote",
                                        lote_id, f"R${pr_kg}/kg {peso_tot}kg {frig}")
                    st.success("Venda registrada!")
                    st.rerun()
                else:
                    st.error("Informe o peso total.")

# ===========================================================================
# RASTREABILIDADE GTA
# ===========================================================================
elif menu == "Rastreabilidade GTA":
    _page_header("📋", "Rastreabilidade GTA", "Guia de Trânsito Animal e certificação SISBOV")

    tab1, tab2, tab3 = st.tabs(["📄 GTAs", "➕ Emitir GTA", "🔖 SISBOV"])

    with tab1:
        gtas = listar_gta()
        if gtas:
            df_g = pd.DataFrame(gtas, columns=["ID","Lote ID","Lote","Nº GTA",
                                                "Emissão","Origem","Destino",
                                                "Qtd","Finalidade","Obs"])
            st.dataframe(df_g, use_container_width=True)
            st.metric("📄 Total de GTAs", len(gtas))
        else:
            st.info("Nenhuma GTA registrada.")

    with tab2:
        lotes = listar_lotes()
        if not lotes:
            st.warning("Cadastre um lote primeiro.")
        else:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            with st.form("form_gta"):
                lote_g   = st.selectbox("Lote", list(dict_l.keys()))
                num_gta  = st.text_input("Número da GTA")
                dt_emis  = st.date_input("Data de emissão")
                origem   = st.text_input("Município/Fazenda de origem")
                destino  = st.text_input("Município/Frigorífico de destino")
                qtd_g    = st.number_input("Quantidade de animais", 1, step=1)
                finalid  = st.selectbox("Finalidade",
                             ["Abate","Recria","Engorda","Reprodução","Exposição"])
                obs_g    = st.text_area("Observação")
                if st.form_submit_button("Registrar GTA"):
                    if num_gta and origem and destino:
                        registrar_gta(dict_l[lote_g], num_gta, str(dt_emis),
                                      origem, destino, int(qtd_g), finalid, obs_g)
                        registrar_auditoria(u["id"],"gta","gta",
                                            dict_l[lote_g], num_gta)
                        st.success("GTA registrada!"); st.rerun()
                    else:
                        st.error("Preencha número, origem e destino.")

    with tab3:
        lotes = listar_lotes()
        if lotes:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            lote_s  = st.selectbox("Lote", list(dict_l.keys()), key="sisbov_lote")
            animais = listar_animais_por_lote(dict_l[lote_s])
            if animais:
                dict_a = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
                anim_s = st.selectbox("Animal", list(dict_a.keys()))
                aid_s  = dict_a[anim_s]
                sb = obter_sisbov(aid_s)
                if sb:
                    st.success(f"✅ SISBOV cadastrado: **{sb[2]}** -- {sb[3]}")
                else:
                    st.info("Animal sem SISBOV cadastrado.")
                with st.form("form_sisbov"):
                    num_sb = st.text_input("Número SISBOV (15 dígitos)")
                    dt_sb  = st.date_input("Data de certificação")
                    if st.form_submit_button("Cadastrar SISBOV"):
                        if len(num_sb) == 15:
                            registrar_sisbov(aid_s, num_sb, str(dt_sb))
                            st.success("SISBOV cadastrado!"); st.rerun()
                        else:
                            st.error("SISBOV deve ter exatamente 15 dígitos.")

# ===========================================================================
# COMPARATIVO DE LOTES
# ===========================================================================
elif menu == "Comparativo de Lotes":
    _page_header("🔀", "Comparativo de Lotes", "Side-by-side de GMD, custos e resultados")

    lotes = listar_lotes()
    if len(lotes) < 2:
        st.warning("Cadastre pelo menos 2 lotes para comparar.")
        st.stop()

    dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    selecionados = st.multiselect("Selecione 2 a 4 lotes para comparar",
                                   list(dict_l.keys()),
                                   default=list(dict_l.keys())[:min(2,len(dict_l))])
    if len(selecionados) < 2:
        st.info("Selecione pelo menos 2 lotes.")
        st.stop()

    preco_kg   = st.number_input("Preço do kg (R$)", 0.0, 100.0, 20.0)
    custo_diar = st.number_input("Custo diário/animal (R$)", 0.0, 100.0, 10.0)

    dados = []
    for nome_l in selecionados:
        lid  = dict_l[nome_l]
        anim = listar_animais_por_lote(lid)
        tm   = taxa_mortalidade_lote(lid)
        tp   = taxa_prenhez_lote(lid)

        gmds, ganho_t, dias_t, custo_san = [], 0, 0, 0
        for a in anim:
            ps = listar_pesagens(a[0])
            if len(ps) >= 2:
                df = pd.DataFrame(ps, columns=["id","aid","peso","data"])
                df["data"] = pd.to_datetime(df["data"])
                df = df.sort_values("data")
                dias = (df["data"].iloc[-1]-df["data"].iloc[0]).days
                if dias > 0:
                    g = (df["peso"].iloc[-1]-df["peso"].iloc[0])/dias
                    if 0 < g <= 2: gmds.append(g)
                    ganho_t += df["peso"].iloc[-1]-df["peso"].iloc[0]
                    dias_t  += dias
            for oc in listar_ocorrencias(a[0]):
                if oc[6]: custo_san += oc[6]

        gmd_m = round(sum(gmds)/len(gmds),3) if gmds else 0
        receita = ganho_t * preco_kg
        custo_op = custo_diar * len(anim) * (dias_t/max(len(anim),1))
        lucro = receita - custo_op - custo_san

        dados.append({
            "Lote":           nome_l.split(" (ID")[0],
            "Animais":        len(anim),
            "GMD médio":      gmd_m,
            "Incidência %":   round(len([a for a in anim if listar_ocorrencias(a[0])])/max(len(anim),1)*100,1),
            "Mortalidade %":  tm["taxa"],
            "Prenhez %":      round(tp["taxa"],1),
            "Receita R$":     round(receita,2),
            "Custo San. R$":  round(custo_san,2),
            "Lucro R$":       round(lucro,2),
        })

    df_comp = pd.DataFrame(dados).set_index("Lote")
    st.dataframe(df_comp, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 GMD médio por lote")
        st.bar_chart(df_comp["GMD médio"])
    with col2:
        st.subheader("💰 Lucro estimado por lote")
        st.bar_chart(df_comp["Lucro R$"])

    melhor = df_comp["GMD médio"].idxmax()
    pior   = df_comp["GMD médio"].idxmin()
    st.success(f"🥇 Melhor GMD: **{melhor}** ({df_comp.loc[melhor,'GMD médio']:.3f} kg/dia)")
    st.warning(f"⚠️ Pior GMD: **{pior}** ({df_comp.loc[pior,'GMD médio']:.3f} kg/dia)")

# ===========================================================================
# GMD AO LONGO DO TEMPO
# ===========================================================================
elif menu == "GMD ao Longo do Tempo":
    _page_header("📉", "GMD ao Longo do Tempo", "Evolução temporal do ganho de peso do lote")

    lotes = listar_lotes()
    if not lotes:
        st.warning("Nenhum lote cadastrado.")
        st.stop()

    dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    lote_sel = st.selectbox("Selecione o lote", list(dict_l.keys()))
    lote_id  = dict_l[lote_sel]

    janela = st.slider("Janela de cálculo (dias)", 7, 60, 14)

    pontos = calcular_gmd_temporal(lote_id, janela_dias=janela)
    if pontos:
        df_gmd = pd.DataFrame(pontos, columns=["Data","GMD médio (kg/dia)"])
        df_gmd = df_gmd.set_index("Data")
        st.line_chart(df_gmd)
        st.dataframe(df_gmd, use_container_width=True)

        ultimo_gmd = pontos[-1][1]
        primeiro_gmd = pontos[0][1]
        delta = ultimo_gmd - primeiro_gmd
        st.metric("📈 GMD atual", f"{ultimo_gmd:.3f} kg/dia",
                  delta=f"{delta:+.3f} vs início")

        if delta < -0.1:
            st.error("🔴 GMD em queda -- revisar nutrição e saúde do lote")
        elif delta > 0.1:
            st.success("✅ GMD em melhora -- manejo eficaz")
        else:
            st.info("📊 GMD estável")
    else:
        st.info("Dados insuficientes. Registre pesagens em datas diferentes para visualizar a evolução.")

# ===========================================================================
# BACKUP DO SISTEMA
# ===========================================================================
elif menu == "Backup do Sistema":
    _page_header("💾", "Backup do Sistema", "Download e envio automático dos seus dados")

    import database as _db_mod
    db_path = _db_mod.DB_PATH

    st.info(f"Banco de dados: `{db_path}`")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📦 Download ZIP (CSVs)")
        st.write("Exporta todas as tabelas em formato CSV dentro de um arquivo ZIP.")
        # Gera o backup direto -- sem step intermediário de button
        if not _BACKUP_OK:
            st.error("backup.py não encontrado no repositório.")
        else:
            with st.spinner("Preparando backup ZIP..."):
                dados_zip = gerar_backup_zip(db_path)
            nome_zip = nome_arquivo_backup("zip")
            st.download_button(
                "⬇️ Baixar Backup ZIP",
                dados_zip,
                nome_zip,
                "application/zip",
                key="dl_zip",
            )
            registrar_auditoria(u["id"], "backup_zip", "sistema", None, nome_zip)

    with col2:
        st.subheader("🗄️ Download SQLite")
        st.write("Cópia fiel do banco -- pode ser restaurada diretamente.")
        if not _BACKUP_OK:
            st.error("backup.py não encontrado no repositório.")
        else:
            with st.spinner("Preparando backup SQLite..."):
                dados_db = gerar_backup_sqlite(db_path)
            nome_db = nome_arquivo_backup("db")
            st.download_button(
                "⬇️ Baixar Backup SQLite",
                dados_db,
                nome_db,
                "application/octet-stream",
                key="dl_db",
            )
            registrar_auditoria(u["id"], "backup_sqlite", "sistema", None, nome_db)

    st.divider()
    st.subheader("📧 Enviar backup por e-mail")
    if not email_configurado():
        st.warning("Configure o SMTP em `.streamlit/secrets.toml` para envio por e-mail.")
    else:
        email_dest = st.text_input("E-mail de destino", value=u["email"])
        if st.button("Enviar backup ZIP por e-mail"):
            from backup import enviar_backup_email
            import notifications as _notif
            ok, msg, _, _ = enviar_backup_email(db_path, _notif, email_dest, u["nome"])
            st.success(msg) if ok else st.warning(msg)

# ===========================================================================
# LOG DE AUDITORIA
# ===========================================================================
elif menu == "Log de Auditoria":
    _page_header("📜", "Log de Auditoria", "Histórico completo de ações por usuário")

    if u["perfil"] != "admin":
        st.warning("Acesso restrito a administradores.")
        st.stop()

    col1, col2 = st.columns(2)
    limite = col1.slider("Últimos registros", 10, 500, 100)
    usuario_filtro = col2.selectbox("Filtrar por usuário",
                                     ["Todos"] + [f"{x[1]} (ID {x[0]})"
                                                  for x in listar_usuarios()])
    uid_f = None
    if usuario_filtro != "Todos":
        uid_f = int(usuario_filtro.split("ID ")[1].rstrip(")"))

    logs = listar_auditoria(limite, uid_f)
    if logs:
        df_log = pd.DataFrame(logs, columns=["ID","Usuário","Ação",
                                              "Tabela","Registro ID",
                                              "Detalhe","Data/Hora"])
        st.dataframe(df_log, use_container_width=True)
        st.metric("📋 Total de registros", len(logs))
    else:
        st.info("Nenhum registro de auditoria encontrado.")# Sistema de Gestao Pecuaria -- app principal.
# Execute com:  streamlit run app.py



import os as _os
if not _os.path.exists('database.py'):
    exec(open('setup_files.py').read())

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
try:
    from exports import gerar_excel_lote, gerar_excel_sanitario, gerar_pdf_relatorio
    _EXPORTS_OK = True
except ImportError:
    _EXPORTS_OK = False
    def gerar_excel_lote(*a, **k): return b""
    def gerar_excel_sanitario(*a, **k): return b""
    def gerar_pdf_relatorio(*a, **k): return b"" 
try:
    from notifications import (
        email_boas_vindas, email_trial_expirando, email_trial_expirado,
        email_vacina_pendente, email_medicamento_critico,
        email_parto_previsto, email_abate_previsto, email_configurado,
        _enviar, _template,
    )
    _NOTIF_OK = True
except ImportError:
    _NOTIF_OK = False
    def email_boas_vindas(*a, **k): return (False, "notifications.py não encontrado")
    def email_trial_expirando(*a, **k): return (False, "")
    def email_trial_expirado(*a, **k): return (False, "")
    def email_vacina_pendente(*a, **k): return (False, "")
    def email_medicamento_critico(*a, **k): return (False, "")
    def email_parto_previsto(*a, **k): return (False, "")
    def email_abate_previsto(*a, **k): return (False, "")
    def email_configurado(): return False
    def _enviar(*a, **k): return (False, "")
    def _template(*a, **k): return "" 
try:
    from cepea import cotacao_com_cache, historico_grafico
    _CEPEA_OK = True
except ImportError:
    _CEPEA_OK = False
    def cotacao_com_cache(_db): return dict(preco=0.0, data="", fonte="", sucesso=False, msg="módulo cepea.py não encontrado")
    def historico_grafico(c): return dict(datas=[], precos=[])

try:
    from backup import gerar_backup_zip, gerar_backup_sqlite, nome_arquivo_backup
    _BACKUP_OK = True
except ImportError:
    _BACKUP_OK = False
    def gerar_backup_zip(p): return b""
    def gerar_backup_sqlite(p): return b""
    def nome_arquivo_backup(ext="zip"): return f"backup.{ext}" 
from database import (
    registrar_morte, listar_mortalidade, taxa_mortalidade_lote,
    registrar_auditoria, listar_auditoria,
    registrar_gta, listar_gta, registrar_sisbov, obter_sisbov,
    calcular_score_saude,
    registrar_venda_lote, calcular_margem_lote, listar_vendas_lote,
    salvar_cotacao, listar_cotacoes, obter_ultima_cotacao,
    calcular_gmd_temporal,
    importar_pesagens_csv, importar_animais_csv,
    verificar_carencia,
    atualizar_qtd_lote, resumo_lote,
)

inicializar_banco()

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão Pecuária",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
# SIDEBAR -- usuário logado
# ---------------------------------------------------------------------------
u = st.session_state.usuario

# --- Cabeçalho do usuário ---
with st.sidebar:
    col_icon, col_info = st.columns([1, 3])
    with col_icon:
        perfil_emoji = {"admin": "⚙️", "veterinario": "🩺", "fazendeiro": "🌾"}.get(u["perfil"], "👤")
        st.markdown(f"<div style='font-size:28px;padding-top:4px'>{perfil_emoji}</div>",
                    unsafe_allow_html=True)
    with col_info:
        st.markdown(f"**{u['nome']}**")
        st.caption(u["perfil"].capitalize())
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.usuario = None
        st.rerun()

# --- Banner de trial ---
_status_plano = obter_status_plano(u["id"])
with st.sidebar:
    if _status_plano["plano"] == "trial":
        _dr = _status_plano["dias_restantes"]
        if _dr <= 3:
            st.error(f"🔴 Trial: {_dr} dia(s) restante(s)!")
        elif _dr <= 7:
            st.warning(f"⚠️ Trial expira em {_dr} dias")
            if email_configurado():
                email_trial_expirando(u["email"], u["nome"], _dr)
        else:
            pct = int((_dr / 30) * 100)
            st.progress(pct / 100, text=f"🕐 Trial: {_dr}/30 dias")
    elif _status_plano["plano"] == "expirado":
        st.error("🔴 Trial expirado")
        if email_configurado():
            email_trial_expirado(u["email"], u["nome"])
    else:
        st.success("✅ Plano ativo")

# --- Alertas rápidos compactos ---
_pendentes = listar_vacinas_pendentes()
_criticos  = listar_medicamentos_criticos()
_partos    = listar_partos_previstos()
with st.sidebar:
    alertas = []
    if _pendentes: alertas.append(f"💉 {len(_pendentes)} vacina(s)")
    if _criticos:  alertas.append(f"💊 {len(_criticos)} med. crítico(s)")
    if _partos:    alertas.append(f"🐄 {len(_partos)} parto(s) em 30d")
    if alertas:
        st.warning("**Alertas:** " + " · ".join(alertas))

st.sidebar.divider()

# --- MENU REORGANIZADO EM GRUPOS ---
with st.sidebar:
    st.caption("NAVEGAÇÃO")

menu = st.sidebar.selectbox(
    "Ir para",
    [
        # ── INÍCIO ─────────────────────────────────
        "🏠  Início",
        "🔍  Buscar Animal",
        # ── CADASTROS ──────────────────────────────
        "─── Cadastros ───",
        "📦  Cadastrar Lote",
        "🐄  Cadastrar Animal",
        "⚖️  Registrar Pesagem",
        "🚨  Registrar Ocorrência",
        "💀  Registrar Morte",
        "📥  Importar Dados (CSV)",
        # ── ANÁLISE ────────────────────────────────
        "─── Análise ───",
        "📊  Dashboard Sanitário",
        "📈  Analisar por Lote",
        "🐄  Analisar Animal",
        "💯  Score de Saúde",
        "📉  GMD ao Longo do Tempo",
        "🔀  Comparativo de Lotes",
        "💰  Painel de Decisão",
        "📊  Dashboard Executivo",
        "🔎  Pesquisar Ocorrências",
        # ── GESTÃO ─────────────────────────────────
        "─── Gestão ───",
        "💉  Calendário Sanitário",
        "💊  Estoque de Medicamentos",
        "🐄  Controle Reprodutivo",
        "🌿  Mapa de Piquetes",
        "🥩  Previsão de Abate",
        "📋  Prontuário do Animal",
        "💰  Margem Real do Lote",
        "📈  Cotação Cepea",
        # ── RASTREABILIDADE ────────────────────────
        "─── Rastreabilidade ───",
        "📄  Rastreabilidade GTA",
        # ── RELATÓRIOS ─────────────────────────────
        "─── Relatórios ───",
        "📄  Exportar Relatórios",
        "💾  Backup do Sistema",
        # ── SISTEMA ────────────────────────────────
        "─── Sistema ───",
        "📧  Notificações",
        "📜  Log de Auditoria",
        "⚙️  Administração",
    ],
    label_visibility="collapsed",
)

# Navegação programática (ações rápidas do Home)
if "_nav" in st.session_state and st.session_state["_nav"]:
    _destino = st.session_state.pop("_nav")
    # Encontrar a chave do menu_map que aponta para o destino
    _chave = next((k for k, v in _menu_map.items() if v == _destino), None)
    if _chave:
        st.session_state["_menu_key"] = _chave

# Normalizar menu: remover emoji + espaços para manter compatibilidade
import re as _re
_menu_map = {
    "🏠  Início":                   "Home Dashboard",
    "🔍  Buscar Animal":             "Busca de Animal",
    "📦  Cadastrar Lote":            "Cadastrar Lote",
    "🐄  Cadastrar Animal":          "Cadastrar Animal",
    "⚖️  Registrar Pesagem":         "Registrar Pesagem",
    "🚨  Registrar Ocorrência":      "Ocorrências Adversas",
    "💀  Registrar Morte":           "Mortalidade",
    "📥  Importar Dados (CSV)":      "Importar Dados",
    "📊  Dashboard Sanitário":       "Dashboard Sanitário",
    "📈  Analisar por Lote":         "Analisar por Lote",
    "🐄  Analisar Animal":           "Analisar Animal",
    "💯  Score de Saúde":            "Score de Saúde",
    "📉  GMD ao Longo do Tempo":     "GMD ao Longo do Tempo",
    "🔀  Comparativo de Lotes":      "Comparativo de Lotes",
    "💰  Painel de Decisão":         "Painel de Decisão",
    "📊  Dashboard Executivo":       "Dashboard Executivo",
    "🔎  Pesquisar Ocorrências":     "Pesquisar Ocorrências",
    "💉  Calendário Sanitário":      "Calendário Sanitário",
    "💊  Estoque de Medicamentos":   "Estoque de Medicamentos",
    "🐄  Controle Reprodutivo":      "Controle Reprodutivo",
    "🌿  Mapa de Piquetes":          "Mapa de Piquetes",
    "🥩  Previsão de Abate":         "Previsão de Abate",
    "📋  Prontuário do Animal":      "Prontuário do Animal",
    "💰  Margem Real do Lote":       "Margem Real do Lote",
    "📈  Cotação Cepea":             "Cotação Cepea",
    "📄  Rastreabilidade GTA":       "Rastreabilidade GTA",
    "📄  Exportar Relatórios":       "Exportar Relatórios",
    "💾  Backup do Sistema":         "Backup do Sistema",
    "📧  Notificações":              "Notificações",
    "📜  Log de Auditoria":          "Log de Auditoria",
    "⚙️  Administração":             "Administração",
}
# separadores viram None → página em branco
menu = _menu_map.get(menu, None)

# ---------------------------------------------------------------------------
# Helper: cabeçalho padronizado de página
# ---------------------------------------------------------------------------
def _page_header(icone: str, titulo: str, subtitulo: str = ""):
    '''Renderiza cabeçalho limpo e padronizado em todas as telas.'''
    st.markdown(f"## {icone} {titulo}")
    if subtitulo:
        st.caption(subtitulo)
    st.divider()

# ===========================================================================
# SEPARADORES (menu=None quando usuário clica num grupo)
# ===========================================================================
if menu is None:
    st.info("👈 Selecione uma opção no menu lateral.")
    st.stop()

# ===========================================================================
# CADASTRAR LOTE
# ===========================================================================
elif menu == "Cadastrar Lote":
    _page_header("📦", "Cadastrar Lote", "Registre um novo lote de animais")

    col_form, col_info = st.columns([2, 1])

    with col_form:
        with st.form("form_cadastrar_lote"):
            st.markdown("#### 📋 Dados do lote")
            c1, c2 = st.columns(2)
            with c1:
                nome         = st.text_input("Nome do lote *")
                data         = st.date_input("Data de entrada")
                qtd_comprada = st.number_input("Qtd comprada", min_value=0, step=1)
                transporte   = st.text_input("Transportadora")
            with c2:
                descricao     = st.text_area("Descrição", height=70)
                qtd_recebida  = st.number_input("Qtd recebida", min_value=0, step=1)
                preco_por_animal = st.number_input("Preço por animal (R$)", min_value=0.0)

            st.markdown("#### 🌿 Manejo")
            c3, c4 = st.columns(2)
            with c3:
                tipo_alimentacao = st.selectbox("Alimentação",
                    ["Pasto", "Confinamento", "Semi-confinamento"])
            with c4:
                tipo_dieta = st.selectbox("Dieta",
                    ["Capim", "Ração", "Silagem", "Misto"])

            salvar = st.form_submit_button("💾 Salvar Lote", use_container_width=True,
                                            type="primary")

        if salvar:
            if not nome:
                st.error("Informe o nome do lote")
            elif qtd_recebida > qtd_comprada:
                st.error("Quantidade recebida não pode ser maior que a comprada")
            elif qtd_recebida == 0:
                st.error("Informe a quantidade recebida")
            else:
                lid = adicionar_lote(nome, descricao, str(data),
                                     qtd_comprada, qtd_recebida, transporte)
                registrar_auditoria(u["id"], "criar_lote", "lotes", lid, nome)
                st.success(f"✅ Lote **{nome}** criado com sucesso!")
                st.balloons()

    with col_info:
        st.markdown("#### 💡 Dicas")
        st.info("**Nome:** use algo fácil de identificar, ex: *Lote Nelore Jan/25*")
        st.info("**Qtd recebida:** pode ser menor que a comprada se houve perdas no transporte")
        st.info("**Preço por animal:** usado para calcular a margem real na hora da venda")
        if "preco_por_animal" in dir() and qtd_comprada > 0:
            custo_total = preco_por_animal * qtd_comprada
            st.metric("💰 Custo total estimado", f"R$ {custo_total:,.2f}")

# ===========================================================================
# DASHBOARD SANITÁRIO
# ===========================================================================
elif menu == "Dashboard Sanitário":
    _page_header("🦠", "Dashboard Sanitário", "Incidências, curva epidêmica e alertas")

    lotes = listar_lotes()
    opcoes = ["Todos os lotes"]
    dict_lotes = {}
    for l in lotes:
        nome_opcao = f"{l[1]} (ID {l[0]})"
        opcoes.append(nome_opcao)
        dict_lotes[nome_opcao] = l[0]

    escolha = st.selectbox("Filtrar por lote", opcoes)

    if escolha == "Todos os lotes":
        animais = listar_animais()
    else:
        lote_id = dict_lotes[escolha]
        animais = listar_animais_por_lote(lote_id)

    # Coletar ocorrências
    todas_ocorrencias = []
    for animal in animais:
        oc = listar_ocorrencias(animal[0])
        todas_ocorrencias.extend(oc)

    df_oc = pd.DataFrame(
        todas_ocorrencias,
        columns=["id","animal_id","data","tipo","descricao",
                 "gravidade","custo","dias_recuperacao","status"],
    ) if todas_ocorrencias else pd.DataFrame(
        columns=["id","animal_id","data","tipo","descricao",
                 "gravidade","custo","dias_recuperacao","status"])

    total_animais = len(animais)
    animais_com_oc = df_oc["animal_id"].nunique() if len(df_oc) > 0 else 0
    incidencia     = (animais_com_oc / total_animais * 100) if total_animais > 0 else 0
    custo_total_oc = df_oc["custo"].fillna(0).sum() if len(df_oc) > 0 else 0

    # --- KPIs ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🐄 Animais analisados", total_animais)
    k2.metric("🦠 Com ocorrência",     animais_com_oc)
    k3.metric("📊 Incidência",         f"{incidencia:.1f}%",
              delta="⚠️ Alta" if incidencia > 20 else None,
              delta_color="inverse" if incidencia > 20 else "normal")
    k4.metric("💊 Custo sanitário",    f"R$ {custo_total_oc:.2f}")

    st.divider()

    if len(df_oc) > 0:
        tab_graf, tab_lote, tab_curva, tab_corr, tab_alerta = st.tabs([
            "📊 Gráficos", "🐄 Por Lote", "📈 Curva Epidêmica",
            "📉 Correlação GMD", "🚨 Alertas"
        ])

        with tab_graf:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Ocorrências por tipo")
                st.bar_chart(df_oc["tipo"].value_counts())
            with c2:
                st.subheader("Por gravidade")
                st.bar_chart(df_oc["gravidade"].value_counts())

        with tab_lote:
            dados_lote = []
            for lote in lotes:
                lid_t = lote[0]
                animais_lote = listar_animais_por_lote(lid_t)
                total = len(animais_lote)
                ids   = [a[0] for a in animais_lote]
                oc_lt = df_oc[df_oc["animal_id"].isin(ids)] if len(df_oc) > 0 else pd.DataFrame()
                doentes = oc_lt["animal_id"].nunique() if len(oc_lt) > 0 else 0
                inc_l   = (doentes / total * 100) if total > 0 else 0
                dados_lote.append((lote[1], inc_l))
            df_lt = pd.DataFrame(dados_lote, columns=["Lote","Incidência (%)"]).set_index("Lote")
            st.bar_chart(df_lt)

            dados_tipo = []
            if total_animais > 0:
                for tipo in df_oc["tipo"].unique():
                    d_tp = df_oc[df_oc["tipo"] == tipo]["animal_id"].nunique()
                    dados_tipo.append((tipo, d_tp / total_animais * 100))
            if dados_tipo:
                df_tp = pd.DataFrame(dados_tipo, columns=["Tipo","Incidência (%)"]).set_index("Tipo")
                st.subheader("Por tipo (%)")
                st.bar_chart(df_tp)

        with tab_curva:
            df_oc["data"] = pd.to_datetime(df_oc["data"])
            curva_tipo = df_oc.groupby(["data","tipo"]).size().unstack(fill_value=0)
            st.line_chart(curva_tipo)

        with tab_corr:
            dados_corr = []
            for animal in listar_animais():
                ps = listar_pesagens(animal[0])
                if len(ps) > 1:
                    df_p = pd.DataFrame(ps, columns=["ID","Animal","Peso","Data"])
                    df_p["Data"] = pd.to_datetime(df_p["Data"])
                    df_p = df_p.sort_values("Data")
                    dias = (df_p["Data"].iloc[-1] - df_p["Data"].iloc[0]).days
                    if dias > 0:
                        g = (df_p["Peso"].iloc[-1] - df_p["Peso"].iloc[0]) / dias
                        qtd = len(listar_ocorrencias(animal[0]))
                        dados_corr.append((animal[1], round(g,3), qtd))
            if dados_corr:
                df_c = pd.DataFrame(dados_corr, columns=["Animal","GMD","Ocorrencias"])
                st.scatter_chart(df_c, x="Ocorrencias", y="GMD")
                media_g = df_c["GMD"].mean()
                for _, row in df_c.iterrows():
                    if row["Ocorrencias"] > 0 and row["GMD"] < media_g:
                        st.error(f"🔴 {row['Animal']}: baixo GMD + ocorrência")
                    elif row["Ocorrencias"] > 0:
                        st.warning(f"🟡 {row['Animal']}: ocorrência sem impacto aparente")
                    elif row["GMD"] < media_g:
                        st.warning(f"🟠 {row['Animal']}: baixo GMD sem ocorrência")
                    else:
                        st.success(f"🟢 {row['Animal']}: bom desempenho e saudável")
            else:
                st.info("Sem dados suficientes para correlação")

        with tab_alerta:
            # Alertas por lote
            st.subheader("Por lote")
            for nome, inc in dados_lote:
                if inc > 20:   st.error(f"🔴 {nome}: alta incidência ({inc:.1f}%)")
                elif inc > 5:  st.warning(f"🟡 {nome}: incidência moderada ({inc:.1f}%)")
                else:          st.success(f"🟢 {nome}: controle adequado ({inc:.1f}%)")

            if dados_tipo:
                st.subheader("Por tipo")
                for tipo, inc in dados_tipo:
                    if inc > 20:  st.error(f"🔴 {tipo}: alta incidência ({inc:.1f}%)")
                    elif inc > 5: st.warning(f"🟡 {tipo}: incidência moderada ({inc:.1f}%)")
                    else:         st.success(f"🟢 {tipo}: controle adequado ({inc:.1f}%)")

            # Alertas inteligentes
            st.subheader("🧠 Alertas Inteligentes")
            for lote in listar_lotes():
                lid_a   = lote[0]
                nom_a   = lote[1]
                anim_a  = listar_animais_por_lote(lid_a)
                tot_a   = len(anim_a)
                if tot_a == 0: continue
                ocs_a, gmds_a, custo_a = [], [], 0
                for an in anim_a:
                    oc_a = listar_ocorrencias(an[0])
                    ocs_a.extend(oc_a)
                    custo_a += sum(o[6] for o in oc_a if o[6])
                    ps_a = listar_pesagens(an[0])
                    if len(ps_a) > 1:
                        df_a = pd.DataFrame(ps_a, columns=["ID","Animal","Peso","Data"])
                        df_a["Data"] = pd.to_datetime(df_a["Data"])
                        df_a = df_a.sort_values("Data")
                        d_a  = (df_a["Data"].iloc[-1]-df_a["Data"].iloc[0]).days
                        if d_a > 0:
                            g_a = (df_a["Peso"].iloc[-1]-df_a["Peso"].iloc[0])/d_a
                            if 0 <= g_a <= 2: gmds_a.append(g_a)
                inc_a  = (len(set(o[1] for o in ocs_a))/tot_a*100) if ocs_a else 0
                gmd_a  = sum(gmds_a)/len(gmds_a) if gmds_a else 0
                if inc_a > 20 and gmd_a < 0.5:
                    st.error(f"🔴 {nom_a}: incidência {inc_a:.1f}% + GMD {gmd_a:.2f} -- problema grave")
                elif custo_a > 1000:
                    st.warning(f"🟡 {nom_a}: custo sanitário elevado R$ {custo_a:.2f}")
                elif len(ocs_a) >= 5:
                    st.warning(f"🟠 {nom_a}: {len(ocs_a)} ocorrências -- monitorar surto")
                else:
                    st.success(f"🟢 {nom_a}: controlado (inc {inc_a:.1f}%, GMD {gmd_a:.2f})")
    else:
        st.info("Nenhuma ocorrência registrada ainda.")
        st.caption("Registre ocorrências em **Cadastros → Registrar Ocorrência**.")


# ===========================================================================
# CADASTRAR ANIMAL
# ===========================================================================
elif menu == "Cadastrar Animal":
    _page_header("🐄", "Cadastrar Animal", "Vincule um animal a um lote")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado.")
        st.info("👈 Vá em **Cadastros → Cadastrar Lote** primeiro.")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        col_sel, col_info = st.columns([2, 1])

        with col_sel:
            escolha = st.selectbox("Selecione o lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha]
        lote    = obter_lote(lote_id)
        qtd_recebida  = lote[5]
        total_animais = contar_animais_no_lote(lote_id)
        vagas = max(0, qtd_recebida - total_animais)

        with col_info:
            st.metric("🐄 Cadastrados / Capacidade",
                      f"{total_animais} / {qtd_recebida}",
                      delta=f"{vagas} vaga(s)" if vagas > 0 else "Lote cheio",
                      delta_color="normal" if vagas > 0 else "inverse")

        if total_animais >= qtd_recebida:
            st.error("⚠️ Limite do lote atingido. Aumente a capacidade em Cadastrar Lote.")
        else:
            with st.form("form_cadastrar_animal"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    identificacao = st.text_input("Identificação / Brinco *",
                                                   placeholder="Ex: BOI-001")
                with c2:
                    idade = st.number_input("Idade (meses)", 0, 240, value=24)
                with c3:
                    peso_entrada = st.number_input("Peso de entrada (kg)", 0.0, value=0.0)

                c4, c5, c6 = st.columns(3)
                with c4:
                    raca = st.text_input("Raça", placeholder="Ex: Nelore")
                with c5:
                    sexo = st.selectbox("Sexo", ["indefinido", "macho", "fêmea"])
                with c6:
                    peso_alvo = st.number_input("Peso alvo abate (kg)", 0.0, value=0.0)

                salvar = st.form_submit_button("💾 Cadastrar Animal",
                                               use_container_width=True, type="primary")

            if salvar:
                if not identificacao:
                    st.error("Informe a identificação do animal")
                else:
                    aid = adicionar_animal(identificacao, idade, lote_id)
                    if peso_alvo > 0 or raca or sexo != "indefinido" or peso_entrada > 0:
                        atualizar_animal_detalhes(aid, peso_alvo=peso_alvo if peso_alvo > 0 else None,
                                                  observacoes=None)
                    registrar_auditoria(u["id"], "cadastro_animal", "animais", aid, identificacao)
                    st.success(f"✅ **{identificacao}** cadastrado no lote **{lote[1]}**!")
                    st.rerun()

# ===========================================================================
# REGISTRAR PESAGEM
# ===========================================================================
elif menu == "Registrar Pesagem":
    _page_header("⚖️", "Registrar Pesagem", "Registre o peso atual de um animal")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado.")
        st.info("👈 Vá em **Cadastros → Cadastrar Lote** primeiro.")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}

        col_a, col_b = st.columns([1, 1])
        with col_a:
            escolha_lote = st.selectbox("Lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha_lote]
        animais = listar_animais_por_lote(lote_id)

        if len(animais) == 0:
            st.warning("Nenhum animal neste lote.")
        else:
            dict_animais = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
            with col_b:
                escolha_animal = st.selectbox("Animal", list(dict_animais.keys()))
            animal_id = dict_animais[escolha_animal]

            # Mostrar última pesagem do animal para referência
            pesagens_ant = listar_pesagens(animal_id)
            if pesagens_ant:
                ult = pesagens_ant[-1]
                det = obter_animal(animal_id)
                c1, c2, c3 = st.columns(3)
                c1.metric("⚖️ Último peso", f"{ult[2]:.1f} kg", f"em {ult[3]}")
                if det and det[7] > 0:
                    falta = det[7] - ult[2]
                    c2.metric("🎯 Peso alvo", f"{det[7]:.0f} kg",
                              f"faltam {falta:.1f} kg" if falta > 0 else "✅ atingido!")
                if len(pesagens_ant) >= 2:
                    df_p = pd.DataFrame(pesagens_ant, columns=["id","aid","peso","data"])
                    df_p["data"] = pd.to_datetime(df_p["data"])
                    df_p = df_p.sort_values("data")
                    dias = (df_p["data"].iloc[-1] - df_p["data"].iloc[0]).days
                    if dias > 0:
                        gmd_ref = (df_p["peso"].iloc[-1] - df_p["peso"].iloc[0]) / dias
                        c3.metric("📈 GMD atual", f"{gmd_ref:.3f} kg/dia")
                st.divider()

            with st.form("form_pesagem"):
                cp1, cp2 = st.columns(2)
                with cp1:
                    peso = st.number_input("Peso (kg) *", 0.0, 1000.0, step=0.5)
                with cp2:
                    data_p = st.date_input("Data da pesagem")
                salvar_p = st.form_submit_button("💾 Salvar Pesagem",
                                                  use_container_width=True, type="primary")

            if salvar_p:
                if peso <= 0:
                    st.error("Informe um peso válido (maior que zero)")
                elif peso > 1000:
                    st.error("Peso muito alto -- verifique o valor")
                else:
                    adicionar_pesagem(animal_id, peso, str(data_p))
                    registrar_auditoria(u["id"], "pesagem", "pesagens",
                                        animal_id, f"{peso}kg em {data_p}")
                    st.success(f"✅ Pesagem de **{peso:.1f} kg** registrada!")
                    st.rerun()

# ===========================================================================
# ANÁLISE POR LOTE
# ===========================================================================
elif menu == "Analisar por Lote":
    _page_header("📈", "Análise por Lote", "Desempenho econômico e zootécnico")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        escolha = st.selectbox("Selecione o lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha]

        lote = obter_lote(lote_id)
        animais = listar_animais_por_lote(lote_id)

        # --- Resumo consistente do lote ---
        rs = resumo_lote(lote_id)
        col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns(5)
        col_r1.metric("🐄 Animais ativos",   rs["ativos"])
        col_r2.metric("💀 Mortes",           rs["mortos"])
        col_r3.metric("📄 GTAs emitidas",    rs["gtas_emitidas"])
        col_r4.metric("🚨 Ocorrências",      rs["ocorrencias"])
        col_r5.metric("💉 Vacinas pendentes",rs["vacinas_pendentes"])
        st.divider()

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

        st.metric("📆 Duração do lote", f"{dias_lote} dias")
        st.metric("💰 Custo operacional", f"R$ {custo_operacional:,.2f}")

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
        st.metric("📈 Receita estimada", f"R$ {receita:,.2f}")
        st.metric("💸 Custo operacional", f"R$ {custo_operacional:,.2f}")
        st.metric("💊 Custo sanitário", f"R$ {custo_sanitario:,.2f}")

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
            st.metric("⚖️ Ganho total", f"{ganho_total:.2f} kg")
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
            st.metric("🚀 GMD médio do lote", f"{gmd_medio:.3f} kg/dia")
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
    _page_header("🐄", "Análise Individual", "Histórico de peso, ocorrências e alertas do animal")

    lotes = listar_lotes()
    if len(lotes) == 0:
        st.warning("Nenhum lote cadastrado")
    else:
        dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        ca1, ca2 = st.columns(2)
        with ca1:
            escolha_lote  = st.selectbox("Lote", list(dict_lotes.keys()))
        lote_id = dict_lotes[escolha_lote]
        animais = listar_animais_por_lote(lote_id)

        if len(animais) == 0:
            st.warning("Nenhum animal neste lote")
        else:
            dict_animais = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
            with ca2:
                escolha_animal = st.selectbox("Animal", list(dict_animais.keys()))
            animal_id  = dict_animais[escolha_animal]
            pesagens   = listar_pesagens(animal_id)
            ocorrencias = listar_ocorrencias(animal_id)
            gmd        = None
            sc         = calcular_score_saude(animal_id)

            # KPIs rápidos
            km1, km2, km3, km4 = st.columns(4)
            km1.metric("⚖️ Pesagens",    len(pesagens))
            km2.metric("🚨 Ocorrências", len(ocorrencias))
            km3.metric("💯 Score saúde", f"{sc['score']}/100")
            km4.metric("🏷️ Status",      sc["classificacao"])

            tab_peso, tab_oc, tab_alerta = st.tabs(
                ["📊 Pesagens & GMD", "🚨 Ocorrências", "🔔 Alertas & Diagnóstico"])

            with tab_peso:
                if len(pesagens) > 0:
                    df = pd.DataFrame(pesagens, columns=["ID","Animal","Peso","Data"])
                    df["Data"] = pd.to_datetime(df["Data"])
                    df = df.sort_values("Data")
                    st.line_chart(df.set_index("Data")["Peso"])
                    st.dataframe(df[["Data","Peso"]].rename(columns={"Peso":"Peso (kg)"}),
                                 use_container_width=True)

                    if len(df) > 1:
                        peso_inicial = df["Peso"].iloc[0]
                        peso_final   = df["Peso"].iloc[-1]
                        dias = (df["Data"].iloc[-1] - df["Data"].iloc[0]).days
                        if dias > 0:
                            gmd = (peso_final - peso_inicial) / dias
                            d1, d2, d3 = st.columns(3)
                            d1.metric("⚖️ Ganho total",  f"{peso_final-peso_inicial:.2f} kg")
                            d2.metric("📆 Período",       f"{dias} dias")
                            d3.metric("📈 GMD",           f"{gmd:.3f} kg/dia")
                            if gmd < 0:
                                st.error("🚨 Perda de peso -- possível doença")
                            elif gmd > 2:
                                st.error("🚨 GMD irreal -- revisar dados")
                            elif gmd < 0.5:
                                st.warning("⚠️ GMD baixo")
                            else:
                                st.success("✅ Bom desempenho")
                else:
                    st.info("Sem pesagens registradas para este animal.")

            with tab_oc:
                if len(ocorrencias) > 0:
                    df_oc = pd.DataFrame(ocorrencias,
                        columns=["id","animal_id","data","tipo","descricao",
                                 "gravidade","custo","dias_recuperacao","status"])
                    df_oc["data"] = pd.to_datetime(df_oc["data"])
                    st.dataframe(df_oc[["data","tipo","gravidade","descricao","custo","status"]],
                                 use_container_width=True)
                    custo_tot = df_oc["custo"].fillna(0).sum()
                    st.metric("💊 Custo total tratamentos", f"R$ {custo_tot:.2f}")
                    for _, row in df_oc.iterrows():
                        if row["gravidade"] == "Alta":
                            st.error(f"🔴 {row['tipo']} -- {row['descricao']}")
                        elif row["gravidade"] == "Média":
                            st.warning(f"🟡 {row['tipo']} -- {row['descricao']}")
                        else:
                            st.info(f"🔵 {row['tipo']} -- {row['descricao']}")
                else:
                    st.success("✅ Nenhuma ocorrência registrada")

            with tab_alerta:
                # Score detalhado
                det = sc["detalhes"]
                sa1, sa2, sa3 = st.columns(3)
                sa1.metric("GMD (pts)",         f"{det['pts_gmd']}/50")
                sa2.metric("Ocorrências (pts)", f"{det['pts_ocorrencias']}/35")
                sa3.metric("Reprodução (pts)",  f"{det['pts_reproducao']}/15")

                # Alerta integrado
                if gmd is not None:
                    if gmd < 0.5 and len(ocorrencias) > 0:
                        st.error("🚨 Alto risco: baixo desempenho + histórico clínico")
                    elif gmd < 0.5:
                        st.warning("⚠️ Baixo GMD -- revisar nutrição e sanidade")
                    elif len(ocorrencias) > 0:
                        st.warning("⚠️ Histórico clínico -- monitorar")
                    else:
                        st.success("✅ Animal saudável e produtivo")

                # Carência
                car = verificar_carencia(animal_id)
                if car["em_carencia"]:
                    st.error(f"💊 Em carência até **{car['liberado_em']}** -- não abater antes!")
                else:
                    st.success("✅ Sem restrição de carência")

# ===========================================================================
# OCORRÊNCIAS ADVERSAS
# ===========================================================================
elif menu == "Ocorrências Adversas":
    _page_header("🚨", "Registrar Ocorrência", "Doenças, lesões e medicações")

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
    _page_header("📊", "Painel de Decisão", "Resultado financeiro por lote")

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
    _page_header("🔎", "Pesquisar Ocorrências", "Filtros por lote, tipo e gravidade")

    lotes = listar_lotes()
    dict_lotes = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}

    # Filtros em linha
    f1, f2, f3 = st.columns(3)
    with f1:
        escolha_lote = st.selectbox("Lote", ["Todos"] + list(dict_lotes.keys()))
    with f2:
        tipo_f = st.selectbox("Tipo", ["Todos","Doença","Lesão","Medicamento","Outros"])
    with f3:
        grav_f = st.selectbox("Gravidade", ["Todas","Baixa","Média","Alta"])

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
        columns=["id","animal_id","data","tipo","descricao",
                 "gravidade","custo","dias_recuperacao","status"],
    ) if todas_ocorrencias else pd.DataFrame(
        columns=["id","animal_id","data","tipo","descricao",
                 "gravidade","custo","dias_recuperacao","status"])

    if len(df_oc) > 0:
        if tipo_f != "Todos":
            df_oc = df_oc[df_oc["tipo"] == tipo_f]
        if grav_f != "Todas":
            df_oc = df_oc[df_oc["gravidade"] == grav_f]
        df_oc["data"] = pd.to_datetime(df_oc["data"])
        df_oc = df_oc.sort_values(by="data", ascending=False)

    st.divider()

    if len(df_oc) > 0:
        # KPIs da pesquisa
        pk1, pk2, pk3, pk4 = st.columns(4)
        pk1.metric("📋 Ocorrências",    len(df_oc))
        pk2.metric("🐄 Animais afetados", df_oc["animal_id"].nunique())
        custo_tot = df_oc["custo"].fillna(0).sum()
        pk3.metric("💰 Custo total",    f"R$ {custo_tot:.2f}")
        altas = len(df_oc[df_oc["gravidade"]=="Alta"])
        pk4.metric("🔴 Gravidade Alta", altas,
                   delta="⚠️" if altas > 0 else None,
                   delta_color="inverse" if altas > 0 else "normal")

        # Nível de incidência
        if len(df_oc) >= 10:
            st.error("🚨 Alta incidência de ocorrências")
        elif len(df_oc) >= 5:
            st.warning("⚠️ Incidência moderada")
        else:
            st.success("✅ Baixa incidência")

        st.divider()
        tab_dados, tab_grafico = st.tabs(["📋 Registros", "📊 Análise"])

        with tab_dados:
            st.dataframe(
                df_oc[["data","tipo","gravidade","descricao","custo","dias_recuperacao","status"]],
                use_container_width=True
            )

        with tab_grafico:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("Por tipo")
                st.bar_chart(df_oc["tipo"].value_counts())
            with col_g2:
                st.subheader("Por gravidade")
                st.bar_chart(df_oc["gravidade"].value_counts())

            custo_por_tipo = df_oc.groupby("tipo")["custo"].sum()
            if len(custo_por_tipo) > 0:
                tipo_caro   = custo_por_tipo.idxmax()
                valor_caro  = custo_por_tipo.max()
                st.warning(f"💸 Maior impacto financeiro: **{tipo_caro}** -- R$ {valor_caro:.2f}")

        # Alertas inteligentes integrados
        st.divider()
        st.subheader("🧠 Alertas Inteligentes")
        for lote in listar_lotes():
            lid_i    = lote[0]
            nom_i    = lote[1]
            anim_i   = listar_animais_por_lote(lid_i)
            tot_i    = len(anim_i)
            if tot_i == 0: continue
            ocs_i, gmds_i, custo_i = [], [], 0
            for an in anim_i:
                oc_i = listar_ocorrencias(an[0])
                ocs_i.extend(oc_i)
                custo_i += sum(o[6] for o in oc_i if o[6])
                ps_i = listar_pesagens(an[0])
                if len(ps_i) > 1:
                    df_i = pd.DataFrame(ps_i, columns=["ID","Animal","Peso","Data"])
                    df_i["Data"] = pd.to_datetime(df_i["Data"])
                    df_i = df_i.sort_values("Data")
                    d_i  = (df_i["Data"].iloc[-1]-df_i["Data"].iloc[0]).days
                    if d_i > 0:
                        g_i = (df_i["Peso"].iloc[-1]-df_i["Peso"].iloc[0])/d_i
                        if 0 <= g_i <= 2: gmds_i.append(g_i)
            inc_i  = (len(set(o[1] for o in ocs_i))/tot_i*100) if ocs_i else 0
            gmd_i  = sum(gmds_i)/len(gmds_i) if gmds_i else 0
            if inc_i > 20 and gmd_i < 0.5:
                st.error(f"🔴 {nom_i}: incidência {inc_i:.1f}% + GMD baixo -- atenção urgente")
            elif custo_i > 1000:
                st.warning(f"🟡 {nom_i}: custo sanitário elevado R$ {custo_i:.2f}")
            elif len(ocs_i) >= 5:
                st.warning(f"🟠 {nom_i}: {len(ocs_i)} ocorrências -- monitorar surto")
            else:
                st.success(f"🟢 {nom_i}: controlado (inc {inc_i:.1f}%, GMD {gmd_i:.2f})")
    else:
        st.info("Nenhuma ocorrência encontrada com os filtros selecionados.")


# ===========================================================================
# DASHBOARD EXECUTIVO
# ===========================================================================
elif menu == "Dashboard Executivo":
    _page_header("📊", "Dashboard Executivo", "KPIs consolidados do lote")

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
    st.metric("🐄 Animais no lote", numero_animais)
    st.metric("⚖️ Ganho total", f"{ganho_total:.2f} kg")
    st.metric("💸 Custo sanitário", f"R$ {custo_sanitario:.2f}")

# ===========================================================================
# SEPARADOR DE MENU (item não clicável)
# ===========================================================================
elif menu == "── Novos Módulos ──":
    pass  # separador obsoleto

# ===========================================================================
# CALENDÁRIO SANITÁRIO
# ===========================================================================
elif menu == "Calendário Sanitário":
    _page_header("💉", "Calendário Sanitário", "Agenda de vacinas e medicações")

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
                    st.success(f"✅ {row['Vacina']} -- Lote {row['Lote ID']} -- Realizado em {row['Realizado']}")
                elif atrasado:
                    st.error(f"🔴 ATRASADA: {row['Vacina']} -- Previsto {row['Previsto']}")
                else:
                    st.warning(f"🟡 Pendente: {row['Vacina']} -- Previsto {row['Previsto']}")

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
            opcoes_v = {f"{r['Vacina']} -- {r['Lote']} (prev. {r['Previsto']})": r["ID"]
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
    _page_header("💊", "Estoque de Medicamentos", "Controle de estoque, validade e uso")

    tab1, tab2, tab3 = st.tabs(["📦 Estoque Atual", "➕ Cadastrar", "💉 Registrar Uso"])

    with tab1:
        meds = listar_medicamentos()
        criticos = listar_medicamentos_criticos()

        if criticos:
            st.error(f"🚨 {len(criticos)} medicamento(s) em alerta de estoque ou validade:")
            for m in criticos:
                motivo = "estoque baixo" if m[3] <= m[4] else f"vence em {m[5]}"
                st.warning(f"⚠️ {m[1]} -- {m[3]:.1f} {m[2]} ({motivo})")

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
                anim_sel = st.selectbox("Animal", list(dict_a.keys()) if dict_a else ["--"])
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
    _page_header("🐄", "Controle Reprodutivo", "IATF, diagnóstico, prenhez e partos")

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
                        "Data Cio": r[2] or "--",
                        "Diagnóstico": r[4] or "--",
                        "Resultado": r[5],
                        "Parto Previsto": r[6] or "--",
                        "Parto Real": r[7] or "--",
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
                anim_s  = st.selectbox("Animal", list(dict_a.keys()) if dict_a else ["--"])
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
    _page_header("🌿", "Mapa de Piquetes", "Alocação de lotes e histórico de ocupação")

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
    _page_header("📄", "Exportar Relatórios", "PDF e Excel do lote, sanitário e estoque")

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
        st.subheader("📊 Excel -- Dados do Lote")
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
        st.subheader("📋 PDF -- Relatório do Lote")
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
            pdf = gerar_pdf_relatorio(f"Relatório -- {nome_lote}", secoes)
            st.download_button(
                label="⬇️ Baixar PDF",
                data=pdf,
                file_name=f"relatorio_{nome_lote.replace(' ','_')}.pdf",
                mime="application/pdf",
                key="dl_pdf_relatorio",
            )

    st.divider()
    st.subheader("💊 Excel -- Calendário Sanitário e Medicamentos")
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
    _page_header("⚙️", "Administração", "Usuários, planos e configurações")

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
    _page_header("🥩", "Previsão de Abate", "Data estimada e receita projetada por GMD")

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
                st.warning(f"🟡 {r['Animal']}: {r['Dias Restantes']} dias -- prepare o abate")
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
    _page_header("📋", "Prontuário do Animal", "Histórico completo: peso, saúde e reprodução")

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
                    st.caption("⚠️ Confiança baixa -- registre mais pesagens para melhorar a previsão.")

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
    _page_header("📧", "Notificações", "Alertas por e-mail e gestão de planos")

    if not email_configurado():
        st.warning("⚠️ E-mail não configurado.")
        st.markdown('''
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
        ''')
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

# ===========================================================================
# SEPARADOR AVANÇADO
# ===========================================================================
elif menu == "── Avançado ──":
    st.info("Selecione um módulo avançado no menu lateral.")

# ===========================================================================
# HOME DASHBOARD
# ===========================================================================
elif menu == "Home Dashboard":
    # Saudação dinâmica
    hora = datetime.now().hour
    saudacao = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    st.markdown(f"## {saudacao}, **{u['nome']}** 👋")
    st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.divider()

    lotes         = listar_lotes()
    animais_todos = listar_animais()
    pendentes     = listar_vacinas_pendentes()
    criticos      = listar_medicamentos_criticos()
    partos        = listar_partos_previstos()

    # --- KPIs ---
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📦 Lotes",            len(lotes))
    k2.metric("🐄 Animais ativos",   len(animais_todos))
    k3.metric("💉 Vacinas pendentes",len(pendentes),
              delta="⚠️" if pendentes else None,
              delta_color="inverse" if pendentes else "normal")
    k4.metric("💊 Meds. críticos",   len(criticos),
              delta="⚠️" if criticos else None,
              delta_color="inverse" if criticos else "normal")
    k5.metric("🐄 Partos em 30d",    len(partos))

    st.divider()

    # --- Cotação + Alertas ---
    col_cot, col_alert = st.columns([1, 2])

    with col_cot:
        st.subheader("💰 Cotação do dia")
        import database as _db_cot
        cot = cotacao_com_cache(_db_cot)
        if cot["sucesso"]:
            st.success(f"**R$ {cot['preco']:.2f} /@**")
            st.caption(f"{cot['data']} · {cot['fonte']}")
        else:
            st.warning("Cotação indisponível")
            with st.form("form_cot_home"):
                pr_h = st.number_input("R$/@", 0.0, 1000.0, 195.0,
                                        label_visibility="collapsed")
                if st.form_submit_button("💾 Salvar cotação"):
                    salvar_cotacao(str(date.today()), pr_h, "manual")
                    st.rerun()

    with col_alert:
        st.subheader("🚨 Alertas")
        if not pendentes and not criticos and not partos:
            st.success("✅ Tudo em ordem! Nenhum alerta crítico hoje.")
        if pendentes:
            with st.expander(f"💉 {len(pendentes)} vacina(s) pendente(s)", expanded=True):
                for v in pendentes[:5]:
                    st.caption(f"• **{v[3]}** -- Lote: {v[2]} -- Previsto: {v[4]}")
        if criticos:
            with st.expander(f"💊 {len(criticos)} medicamento(s) em alerta", expanded=True):
                for m in criticos[:5]:
                    motivo = "estoque baixo" if m[3] <= m[4] else f"vence {m[5]}"
                    st.caption(f"• **{m[1]}** -- {m[3]:.0f} {m[2]} ({motivo})")
        if partos:
            with st.expander(f"🐄 {len(partos)} parto(s) previsto(s)"):
                for p in partos[:5]:
                    st.caption(f"• **{p[1]}** -- Lote: {p[2]} -- {p[3]}")

    st.divider()

    # --- Cards de lotes ---
    st.subheader("📦 Seus lotes")
    if not lotes:
        st.info("Nenhum lote cadastrado. Vá em **Cadastros → Cadastrar Lote**.")
    else:
        ncols = min(3, len(lotes))
        cols_lote = st.columns(ncols)
        for i, l in enumerate(lotes[:6]):
            rs = resumo_lote(l[0])
            ico = "🟢" if rs["ativos"] > 0 else "⚫"
            tags = []
            if rs["mortos"]:           tags.append(f"💀 {rs['mortos']}")
            if rs["vacinas_pendentes"]:tags.append(f"💉 {rs['vacinas_pendentes']}")
            if rs["ocorrencias"]:      tags.append(f"🚨 {rs['ocorrencias']}")
            tag_str = " · ".join(tags) if tags else "✅ sem alertas"
            with cols_lote[i % ncols]:
                linha1 = f"**{ico} {l[1]}**"
                linha2 = f"🐄 {rs['ativos']} ativos · 📅 {l[3]}"
                linha3 = f"_{tag_str}_"
                st.markdown(linha1 + "  \n" + linha2 + "  \n" + linha3)
                st.divider()
        if len(lotes) > 6:
            st.caption(f"... e mais {len(lotes)-6} lote(s).")

    st.divider()

    # --- Ações rápidas ---
    st.subheader("⚡ Ações rápidas")
    qa1, qa2, qa3, qa4 = st.columns(4)
    if qa1.button("➕ Novo Lote",         use_container_width=True):
        st.session_state["_nav"] = "Cadastrar Lote"; st.rerun()
    if qa2.button("⚖️ Registrar Pesagem", use_container_width=True):
        st.session_state["_nav"] = "Registrar Pesagem"; st.rerun()
    if qa3.button("🚨 Nova Ocorrência",   use_container_width=True):
        st.session_state["_nav"] = "Ocorrências Adversas"; st.rerun()
    if qa4.button("📄 Exportar Relatório",use_container_width=True):
        st.session_state["_nav"] = "Exportar Relatórios"; st.rerun()

# ===========================================================================
# BUSCA DE ANIMAL
# ===========================================================================
elif menu == "Busca de Animal":
    _page_header("🔍", "Buscar Animal", "Encontre qualquer animal pelo brinco ou identificação")
    termo = st.text_input("Digite a identificação (brinco, tag, nome...)",
                           placeholder="Ex: BOI-001")
    if termo:
        animais_todos = listar_animais()
        encontrados = [a for a in animais_todos
                       if termo.lower() in a[1].lower()]
        if encontrados:
            st.success(f"{len(encontrados)} animal(is) encontrado(s)")
            for a in encontrados:
                lote = obter_lote(a[3])
                nome_lote = lote[1] if lote else "--"
                with st.expander(f"🐄 {a[1]} -- Lote: {nome_lote}"):
                    det = obter_animal(a[0])
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**ID:** {a[0]}")
                        st.write(f"**Idade:** {a[2]} meses")
                        st.write(f"**Raça:** {det[5] if det else '--'}")
                        st.write(f"**Peso alvo:** {det[7] if det else 0} kg")
                    with col2:
                        ocs = listar_ocorrencias(a[0])
                        ps  = listar_pesagens(a[0])
                        st.write(f"**Pesagens:** {len(ps)}")
                        st.write(f"**Ocorrências:** {len(ocs)}")
                        sc = calcular_score_saude(a[0])
                        st.write(f"**Score saúde:** {sc['score']}/100 ({sc['classificacao']})")
                        car = verificar_carencia(a[0])
                        if car["em_carencia"]:
                            st.warning(f"⚠️ Em carência até {car['liberado_em']}")
                    if st.button(f"Abrir Prontuário", key=f"btn_{a[0]}"):
                        st.session_state["animal_selecionado"] = a[0]
                        st.info("Vá em Prontuário do Animal para ver o histórico completo.")
        else:
            st.warning(f"Nenhum animal encontrado para '{termo}'")

# ===========================================================================
# MORTALIDADE
# ===========================================================================
elif menu == "Mortalidade":
    _page_header("💀", "Mortalidade", "Baixa de animais com causa e custo da perda")
    tab1, tab2 = st.tabs(["📋 Histórico", "➕ Registrar Morte"])

    with tab1:
        lotes = listar_lotes()
        if lotes:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            filtro = st.selectbox("Filtrar por lote", ["Todos"]+list(dict_l.keys()))
            lote_id_f = dict_l.get(filtro) if filtro != "Todos" else None
            morts = listar_mortalidade(lote_id_f)
            if morts:
                df_m = pd.DataFrame(morts, columns=["ID","Animal ID","Animal",
                                                     "Data","Causa","Descrição","Custo Perda"])
                st.dataframe(df_m, use_container_width=True)
                col1,col2 = st.columns(2)
                col1.metric("💀 Total de mortes", len(morts))
                col2.metric("💸 Custo total perdas",
                            f"R$ {sum(m[6] for m in morts if m[6]):.2f}")
                if lote_id_f:
                    tm = taxa_mortalidade_lote(lote_id_f)
                    st.metric("📊 Taxa de mortalidade", f"{tm['taxa']:.1f}%")
            else:
                st.success("✅ Nenhuma morte registrada.")

    with tab2:
        lotes = listar_lotes()
        if not lotes:
            st.warning("Cadastre um lote primeiro.")
        else:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            # selectbox FORA do form para atualizar lista de animais dinamicamente
            lote_sel_m = st.selectbox("Lote", list(dict_l.keys()),
                                       key="morte_lote_sel")
            lote_id_m  = dict_l[lote_sel_m]
            animais_m  = listar_animais_por_lote(lote_id_m)

            if not animais_m:
                st.warning("Nenhum animal neste lote.")
            else:
                dict_a_m = {f"{a[1]} (ID {a[0]})": a[0] for a in animais_m}
                with st.form("form_morte"):
                    anim_sel   = st.selectbox("Animal", list(dict_a_m.keys()))
                    data_morte = st.date_input("Data")
                    causa      = st.selectbox("Causa",
                                  ["Doença","Acidente","Desaparecimento",
                                   "Predador","Outras"])
                    desc_m     = st.text_area("Descrição")
                    custo_p    = st.number_input("Custo da perda (R$)", 0.0)
                    if st.form_submit_button("Registrar Morte"):
                        registrar_morte(dict_a_m[anim_sel], str(data_morte),
                                        causa, desc_m, custo_p)
                        registrar_auditoria(u["id"], "morte_animal",
                                            "animais", dict_a_m[anim_sel],
                                            f"{anim_sel} -- {causa}")
                        st.success("Morte registrada e animal baixado do lote.")
                        st.rerun()

# ===========================================================================
# IMPORTAR DADOS
# ===========================================================================
elif menu == "Importar Dados":
    _page_header("📥", "Importar Dados", "Importe pesagens e animais via planilha CSV")

    lotes = listar_lotes()

    # --- Seleção ou criação de lote ---
    st.subheader("📦 Lote de destino")
    opcao_lote = st.radio("O que deseja fazer?",
                          ["Usar lote existente", "Criar novo lote agora"],
                          horizontal=True, key="import_opcao_lote")

    lote_id = None

    if opcao_lote == "Criar novo lote agora":
        with st.form("form_novo_lote_import"):
            col1, col2 = st.columns(2)
            with col1:
                nome_nl    = st.text_input("Nome do lote *")
                qtd_comp   = st.number_input("Qtd comprada", 0, step=1)
                qtd_rec    = st.number_input("Qtd recebida", 0, step=1)
            with col2:
                data_nl    = st.date_input("Data de entrada")
                transp_nl  = st.text_input("Transportadora")
                desc_nl    = st.text_area("Descrição")
            if st.form_submit_button("✅ Criar lote e continuar"):
                if nome_nl:
                    lote_id = adicionar_lote(nome_nl, desc_nl, str(data_nl),
                                             qtd_comp, qtd_rec, transp_nl)
                    registrar_auditoria(u["id"], "criar_lote", "lotes",
                                        lote_id, nome_nl)
                    st.success(f"Lote '{nome_nl}' criado! Agora faça o upload do CSV abaixo.")
                    st.rerun()
                else:
                    st.error("Informe o nome do lote.")
        # Após criar, pega o lote mais recente
        lotes = listar_lotes()
        if lotes:
            lote_id = lotes[0][0]
            st.info(f"Lote selecionado: **{lotes[0][1]}**")
    else:
        if not lotes:
            st.warning("Nenhum lote cadastrado. Selecione 'Criar novo lote agora'.")
            st.stop()
        dict_l   = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
        lote_sel = st.selectbox("Selecione o lote", list(dict_l.keys()),
                                 key="import_lote_sel")
        lote_id  = dict_l[lote_sel]

    if not lote_id:
        st.stop()

    st.divider()
    tab1, tab2 = st.tabs(["⚖️ Importar Pesagens", "🐄 Importar Animais"])

    with tab1:
        st.markdown('''
        **Formato esperado do CSV:**
        ```
        identificacao,peso,data
        BOI-001,310.5,2024-01-15
        BOI-002,295.0,2024-01-15
        ```
        ''')
        arq = st.file_uploader("Selecione o arquivo CSV", type=["csv"], key="csv_pesagens")
        if arq:
            import csv as csv_mod, io as io_mod
            texto = arq.read().decode("utf-8-sig", errors="ignore")
            reader = csv_mod.DictReader(io_mod.StringIO(texto))
            linhas = list(reader)
            st.info(f"{len(linhas)} linha(s) encontradas no arquivo.")
            if st.button("Importar pesagens"):
                res = importar_pesagens_csv(linhas, lote_id)
                registrar_auditoria(u["id"], "import_pesagens", "pesagens",
                                    lote_id, f"{res['importados']} importadas")
                st.success(f"✅ {res['importados']} pesagens importadas | "
                           f"🆕 {res['animais_criados']} animais criados | "
                           f"❌ {res['erros']} erros")
                for msg in res["mensagens"]:
                    st.warning(msg)

    with tab2:
        st.markdown('''
        **Formato esperado do CSV:**
        ```
        identificacao,idade,raca,sexo,peso_entrada,peso_alvo
        BOI-001,24,Nelore,macho,280,450
        ```
        Apenas `identificacao` é obrigatório.
        ''')
        arq2 = st.file_uploader("Selecione o arquivo CSV", type=["csv"], key="csv_animais")
        if arq2:
            import csv as csv_mod, io as io_mod
            texto2 = arq2.read().decode("utf-8-sig", errors="ignore")
            reader2 = csv_mod.DictReader(io_mod.StringIO(texto2))
            linhas2 = list(reader2)
            st.info(f"{len(linhas2)} linha(s) encontradas.")
            if st.button("Importar animais"):
                res2 = importar_animais_csv(linhas2, lote_id)
                registrar_auditoria(u["id"], "import_animais", "animais",
                                    lote_id, f"{res2['importados']} importados")
                st.success(f"✅ {res2['importados']} animais importados | "
                           f"❌ {res2['erros']} erros")
                for msg in res2["mensagens"]:
                    st.warning(msg)

# ===========================================================================
# COTAÇÃO CEPEA
# ===========================================================================
elif menu == "Cotação Cepea":
    _page_header("📈", "Cotação Cepea", "Preço do boi gordo -- ESALQ/Cepea")

    col1, col2 = st.columns([2,1])
    with col1:
        if st.button("🔄 Buscar cotação atual"):
            from cepea import buscar_cotacao_cepea
            with st.spinner("Buscando no Cepea..."):
                res = buscar_cotacao_cepea()
            if res["sucesso"]:
                salvar_cotacao(res["data"], res["preco"], res["fonte"])
                st.success(f"✅ R$ {res['preco']:.2f}/@ -- {res['data']}")
            else:
                st.warning(f"Cepea indisponível: {res['msg']}")

    with col2:
        with st.form("form_cotacao_manual"):
            dt_cot = st.date_input("Data")
            pr_cot = st.number_input("Preço (R$/@)", 0.0, 1000.0, 195.0)
            if st.form_submit_button("Salvar manual"):
                salvar_cotacao(str(dt_cot), pr_cot, "manual")
                st.success("Salvo!"); st.rerun()

    cotacoes = listar_cotacoes(0)  # todas
    if cotacoes:
        ult = cotacoes[-1]
        st.metric("💰 Última cotação", f"R$ {ult[2]:.2f}/@",
                  delta=f"{ult[1]} ({ult[3]})")

        hist = historico_grafico(cotacoes[-60:])  # últimas 60
        if hist["datas"]:
            df_cot = pd.DataFrame({"Data": hist["datas"], "Preço R$/@": hist["precos"]})
            df_cot = df_cot.set_index("Data")
            st.subheader("📊 Histórico de cotações")
            st.line_chart(df_cot)
            st.dataframe(df_cot.tail(10), use_container_width=True)
    else:
        st.info("Nenhuma cotação registrada. Clique em 'Buscar cotação atual' ou insira manualmente.")

# ===========================================================================
# SCORE DE SAÚDE
# ===========================================================================
elif menu == "Score de Saúde":
    _page_header("💯", "Score de Saúde", "Ranking 0-100 por animal (GMD + ocorrências + reprodução)")

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

    scores = []
    for a in animais:
        sc = calcular_score_saude(a[0])
        car = verificar_carencia(a[0])
        scores.append({
            "Animal":       a[1],
            "Score":        sc["score"],
            "Classificação":sc["classificacao"],
            "GMD":          sc["detalhes"]["gmd"],
            "Ocorrências":  sc["detalhes"]["n_ocorrencias"],
            "Pts GMD":      sc["detalhes"]["pts_gmd"],
            "Pts Ocorr.":   sc["detalhes"]["pts_ocorrencias"],
            "Pts Reprod.":  sc["detalhes"]["pts_reproducao"],
            "Em Carência":  "⚠️ Sim" if car["em_carencia"] else "✅ Não",
        })

    df_sc = pd.DataFrame(scores).sort_values("Score", ascending=False)
    st.dataframe(df_sc, use_container_width=True)

    # Métricas resumo
    col1,col2,col3,col4 = st.columns(4)
    col1.metric("🏆 Score médio", f"{df_sc['Score'].mean():.1f}")
    col2.metric("🥇 Melhor animal", df_sc.iloc[0]["Animal"])
    col3.metric("⚠️ Críticos (< 40)", len(df_sc[df_sc["Score"]<40]))
    col4.metric("💊 Em carência", len(df_sc[df_sc["Em Carência"]=="⚠️ Sim"]))

    # Gráfico
    st.bar_chart(df_sc.set_index("Animal")["Score"])

    # Alertas individuais
    st.subheader("🚨 Alertas")
    for _, row in df_sc.iterrows():
        if row["Score"] < 40:
            st.error(f"🔴 {row['Animal']}: Score {row['Score']} -- CRÍTICO")
        elif row["Score"] < 60:
            st.warning(f"🟡 {row['Animal']}: Score {row['Score']} -- Regular")
        if row["Em Carência"] == "⚠️ Sim":
            st.warning(f"💊 {row['Animal']}: em período de carência -- verificar liberação para abate")

# ===========================================================================
# MARGEM REAL DO LOTE
# ===========================================================================
elif menu == "Margem Real do Lote":
    _page_header("💰", "Margem Real do Lote", "Resultado financeiro: compra × venda × custos")

    lotes = listar_lotes()
    if not lotes:
        st.warning("Nenhum lote cadastrado.")
        st.stop()

    dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    lote_sel = st.selectbox("Selecione o lote", list(dict_l.keys()))
    lote_id  = dict_l[lote_sel]

    tab1, tab2 = st.tabs(["📊 Resultado", "➕ Registrar Venda"])

    with tab1:
        mg = calcular_margem_lote(lote_id)
        if mg:
            if not mg["venda_registrada"]:
                st.info("💡 Nenhuma venda registrada ainda. Registre na aba ao lado para ver a margem real.")

            col1,col2,col3 = st.columns(3)
            col1.metric("🛒 Custo de compra", f"R$ {mg['custo_compra']:,.2f}")
            col2.metric("📈 Receita real", f"R$ {mg['receita_real']:,.2f}")
            col3.metric("💊 Custo sanitário", f"R$ {mg['custo_sanitario']:,.2f}")

            cor = "normal" if mg["margem"] >= 0 else "inverse"
            st.metric("💰 Margem líquida",
                      f"R$ {mg['margem']:,.2f}",
                      delta=f"{mg['margem_pct']:.1f}%",
                      delta_color=cor)

            if mg["venda_registrada"]:
                st.success(f"🏭 Frigorífico: {mg['frigorific']} -- Venda: {mg['data_venda']}")

            # Histórico de vendas
            vendas = listar_vendas_lote(lote_id)
            if vendas:
                st.subheader("📋 Histórico de vendas")
                df_v = pd.DataFrame(vendas, columns=["ID","Lote","Data","R$/kg",
                                                      "Peso Total kg","Frigorífico","Obs"])
                st.dataframe(df_v, use_container_width=True)

    with tab2:
        with st.form("form_venda"):
            dt_venda = st.date_input("Data da venda")
            pr_kg    = st.number_input("Preço de venda (R$/kg)", 0.0, 100.0, 22.0)
            peso_tot = st.number_input("Peso total vendido (kg)", 0.0)
            frig     = st.text_input("Frigorífico")
            obs_v    = st.text_area("Observação")
            if st.form_submit_button("Registrar Venda"):
                if peso_tot > 0:
                    registrar_venda_lote(lote_id, str(dt_venda),
                                         pr_kg, peso_tot, frig, obs_v)
                    registrar_auditoria(u["id"], "venda_lote", "vendas_lote",
                                        lote_id, f"R${pr_kg}/kg {peso_tot}kg {frig}")
                    st.success("Venda registrada!")
                    st.rerun()
                else:
                    st.error("Informe o peso total.")

# ===========================================================================
# RASTREABILIDADE GTA
# ===========================================================================
elif menu == "Rastreabilidade GTA":
    _page_header("📋", "Rastreabilidade GTA", "Guia de Trânsito Animal e certificação SISBOV")

    tab1, tab2, tab3 = st.tabs(["📄 GTAs", "➕ Emitir GTA", "🔖 SISBOV"])

    with tab1:
        gtas = listar_gta()
        if gtas:
            df_g = pd.DataFrame(gtas, columns=["ID","Lote ID","Lote","Nº GTA",
                                                "Emissão","Origem","Destino",
                                                "Qtd","Finalidade","Obs"])
            st.dataframe(df_g, use_container_width=True)
            st.metric("📄 Total de GTAs", len(gtas))
        else:
            st.info("Nenhuma GTA registrada.")

    with tab2:
        lotes = listar_lotes()
        if not lotes:
            st.warning("Cadastre um lote primeiro.")
        else:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            with st.form("form_gta"):
                lote_g   = st.selectbox("Lote", list(dict_l.keys()))
                num_gta  = st.text_input("Número da GTA")
                dt_emis  = st.date_input("Data de emissão")
                origem   = st.text_input("Município/Fazenda de origem")
                destino  = st.text_input("Município/Frigorífico de destino")
                qtd_g    = st.number_input("Quantidade de animais", 1, step=1)
                finalid  = st.selectbox("Finalidade",
                             ["Abate","Recria","Engorda","Reprodução","Exposição"])
                obs_g    = st.text_area("Observação")
                if st.form_submit_button("Registrar GTA"):
                    if num_gta and origem and destino:
                        registrar_gta(dict_l[lote_g], num_gta, str(dt_emis),
                                      origem, destino, int(qtd_g), finalid, obs_g)
                        registrar_auditoria(u["id"],"gta","gta",
                                            dict_l[lote_g], num_gta)
                        st.success("GTA registrada!"); st.rerun()
                    else:
                        st.error("Preencha número, origem e destino.")

    with tab3:
        lotes = listar_lotes()
        if lotes:
            dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
            lote_s  = st.selectbox("Lote", list(dict_l.keys()), key="sisbov_lote")
            animais = listar_animais_por_lote(dict_l[lote_s])
            if animais:
                dict_a = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
                anim_s = st.selectbox("Animal", list(dict_a.keys()))
                aid_s  = dict_a[anim_s]
                sb = obter_sisbov(aid_s)
                if sb:
                    st.success(f"✅ SISBOV cadastrado: **{sb[2]}** -- {sb[3]}")
                else:
                    st.info("Animal sem SISBOV cadastrado.")
                with st.form("form_sisbov"):
                    num_sb = st.text_input("Número SISBOV (15 dígitos)")
                    dt_sb  = st.date_input("Data de certificação")
                    if st.form_submit_button("Cadastrar SISBOV"):
                        if len(num_sb) == 15:
                            registrar_sisbov(aid_s, num_sb, str(dt_sb))
                            st.success("SISBOV cadastrado!"); st.rerun()
                        else:
                            st.error("SISBOV deve ter exatamente 15 dígitos.")

# ===========================================================================
# COMPARATIVO DE LOTES
# ===========================================================================
elif menu == "Comparativo de Lotes":
    _page_header("🔀", "Comparativo de Lotes", "Side-by-side de GMD, custos e resultados")

    lotes = listar_lotes()
    if len(lotes) < 2:
        st.warning("Cadastre pelo menos 2 lotes para comparar.")
        st.stop()

    dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    selecionados = st.multiselect("Selecione 2 a 4 lotes para comparar",
                                   list(dict_l.keys()),
                                   default=list(dict_l.keys())[:min(2,len(dict_l))])
    if len(selecionados) < 2:
        st.info("Selecione pelo menos 2 lotes.")
        st.stop()

    preco_kg   = st.number_input("Preço do kg (R$)", 0.0, 100.0, 20.0)
    custo_diar = st.number_input("Custo diário/animal (R$)", 0.0, 100.0, 10.0)

    dados = []
    for nome_l in selecionados:
        lid  = dict_l[nome_l]
        anim = listar_animais_por_lote(lid)
        tm   = taxa_mortalidade_lote(lid)
        tp   = taxa_prenhez_lote(lid)

        gmds, ganho_t, dias_t, custo_san = [], 0, 0, 0
        for a in anim:
            ps = listar_pesagens(a[0])
            if len(ps) >= 2:
                df = pd.DataFrame(ps, columns=["id","aid","peso","data"])
                df["data"] = pd.to_datetime(df["data"])
                df = df.sort_values("data")
                dias = (df["data"].iloc[-1]-df["data"].iloc[0]).days
                if dias > 0:
                    g = (df["peso"].iloc[-1]-df["peso"].iloc[0])/dias
                    if 0 < g <= 2: gmds.append(g)
                    ganho_t += df["peso"].iloc[-1]-df["peso"].iloc[0]
                    dias_t  += dias
            for oc in listar_ocorrencias(a[0]):
                if oc[6]: custo_san += oc[6]

        gmd_m = round(sum(gmds)/len(gmds),3) if gmds else 0
        receita = ganho_t * preco_kg
        custo_op = custo_diar * len(anim) * (dias_t/max(len(anim),1))
        lucro = receita - custo_op - custo_san

        dados.append({
            "Lote":           nome_l.split(" (ID")[0],
            "Animais":        len(anim),
            "GMD médio":      gmd_m,
            "Incidência %":   round(len([a for a in anim if listar_ocorrencias(a[0])])/max(len(anim),1)*100,1),
            "Mortalidade %":  tm["taxa"],
            "Prenhez %":      round(tp["taxa"],1),
            "Receita R$":     round(receita,2),
            "Custo San. R$":  round(custo_san,2),
            "Lucro R$":       round(lucro,2),
        })

    df_comp = pd.DataFrame(dados).set_index("Lote")
    st.dataframe(df_comp, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 GMD médio por lote")
        st.bar_chart(df_comp["GMD médio"])
    with col2:
        st.subheader("💰 Lucro estimado por lote")
        st.bar_chart(df_comp["Lucro R$"])

    melhor = df_comp["GMD médio"].idxmax()
    pior   = df_comp["GMD médio"].idxmin()
    st.success(f"🥇 Melhor GMD: **{melhor}** ({df_comp.loc[melhor,'GMD médio']:.3f} kg/dia)")
    st.warning(f"⚠️ Pior GMD: **{pior}** ({df_comp.loc[pior,'GMD médio']:.3f} kg/dia)")

# ===========================================================================
# GMD AO LONGO DO TEMPO
# ===========================================================================
elif menu == "GMD ao Longo do Tempo":
    _page_header("📉", "GMD ao Longo do Tempo", "Evolução temporal do ganho de peso do lote")

    lotes = listar_lotes()
    if not lotes:
        st.warning("Nenhum lote cadastrado.")
        st.stop()

    dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    lote_sel = st.selectbox("Selecione o lote", list(dict_l.keys()))
    lote_id  = dict_l[lote_sel]

    janela = st.slider("Janela de cálculo (dias)", 7, 60, 14)

    pontos = calcular_gmd_temporal(lote_id, janela_dias=janela)
    if pontos:
        df_gmd = pd.DataFrame(pontos, columns=["Data","GMD médio (kg/dia)"])
        df_gmd = df_gmd.set_index("Data")
        st.line_chart(df_gmd)
        st.dataframe(df_gmd, use_container_width=True)

        ultimo_gmd = pontos[-1][1]
        primeiro_gmd = pontos[0][1]
        delta = ultimo_gmd - primeiro_gmd
        st.metric("📈 GMD atual", f"{ultimo_gmd:.3f} kg/dia",
                  delta=f"{delta:+.3f} vs início")

        if delta < -0.1:
            st.error("🔴 GMD em queda -- revisar nutrição e saúde do lote")
        elif delta > 0.1:
            st.success("✅ GMD em melhora -- manejo eficaz")
        else:
            st.info("📊 GMD estável")
    else:
        st.info("Dados insuficientes. Registre pesagens em datas diferentes para visualizar a evolução.")

# ===========================================================================
# BACKUP DO SISTEMA
# ===========================================================================
elif menu == "Backup do Sistema":
    _page_header("💾", "Backup do Sistema", "Download e envio automático dos seus dados")

    import database as _db_mod
    db_path = _db_mod.DB_PATH

    st.info(f"Banco de dados: `{db_path}`")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📦 Download ZIP (CSVs)")
        st.write("Exporta todas as tabelas em formato CSV dentro de um arquivo ZIP.")
        # Gera o backup direto -- sem step intermediário de button
        if not _BACKUP_OK:
            st.error("backup.py não encontrado no repositório.")
        else:
            with st.spinner("Preparando backup ZIP..."):
                dados_zip = gerar_backup_zip(db_path)
            nome_zip = nome_arquivo_backup("zip")
            st.download_button(
                "⬇️ Baixar Backup ZIP",
                dados_zip,
                nome_zip,
                "application/zip",
                key="dl_zip",
            )
            registrar_auditoria(u["id"], "backup_zip", "sistema", None, nome_zip)

    with col2:
        st.subheader("🗄️ Download SQLite")
        st.write("Cópia fiel do banco -- pode ser restaurada diretamente.")
        if not _BACKUP_OK:
            st.error("backup.py não encontrado no repositório.")
        else:
            with st.spinner("Preparando backup SQLite..."):
                dados_db = gerar_backup_sqlite(db_path)
            nome_db = nome_arquivo_backup("db")
            st.download_button(
                "⬇️ Baixar Backup SQLite",
                dados_db,
                nome_db,
                "application/octet-stream",
                key="dl_db",
            )
            registrar_auditoria(u["id"], "backup_sqlite", "sistema", None, nome_db)

    st.divider()
    st.subheader("📧 Enviar backup por e-mail")
    if not email_configurado():
        st.warning("Configure o SMTP em `.streamlit/secrets.toml` para envio por e-mail.")
    else:
        email_dest = st.text_input("E-mail de destino", value=u["email"])
        if st.button("Enviar backup ZIP por e-mail"):
            from backup import enviar_backup_email
            import notifications as _notif
            ok, msg, _, _ = enviar_backup_email(db_path, _notif, email_dest, u["nome"])
            st.success(msg) if ok else st.warning(msg)

# ===========================================================================
# LOG DE AUDITORIA
# ===========================================================================
elif menu == "Log de Auditoria":
    _page_header("📜", "Log de Auditoria", "Histórico completo de ações por usuário")

    if u["perfil"] != "admin":
        st.warning("Acesso restrito a administradores.")
        st.stop()

    col1, col2 = st.columns(2)
    limite = col1.slider("Últimos registros", 10, 500, 100)
    usuario_filtro = col2.selectbox("Filtrar por usuário",
                                     ["Todos"] + [f"{x[1]} (ID {x[0]})"
                                                  for x in listar_usuarios()])
    uid_f = None
    if usuario_filtro != "Todos":
        uid_f = int(usuario_filtro.split("ID ")[1].rstrip(")"))

    logs = listar_auditoria(limite, uid_f)
    if logs:
        df_log = pd.DataFrame(logs, columns=["ID","Usuário","Ação",
                                              "Tabela","Registro ID",
                                              "Detalhe","Data/Hora"])
        st.dataframe(df_log, use_container_width=True)
        st.metric("📋 Total de registros", len(logs))
    else:
        st.info("Nenhum registro de auditoria encontrado.")
