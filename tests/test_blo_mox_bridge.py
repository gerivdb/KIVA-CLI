#!/usr/bin/env python3
"""
Test Suite: BLO-MOX Bridge

Tests for the BLO-MOX PRD synchronization bridge.
"""

import pytest
import os
import sys
from pathlib import Path
import tempfile
import shutil

# Add repo root to path for direct import
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import blo_mox_bridge as bm_bridge
from blo_mox_bridge import (
    extract_frontmatter,
    sync_blo_to_mox,
    ELIGIBLE_STATUSES,
)


@pytest.fixture
def temp_prd_dir():
    """Create a temporary BLO PRD directory with test files."""
    temp_dir = Path(tempfile.mkdtemp(prefix="blo_mox_test_"))
    
    # Create a valid PRD file
    valid_prd = temp_dir / "PRD-TEST-001.md"
    valid_prd.write_text(
        "---\n"
        "type: PRD\n"
        "status: active\n"
        "intent_hash: 0xTEST12345678\n"
        "title: Test PRD\n"
        "repo: gerivdb/BLO\n"
        "body: This is a test PRD body.\n"
        "---\n"
        "# Test PRD\n"
        "Content here.\n",
        encoding="utf-8"
    )
    
    # Create a draft PRD file
    draft_prd = temp_dir / "PRD-TEST-002.md"
    draft_prd.write_text(
        "---\n"
        "type: PRD\n"
        "status: draft\n"
        "intent_hash: 0xTEST87654321\n"
        "title: Draft PRD\n"
        "repo: gerivdb/BLO\n"
        "---\n"
        "# Draft PRD\n",
        encoding="utf-8"
    )
    
    # Create a file without frontmatter
    no_fm = temp_dir / "PRD-NOFM.md"
    no_fm.write_text("# No frontmatter\n", encoding="utf-8")
    
    # Create a file with ineligible status
    archived = temp_dir / "PRD-ARCHIVED.md"
    archived.write_text(
        "---\n"
        "type: PRD\n"
        "status: archived\n"
        "---\n"
        "# Archived\n",
        encoding="utf-8"
    )
    
    yield temp_dir
    
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="blo_mox_out_"))
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


def _patch_paths(monkeypatch, prd_dir, template, output_dir):
    """Patch module-level path constants."""
    monkeypatch.setattr(bm_bridge, "BLO_PRD_DIR", prd_dir)
    monkeypatch.setattr(bm_bridge, "MOX_TEMPLATE", template)
    monkeypatch.setattr(bm_bridge, "PRD_OUTPUT_DIR", output_dir)


class TestExtractFrontmatter:
    """Test extract_frontmatter function."""

    def test_extract_valid_frontmatter(self, temp_prd_dir):
        """Test extracting valid YAML frontmatter."""
        prd_file = temp_prd_dir / "PRD-TEST-001.md"
        fm = extract_frontmatter(prd_file)
        
        assert fm is not None
        assert fm.get("type") == "PRD"
        assert fm.get("status") == "active"
        assert fm.get("intent_hash") == "0xTEST12345678"

    def test_extract_no_frontmatter(self, temp_prd_dir):
        """Test extracting from file without frontmatter."""
        prd_file = temp_prd_dir / "PRD-NOFM.md"
        fm = extract_frontmatter(prd_file)
        
        assert fm is None

    def test_extract_invalid_yaml(self, tmp_path):
        """Test extracting from file with invalid YAML."""
        bad_yaml = tmp_path / "bad.yaml.md"
        bad_yaml.write_text(
            "---\n"
            "type: PRD\n"
            "status: active\n"
            "invalid: [yaml\n"
            "---\n",
            encoding="utf-8"
        )
        fm = extract_frontmatter(bad_yaml)
        assert fm is None


class TestSyncBloToMox:
    """Test sync_blo_to_mox function."""

    def test_dry_run_with_valid_prds(self, temp_prd_dir, temp_output_dir, monkeypatch):
        """Test dry-run sync with valid PRDs."""
        _patch_paths(monkeypatch, temp_prd_dir, temp_prd_dir / "nonexistent.md", temp_output_dir)
        
        results = sync_blo_to_mox(dry_run=True)
        
        # Should process valid PRDs
        assert len(results) > 0
        # No files should be created in dry-run
        assert temp_output_dir.exists()
        # Count DRY-RUN entries
        dry_run_count = sum(1 for r in results if "[DRY-RUN]" in r)
        assert dry_run_count >= 2  # At least the 2 eligible PRDs

    def test_live_sync_creates_files(self, temp_prd_dir, temp_output_dir, monkeypatch):
        """Test live sync creates output files."""
        _patch_paths(monkeypatch, temp_prd_dir, temp_prd_dir / "nonexistent.md", temp_output_dir)
        
        results = sync_blo_to_mox(dry_run=False)
        
        # Should create output files for eligible PRDs
        sync_count = sum(1 for r in results if "[SYNC] Created" in r)
        assert sync_count >= 2
        
        # Verify files exist
        output_files = list(temp_output_dir.glob("*.md"))
        assert len(output_files) >= 2

    def test_missing_blo_dir(self, tmp_path, monkeypatch):
        """Test handling of missing BLO PRD directory."""
        _patch_paths(monkeypatch, tmp_path / "nonexistent", tmp_path / "nonexistent.md", tmp_path / "out")
        
        results = sync_blo_to_mox(dry_run=True)
        
        assert len(results) == 1
        assert "[SKIP]" in results[0]
        assert "not found" in results[0]

    def test_eligible_statuses(self):
        """Test that eligible statuses are correctly defined."""
        assert "active" in ELIGIBLE_STATUSES
        assert "draft" in ELIGIBLE_STATUSES
        assert "proposed" in ELIGIBLE_STATUSES
        assert "archived" not in ELIGIBLE_STATUSES

    def test_skips_ineligible_status(self, temp_prd_dir, temp_output_dir, monkeypatch):
        """Test that ineligible statuses are skipped."""
        _patch_paths(monkeypatch, temp_prd_dir, temp_prd_dir / "nonexistent.md", temp_output_dir)
        
        results = sync_blo_to_mox(dry_run=True)
        
        # Archived PRD should be skipped
        skip_archived = any("archived" in r.lower() and "[SKIP]" in r for r in results)
        assert skip_archived

    def test_skips_no_frontmatter(self, temp_prd_dir, temp_output_dir, monkeypatch):
        """Test that files without frontmatter are skipped."""
        _patch_paths(monkeypatch, temp_prd_dir, temp_prd_dir / "nonexistent.md", temp_output_dir)
        
        results = sync_blo_to_mox(dry_run=True)
        
        # PRD-NOFM.md should be skipped
        skip_nofm = any("PRD-NOFM" in r and "[SKIP]" in r for r in results)
        assert skip_nofm
