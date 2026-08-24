# Workflow: Gerar Radar Diário (relatório matinal)

## Objetivo
Produzir e publicar um briefing matinal seccionado: manchete do dia, indicadores de
mercado e seções temáticas com 2–3 notícias **recentes e específicas** cada, resumidas,
sem repetir o que já saiu. Publicar no GitHub Pages e avisar no WhatsApp.

## Inputs necessários
- `config/sources.json` — seções, queries, roteamento do Gmail, regras de curadoria.
- `.env` com: `GITHUB_REPO`, `GITHUB_TOKEN`, `NEWSLETTER_PUBLIC_URL`,
  `CALLMEBOT_PHONE`, `CALLMEBOT_APIKEY`.
- Data da edição (default: hoje).

## Passos

### 1. Ler configuração e histórico
- Leia `config/sources.json` (seções na ordem do array `secoes`; regras em `curadoria`).
- Leia `site/manifest.json` e os `.md` das últimas edições (janela `janela_dedupe_dias`)
  para **não repetir** notícias já publicadas.

### 2. Indicadores de mercado
`tools/market_data.py --out .tmp/mercado.json` → injeta a lista em `edition.json.mercado`.

### 3. Coletar por seção (bruto → `.tmp/`)
Para cada seção **ativa**, rode suas `queries` via **WebSearch**:
- Priorize resultados das últimas **24–48h** (`curadoria.frescor_horas`). Descarte
  evergreen ('o que é', 'guia', 'tendências para o ano') e opinião genérica.
- Para os candidatos mais fortes, use `tools/scrape_single_site.py --url <url>` para
  puxar o **texto real** e resumir com fidelidade (não resuma pelo título).
- Guarde os candidatos por seção (ex.: `.tmp/coleta_<id>.json`).

**Gmail:** rode a `query` do config via conector; roteie por remetente conforme
`gmail.roteamento` (Agro Espresso → `agro`; Café com seu Dinheiro → `mercado_ma`).
Extraia manchete/trecho/link de cada edição recebida.

**Seção `carteira` (Carteira Ecotransforma — tarja de monitoramento):** trate diferente das
seções por `queries`. Ela tem a lista `empresas` (cada uma com `nome`, `setor` e às vezes
`aliases`). Para **cada empresa**, monte buscas em tempo de execução usando `nome` + `aliases`,
**sempre qualificando** por `setor`/"Brasil" para evitar homônimos (crítico p/ TAG, Grupo Sada,
Enercan, Imetame, Jaepel, Sylvamo, Compagás, Copergás). Busque três frentes via **WebSearch**:
(a) notícias/releases/resultados/expansões; (b) **licitações/editais** — incl. **editais de
patrocínio/cultura** e Lei Rouanet; (c) sinais **ESG**/socioambientais.
- **Curadoria FUP:** aplique `carteira.foco_fup` — priorize fatos que sinalizem verba/apetite
  para patrocínio (resultado/lucro, edital de patrocínio, expansão, compromisso ESG/cultural).
  Fato institucional forte ainda entra, mas o gancho de captação vem primeiro.
- No `resumo`, quando fizer sentido, explicite o **gancho de FUP** a partir do fato real
  (ex.: "resultado recorde no 2º tri — janela para pauta de patrocínio"). **Nunca invente.**

> Fonte que falhar (rede/rate limit) → logar e seguir. Nunca travar a edição inteira.

### 3.5. Filtrar já publicados (anti-repetição — determinístico)
Junte os candidatos coletados numa lista e passe por:
`tools/filter_seen.py --candidates .tmp/candidatos.json --dias <janela_dedupe_dias> --out .tmp/novos.json`
Isso remove qualquer URL já publicada (sempre) e títulos parecidos dentro da janela,
comparando contra `site/history.json`. Cure **somente** a partir de `.tmp/novos.json`.
(O histórico é gravado automaticamente pelo `build_edition.py` a cada edição.)

### 4. Selecionar + resumir (papel do agente)
Aplique `curadoria.regras`:
- Por seção: escolha até `max_itens` (2–3), resumo de **3–4 frases**, pt-BR neutro,
  sempre com `url` e `fonte` reais.
- Escolha **1 manchete**: o fato mais relevante do dia (de qualquer seção).
- **Omita** seções sem notícia relevante e recente (não preencher com enrolação).
- Dedupe contra o histórico do passo 1.

Monte `.tmp/edition.json`:
```json
{
  "data": "AAAA-MM-DD",
  "titulo": "Radar Diário",
  "manchete": {"titulo": "...", "resumo": "...", "url": "...", "fonte": "..."},
  "mercado": [ ...indicadores... ],
  "secoes": [
    {"titulo": "Mercado Financeiro & Aquisições", "itens": [
      {"titulo": "...", "resumo": "...", "url": "https://...", "fonte": "..."}
    ]},
    {"titulo": "Carteira Ecotransforma", "tarja": true, "itens": [
      {"titulo": "...", "resumo": "...", "url": "https://...", "fonte": "..."}
    ]}
  ]
}
```
- A **`carteira`** entra como **última** seção e leva `"tarja": true` (vira o bloco destacado
  no fim da edição). Com 18 empresas, respeite `max_itens` (5): escolha os **5 fatos mais
  relevantes do dia entre todas** — não force uma linha por empresa. Sem nada relevante, **omita**
  (seções sem `itens` já são descartadas no build).

### 5. Montar a edição
`tools/build_edition.py --input .tmp/edition.json` → gera
`site/editions/AAAA-MM-DD.html` + `.md`, atualiza `manifest.json` e `index.html`.
(Seções vazias são omitidas automaticamente.)

