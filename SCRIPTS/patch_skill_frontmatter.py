"""
P12 — Batch patch trit_primitive dans les frontmatters skills.
Strategie A : inference par nom de skill.
Usage : python scripts/patch_skill_frontmatter.py --skills-dir <path> [--dry-run]
"""
from __future__ import annotations
import argparse, re
from pathlib import Path

# ── Table d'inférence nom → trit_primitive ───────────────────────
# Les noms correspondent EXACTEMENT aux primitives du TritRegistry.yaml
TRIT_MAP: dict[str, str] = {
    # TritObserve — surveillance, health, scan, check
    "argus": "TritObserve", "monitor": "TritObserve",
    "auditor": "TritCheckConfig", "audit": "TritCheckConfig",
    "reposcope": "TritScanRegistry", "coverage": "TritScanRegistry",
    "probe": "TritCheckPrerequisites", "tracker": "TritObserve",
    "health": "TritCheckPrerequisites", "watch": "TritObserve",

    # TritDiscover — cartographie, recherche, scan
    "map": "TritDiscover", "registry": "TritScanRegistry",
    "wiki": "TritDiscoverArtifact", "deepwiki": "TritDiscoverArtifact",
    "data": "TritScanRegistry", "view": "TritScanRegistry",

    # TritDecompose / TritHierarchize — PRD, structuration
    "reasoning": "TritDecompose", "prd": "TritDecompose",
    "lecun": "TritDecompose", "adr": "TritDocumentRegister",
    "governance": "TritEnforcePolicy", "factory": "TritDecompose",

    # TritValidate / TritCheck — tests, validation, encoding
    "test": "TritRunTests", "validate": "TritValidate",
    "validator": "TritValidateSyntax", "encoding": "TritCheckEncoding",
    "normalizer": "TritCheckEncoding", "check": "TritCheckConsistency",
    "lint": "TritValidateSyntax",

    # TritMerge / TritSync — synchronisation, git
    "syncer": "TritFullSync", "sync": "TritVerseSync",
    "git": "TritDocumentTrace", "workflow": "TritDocumentTrace",
    "lock": "TritResolvePath", "resolver": "TritResolvePath",

    # TritIsolate / TritBuild — construction, scaffolding
    "scaffold": "TritDecompose", "keel": "TritIsolate",
    "peg": "TritIsolate", "pipeline": "TritIsolate",
    "build": "TritIsolate",

    # TritCommunicate — agents, triade, HITL, bus, notify
    "hitl": "TritNotify", "triade": "TritNotify",
    "swarm": "TritNotify", "task": "TritNotify",
    "hub": "TritNotify", "bus": "TritNotify",

    # TritProtect — sécurité, guard, recovery, quarantine
    "security": "TritQuarantine", "guard": "TritEnforcePolicy",
    "hardening": "TritEnforcePolicy", "recovery": "TritRollback",
    "win-unix": "TritResolvePath", "adapter": "TritResolvePath",

    # TritOptimize — perf, hardware, pruning, entropy
    "pruning": "TritEntropyMeasure", "optimizer": "TritEntropyMeasure",
    "boinc": "TritEntropyMeasure", "z600": "TritTernaryStateRust",
    "pulse": "TritEntropyMeasure", "hardware": "TritTernaryStateRust",
    "bench": "TritRunTests",

    # TritExpress — visualisation, diagramme, média, document
    "diagram": "TritDocumentCreate", "iot": "TritDocumentCreate",
    "media": "TritDocumentCreate", "infographic": "TritDocumentCreate",
    "vega": "TritDocumentCreate", "mermaid": "TritDocumentCreate",
    "uml": "TritDocumentCreate", "base243": "TritTernaryStateRust",
    "plix": "TritDocumentClassify",

    # TritAdapt — IDE, config, intent, réforme, deps
    "ide": "TritDiscoverArtifact", "devtools": "TritCheckConfig",
    "github": "TritDocumentRegister", "intent": "TritInferDep",
    "reformer": "TritRollforward", "compliance": "TritEnforcePolicy",
    "bridge": "TritInferDep", "router": "TritResolvePath",
    "slot": "TritHierarchize", "governor": "TritEnforcePolicy",
    "rewriter": "TritDocumentClassify", "skills": "TritDocumentClassify",
    "agentic": "TritDiscoverArtifact", "session": "TritDocumentRegister",
    "closeout": "TritDocumentRegister", "snapshot": "TritPersist",
    "skill": "TritDocumentClassify", "deps": "TritCheckDependencies",
    "kiva": "TritCheckDependencies", "ecos": "TritCheckDependencies",
    "nexus-deps": "TritCheckDependencies",

    # TritObserve — secrets, scan
    "secret": "TritScanSecrets",

    # TritRecommend — qualité, review
    "review": "TritRecommend", "quality": "TritRecommend",

    # TritPersist — sauvegarde, snapshot
    "snapshot": "TritPersist", "persist": "TritPersist",

    # TritTrace — logging, audit trail
    "trace": "TritTrace", "log": "TritLogResolution",

    # TritBalance — weighted decisions
    "balance": "TritBalance",

    # TritCrossRef — cross-references, links
    "crossref": "TritCrossRef", "xref": "TritCrossRef",

    # TritAbduce — root cause, inference
    "abduce": "TritAbduce", "root-cause": "TritAbduce",
    "infer": "TritInferDep",

    # TritBlindSpot — gap detection
    "blindspot": "TritBlindSpot", "gap": "TritBlindSpot",

    # TritMetaGov — governance decisions
    "metagov": "TritMetaGov", "decision": "TritMetaGov",

    # TritPingService — health checks, monitoring
    "ping": "TritPingService", "health-check": "TritPingService",

    # TritSimulateDeploy — deployment simulation
    "deploy": "TritSimulateDeploy", "simulation": "TritSimulateDeploy",

    # TritRollback — rollback, undo
    "rollback": "TritRollback", "undo": "TritRollback",

    # TritRollforward — forward recovery
    "rollforward": "TritRollforward",

    # TritQuarantine — isolation, security
    "quarantine": "TritQuarantine", "isolate": "TritQuarantine",

    # TritSignOperation — signatures, crypto
    "sign": "TritSignOperation", "crypto": "TritSignOperation",

    # TritVectorClockCompare — vector clocks, consistency
    "vector-clock": "TritVectorClockCompare", "consistency": "TritCheckConsistency",

    # TritQuantumResolve — conflict resolution
    "quantum": "TritQuantumResolve", "resolve": "TritResolvePath",

    # TritNotify — notifications, alerts
    "notify": "TritNotify", "alert": "TritNotify",

    # TritDocumentMove — file operations
    "move": "TritDocumentMove", "copy": "TritDocumentMove",

    # TritDocumentPurge — cleanup
    "purge": "TritDocumentPurge", "cleanup": "TritDocumentPurge",

    # TritScanRegistry — registry scanning
    "scan": "TritScanRegistry",

    # TritCheckFrenchGrammar — French grammar
    "french": "TritCheckFrenchGrammar", "grammar": "TritCheckFrenchGrammar",

    # TritTernaryStateRust — ternary state, base243
    "ternary": "TritTernaryStateRust", "base243": "TritTernaryStateRust",

    # TritBinDualWrite — dual write operations
    "dual-write": "BIN_DUAL_WRITE", "dual-read": "BIN_DUAL_READ",

    # TritBinMigrationStatus — migration tracking
    "migration": "BIN_MIGRATION_STATUS",

    # TritBinThermoGate — thermal gate
    "thermo": "BinThermoGate", "thermal": "BinThermoGate",

    # TritBinDecisionGate — decision gate
    "decision-gate": "BIN_DECISION_GATE",

    # TritBinConsistentHash — consistent hashing
    "consistent-hash": "BIN_CONSISTENT_HASH",

    # TritEntropyMeasure — entropy, optimization
    "entropy": "TritEntropyMeasure",

    # TritCompareRegistries — registry comparison
    "compare": "TritCompareRegistries",

    # TritEnforcePolicy — policy enforcement
    "policy": "TritEnforcePolicy", "enforce": "TritEnforcePolicy",

    # TritEnforceRegistration — registration enforcement
    "registration": "TritEnforceRegistration",

    # TritDocumentClassify — document classification
    "classify": "TritDocumentClassify", "classification": "TritDocumentClassify",

    # TritDocumentRegister — document registration
    "register": "TritDocumentRegister",

    # TritDocumentTrace — document tracing
    "document-trace": "TritDocumentTrace",

    # TritInferDep — dependency inference
    "dependency": "TritInferDep", "deps": "TritInferDep",

    # TritResolvePath — path resolution
    "path": "TritResolvePath", "resolve-path": "TritResolvePath",

    # TritRunTests — test execution
    "run-tests": "TritRunTests",

    # TritValidateSyntax — syntax validation
    "syntax": "TritValidateSyntax",

    # TritCheckConfig — configuration checking
    "config": "TritCheckConfig", "check-config": "TritCheckConfig",

    # TritCheckConsistency — consistency checking
    "check-consistency": "TritCheckConsistency",

    # TritCheckDependencies — dependency checking
    "check-deps": "TritCheckDependencies",

    # TritCheckEncoding — encoding checking
    "check-encoding": "TritCheckEncoding",

    # TritCheckFrenchGrammar — French grammar checking
    "check-french": "TritCheckFrenchGrammar",

    # TritCheckPrerequisites — prerequisite checking
    "prerequisites": "TritCheckPrerequisites", "pre-check": "TritCheckPrerequisites",

    # TritScanSecrets — secret scanning
    "scan-secrets": "TritScanSecrets",

    # TritFullSync — full synchronization
    "full-sync": "TritFullSync",

    # TritVerseSync — verse synchronization
    "verse-sync": "TritVerseSync",

    # TritDiamondOrchestrate — diamond orchestration
    "diamond": "TritDiamondOrchestrate", "orchestrate": "TritDiamondOrchestrate",
}

