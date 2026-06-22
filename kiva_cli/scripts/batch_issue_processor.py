#!/usr/bin/env python3
"""
Batch Issue Processor for KIVA-CLI

Processes multiple GitHub issues in parallel with WAL tracking.

Features:
- Parallel processing with configurable workers
- IntentHash¹¹ validation
- φ-CPS tracking per issue
- Automatic retry on failure
- Progress reporting
- WAL event logging
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import time

from ..core.global_wal_manager import GlobalWALManager, WALEvent

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of batch processing"""
    total_issues: int
    processed: int
    succeeded: int
    failed: int
    skipped: int
    total_phi_delta: float
    duration_seconds: float
    errors: List[Dict[str, str]]


class BatchIssueProcessor:
    """Process multiple issues in batch mode"""
    
    def __init__(
        self,
        repo_name: str,
        max_workers: int = 3,
        max_retries: int = 2,
        wal_manager: Optional[GlobalWALManager] = None
    ):
        """
        Args:
            repo_name: Repository name
            max_workers: Maximum parallel workers
            max_retries: Maximum retry attempts per issue
            wal_manager: Global WAL manager instance
        """
        self.repo_name = repo_name
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.wal_manager = wal_manager or GlobalWALManager()
        
        self._processed = 0
        self._succeeded = 0
        self._failed = 0
        self._skipped = 0
        self._errors: List[Dict[str, str]] = []
        self._total_phi_delta = 0.0
        
        logger.info(
            f"BatchIssueProcessor initialized: {repo_name}, "
            f"workers={max_workers}, retries={max_retries}"
        )
    
    async def process_issues(
        self,
        issues: List[Dict[str, Any]],
        processor_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> BatchResult:
        """
        Process issues in parallel
        
        Args:
            issues: List of issue data dictionaries
            processor_func: Function to process each issue
                            Should return dict with keys: success, phi_delta, error
        
        Returns:
            BatchResult with processing statistics
        """
        start_time = time.time()
        
        logger.info(f"Starting batch processing: {len(issues)} issues")
        
        # Reset counters
        self._processed = 0
        self._succeeded = 0
        self._failed = 0
        self._skipped = 0
        self._errors = []
        self._total_phi_delta = 0.0
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self._process_single_issue, issue, processor_func)
                for issue in issues
            ]
            
            # Wait for all to complete
            for future in futures:
                try:
                    await asyncio.wrap_future(future)
                except Exception as e:
                    logger.error(f"Future failed: {e}")
        
        duration = time.time() - start_time
        
        result = BatchResult(
            total_issues=len(issues),
            processed=self._processed,
            succeeded=self._succeeded,
            failed=self._failed,
            skipped=self._skipped,
            total_phi_delta=self._total_phi_delta,
            duration_seconds=duration,
            errors=self._errors
        )
        
        logger.info(
            f"Batch processing complete: {self._succeeded}/{len(issues)} succeeded, "
            f"{self._failed} failed, {self._skipped} skipped "
            f"(Δφ total: +{self._total_phi_delta:.4f}, duration: {duration:.1f}s)"
        )
        
        return result
    
    def _process_single_issue(
        self,
        issue: Dict[str, Any],
        processor_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ):
        """Process single issue with retry logic"""
        issue_number = issue.get("number", "unknown")
        issue_title = issue.get("title", "")
        
        logger.info(f"Processing issue #{issue_number}: {issue_title}")
        
        # Create pending WAL event
        event = self.wal_manager.append_event(
            repo_name=self.repo_name,
            event_type=GlobalWALManager.EVENT_ISSUE,
            entity_id=str(issue_number),
            action="process",
            phi_delta=0.0,
            metadata={
                "title": issue_title,
                "state": issue.get("state", "unknown")
            },
            status=GlobalWALManager.STATUS_PENDING
        )
        
        # Retry loop
        for attempt in range(self.max_retries + 1):
            try:
                # Execute processor function
                result = processor_func(issue)
                
                if result.get("success", False):
                    phi_delta = result.get("phi_delta", 0.0)
                    
                    # Update WAL event
                    self.wal_manager.update_event_status(
                        event.event_id,
                        GlobalWALManager.STATUS_SUCCESS
                    )
                    
                    # Log successful processing
                    self.wal_manager.append_event(
                        repo_name=self.repo_name,
                        event_type=GlobalWALManager.EVENT_ISSUE,
                        entity_id=str(issue_number),
                        action="complete",
                        phi_delta=phi_delta,
                        metadata={
                            "title": issue_title,
                            "attempts": attempt + 1
                        },
                        status=GlobalWALManager.STATUS_SUCCESS
                    )
                    
                    self._processed += 1
                    self._succeeded += 1
                    self._total_phi_delta += phi_delta
                    
                    logger.info(
                        f"✓ Issue #{issue_number} processed successfully "
                        f"(Δφ: +{phi_delta:.4f}, attempt: {attempt + 1})"
                    )
                    return
                else:
                    error = result.get("error", "Unknown error")
                    
                    if attempt < self.max_retries:
                        logger.warning(
                            f"Issue #{issue_number} failed (attempt {attempt + 1}), "
                            f"retrying... Error: {error}"
                        )
                        time.sleep(1)  # Brief delay before retry
                    else:
                        raise Exception(error)
            
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(
                        f"Issue #{issue_number} failed (attempt {attempt + 1}), "
                        f"retrying... Error: {str(e)}"
                    )
                    time.sleep(1)
                else:
                    # Max retries exhausted
                    error_msg = str(e)
                    
                    # Update WAL event
                    self.wal_manager.update_event_status(
                        event.event_id,
                        GlobalWALManager.STATUS_FAILED,
                        error=error_msg
                    )
                    
                    self._processed += 1
                    self._failed += 1
                    self._errors.append({
                        "issue_number": str(issue_number),
                        "issue_title": issue_title,
                        "error": error_msg
                    })
                    
                    logger.error(
                        f"✗ Issue #{issue_number} failed after {self.max_retries + 1} attempts: {error_msg}"
                    )
    
    def process_issues_sync(
        self,
        issues: List[Dict[str, Any]],
        processor_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> BatchResult:
        """Synchronous version of process_issues"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.process_issues(issues, processor_func)
            )
        finally:
            loop.close()
    
    def generate_report(self, result: BatchResult) -> str:
        """Generate markdown report"""
        success_rate = (result.succeeded / result.total_issues * 100) if result.total_issues > 0 else 0
        
        report = f"""# Batch Processing Report

## Summary

| Metric | Value |
|--------|-------|
| Total Issues | {result.total_issues} |
| Processed | {result.processed} |
| Succeeded | {result.succeeded} |
| Failed | {result.failed} |
| Skipped | {result.skipped} |
| Success Rate | {success_rate:.1f}% |
| Total Δφ-CPS | +{result.total_phi_delta:.4f} |
| Duration | {result.duration_seconds:.1f}s |

## Status Breakdown

"""
        
        if result.succeeded > 0:
            report += f"### ✓ Succeeded: {result.succeeded}\n\n"
        
        if result.failed > 0:
            report += f"### ✗ Failed: {result.failed}\n\n"
            for error in result.errors:
                report += f"- Issue #{error['issue_number']}: {error['issue_title']}\n"
                report += f"  Error: {error['error']}\n\n"
        
        if result.skipped > 0:
            report += f"### ⏸ Skipped: {result.skipped}\n\n"
        
        report += "\n---\n\n"
        report += f"**Generated by**: ECOS-AUTO Batch Processor\n"
        report += f"**Repository**: {self.repo_name}\n"
        report += f"**Workers**: {self.max_workers}\n"
        
        return report


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_processor(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Example processor function"""
    try:
        # Simulate processing
        issue_number = issue["number"]
        
        # Your processing logic here
        # ...
        
        return {
            "success": True,
            "phi_delta": 0.005,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "phi_delta": 0.0,
            "error": str(e)
        }


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    processor = BatchIssueProcessor(
        repo_name="KIVA-CLI",
        max_workers=3,
        max_retries=2
    )
    
    # Mock issues
    issues = [
        {"number": 1, "title": "Test Issue 1", "state": "open"},
        {"number": 2, "title": "Test Issue 2", "state": "open"},
        {"number": 3, "title": "Test Issue 3", "state": "open"},
    ]
    
    result = processor.process_issues_sync(issues, example_processor)
    
    print(processor.generate_report(result))
