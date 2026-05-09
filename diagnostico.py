# diagnostico.py -- testar conexao Supabase
import streamlit as st

st.title("Diagnostico de Conexao")

st.subheader("1. Secrets")
try:
    db = st.secrets.get("database", {})
    url = db.get("url", "NAO ENCONTRADO")
    # Mascarar senha
    if "@" in url:
        partes = url.split("@")
        credenciais = partes[0].split(":")
        url_segura = ":".join(credenciais[:-1]) + ":***@" + partes[1]
    else:
        url_segura = url
    st.success(f"URL encontrada: {url_segura}")
except Exception as e:
    st.error(f"Erro ao ler secrets: {e}")

st.subheader("2. psycopg2")
try:
    import psycopg2
    st.success(f"psycopg2 instalado: {psycopg2.__version__}")
except ImportError as e:
    st.error(f"psycopg2 NAO disponivel: {e}")

st.subheader("3. SQLAlchemy")
try:
    import sqlalchemy
    st.success(f"SQLAlchemy instalado: {sqlalchemy.__version__}")
except ImportError as e:
    st.error(f"SQLAlchemy NAO disponivel: {e}")

st.subheader("4. Conexao direta")
try:
    url = st.secrets["database"]["url"]
    import psycopg2
    conn = psycopg2.connect(url, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT version()")
    versao = cur.fetchone()[0]
    conn.close()
    st.success(f"Conexao OK! PostgreSQL: {versao[:50]}")
except Exception as e:
    st.error(f"Erro na conexao: {e}")
