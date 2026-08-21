# Changelog — PII Detection

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-08-19

### Added

- `detect(text: str) -> PIIDetectionResult`: motor de detecção de PII em
  texto livre em português, 100% offline e determinístico via regex.
- Detecção de CPF e CNPJ com validação de dígito verificador (algoritmo
  oficial), reduzindo falso positivo com outros números de 11/14 dígitos.
- Detecção de RG via janela de contexto (palavra-chave "RG" próxima ao
  número), dado que o formato de RG varia por estado e não possui dígito
  verificador universal.
- Detecção de e-mail, telefone (BR — com/sem DDD, com/sem `+55`) e CEP.
- Detecção de data de nascimento via regex de data + janela de contexto
  (ex. "data de nascimento", "nasc.", "DN").
- Heurística leve para nomes próprios: sequência de 2+ palavras
  capitalizadas fora de início de frase, com lista de stopwords em
  português para reduzir falso positivo.
- Classificação de cada achado em `DataCategory` conforme LGPD Art. 5º:
  CPF/RG/nome/e-mail/telefone/CEP/data de nascimento => `PERSONAL`;
  menções a dado de saúde, biometria, orientação sexual, religião,
  etnia/raça e opinião política/filiação sindical => `SENSITIVE`
  (detecção por palavra-chave, não por NLP real).
- Enriquecimento opcional via spaCy (`pt_core_news_sm`) para NER de
  pessoas, executado em best-effort dentro de `try/except` — nunca
  obrigatório para o caminho crítico funcionar ou para os testes passarem.
- Suíte de testes pytest cobrindo todos os tipos de dado do escopo V1,
  o contrato de saída (`PIIDetectionResult`/`PIIFinding` de
  `shared/schemas.py`) e casos negativos (texto limpo, contexto ausente).

### Fixed

- Detecção de dado sensível por palavra-chave agora é insensível a
  acentuação (`_fold`, mapa acento -> ASCII preservando offsets). Sem
  isso, texto real em português sem acento (comum em WhatsApp,
  formulários, logs mal codificados) gerava falso negativo — ex.
  "diagnostico de depressao" não batia com a palavra-chave "diagnóstico"
  nem "depressão". Bug encontrado ao executar exemplos reais no notebook
  de dev-log (não em teste sintético) e coberto por teste de regressão
  (`test_sensitive_mention_detected_without_accents`).

### Notes

- Nenhum tipo redefinido localmente — todos os contratos vêm de
  `shared/schemas.py` (`PIIFinding`, `PIIDetectionResult`, `DataCategory`).
- Limitações conhecidas documentadas em
  `notebooks/pii_detection_dev_log.ipynb` (seção Handoff Summary).
