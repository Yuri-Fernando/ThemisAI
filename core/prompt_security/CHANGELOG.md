# Changelog — Prompt Security

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
versionamento em [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.1] - 2026-08-21 — Fix de dois gaps reais de detecção em PT (V5, item 1)

### Fixed
- `ignore_previous_instructions`: o regex esperava no máximo UMA palavra
  entre "ignor[ae]" e "instru[çc][õo]es" (`as`/`all`/`the`) — não cobria
  `"ignore TODAS AS instruções anteriores"` (duas palavras: "todas" + "as").
  Achado real por `core/red_team_lab` (payload `RT-01`). Corrigido
  adicionando a alternativa `todas?\s+(as\s+)?`.
- `other_users_data`: o regex esperava `"dados de outros usuários"`
  literalmente adjacente — não cobria `"dados PESSOAIS de outros
  usuários"` (palavra extra entre "dados" e "de"). Achado real por
  `core/red_team_lab` (payload `RT-06`). Corrigido permitindo uma palavra
  opcional entre "dados"/"informações" e "de outro(s) usuário(s)".

### Notes
- Taxa de detecção real medida por `red_team_lab` subiu de 50% para 67%
  (10/12 payloads) com este fix — ver `core/red_team_lab/CHANGELOG.md`
  `[0.1.1]`. Os dois gaps restantes (`RT-08` paráfrase, `RT-09` homoglifos)
  permanecem — ver seção "Known limitations" abaixo, ainda válida.

## [0.1.0] - 2026-08-19

### Added

- `scan(prompt: str) -> PromptSecurityResult` — scanner heurístico 100% offline
  e determinístico, sem chamadas de rede e sem modelo de ML.
- Detecção por regex categorizada em 4 técnicas:
  - `prompt_injection`: tentativas de sobrescrever/ignorar o system prompt
    (PT e EN), incluindo "ignore as instruções anteriores", "desconsidere
    tudo acima", "você agora é...", "esqueça suas regras", "sobrescreva o
    system prompt", marcador "novas instruções:", spoofing de role `[system]`.
  - `jailbreak`: personas conhecidas (DAN/"do anything now", STAN/AIM/DUDE),
    "modo desenvolvedor"/"developer mode", pedidos de resposta "sem
    filtros"/"without restrictions", roleplay explícito para burlar regras,
    menção direta a "jailbreak", "opposite day".
  - `pii_exfiltration`: pedidos para revelar system prompt, dados de
    treinamento, chaves/segredos/senhas, dados de outros usuários,
    variáveis de ambiente.
  - `obfuscation`: blobs longos em base64/hex (>= 32-40 chars contíguos),
    instruções explícitas de decodificação, uso excessivo (>=3) de
    caracteres zero-width/invisíveis.
- `score` em `[0.0, 1.0]`: começa em `1.0` e subtrai um peso por achado
  único (deduplicado por técnica+padrão), por severidade
  (`LOW=0.15, MEDIUM=0.55, HIGH=0.75, CRITICAL=0.95`), com piso em `0.0`.
- `is_safe`: `True` quando `score >= SAFE_THRESHOLD` (`SAFE_THRESHOLD = 0.5`,
  exportado de `core.prompt_security`), documentado em `scanner.py`. Os pesos
  de MEDIUM/HIGH/CRITICAL são propositalmente `> 0.5`: um único achado
  isolado dessas severidades já é suficiente para marcar `is_safe=False`
  (o scanner erra para o lado da cautela); apenas um achado LOW isolado
  mantém o prompt como seguro.
- Contratos de retorno importados de `shared/schemas.py`
  (`PromptSecurityFinding`, `PromptSecurityResult`, `RiskLevel`) — nenhum
  tipo redefinido neste módulo.
- Suíte pytest cobrindo as 4 categorias isoladamente, prompts limpos
  (vazio, whitespace, texto normal), prompts com múltiplas técnicas
  combinadas, determinismo (`scan(x) == scan(x)`), não duplicação de
  achados ao repetir o mesmo padrão, e limites de score.
- `notebooks/prompt_security_dev_log.ipynb` com exemplos reais, decisões de
  design e limitações conhecidas de evasão.

### Known limitations (honesto, não é robustez fingida)

- **Evasão trivial:** troca de sinônimos, paráfrase, erros de digitação
  proposital, ou tradução para um 3º idioma não coberto passam direto sem
  serem detectados — é um scanner de padrão léxico, não de intenção
  semântica.
- **Unicode homoglyphs/leetspeak:** substituição de caracteres (ex. "1gn0re",
  caracteres cirílicos parecidos com latinos) não é normalizada nem
  detectada, exceto o caso simples de excesso de caracteres zero-width.
- **Ofuscação em camadas:** um payload base64 dentro de outro encoding (ex.
  base64 de um base64, ou split em múltiplas mensagens) não é decodificado
  nem correlacionado entre turnos — o scanner é *stateless*, avalia um
  prompt por vez.
- **Sem aprendizado:** não há adaptação a novos ataques sem atualização
  manual das regras (ver TODO em `docs/decisions/` para roadmap V2 —
  Behavioral Monitoring e classificador treinado ficam fora do escopo V1).

[0.1.0]: #010---2026-08-19
