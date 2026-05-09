# app.py – Sistema de Gestao Pecuaria

# Execute: streamlit run app.py

import os as _os

# Restaurar database.py se necessario (protege contra corrupcao de upload)

if not _os.path.exists(“database.py”):
exec(open(“setup_db.py”).read())

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

from database import (
inicializar_banco,
adicionar_lote, listar_lotes, obter_lote,
adicionar_animal, listar_animais, listar_animais_por_lote,
contar_animais_no_lote, atualizar_animal_detalhes, obter_animal,
adicionar_pesagem, listar_pesagens,
adicionar_ocorrencia, listar_ocorrencias,
criar_usuario, autenticar_usuario, listar_usuarios,
usuario_existe, alterar_senha,
adicionar_fazenda, listar_fazendas,
adicionar_vacina_agenda, registrar_vacina_realizada,
listar_vacinas_agenda, listar_vacinas_pendentes,
adicionar_medicamento, listar_medicamentos,
registrar_uso_medicamento, listar_medicamentos_criticos,
adicionar_reproducao, atualizar_reproducao, listar_reproducao,
listar_partos_previstos, taxa_prenhez_lote,
adicionar_piquete, listar_piquetes,
alocar_lote_piquete, liberar_piquete, historico_piquete,
ativar_trial, obter_status_plano, converter_para_pago,
listar_usuarios_trial_expirando,
registrar_morte, listar_mortalidade, taxa_mortalidade_lote,
registrar_auditoria, listar_auditoria,
registrar_gta, listar_gta, registrar_sisbov, obter_sisbov,
verificar_carencia, calcular_score_saude,
registrar_venda_lote, calcular_margem_lote, listar_vendas_lote,
salvar_cotacao, listar_cotacoes, obter_ultima_cotacao,
calcular_gmd_temporal, calcular_previsao_abate,
importar_pesagens_csv, importar_animais_csv,
atualizar_qtd_lote, resumo_lote, sincronizar_todos_lotes,
atualizar_lote, excluir_lote,
atualizar_animal, excluir_animal,
atualizar_pesagem, excluir_pesagem,
atualizar_ocorrencia, excluir_ocorrencia,
listar_tratamentos_vencidos, listar_ocorrencias_em_tratamento,
listar_pesagens_lote,
)

try:
from exports import gerar_excel_lote, gerar_excel_sanitario, gerar_pdf_relatorio
_EXP = True
except ImportError:
_EXP = False
def gerar_excel_lote(*a, **k): return b””
def gerar_excel_sanitario(*a, **k): return b””
def gerar_pdf_relatorio(*a, **k): return b””

try:
from notifications import (
email_boas_vindas, email_trial_expirando, email_trial_expirado,
email_vacina_pendente, email_medicamento_critico,
email_parto_previsto, email_abate_previsto, email_configurado,
)
_NOTIF = True
except ImportError:
_NOTIF = False
def email_boas_vindas(*a, **k): return (False, “”)
def email_trial_expirando(*a, **k): return (False, “”)
def email_trial_expirado(*a, **k): return (False, “”)
def email_vacina_pendente(*a, **k): return (False, “”)
def email_medicamento_critico(*a, **k): return (False, “”)
def email_parto_previsto(*a, **k): return (False, “”)
def email_abate_previsto(*a, **k): return (False, “”)
def email_configurado(): return False

try:
from cepea import cotacao_com_cache, historico_grafico
_CEPEA = True
except ImportError:
_CEPEA = False
def cotacao_com_cache(_db): return dict(preco=0.0, data=””, fonte=””, sucesso=False, msg=“cepea.py nao encontrado”)
def historico_grafico(c): return dict(datas=[], precos=[])

try:
from backup import gerar_backup_zip, gerar_backup_sqlite, nome_arquivo_backup
_BACKUP = True
except ImportError:
_BACKUP = False
def gerar_backup_zip(p): return b””
def gerar_backup_sqlite(p): return b””
def nome_arquivo_backup(ext=“zip”): return f”backup.{ext}”

st.set_page_config(
page_title=“Gestao Pecuaria”,
page_icon=”:cow2:”,
layout=“wide”,
initial_sidebar_state=“expanded”,
)

try:
inicializar_banco()
except Exception as _e_init:
st.error(f”Erro ao inicializar banco: {_e_init}”)
st.stop()

# ── helper ──────────────────────────────────────────────────────────────────

