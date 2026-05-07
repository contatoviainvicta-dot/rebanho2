"""
cepea.py — Cotação automática do boi gordo via Cepea / ESALQ.

Tenta buscar o preço atual do boi gordo pelo indicador CEPEA/ESALQ.
Faz fallback gracioso se não conseguir conectar (offline, timeout, etc.).
"""

import re
from datetime import date, datetime
from typing import Optional

try:
    import urllib.request as _req
    _URLLIB = True
except ImportError:
    _URLLIB = False


# URL pública do indicador diário Cepea boi gordo
_URL_CEPEA = "https://www.cepea.esalq.usp.br/br/indicador/boi-gordo.aspx"

# Regex para capturar o valor mais recente (ex: "195,42")
_RE_PRECO = re.compile(r'R\$\s*([\d]+[,.][\d]+)', re.IGNORECASE)
_RE_PRECO2 = re.compile(r'indicador.*?([\d]{2,3}[,.][\d]{2})', re.IGNORECASE | re.DOTALL)


def buscar_cotacao_cepea(timeout: int = 8) -> dict:
    """
    Tenta buscar a cotação atual do boi gordo no Cepea.
    Retorna dict com: preco (float), data (str), fonte (str), sucesso (bool), msg (str)
    """
    if not _URLLIB:
        return _fallback("urllib indisponível")

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
        req = _req.Request(_URL_CEPEA, headers=headers)
        with _req.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        preco = _extrair_preco(html)
        if preco and preco > 50:  # sanidade: boi gordo > R$50/@
            return dict(
                preco=preco,
                data=str(date.today()),
                fonte="cepea",
                sucesso=True,
                msg=f"Cotação obtida: R$ {preco:.2f}/@",
            )
        return _fallback("Preço não encontrado no HTML")

    except OSError as e:
        return _fallback(f"Sem acesso à internet: {e}")
    except Exception as e:
        return _fallback(f"Erro inesperado: {e}")


def _extrair_preco(html: str) -> Optional[float]:
    """Tenta extrair o preço do HTML do Cepea."""
    # Tenta padrões diferentes
    for pattern in [
        r'R\$\s*([\d]{2,3}[,.][\d]{2})',
        r'([\d]{3}[,.][\d]{2})',
    ]:
        matches = re.findall(pattern, html)
        for m in matches:
            try:
                val = float(m.replace(",", "."))
                if 100 < val < 500:  # faixa razoável para boi gordo @
                    return val
            except Exception:
                continue
    return None


def _fallback(msg: str) -> dict:
    return dict(preco=0.0, data=str(date.today()),
                fonte="indisponivel", sucesso=False, msg=msg)


def cotacao_com_cache(database_module) -> dict:
    """
    Retorna cotação do dia. Usa cache do banco se já buscou hoje.
    Se não encontrar, tenta Cepea. Se falhar, retorna última conhecida.
    """
    hoje = str(date.today())

    # Verificar cache do banco
    ultima = database_module.obter_ultima_cotacao()
    if ultima and ultima[1] == hoje:
        return dict(preco=ultima[2], data=ultima[1],
                    fonte=ultima[3], sucesso=True,
                    msg="Cache do banco de dados")

    # Tentar Cepea
    resultado = buscar_cotacao_cepea()
    if resultado["sucesso"]:
        database_module.salvar_cotacao(resultado["data"],
                                        resultado["preco"],
                                        resultado["fonte"])
        return resultado

    # Fallback: última cotação conhecida
    if ultima:
        return dict(preco=ultima[2], data=ultima[1],
                    fonte=f"{ultima[3]} (cache)",
                    sucesso=False,
                    msg=f"Cepea indisponível. Usando última cotação de {ultima[1]}")

    return resultado  # sem dados


def historico_grafico(cotacoes: list) -> dict:
    """
    Converte lista de tuplas (id, data, preco, fonte) em
    dict {datas: [...], precos: [...]} para plotar.
    """
    if not cotacoes:
        return dict(datas=[], precos=[])
    return dict(
        datas=[c[1] for c in cotacoes],
        precos=[c[2] for c in cotacoes],
    )
