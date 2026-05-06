"""
database.py — Camada de persistência do Sistema de Gestão Pecuária.

Índices de retorno (tuplas):
  lote        → (id[0], nome[1], descricao[2], data_entrada[3],
                  qtd_comprada[4], qtd_recebida[5], transporte[6])
  animal      → (id[0], identificacao[1], idade[2], lote_id[3])
  pesagem     → (id[0], animal_id[1], peso[2], data[3])
  ocorrencia  → (id[0], animal_id[1], data[2], tipo[3], descricao[4],
                  gravidade[5], custo[6], dias_recuperacao[7], status[8])
  usuario     → (id[0], nome[1], email[2], perfil[3], fazenda_id[4])
  vacina_agenda → (id[0], lote_id[1], nome_vacina[2], data_prevista[3],
                   data_realizada[4], status[5], observacao[6])
  medicamento → (id[0], nome[1], unidade[2], estoque_atual[3],
                 estoque_minimo[4], validade[5], custo_unitario[6])
  reproducao  → (id[0], animal_id[1], data_cio[2], tipo_cobertura[3],
                 data_diagnostico[4], resultado[5], data_parto_previsto[6],
                 data_parto_real[7], observacao[8])
"""

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


def inicializar_banco() -> None:
    """Cria tabelas e executa migrações. Seguro chamar múltiplas vezes."""
    with _conexao() as conn:
        conn.executescript("""
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

            CREATE INDEX IF NOT EXISTS idx_animais_lote      ON animais(lote_id);
            CREATE INDEX IF NOT EXISTS idx_pesagens_animal   ON pesagens(animal_id);
            CREATE INDEX IF NOT EXISTS idx_ocorrencias_animal ON ocorrencias(animal_id);
            CREATE INDEX IF NOT EXISTS idx_vacinas_lote      ON vacinas_agenda(lote_id);
            CREATE INDEX IF NOT EXISTS idx_reproducao_animal ON reproducao(animal_id);
            CREATE INDEX IF NOT EXISTS idx_med_uso_animal    ON medicamentos_uso(animal_id);
        """)
    _migrar()


def _migrar():
    """Adiciona colunas novas sem perder dados existentes."""
    novas_colunas = [
        ("animais",  "sexo TEXT DEFAULT 'indefinido'"),
        ("animais",  "raca TEXT DEFAULT ''"),
        ("animais",  "peso_entrada REAL DEFAULT 0"),
        ("lotes",    "fazenda_id INTEGER DEFAULT NULL"),
        ("lotes",    "tipo_alimentacao TEXT DEFAULT 'Pasto'"),
        ("lotes",    "tipo_dieta TEXT DEFAULT 'Capim'"),
        ("lotes",    "preco_por_animal REAL DEFAULT 0"),
        ("usuarios", "trial_inicio TEXT DEFAULT NULL"),
        ("usuarios", "plano TEXT DEFAULT 'trial'"),
        ("usuarios", "plano_expira TEXT DEFAULT NULL"),
        ("animais",  "foto_path TEXT DEFAULT NULL"),
        ("animais",  "observacoes TEXT DEFAULT ''"),
        ("animais",  "peso_alvo REAL DEFAULT 0"),
    ]
    with _conexao() as conn:
        for tabela, coluna_def in novas_colunas:
            try:
                conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna_def}")
            except sqlite3.OperationalError:
                pass


# ===========================================================================
# FUNÇÕES ORIGINAIS (100% preservadas)
# ===========================================================================

