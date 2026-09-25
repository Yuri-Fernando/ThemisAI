"""Adaptador de fonte: HTML compilado do Planalto → texto normativo por linha.

O Planalto publica os textos compilados em HTML legado (FrontPage/Word,
windows-1252) com três armadilhas reais que este adaptador trata:

1. **Redação revogada continua no HTML**, marcada com `<strike>`, `<s>`,
   `<del>` ou `style="text-decoration: line-through"` — precisa sair, senão o
   parser lê a redação antiga como se fosse vigente;
2. **Quebra de linha do código-fonte não é quebra de dispositivo** — o HTML
   quebra "Art.\\n41." no meio do marcador; o que separa dispositivos são os
   elementos de bloco (`<p>`, `<br>`, `<div>`...);
3. **Encoding windows-1252** — `decode_planalto_bytes` tenta UTF-8 e cai para
   cp1252.

Sem dependência externa (regex puro), para rodar igual no CI do Themis.
"""
from __future__ import annotations

import html
import re

_DROP_BLOCKS_RE = re.compile(r"(?is)<(script|style|head|title)\b.*?</\1\s*>")
_STRUCK_RE = re.compile(r"(?is)<(strike|s|del)\b[^>]*>.*?</\1\s*>")
_LINE_THROUGH_RE = re.compile(
    r"(?is)<(span|font|p|a)\b[^>]*text-decoration\s*:\s*line-through[^>]*>.*?</\1\s*>"
)
_BLOCK_BREAK_RE = re.compile(r"(?i)<br\s*/?>|</?(?:p|div|h[1-6]|tr|li|table|blockquote|center)\b[^>]*>")
_TAG_RE = re.compile(r"(?s)<[^>]+>")


def decode_planalto_bytes(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def html_to_legal_text(markup: str) -> str:
    """Converte o HTML de uma norma em texto com um bloco por linha."""
    # NUL (U+0000) aparece em alguns HTMLs do Planalto (ex.: Lei 11.340) e o
    # Postgres recusa em colunas text — remove antes de tudo. Na mesma lei, U+001C
    # e U+001D são aspas curvas mal codificadas em volta do texto que ela insere em
    # outras leis ("acrescido do seguinte inciso: “Art. 313...”"): voltam a ser aspas,
    # senão o artigo citado vira um artigo da própria lei (e `\s` do Python trata
    # U+001C como espaço, divergindo do TypeScript).
    markup = markup.replace("\x00", "").replace("\x1c", "“").replace("\x1d", "”")
    text = _DROP_BLOCKS_RE.sub(" ", markup)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)
    # Remoção repetida: tags de tachado às vezes vêm aninhadas.
    for _ in range(3):
        text = _STRUCK_RE.sub(" ", text)
        text = _LINE_THROUGH_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)          # quebra do código-fonte = espaço
    text = _BLOCK_BREAK_RE.sub("\n", text)    # só bloco quebra linha
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text).replace(" ", " ")
    lines = (re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n"))
    # Leis antigas do Planalto (ex.: 7.357 Cheque, 5.474 Duplicatas) escrevem
    # "Art . 1º" — sem isto o parser não reconhece nenhum artigo.
    lines = (re.sub(r"^Art \.", "Art.", line) for line in lines)
    return "\n".join(line for line in lines if line)
