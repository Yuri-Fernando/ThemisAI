# Changelog — Sensitive Data Scanner

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este módulo segue SemVer independente (`core/sensitive_data_scanner/`).

## [0.1.0] - 2026-08-20

### Added

- `scanner.py`: `scan_document(file_path) -> DocumentScanResult`, evolução do
  `pii_detection` para documentos inteiros (`.txt`, `.pdf` via `pypdf`,
  `.docx` via `python-docx`) em vez de só texto solto. Extrai o texto do
  documento (única responsabilidade nova) e repassa integralmente para
  `pii_detection.detect()` — nenhuma lógica de detecção de PII reimplementada.
  `.docx`: parágrafos e células de tabela são extraídos e concatenados.
- Novas dependências: `pypdf`, `python-docx` (`requirements-heavy.txt`).
- Contrato novo em `shared/schemas.py` (`DocumentScanResult`).
- Suíte de testes pytest (`tests/test_scanner.py`, 9 testes) contra
  documentos `.txt`/`.pdf`/`.docx` **reais** gerados em disco no próprio
  teste (`tests/conftest.py`: gerador de PDF 1.4 mínimo válido feito à mão —
  sem depender de nenhuma lib de geração de PDF, que não é dependência do
  projeto — e `python-docx` para os `.docx` de teste). Nenhum mock de
  extração de texto nem de `pii_detection.detect`.

### Notes

- **OCR não suportado nesta versão** (documentos escaneados / imagem dentro
  de PDF): o item original do ROADMAP citava "documentos/OCR" — OCR exigiria
  uma dependência de motor de reconhecimento óptico (ex. Tesseract) fora do
  conjunto atual de dependências do projeto. `scan_document` detecta esse
  caso (PDF sem texto extraível) e sinaliza em `extraction_notes`, mas não
  processa a imagem. TODO explícito de onda futura.
- Formatos adicionais (`.xlsx`, `.pptx`, `.html`, imagens) também ficam fora
  de escopo desta versão — `SUPPORTED_EXTENSIONS` documenta exatamente o que
  é suportado hoje.
