"""Testes do motor de PII Detection (core/pii_detection/detector.py).

Cobre o caminho crítico regex (determinístico, 100% offline) exigido para
todos os tipos de dado do escopo V1, mais a classificação LGPD Art. 5º
(PERSONAL vs SENSITIVE) e o contrato de saída (PIIDetectionResult).
"""
from __future__ import annotations

from core.pii_detection.detector import detect
from shared.schemas import DataCategory, PIIDetectionResult, PIIFinding


def _entity_types(result: PIIDetectionResult) -> list[str]:
    return [f.entity_type for f in result.findings]


# ---------------------------------------------------------------------------
# Contrato / tipos
# ---------------------------------------------------------------------------


def test_detect_returns_pii_detection_result_instance():
    result = detect("Texto qualquer sem dado pessoal.")
    assert isinstance(result, PIIDetectionResult)
    assert all(isinstance(f, PIIFinding) for f in result.findings)


def test_confidence_scores_within_bounds():
    text = (
        "Contato: joao.silva@example.com, CPF 111.444.777-35, "
        "telefone (11) 91234-5678."
    )
    result = detect(text)
    assert result.findings, "esperava ao menos um achado"
    assert all(0.0 <= f.confidence <= 1.0 for f in result.findings)


# ---------------------------------------------------------------------------
# CPF
# ---------------------------------------------------------------------------


def test_cpf_formatted_and_valid_detected():
    result = detect("O CPF do cliente é 111.444.777-35.")
    cpf_findings = [f for f in result.findings if f.entity_type == "CPF"]
    assert len(cpf_findings) == 1
    assert cpf_findings[0].text_span == "111.444.777-35"
    assert cpf_findings[0].category == DataCategory.PERSONAL
    assert cpf_findings[0].confidence >= 0.9


def test_cpf_plain_digits_valid_checksum_detected_as_cpf_not_phone():
    # 11144477735 é um CPF de teste válido (dígito verificador correto).
    result = detect("Documento informado: 11144477735 para validação.")
    cpf_findings = [f for f in result.findings if f.entity_type == "CPF"]
    assert len(cpf_findings) == 1
    assert cpf_findings[0].text_span == "11144477735"


def test_cpf_formatted_invalid_checksum_still_flagged_lower_confidence():
    result = detect("CPF: 123.456.789-00")
    cpf_findings = [f for f in result.findings if f.entity_type == "CPF"]
    assert len(cpf_findings) == 1
    assert cpf_findings[0].confidence < 0.9


# ---------------------------------------------------------------------------
# CNPJ
# ---------------------------------------------------------------------------


def test_cnpj_formatted_and_valid_detected():
    result = detect("Empresa inscrita sob CNPJ 11.222.333/0001-81.")
    cnpj_findings = [f for f in result.findings if f.entity_type == "CNPJ"]
    assert len(cnpj_findings) == 1
    assert cnpj_findings[0].text_span == "11.222.333/0001-81"
    assert cnpj_findings[0].category == DataCategory.PERSONAL


# ---------------------------------------------------------------------------
# E-mail
# ---------------------------------------------------------------------------


def test_email_detected():
    result = detect("Envie para maria.santos@empresa.com.br o contrato.")
    email_findings = [f for f in result.findings if f.entity_type == "EMAIL"]
    assert len(email_findings) == 1
    assert email_findings[0].text_span == "maria.santos@empresa.com.br"
    assert email_findings[0].category == DataCategory.PERSONAL


# ---------------------------------------------------------------------------
# Telefone
# ---------------------------------------------------------------------------


def test_phone_with_ddd_and_country_code_detected():
    result = detect("Ligue para +55 11 91234-5678 assim que possível.")
    phone_findings = [f for f in result.findings if f.entity_type == "TELEFONE"]
    assert len(phone_findings) == 1


def test_phone_with_parenthesized_ddd_detected():
    result = detect("Meu telefone é (21) 3456-7890.")
    phone_findings = [f for f in result.findings if f.entity_type == "TELEFONE"]
    assert len(phone_findings) == 1


def test_phone_without_ddd_with_hyphen_detected():
    result = detect("Ramal direto: 91234-5678 para suporte.")
    phone_findings = [f for f in result.findings if f.entity_type == "TELEFONE"]
    assert len(phone_findings) >= 1


# ---------------------------------------------------------------------------
# CEP
# ---------------------------------------------------------------------------


def test_cep_formatted_detected():
    result = detect("Endereço: Rua das Flores, CEP 01310-100, São Paulo.")
    cep_findings = [f for f in result.findings if f.entity_type == "CEP"]
    assert len(cep_findings) == 1
    assert cep_findings[0].text_span == "01310-100"


# ---------------------------------------------------------------------------
# RG
# ---------------------------------------------------------------------------


