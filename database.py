# database.py -- Camada de persistencia do Sistema de Gestao Pecuaria.
#
# Indices de retorno (tuplas):
# lote        -> (id[0], nome[1], descricao[2], data_entrada[3],
#                 qtd_comprada[4], qtd_recebida[5], transporte[6])
# animal      -> (id[0], identificacao[1], idade[2], lote_id[3])
# pesagem     -> (id[0], animal_id[1], peso[2], data[3])
# ocorrencia  -> (id[0], animal_id[1], data[2], tipo[3], descricao[4],
#                 gravidade[5], custo[6], dias_recuperacao[7], status[8])

import sqlite3
import os
import hashlib
import secrets
from contextlib import contextmanager

_DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DB_DIR, "pecuaria.db")


@contextmanager
def _conexao():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def inicializar_banco():
    with _conexao() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS lotes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                nome          TEXT    NOT NULL,
                descricao     TEXT    DEFAULT '',
                data_entrada  TEXT    NOT NULL,
                qtd_comprada  INTEGER NOT NULL DEFAULT 0,
                qtd_recebida  INTEGER NOT NULL DEFAULT 0,
                transporte    TEXT    DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS animais (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                identificacao TEXT    NOT NULL,
                idade         INTEGER NOT NULL DEFAULT 0,
                lote_id       INTEGER NOT NULL,
                FOREIGN KEY (lote_id) REFERENCES lotes(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS pesagens (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id INTEGER NOT NULL,
                peso      REAL    NOT NULL,
                data      TEXT    NOT NULL,
                FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS ocorrencias (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id        INTEGER NOT NULL,
                data             TEXT    NOT NULL,
                tipo             TEXT    NOT NULL,
                descricao        TEXT    DEFAULT '',
                gravidade        TEXT    NOT NULL DEFAULT 'Baixa',
                custo            REAL    DEFAULT 0.0,
                dias_recuperacao INTEGER DEFAULT 0,
                status           TEXT    NOT NULL DEFAULT 'Em tratamento',
                FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS fazendas (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nome   TEXT NOT NULL,
                cidade TEXT DEFAULT '',
                estado TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS usuarios (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nome       TEXT NOT NULL,
                email      TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                salt       TEXT NOT NULL,
                perfil     TEXT NOT NULL DEFAULT 'fazendeiro',
                fazenda_id INTEGER,
                ativo      INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (fazenda_id) REFERENCES fazendas(id)
            );
            CREATE TABLE IF NOT EXISTS vacinas_agenda (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id        INTEGER NOT NULL,
                nome_vacina    TEXT    NOT NULL,
                data_prevista  TEXT    NOT NULL,
                data_realizada TEXT    DEFAULT NULL,
                status         TEXT    NOT NULL DEFAULT 'pendente',
                observacao     TEXT    DEFAULT '',
                FOREIGN KEY (lote_id) REFERENCES lotes(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS medicamentos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nome           TEXT NOT NULL,
                unidade        TEXT NOT NULL DEFAULT 'dose',
                estoque_atual  REAL NOT NULL DEFAULT 0,
                estoque_minimo REAL NOT NULL DEFAULT 0,
                validade       TEXT DEFAULT NULL,
                custo_unitario REAL NOT NULL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS medicamentos_uso (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                medicamento_id INTEGER NOT NULL,
                animal_id      INTEGER NOT NULL,
                ocorrencia_id  INTEGER DEFAULT NULL,
                data_uso       TEXT NOT NULL,
                quantidade     REAL NOT NULL DEFAULT 1,
                FOREIGN KEY (medicamento_id) REFERENCES medicamentos(id),
                FOREIGN KEY (animal_id)      REFERENCES animais(id),
                FOREIGN KEY (ocorrencia_id)  REFERENCES ocorrencias(id)
            );
            CREATE TABLE IF NOT EXISTS reproducao (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id           INTEGER NOT NULL,
                data_cio            TEXT    DEFAULT NULL,
                tipo_cobertura      TEXT    NOT NULL DEFAULT 'IATF',
                data_diagnostico    TEXT    DEFAULT NULL,
                resultado           TEXT    DEFAULT 'pendente',
                data_parto_previsto TEXT    DEFAULT NULL,
                data_parto_real     TEXT    DEFAULT NULL,
                observacao          TEXT    DEFAULT '',
                FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS piquetes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                fazenda_id    INTEGER DEFAULT NULL,
                nome          TEXT NOT NULL,
                area_ha       REAL DEFAULT 0,
                capacidade_ua REAL DEFAULT 0,
                FOREIGN KEY (fazenda_id) REFERENCES fazendas(id)
            );
            CREATE TABLE IF NOT EXISTS piquetes_historico (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                piquete_id INTEGER NOT NULL,
                lote_id    INTEGER NOT NULL,
                entrada    TEXT NOT NULL,
                saida      TEXT DEFAULT NULL,
                FOREIGN KEY (piquete_id) REFERENCES piquetes(id),
                FOREIGN KEY (lote_id)    REFERENCES lotes(id)
            );
            CREATE TABLE IF NOT EXISTS mortalidade (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id   INTEGER NOT NULL,
                data        TEXT NOT NULL,
                causa       TEXT NOT NULL DEFAULT 'Doenca',
                descricao   TEXT DEFAULT '',
                custo_perda REAL DEFAULT 0.0,
                FOREIGN KEY (animal_id) REFERENCES animais(id)
            );
            CREATE TABLE IF NOT EXISTS auditoria (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id  INTEGER NOT NULL,
                acao        TEXT NOT NULL,
                tabela      TEXT DEFAULT '',
                registro_id INTEGER DEFAULT NULL,
                detalhe     TEXT DEFAULT '',
                data_hora   TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            );
            CREATE TABLE IF NOT EXISTS gta (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id       INTEGER NOT NULL,
                numero_gta    TEXT NOT NULL,
                data_emissao  TEXT NOT NULL,
                origem        TEXT DEFAULT '',
                destino       TEXT DEFAULT '',
                quantidade    INTEGER DEFAULT 0,
                finalidade    TEXT DEFAULT 'Abate',
                observacao    TEXT DEFAULT '',
                FOREIGN KEY (lote_id) REFERENCES lotes(id)
            );
            CREATE TABLE IF NOT EXISTS sisbov (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id          INTEGER NOT NULL UNIQUE,
                numero_sisbov      TEXT NOT NULL,
                data_certificacao  TEXT NOT NULL,
                FOREIGN KEY (animal_id) REFERENCES animais(id)
            );
            CREATE TABLE IF NOT EXISTS vendas_lote (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id        INTEGER NOT NULL,
                data_venda     TEXT NOT NULL,
                preco_venda_kg REAL NOT NULL DEFAULT 0,
                peso_total_kg  REAL NOT NULL DEFAULT 0,
                frigorific     TEXT DEFAULT '',
                observacao     TEXT DEFAULT '',
                FOREIGN KEY (lote_id) REFERENCES lotes(id)
            );
            CREATE TABLE IF NOT EXISTS cotacoes (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                data   TEXT NOT NULL UNIQUE,
                preco  REAL NOT NULL,
                fonte  TEXT DEFAULT 'manual'
            );
            CREATE INDEX IF NOT EXISTS idx_animais_lote       ON animais(lote_id);
            CREATE INDEX IF NOT EXISTS idx_pesagens_animal    ON pesagens(animal_id);
            CREATE INDEX IF NOT EXISTS idx_ocorrencias_animal ON ocorrencias(animal_id);
            CREATE INDEX IF NOT EXISTS idx_vacinas_lote       ON vacinas_agenda(lote_id);
            CREATE INDEX IF NOT EXISTS idx_reproducao_animal  ON reproducao(animal_id);
            CREATE INDEX IF NOT EXISTS idx_med_uso_animal     ON medicamentos_uso(animal_id);
            CREATE INDEX IF NOT EXISTS idx_mortalidade_animal ON mortalidade(animal_id);
            CREATE INDEX IF NOT EXISTS idx_auditoria_usuario  ON auditoria(usuario_id);
            CREATE INDEX IF NOT EXISTS idx_gta_lote           ON gta(lote_id);
            CREATE INDEX IF NOT EXISTS idx_cotacoes_data      ON cotacoes(data);
        ''')
    _migrar()


def _migrar():
    cols = [
        ("animais",      "sexo TEXT DEFAULT 'indefinido'"),
        ("animais",      "raca TEXT DEFAULT ''"),
        ("animais",      "peso_entrada REAL DEFAULT 0"),
        ("animais",      "foto_path TEXT DEFAULT NULL"),
        ("animais",      "observacoes TEXT DEFAULT ''"),
        ("animais",      "peso_alvo REAL DEFAULT 0"),
        ("animais",      "ativo INTEGER DEFAULT 1"),
        ("lotes",        "fazenda_id INTEGER DEFAULT NULL"),
        ("lotes",        "tipo_alimentacao TEXT DEFAULT 'Pasto'"),
        ("lotes",        "tipo_dieta TEXT DEFAULT 'Capim'"),
        ("lotes",        "preco_por_animal REAL DEFAULT 0"),
        ("lotes",        "data_venda TEXT DEFAULT NULL"),
        ("usuarios",     "trial_inicio TEXT DEFAULT NULL"),
        ("usuarios",     "plano TEXT DEFAULT 'trial'"),
        ("usuarios",     "plano_expira TEXT DEFAULT NULL"),
        ("medicamentos", "carencia_dias INTEGER DEFAULT 0"),
    ]
    with _conexao() as conn:
        for tabela, coluna_def in cols:
            try:
                conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna_def}")
            except sqlite3.OperationalError:
                pass


# ── LOTES ──────────────────────────────────────────────────────────────────

def adicionar_lote(nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO lotes (nome,descricao,data_entrada,qtd_comprada,qtd_recebida,transporte) VALUES(?,?,?,?,?,?)",
            (nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte),
        )
        return cur.lastrowid

def listar_lotes():
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id,nome,descricao,data_entrada,qtd_comprada,qtd_recebida,transporte FROM lotes ORDER BY data_entrada DESC,id DESC"
        ).fetchall()
        return [tuple(r) for r in rows]

def obter_lote(lote_id):
    with _conexao() as conn:
        row = conn.execute(
            "SELECT id,nome,descricao,data_entrada,qtd_comprada,qtd_recebida,transporte FROM lotes WHERE id=?",
            (lote_id,),
        ).fetchone()
        return tuple(row) if row else None


# ── ANIMAIS ────────────────────────────────────────────────────────────────

def adicionar_animal(identificacao, idade, lote_id):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO animais (identificacao,idade,lote_id) VALUES(?,?,?)",
            (identificacao, idade, lote_id),
        )
        return cur.lastrowid

def listar_animais(incluir_inativos=False):
    with _conexao() as conn:
        sql = "SELECT id,identificacao,idade,lote_id FROM animais"
        sql += " ORDER BY id" if incluir_inativos else " WHERE COALESCE(ativo,1)=1 ORDER BY id"
        return [tuple(r) for r in conn.execute(sql).fetchall()]

def listar_animais_por_lote(lote_id, incluir_inativos=False):
    with _conexao() as conn:
        if incluir_inativos:
            sql = "SELECT id,identificacao,idade,lote_id FROM animais WHERE lote_id=? ORDER BY id"
        else:
            sql = "SELECT id,identificacao,idade,lote_id FROM animais WHERE lote_id=? AND COALESCE(ativo,1)=1 ORDER BY id"
        return [tuple(r) for r in conn.execute(sql, (lote_id,)).fetchall()]

def contar_animais_no_lote(lote_id, incluir_inativos=False):
    with _conexao() as conn:
        if incluir_inativos:
            row = conn.execute("SELECT COUNT(*) FROM animais WHERE lote_id=?", (lote_id,)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM animais WHERE lote_id=? AND COALESCE(ativo,1)=1", (lote_id,)).fetchone()
        return row[0] if row else 0

def atualizar_animal_detalhes(animal_id, peso_alvo=None, observacoes=None, foto_path=None):
    campos, vals = [], []
    if peso_alvo    is not None: campos.append("peso_alvo=?");    vals.append(peso_alvo)
    if observacoes  is not None: campos.append("observacoes=?");   vals.append(observacoes)
    if foto_path    is not None: campos.append("foto_path=?");     vals.append(foto_path)
    if not campos: return
    vals.append(animal_id)
    with _conexao() as conn:
        conn.execute(f"UPDATE animais SET {', '.join(campos)} WHERE id=?", vals)

def obter_animal(animal_id):
    with _conexao() as conn:
        row = conn.execute(
            "SELECT id,identificacao,idade,lote_id,"
            "COALESCE(sexo,'indefinido'),COALESCE(raca,''),COALESCE(peso_entrada,0),"
            "COALESCE(peso_alvo,0),COALESCE(observacoes,''),COALESCE(foto_path,NULL)"
            " FROM animais WHERE id=?",
            (animal_id,),
        ).fetchone()
        return tuple(row) if row else None


# ── PESAGENS ───────────────────────────────────────────────────────────────

def adicionar_pesagem(animal_id, peso, data):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO pesagens (animal_id,peso,data) VALUES(?,?,?)",
            (animal_id, peso, data),
        )
        return cur.lastrowid

def listar_pesagens(animal_id):
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id,animal_id,peso,data FROM pesagens WHERE animal_id=? ORDER BY data ASC,id ASC",
            (animal_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


# ── OCORRENCIAS ────────────────────────────────────────────────────────────

def adicionar_ocorrencia(animal_id, data, tipo, descricao, gravidade, custo, dias_recuperacao, status):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO ocorrencias (animal_id,data,tipo,descricao,gravidade,custo,dias_recuperacao,status) VALUES(?,?,?,?,?,?,?,?)",
            (animal_id, data, tipo, descricao, gravidade, custo, dias_recuperacao, status),
        )
        return cur.lastrowid

def listar_ocorrencias(animal_id):
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id,animal_id,data,tipo,descricao,gravidade,custo,dias_recuperacao,status FROM ocorrencias WHERE animal_id=? ORDER BY data ASC,id ASC",
            (animal_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


# ── USUARIOS ───────────────────────────────────────────────────────────────

def _hash_senha(senha, salt):
    return hashlib.sha256((salt + senha).encode()).hexdigest()

def criar_usuario(nome, email, senha, perfil="fazendeiro", fazenda_id=None):
    salt = secrets.token_hex(16)
    h = _hash_senha(senha, salt)
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome,email,senha_hash,salt,perfil,fazenda_id) VALUES(?,?,?,?,?,?)",
            (nome, email, h, salt, perfil, fazenda_id),
        )
        return cur.lastrowid

def autenticar_usuario(email, senha):
    with _conexao() as conn:
        row = conn.execute(
            "SELECT id,nome,email,senha_hash,salt,perfil,fazenda_id,ativo FROM usuarios WHERE email=?",
            (email,),
        ).fetchone()
    if not row or not row["ativo"]: return None
    if _hash_senha(senha, row["salt"]) != row["senha_hash"]: return None
    return dict(id=row["id"], nome=row["nome"], email=row["email"],
                perfil=row["perfil"], fazenda_id=row["fazenda_id"])

def listar_usuarios():
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id,nome,email,perfil,fazenda_id FROM usuarios WHERE ativo=1 ORDER BY nome"
        ).fetchall()
        return [tuple(r) for r in rows]

def usuario_existe():
    with _conexao() as conn:
        return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] > 0

def alterar_senha(usuario_id, nova_senha):
    salt = secrets.token_hex(16)
    h = _hash_senha(nova_senha, salt)
    with _conexao() as conn:
        conn.execute("UPDATE usuarios SET senha_hash=?,salt=? WHERE id=?", (h, salt, usuario_id))


# ── FAZENDAS ───────────────────────────────────────────────────────────────

def adicionar_fazenda(nome, cidade="", estado=""):
    with _conexao() as conn:
        cur = conn.execute("INSERT INTO fazendas (nome,cidade,estado) VALUES(?,?,?)", (nome, cidade, estado))
        return cur.lastrowid

def listar_fazendas():
    with _conexao() as conn:
        rows = conn.execute("SELECT id,nome,cidade,estado FROM fazendas ORDER BY nome").fetchall()
        return [tuple(r) for r in rows]


# ── VACINAS ────────────────────────────────────────────────────────────────

def adicionar_vacina_agenda(lote_id, nome_vacina, data_prevista, observacao=""):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO vacinas_agenda (lote_id,nome_vacina,data_prevista,observacao) VALUES(?,?,?,?)",
            (lote_id, nome_vacina, data_prevista, observacao),
        )
        return cur.lastrowid

def registrar_vacina_realizada(vacina_id, data_realizada):
    with _conexao() as conn:
        conn.execute(
            "UPDATE vacinas_agenda SET data_realizada=?,status='realizado' WHERE id=?",
            (data_realizada, vacina_id),
        )

def listar_vacinas_agenda(lote_id=None):
    with _conexao() as conn:
        if lote_id:
            rows = conn.execute(
                "SELECT id,lote_id,nome_vacina,data_prevista,data_realizada,status,observacao FROM vacinas_agenda WHERE lote_id=? ORDER BY data_prevista",
                (lote_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,lote_id,nome_vacina,data_prevista,data_realizada,status,observacao FROM vacinas_agenda ORDER BY data_prevista"
            ).fetchall()
        return [tuple(r) for r in rows]

def listar_vacinas_pendentes():
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT v.id,v.lote_id,l.nome,v.nome_vacina,v.data_prevista,v.status,v.observacao"
            " FROM vacinas_agenda v JOIN lotes l ON l.id=v.lote_id"
            " WHERE v.status='pendente' ORDER BY v.data_prevista"
        ).fetchall()
        return [tuple(r) for r in rows]


# ── MEDICAMENTOS ───────────────────────────────────────────────────────────

def adicionar_medicamento(nome, unidade, estoque_atual, estoque_minimo, validade, custo_unitario):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO medicamentos (nome,unidade,estoque_atual,estoque_minimo,validade,custo_unitario) VALUES(?,?,?,?,?,?)",
            (nome, unidade, estoque_atual, estoque_minimo, validade, custo_unitario),
        )
        return cur.lastrowid

def listar_medicamentos():
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id,nome,unidade,estoque_atual,estoque_minimo,validade,custo_unitario FROM medicamentos ORDER BY nome"
        ).fetchall()
        return [tuple(r) for r in rows]

def atualizar_estoque(medicamento_id, quantidade):
    with _conexao() as conn:
        conn.execute(
            "UPDATE medicamentos SET estoque_atual=MAX(0,estoque_atual-?) WHERE id=?",
            (quantidade, medicamento_id),
        )

def registrar_uso_medicamento(medicamento_id, animal_id, data_uso, quantidade, ocorrencia_id=None):
    atualizar_estoque(medicamento_id, quantidade)
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO medicamentos_uso (medicamento_id,animal_id,ocorrencia_id,data_uso,quantidade) VALUES(?,?,?,?,?)",
            (medicamento_id, animal_id, ocorrencia_id, data_uso, quantidade),
        )
        return cur.lastrowid

def listar_medicamentos_criticos():
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id,nome,unidade,estoque_atual,estoque_minimo,validade,custo_unitario FROM medicamentos"
            " WHERE estoque_atual<=estoque_minimo OR (validade IS NOT NULL AND validade<=date('now','+30 days'))"
            " ORDER BY validade"
        ).fetchall()
        return [tuple(r) for r in rows]


# ── REPRODUCAO ─────────────────────────────────────────────────────────────

def adicionar_reproducao(animal_id, tipo_cobertura, data_cio=None, data_diagnostico=None,
                          resultado="pendente", data_parto_previsto=None, observacao=""):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO reproducao (animal_id,data_cio,tipo_cobertura,data_diagnostico,resultado,data_parto_previsto,observacao) VALUES(?,?,?,?,?,?,?)",
            (animal_id, data_cio, tipo_cobertura, data_diagnostico, resultado, data_parto_previsto, observacao),
        )
        return cur.lastrowid

def atualizar_reproducao(repro_id, resultado, data_parto_real=None, data_diagnostico=None, data_parto_previsto=None):
    with _conexao() as conn:
        conn.execute(
            "UPDATE reproducao SET resultado=?,data_parto_real=COALESCE(?,data_parto_real),"
            "data_diagnostico=COALESCE(?,data_diagnostico),data_parto_previsto=COALESCE(?,data_parto_previsto) WHERE id=?",
            (resultado, data_parto_real, data_diagnostico, data_parto_previsto, repro_id),
        )

def listar_reproducao(animal_id):
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id,animal_id,data_cio,tipo_cobertura,data_diagnostico,resultado,data_parto_previsto,data_parto_real,observacao"
            " FROM reproducao WHERE animal_id=? ORDER BY data_cio DESC",
            (animal_id,),
        ).fetchall()
        return [tuple(r) for r in rows]

def listar_partos_previstos():
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT r.id,a.identificacao,l.nome,r.data_parto_previsto,r.tipo_cobertura"
            " FROM reproducao r JOIN animais a ON a.id=r.animal_id JOIN lotes l ON l.id=a.lote_id"
            " WHERE r.resultado='positivo' AND r.data_parto_real IS NULL"
            " AND r.data_parto_previsto<=date('now','+30 days') ORDER BY r.data_parto_previsto"
        ).fetchall()
        return [tuple(r) for r in rows]

def taxa_prenhez_lote(lote_id):
    with _conexao() as conn:
        total = conn.execute(
            "SELECT COUNT(DISTINCT r.animal_id) FROM reproducao r JOIN animais a ON a.id=r.animal_id WHERE a.lote_id=?",
            (lote_id,),
        ).fetchone()[0]
        positivas = conn.execute(
            "SELECT COUNT(DISTINCT r.animal_id) FROM reproducao r JOIN animais a ON a.id=r.animal_id WHERE a.lote_id=? AND r.resultado='positivo'",
            (lote_id,),
        ).fetchone()[0]
    return dict(total=total, positivas=positivas, taxa=(positivas/total*100) if total > 0 else 0)


# ── PIQUETES ───────────────────────────────────────────────────────────────

def adicionar_piquete(nome, area_ha, capacidade_ua, fazenda_id=None):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO piquetes (nome,area_ha,capacidade_ua,fazenda_id) VALUES(?,?,?,?)",
            (nome, area_ha, capacidade_ua, fazenda_id),
        )
        return cur.lastrowid

def listar_piquetes(fazenda_id=None):
    with _conexao() as conn:
        if fazenda_id:
            rows = conn.execute("SELECT id,fazenda_id,nome,area_ha,capacidade_ua FROM piquetes WHERE fazenda_id=? ORDER BY nome", (fazenda_id,)).fetchall()
        else:
            rows = conn.execute("SELECT id,fazenda_id,nome,area_ha,capacidade_ua FROM piquetes ORDER BY nome").fetchall()
        return [tuple(r) for r in rows]

def alocar_lote_piquete(piquete_id, lote_id, data_entrada):
    with _conexao() as conn:
        cur = conn.execute("INSERT INTO piquetes_historico (piquete_id,lote_id,entrada) VALUES(?,?,?)", (piquete_id, lote_id, data_entrada))
        return cur.lastrowid

def liberar_piquete(piquete_id, data_saida):
    with _conexao() as conn:
        conn.execute("UPDATE piquetes_historico SET saida=? WHERE piquete_id=? AND saida IS NULL", (data_saida, piquete_id))

def historico_piquete(piquete_id):
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT ph.id,l.nome,ph.entrada,ph.saida FROM piquetes_historico ph JOIN lotes l ON l.id=ph.lote_id WHERE ph.piquete_id=? ORDER BY ph.entrada DESC",
            (piquete_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


# ── TRIAL / PLANO ──────────────────────────────────────────────────────────

from datetime import date as _date, timedelta as _td

TRIAL_DIAS = 30

def ativar_trial(usuario_id):
    hoje = str(_date.today())
    expira = str(_date.today() + _td(days=TRIAL_DIAS))
    with _conexao() as conn:
        conn.execute("UPDATE usuarios SET trial_inicio=?,plano='trial',plano_expira=? WHERE id=?", (hoje, expira, usuario_id))

def obter_status_plano(usuario_id):
    with _conexao() as conn:
        row = conn.execute("SELECT plano,trial_inicio,plano_expira,ativo FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
    if not row:
        return dict(plano="expirado", dias_restantes=0, trial_inicio=None, plano_expira=None, pode_exportar=False, ativo=False)
    plano = row["plano"] or "trial"
    trial_inicio = row["trial_inicio"]
    plano_expira = row["plano_expira"]
    ativo = bool(row["ativo"])
    hoje = _date.today()
    if plano == "trial" and not trial_inicio:
        ativar_trial(usuario_id)
        trial_inicio = str(hoje)
        plano_expira = str(hoje + _td(days=TRIAL_DIAS))
    dias_restantes = (_date.fromisoformat(plano_expira) - hoje).days if plano_expira else 0
    if plano == "pago":
        status, pode_exportar = "pago", True
    elif dias_restantes > 0:
        status, pode_exportar = "trial", False
    else:
        status, pode_exportar = "expirado", False
    return dict(plano=status, dias_restantes=dias_restantes, trial_inicio=trial_inicio,
                plano_expira=plano_expira, pode_exportar=pode_exportar, ativo=ativo)

def converter_para_pago(usuario_id):
    with _conexao() as conn:
        conn.execute("UPDATE usuarios SET plano='pago',plano_expira=NULL WHERE id=?", (usuario_id,))

def listar_usuarios_trial_expirando(dias=7):
    limite = str(_date.today() + _td(days=dias))
    hoje = str(_date.today())
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id,nome,email,plano_expira FROM usuarios WHERE plano='trial' AND plano_expira IS NOT NULL AND plano_expira>=? AND plano_expira<=? ORDER BY plano_expira",
            (hoje, limite),
        ).fetchall()
    return [tuple(r) for r in rows]


# ── MORTALIDADE ────────────────────────────────────────────────────────────

def registrar_morte(animal_id, data, causa, descricao="", custo_perda=0.0):
    with _conexao() as conn:
        row = conn.execute("SELECT lote_id FROM animais WHERE id=?", (animal_id,)).fetchone()
        lote_id = row[0] if row else None
        conn.execute("UPDATE animais SET ativo=0 WHERE id=?", (animal_id,))
        cur = conn.execute(
            "INSERT INTO mortalidade (animal_id,data,causa,descricao,custo_perda) VALUES(?,?,?,?,?)",
            (animal_id, data, causa, descricao, custo_perda),
        )
        mid = cur.lastrowid
    if lote_id:
        atualizar_qtd_lote(lote_id)
    return mid

def listar_mortalidade(lote_id=None):
    with _conexao() as conn:
        if lote_id:
            rows = conn.execute(
                "SELECT m.id,m.animal_id,a.identificacao,m.data,m.causa,m.descricao,m.custo_perda FROM mortalidade m JOIN animais a ON a.id=m.animal_id WHERE a.lote_id=? ORDER BY m.data DESC",
                (lote_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT m.id,m.animal_id,a.identificacao,m.data,m.causa,m.descricao,m.custo_perda FROM mortalidade m JOIN animais a ON a.id=m.animal_id ORDER BY m.data DESC"
            ).fetchall()
        return [tuple(r) for r in rows]

def taxa_mortalidade_lote(lote_id):
    with _conexao() as conn:
        total = conn.execute("SELECT COUNT(*) FROM animais WHERE lote_id=?", (lote_id,)).fetchone()[0]
        mortos = conn.execute(
            "SELECT COUNT(*) FROM mortalidade m JOIN animais a ON a.id=m.animal_id WHERE a.lote_id=?",
            (lote_id,),
        ).fetchone()[0]
    taxa = (mortos/total*100) if total > 0 else 0
    return dict(total=total, mortos=mortos, taxa=round(taxa, 2))


# ── AUDITORIA ──────────────────────────────────────────────────────────────

def registrar_auditoria(usuario_id, acao, tabela="", registro_id=None, detalhe=""):
    with _conexao() as conn:
        conn.execute(
            "INSERT INTO auditoria (usuario_id,acao,tabela,registro_id,detalhe,data_hora) VALUES(?,?,?,?,?,datetime('now','localtime'))",
            (usuario_id, acao, tabela, registro_id, detalhe),
        )

def listar_auditoria(limite=100, usuario_id=None):
    with _conexao() as conn:
        if usuario_id:
            rows = conn.execute(
                "SELECT a.id,u.nome,a.acao,a.tabela,a.registro_id,a.detalhe,a.data_hora FROM auditoria a JOIN usuarios u ON u.id=a.usuario_id WHERE a.usuario_id=? ORDER BY a.id DESC LIMIT ?",
                (usuario_id, limite),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT a.id,u.nome,a.acao,a.tabela,a.registro_id,a.detalhe,a.data_hora FROM auditoria a JOIN usuarios u ON u.id=a.usuario_id ORDER BY a.id DESC LIMIT ?",
                (limite,),
            ).fetchall()
        return [tuple(r) for r in rows]


# ── GTA / SISBOV ───────────────────────────────────────────────────────────

def registrar_gta(lote_id, numero_gta, data_emissao, origem, destino, quantidade, finalidade="Abate", observacao=""):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO gta (lote_id,numero_gta,data_emissao,origem,destino,quantidade,finalidade,observacao) VALUES(?,?,?,?,?,?,?,?)",
            (lote_id, numero_gta, data_emissao, origem, destino, quantidade, finalidade, observacao),
        )
        gta_id = cur.lastrowid
        if finalidade in ("Abate", "Venda"):
            rows = conn.execute(
                "SELECT id FROM animais WHERE lote_id=? AND COALESCE(ativo,1)=1 ORDER BY id DESC LIMIT ?",
                (lote_id, quantidade),
            ).fetchall()
            for row in rows:
                conn.execute("UPDATE animais SET ativo=0 WHERE id=?", (row[0],))
    atualizar_qtd_lote(lote_id)
    return gta_id

def listar_gta(lote_id=None):
    with _conexao() as conn:
        if lote_id:
            rows = conn.execute(
                "SELECT g.id,g.lote_id,l.nome,g.numero_gta,g.data_emissao,g.origem,g.destino,g.quantidade,g.finalidade,g.observacao FROM gta g JOIN lotes l ON l.id=g.lote_id WHERE g.lote_id=? ORDER BY g.data_emissao DESC",
                (lote_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT g.id,g.lote_id,l.nome,g.numero_gta,g.data_emissao,g.origem,g.destino,g.quantidade,g.finalidade,g.observacao FROM gta g JOIN lotes l ON l.id=g.lote_id ORDER BY g.data_emissao DESC"
            ).fetchall()
        return [tuple(r) for r in rows]

def registrar_sisbov(animal_id, numero_sisbov, data_certificacao):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO sisbov (animal_id,numero_sisbov,data_certificacao) VALUES(?,?,?)",
            (animal_id, numero_sisbov, data_certificacao),
        )
        return cur.lastrowid

def obter_sisbov(animal_id):
    with _conexao() as conn:
        row = conn.execute("SELECT id,animal_id,numero_sisbov,data_certificacao FROM sisbov WHERE animal_id=?", (animal_id,)).fetchone()
        return tuple(row) if row else None


# ── CARENCIA ───────────────────────────────────────────────────────────────

def verificar_carencia(animal_id):
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT mu.data_uso,m.nome,m.carencia_dias,date(mu.data_uso,'+'||m.carencia_dias||' days') as libera_em"
            " FROM medicamentos_uso mu JOIN medicamentos m ON m.id=mu.medicamento_id"
            " WHERE mu.animal_id=? AND m.carencia_dias>0 AND date(mu.data_uso,'+'||m.carencia_dias||' days')>=date('now')"
            " ORDER BY libera_em DESC",
            (animal_id,),
        ).fetchall()
    if not rows:
        return dict(em_carencia=False, medicamentos=[], liberado_em=None)
    meds = [dict(medicamento=r[1], uso=r[0], carencia_dias=r[2], libera_em=r[3]) for r in rows]
    return dict(em_carencia=True, medicamentos=meds, liberado_em=max(r["libera_em"] for r in meds))


# ── SCORE DE SAUDE ─────────────────────────────────────────────────────────

def calcular_score_saude(animal_id):
    import pandas as pd
    pesagens = listar_pesagens(animal_id)
    gmd = 0.0
    if len(pesagens) >= 2:
        df = pd.DataFrame(pesagens, columns=["id","aid","peso","data"])
        df["data"] = pd.to_datetime(df["data"])
        df = df.sort_values("data")
        dias = (df["data"].iloc[-1] - df["data"].iloc[0]).days
        if dias > 0:
            gmd = (df["peso"].iloc[-1] - df["peso"].iloc[0]) / dias
    pts_gmd = 50 if gmd>=1.2 else 45 if gmd>=1.0 else 38 if gmd>=0.8 else 30 if gmd>=0.6 else 20 if gmd>=0.4 else 10 if gmd>=0.0 else 0
    ocs = listar_ocorrencias(animal_id)
    pen = min(35, sum(1 for o in ocs if o[5]=="Alta")*15 + sum(1 for o in ocs if o[5]=="Media")*7 + sum(1 for o in ocs if o[5]=="Baixa")*3)
    pts_oc = max(0, 35 - pen)
    repros = listar_reproducao(animal_id)
    pts_rep = 5 if repros and repros[0][5]=="negativo" else 10 if repros and repros[0][5]=="pendente" else 15
    score = pts_gmd + pts_oc + pts_rep
    classif = "Excelente" if score>=80 else "Bom" if score>=60 else "Regular" if score>=40 else "Critico"
    return dict(score=score, classificacao=classif,
                detalhes=dict(pts_gmd=pts_gmd, pts_ocorrencias=pts_oc, pts_reproducao=pts_rep, gmd=round(gmd,3), n_ocorrencias=len(ocs)))


# ── PREVISAO DE ABATE ──────────────────────────────────────────────────────

def calcular_previsao_abate(animal_id):
    import pandas as pd
    from datetime import date as dt
    animal = obter_animal(animal_id)
    if not animal: return {}
    peso_alvo = animal[7]
    pesagens = listar_pesagens(animal_id)
    if len(pesagens) < 2 or peso_alvo <= 0:
        return dict(erro="Necessario >= 2 pesagens e peso alvo definido")
    df = pd.DataFrame(pesagens, columns=["id","aid","peso","data"])
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values("data")
    peso_atual = df["peso"].iloc[-1]
    dias_hist = (df["data"].iloc[-1] - df["data"].iloc[0]).days
    if dias_hist == 0: return dict(erro="Datas de pesagem identicas")
    gmd = (peso_atual - df["peso"].iloc[0]) / dias_hist
    if gmd <= 0: return dict(erro="GMD negativo")
    if peso_atual >= peso_alvo:
        return dict(gmd=round(gmd,3), peso_atual=peso_atual, peso_alvo=peso_alvo, dias_restantes=0, data_prevista=str(dt.today()), confianca="pronto")
    dias_rest = int((peso_alvo - peso_atual) / gmd)
    data_prev = dt.today() + _td(days=dias_rest)
    confianca = "alta" if len(pesagens)>=5 else "media" if len(pesagens)>=3 else "baixa"
    return dict(gmd=round(gmd,3), peso_atual=round(peso_atual,1), peso_alvo=round(peso_alvo,1),
                dias_restantes=dias_rest, data_prevista=str(data_prev), confianca=confianca)


# ── VENDAS / MARGEM ────────────────────────────────────────────────────────

def registrar_venda_lote(lote_id, data_venda, preco_venda_kg, peso_total_kg, frigorific="", observacao=""):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO vendas_lote (lote_id,data_venda,preco_venda_kg,peso_total_kg,frigorific,observacao) VALUES(?,?,?,?,?,?)",
            (lote_id, data_venda, preco_venda_kg, peso_total_kg, frigorific, observacao),
        )
        return cur.lastrowid

def calcular_margem_lote(lote_id):
    with _conexao() as conn:
        lote = obter_lote(lote_id)
        if not lote: return {}
        preco_animal = conn.execute("SELECT COALESCE(preco_por_animal,0) FROM lotes WHERE id=?", (lote_id,)).fetchone()[0]
        custo_compra = preco_animal * lote[5]
        venda = conn.execute("SELECT preco_venda_kg,peso_total_kg,data_venda,frigorific FROM vendas_lote WHERE lote_id=? ORDER BY id DESC LIMIT 1", (lote_id,)).fetchone()
        receita_real = (venda[0]*venda[1]) if venda else 0.0
        animais = listar_animais_por_lote(lote_id)
        custo_san = sum(o[6] for a in animais for o in listar_ocorrencias(a[0]) if o[6])
        margem = receita_real - custo_compra - custo_san
        margem_pct = (margem/custo_compra*100) if custo_compra > 0 else 0
    return dict(custo_compra=round(custo_compra,2), receita_real=round(receita_real,2),
                custo_sanitario=round(custo_san,2), margem=round(margem,2), margem_pct=round(margem_pct,1),
                data_venda=venda[2] if venda else None, frigorific=venda[3] if venda else "",
                venda_registrada=venda is not None)

def listar_vendas_lote(lote_id):
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id,lote_id,data_venda,preco_venda_kg,peso_total_kg,frigorific,observacao FROM vendas_lote WHERE lote_id=? ORDER BY data_venda DESC",
            (lote_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


# ── COTACOES ───────────────────────────────────────────────────────────────

def salvar_cotacao(data, preco, fonte="manual"):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO cotacoes (data,preco,fonte) VALUES(?,?,?) ON CONFLICT(data) DO UPDATE SET preco=excluded.preco,fonte=excluded.fonte",
            (data, preco, fonte),
        )
        return cur.lastrowid

def listar_cotacoes(dias=30):
    with _conexao() as conn:
        if dias <= 0:
            rows = conn.execute("SELECT id,data,preco,fonte FROM cotacoes ORDER BY data ASC").fetchall()
        else:
            rows = conn.execute(
                "SELECT id,data,preco,fonte FROM cotacoes WHERE data>=date('now',?||' days') ORDER BY data ASC",
                (f"-{dias}",),
            ).fetchall()
        return [tuple(r) for r in rows]

def obter_ultima_cotacao():
    with _conexao() as conn:
        row = conn.execute("SELECT id,data,preco,fonte FROM cotacoes ORDER BY data DESC LIMIT 1").fetchone()
        return tuple(row) if row else None


# ── GMD TEMPORAL ───────────────────────────────────────────────────────────

def calcular_gmd_temporal(lote_id, janela_dias=14):
    import pandas as pd
    animais = listar_animais_por_lote(lote_id)
    todos = [{"animal_id":a[0],"peso":p[2],"data":p[3]} for a in animais for p in listar_pesagens(a[0])]
    if len(todos) < 2: return []
    df = pd.DataFrame(todos)
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values("data")
    resultado = []
    data_atual = df["data"].min() + pd.Timedelta(days=janela_dias)
    while data_atual <= df["data"].max():
        janela = df[df["data"] <= data_atual]
        gmds = []
        for aid in janela["animal_id"].unique():
            sub = janela[janela["animal_id"]==aid].sort_values("data")
            if len(sub) >= 2:
                dias = (sub["data"].iloc[-1]-sub["data"].iloc[0]).days
                if dias > 0:
                    g = (sub["peso"].iloc[-1]-sub["peso"].iloc[0])/dias
                    if 0 < g <= 2: gmds.append(g)
        if gmds: resultado.append((str(data_atual.date()), round(sum(gmds)/len(gmds),4)))
        data_atual += pd.Timedelta(days=janela_dias)
    return resultado


# ── IMPORTACAO CSV ─────────────────────────────────────────────────────────

def importar_pesagens_csv(linhas, lote_id):
    ok = erros = criados = 0
    msgs = []
    existentes = {a[1]:a[0] for a in listar_animais_por_lote(lote_id)}
    for i, linha in enumerate(linhas, 1):
        try:
            ident = str(linha.get("identificacao","")).strip()
            peso  = float(str(linha.get("peso","0")).replace(",","."))
            data  = str(linha.get("data","")).strip()
            if not ident or not data or peso <= 0:
                erros += 1; msgs.append(f"Linha {i}: invalido"); continue
            if ident not in existentes:
                existentes[ident] = adicionar_animal(ident, 0, lote_id); criados += 1
            adicionar_pesagem(existentes[ident], peso, data); ok += 1
        except Exception as e:
            erros += 1; msgs.append(f"Linha {i}: {e}")
    if criados > 0:
        atualizar_qtd_lote(lote_id)
    return dict(importados=ok, erros=erros, animais_criados=criados, mensagens=msgs)

def importar_animais_csv(linhas, lote_id):
    ok = erros = 0; msgs = []
    existentes = {a[1] for a in listar_animais_por_lote(lote_id)}
    for i, linha in enumerate(linhas, 1):
        try:
            ident = str(linha.get("identificacao","")).strip()
            if not ident: erros+=1; msgs.append(f"Linha {i}: vazio"); continue
            if ident in existentes: erros+=1; msgs.append(f"Linha {i}: {ident} existe"); continue
            idade = int(float(str(linha.get("idade",0)).replace(",",".") or 0))
            aid = adicionar_animal(ident, idade, lote_id)
            pa = float(str(linha.get("peso_alvo",0)).replace(",",".") or 0)
            ob = str(linha.get("observacoes",""))
            atualizar_animal_detalhes(aid, peso_alvo=pa if pa>0 else None, observacoes=ob if ob else None)
            existentes.add(ident); ok += 1
        except Exception as e:
            erros+=1; msgs.append(f"Linha {i}: {e}")
    if ok > 0:
        atualizar_qtd_lote(lote_id)
    return dict(importados=ok, erros=erros, mensagens=msgs)


# ── CONSISTENCIA DE LOTE ───────────────────────────────────────────────────

def atualizar_qtd_lote(lote_id):
    with _conexao() as conn:
        n = conn.execute("SELECT COUNT(*) FROM animais WHERE lote_id=? AND COALESCE(ativo,1)=1", (lote_id,)).fetchone()[0]
        conn.execute("UPDATE lotes SET qtd_recebida=? WHERE id=?", (n, lote_id))
    return n

def resumo_lote(lote_id):
    with _conexao() as conn:
        ativos   = conn.execute("SELECT COUNT(*) FROM animais WHERE lote_id=? AND COALESCE(ativo,1)=1", (lote_id,)).fetchone()[0]
        mortos   = conn.execute("SELECT COUNT(*) FROM mortalidade m JOIN animais a ON a.id=m.animal_id WHERE a.lote_id=?", (lote_id,)).fetchone()[0]
        total    = conn.execute("SELECT COUNT(*) FROM animais WHERE lote_id=?", (lote_id,)).fetchone()[0]
        gtas     = conn.execute("SELECT COUNT(*),COALESCE(SUM(quantidade),0) FROM gta WHERE lote_id=?", (lote_id,)).fetchone()
        custo    = conn.execute("SELECT COALESCE(SUM(o.custo),0) FROM ocorrencias o JOIN animais a ON a.id=o.animal_id WHERE a.lote_id=?", (lote_id,)).fetchone()[0]
        ocorr    = conn.execute("SELECT COUNT(*) FROM ocorrencias o JOIN animais a ON a.id=o.animal_id WHERE a.lote_id=?", (lote_id,)).fetchone()[0]
        vac_pend = conn.execute("SELECT COUNT(*) FROM vacinas_agenda WHERE lote_id=? AND status='pendente'", (lote_id,)).fetchone()[0]
    return dict(total_animais=total, ativos=ativos, mortos=mortos,
                gtas_emitidas=gtas[0], animais_saida_gta=int(gtas[1]),
                ocorrencias=ocorr, custo_sanitario=round(custo,2), vacinas_pendentes=vac_pend)


# ── EDICAO E EXCLUSAO ──────────────────────────────────────────────────────

def atualizar_lote(lote_id, nome, descricao, data_entrada,
                   qtd_comprada, qtd_recebida, transporte, preco_por_animal=None):
    # qtd_recebida sempre calculada pelos animais ativos -- ignora o valor passado
    with _conexao() as conn:
        ativos_reais = conn.execute(
            "SELECT COUNT(*) FROM animais WHERE lote_id=? AND COALESCE(ativo,1)=1",
            (lote_id,),
        ).fetchone()[0]
        conn.execute(
            "UPDATE lotes SET nome=?,descricao=?,data_entrada=?,qtd_comprada=?,qtd_recebida=?,transporte=? WHERE id=?",
            (nome, descricao, data_entrada, qtd_comprada, ativos_reais, transporte, lote_id),
        )
        if preco_por_animal is not None:
            conn.execute("UPDATE lotes SET preco_por_animal=? WHERE id=?", (preco_por_animal, lote_id))

def excluir_lote(lote_id):
    with _conexao() as conn:
        conn.execute("DELETE FROM lotes WHERE id=?", (lote_id,))

def atualizar_animal(animal_id, identificacao, idade):
    with _conexao() as conn:
        conn.execute(
            "UPDATE animais SET identificacao=?,idade=? WHERE id=?",
            (identificacao, idade, animal_id),
        )

def excluir_animal(animal_id):
    with _conexao() as conn:
        conn.execute("DELETE FROM animais WHERE id=?", (animal_id,))

def atualizar_pesagem(pesagem_id, peso, data):
    with _conexao() as conn:
        conn.execute(
            "UPDATE pesagens SET peso=?,data=? WHERE id=?",
            (peso, data, pesagem_id),
        )

def excluir_pesagem(pesagem_id):
    with _conexao() as conn:
        conn.execute("DELETE FROM pesagens WHERE id=?", (pesagem_id,))

def atualizar_ocorrencia(ocorrencia_id, tipo, descricao, gravidade,
                          custo, dias_recuperacao, status, data=None):
    with _conexao() as conn:
        if data:
            conn.execute(
                "UPDATE ocorrencias SET tipo=?,descricao=?,gravidade=?,custo=?,dias_recuperacao=?,status=?,data=? WHERE id=?",
                (tipo, descricao, gravidade, custo, dias_recuperacao, status, data, ocorrencia_id),
            )
        else:
            conn.execute(
                "UPDATE ocorrencias SET tipo=?,descricao=?,gravidade=?,custo=?,dias_recuperacao=?,status=? WHERE id=?",
                (tipo, descricao, gravidade, custo, dias_recuperacao, status, ocorrencia_id),
            )

def excluir_ocorrencia(ocorrencia_id):
    with _conexao() as conn:
        conn.execute("DELETE FROM ocorrencias WHERE id=?", (ocorrencia_id,))

def listar_ocorrencias_em_tratamento():
    from datetime import date as dt
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT o.id,o.animal_id,a.identificacao,l.nome,o.data,o.tipo,"
            "o.gravidade,o.dias_recuperacao,o.custo,o.status,"
            "date(o.data,'+'||o.dias_recuperacao||' days') as previsao_alta"
            " FROM ocorrencias o"
            " JOIN animais a ON a.id=o.animal_id"
            " JOIN lotes l ON l.id=a.lote_id"
            " WHERE o.status='Em tratamento'"
            " ORDER BY previsao_alta ASC"
        ).fetchall()
        return [tuple(r) for r in rows]

def listar_tratamentos_vencidos():
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT o.id,o.animal_id,a.identificacao,l.nome,o.data,o.tipo,"
            "o.gravidade,o.dias_recuperacao,o.custo,o.status,"
            "date(o.data,'+'||o.dias_recuperacao||' days') as previsao_alta"
            " FROM ocorrencias o"
            " JOIN animais a ON a.id=o.animal_id"
            " JOIN lotes l ON l.id=a.lote_id"
            " WHERE o.status='Em tratamento'"
            " AND date(o.data,'+'||o.dias_recuperacao||' days') <= date('now')"
            " ORDER BY previsao_alta ASC"
        ).fetchall()
        return [tuple(r) for r in rows]

def listar_pesagens_lote(lote_id):
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT p.id,a.identificacao,p.peso,p.data,p.animal_id"
            " FROM pesagens p JOIN animais a ON a.id=p.animal_id"
            " WHERE a.lote_id=? ORDER BY p.data DESC,a.identificacao",
            (lote_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


def sincronizar_todos_lotes():
    lotes = listar_lotes()
    resultados = []
    for l in lotes:
        n = atualizar_qtd_lote(l[0])
        resultados.append((l[0], l[1], n))
    return resultados
