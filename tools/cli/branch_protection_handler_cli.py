#!/usr/bin/env python3
"""CLI interface for BranchProtectionHandlerSkill.

Usage:
    python branch_protection_handler_cli.py \
        --repository gerivdb/BRAIN \
        --base-branch main \
        --title '[ECOS-AUTO] Add documentation' \
        --body 'Auto-generated guides for components' \
        --file guides/MyGuide.md:content.md \
        --auto-merge \
        --reviewer gerivdb
"""

import argparse
import json
import logging
import os
import sys
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.branch_protection_handler_skill import (
    BranchProtectionHandlerSkill,
    FileChange,
    PRStatus
)


def parse_file_spec(file_spec: str) -> FileChange:
    """Parse file specification in format 'path:content_file'.
    
    Args:
        file_spec: File spec like 'guides/MyGuide.md:content.md'
        
    Returns:
        FileChange object
    """
    parts = file_spec.split(':', 1)
    
    if len(parts) != 2:
        raise ValueError(
            f"Invalid file spec: {file_spec}. Expected format: path:content_file"
        )
    
    path, content_file = parts
    
    # Read content from file
    with open(content_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return FileChange(path=path, content=content)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Handle protected branches with PR workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create PR for single file
  %(prog)s --repository gerivdb/BRAIN --base-branch main \
    --title '[ECOS-AUTO] Add guide' \
    --body 'Auto-generated documentation' \
    --file guides/MyGuide.md:content.md \
    --auto-merge

  # Create PR with multiple files and reviewer
  %(prog)s --repository gerivdb/BRAIN --base-branch main \
    --title '[ECOS-AUTO] Update guides' \
    --body 'Batch update for component guides' \
    --file guides/Guide1.md:guide1.md \
    --file guides/Guide2.md:guide2.md \
    --reviewer gerivdb
        """
    )
    
    parser.add_argument(
        '--repository', '-r',
        required=True,
        help='Repository in format owner/repo (e.g., gerivdb/BRAIN)'
    )
    parser.add_argument(
        '--base-branch', '-b',
        required=True,
        help='Base branch (e.g., main)'
    )
    parser.add_argument(
        '--title', '-t',
        required=True,
        help='PR title'
    )
    parser.add_argument(
        '--body',
        required=True,
        help='PR body/description'
    )
    parser.add_argument(
        '--file', '-f',
        action='append',
        dest='files',
        required=True,
        help='File in format path:content_file. Can be repeated.'
    )
    parser.add_argument(
        '--reviewer',
        action='append',
        dest='reviewers',
        help='GitHub username to request review. Can be repeated.'
    )
    parser.add_argument(
        '--auto-merge',
        action='store_true',
        help='Automatically merge PR when approved (No-HITL mode)'
    )
    parser.add_argument(
        '--no-delete-branch',
        action='store_true',
        help='Do not delete feature branch after merge'
    )
    parser.add_argument(
        '--merge-method',
        choices=['squash', 'merge', 'rebase'],
        default='squash',
        help='Merge method (default: squash)'
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
    
    # Parse file specifications
    try:
        file_changes = [parse_file_spec(f) for f in args.files]
    except Exception as e:
        logger.error(f"Error parsing file specs: {e}")
        return 1
    
    # Create handler
    handler = BranchProtectionHandlerSkill(
        github_token=github_token,
        auto_merge=args.auto_merge,
        delete_branch_on_merge=not args.no_delete_branch,
        merge_method=args.merge_method,
        logger=logger
    )
    
    # Run PR workflow
    logger.info(
        f"Starting PR workflow for {args.repository} "
        f"({len(file_changes)} files)"
    )
    
    workflow = handler.handle(
        repository=args.repository,
        base_branch=args.base_branch,
        files=file_changes,
        title=args.title,
        body=args.body,
        reviewers=args.reviewers
    )
    
    # Output results
    json_output = handler.to_json(workflow)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        logger.info(f"Results written to {args.output}")
    else:
        print(json_output)
    
    # Exit code based on PR status
    if workflow.pr_status == PRStatus.MERGED:
        logger.info(
            f"✅ PR #{workflow.pr_number} merged successfully: {workflow.pr_url}"
        )
        return 0
    elif workflow.pr_status == PRStatus.OPEN:
        logger.info(
            f"⏳ PR #{workflow.pr_number} awaiting review: {workflow.pr_url}"
        )
        return 0
    elif workflow.pr_status == PRStatus.FAILED:
        logger.error(f"❌ PR workflow failed: {workflow.error_message}")
        return 1
    else:
        logger.warning("⚠️  PR status unknown")
        return 2


if __name__ == '__main__':
    sys.exit(main())