def adicionar_lote(nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte):
    with _conexao() as conn:
        cur = conn.execute(
            """INSERT INTO lotes (nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte),
        )
        return cur.lastrowid


def listar_lotes():
    with _conexao() as conn:
        rows = conn.execute(
            """SELECT id, nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte
               FROM lotes ORDER BY data_entrada DESC, id DESC"""
        ).fetchall()
        return [tuple(r) for r in rows]


def obter_lote(lote_id):
    with _conexao() as conn:
        row = conn.execute(
            """SELECT id, nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte
               FROM lotes WHERE id = ?""",
            (lote_id,),
        ).fetchone()
        return tuple(row) if row else None


def adicionar_animal(identificacao, idade, lote_id):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO animais (identificacao, idade, lote_id) VALUES (?, ?, ?)",
            (identificacao, idade, lote_id),
        )
        return cur.lastrowid


def listar_animais():
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id, identificacao, idade, lote_id FROM animais ORDER BY id"
        ).fetchall()
        return [tuple(r) for r in rows]


def listar_animais_por_lote(lote_id):
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id, identificacao, idade, lote_id FROM animais WHERE lote_id = ? ORDER BY id",
            (lote_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


def contar_animais_no_lote(lote_id):
    with _conexao() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM animais WHERE lote_id = ?", (lote_id,)
        ).fetchone()
        return row[0] if row else 0


def adicionar_pesagem(animal_id, peso, data):
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO pesagens (animal_id, peso, data) VALUES (?, ?, ?)",
            (animal_id, peso, data),
        )
        return cur.lastrowid


def listar_pesagens(animal_id):
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id, animal_id, peso, data FROM pesagens WHERE animal_id = ? ORDER BY data ASC, id ASC",
            (animal_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


def adicionar_ocorrencia(animal_id, data, tipo, descricao, gravidade, custo, dias_recuperacao, status):
    with _conexao() as conn:
        cur = conn.execute(
            """INSERT INTO ocorrencias
               (animal_id, data, tipo, descricao, gravidade, custo, dias_recuperacao, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (animal_id, data, tipo, descricao, gravidade, custo, dias_recuperacao, status),
        )
        return cur.lastrowid


def listar_ocorrencias(animal_id):
    with _conexao() as conn:
        rows = conn.execute(
            """SELECT id, animal_id, data, tipo, descricao,
                      gravidade, custo, dias_recuperacao, status
               FROM ocorrencias WHERE animal_id = ? ORDER BY data ASC, id ASC""",
            (animal_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


# ===========================================================================
# USUÁRIOS / AUTENTICAÇÃO
# ===========================================================================

def _hash_senha(senha: str, salt: str) -> str:
    return hashlib.sha256((salt + senha).encode()).hexdigest()


def criar_usuario(nome: str, email: str, senha: str,
                  perfil: str = "fazendeiro", fazenda_id=None) -> int:
    salt = secrets.token_hex(16)
    h = _hash_senha(senha, salt)
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, salt, perfil, fazenda_id) VALUES (?,?,?,?,?,?)",
            (nome, email, h, salt, perfil, fazenda_id),
        )
        return cur.lastrowid


def autenticar_usuario(email: str, senha: str):
    """Retorna dict com dados do usuário ou None se inválido."""
    with _conexao() as conn:
        row = conn.execute(
            "SELECT id, nome, email, senha_hash, salt, perfil, fazenda_id, ativo FROM usuarios WHERE email = ?",
            (email,),
        ).fetchone()
    if not row or not row["ativo"]:
        return None
    if _hash_senha(senha, row["salt"]) != row["senha_hash"]:
        return None
    return dict(id=row["id"], nome=row["nome"], email=row["email"],
                perfil=row["perfil"], fazenda_id=row["fazenda_id"])


def listar_usuarios():
    """Tupla: (id, nome, email, perfil, fazenda_id)"""
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id, nome, email, perfil, fazenda_id FROM usuarios WHERE ativo = 1 ORDER BY nome"
        ).fetchall()
        return [tuple(r) for r in rows]


def usuario_existe() -> bool:
    with _conexao() as conn:
        return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] > 0


def alterar_senha(usuario_id: int, nova_senha: str):
    salt = secrets.token_hex(16)
    h = _hash_senha(nova_senha, salt)
    with _conexao() as conn:
        conn.execute(
            "UPDATE usuarios SET senha_hash=?, salt=? WHERE id=?",
            (h, salt, usuario_id),
        )


# ===========================================================================
# FAZENDAS
# ===========================================================================

def adicionar_fazenda(nome: str, cidade: str = "", estado: str = "") -> int:
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO fazendas (nome, cidade, estado) VALUES (?, ?, ?)",
            (nome, cidade, estado),
        )
        return cur.lastrowid


