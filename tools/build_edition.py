#!/usr/bin/env python3
"""
build_edition.py — Monta uma edição da newsletter em HTML + Markdown (Layer 3 / WAT).

Recebe um JSON curado (itens já selecionados e resumidos pelo agente) e gera:
  - docs/editions/AAAA-MM-DD.html   (página da edição, pronta p/ GitHub Pages)
  - docs/editions/AAAA-MM-DD.md     (versão Markdown)
  - docs/manifest.json              (índice de todas as edições)
  - docs/index.html                 (home listando as edições, mais recente no topo)

Uso:
  python3 tools/build_edition.py --input .tmp/edition.json

Schema esperado do --input:
{
  "data": "2026-07-21",              # opcional; default = hoje (passe via --data)
  "titulo": "Minha Newsletter",
  "intro": "Texto de abertura (opcional)",
  "itens": [
    {"titulo": "...", "resumo": "...", "url": "https://...", "fonte": "Nome da fonte"}
  ]
}
"""

import argparse
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "docs")            # pasta publicada (GitHub Pages serve daqui)
EDITIONS = os.path.join(SITE, "editions")
MANIFEST = os.path.join(SITE, "manifest.json")
HISTORY = os.path.join(ROOT, "history.json")  # histórico fica fora da pasta pública

