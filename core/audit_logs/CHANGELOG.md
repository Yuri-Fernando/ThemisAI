# Changelog — audit_logs

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

## [0.1.0] - 2026-08-19

### Adicionado

- `AuditLogger`: classe parametrizável por caminho de arquivo (`log_path`),
  permitindo uso com arquivos temporários em testes.
  - `record_event(event_type, actor, payload) -> AuditEvent`: registra um
    evento imutável encadeado ao evento anterior via hash SHA-256
    (`hash = SHA256(prev_hash + event_type + actor + timestamp + json(payload, sort_keys=True))`).
    Persiste cada evento como uma linha JSON (`.jsonl`) em modo *append-only*.
  - `verify_chain() -> bool`: relê o arquivo inteiro e recalcula a cadeia de
    hashes em sequência, detectando qualquer adulteração de payload/actor/
    event_type/timestamp/hash ou quebra na sequência de `prev_hash`.
  - `read_events() -> list[AuditEvent]`: leitura auxiliar de todos os eventos
    gravados, na ordem em que foram escritos.
- `default_logger()`: função de conveniência em nível de módulo que retorna
  um `AuditLogger` apontando para o log padrão do projeto
  (`core/audit_logs/data/audit_log.jsonl`), para uso fácil por outros módulos.
- `GENESIS_HASH`: hash gênese fixo (`"0" * 64`) usado como `prev_hash` do
  primeiro evento de qualquer cadeia — documentado e exportado publicamente.
- Pasta `core/audit_logs/data/` (com `.gitkeep`) como destino padrão do log.
- Suíte de testes pytest (`core/audit_logs/tests/test_logger.py`) cobrindo:
  registro de evento único, registro de múltiplos eventos em sequência,
  adulteração de payload no meio da cadeia (teste crítico), adulteração
  direta de um hash, arquivo vazio/inexistente, e uso do hash gênese no
  primeiro evento.
- `notebooks/audit_logs_dev_log.ipynb`: dev log com objetivo, decisões de
  design, demonstração prática (encadeamento + detecção de adulteração) e
  handoff summary para os demais módulos.

### Corrigido

- Bug encontrado durante o desenvolvimento (via teste real, não hipotético):
  `verify_chain()` retornava `False` mesmo para uma cadeia intacta recém-criada.
  Causa raiz: `record_event()` calculava o hash usando
  `datetime.isoformat()` (sufixo `+00:00`), mas persistia o evento via
  `AuditEvent.model_dump_json()`, cuja serialização Pydantic v2 para
  datetimes usa sufixo `Z` — a string de timestamp relida do disco não era
  idêntica à usada no cálculo do hash, quebrando a verificação em 100% dos
  casos. Corrigido persistindo um dict construído manualmente com o mesmo
  `timestamp_iso` usado no hash, em vez de depender da serialização
  automática do Pydantic para o campo `timestamp`.

### Contratos utilizados

- `AuditEvent` e `AuditEventType` importados de `shared/schemas.py`
  (SCHEMA_VERSION 0.1.0) — nenhum tipo foi redefinido neste módulo.

### Limitações conhecidas (honestidade sobre segurança)

- Este é um hash-chain **local**, não uma blockchain distribuída: não há
  consenso, múltiplos nós, nem ancoragem externa (timestamping notarial,
  blockchain pública, etc.).
- Um atacante com acesso de **escrita** ao arquivo `.jsonl` e capacidade de
  rodar `verify_chain()` localmente pode adulterar um evento e recalcular
  toda a cadeia subsequente para que a verificação volte a passar — a
  garantia aqui é de **integridade contra erro/adulteração acidental ou
  detecção de adulteração não seguida de recálculo completo**, não uma prova
  criptográfica contra um adversário com controle total do disco.
  Mitigação real (fora de escopo do V1) exigiria replicação para um destino
  write-once (ex. WORM storage, log remoto append-only, ou blockchain real)
  — ver ROADMAP V2 "Blockchain Audit Layer".
