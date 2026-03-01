#!/usr/bin/env python3
"""Batch skill registration from directory scan.

Scans directory for scripts (Python/PowerShell/Bash), auto-detects type,
extracts metadata from docstrings, and registers in SkillManager.

Usage:
    python scripts/batch_skill_register.py --scan-dir ./scripts --filter "*.py"
    python scripts/batch_skill_register.py --scan-dir ./tools --validate
"""

import sys
import argparse
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.core.skill_manager import SkillManager


def detect_script_type(file_path: Path) -> Optional[str]:
    """Detect script type from file extension.
    
    Args:
        file_path: Path to script file
    
    Returns:
        Skill type or None if unsupported
    """
    suffix = file_path.suffix.lower()
    
    if suffix == ".py":
        return "PYTHON_SCRIPT"
    elif suffix in [".ps1", ".psm1"]:
        return "POWERSHELL_SCRIPT"
    elif suffix == ".sh":
        return "BASH_SCRIPT"
    
    return None


def extract_metadata_from_docstring(file_path: Path) -> Tuple[Optional[str], Dict[str, str]]:
    """Extract description and metadata from script docstring.
    
    Args:
        file_path: Path to script file
    
    Returns:
        Tuple of (description, metadata_dict)
    """
    description = None
    metadata = {}
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Python docstring
        if file_path.suffix == ".py":
            # Find first docstring (triple quotes)
            match = re.search(r'"""([\s\S]*?)"""', content)
            if match:
                docstring = match.group(1).strip()
                lines = docstring.split("\n")
                if lines:
                    description = lines[0].strip()
                
                # Extract metadata from docstring
                # Look for patterns like "Version: 1.0.0"
                for line in lines:
                    meta_match = re.match(r"\s*(\w+):\s*(.+)", line)
                    if meta_match:
                        key, value = meta_match.groups()
                        metadata[key.lower()] = value.strip()
        
        # PowerShell comment block
        elif file_path.suffix in [".ps1", ".psm1"]:
            # Find <# ... #> block
            match = re.search(r'<#([\s\S]*?)#>', content)
            if match:
                comment_block = match.group(1).strip()
                lines = comment_block.split("\n")
                if lines:
                    description = lines[0].strip()
        
        # Bash shebang + comments
        elif file_path.suffix == ".sh":
            lines = content.split("\n")
            for line in lines:
                if line.startswith("#") and not line.startswith("#!/"):
                    desc_line = line[1:].strip()
                    if desc_line and not description:
                        description = desc_line
                        break
    
    except Exception as e:
        print(f"Warning: Could not extract metadata from {file_path}: {e}")
    
    return description, metadata


def scan_and_register(
    scan_dir: str,
    file_filter: str = "*",
    validate: bool = False,
    dry_run: bool = False
) -> Dict[str, int]:
    """Scan directory and register skills.
    
    Args:
        scan_dir: Directory to scan
        file_filter: File filter pattern (e.g., "*.py")
        validate: Whether to validate registered skills
        dry_run: If True, only preview without registering
    
    Returns:
        Stats dict with counts (registered, skipped, errors)
    """
    scan_path = Path(scan_dir)
    if not scan_path.exists():
        print(f"Error: Directory not found: {scan_dir}")
        return {"registered": 0, "skipped": 0, "errors": 0}
    
    manager = SkillManager()
    stats = {"registered": 0, "skipped": 0, "errors": 0}
    
    # Find all matching files
    files = list(scan_path.glob(f"**/{file_filter}"))
    
    print(f"🔍 Scanning directory: {scan_dir}")
    print(f"   Filter: {file_filter}")
    print(f"   Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print(f"   Found {len(files)} file(s)\n")
    
    for file_path in files:
        # Detect script type
        skill_type = detect_script_type(file_path)
        if not skill_type:
            print(f"⏭️  Skipped: {file_path.name} (unsupported type)")
            stats["skipped"] += 1
            continue
        
        # Extract metadata
        description, metadata = extract_metadata_from_docstring(file_path)
        
        # Generate skill name from filename
        skill_name = file_path.stem.replace("_", "-")
        
        if dry_run:
            print(f"📝 Would register: {skill_name}")
            print(f"   Type: {skill_type}")
            print(f"   Path: {file_path}")
            print(f"   Description: {description or 'N/A'}")
            print()
            stats["registered"] += 1
            continue
        
        try:
            # Check if already registered
            existing_skills = manager.list_skills()
            if any(s["name"] == skill_name for s in existing_skills):
                print(f"⏭️  Skipped: {skill_name} (already registered)")
                stats["skipped"] += 1
                continue
            
            # Register skill
            skill_id = manager.register_skill(
                name=skill_name,
                skill_type=skill_type,
                script_path=str(file_path.absolute()),
                description=description,
                metadata=metadata
            )
            
            print(f"✅ Registered: {skill_name}")
            print(f"   Skill ID: {skill_id}")
            print(f"   Type: {skill_type}")
            
            stats["registered"] += 1
            
            # Validate if requested
            if validate:
                try:
                    validation_state, phi_cps = manager.validate_skill(skill_id)
                    print(f"   Validation: {validation_state} (φ-CPS: {phi_cps:.3f})")
                except Exception as ve:
                    print(f"   Validation: FAILED ({ve})")
            
            print()
        
        except Exception as e:
            print(f"❌ Error registering {skill_name}: {e}")
            stats["errors"] += 1
            print()
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Batch skill registration from directory scan")
    parser.add_argument("--scan-dir", required=True, help="Directory to scan for scripts")
    parser.add_argument("--filter", default="*", help="File filter pattern (e.g., '*.py')")
    parser.add_argument("--validate", action="store_true", help="Validate skills after registration")
    parser.add_argument("--dry-run", action="store_true", help="Preview without registering")
    
    args = parser.parse_args()
    
    stats = scan_and_register(
        scan_dir=args.scan_dir,
        file_filter=args.filter,
        validate=args.validate,
        dry_run=args.dry_run
    )
    
    print("=" * 60)
    print("BATCH SKILL REGISTRATION SUMMARY")
    print("=" * 60)
    print(f"Skills registered: {stats['registered']}")
    print(f"Skills skipped:    {stats['skipped']}")
    print(f"Errors:            {stats['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