PAGE_CSS = """
:root {
  color-scheme: light dark;
  --paper:#f6f5f2; --panel:#fffefb; --ink:#1a1d21; --muted:#6b6e73;
  --line:rgba(20,22,26,.12); --line-strong:rgba(20,22,26,.24);
  --accent:#1f6f78; --up:#157f3b; --down:#c02b2b;
  --serif:Georgia,"Times New Roman",Cambria,serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
@media (prefers-color-scheme:dark){
  :root{ --paper:#14171a; --panel:#191d21; --ink:#e9e8e4; --muted:#9ba0a6;
    --line:rgba(255,255,255,.12); --line-strong:rgba(255,255,255,.24);
    --accent:#5fb6be; --up:#4fbe77; --down:#e86a6a; }
}
:root[data-theme="light"]{ --paper:#f6f5f2; --panel:#fffefb; --ink:#1a1d21; --muted:#6b6e73;
  --line:rgba(20,22,26,.12); --line-strong:rgba(20,22,26,.24);
  --accent:#1f6f78; --up:#157f3b; --down:#c02b2b; }
:root[data-theme="dark"]{ --paper:#14171a; --panel:#191d21; --ink:#e9e8e4; --muted:#9ba0a6;
  --line:rgba(255,255,255,.12); --line-strong:rgba(255,255,255,.24);
  --accent:#5fb6be; --up:#4fbe77; --down:#e86a6a; }

* { box-sizing:border-box; }
body { font-family:var(--sans); line-height:1.62; max-width:680px;
  margin:0 auto; padding:2.5rem 1.25rem 4rem; color:var(--ink); background:var(--paper);
  -webkit-font-smoothing:antialiased; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; text-underline-offset:2px; }

.eyebrow { font-size:.7rem; text-transform:uppercase; letter-spacing:.12em;
  color:var(--muted); font-weight:600; }
.back { display:inline-block; margin-bottom:1.75rem; font-size:.72rem;
  text-transform:uppercase; letter-spacing:.1em; }

header.nl { margin-bottom:1.5rem; }
header.nl .kicker { display:flex; justify-content:space-between; align-items:baseline;
  gap:1rem; border-bottom:2px solid var(--ink); padding-bottom:.5rem; }
header.nl h1 { font-family:var(--serif); font-weight:700; letter-spacing:-.01em;
  margin:0; font-size:2.5rem; line-height:1.02; text-wrap:balance; }
header.nl .data { font-family:var(--sans); font-size:.72rem; text-transform:uppercase;
  letter-spacing:.1em; color:var(--muted); white-space:nowrap; }

.mercado { display:grid; grid-template-columns:repeat(auto-fit,minmax(96px,1fr));
  border:1px solid var(--line); border-radius:2px; margin:1rem 0 2rem; overflow:hidden; }
.tick { padding:.6rem .7rem; text-align:left; border-right:1px solid var(--line);
  background:var(--panel); }
.tick:last-child { border-right:none; }
.tick .nome { font-size:.62rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }
.tick .valor { font-size:1.02rem; font-weight:600; font-variant-numeric:tabular-nums;
  margin-top:.1rem; }
.tick .var { font-size:.74rem; font-weight:600; font-variant-numeric:tabular-nums; }
.var.up{ color:var(--up); } .var.down{ color:var(--down); } .var.flat{ color:var(--muted); }

.intro { font-family:var(--serif); font-style:italic; font-size:1.18rem; line-height:1.5;
  color:var(--ink); margin:0 0 2.25rem; padding-left:1rem; border-left:2px solid var(--accent); }

.manchete { margin:0 0 2rem; padding:1.25rem 1.25rem 1.4rem; background:var(--panel);
  border:1px solid var(--line); border-top:3px solid var(--accent); border-radius:2px; }
.manchete .fonte { color:var(--accent); margin-bottom:.5rem; }
.manchete h2 { font-family:var(--serif); font-weight:700; font-size:1.75rem; line-height:1.1;
  margin:0 0 .6rem; letter-spacing:-.015em; text-wrap:balance; }
.manchete h2 a { color:var(--ink); }
.manchete h2 a:hover { color:var(--accent); text-decoration:none; }
.manchete .resumo { margin:0; font-size:1.05rem; }

.secao { margin:2.5rem 0 0; padding-bottom:.4rem; border-bottom:2px solid var(--ink);
  font-family:var(--sans); font-weight:700; font-size:.82rem; text-transform:uppercase;
  letter-spacing:.1em; }

.tarja { margin:2.5rem 0 1rem; padding:1.1rem 1.25rem 1.4rem; background:var(--panel);
  border:1px solid var(--line); border-left:4px solid var(--accent); border-radius:2px; }
.tarja .tarja-label { color:var(--accent); margin-bottom:.35rem; }
.tarja h2.tarja-titulo { font-family:var(--sans); font-weight:700; font-size:.95rem;
  text-transform:uppercase; letter-spacing:.08em; border:0; margin:.1rem 0 .4rem; }
.tarja .item:first-of-type { border-top:1px solid var(--line); }

.item { padding:1.4rem 0; border-top:1px solid var(--line); }
.item .fonte { margin-bottom:.35rem; }
.item h3 { font-family:var(--serif); font-weight:700; font-size:1.3rem; line-height:1.16;
  margin:0 0 .45rem; letter-spacing:-.01em; text-wrap:balance; }
.item h3 a { color:var(--ink); }
.item h3 a:hover { color:var(--accent); text-decoration:none; }
.item .resumo { margin:0; color:var(--ink); }

footer { margin-top:3rem; padding-top:1rem; border-top:2px solid var(--ink);
  font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted);
  display:flex; justify-content:space-between; }

ul.edicoes { list-style:none; padding:0; margin:0; }
ul.edicoes li { padding:1rem 0; border-top:1px solid var(--line); }
ul.edicoes a { font-family:var(--serif); font-size:1.2rem; color:var(--ink); }
ul.edicoes a:hover { color:var(--accent); text-decoration:none; }
ul.edicoes .data { display:block; font-family:var(--sans); font-size:.7rem;
  text-transform:uppercase; letter-spacing:.09em; color:var(--muted); margin-top:.15rem; }
@media (prefers-reduced-motion:reduce){ *{ transition:none!important; } }
""".strip()


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def norm_url(u: str) -> str:
    """Normaliza URL para comparação: sem protocolo, querystring, âncora ou barra final."""
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    u = u.split("?")[0].split("#")[0]
    return u.rstrip("/")


