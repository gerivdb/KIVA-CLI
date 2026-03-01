#!/usr/bin/env python3
"""PhiMonitor Daemon - Real-time φ-CPS drift monitoring.

Monitors ECOS_ROOT.json every 1 minute for φ-CPS drift detection.
Triggers alerts and initiates AutoRollback Pipeline if threshold exceeded.

Base-3 States:
- UNKNOWN: Initial state before first reading
- VALID: φ-CPS within threshold (Δφ ≤ 0.05)
- INVALID: φ-CPS exceeds threshold (Δφ > 0.05)

Base-4 Lifecycle:
- GENESIS: Daemon starting
- ACTIVE: Monitoring in progress
- DEPRECATED: Graceful shutdown initiated
- ARCHIVED: Daemon stopped
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidationState(Enum):
    """Base-3 ternary validation states."""
    UNKNOWN = 0.0
    VALID = 1.0
    INVALID = 0.5


class LifecycleState(Enum):
    """Base-4 lifecycle states."""
    GENESIS = "GENESIS"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class PhiMonitorDaemon:
    """Daemon for monitoring φ-CPS drift in real-time."""

    def __init__(
        self,
        ecos_root_path: str = "ECOS_ROOT.json",
        check_interval: int = 60,  # seconds
        threshold: float = 0.05,
        grace_period: int = 300,  # seconds
    ):
        """Initialize PhiMonitor Daemon.
        
        Args:
            ecos_root_path: Path to ECOS_ROOT.json
            check_interval: Seconds between checks (default 60s = 1min)
            threshold: φ-CPS drift threshold (default 0.05)
            grace_period: Seconds before triggering rollback (default 300s = 5min)
        """
        self.ecos_root_path = Path(ecos_root_path)
        self.check_interval = check_interval
        self.threshold = threshold
        self.grace_period = grace_period
        
        self.lifecycle_state = LifecycleState.GENESIS
        self.validation_state = ValidationState.UNKNOWN
        self.phi_baseline: Optional[float] = None
        self.phi_current: Optional[float] = None
        self.phi_delta: Optional[float] = None
        self.alert_triggered_at: Optional[datetime] = None
        self.running = False

    async def start(self):
        """Start the daemon monitoring loop."""
        logger.info("PhiMonitor Daemon starting...")
        self.lifecycle_state = LifecycleState.GENESIS
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        
        # Initial read
        await self._read_ecos_root()
        
        self.lifecycle_state = LifecycleState.ACTIVE
        logger.info(f"PhiMonitor Daemon ACTIVE - checking every {self.check_interval}s")
        
        # Main monitoring loop
        while self.running:
            try:
                await self._monitor_cycle()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                await asyncio.sleep(self.check_interval)

    async def _monitor_cycle(self):
        """Execute one monitoring cycle."""
        # Read current φ-CPS state
        await self._read_ecos_root()
        
        # Validate φ-CPS drift
        self._validate_phi_drift()
        
        # Check if alert grace period exceeded
        if self.alert_triggered_at:
            elapsed = (datetime.now() - self.alert_triggered_at).total_seconds()
            if elapsed > self.grace_period:
                logger.critical(
                    f"Grace period exceeded ({elapsed:.0f}s > {self.grace_period}s) - "
                    f"Triggering AutoRollback Pipeline"
                )
                await self._trigger_rollback()

    async def _read_ecos_root(self):
        """Read ECOS_ROOT.json and extract φ-CPS metrics."""
        try:
            with open(self.ecos_root_path, 'r') as f:
                data = json.load(f)
            
            self.phi_baseline = data.get("phi_cps_baseline")
            self.phi_current = data.get("phi_cps_current")
            self.phi_delta = data.get("phi_cps_delta")
            
            logger.debug(
                f"φ-CPS State: baseline={self.phi_baseline}, "
                f"current={self.phi_current}, delta={self.phi_delta}"
            )
        except FileNotFoundError:
            logger.error(f"ECOS_ROOT.json not found at {self.ecos_root_path}")
            self.validation_state = ValidationState.UNKNOWN
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in ECOS_ROOT.json: {e}")
            self.validation_state = ValidationState.UNKNOWN

    def _validate_phi_drift(self):
        """Validate φ-CPS drift against threshold."""
        if self.phi_delta is None:
            self.validation_state = ValidationState.UNKNOWN
            return
        
        if self.phi_delta <= self.threshold:
            # Within threshold - clear alert
            if self.validation_state == ValidationState.INVALID:
                logger.info(
                    f"φ-CPS drift resolved: Δφ={self.phi_delta:.3f} ≤ {self.threshold}"
                )
                self.alert_triggered_at = None
            self.validation_state = ValidationState.VALID
        else:
            # Exceeds threshold - trigger alert
            if self.validation_state != ValidationState.INVALID:
                logger.warning(
                    f"⚠️ φ-CPS ALERT: Drift Δφ={self.phi_delta:.3f} > {self.threshold} "
                    f"(baseline={self.phi_baseline}, current={self.phi_current})"
                )
                self.alert_triggered_at = datetime.now()
            self.validation_state = ValidationState.INVALID

    async def _trigger_rollback(self):
        """Trigger AutoRollback Pipeline (external process)."""
        logger.critical("🚨 TRIGGERING AUTO-ROLLBACK PIPELINE 🚨")
        
        # In production, this would launch the AutoRollbackPipeline
        # For now, log the trigger event
        try:
            from tools.pipeline.auto_rollback_pipeline import AutoRollbackPipeline
            pipeline = AutoRollbackPipeline(
                ecos_root_path=str(self.ecos_root_path)
            )
            result = await pipeline.execute()
            
            if result["status"] == "SUCCESS":
                logger.info("AutoRollback Pipeline completed successfully")
                self.alert_triggered_at = None
                self.validation_state = ValidationState.VALID
            else:
                logger.error(f"AutoRollback Pipeline failed: {result.get('error')}")
        except ImportError:
            logger.error("AutoRollback Pipeline not available (import failed)")
        except Exception as e:
            logger.error(f"Failed to trigger AutoRollback Pipeline: {e}")

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown signals."""
        logger.info(f"Received signal {signum} - initiating graceful shutdown")
        self.lifecycle_state = LifecycleState.DEPRECATED
        self.running = False

    async def stop(self):
        """Stop the daemon gracefully."""
        logger.info("PhiMonitor Daemon stopping...")
        self.lifecycle_state = LifecycleState.DEPRECATED
        self.running = False
        await asyncio.sleep(1)  # Allow current cycle to finish
        self.lifecycle_state = LifecycleState.ARCHIVED
        logger.info("PhiMonitor Daemon stopped")

    def get_status(self) -> Dict:
        """Get current daemon status."""
        return {
            "lifecycle_state": self.lifecycle_state.value,
            "validation_state": self.validation_state.name,
            "phi_baseline": self.phi_baseline,
            "phi_current": self.phi_current,
            "phi_delta": self.phi_delta,
            "threshold": self.threshold,
            "alert_active": self.alert_triggered_at is not None,
            "alert_triggered_at": self.alert_triggered_at.isoformat() if self.alert_triggered_at else None,
            "running": self.running,
        }


async def main():
    """Main entry point for daemon."""
    daemon = PhiMonitorDaemon(
        ecos_root_path="ECOS_ROOT.json",
        check_interval=60,
        threshold=0.05,
        grace_period=300,
    )
    
    try:
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())
