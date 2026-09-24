"""Parser estrutural determinístico de texto normativo brasileiro.

Converte texto corrido (uma unidade por linha, como sai do HTML compilado do
Planalto depois de normalizado) numa lista de `LegalUnit` endereçáveis:

    art-20                    → caput do Art. 20
    art-20.par-1              → § 1º do Art. 20
    art-20.par-unico          → Parágrafo único
    art-5.inc-LXXVIII         → inciso LXXVIII do caput do Art. 5º
    art-20.par-1.inc-II.ali-a → alínea a do inciso II do § 1º

Segue a hierarquia da LC 95/1998, art. 10 (artigo > parágrafo > inciso >
alínea > item). Anotações editoriais do Planalto — "(Redação dada pela Lei nº
13.853, de 2019)", "(Incluído pela ...)", "(Revogado)", "(VETADO)", "Vigência"
— são removidas do texto comparável e guardadas em `annotations`; os atos
alteradores citados nelas vão para `amended_by`.

**Escopo honesto**: é um parser de regras (regex), não um parser jurídico
completo. Linhas que não casam com nenhum marcador são tratadas como
continuação da unidade corrente; texto antes do primeiro artigo (ementa,
preâmbulo) não vira unidade e reduz `coverage` — que é exatamente o sinal
usado como confiança estrutural em `analyze_legal_change`.
"""
from __future__ import annotations

import re
import unicodedata

from shared.schemas import LegalUnit, LegalUnitType

# Hierarquia de agrupamento (não são dispositivos, só contexto de navegação).
_HEADING_RE = re.compile(
    r"^(PARTE|LIVRO|T[ÍI]TULO|CAP[ÍI]TULO|SE[ÇC][ÃA]O|Se[çc][ãa]o|SUBSE[ÇC][ÃA]O|Subse[çc][ãa]o)\s+([IVXLCDM]+|[ÚU]NIC[OA]|GERAL|ESPECIAL|PRELIMINAR)\b.*$"
)
_HEADING_LEVEL = {
    "PARTE": 0, "LIVRO": 1, "TITULO": 2, "CAPITULO": 3, "SECAO": 4, "SUBSECAO": 5,
}

_ARTICLE_RE = re.compile(
    r"^Art\.?\s*(\d{1,3}(?:\.\d{3})*)\s*(?:º|°|o(?=[\s\.\-–—]))?(?:-([A-Z]{1,2})(?![A-Za-zÀ-ú]))?\s*(?:[\.\-–—](?!\d))?\s*(.*)$"
)
_PARAGRAPH_RE = re.compile(
    r"^§\s*(\d+)\s*(?:º|°|o(?=[\s\.\-–—]))?(?:-([A-Z]{1,2})(?![A-Za-zÀ-ú]))?\s*(?:[\.\-–—](?!\d))?\s*(.*)$"
)
_SOLE_PARAGRAPH_RE = re.compile(r"^Par[áa]grafo\s+[úu]nico\s*[\.\-–—:]?\s*(.*)$", re.IGNORECASE)
# Sufixo de dispositivo intercalado ("I-A", "Art. 5º-A") vem COLADO ao número;
# com espaço ("I - A empresa...") é só o início do texto do inciso I.
_INCISO_RE = re.compile(r"^([IVXLCDM]+)(?:-([A-Z]{1,2}))?\s*[\-–—]\s*(.*)$")
_ALINEA_RE = re.compile(r"^([a-z])(?:-\s*([A-Z]))?\)\s*(.*)$")
_ITEM_RE = re.compile(r"^(\d{1,2})\.\s+(.*)$")
# Marcador que ficou sozinho na linha por quebra do HTML de origem ("Art." / "§").
_DANGLING_MARKER_RE = re.compile(r"^(?:Art\.?|§|Par[áa]grafo)$", re.IGNORECASE)
# A CF reinicia a numeração de artigos no ADCT — vira um namespace próprio.
_NAMESPACE_RE = re.compile(r"^ATO\s+DAS\s+DISPOSI[ÇC][ÕO]ES\s+CONSTITUCIONAIS\s+TRANSIT[ÓO]RIAS\b", re.IGNORECASE)

