"""Testes do AI Observability — medição real de tempo (time.perf_counter),
nenhum mock de relógio."""
from __future__ import annotations

import time

import pytest

from core.ai_observability.observability import ObservabilityRecorder, export_prometheus_text, traced
from core.pii_detection.detector import detect


def test_traced_records_ok_call_with_real_module():
    recorder = ObservabilityRecorder()
    with traced(recorder, module="pii_detection", function="detect"):
        detect("CPF 111.444.777-35")

    snapshot = recorder.snapshot()
    assert snapshot.total_calls == 1
    assert snapshot.error_count == 0
    assert snapshot.metrics[0].module == "pii_detection"
    assert snapshot.metrics[0].function == "detect"
    assert snapshot.metrics[0].status == "ok"
    assert snapshot.metrics[0].duration_ms >= 0.0


def test_traced_records_error_and_reraises():
    recorder = ObservabilityRecorder()

    with pytest.raises(ValueError, match="boom"):
        with traced(recorder, module="fake_module", function="fake_fn"):
            raise ValueError("boom")

    snapshot = recorder.snapshot()
    assert snapshot.total_calls == 1
    assert snapshot.error_count == 1
    assert snapshot.metrics[0].status == "error"
    assert snapshot.metrics[0].error_message == "boom"


def test_snapshot_avg_duration_and_by_module():
    recorder = ObservabilityRecorder()
    with traced(recorder, module="a", function="f1"):
        time.sleep(0.001)
    with traced(recorder, module="a", function="f2"):
        time.sleep(0.001)
    with traced(recorder, module="b", function="f1"):
        time.sleep(0.001)

    snapshot = recorder.snapshot()
    assert snapshot.total_calls == 3
    assert snapshot.by_module == {"a": 2, "b": 1}
    assert snapshot.avg_duration_ms > 0.0


def test_empty_recorder_snapshot():
    recorder = ObservabilityRecorder()
    snapshot = recorder.snapshot()
    assert snapshot.total_calls == 0
    assert snapshot.error_count == 0
    assert snapshot.avg_duration_ms == 0.0
    assert snapshot.by_module == {}


def test_reset_clears_metrics():
    recorder = ObservabilityRecorder()
    with traced(recorder, module="a", function="f1"):
        pass
    recorder.reset()
    assert recorder.snapshot().total_calls == 0


def test_export_prometheus_text_format():
    recorder = ObservabilityRecorder()
    with traced(recorder, module="pii_detection", function="detect"):
        pass
    with pytest.raises(ValueError):
        with traced(recorder, module="pii_detection", function="detect"):
            raise ValueError("x")

    text = export_prometheus_text(recorder.snapshot())
    assert "# HELP themis_module_calls_total" in text
    assert "# TYPE themis_module_calls_total counter" in text
    assert 'themis_module_calls_total{module="pii_detection"} 2' in text
    assert "themis_module_call_errors_total 1" in text
    assert "themis_module_call_duration_ms_avg" in text


def test_export_prometheus_text_empty_snapshot_is_valid_text():
    recorder = ObservabilityRecorder()
    text = export_prometheus_text(recorder.snapshot())
    assert isinstance(text, str)
    assert "themis_module_call_errors_total 0" in text
