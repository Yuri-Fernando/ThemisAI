"""PII Detection — módulo V1 do Themis AI.

Detecta dados pessoais e sensíveis (LGPD Art. 5º) em texto livre em
português. Ver `detector.detect` para a API pública.
"""
from core.pii_detection.detector import detect

__all__ = ["detect"]

__version__ = "0.1.0"
