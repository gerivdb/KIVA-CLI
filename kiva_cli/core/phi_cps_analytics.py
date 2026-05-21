#!/usr/bin/env python3
"""
φ-CPS Analytics Manager - KIVA CLI

Provides analytics, visualization, and drift detection for φ-CPS metrics.
Tracks IntentHash continuity, drift thresholds, and generates reports.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class PhiCPSMetric:
    """Represents a φ-CPS metric data point."""
    def __init__(self, data: Dict[str, Any]):
        self.timestamp = data.get("timestamp", datetime.now().isoformat())
        self.phi_value = data.get("phi_value", 0.0)
        self.drift = data.get("drift", 0.0)
        self.intent_hash = data.get("intent_hash", "")
        self.component = data.get("component", "")
        self.level = data.get("level", "")
        self.status = data.get("status", "OK")


class PhiCPSAnalytics:
    """Manages φ-CPS analytics and drift detection."""

    WARNING_THRESHOLD = 0.02
    CRITICAL_THRESHOLD = 0.05
    EMERGENCY_THRESHOLD = 0.10

    def __init__(self, metrics_path: Optional[str] = None):
        if metrics_path is None:
            metrics_path = "C:\\DevTools\\data\\phi-cps\\metrics.json"
        self.metrics_path = Path(metrics_path)
        self.metrics: List[PhiCPSMetric] = []
        self._load_metrics()

    def _load_metrics(self):
        if self.metrics_path.exists():
            try:
                with open(self.metrics_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Handle both formats: {"metrics": [...]} and direct [...]
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("metrics", [])
                else:
                    items = []
                for m in items:
                    if isinstance(m, dict) and "phi_value" in m:
                        self.metrics.append(PhiCPSMetric(m))
            except (json.JSONDecodeError, IOError, TypeError):
                pass

    def _save_metrics(self):
        data = {
            "metrics": [
                {
                    "timestamp": m.timestamp,
                    "phi_value": m.phi_value,
                    "drift": m.drift,
                    "intent_hash": m.intent_hash,
                    "component": m.component,
                    "level": m.level,
                    "status": m.status
                }
                for m in self.metrics
            ]
        }
        os.makedirs(os.path.dirname(self.metrics_path), exist_ok=True)
        with open(self.metrics_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_metric(self, phi_value: float, drift: float, intent_hash: str, component: str, level: str):
        status = self._calculate_status(drift)
        metric = PhiCPSMetric({
            "phi_value": phi_value,
            "drift": drift,
            "intent_hash": intent_hash,
            "component": component,
            "level": level,
            "status": status
        })
        self.metrics.append(metric)
        self._save_metrics()

    def _calculate_status(self, drift: float) -> str:
        if drift >= self.EMERGENCY_THRESHOLD:
            return "EMERGENCY"
        elif drift >= self.CRITICAL_THRESHOLD:
            return "CRITICAL"
        elif drift >= self.WARNING_THRESHOLD:
            return "WARNING"
        return "OK"

    def get_current_status(self, component: Optional[str] = None) -> Dict[str, Any]:
        filtered = self.metrics
        if component:
            filtered = [m for m in filtered if m.component == component]
        
        if not filtered:
            return {"status": "N/A", "message": "No metrics available"}
        
        latest = filtered[-1]
        return {
            "status": latest.status,
            "phi_value": latest.phi_value,
            "drift": latest.drift,
            "intent_hash": latest.intent_hash,
            "component": latest.component,
            "level": latest.level,
            "timestamp": latest.timestamp
        }

    def get_alerts(self, component: Optional[str] = None) -> List[PhiCPSMetric]:
        filtered = [
            m for m in self.metrics
            if m.status in ("WARNING", "CRITICAL", "EMERGENCY")
        ]
        if component:
            filtered = [m for m in filtered if m.component == component]
        return filtered

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.metrics)
        if total == 0:
            return {"total_metrics": 0, "status": "N/A", "alerts": 0, "avg_drift": 0.0}
        
        alerts = len(self.get_alerts())
        avg_drift = sum(m.drift for m in self.metrics) / total
        latest_status = self.get_current_status()["status"]
        
        return {
            "total_metrics": total,
            "status": latest_status,
            "alerts": alerts,
            "avg_drift": round(avg_drift, 4),
            "warning_threshold": self.WARNING_THRESHOLD,
            "critical_threshold": self.CRITICAL_THRESHOLD,
            "emergency_threshold": self.EMERGENCY_THRESHOLD
        }

    def generate_report(self, output_path: Optional[str] = None) -> str:
        summary = self.get_summary()
        alerts = self.get_alerts()
        
        report = f"""
phi-CPS Analytics Report
======================
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Summary
-------
Total Metrics: {summary['total_metrics']}
Current Status: {summary['status']}
Active Alerts: {summary['alerts']}
Average Drift: {summary['avg_drift']}

Thresholds
----------
WARNING:   2%
CRITICAL:  5%
EMERGENCY: 10%
"""
        
        if alerts:
            report += "\nActive Alerts\n-------------\n"
            for alert in alerts[-10:]:
                report += f"  [{alert.status}] {alert.component} - Drift: {alert.drift * 100:.2f}%\n"
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report