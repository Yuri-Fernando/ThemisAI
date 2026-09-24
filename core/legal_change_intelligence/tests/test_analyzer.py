"""`analyze_legal_change` — propriedades que não cabem nos casos JSON:
determinismo, hash, integração real com a fila de revisão humana, diff e
textual score isolados."""
from __future__ import annotations

from datetime import datetime, timezone

from core.human_oversight.queue import OversightQueue
from core.legal_change_intelligence import analyze_legal_change, content_hash, structural_diff, textual_change_score
from core.legal_change_intelligence.signals import classify_topics
from core.legal_change_intelligence.structure import parse_legal_text
from shared.schemas import LegalChangeType, OversightItemStatus, RiskLevel

PREV = "Art. 10. O fornecedor deverá comunicar em 30 (trinta) dias, sob pena de multa de 2%."
CURR = "Art. 10. O fornecedor deverá comunicar em 15 (quinze) dias, sob pena de multa de 10%."
FIXED = datetime(2026, 9, 23, tzinfo=timezone.utc)


def test_deterministic_same_input_same_output():
    a = analyze_legal_change(PREV, CURR, analyzed_at=FIXED)
    b = analyze_legal_change(PREV, CURR, analyzed_at=FIXED)
    assert a.model_dump() == b.model_dump()


def test_hashes_and_metadata_passthrough():
    result = analyze_legal_change(PREV, CURR, metadata={"norm_id": "x", "title": "Lei X"}, analyzed_at=FIXED)
    assert result.previous_hash == content_hash(PREV)
    assert result.current_hash == content_hash(CURR)
    assert result.document["title"] == "Lei X"
    assert result.engine_version == "0.1.0"
    assert result.summary.startswith("Lei X:")


def test_requires_review_enqueues_in_real_oversight_queue(tmp_path):
    queue = OversightQueue(storage_path=tmp_path / "queue.json")
    result = analyze_legal_change(PREV, CURR, metadata={"title": "Lei X"}, oversight_queue=queue, analyzed_at=FIXED)
    assert result.requires_human_review
    item = queue.get(result.oversight_item_id)
    assert item.status == OversightItemStatus.PENDING
    assert item.risk_level == RiskLevel.HIGH
    assert "R2_MATERIAL_SIGNAL" in item.reason


def test_no_enqueue_when_review_not_required(tmp_path):
    queue = OversightQueue(storage_path=tmp_path / "queue.json")
    result = analyze_legal_change(PREV, PREV, oversight_queue=queue, analyzed_at=FIXED)
    assert result.oversight_item_id is None
    assert queue.list_items() == []


def test_confidence_is_structural_coverage():
    noisy = "Texto solto sem estrutura nenhuma aqui e bem longo para pesar.\n" + PREV
    result = analyze_legal_change(noisy, CURR, analyzed_at=FIXED)
    assert result.confidence == result.parse_coverage_before < 1.0
    assert analyze_legal_change("", CURR, analyzed_at=FIXED).confidence == 0.0


def test_client_context_accepts_dicts():
    clients = [{"client_id": "c1", "name": "C1", "watched_norms": ["lei-x"],
                "documents": [{"doc_id": "d1", "title": "Parecer", "text": "ver art. 10"}]}]
    result = analyze_legal_change(PREV, CURR, metadata={"norm_id": "lei-x"}, client_context=clients, analyzed_at=FIXED)
    assert result.related_clients[0].strength == "strong"
    assert result.related_clients[0].matched_units == ["art-10"]
    assert result.risk_level == RiskLevel.CRITICAL


def test_removed_unit_keeps_position_and_is_flagged():
    before = parse_legal_text("Art. 1º A.\n§ 1º B.\n§ 2º C.\nArt. 2º D.")
    after = parse_legal_text("Art. 1º A.\n§ 2º C.\nArt. 2º D.")
    changes = structural_diff(before, after)
    assert [(c.unit_id, c.change_type) for c in changes] == [("art-1.par-1", LegalChangeType.REMOVED)]
    result = analyze_legal_change("Art. 1º A.\n§ 1º B.", "Art. 1º A.", analyzed_at=FIXED)
    assert "R1_REVOCATION" in {r.rule_id for r in result.rules_fired}


def test_textual_change_score_bounds():
    assert textual_change_score("a b c", "a b c") == 0.0
    assert textual_change_score(None, "x") == 1.0
    assert textual_change_score(None, None) == 0.0
    assert 0.0 < textual_change_score("prazo de 30 dias", "prazo de 15 dias") < 0.35


def test_topics_use_word_boundaries():
    # "apenas" não pode disparar o tema penal via "pena".
    assert "penal" not in classify_topics(["aplica-se apenas ao caso"])
    assert "penal" in classify_topics(["pena de reclusão"])
