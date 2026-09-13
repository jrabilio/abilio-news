#!/usr/bin/env python3
"""
verify_pages.py — Confirma que o GitHub Pages publicou a edição do dia antes
do aviso no WhatsApp (Layer 3.5, entre publish_git.py e notify_whatsapp.py).

Por quê existe: publish_git.py garante que o *push* chegou ao GitHub, não que
o Pages de fato rebuildou o site. Em 13/09/2026 o push da edição do dia
(commit cd4c755) chegou ao `main` normalmente, mas o build automático do
Pages nunca disparou — sem erro, sem log, apenas ausente. Coincidiu com uma
degradação do GitHub Actions no mesmo horário (confirmada e já resolvida em
githubstatus.com), e o hook interno de build do Pages depende do Actions
para disparar; nesse tipo de degradação o evento é descartado, não fica
"falhou" — só não é criado. O WhatsApp saiu mesmo assim, com link 404.

O que este script faz: espera o Pages publicar o HTML da edição (poll no
próprio link público). Se não publicar sozinho dentro do prazo, força um
novo push (retrigger: toca um marcador em docs/ e empurra de novo) — como
o build do Pages é sempre da árvore inteira do HEAD, isso repete a tentativa
de build sem duplicar nem alterar a edição já publicada. Só then a rotina
segue para o aviso no WhatsApp. Se mesmo assim não publicar, sai com erro
para a rotina RELATAR a falha (nunca mandar o link no WhatsApp sem checar).

Uso:
  python3 tools/verify_pages.py --data 2026-09-13
  python3 tools/verify_pages.py --data 2026-09-13 --max-wait-s 240 --poll-s 15
"""

import argparse
import os
import subprocess
import sys
import time

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))


def git(*args, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", ROOT, *args],
                           capture_output=True, text=True, check=check)


def public_base() -> str:
    url = os.environ.get("NEWSLETTER_PUBLIC_URL", "").strip()
    if url:
        return url.rstrip("/")
    repo = os.environ.get("GITHUB_REPO", "").strip()
    if repo and "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}"
    r = git("remote", "get-url", "origin", check=False)
    remote = r.stdout.strip()
    if "github.com" in remote:
        path = remote.split("github.com")[-1].lstrip(":/").removesuffix(".git")
        if "/" in path:
            owner, name = path.split("/", 1)
            return f"https://{owner}.github.io/{name}"
    return ""


def edition_url(data: str) -> str:
    return f"{public_base()}/editions/{data}.html"


def is_live(url: str, timeout: int = 10) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def retrigger() -> bool:
    """Empurra um novo commit trivial só para reacordar o hook de build do
    Pages. Não toca docs/editions nem history.json — nada de conteúdo muda,
    só o marcador. O build do Pages sempre usa o HEAD inteiro, então a
    edição do dia (já commitada por publish_git.py) sai no mesmo build."""
    marker = os.path.join(ROOT, "docs", ".pages-heartbeat")
    with open(marker, "w") as f:
        f.write(f"{time.time()}\n")
    git("add", "docs/.pages-heartbeat")
    if not git("diff", "--cached", "--name-only").stdout.strip():
        return False
    git("commit", "-m", "Retrigger Pages build (deploy check)")
    git("fetch", "origin", "main", check=False)
    r = git("push", "origin", "HEAD:main", check=False)
    if r.returncode != 0:
        print(f"Retrigger: push falhou:\n{r.stderr}", file=sys.stderr)
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Confirma o deploy do Pages antes do WhatsApp.")
    ap.add_argument("--data", required=True, help="Data da edição (AAAA-MM-DD).")
    ap.add_argument("--max-wait-s", type=int, default=180, help="Prazo total de espera.")
    ap.add_argument("--poll-s", type=int, default=15, help="Intervalo entre checagens.")
    args = ap.parse_args()

    url = edition_url(args.data)
    if not url.startswith("http"):
        print("ERRO: não consegui resolver a URL pública (NEWSLETTER_PUBLIC_URL/GITHUB_REPO/remote).",
              file=sys.stderr)
        return 1

    deadline = time.time() + args.max_wait_s
    retrigger_at = time.time() + args.max_wait_s / 2
    retried = False

    while True:
        if is_live(url):
            print(f"OK: Pages publicou {url}")
            return 0
        now = time.time()
        if now >= deadline:
            break
        if not retried and now >= retrigger_at:
            print("Pages ainda não publicou a edição; forçando retrigger...", file=sys.stderr)
            retried = retrigger()
        time.sleep(min(args.poll_s, max(0, deadline - time.time())))

    print(f"ERRO: {url} não ficou disponível em {args.max_wait_s}s"
          f"{' mesmo após retrigger' if retried else ' (retrigger não chegou a rodar)'}.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
