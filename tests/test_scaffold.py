"""Tests P10 — Scaffold Scanner CLI."""
import pytest
import yaml
import tempfile
from pathlib import Path
from kiva_cli.scaffold.gap_parser import parse_gap, infer_check_type, GapMeta, _slugify
from kiva_cli.scaffold.scanner_template import generate_scanner_yaml, generate_from_gap_id


MOCK_REPORT = {
    "by_priority": {
        "P1": [
            {
                "id": "SGR-TEST-001",
                "title": "Scanner ARGUS manquant pour TEST-REPO",
                "severity": "P1",
                "source": "TEST-REPO",
                "trit": "TritObserve",
                "action": "Creer un scanner ARGUS pour surveiller TEST-REPO",
                "family": "monitoring",
                "status": "open",
            },
            {
                "id": "SGR-CLOSED-001",
                "title": "Gap deja resolu",
                "severity": "P1",
                "source": "CLOSED-REPO",
                "trit": "TritObserve",
                "action": "Rien a faire",
                "family": "",
                "status": "closed",
            },
        ],
        "P2": [
            {
                "id": "SGR-P2-001",
                "title": "Config manquante pour SYNC-REPO",
                "severity": "P2",
                "source": "SYNC-REPO",
                "trit": "TritObserve",
                "action": "Creer config.yaml avec les routes",
                "family": "sync",
                "status": "open",
            }
        ],
    }
}


@pytest.fixture
def mock_report(tmp_path):
    p = tmp_path / "GAP_REPORT.yaml"
    p.write_text(yaml.dump(MOCK_REPORT))
    return p


class TestGapParser:
    def test_parse_gap_found(self, mock_report):
        gap = parse_gap(mock_report, "SGR-TEST-001")
        assert gap is not None
        assert gap.source == "TEST-REPO"
        assert gap.severity == "P1"

    def test_parse_gap_not_found(self, mock_report):
        assert parse_gap(mock_report, "SGR-NONEXISTENT") is None

    def test_parse_gap_closed(self, mock_report):
        gap = parse_gap(mock_report, "SGR-CLOSED-001")
        assert gap.status == "closed"

    def test_slugify(self):
        assert _slugify("GATEWAY-MANAGER") == "gateway_manager"
        assert _slugify("KIVA-CLI") == "kiva_cli"

    def test_infer_check_type_scanner(self):
        gap = GapMeta("SGR-001", "Scanner ARGUS manquant", "P1",
                      "TEST-REPO", "TritObserve", "Creer scanner ARGUS")
        ct, hints = infer_check_type(gap)
        assert ct == "file_exists"

    def test_infer_check_type_config(self):
        gap = GapMeta("SGR-001", "Config manquante", "P2",
                      "TEST-REPO", "TritObserver", "Creer config.yaml")
        ct, hints = infer_check_type(gap)
        assert ct == "composite"

    def test_infer_check_type_default(self):
        gap = GapMeta("SGR-001", "Gap quelconque", "P3",
                      "TEST-REPO", "TritObserver", "Faire quelque chose")
        ct, hints = infer_check_type(gap)
        assert ct == "file_exists"


class TestScannerTemplate:
    def test_generate_scanner_yaml_basic(self, tmp_path):
        gap = GapMeta("SGR-001", "Scanner manquant", "P1",
                      "TEST-REPO", "TritObserve", "Creer scanner", "monitoring")
        out = tmp_path / "test_health.yaml"
        content = generate_scanner_yaml(gap, out)
        assert out.exists()
        assert "scanner_id: test_repo_health" in content
        assert "SGR-001" in content

    def test_generate_includes_monitoring_check(self, tmp_path):
        gap = GapMeta("SGR-001", "Rapport perime", "P2",
                      "TEST-REPO", "TritObserve", "Relancer", "monitoring")
        out = tmp_path / "test_health.yaml"
        content = generate_scanner_yaml(gap, out)
        assert "file_age" in content

    def test_generate_without_monitoring(self, tmp_path):
        gap = GapMeta("SGR-001", "Scanner manquant", "P2",
                      "TEST-REPO", "TritObserve", "Creer", "governance")
        out = tmp_path / "test_health.yaml"
        content = generate_scanner_yaml(gap, out)
        assert "file_age" not in content

    def test_generate_from_gap_id(self, mock_report, tmp_path):
        out_path, content = generate_from_gap_id("SGR-TEST-001", mock_report, tmp_path)
        assert out_path.exists()
        assert "test_repo_health" in content

    def test_generate_from_gap_id_not_found(self, mock_report, tmp_path):
        with pytest.raises(ValueError, match="introuvable"):
            generate_from_gap_id("SGR-NONEXISTENT", mock_report, tmp_path)


class TestCLIIntegration:
    def test_list_gaps(self, mock_report, capsys):
        from kiva_cli.commands.scaffold_scanner import cmd_scaffold_scanner
        import argparse
        ns = argparse.Namespace(
            list_gaps=True, all_p1=False, gap_id=None,
            from_report=str(mock_report), output_dir=None
        )
        rc = cmd_scaffold_scanner(ns)
        assert rc == 0
        captured = capsys.readouterr()
        assert "SGR-TEST-001" in captured.out
        assert "SGR-CLOSED-001" in captured.out

    def test_all_p1_skips_closed(self, mock_report, tmp_path, capsys):
        from kiva_cli.commands.scaffold_scanner import cmd_scaffold_scanner
        import argparse
        ns = argparse.Namespace(
            list_gaps=False, all_p1=True, gap_id=None,
            from_report=str(mock_report), output_dir=str(tmp_path)
        )
        rc = cmd_scaffold_scanner(ns)
        assert rc == 0
        # Only SGR-TEST-001 should be created (SGR-CLOSED-001 is closed)
        created = list(tmp_path.glob("*.yaml"))
        assert len(created) == 1

    def test_gap_id_mode(self, mock_report, tmp_path, capsys):
        from kiva_cli.commands.scaffold_scanner import cmd_scaffold_scanner
        import argparse
        ns = argparse.Namespace(
            list_gaps=False, all_p1=False, gap_id="SGR-TEST-001",
            from_report=str(mock_report), output_dir=str(tmp_path)
        )
        rc = cmd_scaffold_scanner(ns)
        assert rc == 0
        created = list(tmp_path.glob("*.yaml"))
        assert len(created) == 1