def hdr(icone, titulo, sub=””):
st.markdown(f”## {icone} {titulo}”)
if sub: st.caption(sub)
st.divider()

def sel_lote(key=“lote”):
lotes = listar_lotes()
if not lotes:
st.warning(“Nenhum lote cadastrado. Va em Cadastrar Lote primeiro.”)
return None, None
d = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
sel = st.selectbox(“Lote”, list(d.keys()), key=key)
return d[sel], lotes

def sel_animal(lote_id, key=“animal”):
animais = listar_animais_por_lote(lote_id)
if not animais:
st.warning(“Nenhum animal neste lote.”)
return None
d = {f”{a[1]} (ID {a[0]})”: a[0] for a in animais}
sel = st.selectbox(“Animal”, list(d.keys()), key=key)
return d[sel]

# ── autenticacao ─────────────────────────────────────────────────────────────

if “usuario” not in st.session_state:
st.session_state.usuario = None

if st.session_state.usuario is None:
st.title(“Gestao Pecuaria”)
if not usuario_existe():
st.info(“Primeiro acesso: crie sua conta de administrador.”)
with st.form(“form_first”):
nome  = st.text_input(“Nome”)
email = st.text_input(“E-mail”)
senha = st.text_input(“Senha”, type=“password”)
perf  = st.selectbox(“Perfil”, [“admin”,“veterinario”,“fazendeiro”])
if st.form_submit_button(“Criar conta”):
if nome and email and senha:
uid = criar_usuario(nome, email, senha, perf)
ativar_trial(uid)
email_boas_vindas(email, nome)
st.success(“Conta criada! Faca login.”)
st.rerun()
else:
st.error(“Preencha todos os campos.”)
else:
with st.form(“form_login”):
email = st.text_input(“E-mail”)
senha = st.text_input(“Senha”, type=“password”)
if st.form_submit_button(“Entrar”):
u = autenticar_usuario(email, senha)
if u:
st.session_state.usuario = u
st.rerun()
else:
st.error(“E-mail ou senha incorretos.”)
st.stop()

u = st.session_state.usuario

# ── sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
perf_ico = {“admin”:“gear”,“veterinario”:“stethoscope”,“fazendeiro”:“seedling”}.get(u[“perfil”],“person”)
st.markdown(f”**{u[‘nome’]}**”)
st.caption(u[“perfil”].capitalize())
if st.button(“Sair”, use_container_width=True):
st.session_state.usuario = None
st.rerun()

```
sp = obter_status_plano(u["id"])
if sp["plano"] == "trial":
    dr = sp["dias_restantes"]
    if dr <= 3:   st.error(f"Trial: {dr} dia(s) restante(s)!")
    elif dr <= 7: st.warning(f"Trial: {dr} dias restantes")
    else:         st.progress(dr/30, text=f"Trial: {dr}/30 dias")
elif sp["plano"] == "expirado":
    st.error("Trial expirado")
else:
    st.success("Plano ativo")

# Tratamentos vencidos
_trat_venc = listar_tratamentos_vencidos()
if _trat_venc:
    st.sidebar.error(f"{len(_trat_venc)} trat. pendente(s) de resolucao!")

pend  = listar_vacinas_pendentes()
crit  = listar_medicamentos_criticos()
parto = listar_partos_previstos()
alertas = []
if pend:  alertas.append(f"Vacinas: {len(pend)}")
if crit:  alertas.append(f"Meds: {len(crit)}")
if parto: alertas.append(f"Partos: {len(parto)}")
if alertas: st.warning(" | ".join(alertas))

st.divider()
st.caption("MENU")

GRUPOS = {
    "Inicio": [
        ("Inicio",          "Painel geral"),
        ("Buscar Animal",   "Busca por brinco"),
    ],
    "Cadastros": [
        ("Cadastrar Lote",       "Novo lote"),
        ("Cadastrar Animal",     "Novo animal"),
        ("Registrar Pesagem",    "Novo peso"),
        ("Registrar Ocorrencia", "Nova ocorrencia"),
        ("Registrar Morte",      "Baixa de animal"),
        ("Importar CSV",         "Importacao em lote"),
        ("Editar Lote",          "Alterar dados do lote"),
        ("Editar Animal",        "Alterar dados do animal"),
        ("Editar Pesagens",      "Corrigir ou excluir pesagens"),
        ("Gerenciar Ocorrencias","Editar e resolver tratamentos"),
    ],
    "Analise": [
        ("Dashboard Sanitario",  "Incidencias e alertas"),
        ("Analisar por Lote",    "GMD e financeiro"),
        ("Analisar Animal",      "Individual"),
        ("Score de Saude",       "Ranking 0-100"),
        ("GMD Temporal",         "Evolucao no tempo"),
        ("Comparativo Lotes",    "Side by side"),
        ("Painel de Decisao",    "Lucro por lote"),
        ("Dashboard Executivo",  "KPIs do lote"),
        ("Pesquisar Ocorrencias","Filtros avancados"),
    ],
    "Gestao": [
        ("Calendario Sanitario", "Vacinas e alertas"),
        ("Estoque Medicamentos", "Controle de estoque"),
        ("Controle Reprodutivo", "IATF e prenhez"),
        ("Mapa Piquetes",        "Pastagens"),
        ("Previsao Abate",       "Data estimada"),
        ("Prontuario Animal",    "Historico completo"),
        ("Margem Real",          "Compra x Venda"),
        ("Cotacao Cepea",        "Preco boi gordo"),
    ],
    "Rastreabilidade": [
        ("Rastreabilidade GTA",  "GTA e SISBOV"),
    ],
    "Relatorios": [
        ("Exportar Relatorios",  "PDF e Excel"),
        ("Backup",               "Download do banco"),
    ],
    "Sistema": [
        ("Notificacoes",         "E-mail e alertas"),
        ("Log Auditoria",        "Historico de acoes"),
        ("Administracao",        "Usuarios e planos"),
    ],
}

if "menu" not in st.session_state:
    st.session_state.menu = "Inicio"

for grupo, itens in GRUPOS.items():
    st.caption(grupo.upper())
    for nome_item, desc in itens:
        ativo = st.session_state.menu == nome_item
        label = f"**{nome_item}**" if ativo else nome_item
        if st.button(label, key=f"menu_{nome_item}", use_container_width=True, help=desc):
            st.session_state.menu = nome_item
            st.rerun()
    st.write("")
```

menu = st.session_state.menu

# ============================================================

# INICIO

# ============================================================

if menu == “Inicio”:
hora = datetime.now().hour
sau  = “Bom dia” if hora < 12 else “Boa tarde” if hora < 18 else “Boa noite”
st.markdown(f”## {sau}, **{u[‘nome’]}**”)
st.caption(datetime.now().strftime(”%d/%m/%Y %H:%M”))
st.divider()

```
lotes         = listar_lotes()
animais_todos = listar_animais()

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Lotes",          len(lotes))
k2.metric("Animais ativos", len(animais_todos))
k3.metric("Vacinas pend.",  len(pend),  delta="atencao" if pend  else None, delta_color="inverse" if pend  else "normal")
k4.metric("Meds. criticos", len(crit),  delta="atencao" if crit  else None, delta_color="inverse" if crit  else "normal")
k5.metric("Partos 30d",     len(parto))

st.divider()
ca, cb = st.columns([1,2])

with ca:
    st.subheader("Cotacao do dia")
    import database as _dbc
    cot = cotacao_com_cache(_dbc)
    if cot["sucesso"]:
        st.success(f"R$ {cot['preco']:.2f} /@")
        st.caption(f"{cot['data']} - {cot['fonte']}")
    else:
        st.warning("Cotacao indisponivel")
        with st.form("cot_home"):
            pr = st.number_input("R$/@", 0.0, 1000.0, 195.0, label_visibility="collapsed")
            if st.form_submit_button("Salvar"):
                salvar_cotacao(str(date.today()), pr, "manual")
                st.rerun()

with cb:
    st.subheader("Alertas")
    if not pend and not crit and not parto:
        st.success("Tudo em ordem! Nenhum alerta critico.")
    if pend:
        with st.expander(f"Vacinas pendentes ({len(pend)})", expanded=True):
            for v in pend[:5]: st.caption(f"- {v[3]} | Lote: {v[2]} | {v[4]}")
    if crit:
        with st.expander(f"Medicamentos em alerta ({len(crit)})", expanded=True):
            for m in crit[:5]:
                mot = "estoque baixo" if m[3]<=m[4] else f"vence {m[5]}"
                st.caption(f"- {m[1]} | {m[3]:.0f} {m[2]} ({mot})")
    if parto:
        with st.expander(f"Partos previstos ({len(parto)})"):
            for p in parto[:5]: st.caption(f"- {p[1]} | Lote: {p[2]} | {p[3]}")

st.divider()
st.subheader("Seus lotes")
if not lotes:
    st.info("Nenhum lote. Va em Cadastros > Cadastrar Lote.")
else:
    ncols = min(3, len(lotes))
    cols  = st.columns(ncols)
    for i, l in enumerate(lotes[:6]):
        rs   = resumo_lote(l[0])
        ico  = "verde" if rs["ativos"] > 0 else "cinza"
        tags = []
        if rs["mortos"]:           tags.append(f"Mortes: {rs['mortos']}")
        if rs["vacinas_pendentes"]:tags.append(f"Vac pend: {rs['vacinas_pendentes']}")
        if rs["ocorrencias"]:      tags.append(f"Ocorr: {rs['ocorrencias']}")
        tag_str = " | ".join(tags) if tags else "Sem alertas"
        with cols[i % ncols]:
            st.markdown(f"**{l[1]}**")
            st.caption(f"Ativos: {rs['ativos']} | Entrada: {l[3]}")
            st.caption(tag_str)
            st.divider()

st.subheader("Acoes rapidas")
qa1,qa2,qa3,qa4 = st.columns(4)
if qa1.button("Novo Lote",        use_container_width=True): st.session_state.menu="Cadastrar Lote";       st.rerun()
if qa2.button("Registrar Peso",   use_container_width=True): st.session_state.menu="Registrar Pesagem";    st.rerun()
if qa3.button("Nova Ocorrencia",  use_container_width=True): st.session_state.menu="Registrar Ocorrencia"; st.rerun()
if qa4.button("Exportar",         use_container_width=True): st.session_state.menu="Exportar Relatorios";  st.rerun()
```

# ============================================================

# BUSCAR ANIMAL

# ============================================================

elif menu == “Buscar Animal”:
hdr(“Buscar Animal”, “Busca Global”, “Encontre qualquer animal pelo brinco ou identificacao”)
termo = st.text_input(“Identificacao / brinco”, placeholder=“Ex: BOI-001”)
if termo:
encontrados = [a for a in listar_animais() if termo.lower() in a[1].lower()]
if encontrados:
st.success(f”{len(encontrados)} animal(is) encontrado(s)”)
for a in encontrados:
lote = obter_lote(a[3])
nome_lote = lote[1] if lote else “?”
with st.expander(f”{a[1]} – Lote: {nome_lote}”):
det = obter_animal(a[0])
c1,c2 = st.columns(2)
with c1:
st.write(f”ID: {a[0]} | Idade: {a[2]} meses”)
if det: st.write(f”Raca: {det[5]} | Peso alvo: {det[7]} kg”)
with c2:
ps = listar_pesagens(a[0])
ocs = listar_ocorrencias(a[0])
sc  = calcular_score_saude(a[0])
st.write(f”Pesagens: {len(ps)} | Ocorrencias: {len(ocs)}”)
st.write(f”Score saude: {sc[‘score’]}/100 ({sc[‘classificacao’]})”)
car = verificar_carencia(a[0])
if car[“em_carencia”]:
st.warning(f”Em carencia ate {car[‘liberado_em’]}”)
else:
st.warning(f”Nenhum animal encontrado para ‘{termo}’”)

# ============================================================

# CADASTRAR LOTE

# ============================================================

elif menu == “Cadastrar Lote”:
hdr(“Cadastrar Lote”, “Novo Lote”, “Registre um novo lote de animais”)
c1,c2 = st.columns([2,1])
with c1:
with st.form(“form_lote”):
st.markdown(”#### Dados do lote”)
col1,col2 = st.columns(2)
with col1:
nome         = st.text_input(“Nome do lote *”)
data_ent     = st.date_input(“Data de entrada”)
qtd_comp     = st.number_input(“Qtd comprada”, 0, step=1)
transporte   = st.text_input(“Transportadora”)
with col2:
descricao    = st.text_area(“Descricao”, height=70)
qtd_rec      = st.number_input(“Qtd recebida”, 0, step=1)
preco_anim   = st.number_input(“Preco por animal (R$)”, 0.0)
st.markdown(”#### Manejo”)
m1,m2 = st.columns(2)
with m1: tipo_alim = st.selectbox(“Alimentacao”, [“Pasto”,“Confinamento”,“Semi-confinamento”])
with m2: tipo_diet = st.selectbox(“Dieta”, [“Capim”,“Racao”,“Silagem”,“Misto”])
salvar = st.form_submit_button(“Salvar Lote”, use_container_width=True, type=“primary”)
if salvar:
if not nome:               st.error(“Informe o nome do lote”)
elif qtd_rec > qtd_comp:   st.error(“Qtd recebida nao pode ser maior que comprada”)
elif qtd_rec == 0:         st.error(“Informe a quantidade recebida”)
else:
lid = adicionar_lote(nome, descricao, str(data_ent), qtd_comp, qtd_rec, transporte)
registrar_auditoria(u[“id”], “criar_lote”, “lotes”, lid, nome)
st.success(f”Lote **{nome}** criado!”)
st.balloons()
with c2:
st.markdown(”#### Dicas”)
st.info(“Use um nome facil de identificar, ex: Nelore Jan/25”)
st.info(“Qtd recebida pode ser menor que a comprada se houve perdas no transporte”)
if qtd_comp > 0 and preco_anim > 0:
st.metric(“Custo total estimado”, f”R$ {preco_anim*qtd_comp:,.2f}”)

# ============================================================

# CADASTRAR ANIMAL

# ============================================================

elif menu == “Cadastrar Animal”:
hdr(“Cadastrar Animal”, “Novo Animal”, “Vincule um animal a um lote”)
lotes = listar_lotes()
if not lotes:
st.warning(“Cadastre um lote primeiro.”)
else:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
c_sel,c_info = st.columns([2,1])
with c_sel: lote_sel = st.selectbox(“Lote”, list(dict_l.keys()))
lote_id = dict_l[lote_sel]
lote    = obter_lote(lote_id)
total   = contar_animais_no_lote(lote_id)
vagas   = max(0, lote[5] - total)
with c_info:
st.metric(“Cadastrados / Capacidade”, f”{total} / {lote[5]}”,
delta=f”{vagas} vaga(s)” if vagas > 0 else “Lote cheio”,
delta_color=“normal” if vagas > 0 else “inverse”)
if total >= lote[5]:
st.error(“Limite do lote atingido.”)
else:
with st.form(“form_animal”):
a1,a2,a3 = st.columns(3)
with a1: ident  = st.text_input(“Brinco / Identificacao *”, placeholder=“BOI-001”)
with a2: idade  = st.number_input(“Idade (meses)”, 0, 240, 24)
with a3: p_ent  = st.number_input(“Peso entrada (kg)”, 0.0)
b1,b2,b3 = st.columns(3)
with b1: raca   = st.text_input(“Raca”, placeholder=“Nelore”)
with b2: sexo   = st.selectbox(“Sexo”, [“indefinido”,“macho”,“femea”])
with b3: p_alvo = st.number_input(“Peso alvo abate (kg)”, 0.0)
salvar = st.form_submit_button(“Cadastrar Animal”, use_container_width=True, type=“primary”)
if salvar:
if not ident:
st.error(“Informe a identificacao do animal”)
else:
aid = adicionar_animal(ident, idade, lote_id)
if p_alvo > 0: atualizar_animal_detalhes(aid, peso_alvo=p_alvo)
registrar_auditoria(u[“id”], “cadastro_animal”, “animais”, aid, ident)
st.success(f”**{ident}** cadastrado no lote **{lote[1]}**!”)
st.rerun()

# ============================================================

# REGISTRAR PESAGEM

# ============================================================

elif menu == “Registrar Pesagem”:
hdr(“Registrar Pesagem”, “Novo Peso”, “Registre o peso atual de um animal”)
lotes = listar_lotes()
if not lotes:
st.warning(“Cadastre um lote primeiro.”)
else:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
c1,c2 = st.columns(2)
with c1: lote_sel = st.selectbox(“Lote”, list(dict_l.keys()), key=“pes_lote”)
lote_id = dict_l[lote_sel]
animais = listar_animais_por_lote(lote_id)
if not animais:
st.warning(“Nenhum animal neste lote.”)
else:
dict_a = {f”{a[1]} (ID {a[0]})”: a[0] for a in animais}
with c2: anim_sel = st.selectbox(“Animal”, list(dict_a.keys()), key=“pes_anim”)
animal_id = dict_a[anim_sel]
ps_ant = listar_pesagens(animal_id)
if ps_ant:
ult = ps_ant[-1]
det = obter_animal(animal_id)
r1,r2,r3 = st.columns(3)
r1.metric(“Ultimo peso”, f”{ult[2]:.1f} kg”, f”em {ult[3]}”)
if det and det[7] > 0:
falta = det[7] - ult[2]
r2.metric(“Peso alvo”, f”{det[7]:.0f} kg”, f”faltam {falta:.1f} kg” if falta>0 else “Atingido!”)
if len(ps_ant) >= 2:
df_r = pd.DataFrame(ps_ant, columns=[“id”,“aid”,“peso”,“data”])
df_r[“data”] = pd.to_datetime(df_r[“data”])
df_r = df_r.sort_values(“data”)
dias_r = (df_r[“data”].iloc[-1]-df_r[“data”].iloc[0]).days
if dias_r > 0:
gmd_r = (df_r[“peso”].iloc[-1]-df_r[“peso”].iloc[0])/dias_r
r3.metric(“GMD atual”, f”{gmd_r:.3f} kg/dia”)
st.divider()
with st.form(“form_pesagem”):
p1,p2 = st.columns(2)
with p1: peso   = st.number_input(“Peso (kg) *”, 0.0, 1000.0, step=0.5)
with p2: data_p = st.date_input(“Data”)
salvar = st.form_submit_button(“Salvar Pesagem”, use_container_width=True, type=“primary”)
if salvar:
if peso <= 0:    st.error(“Peso invalido”)
elif peso > 1000: st.error(“Peso muito alto”)
else:
adicionar_pesagem(animal_id, peso, str(data_p))
registrar_auditoria(u[“id”], “pesagem”, “pesagens”, animal_id, f”{peso}kg em {data_p}”)
st.success(f”Pesagem de **{peso:.1f} kg** registrada!”)
st.rerun()

# ============================================================

# REGISTRAR OCORRENCIA

# ============================================================

elif menu == “Registrar Ocorrencia”:
hdr(“Registrar Ocorrencia”, “Nova Ocorrencia”, “Doencas, lesoes e medicacoes”)
lotes = listar_lotes()
if not lotes:
st.warning(“Cadastre um lote primeiro.”)
else:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
o1,o2 = st.columns(2)
with o1: lote_sel = st.selectbox(“Lote”, list(dict_l.keys()), key=“oc_lote”)
lote_id = dict_l[lote_sel]
animais = listar_animais_por_lote(lote_id)
if not animais:
st.warning(“Nenhum animal neste lote.”)
else:
dict_a = {f”{a[1]} (ID {a[0]})”: a[0] for a in animais}
with o2: anim_sel = st.selectbox(“Animal”, list(dict_a.keys()), key=“oc_anim”)
animal_id = dict_a[anim_sel]
with st.form(“form_oc”):
oc1,oc2,oc3 = st.columns(3)
with oc1: data_oc  = st.date_input(“Data”)
with oc2: tipo_oc  = st.selectbox(“Tipo”, [“Doenca”,“Lesao”,“Medicamento”,“Outros”])
with oc3: grav_oc  = st.selectbox(“Gravidade”, [“Baixa”,“Media”,“Alta”])
desc_oc  = st.text_area(“Descricao”)
oc4,oc5,oc6 = st.columns(3)
with oc4: custo_oc = st.number_input(“Custo (R$)”, 0.0)
with oc5: dias_oc  = st.number_input(“Dias recuperacao”, 0)
with oc6: stat_oc  = st.selectbox(“Status”, [“Em tratamento”,“Resolvido”])
salvar = st.form_submit_button(“Salvar Ocorrencia”, use_container_width=True, type=“primary”)
if salvar:
oid = adicionar_ocorrencia(animal_id, str(data_oc), tipo_oc, desc_oc, grav_oc, custo_oc, dias_oc, stat_oc)
registrar_auditoria(u[“id”], “ocorrencia”, “ocorrencias”, oid, f”{tipo_oc}/{grav_oc}”)
st.success(“Ocorrencia registrada!”)
st.rerun()

# ============================================================

# REGISTRAR MORTE

# ============================================================

elif menu == “Registrar Morte”:
hdr(“Registrar Morte”, “Baixa de Animal”, “Registre a morte e retire o animal do lote”)
tab1,tab2 = st.tabs([“Registrar”, “Historico”])
with tab1:
lotes = listar_lotes()
if not lotes:
st.warning(“Cadastre um lote primeiro.”)
else:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
lote_sel_m = st.selectbox(“Lote”, list(dict_l.keys()), key=“morte_lote”)
lote_id_m  = dict_l[lote_sel_m]
animais_m  = listar_animais_por_lote(lote_id_m)
if not animais_m:
st.warning(“Nenhum animal ativo neste lote.”)
else:
dict_am = {f”{a[1]} (ID {a[0]})”: a[0] for a in animais_m}
with st.form(“form_morte”):
anim_sel_m = st.selectbox(“Animal”, list(dict_am.keys()))
m1,m2 = st.columns(2)
with m1:
data_m  = st.date_input(“Data”)
causa_m = st.selectbox(“Causa”, [“Doenca”,“Acidente”,“Desaparecimento”,“Predador”,“Outras”])
with m2:
custo_m = st.number_input(“Custo da perda (R$)”, 0.0)
desc_m  = st.text_area(“Descricao”)
salvar = st.form_submit_button(“Registrar Morte”, use_container_width=True, type=“primary”)
if salvar:
registrar_morte(dict_am[anim_sel_m], str(data_m), causa_m, desc_m, custo_m)
registrar_auditoria(u[“id”], “morte_animal”, “animais”, dict_am[anim_sel_m], f”{anim_sel_m} - {causa_m}”)
st.success(“Morte registrada. Animal removido do lote.”)
st.rerun()
with tab2:
lotes = listar_lotes()
if lotes:
dict_l2 = {“Todos”: None, **{f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}}
filtro_m = st.selectbox(“Filtrar por lote”, list(dict_l2.keys()), key=“mort_hist”)
morts = listar_mortalidade(dict_l2[filtro_m])
if morts:
df_m = pd.DataFrame(morts, columns=[“ID”,“Animal ID”,“Animal”,“Data”,“Causa”,“Descricao”,“Custo Perda”])
st.dataframe(df_m, use_container_width=True)
st.metric(“Custo total perdas”, f”R$ {sum(m[6] for m in morts if m[6]):.2f}”)
else:
st.success(“Nenhuma morte registrada.”)

# ============================================================

# IMPORTAR CSV

# ============================================================

elif menu == “Importar CSV”:
hdr(“Importar CSV”, “Importacao em Lote”, “Importe pesagens e animais via planilha CSV”)
lotes = listar_lotes()
st.subheader(“Lote de destino”)
opcao = st.radio(””, [“Usar lote existente”,“Criar novo lote”], horizontal=True, key=“imp_op”)
lote_id = None
if opcao == “Criar novo lote”:
with st.form(“form_lote_imp”):
ci1,ci2 = st.columns(2)
with ci1:
nome_nl = st.text_input(“Nome do lote *”)
qtd_c2  = st.number_input(“Qtd comprada”, 0, step=1)
qtd_r2  = st.number_input(“Qtd recebida”, 0, step=1)
with ci2:
data_nl = st.date_input(“Data entrada”)
trp_nl  = st.text_input(“Transportadora”)
if st.form_submit_button(“Criar lote”):
if nome_nl:
lote_id = adicionar_lote(nome_nl, “”, str(data_nl), qtd_c2, qtd_r2, trp_nl)
registrar_auditoria(u[“id”], “criar_lote”, “lotes”, lote_id, nome_nl)
st.success(f”Lote ‘{nome_nl}’ criado!”)
st.rerun()
else: st.error(“Informe o nome.”)
lotes = listar_lotes()
if lotes: lote_id = lotes[0][0]; st.info(f”Lote: {lotes[0][1]}”)
else:
if not lotes: st.warning(“Crie um lote primeiro.”); st.stop()
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
lote_id = dict_l[st.selectbox(“Selecione o lote”, list(dict_l.keys()), key=“imp_lote”)]

```
if not lote_id: st.stop()
st.divider()
tab_p,tab_a = st.tabs(["Importar Pesagens","Importar Animais"])

with tab_p:
    st.markdown("**Formato CSV:**")
    st.code("identificacao,peso,data\nBOI-001,310.5,2024-01-15")
    arq = st.file_uploader("CSV de pesagens", type=["csv"], key="csv_pes")
    if arq:
        import csv, io as _io
        txt = arq.read().decode("utf-8-sig", errors="ignore")
        linhas = list(csv.DictReader(_io.StringIO(txt)))
        st.info(f"{len(linhas)} linhas encontradas.")
        if st.button("Importar pesagens"):
            res = importar_pesagens_csv(linhas, lote_id)
            registrar_auditoria(u["id"], "import_pesagens", "pesagens", lote_id, f"{res['importados']} importadas")
            st.success(f"Importadas: {res['importados']} | Animais criados: {res['animais_criados']} | Erros: {res['erros']}")
            for msg in res["mensagens"]: st.warning(msg)

with tab_a:
    st.markdown("**Formato CSV:**")
    st.code("identificacao,idade,raca,sexo,peso_alvo\nBOI-001,24,Nelore,macho,450")
    arq2 = st.file_uploader("CSV de animais", type=["csv"], key="csv_anim")
    if arq2:
        import csv, io as _io
        txt2 = arq2.read().decode("utf-8-sig", errors="ignore")
        linhas2 = list(csv.DictReader(_io.StringIO(txt2)))
        st.info(f"{len(linhas2)} linhas encontradas.")
        if st.button("Importar animais"):
            res2 = importar_animais_csv(linhas2, lote_id)
            registrar_auditoria(u["id"], "import_animais", "animais", lote_id, f"{res2['importados']} importados")
            st.success(f"Importados: {res2['importados']} | Erros: {res2['erros']}")
            for msg in res2["mensagens"]: st.warning(msg)
```

# ============================================================

# DASHBOARD SANITARIO

# ============================================================

elif menu == “Dashboard Sanitario”:
hdr(“Dashboard Sanitario”, “Saude do Rebanho”, “Incidencias, curva epidemica e alertas”)
lotes = listar_lotes()
opcoes = [“Todos os lotes”] + [f”{l[1]} (ID {l[0]})” for l in lotes]
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
escolha = st.selectbox(“Filtrar por lote”, opcoes)
animais = listar_animais() if escolha == “Todos os lotes” else listar_animais_por_lote(dict_l[escolha])

```
todas_oc = []
for a in animais: todas_oc.extend(listar_ocorrencias(a[0]))

df_oc = pd.DataFrame(todas_oc, columns=["id","animal_id","data","tipo","descricao","gravidade","custo","dias_rec","status"]) if todas_oc else pd.DataFrame(columns=["id","animal_id","data","tipo","descricao","gravidade","custo","dias_rec","status"])

total_a  = len(animais)
c_oc     = df_oc["animal_id"].nunique() if len(df_oc)>0 else 0
inc      = (c_oc/total_a*100) if total_a>0 else 0
custo_oc = df_oc["custo"].fillna(0).sum() if len(df_oc)>0 else 0

k1,k2,k3,k4 = st.columns(4)
k1.metric("Animais", total_a)
k2.metric("Com ocorrencia", c_oc)
k3.metric("Incidencia", f"{inc:.1f}%", delta="Alta" if inc>20 else None, delta_color="inverse" if inc>20 else "normal")
k4.metric("Custo sanitario", f"R$ {custo_oc:.2f}")

st.divider()

if len(df_oc) > 0:
    t1,t2,t3,t4 = st.tabs(["Graficos","Por Lote","Curva Epidemica","Alertas"])
    with t1:
        c1,c2 = st.columns(2)
        with c1:
            st.subheader("Por tipo")
            st.bar_chart(df_oc["tipo"].value_counts())
        with c2:
            st.subheader("Por gravidade")
            st.bar_chart(df_oc["gravidade"].value_counts())
    with t2:
        dados_l = []
        for lote in lotes:
            anim_l = listar_animais_por_lote(lote[0])
            tot_l  = len(anim_l)
            ids_l  = [a[0] for a in anim_l]
            oc_l   = df_oc[df_oc["animal_id"].isin(ids_l)] if len(df_oc)>0 else pd.DataFrame()
            doentes_l = oc_l["animal_id"].nunique() if len(oc_l)>0 else 0
            inc_l  = (doentes_l/tot_l*100) if tot_l>0 else 0
            dados_l.append((lote[1], inc_l))
        df_l = pd.DataFrame(dados_l, columns=["Lote","Incidencia (%)"]).set_index("Lote")
        st.bar_chart(df_l)
    with t3:
        df_oc2 = df_oc.copy()
        df_oc2["data"] = pd.to_datetime(df_oc2["data"])
        curva = df_oc2.groupby(["data","tipo"]).size().unstack(fill_value=0)
        st.line_chart(curva)
    with t4:
        for nome_l, inc_l in dados_l:
            if inc_l > 20:  st.error(f"{nome_l}: alta incidencia ({inc_l:.1f}%)")
            elif inc_l > 5: st.warning(f"{nome_l}: incidencia moderada ({inc_l:.1f}%)")
            else:           st.success(f"{nome_l}: controle adequado ({inc_l:.1f}%)")
else:
    st.info("Nenhuma ocorrencia registrada ainda.")
```

# ============================================================

# ANALISAR POR LOTE

# ============================================================

elif menu == “Analisar por Lote”:
hdr(“Analisar por Lote”, “Analise do Lote”, “Desempenho economico e zootecnico”)
lote_id, lotes = sel_lote(“analise_lote”)
if lote_id:
lote   = obter_lote(lote_id)
animais = listar_animais_por_lote(lote_id)
rs = resumo_lote(lote_id)
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric(“Ativos”,    rs[“ativos”])
k2.metric(“Mortes”,    rs[“mortos”])
k3.metric(“GTAs”,      rs[“gtas_emitidas”])
k4.metric(“Ocorrencias”, rs[“ocorrencias”])
k5.metric(“Vac. pend.”,  rs[“vacinas_pendentes”])
st.divider()

```
    custo_diar = st.number_input("Custo diario por animal (R$)", 0.0, 100.0, 10.0)
    preco_kg   = st.number_input("Preco do kg (R$)", 0.0, 50.0, 10.0)

    datas = [p[3] for a in animais for p in listar_pesagens(a[0])]
    dias_lote = 0
    if len(datas) > 1:
        dts = pd.to_datetime(datas)
        dias_lote = (max(dts)-min(dts)).days

    custo_op = custo_diar * len(animais) * dias_lote
    ganho_t  = 0
    custo_san = 0
    gmds = []
    for a in animais:
        ps = listar_pesagens(a[0])
        if len(ps) > 1:
            df = pd.DataFrame(ps, columns=["id","aid","peso","data"])
            df["data"] = pd.to_datetime(df["data"])
            df = df.sort_values("data")
            g  = df["peso"].iloc[-1] - df["peso"].iloc[0]
            d  = (df["data"].iloc[-1]-df["data"].iloc[0]).days
            if g > 0: ganho_t += g
            if d > 0:
                gmd = g/d
                if 0 <= gmd <= 2: gmds.append(gmd)
        for oc in listar_ocorrencias(a[0]):
            if oc[6]: custo_san += oc[6]

    receita = ganho_t * preco_kg
    lucro   = receita - custo_op - custo_san
    gmd_m   = sum(gmds)/len(gmds) if gmds else 0

    st.subheader("Resultado Economico")
    re1,re2,re3,re4 = st.columns(4)
    re1.metric("Receita estimada", f"R$ {receita:,.2f}")
    re2.metric("Custo operacional", f"R$ {custo_op:,.2f}")
    re3.metric("Custo sanitario",  f"R$ {custo_san:,.2f}")
    re4.metric("Lucro / Prejuizo", f"R$ {lucro:,.2f}", delta="Lucro" if lucro>=0 else "Prejuizo", delta_color="normal" if lucro>=0 else "inverse")

    st.metric("GMD medio do lote", f"{gmd_m:.3f} kg/dia")
    if gmd_m < 0.5: st.warning("Baixo desempenho")
    elif gmd_m > 0: st.success("Bom desempenho")

    lucro_anim = lucro/len(animais) if animais else 0
    st.metric("Lucro por animal", f"R$ {lucro_anim:,.2f}")

    # Ranking GMD
    ranking = []
    for a in animais:
        ps = listar_pesagens(a[0])
        if len(ps) > 1:
            df = pd.DataFrame(ps, columns=["id","aid","peso","data"])
            df["data"] = pd.to_datetime(df["data"])
            df = df.sort_values("data")
            d  = (df["data"].iloc[-1]-df["data"].iloc[0]).days
            if d > 0:
                gmd = (df["peso"].iloc[-1]-df["peso"].iloc[0])/d
                if 0 <= gmd <= 2: ranking.append((a[1], gmd))
    if ranking:
        ranking.sort(key=lambda x: x[1], reverse=True)
        st.subheader("Ranking GMD")
        for i,(nm,gmd) in enumerate(ranking,1):
            st.write(f"{i}. {nm} -> {gmd:.3f} kg/dia")
```

# ============================================================

# ANALISAR ANIMAL

# ============================================================

elif menu == “Analisar Animal”:
hdr(“Analisar Animal”, “Analise Individual”, “Historico de peso, ocorrencias e alertas”)
lotes = listar_lotes()
if not lotes:
st.warning(“Nenhum lote cadastrado”)
else:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
aa1,aa2 = st.columns(2)
with aa1: lote_s = st.selectbox(“Lote”, list(dict_l.keys()), key=“aa_lote”)
lote_id = dict_l[lote_s]
animais = listar_animais_por_lote(lote_id)
if not animais:
st.warning(“Nenhum animal neste lote.”)
else:
dict_a = {f”{a[1]} (ID {a[0]})”: a[0] for a in animais}
with aa2: anim_s = st.selectbox(“Animal”, list(dict_a.keys()), key=“aa_anim”)
animal_id = dict_a[anim_s]
pesagens   = listar_pesagens(animal_id)
ocorrencias = listar_ocorrencias(animal_id)
sc = calcular_score_saude(animal_id)
gmd = None

```
        km1,km2,km3,km4 = st.columns(4)
        km1.metric("Pesagens",    len(pesagens))
        km2.metric("Ocorrencias", len(ocorrencias))
        km3.metric("Score saude", f"{sc['score']}/100")
        km4.metric("Classificacao", sc["classificacao"])

        t1,t2,t3 = st.tabs(["Pesagens & GMD","Ocorrencias","Alertas"])

        with t1:
            if pesagens:
                df = pd.DataFrame(pesagens, columns=["ID","Animal","Peso","Data"])
                df["Data"] = pd.to_datetime(df["Data"])
                df = df.sort_values("Data")
                st.line_chart(df.set_index("Data")["Peso"])
                st.dataframe(df[["Data","Peso"]].rename(columns={"Peso":"Peso (kg)"}), use_container_width=True)
                if len(df) > 1:
                    dias = (df["Data"].iloc[-1]-df["Data"].iloc[0]).days
                    if dias > 0:
                        gmd = (df["Peso"].iloc[-1]-df["Peso"].iloc[0])/dias
                        d1,d2,d3 = st.columns(3)
                        d1.metric("Ganho total", f"{df['Peso'].iloc[-1]-df['Peso'].iloc[0]:.2f} kg")
                        d2.metric("Periodo",     f"{dias} dias")
                        d3.metric("GMD",         f"{gmd:.3f} kg/dia")
                        if gmd < 0:    st.error("Perda de peso - possivel doenca")
                        elif gmd > 2:  st.error("GMD irreal - revisar dados")
                        elif gmd < 0.5: st.warning("GMD baixo")
                        else:          st.success("Bom desempenho")
            else:
                st.info("Sem pesagens registradas.")

        with t2:
            if ocorrencias:
                df_oc = pd.DataFrame(ocorrencias, columns=["id","animal_id","data","tipo","descricao","gravidade","custo","dias_rec","status"])
                df_oc["data"] = pd.to_datetime(df_oc["data"])
                st.dataframe(df_oc[["data","tipo","gravidade","descricao","custo","status"]], use_container_width=True)
                custo_tot = df_oc["custo"].fillna(0).sum()
                st.metric("Custo total tratamentos", f"R$ {custo_tot:.2f}")
            else:
                st.success("Nenhuma ocorrencia registrada.")

        with t3:
            det = sc["detalhes"]
            s1,s2,s3 = st.columns(3)
            s1.metric("GMD (pts)",        f"{det['pts_gmd']}/50")
            s2.metric("Ocorrencias (pts)",f"{det['pts_ocorrencias']}/35")
            s3.metric("Reproducao (pts)", f"{det['pts_reproducao']}/15")
            if gmd is not None:
                if gmd < 0.5 and ocorrencias: st.error("Alto risco: baixo GMD + ocorrencias")
                elif gmd < 0.5:               st.warning("Baixo GMD")
                elif ocorrencias:             st.warning("Historico clinico - monitorar")
                else:                         st.success("Animal saudavel e produtivo")
            car = verificar_carencia(animal_id)
            if car["em_carencia"]:
                st.error(f"Em carencia ate {car['liberado_em']} - nao abater!")
            else:
                st.success("Sem restricao de carencia")
```

# ============================================================

# SCORE DE SAUDE

# ============================================================

elif menu == “Score de Saude”:
hdr(“Score de Saude”, “Ranking de Saude”, “Nota 0-100 por animal (GMD + ocorrencias + reproducao)”)
lote_id, _ = sel_lote(“score_lote”)
if lote_id:
animais = listar_animais_por_lote(lote_id)
if not animais:
st.warning(“Nenhum animal.”)
else:
scores = []
for a in animais:
sc  = calcular_score_saude(a[0])
car = verificar_carencia(a[0])
scores.append({“Animal”: a[1], “Score”: sc[“score”], “Classificacao”: sc[“classificacao”],
“GMD”: sc[“detalhes”][“gmd”], “Ocorrencias”: sc[“detalhes”][“n_ocorrencias”],
“Em Carencia”: “Sim” if car[“em_carencia”] else “Nao”})
df_sc = pd.DataFrame(scores).sort_values(“Score”, ascending=False)
st.dataframe(df_sc, use_container_width=True)
c1,c2,c3 = st.columns(3)
c1.metric(“Score medio”,   f”{df_sc[‘Score’].mean():.1f}”)
c2.metric(“Melhor animal”, df_sc.iloc[0][“Animal”])
c3.metric(“Criticos (<40)”, len(df_sc[df_sc[“Score”]<40]))
st.bar_chart(df_sc.set_index(“Animal”)[“Score”])
st.subheader(“Alertas”)
for _, row in df_sc.iterrows():
if row[“Score”] < 40:   st.error(f”{row[‘Animal’]}: Score {row[‘Score’]} - CRITICO”)
elif row[“Score”] < 60: st.warning(f”{row[‘Animal’]}: Score {row[‘Score’]} - Regular”)
if row[“Em Carencia”] == “Sim”: st.warning(f”{row[‘Animal’]}: em carencia de medicamento”)

# ============================================================

# GMD TEMPORAL

# ============================================================

elif menu == “GMD Temporal”:
hdr(“GMD Temporal”, “Evolucao do GMD”, “Evolucao do ganho de peso ao longo do tempo”)
lote_id, _ = sel_lote(“gmd_lote”)
if lote_id:
janela = st.slider(“Janela de calculo (dias)”, 7, 60, 14)
pontos = calcular_gmd_temporal(lote_id, janela)
if pontos:
df_g = pd.DataFrame(pontos, columns=[“Data”,“GMD medio (kg/dia)”]).set_index(“Data”)
st.line_chart(df_g)
st.dataframe(df_g, use_container_width=True)
ult = pontos[-1][1]; pri = pontos[0][1]
st.metric(“GMD atual”, f”{ult:.3f} kg/dia”, delta=f”{ult-pri:+.3f} vs inicio”)
if ult-pri < -0.1:   st.error(“GMD em queda - revisar nutricao”)
elif ult-pri > 0.1:  st.success(“GMD em melhora”)
else:                st.info(“GMD estavel”)
else:
st.info(“Dados insuficientes. Registre pesagens em datas diferentes.”)

# ============================================================

# COMPARATIVO LOTES

# ============================================================

elif menu == “Comparativo Lotes”:
hdr(“Comparativo Lotes”, “Comparativo entre Lotes”, “Side-by-side de GMD, custos e resultados”)
lotes = listar_lotes()
if len(lotes) < 2:
st.warning(“Cadastre pelo menos 2 lotes.”)
else:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
sels = st.multiselect(“Selecione 2 a 4 lotes”, list(dict_l.keys()), default=list(dict_l.keys())[:min(2,len(dict_l))])
if len(sels) < 2:
st.info(“Selecione pelo menos 2 lotes.”)
else:
pk  = st.number_input(“Preco kg (R$)”, 0.0, 100.0, 20.0)
cd  = st.number_input(“Custo diario/animal (R$)”, 0.0, 100.0, 10.0)
dados = []
for nm in sels:
lid   = dict_l[nm]
anim  = listar_animais_por_lote(lid)
tm    = taxa_mortalidade_lote(lid)
tp    = taxa_prenhez_lote(lid)
gmds, ganho, dias_t, custo_s = [], 0, 0, 0
for a in anim:
ps = listar_pesagens(a[0])
if len(ps) >= 2:
df = pd.DataFrame(ps, columns=[“id”,“aid”,“peso”,“data”])
df[“data”] = pd.to_datetime(df[“data”])
df = df.sort_values(“data”)
d  = (df[“data”].iloc[-1]-df[“data”].iloc[0]).days
g  = df[“peso”].iloc[-1]-df[“peso”].iloc[0]
if d > 0:
gv = g/d
if 0 < gv <= 2: gmds.append(gv)
ganho += g; dias_t += d
for oc in listar_ocorrencias(a[0]):
if oc[6]: custo_s += oc[6]
gmd_m  = sum(gmds)/len(gmds) if gmds else 0
receita = ganho * pk
custo_op = cd * len(anim) * (dias_t/max(len(anim),1))
lucro   = receita - custo_op - custo_s
dados.append({“Lote”: nm.split(” (ID”)[0], “Animais”: len(anim),
“GMD medio”: gmd_m, “Incid. %”: round(len([a for a in anim if listar_ocorrencias(a[0])])/max(len(anim),1)*100,1),
“Mortalidade %”: tm[“taxa”], “Prenhez %”: round(tp[“taxa”],1),
“Lucro R$”: round(lucro,2)})
df_c = pd.DataFrame(dados).set_index(“Lote”)
st.dataframe(df_c, use_container_width=True)
c1,c2 = st.columns(2)
with c1: st.subheader(“GMD medio”); st.bar_chart(df_c[“GMD medio”])
with c2: st.subheader(“Lucro R$”);  st.bar_chart(df_c[“Lucro R$”])

# ============================================================

# PAINEL DE DECISAO

# ============================================================

elif menu == “Painel de Decisao”:
hdr(“Painel de Decisao”, “Decisao Financeira”, “Resultado financeiro por lote”)
pk = st.number_input(“Preco kg (R$)”, 0.0, 50.0, 10.0)
cd = st.number_input(“Custo diario/animal (R$)”, 0.0, 100.0, 10.0)
lotes = listar_lotes()
if not lotes: st.warning(“Nenhum lote.”); st.stop()
dados = []
for l in lotes:
anim = listar_animais_por_lote(l[0])
ganho = custo_s = dias_t = 0
for a in anim:
ps = listar_pesagens(a[0])
if len(ps) > 1:
df = pd.DataFrame(ps, columns=[“id”,“aid”,“peso”,“data”])
df[“data”] = pd.to_datetime(df[“data”])
df = df.sort_values(“data”)
g = df[“peso”].iloc[-1]-df[“peso”].iloc[0]
d = (df[“data”].iloc[-1]-df[“data”].iloc[0]).days
if g > 0 and d > 0: ganho += g; dias_t += d
for oc in listar_ocorrencias(a[0]):
if oc[6]: custo_s += oc[6]
custo_op = cd * len(anim) * dias_t
receita  = ganho * pk
lucro    = receita - custo_op - custo_s
dados.append((l[1], lucro, receita, custo_op, custo_s))
df_d = pd.DataFrame(dados, columns=[“Lote”,“Lucro”,“Receita”,“Custo Op”,“Custo San”]).sort_values(“Lucro”, ascending=False)
st.metric(“Lucro total”, f”R$ {df_d[‘Lucro’].sum():,.2f}”)
st.dataframe(df_d, use_container_width=True)
st.bar_chart(df_d.set_index(“Lote”)[“Lucro”])
st.subheader(“Alertas”)
for _, row in df_d.iterrows():
if row[“Lucro”] < 0:                            st.error(f”{row[‘Lote’]}: prejuizo”)
elif row[“Custo San”] > row[“Receita”] * 0.2:  st.warning(f”{row[‘Lote’]}: custo sanitario elevado”)
else:                                           st.success(f”{row[‘Lote’]}: operacao saudavel”)

# ============================================================

# DASHBOARD EXECUTIVO

# ============================================================

elif menu == “Dashboard Executivo”:
hdr(“Dashboard Executivo”, “KPIs Executivos”, “KPIs consolidados do lote”)
pk = st.number_input(“Preco kg (R$)”, 0.0, 50.0, 10.0)
cd = st.number_input(“Custo diario/animal (R$)”, 0.0, 100.0, 10.0)
lote_id, _ = sel_lote(“exec_lote”)
if lote_id:
animais = listar_animais_por_lote(lote_id)
if not animais: st.warning(“Nenhum animal.”); st.stop()
ganho = custo_s = dias_t = 0
animais_oc = set()
gmds = []
for a in animais:
ps = listar_pesagens(a[0])
if len(ps) > 1:
df = pd.DataFrame(ps, columns=[“id”,“aid”,“peso”,“data”])
df[“data”] = pd.to_datetime(df[“data”])
df = df.sort_values(“data”)
g = df[“peso”].iloc[-1]-df[“peso”].iloc[0]
d = (df[“data”].iloc[-1]-df[“data”].iloc[0]).days
if g > 0 and d > 0:
ganho += g; dias_t += d
gmd = g/d
if 0 <= gmd <= 2: gmds.append(gmd)
ocs = listar_ocorrencias(a[0])
if ocs: animais_oc.add(a[0])
for oc in ocs:
if oc[6]: custo_s += oc[6]
n = len(animais)
custo_op = cd * n * dias_t
receita  = ganho * pk
lucro    = receita - custo_op - custo_s
inc      = (len(animais_oc)/n*100) if n>0 else 0
gmd_m    = sum(gmds)/len(gmds) if gmds else 0
c1,c2,c3 = st.columns(3)
c1.metric(“Lucro”,       f”R$ {lucro:,.2f}”)
c2.metric(“Incidencia”,  f”{inc:.2f}%”)
c3.metric(“GMD”,         f”{gmd_m:.3f} kg/dia”)
st.subheader(“Status do Lote”)
if lucro < 0:              st.error(“Prejuizo - acao imediata”)
elif inc > 20:             st.error(“Alta incidencia sanitaria”)
elif gmd_m < 0.5:         st.warning(“Baixo desempenho produtivo”)
elif custo_s > receita*.2: st.warning(“Custo sanitario elevado”)
else:                      st.success(“Lote saudavel e lucrativo”)
st.metric(“Animais”,        n)
st.metric(“Ganho total”,    f”{ganho:.2f} kg”)
st.metric(“Custo sanitario”,f”R$ {custo_s:.2f}”)

# ============================================================

# PESQUISAR OCORRENCIAS

# ============================================================

elif menu == “Pesquisar Ocorrencias”:
hdr(“Pesquisar Ocorrencias”, “Busca de Ocorrencias”, “Filtros por lote, tipo e gravidade”)
lotes = listar_lotes()
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
f1,f2,f3 = st.columns(3)
with f1: escolha_l = st.selectbox(“Lote”, [“Todos”]+list(dict_l.keys()))
with f2: tipo_f    = st.selectbox(“Tipo”, [“Todos”,“Doenca”,“Lesao”,“Medicamento”,“Outros”])
with f3: grav_f    = st.selectbox(“Gravidade”, [“Todas”,“Baixa”,“Media”,“Alta”])
animais = listar_animais() if escolha_l==“Todos” else listar_animais_por_lote(dict_l[escolha_l])
todas_oc = []
for a in animais: todas_oc.extend(listar_ocorrencias(a[0]))
df_oc = pd.DataFrame(todas_oc, columns=[“id”,“animal_id”,“data”,“tipo”,“descricao”,“gravidade”,“custo”,“dias_rec”,“status”]) if todas_oc else pd.DataFrame(columns=[“id”,“animal_id”,“data”,“tipo”,“descricao”,“gravidade”,“custo”,“dias_rec”,“status”])
if len(df_oc)>0:
if tipo_f!=“Todos”:  df_oc = df_oc[df_oc[“tipo”]==tipo_f]
if grav_f!=“Todas”:  df_oc = df_oc[df_oc[“gravidade”]==grav_f]
df_oc[“data”] = pd.to_datetime(df_oc[“data”])
df_oc = df_oc.sort_values(“data”, ascending=False)
st.divider()
if len(df_oc)>0:
p1,p2,p3,p4 = st.columns(4)
p1.metric(“Ocorrencias”,   len(df_oc))
p2.metric(“Animais afetados”, df_oc[“animal_id”].nunique())
p3.metric(“Custo total”,   f”R$ {df_oc[‘custo’].fillna(0).sum():.2f}”)
p4.metric(“Gravidade Alta”, len(df_oc[df_oc[“gravidade”]==“Alta”]))
t1,t2 = st.tabs([“Registros”,“Graficos”])
with t1: st.dataframe(df_oc[[“data”,“tipo”,“gravidade”,“descricao”,“custo”,“status”]], use_container_width=True)
with t2:
c1,c2 = st.columns(2)
with c1: st.bar_chart(df_oc[“tipo”].value_counts())
with c2: st.bar_chart(df_oc[“gravidade”].value_counts())
else:
st.info(“Nenhuma ocorrencia com esses filtros.”)

# ============================================================

# CALENDARIO SANITARIO

# ============================================================

elif menu == “Calendario Sanitario”:
hdr(“Calendario Sanitario”, “Vacinas e Medicacoes”, “Agenda de vacinas e alertas”)
t1,t2,t3 = st.tabs([“Agenda”,“Agendar”,“Confirmar”])
with t1:
lotes = listar_lotes()
if lotes:
d = {“Todos”: None, **{f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}}
f  = st.selectbox(“Lote”, list(d.keys()), key=“cal_f”)
vs = listar_vacinas_agenda(d[f])
if vs:
df_v = pd.DataFrame(vs, columns=[“ID”,“Lote”,“Vacina”,“Previsto”,“Realizado”,“Status”,“Obs”])
st.dataframe(df_v, use_container_width=True)
hoje = date.today()
for _, row in df_v.iterrows():
try:
dt_p = datetime.strptime(str(row[“Previsto”]), “%Y-%m-%d”).date()
atrasado = dt_p < hoje and row[“Status”]==“pendente”
except: atrasado = False
if row[“Status”]==“realizado”:  st.success(f”{row[‘Vacina’]} - realizada”)
elif atrasado:                  st.error(f”ATRASADA: {row[‘Vacina’]} - previsto {row[‘Previsto’]}”)
else:                           st.warning(f”Pendente: {row[‘Vacina’]} - {row[‘Previsto’]}”)
else: st.info(“Nenhuma vacina agendada.”)
with t2:
lotes = listar_lotes()
if not lotes: st.warning(“Cadastre um lote.”)
else:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
with st.form(“form_vac”):
vs1,vs2 = st.columns(2)
with vs1:
lote_v = st.selectbox(“Lote”, list(dict_l.keys()))
nome_v = st.text_input(“Nome da vacina *”)
with vs2:
data_v = st.date_input(“Data prevista”, value=date.today()+timedelta(days=7))
obs_v  = st.text_area(“Observacao”)
if st.form_submit_button(“Agendar”, type=“primary”):
if nome_v:
adicionar_vacina_agenda(dict_l[lote_v], nome_v, str(data_v), obs_v)
st.success(“Agendado!”); st.rerun()
else: st.error(“Informe o nome.”)
with t3:
pend_v = listar_vacinas_pendentes()
if not pend_v: st.success(“Nenhuma vacina pendente.”)
else:
df_p = pd.DataFrame(pend_v, columns=[“ID”,“Lote ID”,“Lote”,“Vacina”,“Previsto”,“Status”,“Obs”])
op   = {f”{r[‘Vacina’]} - {r[‘Lote’]} (prev. {r[‘Previsto’]})”: r[“ID”] for _,r in df_p.iterrows()}
with st.form(“form_real_v”):
sel_v = st.selectbox(“Vacina”, list(op.keys()))
dt_r  = st.date_input(“Data realizacao”)
if st.form_submit_button(“Confirmar”, type=“primary”):
registrar_vacina_realizada(op[sel_v], str(dt_r))
st.success(“Registrado!”); st.rerun()

# ============================================================

# ESTOQUE MEDICAMENTOS

# ============================================================

elif menu == “Estoque Medicamentos”:
hdr(“Estoque Medicamentos”, “Controle de Medicamentos”, “Estoque, validade e uso”)
t1,t2,t3 = st.tabs([“Estoque”,“Cadastrar”,“Registrar Uso”])
with t1:
meds  = listar_medicamentos()
crits = listar_medicamentos_criticos()
if crits:
for m in crits:
mot = “estoque baixo” if m[3]<=m[4] else f”vence {m[5]}”
st.error(f”{m[1]} - {m[3]:.1f} {m[2]} ({mot})”)
if meds:
df_m = pd.DataFrame(meds, columns=[“ID”,“Nome”,“Unidade”,“Estoque”,“Minimo”,“Validade”,“Custo Unit.”])
st.dataframe(df_m, use_container_width=True)
m1,m2 = st.columns(2)
m1.metric(“Valor total estoque”, f”R$ {sum(m[3]*m[6] for m in meds):,.2f}”)
m2.metric(“Itens cadastrados”,   len(meds))
else: st.info(“Nenhum medicamento.”)
with t2:
with st.form(“form_med”):
mn1,mn2 = st.columns(2)
with mn1:
nome_md = st.text_input(“Nome *”)
unid_md = st.selectbox(“Unidade”, [“dose”,“mL”,“g”,“comprimido”,“frasco”,“kg”])
estq_md = st.number_input(“Estoque inicial”, 0.0, step=1.0)
with mn2:
emin_md = st.number_input(“Estoque minimo (alerta)”, 0.0, step=1.0)
val_md  = st.date_input(“Validade”)
cust_md = st.number_input(“Custo unitario (R$)”, 0.0)
if st.form_submit_button(“Cadastrar”, type=“primary”):
if nome_md:
adicionar_medicamento(nome_md, unid_md, estq_md, emin_md, str(val_md), cust_md)
st.success(“Medicamento cadastrado!”); st.rerun()
else: st.error(“Informe o nome.”)
with t3:
meds  = listar_medicamentos()
lotes = listar_lotes()
if not meds or not lotes: st.warning(“Cadastre medicamentos e lotes.”)
else:
dict_md = {f”{m[1]} ({m[3]:.1f} {m[2]})”: m[0] for m in meds}
dict_l  = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
with st.form(“form_uso_md”):
u1,u2 = st.columns(2)
with u1:
med_s  = st.selectbox(“Medicamento”, list(dict_md.keys()))
lote_s = st.selectbox(“Lote”, list(dict_l.keys()))
with u2:
animais_u = listar_animais_por_lote(dict_l[lote_s])
dict_au   = {f”{a[1]} (ID {a[0]})”: a[0] for a in animais_u}
anim_s    = st.selectbox(“Animal”, list(dict_au.keys()) if dict_au else [”–”])
qtd_u     = st.number_input(“Quantidade”, 0.01, step=0.5)
data_u    = st.date_input(“Data”)
if st.form_submit_button(“Registrar”, type=“primary”) and dict_au:
registrar_uso_medicamento(dict_md[med_s], dict_au[anim_s], str(data_u), qtd_u)
st.success(“Uso registrado e estoque atualizado!”); st.rerun()

# ============================================================

# CONTROLE REPRODUTIVO

# ============================================================

elif menu == “Controle Reprodutivo”:
hdr(“Controle Reprodutivo”, “Reproducao”, “IATF, diagnostico, prenhez e partos”)
t1,t2,t3,t4 = st.tabs([“Indicadores”,“Registrar”,“Diagnostico”,“Partos”])
with t1:
lote_id, _ = sel_lote(“rep_ind”)
if lote_id:
tp = taxa_prenhez_lote(lote_id)
c1,c2,c3 = st.columns(3)
c1.metric(“Com registro”, tp[“total”])
c2.metric(“Positivas”,    tp[“positivas”])
c3.metric(“Taxa prenhez”, f”{tp[‘taxa’]:.1f}%”)
with t2:
lotes = listar_lotes()
if lotes:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
with st.form(“form_cob”):
r1,r2 = st.columns(2)
with r1:
lote_r = st.selectbox(“Lote”, list(dict_l.keys()))
anim_r = listar_animais_por_lote(dict_l[lote_r])
dict_ar = {f”{a[1]} (ID {a[0]})”: a[0] for a in anim_r}
anim_rs = st.selectbox(“Animal”, list(dict_ar.keys()) if dict_ar else [”–”])
with r2:
tipo_r = st.selectbox(“Tipo”, [“IATF”,“Monta Natural”,“TE”])
data_r = st.date_input(“Data cio / IATF”)
obs_r  = st.text_area(“Observacao”)
if st.form_submit_button(“Registrar”, type=“primary”) and dict_ar:
adicionar_reproducao(dict_ar[anim_rs], tipo_r, data_cio=str(data_r), observacao=obs_r)
st.success(“Cobertura registrada!”); st.rerun()
with t3:
lotes = listar_lotes()
if lotes:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
d1,d2 = st.columns(2)
with d1: lote_ds = st.selectbox(“Lote”, list(dict_l.keys()), key=“diag_lote”)
anim_d = listar_animais_por_lote(dict_l[lote_ds])
dict_ad = {f”{a[1]} (ID {a[0]})”: a[0] for a in anim_d}
if dict_ad:
with d2: anim_ds = st.selectbox(“Animal”, list(dict_ad.keys()), key=“diag_anim”)
repros = listar_reproducao(dict_ad[anim_ds])
if repros:
r = repros[0]
st.info(f”Ultimo registro: {r[3]} | Resultado: {r[5]}”)
with st.form(“form_diag”):
resultado = st.selectbox(“Resultado”, [“pendente”,“positivo”,“negativo”])
data_diag = st.date_input(“Data diagnostico”)
parto_p   = st.date_input(“Parto previsto”, value=date.today()+timedelta(days=283))
if st.form_submit_button(“Salvar”, type=“primary”):
atualizar_reproducao(r[0], resultado,
data_diagnostico=str(data_diag),
data_parto_previsto=str(parto_p) if resultado==“positivo” else None)
st.success(“Atualizado!”); st.rerun()
else: st.info(“Sem registros reprodutivos.”)
with t4:
partos = listar_partos_previstos()
if partos:
df_p = pd.DataFrame(partos, columns=[“ID”,“Animal”,“Lote”,“Parto Previsto”,“Tipo”])
st.dataframe(df_p, use_container_width=True)
else: st.success(“Nenhum parto previsto nos proximos 30 dias.”)

# ============================================================

# MAPA PIQUETES

# ============================================================

elif menu == “Mapa Piquetes”:
hdr(“Mapa Piquetes”, “Pastagens e Piquetes”, “Alocacao de lotes e historico”)
t1,t2,t3 = st.tabs([“Piquetes”,“Cadastrar”,“Alocar / Liberar”])
with t1:
pqs = listar_piquetes()
if pqs:
df_pq = pd.DataFrame(pqs, columns=[“ID”,“Fazenda”,“Nome”,“Area ha”,“Cap UA”])
st.dataframe(df_pq, use_container_width=True)
p1,p2 = st.columns(2)
p1.metric(“Total piquetes”, len(pqs))
p2.metric(“Area total (ha)”, f”{sum(p[3] for p in pqs):.1f}”)
dict_pq = {f”{p[2]} (ID {p[0]})”: p[0] for p in pqs}
sel_pq  = st.selectbox(“Historico do piquete”, list(dict_pq.keys()))
hist = historico_piquete(dict_pq[sel_pq])
if hist:
df_h = pd.DataFrame(hist, columns=[“ID”,“Lote”,“Entrada”,“Saida”])
st.dataframe(df_h, use_container_width=True)
else: st.info(“Nenhum historico.”)
else: st.info(“Nenhum piquete cadastrado.”)
with t2:
with st.form(“form_pq”):
pq1,pq2,pq3 = st.columns(3)
with pq1: nome_pq = st.text_input(“Nome *”)
with pq2: area_pq = st.number_input(“Area (ha)”, 0.0, step=0.5)
with pq3: cap_pq  = st.number_input(“Capacidade (UA)”, 0.0, step=1.0)
if st.form_submit_button(“Cadastrar”, type=“primary”):
if nome_pq:
adicionar_piquete(nome_pq, area_pq, cap_pq)
st.success(“Piquete cadastrado!”); st.rerun()
else: st.error(“Informe o nome.”)
with t3:
pqs   = listar_piquetes()
lotes = listar_lotes()
if not pqs or not lotes: st.warning(“Cadastre piquetes e lotes.”)
else:
dict_pq = {f”{p[2]} (ID {p[0]})”: p[0] for p in pqs}
dict_l  = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
al1,al2 = st.columns(2)
with al1:
st.subheader(“Alocar”)
with st.form(“form_aloc”):
pq_a  = st.selectbox(“Piquete”, list(dict_pq.keys()), key=“al_pq”)
lt_a  = st.selectbox(“Lote”,    list(dict_l.keys()),  key=“al_lt”)
dt_a  = st.date_input(“Entrada”,                      key=“al_dt”)
if st.form_submit_button(“Alocar”, type=“primary”):
alocar_lote_piquete(dict_pq[pq_a], dict_l[lt_a], str(dt_a))
st.success(“Alocado!”); st.rerun()
with al2:
st.subheader(“Liberar”)
with st.form(“form_lib”):
pq_l = st.selectbox(“Piquete”, list(dict_pq.keys()), key=“lib_pq”)
dt_l = st.date_input(“Saida”,                        key=“lib_dt”)
if st.form_submit_button(“Liberar”, type=“primary”):
liberar_piquete(dict_pq[pq_l], str(dt_l))
st.success(“Piquete liberado!”); st.rerun()

# ============================================================

# PREVISAO ABATE

# ============================================================

elif menu == “Previsao Abate”:
hdr(“Previsao Abate”, “Previsao de Abate”, “Data estimada e receita projetada por GMD”)
lote_id, _ = sel_lote(“abate_lote”)
if lote_id:
animais = listar_animais_por_lote(lote_id)
if not animais: st.warning(“Nenhum animal.”); st.stop()
preco_kg = st.number_input(“Preco de abate (R$/kg)”, 0.0, 100.0, 20.0)
st.info(“Defina o peso alvo em Prontuario do Animal para cada animal.”)
resultados = []
for a in animais:
prev = calcular_previsao_abate(a[0])
if “erro” not in prev:
resultados.append({“Animal”: a[1], “Peso Atual”: prev[“peso_atual”],
“Peso Alvo”: prev[“peso_alvo”], “GMD”: prev[“gmd”],
“Dias Rest.”: prev[“dias_restantes”], “Data Prevista”: prev[“data_prevista”],
“Receita Est.”: round(prev[“peso_alvo”]*preco_kg,2), “Confianca”: prev[“confianca”]})
if resultados:
df_prev = pd.DataFrame(resultados).sort_values(“Dias Rest.”)
st.dataframe(df_prev, use_container_width=True)
pr1,pr2 = st.columns(2)
pr1.metric(“Animais analisados”, len(resultados))
pr2.metric(“Receita total estimada”, f”R$ {sum(r[‘Receita Est.’] for r in resultados):,.2f}”)
st.bar_chart(df_prev.set_index(“Animal”)[“Dias Rest.”])
for r in resultados:
if r[“Dias Rest.”] == 0:   st.success(f”{r[‘Animal’]}: atingiu o peso alvo!”)
elif r[“Dias Rest.”] <= 15: st.warning(f”{r[‘Animal’]}: {r[‘Dias Rest.’]} dias - prepare o abate”)
else: st.info(“Nenhum animal com peso alvo e pesagens suficientes.”)

# ============================================================

# PRONTUARIO ANIMAL

# ============================================================

elif menu == “Prontuario Animal”:
hdr(“Prontuario Animal”, “Prontuario Completo”, “Historico de peso, saude e reproducao”)

```
# ── funcao de timeline ────────────────────────────────────────────────
def montar_timeline(animal_id, det):
    _pd2 = pd
    eventos = []

    # Pesagens
    ps = listar_pesagens(animal_id)
    if ps:
        df_p = _pd2.DataFrame(ps, columns=["id","aid","peso","data"])
        df_p["data"] = _pd2.to_datetime(df_p["data"])
        df_p = df_p.sort_values("data")
        for _, row in df_p.iterrows():
            eventos.append({
                "data": row["data"],
                "tipo": "pesagem",
                "icone": "scale",
                "titulo": f"Pesagem: {row['peso']:.1f} kg",
                "detalhe": "",
                "cor": "azul",
            })
        # GMD entre pesagens consecutivas
        for i in range(1, len(df_p)):
            dias = (df_p["data"].iloc[i] - df_p["data"].iloc[i-1]).days
            if dias > 0:
                gmd = (df_p["peso"].iloc[i] - df_p["peso"].iloc[i-1]) / dias
                if gmd < 0:
                    eventos.append({
                        "data": df_p["data"].iloc[i],
                        "tipo": "alerta_gmd",
                        "icone": "warning",
                        "titulo": f"Queda de GMD: {gmd:.3f} kg/dia",
                        "detalhe": "Perda de peso detectada",
                        "cor": "vermelho",
                    })
                elif gmd < 0.5:
                    eventos.append({
                        "data": df_p["data"].iloc[i],
                        "tipo": "alerta_gmd",
                        "icone": "warning",
                        "titulo": f"GMD baixo: {gmd:.3f} kg/dia",
                        "detalhe": "Desempenho abaixo do esperado",
                        "cor": "amarelo",
                    })

    # Ocorrencias
    ocs = listar_ocorrencias(animal_id)
    for o in ocs:
        cor_oc = "vermelho" if o[5]=="Alta" else "amarelo" if o[5]=="Media" else "azul_claro"
        eventos.append({
            "data": _pd2.to_datetime(o[2]),
            "tipo": "ocorrencia",
            "icone": "medical",
            "titulo": f"{o[3]}: {o[4][:40]}..." if len(o[4])>40 else f"{o[3]}: {o[4]}",
            "detalhe": f"Gravidade: {o[5]} | Custo: R$ {o[6]:.2f} | Status: {o[8]}",
            "cor": cor_oc,
        })

    # Vacinas realizadas
    try:
        lote_id_anim = det[3] if det else None
        if lote_id_anim:
            vacs = listar_vacinas_agenda(lote_id_anim)
            for v in vacs:
                if v[5] == "realizado" and v[4]:
                    eventos.append({
                        "data": _pd2.to_datetime(v[4]),
                        "tipo": "vacina",
                        "icone": "syringe",
                        "titulo": f"Vacina: {v[2]}",
                        "detalhe": "Realizada",
                        "cor": "verde",
                    })
    except Exception:
        pass

    # Reproducao
    repros = listar_reproducao(animal_id)
    for r in repros:
        if r[2]:
            eventos.append({
                "data": _pd2.to_datetime(r[2]),
                "tipo": "reproducao",
                "icone": "heart",
                "titulo": f"Cobertura {r[3]}",
                "detalhe": f"Resultado: {r[5]}",
                "cor": "roxo",
            })
        if r[7]:
            eventos.append({
                "data": _pd2.to_datetime(r[7]),
                "tipo": "parto",
                "icone": "baby",
                "titulo": "Parto realizado",
                "detalhe": f"Tipo: {r[3]}",
                "cor": "verde",
            })

    # Ordenar por data
    eventos.sort(key=lambda x: x["data"])
    return eventos

def render_timeline(eventos):
    if not eventos:
        st.info("Nenhum evento registrado para este animal.")
        return

    COR_MAP = {
        "azul":       ("#1565C0", "#E3F2FD", "Pesagem"),
        "verde":       ("#1B5E20", "#E8F5E9", "Vacina / Parto"),
        "vermelho":    ("#B71C1C", "#FFEBEE", "Alerta / Ocorrencia grave"),
        "amarelo":     ("#E65100", "#FFF3E0", "Alerta moderado"),
        "azul_claro":  ("#0277BD", "#E1F5FE", "Ocorrencia leve"),
        "roxo":        ("#4A148C", "#F3E5F5", "Reproducao"),
    }

    ICONE_MAP = {
        "scale":   "peso",
        "warning": "alerta",
        "medical": "ocorrencia",
        "syringe": "vacina",
        "heart":   "cobertura",
        "baby":    "parto",
    }

    html_parts = [
        "<style>",
        ".tl-wrap{padding:8px 0}",
        ".tl-item{display:flex;gap:12px;margin-bottom:4px;align-items:flex-start}",
        ".tl-line-col{display:flex;flex-direction:column;align-items:center;width:32px;flex-shrink:0}",
        ".tl-dot{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0}",
        ".tl-vline{width:2px;flex:1;min-height:16px;background:#E0E0E0;margin:2px 0}",
        ".tl-content{flex:1;border-radius:8px;padding:8px 12px;border-left:3px solid}",
        ".tl-date{font-size:11px;color:#888;margin-bottom:2px}",
        ".tl-title{font-size:13px;font-weight:600;margin:0}",
        ".tl-detail{font-size:11px;color:#666;margin-top:2px}",
        "</style>",
        "<div class='tl-wrap'>",
    ]

    for i, ev in enumerate(eventos):
        cor_key = ev["cor"]
        cor_borda, cor_fundo, _ = COR_MAP.get(cor_key, ("#555","#F5F5F5",""))
        data_str = ev["data"].strftime("%d/%m/%Y")
        icone_str = ICONE_MAP.get(ev["icone"], ev["icone"])[:2].upper()
        is_last = (i == len(eventos)-1)

        html_parts.append("<div class='tl-item'>")
        html_parts.append("<div class='tl-line-col'>")
        html_parts.append(f"<div class='tl-dot' style='background:{cor_fundo};color:{cor_borda};border:2px solid {cor_borda}'>{icone_str}</div>")
        if not is_last:
            html_parts.append("<div class='tl-vline'></div>")
        html_parts.append("</div>")
        html_parts.append(f"<div class='tl-content' style='background:{cor_fundo};border-color:{cor_borda}'>")
        html_parts.append(f"<div class='tl-date'>{data_str}</div>")
        html_parts.append(f"<div class='tl-title'>{ev['titulo']}</div>")
        if ev["detalhe"]:
            html_parts.append(f"<div class='tl-detail'>{ev['detalhe']}</div>")
        html_parts.append("</div>")
        html_parts.append("</div>")

    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

# ── selecao ───────────────────────────────────────────────────────────
lotes = listar_lotes()
if not lotes: st.warning("Nenhum lote.")
else:
    dict_l = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    pr1,pr2 = st.columns(2)
    with pr1: lote_s = st.selectbox("Lote", list(dict_l.keys()), key="pron_lote")
    animais = listar_animais_por_lote(dict_l[lote_s])
    if not animais: st.warning("Nenhum animal.")
    else:
        dict_a = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
        with pr2: anim_s = st.selectbox("Animal", list(dict_a.keys()), key="pron_anim")
        animal_id = dict_a[anim_s]
        det = obter_animal(animal_id)

        # Score e status rapido
        sc = calcular_score_saude(animal_id)
        car = verificar_carencia(animal_id)
        km1,km2,km3,km4 = st.columns(4)
        km1.metric("Score Saude", f"{sc['score']}/100")
        km2.metric("Classificacao", sc["classificacao"])
        km3.metric("Ocorrencias", sc["detalhes"]["n_ocorrencias"])
        km4.metric("Carencia", "Sim" if car["em_carencia"] else "Nao",
                   delta="Verificar abate" if car["em_carencia"] else None,
                   delta_color="inverse" if car["em_carencia"] else "normal")

        st.divider()

        t1,t2,t3,t4 = st.tabs(["Timeline","Dados","Pesagens","Ocorrencias"])

        with t1:
            st.subheader(f"Timeline clinica de {anim_s.split(' (ID')[0]}")
            st.caption("Todos os eventos do animal em ordem cronologica")

            # Legenda
            leg = st.columns(6)
            leg[0].markdown("<span style='color:#1565C0'>&#9679;</span> Pesagem", unsafe_allow_html=True)
            leg[1].markdown("<span style='color:#1B5E20'>&#9679;</span> Vacina/Parto", unsafe_allow_html=True)
            leg[2].markdown("<span style='color:#B71C1C'>&#9679;</span> Ocorr. grave", unsafe_allow_html=True)
            leg[3].markdown("<span style='color:#E65100'>&#9679;</span> Alerta", unsafe_allow_html=True)
            leg[4].markdown("<span style='color:#0277BD'>&#9679;</span> Ocorr. leve", unsafe_allow_html=True)
            leg[5].markdown("<span style='color:#4A148C'>&#9679;</span> Reproducao", unsafe_allow_html=True)

            st.divider()
            eventos = montar_timeline(animal_id, det)
            render_timeline(eventos)

            if eventos:
                st.caption(f"Total: {len(eventos)} eventos registrados")

        with t2:
            with st.form("form_pron"):
                d1,d2 = st.columns(2)
                with d1:
                    peso_alvo = st.number_input("Peso alvo abate (kg)", 0.0, 1000.0, float(det[7]) if det else 0.0)
                    raca_p    = st.text_input("Raca", value=det[5] if det else "")
                with d2:
                    obs_p = st.text_area("Observacoes clinicas", value=det[8] if det else "", height=100)
                if st.form_submit_button("Salvar", type="primary"):
                    atualizar_animal_detalhes(animal_id, peso_alvo=peso_alvo, observacoes=obs_p)
                    st.success("Prontuario atualizado!"); st.rerun()
            if det and det[7] > 0:
                prev = calcular_previsao_abate(animal_id)
                if "erro" not in prev:
                    st.divider()
                    st.subheader("Previsao de Abate")
                    pv1,pv2,pv3 = st.columns(3)
                    pv1.metric("GMD", f"{prev['gmd']:.3f} kg/dia")
                    pv2.metric("Dias restantes", prev["dias_restantes"])
                    pv3.metric("Data prevista", prev["data_prevista"])

        with t3:
            ps = listar_pesagens(animal_id)
            if ps:
                df_p = pd.DataFrame(ps, columns=["ID","Animal","Peso","Data"])
                df_p["Data"] = pd.to_datetime(df_p["Data"])
                df_p = df_p.sort_values("Data")
                st.line_chart(df_p.set_index("Data")["Peso"])
                st.dataframe(df_p[["Data","Peso"]].rename(columns={"Peso":"Peso (kg)"}), use_container_width=True)
            else: st.info("Sem pesagens.")

        with t4:
            ocs = listar_ocorrencias(animal_id)
            if ocs:
                df_oc = pd.DataFrame(ocs, columns=["ID","Animal","Data","Tipo","Desc","Grav","Custo","Dias","Status"])
                df_oc["Data"] = pd.to_datetime(df_oc["Data"])
                st.dataframe(df_oc[["Data","Tipo","Grav","Desc","Custo","Status"]], use_container_width=True)
                st.metric("Custo total tratamentos", f"R$ {sum(o[6] for o in ocs if o[6]):.2f}")
            else: st.success("Nenhuma ocorrencia registrada.")
            repros = listar_reproducao(animal_id)
            if repros:
                st.subheader("Historico Reprodutivo")
                df_r = pd.DataFrame(repros, columns=["ID","Animal","Cio","Tipo","Diag","Result","Parto Prev","Parto Real","Obs"])
                st.dataframe(df_r[["Cio","Tipo","Result","Parto Prev","Parto Real"]], use_container_width=True)
```

# ============================================================

# MARGEM REAL

# ============================================================

elif menu == “Margem Real”:
hdr(“Margem Real”, “Margem Real do Lote”, “Resultado: compra x venda x custos”)
lote_id, _ = sel_lote(“margem_lote”)
if lote_id:
t1,t2 = st.tabs([“Resultado”,“Registrar Venda”])
with t1:
mg = calcular_margem_lote(lote_id)
if mg:
if not mg[“venda_registrada”]: st.info(“Registre uma venda na aba ao lado para ver a margem real.”)
m1,m2,m3 = st.columns(3)
m1.metric(“Custo de compra”,  f”R$ {mg[‘custo_compra’]:,.2f}”)
m2.metric(“Receita real”,      f”R$ {mg[‘receita_real’]:,.2f}”)
m3.metric(“Custo sanitario”,   f”R$ {mg[‘custo_sanitario’]:,.2f}”)
st.metric(“Margem liquida”, f”R$ {mg[‘margem’]:,.2f}”, delta=f”{mg[‘margem_pct’]:.1f}%”,
delta_color=“normal” if mg[“margem”]>=0 else “inverse”)
if mg[“venda_registrada”]:
st.success(f”Frigorifico: {mg[‘frigorific’]} | Venda: {mg[‘data_venda’]}”)
vendas = listar_vendas_lote(lote_id)
if vendas:
df_v = pd.DataFrame(vendas, columns=[“ID”,“Lote”,“Data”,“R$/kg”,“Peso kg”,“Frigorifico”,“Obs”])
st.dataframe(df_v, use_container_width=True)
with t2:
with st.form(“form_venda”):
v1,v2 = st.columns(2)
with v1:
data_v  = st.date_input(“Data venda”)
pr_kg   = st.number_input(“Preco de venda (R$/kg)”, 0.0, 100.0, 22.0)
with v2:
peso_v  = st.number_input(“Peso total vendido (kg)”, 0.0)
frig_v  = st.text_input(“Frigorifico”)
obs_v   = st.text_area(“Observacao”)
if st.form_submit_button(“Registrar Venda”, type=“primary”):
if peso_v > 0:
registrar_venda_lote(lote_id, str(data_v), pr_kg, peso_v, frig_v, obs_v)
registrar_auditoria(u[“id”], “venda_lote”, “vendas”, lote_id, f”R${pr_kg}/kg {peso_v}kg”)
st.success(“Venda registrada!”); st.rerun()
else: st.error(“Informe o peso total.”)

# ============================================================

# COTACAO CEPEA

# ============================================================

elif menu == “Cotacao Cepea”:
hdr(“Cotacao Cepea”, “Cotacao Boi Gordo”, “Preco do boi gordo ESALQ/Cepea”)
c1,c2 = st.columns([2,1])
with c1:
if st.button(“Buscar cotacao atual”):
if _CEPEA:
from cepea import buscar_cotacao_cepea
with st.spinner(“Buscando…”):
res = buscar_cotacao_cepea()
if res[“sucesso”]:
salvar_cotacao(res[“data”], res[“preco”], res[“fonte”])
st.success(f”R$ {res[‘preco’]:.2f}/@ - {res[‘data’]}”)
else:
st.warning(f”Indisponivel: {res[‘msg’]}”)
else: st.warning(“cepea.py nao encontrado.”)
with c2:
with st.form(“form_cot_m”):
dt_c = st.date_input(“Data”)
pr_c = st.number_input(“Preco (R$/@)”, 0.0, 1000.0, 195.0)
if st.form_submit_button(“Salvar manual”):
salvar_cotacao(str(dt_c), pr_c, “manual”)
st.success(“Salvo!”); st.rerun()
cots = listar_cotacoes(0)
if cots:
ult = cots[-1]
st.metric(“Ultima cotacao”, f”R$ {ult[2]:.2f}/@”, delta=f”{ult[1]} ({ult[3]})”)
hist = historico_grafico(cots[-60:])
if hist[“datas”]:
df_cot = pd.DataFrame({“Data”:hist[“datas”],“Preco R$/@”:hist[“precos”]}).set_index(“Data”)
st.line_chart(df_cot)
else:
st.info(“Nenhuma cotacao. Insira manualmente ou clique em buscar.”)

# ============================================================

# RASTREABILIDADE GTA

# ============================================================

elif menu == “Rastreabilidade GTA”:
hdr(“Rastreabilidade GTA”, “GTA e SISBOV”, “Guia de Transito Animal e certificacao”)
t1,t2,t3 = st.tabs([“GTAs”,“Emitir GTA”,“SISBOV”])
with t1:
gtas = listar_gta()
if gtas:
df_g = pd.DataFrame(gtas, columns=[“ID”,“Lote ID”,“Lote”,“Num GTA”,“Emissao”,“Origem”,“Destino”,“Qtd”,“Finalidade”,“Obs”])
st.dataframe(df_g, use_container_width=True)
else: st.info(“Nenhuma GTA.”)
with t2:
lotes = listar_lotes()
if not lotes: st.warning(“Cadastre um lote.”)
else:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
with st.form(“form_gta”):
g1,g2 = st.columns(2)
with g1:
lote_g  = st.selectbox(“Lote”, list(dict_l.keys()))
num_g   = st.text_input(“Numero GTA *”)
data_g  = st.date_input(“Data emissao”)
qtd_g   = st.number_input(“Quantidade animais”, 1, step=1)
with g2:
orig_g  = st.text_input(“Origem *”)
dest_g  = st.text_input(“Destino *”)
fin_g   = st.selectbox(“Finalidade”, [“Abate”,“Venda”,“Recria”,“Engorda”,“Reproducao”])
obs_g   = st.text_area(“Observacao”)
if st.form_submit_button(“Registrar GTA”, type=“primary”):
if num_g and orig_g and dest_g:
registrar_gta(dict_l[lote_g], num_g, str(data_g), orig_g, dest_g, int(qtd_g), fin_g, obs_g)
registrar_auditoria(u[“id”], “gta”, “gta”, dict_l[lote_g], num_g)
st.success(“GTA registrada!”); st.rerun()
else: st.error(“Preencha numero, origem e destino.”)
with t3:
lotes = listar_lotes()
if lotes:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
s1,s2 = st.columns(2)
with s1: lote_s = st.selectbox(“Lote”, list(dict_l.keys()), key=“sib_lote”)
anim_s = listar_animais_por_lote(dict_l[lote_s])
if anim_s:
dict_as = {f”{a[1]} (ID {a[0]})”: a[0] for a in anim_s}
with s2: anim_ss = st.selectbox(“Animal”, list(dict_as.keys()), key=“sib_anim”)
aid_s = dict_as[anim_ss]
sb = obter_sisbov(aid_s)
if sb: st.success(f”SISBOV: **{sb[2]}** - {sb[3]}”)
else:  st.info(“Sem SISBOV.”)
with st.form(“form_sib”):
num_sb = st.text_input(“Numero SISBOV (15 digitos)”)
dt_sb  = st.date_input(“Data certificacao”)
if st.form_submit_button(“Cadastrar”, type=“primary”):
if len(num_sb) == 15:
registrar_sisbov(aid_s, num_sb, str(dt_sb))
st.success(“SISBOV cadastrado!”); st.rerun()
else: st.error(“SISBOV deve ter 15 digitos.”)

# ============================================================

# EXPORTAR RELATORIOS

# ============================================================

elif menu == “Exportar Relatorios”:
hdr(“Exportar Relatorios”, “Relatorios”, “PDF e Excel do lote, sanitario e estoque”)
lote_id, _ = sel_lote(“exp_lote”)
if lote_id:
lote = obter_lote(lote_id)
nome_lote = lote[1] if lote else “lote”
animais = listar_animais_por_lote(lote_id)
pd_dict = {a[0]: listar_pesagens(a[0])    for a in animais}
oc_dict = {a[0]: listar_ocorrencias(a[0]) for a in animais}
c1,c2 = st.columns(2)
with c1:
st.subheader(“Excel do Lote”)
st.write(“Abas: Resumo, Animais, Pesagens, Ocorrencias”)
if *EXP:
xls = gerar_excel_lote(nome_lote, animais, pd_dict, oc_dict)
st.download_button(
label=“Baixar Excel”,
data=xls,
file_name=f”lote*{nome_lote.replace(’ ‘,’*’)}.xlsx”,
mime=“application/vnd.openxmlformats-officedocument.spreadsheetml.sheet”,
key=“dl_xls_lote”,
)
else: st.warning(“exports.py nao encontrado.”)
with c2:
st.subheader(“PDF do Lote”)
if *EXP:
df_anim = pd.DataFrame(animais, columns=[“ID”,“Identificacao”,“Idade”,“Lote ID”])
todos_p = [p for ps in pd_dict.values() for p in ps]
df_peso = pd.DataFrame(todos_p, columns=[“ID”,“Animal ID”,“Peso”,“Data”]) if todos_p else pd.DataFrame()
todos_o = [o for os in oc_dict.values() for o in os]
df_oc   = pd.DataFrame(todos_o, columns=[“ID”,“Animal”,“Data”,“Tipo”,“Desc”,“Grav”,“Custo”,“Dias”,“Status”]) if todos_o else pd.DataFrame()
secoes  = [{“titulo”:“Animais”,“df”:df_anim},{“titulo”:“Pesagens”,“df”:df_peso},{“titulo”:“Ocorrencias”,“df”:df_oc}]
pdf = gerar_pdf_relatorio(f”Relatorio {nome_lote}”, secoes)
st.download_button(
label=“Baixar PDF”,
data=pdf,
file_name=f”relatorio*{nome_lote.replace(’ ‘,’*’)}.pdf”,
mime=“application/pdf”,
key=“dl_pdf_lote”,
)
else: st.warning(“exports.py nao encontrado.”)
st.divider()
st.subheader(“Excel Sanitario”)
if _EXP:
vacs = listar_vacinas_agenda()
meds = listar_medicamentos()
xls2 = gerar_excel_sanitario(vacs, meds)
st.download_button(
label=“Baixar Excel Sanitario”,
data=xls2,
file_name=“sanitario.xlsx”,
mime=“application/vnd.openxmlformats-officedocument.spreadsheetml.sheet”,
key=“dl_xls_san”,
)

# ============================================================

# BACKUP

# ============================================================

elif menu == “Backup”:
hdr(“Backup”, “Backup do Sistema”, “Download dos seus dados”)
import database as _dbm
db_path = _dbm.DB_PATH
st.info(f”Banco: `{db_path}`”)
c1,c2 = st.columns(2)
with c1:
st.subheader(“Download ZIP (CSVs)”)
if _BACKUP:
with st.spinner(“Preparando…”):
dados_zip = gerar_backup_zip(db_path)
nome_zip = nome_arquivo_backup(“zip”)
st.download_button(“Baixar ZIP”, dados_zip, nome_zip, “application/zip”, key=“dl_bkp_zip”)
registrar_auditoria(u[“id”], “backup_zip”, “sistema”, None, nome_zip)
else: st.warning(“backup.py nao encontrado.”)
with c2:
st.subheader(“Download SQLite”)
if _BACKUP:
with st.spinner(“Preparando…”):
dados_db = gerar_backup_sqlite(db_path)
nome_db = nome_arquivo_backup(“db”)
st.download_button(“Baixar SQLite”, dados_db, nome_db, “application/octet-stream”, key=“dl_bkp_db”)
else: st.warning(“backup.py nao encontrado.”)

# ============================================================

# NOTIFICACOES

# ============================================================

elif menu == “Notificacoes”:
hdr(“Notificacoes”, “Central de Notificacoes”, “Alertas por e-mail”)
if not email_configurado():
st.warning(“E-mail nao configurado.”)
st.markdown(”””
**Para configurar:** crie `.streamlit/secrets.toml` com:

```
[email]
smtp_host     = smtp.gmail.com
smtp_port     = 587
smtp_user     = seu@gmail.com
smtp_password = senha_app
remetente     = Gestao Pecuaria <seu@gmail.com>
```

Use **Senha de App** do Google (nao a senha da conta).
“””)
else:
st.success(“E-mail configurado.”)
c1,c2 = st.columns(2)
with c1:
st.metric(“Vacinas pendentes”, len(pend))
if pend and st.button(“Enviar alerta vacinas”):
vs = [{“lote”:v[2],“vacina”:v[3],“data_prevista”:v[4]} for v in pend]
ok, msg = email_vacina_pendente(u[“email”], u[“nome”], vs)
st.success(msg) if ok else st.error(msg)
st.metric(“Partos previstos”, len(parto))
if parto and st.button(“Enviar alerta partos”):
pts = [{“animal”:p[1],“lote”:p[2],“data_parto_previsto”:p[3]} for p in parto]
ok, msg = email_parto_previsto(u[“email”], u[“nome”], pts)
st.success(msg) if ok else st.error(msg)
with c2:
st.metric(“Medicamentos criticos”, len(crit))
if crit and st.button(“Enviar alerta meds”):
meds = [{“nome”:m[1],“estoque_atual”:m[3],“unidade”:m[2],“validade”:m[5] or “”} for m in crit]
ok, msg = email_medicamento_critico(u[“email”], u[“nome”], meds)
st.success(msg) if ok else st.error(msg)
if u[“perfil”] == “admin”:
st.divider()
st.subheader(“Gestao de Planos”)
usuarios = listar_usuarios()
if usuarios:
df_u = pd.DataFrame(usuarios, columns=[“ID”,“Nome”,“Email”,“Perfil”,“Fazenda”])
st.dataframe(df_u, use_container_width=True)
with st.form(“form_conv”):
uid_c = st.number_input(“ID usuario para converter para PAGO”, 1, step=1)
if st.form_submit_button(“Converter para pago”):
converter_para_pago(int(uid_c))
st.success(f”Usuario {uid_c} convertido!”); st.rerun()

# ============================================================

# LOG AUDITORIA

# ============================================================

elif menu == “Log Auditoria”:
hdr(“Log Auditoria”, “Log de Auditoria”, “Historico de acoes por usuario”)
if u[“perfil”] != “admin”:
st.warning(“Acesso restrito a administradores.”)
else:
c1,c2 = st.columns(2)
lim   = c1.slider(“Ultimos registros”, 10, 500, 100)
usuarios = listar_usuarios()
dict_us  = {“Todos”: None, **{f”{x[1]} (ID {x[0]})”: x[0] for x in usuarios}}
uf       = c2.selectbox(“Filtrar usuario”, list(dict_us.keys()))
logs = listar_auditoria(lim, dict_us[uf])
if logs:
df_log = pd.DataFrame(logs, columns=[“ID”,“Usuario”,“Acao”,“Tabela”,“Reg ID”,“Detalhe”,“Data/Hora”])
st.dataframe(df_log, use_container_width=True)
st.metric(“Total registros”, len(logs))
else: st.info(“Nenhum registro.”)

# ============================================================

# ADMINISTRACAO

# ============================================================

elif menu == “Administracao”:
hdr(“Administracao”, “Administracao”, “Usuarios, planos e configuracoes”)
is_admin = u[“perfil”] == “admin”
t1,t2 = st.tabs([“Usuarios”,“Alterar Senha”])
with t1:
if not is_admin: st.warning(“Acesso restrito a administradores.”)
else:
usuarios = listar_usuarios()
if usuarios:
df_u = pd.DataFrame(usuarios, columns=[“ID”,“Nome”,“Email”,“Perfil”,“Fazenda”])
st.dataframe(df_u, use_container_width=True)
st.subheader(“Criar usuario”)
with st.form(“form_user”):
au1,au2 = st.columns(2)
with au1:
n_nome  = st.text_input(“Nome”)
n_email = st.text_input(“Email”)
with au2:
n_senha = st.text_input(“Senha”, type=“password”)
n_perf  = st.selectbox(“Perfil”, [“fazendeiro”,“veterinario”,“admin”])
if st.form_submit_button(“Criar”, type=“primary”):
if n_nome and n_email and n_senha:
try:
uid_n = criar_usuario(n_nome, n_email, n_senha, n_perf)
ativar_trial(uid_n)
st.success(“Usuario criado!”); st.rerun()
except Exception: st.error(“Email ja cadastrado.”)
else: st.error(“Preencha todos os campos.”)
with t2:
with st.form(“form_senha”):
senha_a = st.text_input(“Senha atual”, type=“password”)
nova_s  = st.text_input(“Nova senha”, type=“password”)
conf_s  = st.text_input(“Confirmar”, type=“password”)
if st.form_submit_button(“Alterar”, type=“primary”):
if not autenticar_usuario(u[“email”], senha_a): st.error(“Senha atual incorreta.”)
elif nova_s != conf_s:                          st.error(“Senhas nao coincidem.”)
elif len(nova_s) < 6:                          st.error(“Minimo 6 caracteres.”)
else:
alterar_senha(u[“id”], nova_s)
st.success(“Senha alterada!”)

# ============================================================

# EDITAR LOTE

# ============================================================

elif menu == “Editar Lote”:
hdr(“Editar Lote”, “Editar / Excluir Lote”, “Altere ou remova um lote cadastrado”)

```
# Botao de sincronizacao em massa (corrige dados historicos)
with st.expander("Corrigir contagem de animais em todos os lotes"):
    st.caption("Use este botao se a quantidade de animais exibida estiver incorreta.")
    if st.button("Sincronizar todos os lotes agora", key="sync_todos"):
        resultados = sincronizar_todos_lotes()
        for lid_s, nome_s, n_s in resultados:
            st.write(f"Lote **{nome_s}**: {n_s} animais ativos")
        st.success("Contagens atualizadas com sucesso!")
        st.rerun()

lotes = listar_lotes()
if not lotes:
    st.warning("Nenhum lote cadastrado.")
else:
    dict_l  = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
    lote_sel = st.selectbox("Selecione o lote para editar", list(dict_l.keys()), key="ed_lote")
    lote_id  = dict_l[lote_sel]
    lote     = obter_lote(lote_id)
    rs       = resumo_lote(lote_id)

    # Resumo do lote
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Animais ativos", rs["ativos"])
    k2.metric("Ocorrencias",    rs["ocorrencias"])
    k3.metric("Mortes",         rs["mortos"])
    k4.metric("GTAs emitidas",  rs["gtas_emitidas"])
    st.divider()

    # Contagem real de animais ativos (fonte da verdade)
    ativos_reais = rs["ativos"]
    st.info(f"Animais ativos no banco: **{ativos_reais}** (calculado automaticamente a partir dos cadastros)")

    tab_edit, tab_del = st.tabs(["Editar dados", "Excluir lote"])

    with tab_edit:
        with st.form("form_edit_lote"):
            el1,el2 = st.columns(2)
            with el1:
                nome_e     = st.text_input("Nome *",          value=lote[1])
                data_e     = st.date_input("Data entrada",    value=pd.to_datetime(lote[3]).date())
                qtd_comp_e = st.number_input("Qtd comprada",  0, step=1, value=int(lote[4]))
                transp_e   = st.text_input("Transportadora",  value=lote[6] or "")
            with el2:
                desc_e     = st.text_area("Descricao",        value=lote[2] or "", height=70)
                st.caption(f"Qtd recebida atual: {ativos_reais} animais ativos (atualizado automaticamente)")
                preco_e    = st.number_input("Preco por animal (R$)", 0.0, step=50.0)
            salvar_e = st.form_submit_button("Salvar alteracoes", type="primary", use_container_width=True)
        if salvar_e:
            if not nome_e:
                st.error("Informe o nome do lote.")
            else:
                # qtd_recebida e sempre recalculada pelos animais ativos reais
                atualizar_lote(lote_id, nome_e, desc_e, str(data_e), qtd_comp_e, ativos_reais, transp_e, preco_e)
                registrar_auditoria(u["id"], "editar_lote", "lotes", lote_id, nome_e)
                st.success(f"Lote **{nome_e}** atualizado! Animais ativos: {ativos_reais}")
                st.rerun()

    with tab_del:
        st.warning("A exclusao e permanente e nao pode ser desfeita.")
        n_anim = contar_animais_no_lote(lote_id, incluir_inativos=True)
        if n_anim > 0:
            st.error(f"Impossivel excluir: este lote tem {n_anim} animal(is) cadastrado(s).")
            st.info("Exclua ou transfira todos os animais antes de remover o lote.")
        else:
            confirma = st.checkbox("Confirmo que desejo excluir este lote permanentemente")
            if confirma:
                if st.button("Excluir lote definitivamente", type="primary"):
                    excluir_lote(lote_id)
                    registrar_auditoria(u["id"], "excluir_lote", "lotes", lote_id, lote[1])
                    st.success("Lote excluido com sucesso.")
                    st.rerun()
```

# ============================================================

# EDITAR ANIMAL

# ============================================================

elif menu == “Editar Animal”:
hdr(“Editar Animal”, “Editar / Excluir Animal”, “Altere ou remova um animal cadastrado”)
lotes = listar_lotes()
if not lotes:
st.warning(“Nenhum lote cadastrado.”)
else:
dict_l = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
ea1,ea2 = st.columns(2)
with ea1: lote_sel = st.selectbox(“Lote”, list(dict_l.keys()), key=“ea_lote”)
lote_id  = dict_l[lote_sel]
# Mostrar todos incluindo inativos para poder editar
animais  = listar_animais_por_lote(lote_id, incluir_inativos=True)
if not animais:
st.warning(“Nenhum animal neste lote.”)
else:
dict_a = {f”{a[1]} (ID {a[0]})”: a[0] for a in animais}
with ea2: anim_sel = st.selectbox(“Animal”, list(dict_a.keys()), key=“ea_anim”)
animal_id = dict_a[anim_sel]
det = obter_animal(animal_id)

```
        # Indicadores do animal
        n_pes = len(listar_pesagens(animal_id))
        n_ocs = len(listar_ocorrencias(animal_id))
        sc    = calcular_score_saude(animal_id)
        i1,i2,i3 = st.columns(3)
        i1.metric("Pesagens",     n_pes)
        i2.metric("Ocorrencias",  n_ocs)
        i3.metric("Score saude",  f"{sc['score']}/100")
        st.divider()

        tab_edit, tab_del = st.tabs(["Editar dados", "Excluir animal"])

        with tab_edit:
            with st.form("form_edit_animal"):
                eab1,eab2 = st.columns(2)
                with eab1:
                    ident_e  = st.text_input("Identificacao / Brinco *", value=det[1] if det else "")
                    idade_e  = st.number_input("Idade (meses)", 0, 240, value=int(det[2]) if det else 0)
                    raca_e   = st.text_input("Raca", value=det[5] if det else "")
                with eab2:
                    p_alvo_e = st.number_input("Peso alvo abate (kg)", 0.0, value=float(det[7]) if det else 0.0)
                    sexo_e   = st.selectbox("Sexo", ["indefinido","macho","femea"],
                                             index=["indefinido","macho","femea"].index(det[4])
                                             if det and det[4] in ["indefinido","macho","femea"] else 0)
                    obs_e    = st.text_area("Observacoes", value=det[8] if det else "", height=68)
                salvar_ea = st.form_submit_button("Salvar alteracoes", type="primary", use_container_width=True)
            if salvar_ea:
                if not ident_e:
                    st.error("Informe a identificacao.")
                else:
                    atualizar_animal(animal_id, ident_e, idade_e)
                    atualizar_animal_detalhes(animal_id,
                                              peso_alvo=p_alvo_e if p_alvo_e > 0 else None,
                                              observacoes=obs_e)
                    registrar_auditoria(u["id"], "editar_animal", "animais", animal_id, ident_e)
                    st.success(f"Animal **{ident_e}** atualizado!")
                    st.rerun()

        with tab_del:
            st.warning("A exclusao remove o animal e todo seu historico.")
            st.caption(f"Este animal tem {n_pes} pesagem(ns) e {n_ocs} ocorrencia(s).")
            confirma_a = st.checkbox("Confirmo a exclusao permanente deste animal")
            if confirma_a:
                if st.button("Excluir animal definitivamente", type="primary"):
                    excluir_animal(animal_id)
                    registrar_auditoria(u["id"], "excluir_animal", "animais", animal_id, det[1] if det else "")
                    st.success("Animal excluido.")
                    st.rerun()
```

# ============================================================

# EDITAR PESAGENS

# ============================================================

elif menu == “Editar Pesagens”:
hdr(“Editar Pesagens”, “Corrigir Pesagens”, “Edite ou exclua pesagens incorretas”)
lotes = listar_lotes()
if not lotes:
st.warning(“Nenhum lote cadastrado.”)
else:
dict_l  = {f”{l[1]} (ID {l[0]})”: l[0] for l in lotes}
ep1,ep2 = st.columns(2)
with ep1: lote_sel = st.selectbox(“Lote”, list(dict_l.keys()), key=“ep_lote”)
lote_id  = dict_l[lote_sel]
animais  = listar_animais_por_lote(lote_id)

```
    if not animais:
        st.warning("Nenhum animal neste lote.")
    else:
        modo = st.radio("Visualizar", ["Todas do lote","Por animal"], horizontal=True)

        if modo == "Por animal":
            dict_a = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
            with ep2: anim_sel = st.selectbox("Animal", list(dict_a.keys()), key="ep_anim")
            pesagens = listar_pesagens(dict_a[anim_sel])
        else:
            pesagens_raw = listar_pesagens_lote(lote_id)
            pesagens     = [(r[0], r[4], r[2], r[3]) for r in pesagens_raw]
            nomes_map    = {r[4]: r[1] for r in pesagens_raw}

        if not pesagens:
            st.info("Nenhuma pesagem registrada.")
        else:
            # Tabela visual
            df_ps = pd.DataFrame(pesagens, columns=["ID","Animal ID","Peso (kg)","Data"])
            if modo == "Todas do lote" and "nomes_map" in dir():
                df_ps["Animal"] = df_ps["Animal ID"].map(nomes_map)
                df_ps = df_ps[["ID","Animal","Peso (kg)","Data"]]
            df_ps["Data"] = pd.to_datetime(df_ps["Data"]).dt.strftime("%d/%m/%Y")
            st.dataframe(df_ps, use_container_width=True)

            st.divider()
            st.subheader("Selecionar pesagem para editar")
            dict_pes = {f"ID {p[0]} | {pd.to_datetime(p[3]).strftime('%d/%m/%Y')} | {p[2]:.1f} kg": p[0]
                        for p in pesagens}
            pes_sel  = st.selectbox("Pesagem", list(dict_pes.keys()), key="ep_pes")
            pes_id   = dict_pes[pes_sel]
            pes_cur  = next((p for p in pesagens if p[0]==pes_id), None)

            tab_edit_p, tab_del_p = st.tabs(["Corrigir", "Excluir"])

            with tab_edit_p:
                with st.form("form_edit_pes"):
                    fe1,fe2 = st.columns(2)
                    with fe1:
                        peso_novo = st.number_input("Peso (kg) *", 0.0, 1000.0,
                                                     value=float(pes_cur[2]) if pes_cur else 0.0,
                                                     step=0.5)
                    with fe2:
                        data_nova = st.date_input("Data",
                                                   value=pd.to_datetime(pes_cur[3]).date() if pes_cur else date.today())
                    if st.form_submit_button("Salvar correcao", type="primary", use_container_width=True):
                        if peso_novo <= 0:       st.error("Peso invalido.")
                        elif peso_novo > 1000:   st.error("Peso muito alto.")
                        else:
                            atualizar_pesagem(pes_id, peso_novo, str(data_nova))
                            registrar_auditoria(u["id"], "editar_pesagem", "pesagens", pes_id,
                                                f"{peso_novo}kg em {data_nova}")
                            st.success("Pesagem corrigida!")
                            st.rerun()

            with tab_del_p:
                if pes_cur:
                    st.warning(f"Excluir pesagem de {pes_cur[2]:.1f} kg registrada em {pd.to_datetime(pes_cur[3]).strftime('%d/%m/%Y')}?")
                confirma_p = st.checkbox("Confirmo a exclusao desta pesagem")
                if confirma_p:
                    if st.button("Excluir pesagem", type="primary"):
                        excluir_pesagem(pes_id)
                        registrar_auditoria(u["id"], "excluir_pesagem", "pesagens", pes_id, "excluido")
                        st.success("Pesagem excluida.")
                        st.rerun()
```

# ============================================================

# GERENCIAR OCORRENCIAS

# ============================================================

elif menu == “Gerenciar Ocorrencias”:
hdr(“Gerenciar Ocorrencias”, “Tratamentos e Ocorrencias”, “Edite ocorrencias e resolva tratamentos pendentes”)

```
# ── Painel de alertas de tratamentos vencidos ──────────────────────
vencidos = listar_tratamentos_vencidos()
if vencidos:
    st.error(f"ATENCAO: {len(vencidos)} tratamento(s) com prazo vencido!")
    with st.expander(f"Ver {len(vencidos)} tratamento(s) vencido(s)", expanded=True):
        for v in vencidos:
            try:
                prev_alta  = pd.to_datetime(v[10]).date()
                dias_atraso = (date.today() - prev_alta).days
            except Exception:
                dias_atraso = 0
            c1,c2,c3,c4 = st.columns([2,2,1,2])
            c1.write(f"**{v[2]}**")
            c2.write(f"Lote: {v[3]}")
            c3.write(f"Tipo: {v[5]}")
            c4.write(f"Vencido ha {dias_atraso} dia(s)")
else:
    st.success("Nenhum tratamento com prazo vencido.")

st.divider()

# ── Selecao ────────────────────────────────────────────────────────
lotes = listar_lotes()
if not lotes:
    st.warning("Nenhum lote cadastrado.")
    st.stop()

dict_l   = {f"{l[1]} (ID {l[0]})": l[0] for l in lotes}
go1,go2  = st.columns(2)
with go1: lote_sel = st.selectbox("Lote", list(dict_l.keys()), key="go_lote")
lote_id  = dict_l[lote_sel]
animais  = listar_animais_por_lote(lote_id)

if not animais:
    st.warning("Nenhum animal neste lote.")
    st.stop()

dict_a   = {f"{a[1]} (ID {a[0]})": a[0] for a in animais}
with go2: anim_sel = st.selectbox("Animal", list(dict_a.keys()), key="go_anim")
animal_id = dict_a[anim_sel]
ocs = listar_ocorrencias(animal_id)

if not ocs:
    st.info("Nenhuma ocorrencia registrada para este animal.")
    st.stop()

# ── Cards de status ────────────────────────────────────────────────
st.subheader(f"Ocorrencias de {anim_sel.split(' (ID')[0]}")

em_trat  = [o for o in ocs if o[8] == "Em tratamento"]
resolvidas = [o for o in ocs if o[8] == "Resolvido"]

r1,r2,r3 = st.columns(3)
r1.metric("Total",         len(ocs))
r2.metric("Em tratamento", len(em_trat),
          delta="Atencao" if em_trat else None,
          delta_color="inverse" if em_trat else "normal")
r3.metric("Resolvidas",    len(resolvidas))

st.divider()

for oc in ocs:
    oc_id, _, data_oc, tipo_oc, desc_oc, grav_oc, custo_oc, dias_oc, stat_oc = oc
    try:
        prev_alta   = (pd.to_datetime(data_oc) + pd.Timedelta(days=int(dias_oc or 0))).date()
        dias_rest   = (prev_alta - date.today()).days
        atraso      = max(0, -dias_rest) if stat_oc == "Em tratamento" else 0
    except Exception:
        prev_alta = None; dias_rest = 0; atraso = 0

    if stat_oc == "Resolvido":
        ic = "Resolvido"
        st.success(f"{ic} | {data_oc} | {tipo_oc} | Grav: {grav_oc} | {desc_oc[:60]}")
    elif atraso > 0:
        ic = f"VENCIDO ha {atraso} dia(s)"
        st.error(f"{ic} | {data_oc} | {tipo_oc} | Prev. alta: {prev_alta} | {desc_oc[:60]}")
    else:
        ic = f"Em tratamento | faltam {dias_rest}d"
        st.warning(f"{ic} | {data_oc} | {tipo_oc} | Prev. alta: {prev_alta} | {desc_oc[:60]}")

st.divider()
st.subheader("Selecionar ocorrencia para editar")

dict_oc = {}
for oc in ocs:
    label = f"ID {oc[0]} | {oc[2]} | {oc[3]} | {oc[8]}"
    dict_oc[label] = oc[0]

oc_sel  = st.selectbox("Ocorrencia", list(dict_oc.keys()), key="go_oc_sel")
oc_id   = dict_oc[oc_sel]
oc_cur  = next((o for o in ocs if o[0]==oc_id), None)

if oc_cur:
    stat_cur = oc_cur[8]
    is_resolv = (stat_cur == "Resolvido")

    if is_resolv:
        st.info("Esta ocorrencia esta resolvida. Voce pode editar os dados mas nao pode reabrir o tratamento.")

    tab_edit_o, tab_del_o = st.tabs(["Editar ocorrencia", "Excluir"])

    with tab_edit_o:
        with st.form("form_edit_oc"):
            oe1,oe2,oe3 = st.columns(3)
            with oe1:
                data_oe = st.date_input("Data",    value=pd.to_datetime(oc_cur[2]).date())
                tipo_oe = st.selectbox("Tipo",     ["Doenca","Lesao","Medicamento","Outros"],
                                        index=["Doenca","Lesao","Medicamento","Outros"].index(oc_cur[3])
                                        if oc_cur[3] in ["Doenca","Lesao","Medicamento","Outros"] else 0)
            with oe2:
                grav_oe  = st.selectbox("Gravidade",["Baixa","Media","Alta"],
                                         index=["Baixa","Media","Alta"].index(oc_cur[5])
                                         if oc_cur[5] in ["Baixa","Media","Alta"] else 0)
                custo_oe = st.number_input("Custo (R$)", 0.0,
                                           value=float(oc_cur[6]) if oc_cur[6] else 0.0)
            with oe3:
                dias_oe  = st.number_input("Dias recuperacao", 0,
                                           value=int(oc_cur[7]) if oc_cur[7] else 0)
                if is_resolv:
                    st.info("Status: Resolvido (imutavel)")
                    stat_oe = "Resolvido"
                else:
                    stat_oe = st.selectbox("Novo status",
                                           ["Em tratamento","Resolvido"],
                                           index=0 if stat_cur=="Em tratamento" else 1)
            desc_oe   = st.text_area("Descricao", value=oc_cur[4] or "")
            salvar_oc = st.form_submit_button("Salvar alteracoes", type="primary", use_container_width=True)

        if salvar_oc:
            atualizar_ocorrencia(oc_id, tipo_oe, desc_oe, grav_oe, custo_oe, dias_oe, stat_oe, str(data_oe))
            registrar_auditoria(u["id"], "editar_ocorrencia", "ocorrencias", oc_id,
                                f"{tipo_oe}/{grav_oe}/{stat_oe}")
            if stat_oe == "Resolvido" and stat_cur == "Em tratamento":
                st.success("Tratamento encerrado! Ocorrencia marcada como Resolvida.")
                st.balloons()
            else:
                st.success("Ocorrencia atualizada!")
            st.rerun()

    with tab_del_o:
        if stat_cur == "Em tratamento":
            st.warning("Resolva o tratamento antes de excluir esta ocorrencia.")
            st.info("Edite o status para 'Resolvido' na aba ao lado e depois exclua se necessario.")
        else:
            st.warning("A exclusao e permanente e nao pode ser desfeita.")
            confirma_oc = st.checkbox("Confirmo a exclusao permanente desta ocorrencia")
            if confirma_oc:
                if st.button("Excluir ocorrencia definitivamente", type="primary"):
                    excluir_ocorrencia(oc_id)
                    registrar_auditoria(u["id"], "excluir_ocorrencia", "ocorrencias", oc_id, "excluido")
                    st.success("Ocorrencia excluida.")
                    st.rerun()
```
