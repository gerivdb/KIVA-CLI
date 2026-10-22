#!/usr/bin/env python3
"""Contrat fail-closed de la porte CI/merge de KIVA-CLI.

Objet
-----
`kiva cicd run` doit exprimer l'echec du pipeline local dans son CODE DE
SORTIE. C'est la condition pour que la porte de merge (`kiva merge pr`, qui
teste `rc != 0`) bloque une PR dont le CI local a echoue.

Defaut corrige (ADR-2026-10-22-002, IntentHash 0xKIVA_CICD_FAIL_CLOSED_20261022)
-------------------------------------------------------------------------------
Avant le correctif, la commande affichait "CI pipeline failed!" puis rendait
0 : la porte de merge lisait 0, concluait au succes, et fusionnait. Constat de
reference : les PR GOVERNANCE-HUB #385 et #387 ont ete fusionnees alors que le
CI local avait echoue.

Ce module verrouille trois proprietes :

1. le code de sortie de `kiva cicd run` distingue le succes de l'echec ;
2. la cause de l'echec est qualifiee (test / timeout / environnement) et la
   sortie de pytest est conservee pour le diagnostic ;
3. PROPRIETE BOUT-EN-BOUT : un CI en echec **bloque** la porte de merge.

La propriete 3 est la seule qui compte pour la securite : les deux autres
n'en sont que les instrumentation.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kiva_cli.commands.cicd_commands import cicd_cli
from kiva_cli.core.cicd_manager import (
    PIPELINE_TIMEOUT_SECONDS,
    REASON_ENVIRONMENT_ERROR,
    REASON_TEST_FAILURE,
    REASON_TIMEOUT,
    CICDManager,
    CIPipelineResult,
)


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# 1. Classification de l'echec
# ---------------------------------------------------------------------------


class TestFailureClassification:
    """La cause de l'echec doit etre qualifiee, pas confondue."""

    @patch("subprocess.run")
    def test_success_is_ok(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = CICDManager(workflows_dir=str(tmp_path)).run_ci_pipeline_detailed(str(tmp_path))
        assert result.ok is True
        assert result.reason == "ok"
        assert result.blocking is False

    @patch("subprocess.run")
    def test_test_failure_is_distinguished(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="FAILED tests/test_a.py::test_b",
            stderr="",
        )
        result = CICDManager(workflows_dir=str(tmp_path)).run_ci_pipeline_detailed(str(tmp_path))
        assert result.ok is False
        assert result.reason == REASON_TEST_FAILURE
        assert result.returncode == 1
        assert result.blocking is True

    @patch("subprocess.run")
    def test_timeout_is_distinguished(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=7)
        result = CICDManager(workflows_dir=str(tmp_path)).run_ci_pipeline_detailed(str(tmp_path))
        assert result.ok is False
        assert result.reason == REASON_TIMEOUT
        assert str(PIPELINE_TIMEOUT_SECONDS) in result.detail

    @patch("subprocess.run")
    def test_environment_error_is_distinguished(self, mock_run, tmp_path):
        mock_run.side_effect = FileNotFoundError("pytest introuvable")
        result = CICDManager(workflows_dir=str(tmp_path)).run_ci_pipeline_detailed(str(tmp_path))
        assert result.ok is False
        assert result.reason == REASON_ENVIRONMENT_ERROR
        assert "pytest introuvable" in result.detail

    @patch("subprocess.run")
    def test_failure_output_is_preserved_for_diagnosis(self, mock_run, tmp_path):
        """La sortie de pytest ne doit pas etre jetee : elle est le diagnostic."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="line-un\nline-deux\nFAILED tests/test_c.py::test_d",
            stderr="warning: SomethingElse",
        )
        result = CICDManager(workflows_dir=str(tmp_path)).run_ci_pipeline_detailed(str(tmp_path))
        assert "FAILED tests/test_c.py::test_d" in result.tail
        assert "warning: SomethingElse" in result.tail

    @patch("subprocess.run")
    def test_legacy_boolean_api_is_preserved(self, mock_run, tmp_path):
        """`run_ci_pipeline` conserve sa signature booleenne historique."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
        manager = CICDManager(workflows_dir=str(tmp_path))
        assert manager.run_ci_pipeline(str(tmp_path)) is False


# ---------------------------------------------------------------------------
# 2. Code de sortie de la commande
# ---------------------------------------------------------------------------


class TestCommandExitCode:
    """`kiva cicd run` doit sortir en code non nul sur echec."""

    def test_success_exits_zero(self, cli_runner, tmp_path):
        with patch("kiva_cli.commands.cicd_commands.CICDManager") as mock_cls:
            mock_cls.return_value.run_ci_pipeline_detailed.return_value = CIPipelineResult(
                ok=True, reason="ok", returncode=0
            )
            result = cli_runner.invoke(cicd_cli, ["run", str(tmp_path)])
        assert result.exit_code == 0
        assert "CI pipeline passed" in result.output

    @pytest.mark.parametrize(
        "reason,detail",
        [
            (REASON_TEST_FAILURE, "pytest a rendu 1"),
            (REASON_TIMEOUT, "budget depasse"),
            (REASON_ENVIRONMENT_ERROR, "FileNotFoundError"),
        ],
    )
    def test_failure_exits_non_zero(self, cli_runner, tmp_path, reason, detail):
        with patch("kiva_cli.commands.cicd_commands.CICDManager") as mock_cls:
            mock_cls.return_value.run_ci_pipeline_detailed.return_value = CIPipelineResult(
                ok=False, reason=reason, detail=detail, returncode=1
            )
            result = cli_runner.invoke(cicd_cli, ["run", str(tmp_path)])
        assert result.exit_code == 1
        assert "CI pipeline failed" in result.output
        assert reason in result.output


# ---------------------------------------------------------------------------
# 3. Propriete bout-en-bout : la porte de merge bloque
# ---------------------------------------------------------------------------


class TestMergeGateIsFailClosed:
    """Un CI local en echec doit empecher la fusion.

    C'est la propriete de securite du correctif. Elle est verifiee de bout en
    bout : on pilote la commande de merge avec un CI en echec et on exige
    qu'aucune fusion ne soit tentee.
    """

    @staticmethod
    def _invoked(mock_run) -> list[str]:
        """Commandes reellement lancees, sous forme de chaine lisible.

        `str(call([...]))` rend une repr Python (`'pr', 'merge'`) : une
        recherche de sous-chaine dessus ne trouve pas `pr merge` et le test
        passerait vacuellement. On extrait donc les arguments reels.
        """
        out: list[str] = []
        for call in mock_run.call_args_list:
            args = call.args[0] if call.args else []
            if isinstance(args, (list, tuple)):
                out.append(" ".join(str(a) for a in args))
            else:
                out.append(str(args))
        return out

    def test_merge_is_cancelled_when_local_ci_fails(self, tmp_path):
        from kiva_cli.commands.merge_commands import merge_pr

        with patch("kiva_cli.commands.merge_commands._run") as mock_run:
            # STEP 0 (snapshot WAL) et STEP 1 (DAG-3) sont simules en succes ;
            # STEP 2 (CI local) doit renvoyer un code non nul.
            def fake_run(cmd, cwd=None, dry_run=False):
                if cmd[:3] == ["kiva", "cicd", "run"]:
                    return 1
                return 0

            mock_run.side_effect = fake_run

            with patch("kiva_cli.commands.merge_commands._wal_append"), patch(
                "kiva_cli.commands.merge_commands._dag3_validate"
            ) as mock_dag3:
                mock_dag3.return_value = {
                    "status": "approved",
                    "recommendations": [],
                    "phi_cps_impact": 0.0,
                }

                with pytest.raises(SystemExit) as exc:
                    merge_pr.callback(
                        repo="RAGX",
                        pr_number=1,
                        source_branch="feat/x",
                        method="squash",
                        hotfix=False,
                        dry_run=False,
                        skip_dag3=False,
                    )

        # La porte doit avoir sorti en erreur...
        assert exc.value.code not in (0, None)
        # ...et surtout n'avoir JAMAIS tente la fusion.
        invoked = self._invoked(mock_run)
        assert not any("pr merge" in c for c in invoked), (
            "la porte de merge a tente la fusion malgre un CI local en echec : "
            f"{invoked}"
        )

    def test_merge_halts_on_real_cli_exit_code(self, tmp_path):
        """Propriete bout-en-bout la plus forte : le code de sortie REEL de
        la commande `kiva cicd run` doit bloquer la porte de merge.

        Ici la commande n'est pas simulee : on invoque la vraie CLI, avec
        seul `pytest` simule en echec. La porte de merge consomme ensuite le
        code de sortie reellement produit. C'est exactement le chemin qui a
        laisse passer les PR GOVERNANCE-HUB #385 et #387.
        """
        from kiva_cli.commands.cicd_commands import cicd_cli
        from kiva_cli.commands.merge_commands import merge_pr

        def fake_run(cmd, cwd=None, dry_run=False):
            if cmd[:3] == ["kiva", "cicd", "run"]:
                with patch("kiva_cli.core.cicd_manager.subprocess.run") as mock_pytest:
                    mock_pytest.return_value = MagicMock(
                        returncode=1,
                        stdout="FAILED tests/test_x.py::test_y",
                        stderr="",
                    )
                    return CliRunner().invoke(cicd_cli, ["run", str(tmp_path)]).exit_code
            return 0

        with patch("kiva_cli.commands.merge_commands._run") as mock_run:
            mock_run.side_effect = fake_run

            with patch("kiva_cli.commands.merge_commands._wal_append"), patch(
                "kiva_cli.commands.merge_commands._dag3_validate"
            ) as mock_dag3:
                mock_dag3.return_value = {
                    "status": "approved",
                    "recommendations": [],
                    "phi_cps_impact": 0.0,
                }

                with pytest.raises(SystemExit) as exc:
                    merge_pr.callback(
                        repo="RAGX",
                        pr_number=1,
                        source_branch="feat/x",
                        method="squash",
                        hotfix=False,
                        dry_run=False,
                        skip_dag3=False,
                    )

        assert exc.value.code not in (0, None)
        invoked = self._invoked(mock_run)
        assert not any("pr merge" in c for c in invoked), (
            "la porte de merge a fusionne alors que la vraie commande "
            f"`kiva cicd run` avait rendu un echec : {invoked}"
        )

    def test_merge_proceeds_when_local_ci_passes(self, tmp_path):
        """Controle de non-regression : un CI vert doit toujours passer."""
        from kiva_cli.commands.merge_commands import merge_pr

        with patch("kiva_cli.commands.merge_commands._run") as mock_run:
            mock_run.return_value = 0

            with patch("kiva_cli.commands.merge_commands._wal_append"), patch(
                "kiva_cli.commands.merge_commands._dag3_validate"
            ) as mock_dag3:
                mock_dag3.return_value = {
                    "status": "approved",
                    "recommendations": [],
                    "phi_cps_impact": 0.0,
                }

                merge_pr.callback(
                    repo="RAGX",
                    pr_number=1,
                    source_branch="feat/x",
                    method="squash",
                    hotfix=False,
                    dry_run=False,
                    skip_dag3=False,
                )

        invoked = self._invoked(mock_run)
        assert any("pr merge" in c for c in invoked), (
            "la porte de merge n'a pas tente la fusion alors que le CI local reussissait"
        )
