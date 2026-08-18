#!/usr/bin/env python3
"""
market_data.py — Coleta indicadores de mercado para o topo da newsletter (Layer 3 / WAT).

Moedas via AwesomeAPI (grátis, sem chave); índices via Yahoo Finance (grátis).
Falha graciosamente: se um indicador não responder, ele é omitido e os demais seguem.

Uso:
  python3 tools/market_data.py                      # imprime JSON
  python3 tools/market_data.py --out .tmp/mercado.json

Saída (JSON):
{
  "atualizado_em": "2026-07-21 17:00",
  "indicadores": [
    {"nome": "Dólar", "valor": "R$ 5,096", "variacao_pct": -0.40, "simbolo": "USD/BRL"},
    ...
  ]
}
"""

import argparse
import json
import sys
import warnings

warnings.filterwarnings("ignore")

import requests

TIMEOUT = 20
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# Moedas buscadas na AwesomeAPI (par -> rótulo).
MOEDAS = [
    ("USD-BRL", "Dólar", "USD/BRL"),
    ("EUR-BRL", "Euro", "EUR/BRL"),
]

# Índices buscados no Yahoo Finance (símbolo -> rótulo).
INDICES = [
    ("^BVSP", "Ibovespa", "Brasil"),
    ("^GSPC", "S&P 500", "EUA"),
    ("^IXIC", "Nasdaq", "EUA"),
]


def fmt_brl(v: float) -> str:
    s = f"{v:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def fmt_pontos(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


def coletar_moedas() -> list:
    pares = ",".join(m[0] for m in MOEDAS)
    out = []
    try:
        r = requests.get(f"https://economia.awesomeapi.com.br/last/{pares}",
                         headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        print(f"AVISO: moedas indisponíveis: {exc}", file=sys.stderr)
        return out
    for par, nome, simbolo in MOEDAS:
        key = par.replace("-", "")
        d = data.get(key)
        if not d:
            continue
        try:
            out.append({
                "nome": nome,
                "valor": fmt_brl(float(d["bid"])),
                "variacao_pct": round(float(d["pctChange"]), 2),
                "simbolo": simbolo,
            })
        except (KeyError, ValueError):
            continue
    return out


def coletar_indices() -> list:
    out = []
    for simbolo, nome, regiao in INDICES:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}"
            r = requests.get(url, params={"interval": "1d", "range": "1d"},
                            headers=UA, timeout=TIMEOUT)
            r.raise_for_status()
            meta = r.json()["chart"]["result"][0]["meta"]
            preco = float(meta["regularMarketPrice"])
            anterior = float(meta.get("previousClose") or meta.get("chartPreviousClose") or preco)
            var = ((preco - anterior) / anterior * 100) if anterior else 0.0
            out.append({
                "nome": nome,
                "valor": fmt_pontos(preco),
                "variacao_pct": round(var, 2),
                "simbolo": regiao,
            })
        except Exception as exc:
            print(f"AVISO: índice {nome} indisponível: {exc}", file=sys.stderr)
            continue
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta indicadores de mercado.")
    parser.add_argument("--out", help="Salvar JSON neste caminho.")
    args = parser.parse_args()

    indicadores = coletar_moedas() + coletar_indices()
    if not indicadores:
        print("ERRO: nenhum indicador coletado (rede?).", file=sys.stderr)
        return 1

    result = {"indicadores": indicadores}
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"Salvo em {args.out} ({len(indicadores)} indicadores).")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