### 6. Publicar
`tools/publish_git.py --data AAAA-MM-DD` (use `--dry-run` para testar sem push).

### 7. Avisar no WhatsApp
`tools/notify_whatsapp.py --edition .tmp/edition.json`
Compõe automaticamente a mensagem-resumo (manchete + 1 destaque por seção + link direto
para a edição, usando `NEWSLETTER_PUBLIC_URL`). Use `--dry-run` para conferir antes.
O link vai **logo abaixo do título** (2ª linha), de propósito: o CallMeBot pode truncar
mensagens longas e, se o link ficasse no fim, sumiria. Se a env faltar, o tool emite AVISO
em stderr em vez de mandar em silêncio sem link.

## Saída esperada
- **Formato:** página HTML seccionada no GitHub Pages + versão Markdown.
- **Destino:** `NEWSLETTER_PUBLIC_URL` (link enviado no WhatsApp).

## Edge cases
- **Fonte fora do ar / rate limit** → pular, logar, continuar.
- **Dia fraco (poucas seções com notícia)** → publicar as que tiverem; avisar o dono se
  o total ficar muito baixo.
- **Só resultados evergreen numa seção** → melhor omitir a seção do que publicar algo atemporal.
- **Falha no push** → checar `GITHUB_TOKEN`.
- **WhatsApp não chega** → checar setup CallMeBot; a edição já está publicada (aviso reenviável).

## Aprendizados
_(Atualize: queries que trazem notícia fresca de verdade, veículos mais confiáveis por
seção, sites que exigem tratamento especial no scrape, etc.)_

- **2026-08-24:** A estratégia de 2026-08-14 (cortar seções inteiras e assinalar
  "(+N seção(ões) no link acima)" quando a lista não coubesse) resolvia o
  estouro do teto, mas o Abilio não queria uma contagem no fim da mensagem —
  queria os itens de verdade. Trocado por truncamento do **título do item**
  (não da seção): `compor_de_edicao` tenta larguras decrescentes até a lista
  inteira caber, cortando cada título com "…" em vez de omitir seções. Só se
  nem o truncamento mínimo (18 caracteres) couber tudo é que alguma linha
  fica de fora — e mesmo aí sem nota de contagem, o link no topo cobre o
  resto. Dias fracos (poucas seções) não são afetados: continuam com o
  título inteiro.
- **2026-08-14:** `notify_whatsapp.py` chegou truncada no meio de uma palavra
  ("Lei Rouane...") num dia forte, com as 6 seções + carteira preenchidas —
  a mensagem tinha 1058 caracteres (1130 bytes UTF-8), e o corte aconteceu
  por volta dos 746 caracteres (803 bytes). O gateway WhatsApp/CallMeBot
  trunca mensagens longas sem avisar (nenhum erro HTTP, envio "com sucesso").
  Corrigido: `compor_de_edicao` agora respeita um orçamento de
  `MAX_MSG_CHARS = 600` (margem de segurança abaixo do ponto observado de
  corte) — título, link e manchete (o essencial) sempre entram; a lista
  "Nesta edição" só inclui destaques inteiros que cabem no orçamento, e se
  algum ficar de fora aparece "(+N seção(ões) no link acima)" em vez de
  cortar a frase no meio. Dias fracos (poucas seções) continuam normais,
  sem a nota de corte.
- **2026-07-27:** `publish_git.py` falhava com "non-fast-forward" quando o
  container tinha HEAD detached e a branch `main` local desatualizada (push
  empurrava a ref local `main`, não o HEAD da edição nova). Corrigido: o tool
  agora faz `git fetch origin main` antes de empurrar e usa `HEAD:main`
  explícito nos dois caminhos (origin direto e fallback com token).
- **2026-07-27:** WebSearch às vezes gera resumos "hoje" com números/eventos
  não verificáveis num artigo específico (ex.: cotação de commodity sem link
  de origem, ou rumor de lançamento de modelo de IA vindo de blog/YouTube).
  Regra prática: só usar um candidato se houver uma URL de artigo real e
  datado batendo com o fato citado — descartar o resto, mesmo que pareça
  plausível.
- **2026-08-13:** Seção `carteira` (Carteira Ecotransforma) saiu em só 1 de 24
  edições — não é bug no código/config, é o prompt da tarefa agendada (fora
  deste repo) que lista "as 6 seções (mercado_ma, captacao, ia, esg, rouanet,
  agro)" e nunca menciona `carteira`. Corrigido no lado do usuário (prompt
  agendado atualizado com um passo 5b dedicado). Se a seção sumir de novo,
  suspeitar primeiro do prompt agendado, não deste arquivo.
- **2026-08-13:** Queries antigas de `rouanet` ("notícia edital novidade",
  "patrocínio cultural incentivado empresa anúncio") convergiam quase sempre
  para a mesma cobertura repetitiva de bastidor do MinC (portarias
  SEFIC/MINC de homologação/prorrogação, quase sempre via O Tempo) — Rouanet
  saiu em só ~46% dos dias, e várias vezes o candidato encontrado já tinha
  sido publicado com outra redação de título (escapando do dedupe por
  string). Testado `site:linkedin.com` como fonte alternativa: não funciona,
  o Google só indexa artigos "Pulse" evergreen, não posts de feed (LinkedIn
  bloqueia indexação). O que funcionou: trocar o foco de "notícia sobre a
  lei" para "edital/chamamento ABERTO buscando patrocinador" — queries nesse
  formato trouxeram editais municipais reais e específicos (Barbacena,
  FCCDA/Itabira) e revelaram dois agregadores úteis como fonte recorrente:
  `culturaemercado.com.br/category/editais` e `editaisculturais.com.br`.
  Queries atualizadas em `config/sources.json`.
