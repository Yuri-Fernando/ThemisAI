"""Model extraction — reconstrói o comportamento de um modelo-alvo treinando
um modelo substituto (surrogate) apenas com pares (entrada, predição) obtidos
por consulta.

Mede a `fidelity`: fração de entradas em que o surrogate concorda com o
alvo. Fidelity alta = o modelo pode ser "roubado" por consultas (risco de
propriedade intelectual e de facilitar ataques de transferência).
"""
from __future__ import annotations

import numpy as np

from core.adversarial_ml.models import LogisticRegressionModel, TargetModel
from shared.schemas import AdversarialAttackResult


def model_extraction_attack(
    target: TargetModel,
    X_query: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    n_classes: int,
    seed: int = 0,
) -> AdversarialAttackResult:
    X_query = np.asarray(X_query, dtype=float)
    X_test = np.asarray(X_test, dtype=float)
    y_test = np.asarray(y_test, dtype=int)

    # 1. consulta o alvo (o atacante só vê as predições)
    y_stolen = target.predict(X_query)

    # 2. treina o surrogate nesses rótulos "roubados"
    surrogate = LogisticRegressionModel(X_query.shape[1], n_classes, seed=seed)
    surrogate.fit(X_query, y_stolen)

    # 3. mede fidelity (concordância surrogate vs alvo) e acurácia do surrogate
    target_pred = target.predict(X_test)
    surrogate_pred = surrogate.predict(X_test)
    fidelity = float((surrogate_pred == target_pred).mean())
    surrogate_acc = float((surrogate_pred == y_test).mean())
    target_acc = float((target_pred == y_test).mean())

    return AdversarialAttackResult(
        attack="extraction",
        clean_accuracy=round(target_acc, 4),
        adversarial_accuracy=round(surrogate_acc, 4),
        accuracy_drop=round(target_acc - surrogate_acc, 4),
        success_rate=round(fidelity, 4),
        samples_evaluated=len(X_test),
        extra={"fidelity": round(fidelity, 4), "n_queries": len(X_query)},
    )
