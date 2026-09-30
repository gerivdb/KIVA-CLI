"""Tests pour KIVA-CLI narrative_generator."""

from src.narrative_generator import Narrative, NarrativeGenerator, build_narrative_generator


def test_build_narrative_generator() -> None:
    generator = build_narrative_generator()
    assert isinstance(generator, NarrativeGenerator)


def test_narrative_generator_generate() -> None:
    generator = build_narrative_generator()
    narrative = generator.generate("cycle-1", {"title": "Test", "content": "Hello"})
    assert narrative.cycle_id == "cycle-1"
    assert narrative.title == "Test"
    assert narrative.content == "Hello"


def test_narrative_generator_defaults() -> None:
    generator = build_narrative_generator()
    narrative = generator.generate("cycle-1", {})
    assert narrative.title == "Cycle cycle-1"
    assert narrative.content == ""
    assert narrative.metadata == {}