def test_rg_detected_with_keyword_context():
    result = detect("Apresentou RG 12.345.678-9 no balcão de atendimento.")
    rg_findings = [f for f in result.findings if f.entity_type == "RG"]
    assert len(rg_findings) == 1
    assert rg_findings[0].category == DataCategory.PERSONAL


def test_number_without_rg_keyword_not_flagged_as_rg():
    # Mesmo formato de dígitos, mas sem a palavra "RG" por perto.
    result = detect("Código de rastreio: 12.345.678-9 para a encomenda.")
    rg_findings = [f for f in result.findings if f.entity_type == "RG"]
    assert len(rg_findings) == 0


# ---------------------------------------------------------------------------
# Data de nascimento
# ---------------------------------------------------------------------------


def test_birthdate_detected_with_context_keyword():
    result = detect("Data de nascimento: 15/03/1990, conforme cadastro.")
    dob_findings = [f for f in result.findings if f.entity_type == "DATA_NASCIMENTO"]
    assert len(dob_findings) == 1
    assert dob_findings[0].text_span == "15/03/1990"


def test_generic_date_without_context_not_flagged_as_birthdate():
    result = detect("A reunião foi marcada para 15/03/1990 na sede da empresa.")
    dob_findings = [f for f in result.findings if f.entity_type == "DATA_NASCIMENTO"]
    assert len(dob_findings) == 0


# ---------------------------------------------------------------------------
# Nome próprio (heurística)
# ---------------------------------------------------------------------------


def test_proper_name_heuristic_detects_full_name_mid_sentence():
    result = detect("O contrato foi assinado por Carlos Eduardo Ferreira ontem.")
    name_findings = [f for f in result.findings if f.entity_type == "NOME"]
    assert any("Carlos Eduardo Ferreira" in f.text_span for f in name_findings)


def test_proper_name_heuristic_ignores_sentence_start():
    # "Segundo o relatório" no início de frase não deve virar "nome".
    result = detect("Segundo Relatório Anual, os números melhoraram muito.")
    name_findings = [f for f in result.findings if f.entity_type == "NOME"]
    assert not any(f.start == 0 for f in name_findings)


# ---------------------------------------------------------------------------
# Dado sensível (LGPD Art. 5º, II)
# ---------------------------------------------------------------------------


def test_health_mention_classified_as_sensitive():
    result = detect("O paciente relatou diagnóstico de câncer no último exame médico.")
    assert result.has_sensitive_data is True
    assert any(f.category == DataCategory.SENSITIVE for f in result.findings)


def test_religion_mention_classified_as_sensitive():
    result = detect("Ele se declarou evangélico durante a entrevista de admissão.")
    assert result.has_sensitive_data is True
    religion_findings = [
        f for f in result.findings if f.entity_type == "SENSITIVE_RELIGION"
    ]
    assert len(religion_findings) >= 1


def test_biometric_mention_classified_as_sensitive():
    result = detect("O sistema usa reconhecimento facial para autenticação.")
    assert result.has_sensitive_data is True


def test_political_union_mention_classified_as_sensitive():
    result = detect("O funcionário informou sua filiação sindical no formulário.")
    assert result.has_sensitive_data is True


def test_sensitive_mention_detected_without_accents():
    # Texto em português sem acentuação é comum na prática (WhatsApp,
    # formulários, logs mal codificados) — o motor não deve depender de
    # acento para não perder um achado sensível.
    result = detect(
        "O paciente relatou diagnostico de depressao e mencionou sua "
        "filiacao sindical."
    )
    assert result.has_sensitive_data is True
    types = {f.entity_type for f in result.findings}
    assert "SENSITIVE_HEALTH" in types
    assert "SENSITIVE_POLITICAL_UNION" in types


# ---------------------------------------------------------------------------
# Texto sem PII / negativo
# ---------------------------------------------------------------------------


def test_clean_text_returns_no_findings():
    result = detect(
        "O relatório trimestral apresentou crescimento de receita "
        "acima da média do setor."
    )
    assert result.findings == []
    assert result.has_sensitive_data is False
    assert result.summary.startswith("0 achado")


def test_empty_text_returns_empty_result():
    result = detect("")
    assert result.findings == []
    assert result.has_sensitive_data is False


# ---------------------------------------------------------------------------
# Combinado / múltiplos achados
# ---------------------------------------------------------------------------


def test_multiple_entity_types_in_single_text():
    text = (
        "Cliente João da Silva, CPF 111.444.777-35, e-mail joao@exemplo.com, "
        "telefone (11) 98888-7777, relatou diagnóstico de depressão."
    )
    result = detect(text)
    types = set(_entity_types(result))
    assert "CPF" in types
    assert "EMAIL" in types
    assert "TELEFONE" in types
    assert result.has_sensitive_data is True