def listar_fazendas():
    """Tupla: (id, nome, cidade, estado)"""
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id, nome, cidade, estado FROM fazendas ORDER BY nome"
        ).fetchall()
        return [tuple(r) for r in rows]


# ===========================================================================
# CALENDÁRIO SANITÁRIO
# ===========================================================================

def adicionar_vacina_agenda(lote_id: int, nome_vacina: str,
                             data_prevista: str, observacao: str = "") -> int:
    with _conexao() as conn:
        cur = conn.execute(
            """INSERT INTO vacinas_agenda (lote_id, nome_vacina, data_prevista, observacao)
               VALUES (?, ?, ?, ?)""",
            (lote_id, nome_vacina, data_prevista, observacao),
        )
        return cur.lastrowid


def registrar_vacina_realizada(vacina_id: int, data_realizada: str):
    with _conexao() as conn:
        conn.execute(
            "UPDATE vacinas_agenda SET data_realizada=?, status='realizado' WHERE id=?",
            (data_realizada, vacina_id),
        )


def listar_vacinas_agenda(lote_id=None):
    """Tupla: (id, lote_id, nome_vacina, data_prevista, data_realizada, status, observacao)"""
    with _conexao() as conn:
        if lote_id:
            rows = conn.execute(
                """SELECT id, lote_id, nome_vacina, data_prevista, data_realizada, status, observacao
                   FROM vacinas_agenda WHERE lote_id=? ORDER BY data_prevista""",
                (lote_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, lote_id, nome_vacina, data_prevista, data_realizada, status, observacao
                   FROM vacinas_agenda ORDER BY data_prevista"""
            ).fetchall()
        return [tuple(r) for r in rows]


def listar_vacinas_pendentes():
    """Vacinas com status pendente, ordenadas por data."""
    with _conexao() as conn:
        rows = conn.execute(
            """SELECT v.id, v.lote_id, l.nome, v.nome_vacina, v.data_prevista, v.status, v.observacao
               FROM vacinas_agenda v
               JOIN lotes l ON l.id = v.lote_id
               WHERE v.status = 'pendente'
               ORDER BY v.data_prevista"""
        ).fetchall()
        return [tuple(r) for r in rows]


# ===========================================================================
# ESTOQUE DE MEDICAMENTOS
# ===========================================================================

def adicionar_medicamento(nome: str, unidade: str, estoque_atual: float,
                           estoque_minimo: float, validade: str,
                           custo_unitario: float) -> int:
    with _conexao() as conn:
        cur = conn.execute(
            """INSERT INTO medicamentos (nome, unidade, estoque_atual, estoque_minimo, validade, custo_unitario)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nome, unidade, estoque_atual, estoque_minimo, validade, custo_unitario),
        )
        return cur.lastrowid


def listar_medicamentos():
    """Tupla: (id, nome, unidade, estoque_atual, estoque_minimo, validade, custo_unitario)"""
    with _conexao() as conn:
        rows = conn.execute(
            """SELECT id, nome, unidade, estoque_atual, estoque_minimo, validade, custo_unitario
               FROM medicamentos ORDER BY nome"""
        ).fetchall()
        return [tuple(r) for r in rows]


def atualizar_estoque(medicamento_id: int, quantidade: float):
    with _conexao() as conn:
        conn.execute(
            "UPDATE medicamentos SET estoque_atual = MAX(0, estoque_atual - ?) WHERE id=?",
            (quantidade, medicamento_id),
        )


def registrar_uso_medicamento(medicamento_id: int, animal_id: int,
                               data_uso: str, quantidade: float,
                               ocorrencia_id=None) -> int:
    atualizar_estoque(medicamento_id, quantidade)
    with _conexao() as conn:
        cur = conn.execute(
            """INSERT INTO medicamentos_uso (medicamento_id, animal_id, ocorrencia_id, data_uso, quantidade)
               VALUES (?, ?, ?, ?, ?)""",
            (medicamento_id, animal_id, ocorrencia_id, data_uso, quantidade),
        )
        return cur.lastrowid


