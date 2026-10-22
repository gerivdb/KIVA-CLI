#!/usr/bin/env python3
"""
CI/CD Integration Manager - KIVA CLI

Manages CI/CD pipelines, GitHub Actions workflows, and self-hosted runners.
Automates testing, building, and deployment for ECOS repositories.
"""

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

# IntentHash: 0xKIVA_CICD_FAIL_CLOSED_20261022
# ADR: ADR-2026-10-22-002 (gerivdb/GOVERNANCE-HUB/ADR/)
#
# La commande `kiva cicd run` doit exprimer l'echec du pipeline dans son CODE
# DE SORTIE. Sans cela, la porte de merge (`kiva merge pr`, qui teste
# `rc != 0`) ne peut pas distinguer un CI vert d'un CI rouge : la porte est
# fail-open, et une PR peut etre fusionnee sur un CI en echec.
#
# Constat de reference (couloir C1, 2026-10-22) : les PR GOVERNANCE-HUB #385
# et #387 ont ete fusionnees alors que le CI local avait echoue, la commande
# ayant renvoye 0 malgre l'echec.

PIPELINE_TIMEOUT_SECONDS = 300
PIPELINE_OUTPUT_TAIL_LINES = 40

#: Raisons discriminables d'echec du pipeline CI local.
REASON_OK = "ok"
REASON_TEST_FAILURE = "test_failure"
REASON_TIMEOUT = "timeout"
REASON_ENVIRONMENT_ERROR = "environment_error"


@dataclass
class CIPipelineResult:
    """Resultat structure d'une execution du pipeline CI local.

    `ok` est la seule truthiness qui decide du code de sortie de la commande.
    `reason` distingue un echec de TEST d'un echec d'ENVIRONNEMENT : les deux
    sont bloquants, mais ils n'appellent pas la meme remediation, et les
    confondre rend la porte de merge inexploitable en diagnostic.
    """

    ok: bool
    reason: str
    detail: str = ""
    returncode: Optional[int] = None
    tail: List[str] = field(default_factory=list)

    @property
    def blocking(self) -> bool:
        """Un echec est bloquant quel que soit sa cause."""
        return not self.ok


class CICDManager:
    """Manages CI/CD integration for ECOS repositories."""

    def __init__(self, workflows_dir: Optional[str] = None):
        if workflows_dir is None:
            workflows_dir = "D:\\DO\\WEB\\TOOLS\\KIVA-CLI\\.github\\workflows"
        self.workflows_dir = Path(workflows_dir)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

    def setup_github_actions(self, repo_path: str, pipeline_name: str = "ecos-ci") -> bool:
        workflow_file = self.workflows_dir / f"{pipeline_name}.yml"
        workflow_content = f"""name: {pipeline_name}
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
jobs:
  test:
    runs-on: self-hosted
    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Run tests
      run: pytest tests/ -v
"""
        try:
            with open(workflow_file, 'w', encoding='utf-8') as f:
                f.write(workflow_content)
            return True
        except IOError:
            return False

    def run_ci_pipeline_detailed(self, repo_path: str) -> CIPipelineResult:
        """Execute le pipeline CI local et qualifie l'echec le cas echeant.

        Discrimine trois causes d'echec, au lieu de les confondre dans un
        `except Exception: return False` muet :

        - `test_failure`      : pytest s'est execute et a rendu un code != 0 ;
        - `timeout`           : pytest n'a pas rendu dans le budget ;
        - `environment_error` : pytest n'a pas pu etre lance du tout.

        La sortie du pipeline (pytest) est conservee : elle est portee dans
        `tail`, parce que la diagnostiquer est la seule facon de distinguer un
        echec de code d'une derive d'environnement.
        """
        print(f"Running CI pipeline in {repo_path}...")
        try:
            result = subprocess.run(
                ["pytest", "tests/", "-v"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=PIPELINE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return CIPipelineResult(
                ok=False,
                reason=REASON_TIMEOUT,
                detail=(
                    f"le pipeline CI n'a pas rendu dans le budget de "
                    f"{PIPELINE_TIMEOUT_SECONDS}s"
                ),
            )
        except Exception as exc:
            return CIPipelineResult(
                ok=False,
                reason=REASON_ENVIRONMENT_ERROR,
                detail=f"{type(exc).__name__}: {exc}",
            )

        if result.returncode == 0:
            return CIPipelineResult(
                ok=True,
                reason=REASON_OK,
                detail="pytest a rendu 0",
                returncode=0,
            )

        tail = self._tail_of(result.stdout, result.stderr)
        return CIPipelineResult(
            ok=False,
            reason=REASON_TEST_FAILURE,
            detail=f"pytest a rendu {result.returncode}",
            returncode=result.returncode,
            tail=tail,
        )

    @staticmethod
    def _tail_of(stdout: Optional[str], stderr: Optional[str], lines: int = PIPELINE_OUTPUT_TAIL_LINES) -> List[str]:
        """Dernieres lignes utiles de la sortie du pipeline (stdout puis stderr)."""
        combined = [ln for ln in (stdout or "").splitlines() if ln.strip()]
        combined += [ln for ln in (stderr or "").splitlines() if ln.strip()]
        return combined[-lines:]

    def run_ci_pipeline(self, repo_path: str) -> bool:
        """Execute le pipeline CI local.

        Conserve pour compatibilite la signature booleenne historique.
        La commande CLI utilise `run_ci_pipeline_detailed` pour qualifier
        l'echec et produire un code de sortie non nul.
        """
        return self.run_ci_pipeline_detailed(repo_path).ok

    def get_pipeline_status(self, repo_path: str) -> Dict[str, Any]:
        workflows = list(self.workflows_dir.glob("*.yml"))
        return {
            "workflows": [w.name for w in workflows],
            "workflows_count": len(workflows),
            "repo_path": repo_path
        }

    def get_pipeline_status(self, repo_path: str) -> Dict[str, Any]:
        workflows = list(self.workflows_dir.glob("*.yml"))
        return {
            "workflows": [w.name for w in workflows],
            "workflows_count": len(workflows),
            "repo_path": repo_path
        }