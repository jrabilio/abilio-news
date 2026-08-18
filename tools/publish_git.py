#!/usr/bin/env python3
"""
publish_git.py — Publica o repositório (raiz) no GitHub Pages (Layer 3 / WAT).

Estratégia de push robusta (funciona tanto local quanto na nuvem):
  1) tenta `git push origin main` como está — na nuvem o ambiente já tem
     credencial de git configurada no clone (credential helper), então isso
     funciona SEM depender do token do .env;
  2) se falhar, injeta a URL com o GITHUB_TOKEN do .env (ignorando qualquer
     credential helper) — caminho usado no ambiente local.

Isso evita o bug em que sobrescrever o origin com a URL do token faz o
credential helper do ambiente de nuvem interferir ("Invalid username or token").

Requer no .env (para o fallback): GITHUB_REPO, GITHUB_TOKEN.

Uso:
  python3 tools/publish_git.py --data 2026-07-22
  python3 tools/publish_git.py --data 2026-07-22 --dry-run   # commit local, sem push
"""

import argparse
import os
import subprocess
import sys

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
load_dotenv(os.path.join(ROOT, ".env"))


def git(*args, check=True, extra_env=None) -> subprocess.CompletedProcess:
    env = {**os.environ, **(extra_env or {})}
    return subprocess.run(["git", "-C", ROOT, *args],
                          capture_output=True, text=True, check=check, env=env)


def ensure_repo():
    if not os.path.isdir(os.path.join(ROOT, ".git")):
        git("init"); git("branch", "-M", "main")
    if not git("config", "user.email", check=False).stdout.strip():
        git("config", "user.email", "newsletter-bot@local")
        git("config", "user.name", "Newsletter Bot")
    os.makedirs(DOCS, exist_ok=True)
    nojekyll = os.path.join(DOCS, ".nojekyll")
    if not os.path.exists(nojekyll):
        open(nojekyll, "w").close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Publica o repositório no GitHub Pages.")
    parser.add_argument("--data", required=True, help="Data da edição (mensagem de commit).")
    parser.add_argument("--dry-run", action="store_true", help="Commita local, sem push.")
    args = parser.parse_args()

    ensure_repo()
    # Restrito de propósito, não use `add -A` aqui. Este repositório é PÚBLICO
    # (serve o GitHub Pages), e a rotina commita sozinha todo dia às 07h. Um
    # `add -A` varre a raiz inteira da árvore de trabalho do container, então
    # qualquer arquivo que apareça sujo entra no commit público. Foi esse o
    # cenário de 13/08/2026, quando um backup de .env com token ficou untracked
    # e visível ao add. O .gitignore fechou aquele caso específico; esta linha
    # fecha a classe inteira, porque só publica o que a edição do dia produz.
    git("add", "docs", "history.json")
    if not git("diff", "--cached", "--name-only").stdout.strip():
        print("Nada novo para publicar.")
        return 0
    git("commit", "-m", f"Edição {args.data}")
    print(f"Commit criado para a edição {args.data}.")

    if args.dry_run:
        print("--dry-run: push pulado.")
        return 0

    # 0) fetch antes de empurrar: sem isso, um HEAD detached com conhecimento
    # desatualizado do origin (comum em containers reaproveitados) faz o passo
    # 1 falhar por non-fast-forward mesmo quando o remoto está OK.
    git("fetch", "origin", "main", check=False,
        extra_env={"GIT_TERMINAL_PROMPT": "0"})

    # 1) push no origin como está (usa credencial do ambiente; não prompta).
    r = git("push", "origin", "HEAD:main", check=False,
            extra_env={"GIT_TERMINAL_PROMPT": "0"})
    if r.returncode == 0:
        print(f"Publicado (origin). {os.environ.get('NEWSLETTER_PUBLIC_URL', '')}")
        return 0
    print("Push no origin falhou; tentando com o token do .env...", file=sys.stderr)

    # 2) fallback: URL com token, ignorando credential helpers do ambiente.
    repo = os.environ.get("GITHUB_REPO", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not repo or not token:
        print("ERRO: push no origin falhou e não há GITHUB_REPO/GITHUB_TOKEN no .env.",
              file=sys.stderr)
        return 1
    url = f"https://x-access-token:{token}@github.com/{repo}.git"
    r2 = git("-c", "credential.helper=", "push", url, "HEAD:main", check=False,
             extra_env={"GIT_TERMINAL_PROMPT": "0"})
    if r2.returncode != 0:
        print(f"ERRO no push (token):\n{r2.stderr.replace(token, '***')}", file=sys.stderr)
        return 1

    public = os.environ.get("NEWSLETTER_PUBLIC_URL", f"https://github.com/{repo}")
    print(f"Publicado (token). {public}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
