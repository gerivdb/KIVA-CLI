"""
ECOS CLI - Main Entry Point
Command-line interface for ECOS ecosystem management

IntentHash: 0x69C0965C49825C93BDDF
Generated: 2026-02-28T22:00:31.548491

Available Commands:
- ecos validate --mode [ternary|lifecycle] <entity_id>
- ecos lifecycle [show|transition|check-auto-transitions] ...
- ecos intenthash verify <hash> --level [L0|L1]
- ecos phi [check-drift|show-metrics|prepare-reset]
"""

import sys
import argparse
import json
from typing import Optional, Dict, List
from datetime import datetime

# Import Phase 6 modules
try:
    from kiva_cli.core.base3_ternary_logic import TernaryValidator, TernaryState
    from kiva_cli.core.base4_lifecycle_manager import (
        LifecycleManager, LifecycleState, LifecycleEntity
    )
    from kiva_cli.core.base4_base3_integration import (
        LifecycleValidator, LifecycleMetrics
    )
    from kiva_cli.core.intent_hash_validator import IntentHashValidator
    from kiva_cli.core.phi_cps_manager import PhiCPSManager
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Some modules not yet deployed: {e}")
    MODULES_AVAILABLE = False


class EcosCLI:
    """Main CLI controller for ECOS commands"""
    
    def __init__(self):
        self.lifecycle_manager = LifecycleManager() if MODULES_AVAILABLE else None
        self.ternary_validator = TernaryValidator() if MODULES_AVAILABLE else None
        self.lifecycle_validator = LifecycleValidator() if MODULES_AVAILABLE else None
        self.intenthash_validator = IntentHashValidator() if MODULES_AVAILABLE else None
        self.phi_manager = PhiCPSManager() if MODULES_AVAILABLE else None
    
    def validate(self, entity_id: str, mode: str = "ternary") -> Dict:
        """
        Validate entity using ternary or lifecycle logic
        
        Args:
            entity_id: Entity identifier (e.g., "repo:KIVA-CLI")
            mode: Validation mode ("ternary" or "lifecycle")
        
        Returns:
            Validation result dictionary
        """
        if mode == "ternary":
            if not self.ternary_validator:
                return {"error": "TernaryValidator not available"}
            
            # Mock validation (in production, fetch entity data)
            checks = [
                ("format_valid", TernaryState.VALID),
                ("content_valid", TernaryState.UNKNOWN)
            ]
            result = self.ternary_validator.validate(entity_id, checks)
            return {
                "entity_id": entity_id,
                "mode": "ternary",
                "state": result["state"],
                "state_name": ["UNKNOWN", "VALID", "INVALID"][result["state"]],
                "checks": result.get("checks", []),
                "timestamp": datetime.now().isoformat()
            }
        
        elif mode == "lifecycle":
            if not self.lifecycle_validator or not self.lifecycle_manager:
                return {"error": "LifecycleValidator not available"}
            
            # Fetch entity (mock for now)
            entity = self.lifecycle_manager.get_entity(entity_id)
            if not entity:
                return {
                    "error": f"Entity {entity_id} not found",
                    "suggestion": "Register entity first with lifecycle manager"
                }
            
            state, details = self.lifecycle_validator.validate_entity_lifecycle(entity)
            return {
                "entity_id": entity_id,
                "mode": "lifecycle",
                "validation_state": state,
                "validation_state_name": ["UNKNOWN", "VALID", "INVALID"][state],
                "lifecycle_state": entity.current_state.name,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
        
        else:
            return {"error": f"Invalid mode: {mode}", "allowed": ["ternary", "lifecycle"]}
    
    def lifecycle_show(self, entity_id: str) -> Dict:
        """Show entity lifecycle state and history"""
        if not self.lifecycle_manager:
            return {"error": "LifecycleManager not available"}
        
        entity = self.lifecycle_manager.get_entity(entity_id)
        if not entity:
            return {
                "error": f"Entity {entity_id} not found",
                "registered_entities": list(self.lifecycle_manager.entities.keys())
            }
        
        return entity.to_dict()
    
    def lifecycle_transition(
        self,
        entity_id: str,
        to_state: str,
        approved_by: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict:
        """Transition entity to new lifecycle state"""
        if not self.lifecycle_manager:
            return {"error": "LifecycleManager not available"}
        
        try:
            target_state = LifecycleState[to_state.upper()]
        except KeyError:
            return {
                "error": f"Invalid state: {to_state}",
                "allowed": [s.name for s in LifecycleState]
            }
        
        success, message = self.lifecycle_manager.transition_entity(
            entity_id=entity_id,
            target_state=target_state,
            reason=reason,
            approved_by=approved_by
        )
        
        return {
            "entity_id": entity_id,
            "transition_success": success,
            "message": message,
            "target_state": to_state.upper(),
            "timestamp": datetime.now().isoformat()
        }
    
    def lifecycle_check_auto_transitions(self) -> Dict:
        """Check which entities should auto-transition"""
        if not self.lifecycle_manager:
            return {"error": "LifecycleManager not available"}
        
        pending = self.lifecycle_manager.check_auto_transitions()
        
        return {
            "pending_auto_transitions": [
                {
                    "entity_id": eid,
                    "current_state": from_state.name,
                    "target_state": to_state.name,
                    "reason": f"Auto-transition from {from_state.name} after timeout"
                }
                for eid, from_state, to_state in pending
            ],
            "count": len(pending),
            "timestamp": datetime.now().isoformat()
        }
    
    def intenthash_verify(self, hash_value: str, level: str = "L0") -> Dict:
        """Verify IntentHash at specified level"""
        if not self.intenthash_validator:
            return {"error": "IntentHashValidator not available"}
        
        if level not in ["L0", "L1"]:
            return {"error": f"Invalid level: {level}", "allowed": ["L0", "L1"]}
        
        # L0: Format check
        if level == "L0":
            is_valid = self.intenthash_validator.validate_format(hash_value)
            return {
                "hash": hash_value,
                "level": "L0",
                "validation": "format_check",
                "result": "VALID" if is_valid else "INVALID",
                "timestamp": datetime.now().isoformat()
            }
        
        # L1: Chain continuity
        else:
            is_valid, chain_data = self.intenthash_validator.validate_chain_continuity(hash_value)
            return {
                "hash": hash_value,
                "level": "L1",
                "validation": "chain_continuity",
                "result": "VALID" if is_valid else "INVALID",
                "chain_data": chain_data,
                "timestamp": datetime.now().isoformat()
            }
    
    def phi_check_drift(self) -> Dict:
        """Check current φ-CPS drift vs threshold"""
        if not self.phi_manager:
            return {"error": "PhiCPSManager not available"}
        
        metrics = self.phi_manager.get_metrics()
        drift = metrics["current"] - metrics["genesis"]
        threshold = metrics["threshold"]
        
        return {
            "phi_cps_genesis": metrics["genesis"],
            "phi_cps_current": metrics["current"],
            "drift": drift,
            "threshold": threshold,
            "drift_exceeds_threshold": drift > threshold,
            "status": "FROZEN" if metrics.get("frozen") else "ACTIVE",
            "recommendation": (
                "Ecosystem-wide baseline reset required"
                if drift > threshold
                else "Drift within acceptable range"
            ),
            "timestamp": datetime.now().isoformat()
        }
    
    def phi_show_metrics(self) -> Dict:
        """Show detailed φ-CPS metrics"""
        if not self.phi_manager:
            return {"error": "PhiCPSManager not available"}
        
        return self.phi_manager.get_detailed_metrics()
    
    def phi_prepare_reset(self, preview: bool = True) -> Dict:
        """Prepare ecosystem-wide baseline reset (preview only)"""
        if not self.phi_manager:
            return {"error": "PhiCPSManager not available"}
        
        reset_plan = self.phi_manager.prepare_baseline_reset(preview=preview)
        
        return {
            "mode": "preview" if preview else "execute",
            "current_genesis": reset_plan["current_genesis"],
            "new_genesis": reset_plan["new_genesis"],
            "affected_repos": reset_plan["affected_repos"],
            "migration_plan": reset_plan["migration_plan"],
            "ecos_root_v2": reset_plan["ecos_root_v2_preview"],
            "estimated_downtime": "~5 minutes",
            "warning": "Preview only. Execute in Phase 7 with full backup.",
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="ECOS CLI - Ecosystem Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # ecos validate
    validate_parser = subparsers.add_parser("validate", help="Validate entity")
    validate_parser.add_argument("entity_id", help="Entity ID (e.g., repo:KIVA-CLI)")
    validate_parser.add_argument("--mode", choices=["ternary", "lifecycle"], default="ternary")
    
    # ecos lifecycle
    lifecycle_parser = subparsers.add_parser("lifecycle", help="Lifecycle management")
    lifecycle_sub = lifecycle_parser.add_subparsers(dest="subcommand")
    
    show_parser = lifecycle_sub.add_parser("show", help="Show lifecycle state")
    show_parser.add_argument("entity_id", help="Entity ID")
    
    transition_parser = lifecycle_sub.add_parser("transition", help="Transition state")
    transition_parser.add_argument("entity_id", help="Entity ID")
    transition_parser.add_argument("--to", required=True, help="Target state")
    transition_parser.add_argument("--approved-by", help="Approver ID")
    transition_parser.add_argument("--reason", help="Transition reason")
    
    lifecycle_sub.add_parser("check-auto-transitions", help="Check auto-transitions")
    
    # ecos intenthash
    intenthash_parser = subparsers.add_parser("intenthash", help="IntentHash operations")
    intenthash_sub = intenthash_parser.add_subparsers(dest="subcommand")
    
    verify_parser = intenthash_sub.add_parser("verify", help="Verify IntentHash")
    verify_parser.add_argument("hash", help="IntentHash to verify")
    verify_parser.add_argument("--level", choices=["L0", "L1"], default="L0")
    
    # ecos phi
    phi_parser = subparsers.add_parser("phi", help="φ-CPS management")
    phi_sub = phi_parser.add_subparsers(dest="subcommand")
    
    phi_sub.add_parser("check-drift", help="Check φ-CPS drift")
    phi_sub.add_parser("show-metrics", help="Show detailed metrics")
    
    reset_parser = phi_sub.add_parser("prepare-reset", help="Prepare baseline reset")
    reset_parser.add_argument("--preview", action="store_true", default=True)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = EcosCLI()
    result = None
    
    # Route commands
    if args.command == "validate":
        result = cli.validate(args.entity_id, args.mode)
    
    elif args.command == "lifecycle":
        if args.subcommand == "show":
            result = cli.lifecycle_show(args.entity_id)
        elif args.subcommand == "transition":
            result = cli.lifecycle_transition(
                args.entity_id,
                args.to,
                args.approved_by,
                args.reason
            )
        elif args.subcommand == "check-auto-transitions":
            result = cli.lifecycle_check_auto_transitions()
    
    elif args.command == "intenthash":
        if args.subcommand == "verify":
            result = cli.intenthash_verify(args.hash, args.level)
    
    elif args.command == "phi":
        if args.subcommand == "check-drift":
            result = cli.phi_check_drift()
        elif args.subcommand == "show-metrics":
            result = cli.phi_show_metrics()
        elif args.subcommand == "prepare-reset":
            result = cli.phi_prepare_reset(args.preview)
    
    # Output result
    if result:
        print(json.dumps(result, indent=2))
        return 0 if not result.get("error") else 1
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
