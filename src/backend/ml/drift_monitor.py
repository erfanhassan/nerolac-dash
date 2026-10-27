"""Nerolac Operations Dashboard - Machine Learning Model Drift Monitor.

Monitors ensemble demand forecasting error metrics (LightGBM + Prophet) over time:
1. Calculates Mean Absolute Percentage Error (MAPE) and Root Mean Squared Error (RMSE).
2. Detects statistical performance degradation and distribution drift against baselines.
3. Classifies drift severity (NORMAL, WARNING, CRITICAL) and generates automated retrain triggers.
4. Synchronizes error gauges with OpenTelemetry/Prometheus metrics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import numpy as np

from src.backend.observability.telemetry import get_telemetry_manager

logger = logging.getLogger("nerolac.ml.drift_monitor")

# Operational Error Thresholds for Paint Industry Demand Forecasting
DEFAULT_BASELINE_MAPE = 12.0  # 12% baseline accuracy target
DEFAULT_WARNING_MAPE = 15.0  # 15% warning threshold
DEFAULT_CRITICAL_MAPE = 25.0  # 25% critical threshold requiring immediate model re-train
EPSILON = 1e-6


class DriftSeverity(str, Enum):
    """Severity classification for machine learning forecasting model drift."""

    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class ForecastRecord:
    """Historical tuple linking actual realized sales with ML ensemble forecasts."""

    depot_id: str
    sku_id: str
    actual: float
    predicted: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DriftEvaluationResult:
    """Detailed audit report of forecasting drift evaluation."""

    is_drift_detected: bool
    severity: DriftSeverity
    current_mape: float
    baseline_mape: float
    mape_delta_percentage: float
    current_rmse: float
    baseline_rmse: float
    rmse_delta_percentage: float
    sample_count: int
    evaluated_at: datetime
    depot_id: str | None
    sku_id: str | None
    alerts: list[str]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert evaluation result to JSON-serializable dictionary."""
        return {
            "is_drift_detected": self.is_drift_detected,
            "severity": self.severity.value,
            "current_mape": round(self.current_mape, 2),
            "baseline_mape": round(self.baseline_mape, 2),
            "mape_delta_percentage": round(self.mape_delta_percentage, 2),
            "current_rmse": round(self.current_rmse, 3),
            "baseline_rmse": round(self.baseline_rmse, 3),
            "rmse_delta_percentage": round(self.rmse_delta_percentage, 2),
            "sample_count": self.sample_count,
            "evaluated_at": self.evaluated_at.isoformat(),
            "depot_id": self.depot_id,
            "sku_id": self.sku_id,
            "alerts": self.alerts,
            "recommendations": self.recommendations,
        }


