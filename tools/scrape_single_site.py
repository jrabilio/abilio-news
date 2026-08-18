#!/usr/bin/env python3
"""
scrape_single_site.py — Raspa uma URL e extrai texto/links úteis (Layer 3 / WAT).

Duas formas de uso:
  # Um artigo direto → título + texto limpo
  python3 tools/scrape_single_site.py --url https://exemplo.com/artigo

  # Uma página de listagem → lista de links de artigos
  python3 tools/scrape_single_site.py --url https://exemplo.com/blog --links

Saída: JSON no stdout. Opcionalmente salva em arquivo com --out.
"""

import argparse
import json
import sys
import warnings
from urllib.parse import urljoin, urlparse

warnings.filterwarnings("ignore")  # silencia NotOpenSSLWarning do urllib3

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )
}
TIMEOUT = 20


def fetch(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def extract_article(soup: BeautifulSoup, url: str) -> dict:
    """Extrai título e texto principal (heurística simples baseada em <p>)."""
    # Título: <title>, og:title ou <h1>
    title = None
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.h1:
        title = soup.h1.get_text(strip=True)

    # Remove ruído
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    # Texto: concatena parágrafos com conteúdo relevante
    paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paras = [p for p in paras if len(p) > 40]
    text = "\n\n".join(paras)

    return {"url": url, "title": title, "text": text, "chars": len(text)}


def extract_links(soup: BeautifulSoup, base_url: str) -> dict:
    """Extrai links de artigos (mesmo domínio, deduplicados)."""
    base_domain = urlparse(base_url).netloc
    seen = set()
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"].split("#")[0])
        if urlparse(href).netloc != base_domain:
            continue
        if href in seen or href.rstrip("/") == base_url.rstrip("/"):
            continue
        text = a.get_text(" ", strip=True)
        if len(text) < 15:  # ignora menus/botões curtos
            continue
        seen.add(href)
        links.append({"url": href, "titulo": text})
    return {"url": base_url, "total": len(links), "links": links}


def main() -> int:
    parser = argparse.ArgumentParser(description="Raspa uma URL (artigo ou listagem).")
    parser.add_argument("--url", required=True, help="URL a raspar.")
    parser.add_argument("--links", action="store_true",
                        help="Extrair links de uma página de listagem.")
    parser.add_argument("--out", help="Salvar JSON neste caminho (ex.: .tmp/scrape.json).")
    args = parser.parse_args()

    try:
        soup = fetch(args.url)
        result = extract_links(soup, args.url) if args.links else extract_article(soup, args.url)
    except requests.RequestException as exc:
        print(f"ERRO de rede em {args.url}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERRO ao processar {args.url}: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"Salvo em {args.out} ({result.get('chars', result.get('total', 0))} unid.)")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
