# Radar Diário

Newsletter diária, gerada por automação e publicada em
**https://jrabilio.github.io/abilio-news/**.

## A regra deste repositório

> **Este repositório é PÚBLICO, e só contém a newsletter.** Ferramenta de negócio, análise,
> documento de cliente e qualquer dado interno vivem no repositório privado do workspace.
>
> A regra não depende de ninguém lembrar dela: o que separa os dois é a fronteira do repositório,
> não a disciplina de quem commita. Foi assim que ela passou a existir, em 17/08/2026 — antes, a
> newsletter dividia repositório com o motor de negócio, e o motor ficou público por efeito
> colateral de o Pages exigir repositório público no plano grátis.

Se você está prestes a trazer um arquivo novo para cá, a pergunta é uma só: **isso é a newsletter?**
Se não for, o lugar é o outro repositório.

## O que tem aqui

| Caminho | O que é |
|---|---|
| `docs/` | As edições publicadas, em HTML, mais o índice e o manifesto. É o que o Pages serve |
| `docs/itinerancia.html` | Calendário da itinerância dos caminhões (ago–out/2026). **Não é newsletter** — está aqui só porque o link precisa continuar no ar. É gerado por ferramenta que fica no repositório privado do workspace; para regerar, é lá |
| `tools/` | O pipeline: coleta, cotações, filtro de repetidos, montagem, publicação e notificação |
| `workflows/gerar_newsletter.md` | O SOP que a rotina da nuvem segue |
| `config/sources.json` | As seções e as buscas de cada uma |
| `history.json` | O que já foi publicado, para não repetir notícia dentro da janela de 7 dias |

## Como a edição do dia é feita

Uma rotina na nuvem dispara às 6h (BRT), segue `workflows/gerar_newsletter.md` e executa:

1. **Coleta** pelas buscas de `config/sources.json`, mais `tools/market_data.py` para as cotações
   (API aberta, sem credencial).
2. **Filtro** com `tools/filter_seen.py`, que consulta `history.json` e descarta URL já publicada e
   título parecido demais.
3. **Curadoria e resumo**, feitos pelo agente.
4. **Montagem** com `tools/build_edition.py`, que escreve `docs/editions/AAAA-MM-DD.html` e atualiza
   índice, manifesto e histórico.
5. **Publicação** com `tools/publish_git.py`, que commita e empurra. O push no `main` republica o
   Pages sozinho.
6. **Notificação** com `tools/notify_whatsapp.py`.

## Duas coisas que quem mexer aqui precisa saber

**O commit da rotina é restrito de propósito.** `tools/publish_git.py` faz
`git add docs history.json`, e **não** `git add -A`. A rotina roda sozinha todo dia num container, e
um `add -A` varreria a árvore inteira. Foi esse o cenário de um incidente em 13/08/2026. Não
reverter.

**A mensagem do WhatsApp tem teto de caracteres.** O gateway do CallMeBot corta acima de ~750 sem
avisar. `tools/notify_whatsapp.py` limita em 600, só inclui destaque inteiro que caiba, e sinaliza
`(+N seção(ões) no link acima)` — medindo o orçamento **com esse aviso já dentro**, senão ele mesmo
estoura o teto. Conferir com `--dry-run` antes de mexer.
