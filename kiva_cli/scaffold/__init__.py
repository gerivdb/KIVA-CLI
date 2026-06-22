"""
ARGUS Scaffold module - generate declarative scanners from SGR gap reports.
"""
from .gap_parser import parse_gap, find_latest_report, GapMeta, infer_check_type
from .scanner_template import generate_scanner_yaml, generate_from_gap_id

__all__ = [
    "parse_gap", "find_latest_report", "GapMeta", "infer_check_type",
    "generate_scanner_yaml", "generate_from_gap_id",
]
