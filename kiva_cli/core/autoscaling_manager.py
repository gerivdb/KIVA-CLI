#!/usr/bin/env python3
"""
Auto-Scaling Manager - KIVA CLI

Manages auto-scaling policies for ECOS services and containers.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any


class ScalingPolicy:
    """Represents an auto-scaling policy."""
    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.service = data.get("service", "")
        self.min_instances = data.get("min_instances", 1)
        self.max_instances = data.get("max_instances", 10)
        self.cpu_threshold = data.get("cpu_threshold", 80)
        self.memory_threshold = data.get("memory_threshold", 85)
        self.scale_up_factor = data.get("scale_up_factor", 2)
        self.scale_down_factor = data.get("scale_down_factor", 0.5)
        self.cooldown_period = data.get("cooldown_period", 300)
        self.last_scale_time = data.get("last_scale_time", "")


class AutoScalingManager:
    """Manages auto-scaling policies."""

    def __init__(self, policies_path: Optional[str] = None):
        if policies_path is None:
            policies_path = "C:\\DevTools\\data\\autoscaling\\policies.json"
        self.policies_path = Path(policies_path)
        self.policies: Dict[str, ScalingPolicy] = {}
        self._load_policies()

    def _load_policies(self):
        if self.policies_path.exists():
            try:
                with open(self.policies_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for name, info in data.get("policies", {}).items():
                    self.policies[name] = ScalingPolicy(info)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_policies(self):
        data = {
            "policies": {
                name: {
                    "name": p.name,
                    "service": p.service,
                    "min_instances": p.min_instances,
                    "max_instances": p.max_instances,
                    "cpu_threshold": p.cpu_threshold,
                    "memory_threshold": p.memory_threshold,
                    "scale_up_factor": p.scale_up_factor,
                    "scale_down_factor": p.scale_down_factor,
                    "cooldown_period": p.cooldown_period,
                    "last_scale_time": p.last_scale_time
                }
                for name, p in self.policies.items()
            }
        }
        os.makedirs(os.path.dirname(self.policies_path), exist_ok=True)
        with open(self.policies_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_policy(self, name: str, service: str, min_instances: int = 1, max_instances: int = 10, cpu_threshold: float = 80, memory_threshold: float = 85) -> bool:
        self.policies[name] = ScalingPolicy({
            "name": name,
            "service": service,
            "min_instances": min_instances,
            "max_instances": max_instances,
            "cpu_threshold": cpu_threshold,
            "memory_threshold": memory_threshold,
            "scale_up_factor": 2,
            "scale_down_factor": 0.5,
            "cooldown_period": 300,
            "last_scale_time": ""
        })
        self._save_policies()
        return True

    def delete_policy(self, name: str) -> bool:
        if name in self.policies:
            del self.policies[name]
            self._save_policies()
            return True
        return False

    def list_policies(self) -> List[ScalingPolicy]:
        return list(self.policies.values())

    def get_policy(self, name: str) -> Optional[ScalingPolicy]:
        return self.policies.get(name)

    def evaluate_policy(self, name: str, current_cpu: float, current_memory: float, current_instances: int) -> Dict[str, Any]:
        policy = self.policies.get(name)
        if not policy:
            return {"action": "none", "reason": "Policy not found"}

        # Check cooldown
        if policy.last_scale_time:
            last_scale = time.strptime(policy.last_scale_time, "%Y-%m-%dT%H:%M:%SZ")
            elapsed = time.time() - time.mktime(last_scale)
            if elapsed < policy.cooldown_period:
                return {"action": "none", "reason": "Cooldown period active"}

        # Scale up decision
        if current_cpu > policy.cpu_threshold or current_memory > policy.memory_threshold:
            new_instances = min(int(current_instances * policy.scale_up_factor), policy.max_instances)
            if new_instances > current_instances:
                policy.last_scale_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                self._save_policies()
                return {
                    "action": "scale_up",
                    "current_instances": current_instances,
                    "new_instances": new_instances,
                    "reason": f"CPU: {current_cpu}%, Memory: {current_memory}% exceeded thresholds"
                }

        # Scale down decision
        if current_cpu < policy.cpu_threshold * 0.5 and current_memory < policy.memory_threshold * 0.5:
            new_instances = max(int(current_instances * policy.scale_down_factor), policy.min_instances)
            if new_instances < current_instances:
                policy.last_scale_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                self._save_policies()
                return {
                    "action": "scale_down",
                    "current_instances": current_instances,
                    "new_instances": new_instances,
                    "reason": f"CPU: {current_cpu}%, Memory: {current_memory}% below thresholds"
                }

        return {"action": "none", "reason": "Within thresholds"}