def listar_medicamentos_criticos():
    """Medicamentos com estoque baixo ou validade próxima (30 dias)."""
    with _conexao() as conn:
        rows = conn.execute(
            """SELECT id, nome, unidade, estoque_atual, estoque_minimo, validade, custo_unitario
               FROM medicamentos
               WHERE estoque_atual <= estoque_minimo
                  OR (validade IS NOT NULL AND validade <= date('now', '+30 days'))
               ORDER BY validade"""
        ).fetchall()
        return [tuple(r) for r in rows]


# ===========================================================================
# CONTROLE REPRODUTIVO
# ===========================================================================

def adicionar_reproducao(animal_id: int, tipo_cobertura: str,
                          data_cio=None, data_diagnostico=None,
                          resultado="pendente", data_parto_previsto=None,
                          observacao="") -> int:
    with _conexao() as conn:
        cur = conn.execute(
            """INSERT INTO reproducao
               (animal_id, data_cio, tipo_cobertura, data_diagnostico,
                resultado, data_parto_previsto, observacao)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (animal_id, data_cio, tipo_cobertura, data_diagnostico,
             resultado, data_parto_previsto, observacao),
        )
        return cur.lastrowid


def atualizar_reproducao(repro_id: int, resultado: str,
                          data_parto_real=None, data_diagnostico=None,
                          data_parto_previsto=None):
    with _conexao() as conn:
        conn.execute(
            """UPDATE reproducao SET resultado=?,
               data_parto_real=COALESCE(?, data_parto_real),
               data_diagnostico=COALESCE(?, data_diagnostico),
               data_parto_previsto=COALESCE(?, data_parto_previsto)
               WHERE id=?""",
            (resultado, data_parto_real, data_diagnostico, data_parto_previsto, repro_id),
        )


def listar_reproducao(animal_id: int):
    """Tupla: (id, animal_id, data_cio, tipo_cobertura, data_diagnostico,
               resultado, data_parto_previsto, data_parto_real, observacao)"""
    with _conexao() as conn:
        rows = conn.execute(
            """SELECT id, animal_id, data_cio, tipo_cobertura, data_diagnostico,
                      resultado, data_parto_previsto, data_parto_real, observacao
               FROM reproducao WHERE animal_id=? ORDER BY data_cio DESC""",
            (animal_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


def listar_partos_previstos():
    """Partos previstos nos próximos 30 dias."""
    with _conexao() as conn:
        rows = conn.execute(
            """SELECT r.id, a.identificacao, l.nome, r.data_parto_previsto, r.tipo_cobertura
               FROM reproducao r
               JOIN animais a ON a.id = r.animal_id
               JOIN lotes   l ON l.id = a.lote_id
               WHERE r.resultado='positivo'
                 AND r.data_parto_real IS NULL
                 AND r.data_parto_previsto <= date('now', '+30 days')
               ORDER BY r.data_parto_previsto"""
        ).fetchall()
        return [tuple(r) for r in rows]


def taxa_prenhez_lote(lote_id: int) -> dict:
    with _conexao() as conn:
        total = conn.execute(
            """SELECT COUNT(DISTINCT r.animal_id) FROM reproducao r
               JOIN animais a ON a.id=r.animal_id WHERE a.lote_id=?""",
            (lote_id,),
        ).fetchone()[0]
        positivas = conn.execute(
            """SELECT COUNT(DISTINCT r.animal_id) FROM reproducao r
               JOIN animais a ON a.id=r.animal_id
               WHERE a.lote_id=? AND r.resultado='positivo'""",
            (lote_id,),
        ).fetchone()[0]
    return dict(total=total, positivas=positivas,
                taxa=(positivas / total * 100) if total > 0 else 0)


# ===========================================================================
# PIQUETES / PASTAGENS
# ===========================================================================

def adicionar_piquete(nome: str, area_ha: float,
                       capacidade_ua: float, fazenda_id=None) -> int:
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO piquetes (nome, area_ha, capacidade_ua, fazenda_id) VALUES (?,?,?,?)",
            (nome, area_ha, capacidade_ua, fazenda_id),
        )
        return cur.lastrowid


def listar_piquetes(fazenda_id=None):
    """Tupla: (id, fazenda_id, nome, area_ha, capacidade_ua)"""
    with _conexao() as conn:
        if fazenda_id:
            rows = conn.execute(
                "SELECT id, fazenda_id, nome, area_ha, capacidade_ua FROM piquetes WHERE fazenda_id=? ORDER BY nome",
                (fazenda_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, fazenda_id, nome, area_ha, capacidade_ua FROM piquetes ORDER BY nome"
            ).fetchall()
        return [tuple(r) for r in rows]


def alocar_lote_piquete(piquete_id: int, lote_id: int, data_entrada: str) -> int:
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO piquetes_historico (piquete_id, lote_id, entrada) VALUES (?,?,?)",
            (piquete_id, lote_id, data_entrada),
        )
        return cur.lastrowid


def liberar_piquete(piquete_id: int, data_saida: str):
    with _conexao() as conn:
        conn.execute(
            "UPDATE piquetes_historico SET saida=? WHERE piquete_id=? AND saida IS NULL",
            (data_saida, piquete_id),
        )


def historico_piquete(piquete_id: int):
    with _conexao() as conn:
        rows = conn.execute(
            """SELECT ph.id, l.nome, ph.entrada, ph.saida
               FROM piquetes_historico ph
               JOIN lotes l ON l.id=ph.lote_id
               WHERE ph.piquete_id=? ORDER BY ph.entrada DESC""",
            (piquete_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


# ===========================================================================
# TRIAL / PLANO
# ===========================================================================

from datetime import date as _date, timedelta as _td

TRIAL_DIAS = 30

def ativar_trial(usuario_id: int):
    """Define trial_inicio=hoje e plano_expira=hoje+30 para o usuário."""
    hoje = str(_date.today())
    expira = str(_date.today() + _td(days=TRIAL_DIAS))
    with _conexao() as conn:
        conn.execute(
            "UPDATE usuarios SET trial_inicio=?, plano='trial', plano_expira=? WHERE id=?",
            (hoje, expira, usuario_id),
        )


def obter_status_plano(usuario_id: int) -> dict:
    """
    Retorna dict com:
      plano          : 'trial' | 'pago' | 'expirado'
      dias_restantes : int (negativo se expirado)
      trial_inicio   : str | None
      plano_expira   : str | None
      pode_exportar  : bool  (False no trial / expirado)
      ativo          : bool
    """
    with _conexao() as conn:
        row = conn.execute(
            "SELECT plano, trial_inicio, plano_expira, ativo FROM usuarios WHERE id=?",
            (usuario_id,),
        ).fetchone()

    if not row:
        return dict(plano="expirado", dias_restantes=0, trial_inicio=None,
                    plano_expira=None, pode_exportar=False, ativo=False)

    plano        = row["plano"] or "trial"
    trial_inicio = row["trial_inicio"]
    plano_expira = row["plano_expira"]
    ativo        = bool(row["ativo"])

    hoje = _date.today()

    # Usuário que nunca teve trial_inicio → ativar agora
    if plano == "trial" and not trial_inicio:
        ativar_trial(usuario_id)
        trial_inicio = str(hoje)
        plano_expira = str(hoje + _td(days=TRIAL_DIAS))

    dias_restantes = 0
    if plano_expira:
        dias_restantes = (_date.fromisoformat(plano_expira) - hoje).days

    if plano == "pago":
        status = "pago"
        pode_exportar = True
    elif dias_restantes > 0:
        status = "trial"
        pode_exportar = False   # exportação liberada só no plano pago
    else:
        status = "expirado"
        pode_exportar = False

    return dict(
        plano=status,
        dias_restantes=dias_restantes,
        trial_inicio=trial_inicio,
        plano_expira=plano_expira,
        pode_exportar=pode_exportar,
        ativo=ativo,
    )


def converter_para_pago(usuario_id: int):
    """Marca o usuário como plano pago (sem expiração)."""
    with _conexao() as conn:
        conn.execute(
            "UPDATE usuarios SET plano='pago', plano_expira=NULL WHERE id=?",
            (usuario_id,),
        )


def listar_usuarios_trial_expirando(dias: int = 7) -> list:
    """Retorna usuários com trial expirando nos próximos `dias` dias."""
    limite = str(_date.today() + _td(days=dias))
    hoje   = str(_date.today())
    with _conexao() as conn:
        rows = conn.execute(
            """SELECT id, nome, email, plano_expira
               FROM usuarios
               WHERE plano='trial'
                 AND plano_expira IS NOT NULL
                 AND plano_expira >= ?
                 AND plano_expira <= ?
               ORDER BY plano_expira""",
            (hoje, limite),
        ).fetchall()
    return [tuple(r) for r in rows]


# ===========================================================================
# PRONTUÁRIO — FOTO / DOCUMENTOS DO ANIMAL
# ===========================================================================

def atualizar_animal_detalhes(animal_id: int, peso_alvo: float = None,
                               observacoes: str = None, foto_path: str = None):
    """Atualiza campos extras do animal sem sobrescrever os outros."""
    campos, vals = [], []
    if peso_alvo is not None:
        campos.append("peso_alvo=?"); vals.append(peso_alvo)
    if observacoes is not None:
        campos.append("observacoes=?"); vals.append(observacoes)
    if foto_path is not None:
        campos.append("foto_path=?"); vals.append(foto_path)
    if not campos:
        return
    vals.append(animal_id)
    with _conexao() as conn:
        conn.execute(f"UPDATE animais SET {', '.join(campos)} WHERE id=?", vals)


def obter_animal(animal_id: int) -> tuple | None:
    """
    Retorna tupla completa do animal:
    (id, identificacao, idade, lote_id, sexo, raca, peso_entrada,
     peso_alvo, observacoes, foto_path)
    """
    with _conexao() as conn:
        row = conn.execute(
            """SELECT id, identificacao, idade, lote_id,
                      COALESCE(sexo,'indefinido') as sexo,
                      COALESCE(raca,'') as raca,
                      COALESCE(peso_entrada,0) as peso_entrada,
                      COALESCE(peso_alvo,0) as peso_alvo,
                      COALESCE(observacoes,'') as observacoes,
                      COALESCE(foto_path,NULL) as foto_path
               FROM animais WHERE id=?""",
            (animal_id,),
        ).fetchone()
    return tuple(row) if row else None


# ===========================================================================
# PREVISÃO DE ABATE
# ===========================================================================

def calcular_previsao_abate(animal_id: int) -> dict:
    """
    Calcula data estimada de abate com base no GMD atual e peso alvo.
    Retorna dict com: gmd, peso_atual, peso_alvo, dias_restantes,
                      data_prevista, confianca
    """
    import pandas as pd
    from datetime import date as dt

    animal = obter_animal(animal_id)
    if not animal:
        return {}

    peso_alvo = animal[7]  # índice 7
    pesagens  = listar_pesagens(animal_id)

    if len(pesagens) < 2 or peso_alvo <= 0:
        return dict(erro="Necessário ≥ 2 pesagens e peso alvo definido")

    df = pd.DataFrame(pesagens, columns=["id","aid","peso","data"])
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values("data")

    peso_atual = df["peso"].iloc[-1]
    dias_hist  = (df["data"].iloc[-1] - df["data"].iloc[0]).days

    if dias_hist == 0:
        return dict(erro="Datas de pesagem idênticas")

    gmd = (peso_atual - df["peso"].iloc[0]) / dias_hist

    if gmd <= 0:
        return dict(erro="GMD negativo — animal perdendo peso")

    if peso_atual >= peso_alvo:
        return dict(
            gmd=round(gmd, 3), peso_atual=peso_atual,
            peso_alvo=peso_alvo, dias_restantes=0,
            data_prevista=str(dt.today()), confianca="pronto",
        )

    dias_rest = int((peso_alvo - peso_atual) / gmd)
    data_prev = dt.today() + _td(days=dias_rest)

    # confiança: baseada em nº de pesagens e consistência do GMD
    if len(pesagens) >= 5:
        confianca = "alta"
    elif len(pesagens) >= 3:
        confianca = "media"
    else:
        confianca = "baixa"

    return dict(
        gmd=round(gmd, 3),
        peso_atual=round(peso_atual, 1),
        peso_alvo=round(peso_alvo, 1),
        dias_restantes=dias_rest,
        data_prevista=str(data_prev),
        confianca=confianca,
    )