# Anotações editoriais (entre parênteses) que o Planalto intercala no texto.
_ANNOTATION_RE = re.compile(
    r"\((?:\s*)(?:Reda[çc][ãa]o\s+dada|Inclu[íi]d[oa]|Acrescid[oa]|Acrescentad[oa]|Revogad[oa]|"
    r"Renumerad[oa]|Vide|Vig[êe]ncia|Vetad[oa]|VETADO|Promulga[çc][ãa]o|Regulamento|Regulamenta[çc][ãa]o|"
    r"Express[ãa]o\s+suspensa|Suspens[oa]|Produ[çc][ãa]o\s+de\s+efeito|Convers[ãa]o|Declarad[oa]|Execu[çc][ãa]o\s+suspensa)"
    r"[^()]*(?:\([^()]*\)[^()]*)*\)",
    re.IGNORECASE,
)
_TRAILING_NOISE_RE = re.compile(r"(?:\s*\b(?:Vig[êe]ncia(?:\s+encerrada)?|Mensagem\s+de\s+veto|Texto\s+compilado)\b\s*)+$", re.IGNORECASE)
_AMENDING_ACT_RE = re.compile(
    r"(Lei\s+Complementar|Lcp|Lei|Decreto-Lei|Decreto|Medida\s+Provis[óo]ria|Emenda\s+Constitucional(?:\s+de\s+Revis[ãa]o)?)"
    r"\s*n?[º°o]?\.?\s*([\d\.]+(?:-\d+)?)(?:\s*,\s*de\s*(?:\d{1,2}[º°]?\.?\s+de\s+\w+\s+de\s+)?(\d{4}))?",
    re.IGNORECASE,
)


def _strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")


def normalize_whitespace(text: str) -> str:
    text = text.replace(" ", " ").replace("​", "")
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def extract_annotations(line: str) -> tuple[str, list[str]]:
    """Separa anotações editoriais do texto do dispositivo.

    Retorna `(texto_limpo, [anotações])`. `"(VETADO)"` isolado é mantido como
    anotação, e o texto limpo fica vazio — quem chama marca `vetoed=True`.
    """
    annotations = [normalize_whitespace(m.group(0)) for m in _ANNOTATION_RE.finditer(line)]
    clean = _ANNOTATION_RE.sub(" ", line)
    clean = _TRAILING_NOISE_RE.sub("", normalize_whitespace(clean))
    clean = re.sub(r"\s+([,.;:])", r"\1", clean)
    clean = normalize_whitespace(clean)
    return clean, annotations


def extract_amending_acts(annotations: list[str]) -> list[str]:
    """Normaliza os atos citados nas anotações para `"Lei 13.853/2019"` etc."""
    acts: list[str] = []
    for note in annotations:
        for m in _AMENDING_ACT_RE.finditer(note):
            kind = normalize_whitespace(m.group(1)).title()
            if kind == "Lcp":  # abreviação usada no compilado do CTN
                kind = "Lei Complementar"
            number = m.group(2).rstrip(".")
            act = f"{kind} {number}" + (f"/{m.group(3)}" if m.group(3) else "")
            if act not in acts:
                acts.append(act)
    return acts


def _heading_level(label: str) -> int:
    key = _strip_accents(label.split()[0]).upper()
    return _HEADING_LEVEL.get(key, 6)


def _norm_number(raw: str, suffix: str | None) -> str:
    number = raw.replace(".", "")
    return f"{number}-{suffix.upper()}" if suffix else number


