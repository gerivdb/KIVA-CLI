import click
import subprocess
from pathlib import Path


@click.group()
def ontology():
    """Commandes pour la gestion des concepts ontologiques."""
    pass


@ontology.command()
@click.argument("concept_id")
@click.option("--ontology-path", default="/path/to/ONTOLOGY", help="Chemin vers le repo ONTOLOGY")
@click.option("--nexus-path", default="/path/to/NEXUS", help="Chemin vers le repo NEXUS")
def pipeline(concept_id, ontology_path, nexus_path):
    """Exécute le pipeline complet pour un concept ontologique."""
    command = [
        "python", "-m", "kiva.pipelines.ontology_pipeline",
        concept_id,
        "--ontology-path", ontology_path,
        "--nexus-path", nexus_path
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Erreur: {result.stderr}")
        raise SystemExit(1)


@ontology.command()
@click.argument("concept_id")
@click.option("--ontology-path", default="/path/to/ONTOLOGY", help="Chemin vers le repo ONTOLOGY")
def validate(concept_id, ontology_path):
    """Valide un concept ontologique."""
    command = (
        f"python -m ONTOLOGY.validators.lifecycle_validator "
        f"--concept {ontology_path}/concepts/{concept_id}.yaml --mode full"
    )
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Erreur: {result.stderr}")
        raise SystemExit(1)


@ontology.command()
@click.option("--ontology-path", default="/path/to/ONTOLOGY", help="Chemin vers le repo ONTOLOGY")
@click.option("--nexus-path", default="/path/to/NEXUS", help="Chemin vers le repo NEXUS")
def index(ontology_path, nexus_path):
    """Indexe tous les concepts dans NEXUS."""
    command = (
        f"python -m scripts.nexus_concept_indexer --mode full "
        f"--ontology-path {ontology_path} --output-dir {nexus_path}"
    )
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Erreur: {result.stderr}")
        raise SystemExit(1)


@ontology.command()
@click.argument("concept_id")
@click.option("--ontology-path", default="/path/to/ONTOLOGY", help="Chemin vers le repo ONTOLOGY")
def sync(concept_id, ontology_path):
    """Synchronise les modifications avec le repo distant."""
    command = (
        f"diff0-fork sync --source {ontology_path} --target gerivdb/ONTOLOGY "
        f"--message 'feat(ontology): add {concept_id} [CONFORME_NEXUS]'"
    )
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Erreur: {result.stderr}")
        raise SystemExit(1)
