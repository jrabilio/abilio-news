# Instruções — repositório da newsletter

**Este repositório é PÚBLICO.** É o único público dos seis do Abilio, e é público por uma razão
só: o GitHub Pages exige repositório público no plano grátis, e é ele que serve
https://jrabilio.github.io/abilio-news/.

## A regra, e ela é uma só

> **Antes de trazer qualquer arquivo para cá: isso é a newsletter?**
> Se não for, não entra. Nem ferramenta de negócio, nem análise, nem documento de cliente, nem
> planilha, nem nada com valor de contrato, CNPJ ou identificador.

O motor de negócio mora no repositório **privado** do workspace (`jrabilio/abilio-git`), que no
disco é a pasta-mãe desta. Se o que você precisa fazer envolve painel, SALIC, marca, budget ou
carteira, **o lugar é lá, não aqui**.

**Por que existe essa separação, desde 18/08/2026.** Os dois dividiam um repositório, e o motor
ficou público por efeito colateral de a newsletter precisar do Pages. Uma regra de conduta
("código pode subir, dado não") foi tentada e durou uma noite — foi violada pelo mesmo push que a
criou. O que separa os dois agora é a fronteira do repositório, que não depende de ninguém lembrar.

## Como a edição do dia é feita

Uma Cloud Routine dispara às 6h (BRT), clona este repositório e segue
[workflows/gerar_newsletter.md](workflows/gerar_newsletter.md). O `README.md` descreve os seis
passos. Se você for mexer no pipeline, leia o SOP antes — ele carrega o aprendizado de cada falha
que já aconteceu em produção.

## Três coisas que já quebraram aqui

**O commit da rotina é restrito de propósito.** `tools/publish_git.py` faz
`git add docs history.json`, e **não** `git add -A`. A rotina roda sozinha num container todo dia;
um `add -A` varreria a árvore inteira para dentro de um commit público. Foi esse o cenário de um
incidente em 13/08/2026. Não reverter.

**A rotina sempre parte de um clone novo.** Então nada que dependa de estado local funciona.
`.tmp/` é gitignorado e não existe no clone — em 18/08/2026 o `market_data.py` e o `filter_seen.py`
morriam em `FileNotFoundError` por não criarem a pasta antes de escrever. Hoje criam. Ao escrever
ferramenta nova que gere arquivo, criar o diretório.

**A mensagem do WhatsApp tem teto.** O gateway do CallMeBot corta acima de ~750 caracteres sem
avisar. `tools/notify_whatsapp.py` limita em 600, só inclui destaque inteiro que caiba, e sinaliza
`(+N seção(ões) no link acima)` — **medindo o orçamento com esse aviso já dentro**. A primeira
versão media antes de anexá-lo e estourava pelo tamanho do próprio aviso. Conferir com
`--dry-run`, nunca disparando de verdade.

## Onde o link é resolvido

`tools/notify_whatsapp.py` resolve a URL pública nesta ordem: `NEWSLETTER_PUBLIC_URL` →
`GITHUB_REPO` → `git remote origin`. Não há `.env` versionado; localmente o `--dry-run` funciona
sem ele, resolvendo pelo remote. O envio real acontece na nuvem, com o segredo no prompt da rotina.
