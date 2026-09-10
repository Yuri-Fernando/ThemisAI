"""Teste da fachada de LLM security — roda contra o motor real de
`prompt_security` via o harness real de `red_team_lab`."""
from __future__ import annotations

from core.adversarial_ml.llm_security import assess_llm_security


def test_assess_llm_security_shape_and_real_engine():
    result = assess_llm_security()
    assert "overall_detection_rate" in result
    assert 0.0 <= result["overall_detection_rate"] <= 1.0
    assert "jailbreak" in result
    assert "coverage_gaps" in result
    assert isinstance(result["coverage_gaps"], list)
    # o motor real detecta jailbreaks clássicos
    if result["jailbreak"]:
        assert result["jailbreak"]["detection_rate"] > 0.0