class MLModelDriftMonitor:
    """Monitors LightGBM and Prophet forecasting accuracy and flags concept drift."""

    _instance: MLModelDriftMonitor | None = None

    def __init__(
        self,
        baseline_mape: float = DEFAULT_BASELINE_MAPE,
        warning_mape: float = DEFAULT_WARNING_MAPE,
        critical_mape: float = DEFAULT_CRITICAL_MAPE,
    ) -> None:
        self.baseline_mape = baseline_mape
        self.warning_mape = warning_mape
        self.critical_mape = critical_mape
        self._records: list[ForecastRecord] = []
        self._audit_history: list[DriftEvaluationResult] = []

    @classmethod
    def get_instance(cls) -> MLModelDriftMonitor:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_forecast_actual(
        self,
        depot_id: str,
        sku_id: str,
        actual: float,
        predicted: float,
        timestamp: datetime | None = None,
    ) -> None:
        """Log a pair of actual SAP invoicing vs prior ML prediction."""
        record = ForecastRecord(
            depot_id=depot_id,
            sku_id=sku_id,
            actual=float(actual),
            predicted=float(predicted),
            timestamp=timestamp or datetime.now(timezone.utc),
        )
        self._records.append(record)

    def calculate_mape(self, actuals: np.ndarray, predictions: np.ndarray) -> float:
        """Calculate Mean Absolute Percentage Error (MAPE).

        Safely handles zero actuals using epsilon masking.
        """
        if len(actuals) == 0:
            return 0.0
        # Prevent division by zero
        safe_actuals = np.where(actuals == 0, EPSILON, actuals)
        abs_percentage_errors = np.abs((actuals - predictions) / safe_actuals)
        return float(np.mean(abs_percentage_errors) * 100.0)

    def calculate_rmse(self, actuals: np.ndarray, predictions: np.ndarray) -> float:
        """Calculate Root Mean Squared Error (RMSE) in metric tons."""
        if len(actuals) == 0:
            return 0.0
        mse = np.mean((actuals - predictions) ** 2)
        return float(np.sqrt(mse))

    def evaluate_drift(
        self,
        depot_id: str | None = None,
        sku_id: str | None = None,
        baseline_rmse: float = 1.5,
    ) -> DriftEvaluationResult:
        """Evaluate recent forecast performance against established baselines."""
        # Filter relevant records
        matching_records = [
            r
            for r in self._records
            if (depot_id is None or r.depot_id == depot_id)
            and (sku_id is None or r.sku_id == sku_id)
        ]

        now = datetime.now(timezone.utc)

        if not matching_records:
            # Return baseline clean evaluation when no records exist yet
            return DriftEvaluationResult(
                is_drift_detected=False,
                severity=DriftSeverity.NORMAL,
                current_mape=self.baseline_mape,
                baseline_mape=self.baseline_mape,
                mape_delta_percentage=0.0,
                current_rmse=baseline_rmse,
                baseline_rmse=baseline_rmse,
                rmse_delta_percentage=0.0,
                sample_count=0,
                evaluated_at=now,
                depot_id=depot_id,
                sku_id=sku_id,
                alerts=[],
                recommendations=["Awaiting live SAP invoicing actuals for drift evaluation."],
            )

        actuals = np.array([r.actual for r in matching_records])
        predictions = np.array([r.predicted for r in matching_records])

        current_mape = self.calculate_mape(actuals, predictions)
        current_rmse = self.calculate_rmse(actuals, predictions)

        # Delta computations
        mape_delta = current_mape - self.baseline_mape
        mape_delta_pct = (
            (mape_delta / self.baseline_mape) * 100.0 if self.baseline_mape > 0 else 0.0
        )

        rmse_delta = current_rmse - baseline_rmse
        rmse_delta_pct = (rmse_delta / baseline_rmse) * 100.0 if baseline_rmse > 0 else 0.0

        # Classify severity
        alerts: list[str] = []
        recommendations: list[str] = []

        if current_mape >= self.critical_mape:
            severity = DriftSeverity.CRITICAL
            is_drift = True
            alerts.append(
                f"CRITICAL DRIFT: MAPE {current_mape:.2f}% exceeds threshold {self.critical_mape}%"
            )
            recommendations.append(
                "Trigger automated Prophet and LightGBM retraining on latest 60-day SAP actuals."
            )
            recommendations.append(
                "Check regional stockout flags in MB52 to prevent artificial zero-demand bias."
            )
        elif current_mape >= self.warning_mape or mape_delta_pct > 25.0:
            severity = DriftSeverity.WARNING
            is_drift = True
            alerts.append(
                f"WARNING: Forecast MAPE {current_mape:.2f}% elevated above {self.baseline_mape}% "
                f"(+{mape_delta_pct:.1f}%)"
            )
            recommendations.append(
                "Review festival seasonal promotions (Eid/Puja) multipliers in demand forecaster."
            )
        else:
            severity = DriftSeverity.NORMAL
            is_drift = False
            recommendations.append("Forecast performance operating within acceptable bounds.")

        # Update OpenTelemetry / Prometheus metrics
        target_depot = depot_id or "ALL"
        target_sku = sku_id or "ALL"
        telemetry = get_telemetry_manager()
        telemetry.update_ml_metrics(
            depot_id=target_depot,
            sku_id=target_sku,
            mape=current_mape,
            rmse=current_rmse,
        )

        result = DriftEvaluationResult(
            is_drift_detected=is_drift,
            severity=severity,
            current_mape=current_mape,
            baseline_mape=self.baseline_mape,
            mape_delta_percentage=mape_delta_pct,
            current_rmse=current_rmse,
            baseline_rmse=baseline_rmse,
            rmse_delta_percentage=rmse_delta_pct,
            sample_count=len(matching_records),
            evaluated_at=now,
            depot_id=depot_id,
            sku_id=sku_id,
            alerts=alerts,
            recommendations=recommendations,
        )

        self._audit_history.append(result)
        return result

    def get_drift_history(self, limit: int = 50) -> list[DriftEvaluationResult]:
        """Return historical drift evaluations."""
        return self._audit_history[-limit:]


def get_drift_monitor() -> MLModelDriftMonitor:
    """Retrieve singleton MLModelDriftMonitor instance."""
    return MLModelDriftMonitor.get_instance()
