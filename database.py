"""
database.py — Camada de persistência do Sistema de Gestão Pecuária.

Banco de dados: SQLite (arquivo local `pecuaria.db`).
Compatível com deploy no Streamlit Community Cloud:
  - O banco é criado automaticamente na primeira execução.
  - Em ambientes sem disco persistente (ex.: Streamlit Cloud free tier),
    o arquivo é recriado a cada reinício — para persistência real nesse
    cenário, substitua o path do DB por um volume montado ou use
    st.secrets + um banco externo (ex.: PostgreSQL no Supabase).

Índices de retorno (tuplas) — contrato com app_melhorado.py:

  lote      → (id[0], nome[1], descricao[2], data_entrada[3],
               qtd_comprada[4], qtd_recebida[5], transporte[6])

  animal    → (id[0], identificacao[1], idade[2], lote_id[3])

  pesagem   → (id[0], animal_id[1], peso[2], data[3])

  ocorrencia→ (id[0], animal_id[1], data[2], tipo[3], descricao[4],
               gravidade[5], custo[6], dias_recuperacao[7], status[8])
"""

import sqlite3
import os
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Configuração do caminho do banco
# ---------------------------------------------------------------------------
_DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DB_DIR, "pecuaria.db")


# ---------------------------------------------------------------------------
# Context manager de conexão
# ---------------------------------------------------------------------------
@contextmanager
def _conexao():
    """Abre conexão, aplica WAL para acesso concorrente, fecha ao sair."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")   # seguro para múltiplos leitores
    conn.execute("PRAGMA foreign_keys=ON")    # integridade referencial
    conn.row_factory = sqlite3.Row            # acesso por nome de coluna
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Criação das tabelas
# ---------------------------------------------------------------------------
def inicializar_banco() -> None:
    """Cria as tabelas caso não existam. Chame uma vez na inicialização do app."""
    with _conexao() as conn:
        conn.executescript("""
            -- ---------------------------------------------------------------
            -- LOTES
            -- ---------------------------------------------------------------
            CREATE TABLE IF NOT EXISTS lotes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                nome          TEXT    NOT NULL,
                descricao     TEXT    DEFAULT '',
                data_entrada  TEXT    NOT NULL,
                qtd_comprada  INTEGER NOT NULL DEFAULT 0,
                qtd_recebida  INTEGER NOT NULL DEFAULT 0,
                transporte    TEXT    DEFAULT ''
            );

            -- ---------------------------------------------------------------
            -- ANIMAIS
            -- ---------------------------------------------------------------
            CREATE TABLE IF NOT EXISTS animais (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                identificacao TEXT    NOT NULL,
                idade         INTEGER NOT NULL DEFAULT 0,
                lote_id       INTEGER NOT NULL,
                FOREIGN KEY (lote_id) REFERENCES lotes(id) ON DELETE CASCADE
            );

            -- ---------------------------------------------------------------
            -- PESAGENS
            -- ---------------------------------------------------------------
            CREATE TABLE IF NOT EXISTS pesagens (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id INTEGER NOT NULL,
                peso      REAL    NOT NULL,
                data      TEXT    NOT NULL,
                FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE
            );

            -- ---------------------------------------------------------------
            -- OCORRÊNCIAS
            -- ---------------------------------------------------------------
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

            -- ---------------------------------------------------------------
            -- ÍNDICES para acelerar as consultas mais frequentes
            -- ---------------------------------------------------------------
            CREATE INDEX IF NOT EXISTS idx_animais_lote
                ON animais(lote_id);

            CREATE INDEX IF NOT EXISTS idx_pesagens_animal
                ON pesagens(animal_id);

            CREATE INDEX IF NOT EXISTS idx_ocorrencias_animal
                ON ocorrencias(animal_id);
        """)


# ===========================================================================
# LOTES
# ===========================================================================

def adicionar_lote(
    nome: str,
    descricao: str,
    data_entrada: str,
    qtd_comprada: int,
    qtd_recebida: int,
    transporte: str,
) -> int:
    """Insere um novo lote. Retorna o id gerado."""
    with _conexao() as conn:
        cur = conn.execute(
            """
            INSERT INTO lotes (nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte),
        )
        return cur.lastrowid


