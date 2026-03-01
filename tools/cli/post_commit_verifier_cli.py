#!/usr/bin/env python3
"""CLI interface for PostCommitVerifierSkill.

Usage:
    python post_commit_verifier_cli.py \
        --repository gerivdb/BRAIN \
        --commit ace91d0a3170f122276c14abca3d02649e935869 \
        --branch main \
        --expect guides/components/PhiMonitorDaemon.md:4ff8762d \
        --expect guides/components/AutoRollbackPipeline.md:dbcb9e4e \
        --max-retries 3 \
        --auto-rollback
"""

import argparse
import json
import logging
import os
import sys
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.post_commit_verifier_skill import (
    FileExpectation,
    PostCommitVerifierSkill,
    VerificationStatus
)


def parse_expectation(expectation_str: str) -> FileExpectation:
    """Parse expectation string in format 'path' or 'path:sha' or 'path:sha:size'."""
    parts = expectation_str.split(':')
    
    if len(parts) == 1:
        return FileExpectation(path=parts[0])
    elif len(parts) == 2:
        return FileExpectation(path=parts[0], sha=parts[1])
    elif len(parts) == 3:
        return FileExpectation(path=parts[0], sha=parts[1], size=int(parts[2]))
    else:
        raise ValueError(f"Invalid expectation format: {expectation_str}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Verify files exist after GitHub commit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify single file exists
  %(prog)s --repository gerivdb/BRAIN --commit abc123 --branch main \
    --expect guides/MyGuide.md

  # Verify file with SHA validation
  %(prog)s --repository gerivdb/BRAIN --commit abc123 --branch main \
    --expect guides/MyGuide.md:4ff8762d

  # Verify multiple files with auto-rollback
  %(prog)s --repository gerivdb/BRAIN --commit abc123 --branch main \
    --expect guides/File1.md:sha1 \
    --expect guides/File2.md:sha2 \
    --auto-rollback
        """
    )
    
    parser.add_argument(
        '--repository', '-r',
        required=True,
        help='Repository in format owner/repo (e.g., gerivdb/BRAIN)'
    )
    parser.add_argument(
        '--commit', '-c',
        required=True,
        help='Commit SHA to verify'
    )
    parser.add_argument(
        '--branch', '-b',
        required=True,
        help='Branch name (e.g., main)'
    )
    parser.add_argument(
        '--expect', '-e',
        action='append',
        dest='expectations',
        required=True,
        help='Expected file in format path[:sha[:size]]. Can be repeated.'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum verification attempts per file (default: 3)'
    )
    parser.add_argument(
        '--retry-delay',
        type=float,
        default=2.0,
        help='Initial retry delay in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--no-exponential-backoff',
        action='store_true',
        help='Disable exponential backoff for retries'
    )
    parser.add_argument(
        '--auto-rollback',
        action='store_true',
        help='Automatically trigger rollback on verification failure'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output JSON file path (default: stdout)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Get GitHub token
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        return 1
    
    # Parse expectations
    try:
        expected_files = [parse_expectation(exp) for exp in args.expectations]
    except ValueError as e:
        logger.error(f"Invalid expectation: {e}")
        return 1
    
    # Create verifier
    verifier = PostCommitVerifierSkill(
        github_token=github_token,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        exponential_backoff=not args.no_exponential_backoff,
        auto_rollback=args.auto_rollback,
        logger=logger
    )
    
    # Run verification
    logger.info(f"Verifying {len(expected_files)} files in {args.repository}@{args.commit[:8]}")
    
    verification = verifier.verify(
        repository=args.repository,
        commit_sha=args.commit,
        branch=args.branch,
        expected_files=expected_files
    )
    
    # Output results
    json_output = verifier.to_json(verification)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        logger.info(f"Results written to {args.output}")
    else:
        print(json_output)
    
    # Exit code based on verification status
    if verification.overall_status == VerificationStatus.VALID:
        logger.info("✅ All files verified successfully")
        return 0
    elif verification.overall_status == VerificationStatus.INVALID:
        logger.error(f"❌ Verification failed: {verification.error_summary}")
        return 1
    else:
        logger.warning("⚠️  Verification status unknown")
        return 2


if __name__ == '__main__':
    sys.exit(main())
