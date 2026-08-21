# status/

Um arquivo `<modulo>.json` por módulo, escrito pelo próprio módulo ao final do
seu desenvolvimento. Formato:

```json
{
  "module": "pii_detection",
  "version": "0.1.0",
  "status": "done",
  "tests_total": 18,
  "tests_passed": 18,
  "capabilities": ["Regex CPF/CNPJ/e-mail/telefone", "NER spaCy pt_core_news_sm", "Classificação LGPD Art. 5º"],
  "notebook": "notebooks/pii_detection_dev_log.ipynb",
  "notes": "Sem chamadas externas; modelo spaCy baixado localmente.",
  "updated_at": "2026-08-19T00:00:00"
}
```

`status` ∈ {"planned", "in_progress", "done", "blocked"}.

Consumido por [`notebooks/00_master_pipeline.ipynb`](../notebooks/00_master_pipeline.ipynb)
para montar o dashboard agregado do projeto, e pelo orquestrador para consolidar
o `CHANGELOG.md` raiz ao final de cada onda.