def norm_titulo(t: str) -> str:
    """Impressão digital do título: minúsculo, sem pontuação, espaços colapsados."""
    t = (t or "").strip().lower()
    t = re.sub(r"[^\w\s]", "", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def coletar_itens(ed: dict) -> list:
    """Todos os itens publicados (manchete + seções)."""
    itens = []
    if ed.get("manchete"):
        itens.append(ed["manchete"])
    for sec in _secoes(ed):
        itens.extend(sec["itens"])
    return itens


def registrar_historico(ed: dict) -> None:
    """Anexa as URLs/títulos publicados a history.json (dedup por URL)."""
    hist = []
    if os.path.exists(HISTORY):
        with open(HISTORY, encoding="utf-8") as fh:
            hist = json.load(fh)
    vistos = {h["url"] for h in hist}
    for it in coletar_itens(ed):
        u = norm_url(it.get("url", ""))
        if u and u not in vistos:
            hist.append({"url": u, "titulo": norm_titulo(it.get("titulo", "")),
                        "data": ed["data"]})
            vistos.add(u)
    with open(HISTORY, "w", encoding="utf-8") as fh:
        json.dump(hist, fh, ensure_ascii=False, indent=2)


def render_mercado_html(indicadores: list) -> str:
    if not indicadores:
        return ""
    ticks = []
    for i in indicadores:
        pct = i.get("variacao_pct")
        if pct is None:
            cls, seta, txt = "flat", "", ""
        elif pct > 0:
            cls, seta, txt = "up", "▲", f"+{pct:.2f}%"
        elif pct < 0:
            cls, seta, txt = "down", "▼", f"{pct:.2f}%"
        else:
            cls, seta, txt = "flat", "", "0,00%"
        ticks.append(
            f'<div class="tick"><div class="nome">{esc(i.get("nome", ""))}</div>'
            f'<div class="valor">{esc(i.get("valor", ""))}</div>'
            f'<div class="var {cls}">{seta} {txt}</div></div>'
        )
    return f'<div class="mercado">{"".join(ticks)}</div>'


def render_mercado_md(indicadores: list) -> str:
    if not indicadores:
        return ""
    partes = []
    for i in indicadores:
        pct = i.get("variacao_pct")
        sinal = "" if pct is None else (f" (+{pct:.2f}%)" if pct > 0 else f" ({pct:.2f}%)")
        partes.append(f'**{i.get("nome","")}** {i.get("valor","")}{sinal}')
    return "> " + " · ".join(partes) + "\n"


def _secoes(ed: dict) -> list:
    """Normaliza para uma lista de seções. Retrocompat: 'itens' plano vira 1 seção."""
    if ed.get("secoes"):
        return [s for s in ed["secoes"] if s.get("itens")]
    if ed.get("itens"):
        return [{"titulo": None, "itens": ed["itens"]}]
    return []


def _item_html(it: dict, tag: str, extra_cls: str = "") -> str:
    fonte = (f'<div class="eyebrow fonte">{esc(it.get("fonte", ""))}</div>'
             if it.get("fonte") else "")
    titulo = esc(it.get("titulo", "Sem título"))
    link = esc(it.get("url", ""))
    titulo_html = f'<a href="{link}">{titulo}</a>' if link else titulo
    return (f'<article class="{extra_cls}">{fonte}'
            f'<{tag}>{titulo_html}</{tag}>'
            f'<p class="resumo">{esc(it.get("resumo", ""))}</p></article>')


def render_manchete_html(m: dict) -> str:
    if not m:
        return ""
    return _item_html(m, "h2", "manchete")


def render_edition_html(ed: dict) -> str:
    blocos = []
    for sec in _secoes(ed):
        if sec.get("tarja"):
            itens = "".join(_item_html(it, "h3", "item") for it in sec["itens"])
            blocos.append(
                '<section class="tarja">'
                '<div class="eyebrow tarja-label">Monitoramento</div>'
                f'<h2 class="tarja-titulo">{esc(sec.get("titulo", ""))}</h2>'
                f'{itens}</section>')
            continue
        if sec.get("titulo"):
            blocos.append(f'<h2 class="secao">{esc(sec["titulo"])}</h2>')
        for it in sec["itens"]:
            blocos.append(_item_html(it, "h3", "item"))
    intro = f'<p class="intro">{esc(ed["intro"])}</p>' if ed.get("intro") else ""
    manchete = render_manchete_html(ed.get("manchete"))
    mercado = render_mercado_html(ed.get("mercado", []))
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(ed["titulo"])} — {esc(ed["data"])}</title>
<style>{PAGE_CSS}</style></head><body>
<a class="back" href="../index.html">← Edições anteriores</a>
<header class="nl"><div class="kicker">
<h1>{esc(ed["titulo"])}</h1>
<div class="data">{esc(ed["data"])}</div></div></header>
{manchete}
{mercado}
{intro}
{''.join(blocos)}
<footer><span>{esc(ed["titulo"])}</span><span>{esc(ed["data"])}</span></footer>
</body></html>"""


def _item_md(it: dict, nivel: str) -> list:
    titulo = it.get("titulo", "Sem título")
    url = it.get("url", "")
    head = f"{nivel} [{titulo}]({url})" if url else f"{nivel} {titulo}"
    out = [head]
    if it.get("fonte"):
        out.append(f"_Fonte: {it['fonte']}_")
    out += ["", it.get("resumo", ""), ""]
    return out


def render_edition_md(ed: dict) -> str:
    lines = [f'# {ed["titulo"]}', f'_{ed["data"]}_', ""]
    mercado = render_mercado_md(ed.get("mercado", []))
    if mercado:
        lines += [mercado, ""]
    if ed.get("manchete"):
        lines += ["## Manchete do dia", ""]
        lines += _item_md(ed["manchete"], "###")
    if ed.get("intro"):
        lines += [ed["intro"], ""]
    for sec in _secoes(ed):
        if sec.get("tarja"):
            lines += ["---", "", f'**📡 Monitoramento — {sec.get("titulo", "")}**', ""]
        elif sec.get("titulo"):
            lines += [f'## {sec["titulo"]}', ""]
        for it in sec["itens"]:
            lines += _item_md(it, "###")
    return "\n".join(lines)


def render_index_html(manifest: list, titulo_geral: str) -> str:
    items = []
    for e in manifest:  # já vem ordenado (mais recente primeiro)
        items.append(
            f'<li><a href="editions/{esc(e["arquivo"])}">{esc(e["titulo"])}</a>'
            f'<span class="data">{esc(e["data"])}</span></li>'
        )
    lista = "\n".join(items) if items else '<li class="vazio">Nenhuma edição ainda.</li>'
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo_geral)}</title>
<style>{PAGE_CSS}</style>
</head><body>
<header class="nl"><div class="kicker"><h1>{esc(titulo_geral)}</h1>
<div class="data">Arquivo</div></div></header>
<ul class="edicoes">{lista}</ul>
<footer><span>{esc(titulo_geral)}</span><span>Edições</span></footer>
</body></html>"""