FALLBACK_TRIT = "TritObserve"


def infer_trit(skill_name: str) -> str:
    name_lower = skill_name.lower()
    if name_lower in TRIT_MAP:
        return TRIT_MAP[name_lower]
    for keyword, trit in TRIT_MAP.items():
        if keyword in name_lower:
            return trit
    return FALLBACK_TRIT


def patch_frontmatter(content: str, trit_value: str, force: bool = False) -> tuple:
    # Vérifier si déjà présent
    existing = re.search(r'^trit_primitive:\s*(\S+)', content, re.MULTILINE)
    if existing:
        if not force:
            return content, False
        # Remplacer la valeur existante
        content = re.sub(r'^(trit_primitive:\s*)\S+', f'\\g<1>{trit_value}', content, flags=re.MULTILINE)
        return content, True
    fm_pattern = re.compile(r"^(---\n)(.*?)(---\n)", re.DOTALL)
    match = fm_pattern.match(content)
    if not match:
        new_fm = f"---\ntrit_primitive: {trit_value}\n---\n"
        return new_fm + content, True
    new_fm = match.group(1) + match.group(2) + f"trit_primitive: {trit_value}\n" + match.group(3)
    return new_fm + content[match.end():], True


def run(skills_dir: Path, dry_run: bool, force: bool) -> dict:
    skills = list(skills_dir.glob("*.md"))
    if not skills:
        print(f"ERREUR: Aucun .md dans {skills_dir}")
        return {}

    results = {"patched": [], "skipped": [], "errors": []}
    trit_counts: dict[str, int] = {}

    for skill_file in sorted(skills):
        name = skill_file.stem
        try:
            content = skill_file.read_text(encoding="utf-8")
            trit = infer_trit(name)
            new_content, modified = patch_frontmatter(content, trit, force=args.force)
            if not modified:
                results["skipped"].append(name)
                continue
            if not dry_run:
                skill_file.write_text(new_content, encoding="utf-8")
            results["patched"].append((name, trit))
            trit_counts[trit] = trit_counts.get(trit, 0) + 1
            icon = "[DRY]" if dry_run else "OK  "
            print(f"  {icon} {name:<40} -> {trit}")
        except Exception as e:
            results["errors"].append((name, str(e)))
            print(f"  ERREUR {name} — {e}")

    mode = "[DRY-RUN] " if dry_run else ""
    print(f"\n{mode}=== RESUME ===")
    print(f"  Patches  : {len(results['patched'])}")
    print(f"  Deja OK  : {len(results['skipped'])}")
    print(f"  Erreurs  : {len(results['errors'])}")
    print(f"\n  Distribution trits :")
    for trit, count in sorted(trit_counts.items(), key=lambda x: -x[1]):
        print(f"    {trit:<25} {count:>3} skills")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skills-dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Remplacer les trit_primitive existants")
    args = parser.parse_args()
    run(Path(args.skills_dir), args.dry_run, args.force)