class _Builder:
    """Máquina de estados que acumula linhas de continuação na unidade corrente."""

    def __init__(self) -> None:
        self.units: list[LegalUnit] = []
        self.headings: list[tuple[int, str]] = []
        self.article: str | None = None
        self.paragraph: str | None = None
        self.inciso: str | None = None
        self.alinea: str | None = None
        self.current: dict | None = None
        self.last_was_heading = False
        self.recognized_chars = 0
        self.namespace = ""

    # -- helpers -----------------------------------------------------------
    def _flush(self) -> None:
        if self.current is None:
            return
        raw = normalize_whitespace(" ".join(self.current.pop("lines")))
        clean, annotations = extract_annotations(raw)
        if not clean.strip(" .;:-–—"):
            clean = ""
        vetoed = any(re.search(r"VETAD[OA]", a, re.IGNORECASE) for a in annotations) and not clean
        revoked = bool(re.match(r"^\(?\s*revogad[oa]", clean, re.IGNORECASE)) or (
            not clean.strip(" .;") and any(re.match(r"\(\s*revogad", a, re.IGNORECASE) for a in annotations)
        )
        if revoked:
            clean = ""
        self.units.append(
            LegalUnit(
                **self.current,
                text=clean.strip(),
                annotations=annotations,
                amended_by=extract_amending_acts(annotations),
                revoked=revoked,
                vetoed=vetoed,
            )
        )
        self.current = None

    def _start(self, unit_type: LegalUnitType, unit_id: str, first_line: str) -> None:
        self._flush()
        self.current = {
            "unit_id": unit_id,
            "unit_type": unit_type,
            "article": self.article or "",
            "paragraph": self.paragraph,
            "inciso": self.inciso,
            "alinea": self.alinea,
            "item": None,
            "heading_path": [label for _, label in self.headings],
            "lines": [first_line] if first_line else [],
        }

    def _prefix(self, upto: str) -> str:
        parts = [f"{self.namespace}art-{self.article}"]
        if self.paragraph and upto in ("inciso", "alinea", "item"):
            parts.append(f"par-{self.paragraph}")
        if self.inciso and upto in ("alinea", "item"):
            parts.append(f"inc-{self.inciso}")
        if self.alinea and upto == "item":
            parts.append(f"ali-{self.alinea}")
        return ".".join(parts)

    # -- linha a linha ------------------------------------------------------
    def feed(self, line: str) -> None:
        line = normalize_whitespace(line)
        if not line:
            return

        if _NAMESPACE_RE.match(line) and (self.units or self.current is not None):
            self._flush()
            self.namespace = "adct."
            self.article = self.paragraph = self.inciso = self.alinea = None
            self.headings = [(0, line)]
            self.last_was_heading = True
            return

        heading = _HEADING_RE.match(line)
        if heading and len(line) < 160:
            self._flush()
            level = _heading_level(heading.group(1))
            self.headings = [(lv, lb) for lv, lb in self.headings if lv < level]
            self.headings.append((level, line))
            self.last_was_heading = True
            return
        # Nome do capítulo/título em linha própria logo após o marcador.
        if self.last_was_heading and self.headings and line.upper() == line and not _ARTICLE_RE.match(line):
            level, label = self.headings[-1]
            self.headings[-1] = (level, f"{label} — {line}")
            return
        self.last_was_heading = False

        m = _ARTICLE_RE.match(line)
        if m:
            self.article = _norm_number(m.group(1), m.group(2))
            self.paragraph = self.inciso = self.alinea = None
            self._start(LegalUnitType.ARTICLE, f"{self.namespace}art-{self.article}", m.group(3))
            self.recognized_chars += len(line)
            return
        if self.article is None:
            return  # ementa/preâmbulo: fora da estrutura articulada

        m = _PARAGRAPH_RE.match(line)
        sole = _SOLE_PARAGRAPH_RE.match(line) if not m else None
        if m or sole:
            self.paragraph = "unico" if sole else _norm_number(m.group(1), m.group(2))
            self.inciso = self.alinea = None
            first_line = sole.group(1) if sole else m.group(3)
            self._start(LegalUnitType.PARAGRAPH, f"{self.namespace}art-{self.article}.par-{self.paragraph}", first_line)
            self.recognized_chars += len(line)
            return

        m = _INCISO_RE.match(line)
        if m:
            self.inciso = _norm_number(m.group(1), m.group(2))
            self.alinea = None
            self._start(LegalUnitType.INCISO, f"{self._prefix('inciso')}.inc-{self.inciso}", m.group(3))
            self.recognized_chars += len(line)
            return

        m = _ALINEA_RE.match(line)
        if m and self.current is not None:
            self.alinea = m.group(1) + (f"-{m.group(2)}" if m.group(2) else "")
            self._start(LegalUnitType.ALINEA, f"{self._prefix('alinea')}.ali-{self.alinea}", m.group(3))
            self.recognized_chars += len(line)
            return

        m = _ITEM_RE.match(line)
        if m and self.alinea is not None:
            self._start(LegalUnitType.ITEM, f"{self._prefix('item')}.item-{m.group(1)}", m.group(2))
            self.current["item"] = m.group(1)
            self.recognized_chars += len(line)
            return

        # Continuação da unidade corrente (quebra de linha no meio do dispositivo).
        if self.current is not None:
            self.current["lines"].append(line)
            self.recognized_chars += len(line)


def parse_legal_text(text: str) -> list[LegalUnit]:
    """Parseia um texto normativo em unidades endereçáveis (ordem do texto)."""
    units, _ = parse_legal_text_with_coverage(text)
    return units


def parse_legal_text_with_coverage(text: str) -> tuple[list[LegalUnit], float]:
    """Como `parse_legal_text`, mas também devolve a cobertura estrutural:
    fração dos caracteres não-vazios do texto que caíram dentro de alguma
    unidade reconhecida (0.0–1.0)."""
    builder = _Builder()
    total = 0
    pending = ""
    for raw_line in text.splitlines():
        line = normalize_whitespace(raw_line)
        if not line:
            continue
        if _DANGLING_MARKER_RE.match(line):
            pending = f"{pending} {line}".strip()
            continue
        if pending:
            line, pending = f"{pending} {line}", ""
        total += len(line)
        builder.feed(line)
    builder._flush()

    # Textos compilados do Planalto repetem o mesmo dispositivo em várias
    # redações (a antiga, tachada ou não, seguida da vigente). A ÚLTIMA
    # ocorrência de cada `unit_id` é a redação vigente — as anteriores saem.
    last_index = {unit.unit_id: i for i, unit in enumerate(builder.units)}
    units = [unit for i, unit in enumerate(builder.units) if last_index[unit.unit_id] == i]

    coverage = (builder.recognized_chars / total) if total else 0.0
    return units, round(min(coverage, 1.0), 4)