def load_manifest() -> list:
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as fh:
            return json.load(fh)
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Monta uma edição da newsletter.")
    parser.add_argument("--input", required=True, help="JSON curado da edição.")
    parser.add_argument("--data", help="Data AAAA-MM-DD (sobrescreve o campo do JSON).")
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as fh:
            ed = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERRO ao ler {args.input}: {exc}", file=sys.stderr)
        return 1

    ed["data"] = args.data or ed.get("data")
    if not ed.get("data"):
        print("ERRO: informe a data no JSON ou via --data (AAAA-MM-DD).", file=sys.stderr)
        return 1
    n_itens = sum(len(s["itens"]) for s in _secoes(ed)) + (1 if ed.get("manchete") else 0)
    if n_itens == 0:
        print("ERRO: nenhum item na edição.", file=sys.stderr)
        return 1
    ed.setdefault("titulo", "Newsletter")

    os.makedirs(EDITIONS, exist_ok=True)
    arquivo = f'{ed["data"]}.html'
    with open(os.path.join(EDITIONS, arquivo), "w", encoding="utf-8") as fh:
        fh.write(render_edition_html(ed))
    with open(os.path.join(EDITIONS, f'{ed["data"]}.md'), "w", encoding="utf-8") as fh:
        fh.write(render_edition_md(ed))

    # Atualiza manifest (dedup por data), ordena desc, regenera index.
    manifest = [e for e in load_manifest() if e["data"] != ed["data"]]
    manifest.append({"data": ed["data"], "titulo": ed["titulo"], "arquivo": arquivo})
    manifest.sort(key=lambda e: e["data"], reverse=True)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_index_html(manifest, ed["titulo"]))

    registrar_historico(ed)

    print(json.dumps({
        "ok": True,
        "data": ed["data"],
        "itens": n_itens,
        "secoes": len(_secoes(ed)),
        "html": os.path.join("docs/editions", arquivo),
        "index": "docs/index.html",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
