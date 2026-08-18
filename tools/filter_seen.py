#!/usr/bin/env python3
"""
filter_seen.py — Remove candidatos já publicados (anti-repetição) (Layer 3 / WAT).

Compara uma lista de candidatos contra o histórico (history.json) por:
  - URL normalizada (nunca republicar o mesmo link), e
  - impressão digital do título dentro de uma janela de N dias (evita a mesma
    notícia vinda de outro veículo).

Uso:
  python3 tools/filter_seen.py --candidates .tmp/candidatos.json --dias 7 --out .tmp/novos.json

Entrada (--candidates): JSON com uma lista de itens, cada um com ao menos "titulo" e "url".
Saída: a mesma lista, apenas com os itens INÉDITOS. Também imprime um resumo no stderr.
"""

import argparse
import json
import os
import re
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.path.join(ROOT, "history.json")


def norm_url(u: str) -> str:
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    u = u.split("?")[0].split("#")[0]
    return u.rstrip("/")


def norm_titulo(t: str) -> str:
    t = (t or "").strip().lower()
    t = re.sub(r"[^\w\s]", "", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def load_history() -> list:
    if os.path.exists(HISTORY):
        with open(HISTORY, encoding="utf-8") as fh:
            return json.load(fh)
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Filtra candidatos já publicados.")
    parser.add_argument("--candidates", required=True, help="JSON com lista de candidatos.")
    parser.add_argument("--dias", type=int, default=7,
                        help="Janela (dias) para dedupe por título. URLs são sempre checadas.")
    parser.add_argument("--hoje", help="Data de referência AAAA-MM-DD (default: hoje).")
    parser.add_argument("--out", help="Salvar JSON filtrado neste caminho.")
    args = parser.parse_args()

    try:
        with open(args.candidates, encoding="utf-8") as fh:
            candidatos = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERRO ao ler {args.candidates}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(candidatos, list):
        print("ERRO: --candidates deve conter uma lista JSON.", file=sys.stderr)
        return 1

    hoje = date.fromisoformat(args.hoje) if args.hoje else date.today()
    limite = hoje - timedelta(days=args.dias)

    hist = load_history()
    urls_vistas = {h["url"] for h in hist}
    titulos_recentes = {
        h.get("titulo", "") for h in hist
        if h.get("data") and date.fromisoformat(h["data"]) >= limite
    }

    novos, descartados = [], 0
    for it in candidatos:
        u = norm_url(it.get("url", ""))
        t = norm_titulo(it.get("titulo", ""))
        if (u and u in urls_vistas) or (t and t in titulos_recentes):
            descartados += 1
            continue
        novos.append(it)

    payload = json.dumps(novos, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"{len(novos)} inéditos, {descartados} já publicados → {args.out}", file=sys.stderr)
    else:
        print(payload)
    print(f"inéditos={len(novos)} descartados={descartados}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