def listar_lotes() -> list[tuple]:
    """
    Retorna todos os lotes ordenados por data de entrada (mais recente primeiro).
    Tupla: (id, nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte)
    """
    with _conexao() as conn:
        rows = conn.execute(
            """
            SELECT id, nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte
            FROM lotes
            ORDER BY data_entrada DESC, id DESC
            """
        ).fetchall()
        return [tuple(r) for r in rows]


def obter_lote(lote_id: int) -> tuple | None:
    """
    Retorna um lote pelo id ou None se não encontrado.
    Tupla: (id, nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte)
    """
    with _conexao() as conn:
        row = conn.execute(
            """
            SELECT id, nome, descricao, data_entrada, qtd_comprada, qtd_recebida, transporte
            FROM lotes
            WHERE id = ?
            """,
            (lote_id,),
        ).fetchone()
        return tuple(row) if row else None


# ===========================================================================
# ANIMAIS
# ===========================================================================

def adicionar_animal(identificacao: str, idade: int, lote_id: int) -> int:
    """Insere um novo animal. Retorna o id gerado."""
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO animais (identificacao, idade, lote_id) VALUES (?, ?, ?)",
            (identificacao, idade, lote_id),
        )
        return cur.lastrowid


def listar_animais() -> list[tuple]:
    """
    Retorna todos os animais.
    Tupla: (id, identificacao, idade, lote_id)
    """
    with _conexao() as conn:
        rows = conn.execute(
            "SELECT id, identificacao, idade, lote_id FROM animais ORDER BY id"
        ).fetchall()
        return [tuple(r) for r in rows]


def listar_animais_por_lote(lote_id: int) -> list[tuple]:
    """
    Retorna os animais de um lote específico.
    Tupla: (id, identificacao, idade, lote_id)
    """
    with _conexao() as conn:
        rows = conn.execute(
            """
            SELECT id, identificacao, idade, lote_id
            FROM animais
            WHERE lote_id = ?
            ORDER BY id
            """,
            (lote_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


def contar_animais_no_lote(lote_id: int) -> int:
    """Retorna a quantidade de animais cadastrados em um lote."""
    with _conexao() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM animais WHERE lote_id = ?", (lote_id,)
        ).fetchone()
        return row[0] if row else 0


# ===========================================================================
# PESAGENS
# ===========================================================================

def adicionar_pesagem(animal_id: int, peso: float, data: str) -> int:
    """Insere uma pesagem. Retorna o id gerado."""
    with _conexao() as conn:
        cur = conn.execute(
            "INSERT INTO pesagens (animal_id, peso, data) VALUES (?, ?, ?)",
            (animal_id, peso, data),
        )
        return cur.lastrowid


def listar_pesagens(animal_id: int) -> list[tuple]:
    """
    Retorna todas as pesagens de um animal, ordenadas por data.
    Tupla: (id, animal_id, peso, data)
    """
    with _conexao() as conn:
        rows = conn.execute(
            """
            SELECT id, animal_id, peso, data
            FROM pesagens
            WHERE animal_id = ?
            ORDER BY data ASC, id ASC
            """,
            (animal_id,),
        ).fetchall()
        return [tuple(r) for r in rows]


# ===========================================================================
# OCORRÊNCIAS
# ===========================================================================

def adicionar_ocorrencia(
    animal_id: int,
    data: str,
    tipo: str,
    descricao: str,
    gravidade: str,
    custo: float,
    dias_recuperacao: int,
    status: str,
) -> int:
    """Insere uma ocorrência. Retorna o id gerado."""
    with _conexao() as conn:
        cur = conn.execute(
            """
            INSERT INTO ocorrencias
                (animal_id, data, tipo, descricao, gravidade, custo, dias_recuperacao, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (animal_id, data, tipo, descricao, gravidade, custo, dias_recuperacao, status),
        )
        return cur.lastrowid


def listar_ocorrencias(animal_id: int) -> list[tuple]:
    """
    Retorna todas as ocorrências de um animal, ordenadas por data.
    Tupla: (id, animal_id, data, tipo, descricao, gravidade, custo, dias_recuperacao, status)
    """
    with _conexao() as conn:
        rows = conn.execute(
            """
            SELECT id, animal_id, data, tipo, descricao,
                   gravidade, custo, dias_recuperacao, status
            FROM ocorrencias
            WHERE animal_id = ?
            ORDER BY data ASC, id ASC
            """,
            (animal_id,),
        ).fetchall()
        return [tuple(r) for r in rows]
