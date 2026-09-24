"""Parser estrutural + adaptador HTML do Planalto — casos pontuais."""
from __future__ import annotations

from core.legal_change_intelligence import (
    decode_planalto_bytes,
    html_to_legal_text,
    parse_legal_text,
    parse_legal_text_with_coverage,
)
from core.legal_change_intelligence.structure import extract_amending_acts, extract_annotations
from shared.schemas import LegalUnitType


def _ids(text: str) -> list[str]:
    return [u.unit_id for u in parse_legal_text(text)]


def test_full_hierarchy_ids():
    text = (
        "Art. 5º Todos são iguais perante a lei:\n"
        "I - homens e mulheres são iguais;\n"
        "§ 1º As normas têm aplicação imediata.\n"
        "I - primeiro inciso do parágrafo;\n"
        "a) alínea a;\n"
        "1. item um;\n"
        "Parágrafo único. Texto final."
    )
    assert _ids(text) == [
        "art-5", "art-5.inc-I", "art-5.par-1", "art-5.par-1.inc-I",
        "art-5.par-1.inc-I.ali-a", "art-5.par-1.inc-I.ali-a.item-1", "art-5.par-unico",
    ]
    types = [u.unit_type for u in parse_legal_text(text)]
    assert types[0] == LegalUnitType.ARTICLE and types[-1] == LegalUnitType.PARAGRAPH


def test_article_number_formats():
    assert _ids("Art. 1.048. Tramitam com prioridade.") == ["art-1048"]
    assert _ids("Art. 20-A. Novo artigo.") == ["art-20-A"]
    assert _ids("Art. 1º - A presente Lei institui.") == ["art-1"]
    assert _ids("Art. 5o Todos.") == ["art-5"]


def test_continuation_lines_are_joined():
    units = parse_legal_text("Art. 1º Esta Lei dispõe\nsobre tratamento\nde dados.")
    assert len(units) == 1
    assert units[0].text == "Esta Lei dispõe sobre tratamento de dados."


def test_dangling_marker_from_html_line_break():
    # Caso real da CF (Art. 41): o HTML quebra "Art." e "41." em linhas distintas.
    assert _ids("Art. 40. O regime.\nArt.\n41. São estáveis.") == ["art-40", "art-41"]


def test_preamble_is_not_a_unit_and_lowers_coverage():
    text = "LEI Nº 99.999, DE 1º DE JANEIRO DE 2026\nDispõe sobre algo.\nArt. 1º Texto."
    units, coverage = parse_legal_text_with_coverage(text)
    assert [u.unit_id for u in units] == ["art-1"]
    assert 0.0 < coverage < 0.5


def test_adct_namespace_only_after_articulated_body():
    text = (
        "ATO DAS DISPOSIÇÕES CONSTITUCIONAIS TRANSITÓRIAS\n"  # índice no topo: ignorado
        "Art. 41. Corpo permanente.\n"
        "ATO DAS DISPOSIÇÕES CONSTITUCIONAIS TRANSITÓRIAS\n"
        "Art. 41. Disposição transitória."
    )
    units = {u.unit_id: u.text for u in parse_legal_text(text)}
    assert units == {"art-41": "Corpo permanente.", "adct.art-41": "Disposição transitória."}


def test_last_occurrence_wins_for_repeated_units():
    # Compilado do Planalto: redação antiga seguida da vigente.
    text = "Art. 47. Multa de R$ 402,53. (Vigência encerrada)\nArt. 47. Multa de R$ 3.000,00. (Redação dada pela Lei nº 13.467, de 2017)"
    units = parse_legal_text(text)
    assert len(units) == 1 and units[0].text == "Multa de R$ 3.000,00."


def test_annotations_and_amending_acts():
    clean, notes = extract_annotations("Texto do dispositivo. (Redação dada pela Emenda Constitucional nº 115, de 2022) Vigência")
    assert clean == "Texto do dispositivo."
    assert extract_amending_acts(notes) == ["Emenda Constitucional 115/2022"]
    assert extract_amending_acts(["(Incluído pela Medida Provisória nº 869, de 2018)"]) == ["Medida Provisória 869/2018"]
    assert extract_amending_acts(["(Redação dada pela Lei Complementar nº 104, de 10.1.2001)"]) == ["Lei Complementar 104"]


def test_revoked_unit():
    units = parse_legal_text("Art. 1º Texto.\n§ 1º (Revogado).\n§ 2º Revogado.")
    by_id = {u.unit_id: u for u in units}
    assert by_id["art-1.par-1"].revoked and by_id["art-1.par-1"].text == ""
    assert by_id["art-1.par-2"].revoked


def test_html_adapter_drops_struck_text_and_respects_blocks():
    markup = (
        "<html><head><title>x</title></head><body>"
        "<p><strike>Art. 1º Redação antiga revogada.</strike></p>"
        "<p><span style=\"text-decoration: line-through\">Art. 1º Outra antiga.</span></p>"
        "<p><font>Art.\n1º Redação vigente&nbsp;com   espaços.</font></p>"
        "<p>§ 1º Parágrafo<br>Art. 2º Segundo.</p>"
        "</body></html>"
    )
    text = html_to_legal_text(markup)
    assert "antiga" not in text
    assert text.splitlines() == ["Art. 1º Redação vigente com espaços.", "§ 1º Parágrafo", "Art. 2º Segundo."]


def test_decode_planalto_bytes_falls_back_to_cp1252():
    raw = "Art. 1º Proteção".encode("cp1252")
    assert decode_planalto_bytes(raw) == "Art. 1º Proteção"
    assert decode_planalto_bytes("ção".encode("utf-8")) == "ção"
