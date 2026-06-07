"""GEM registry and selector — literature-driven model resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from mindbrew_v2.models import (
    GemDiscoveryResult,
    GemProfile,
    GemSelectionResult,
    PathwayCandidate,
    ResearchBrief,
    ValidationMode,
)
from mindbrew_v2.tools.gem_model_cache import ensure_model

REGISTRY_PATH = Path(__file__).parent / "gem_registry.yaml"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = PROJECT_ROOT / "data" / "scenarios"


def _resolve_scenario_ref(ref: str) -> str:
    if not ref:
        return ""
    if ref.startswith("data/"):
        return str(PROJECT_ROOT / ref)
    if Path(ref).is_absolute():
        return ref
    return str(SCENARIOS_DIR / ref)


@dataclass
class GemEntry:
    id: str
    model_ref: str | None
    model_name: str
    organism_aliases: list[str]
    product_classes: list[str]
    feedstock_classes: list[str]
    scenarios: dict
    biomass_validation_scenario: str
    validation_paper_doi: str
    priority: int
    enabled: bool


def load_registry() -> list[GemEntry]:
    with REGISTRY_PATH.open() as f:
        data = yaml.safe_load(f)
    entries = []
    for g in data.get("gems", []):
        if not g.get("enabled", True):
            continue
        if g.get("id") == "auto":
            continue
        entries.append(
            GemEntry(
                id=g["id"],
                model_ref=g.get("model_ref"),
                model_name=g.get("model_name", g["id"]),
                organism_aliases=[a.lower() for a in g.get("organism_aliases", [])],
                product_classes=[p.lower() for p in g.get("product_classes", [])],
                feedstock_classes=[f.lower() for f in g.get("feedstock_classes", [])],
                scenarios=g.get("scenarios", {}),
                biomass_validation_scenario=g.get("biomass_validation_scenario", ""),
                validation_paper_doi=g.get("validation_paper_doi", ""),
                priority=g.get("priority", 0),
                enabled=g.get("enabled", True),
            )
        )
    return sorted(entries, key=lambda e: -e.priority)


def _normalize(s: str) -> str:
    return s.lower().strip()


def resolve_scenario_path(entry: GemEntry, feedstock_class: str) -> str:
    scenarios = entry.scenarios
    default = scenarios.get("default", "")
    by_feed = scenarios.get("by_feedstock", {})
    fc = _normalize(feedstock_class)
    chosen = default
    for key, val in by_feed.items():
        if key.lower() in fc or fc in key.lower():
            chosen = val
            break
    if not chosen:
        return ""
    return _resolve_scenario_ref(chosen)


def resolve_biomass_scenario(entry: GemEntry) -> str:
    name = entry.biomass_validation_scenario
    if not name:
        return ""
    return _resolve_scenario_ref(name)


def _organism_match(brief: ResearchBrief, entry: GemEntry) -> int:
    if not brief.organism:
        return 0
    score = 0
    for org in brief.organism:
        org_l = _normalize(org)
        for alias in entry.organism_aliases:
            if alias in org_l or org_l in alias:
                score = max(score, 2)
    return score


def _class_match(value: str, allowed: list[str]) -> bool:
    if not value:
        return True
    v = _normalize(value)
    return any(a in v or v in a for a in allowed)


def _score_entry(brief: ResearchBrief, entry: GemEntry) -> int:
    if not entry.model_ref:
        return 0
    score = _organism_match(brief, entry)
    target_class = brief.target.compound_class or ""
    feedstock_class = brief.feedstock.compound_class or "plant_oil"
    if target_class and not _class_match(target_class, entry.product_classes):
        if score == 0:
            return 0
        score += 1
    if feedstock_class and not _class_match(feedstock_class, entry.feedstock_classes):
        if score == 0:
            return 0
        score += 1
    if score == 0 and not brief.organism:
        return 0
    return score


def match_registry_entry(
    discovery: GemDiscoveryResult,
    brief: ResearchBrief,
) -> GemEntry | None:
    entries = load_registry()
    model_name_l = _normalize(discovery.model_name)
    if discovery.model_id:
        for entry in entries:
            if entry.id == discovery.model_id:
                return entry
    for entry in entries:
        if model_name_l and model_name_l in _normalize(entry.model_name):
            return entry
        if model_name_l and model_name_l in _normalize(entry.id):
            return entry
    best: GemEntry | None = None
    best_score = 0
    for entry in entries:
        score = _score_entry(brief, entry)
        if score > best_score:
            best_score = score
            best = entry
    return best if best_score > 0 else None


def build_gem_profile(
    entry: GemEntry,
    brief: ResearchBrief,
    *,
    discovery: GemDiscoveryResult | None = None,
    sbml_url: str | None = None,
) -> tuple[GemProfile | None, str]:
    feedstock_class = brief.feedstock.compound_class or "plant_oil"
    cache_path, source, error = ensure_model(
        entry.id,
        entry.model_ref,
        model_name=entry.model_name,
        sbml_url=sbml_url,
        source_doi=(discovery.validation_paper.doi if discovery and discovery.validation_paper else entry.validation_paper_doi),
    )
    if not cache_path:
        return None, error or "Model not available in cache"

    discovery = discovery or GemDiscoveryResult(
        organism=brief.organism[0] if brief.organism else entry.organism_aliases[0],
        model_name=entry.model_name,
        model_id=entry.id,
    )
    return GemProfile(
        gem_id=entry.id,
        model_ref=cache_path,
        model_cache_path=cache_path,
        cache_source=source or "",
        scenario=resolve_scenario_path(entry, feedstock_class),
        biomass_validation_scenario=resolve_biomass_scenario(entry),
        organism=brief.organism[0] if brief.organism else entry.organism_aliases[0],
        feedstock_class=feedstock_class,
        model_name=entry.model_name,
        discovery_rationale=discovery.rationale,
        discovery_confidence=discovery.confidence,
        validation_paper=discovery.validation_paper,
        literature_refs=discovery.literature_refs,
    ), ""


def provisional_validation_mode(brief: ResearchBrief) -> GemSelectionResult:
    """Intake-only hint: FBA possible if registry has a plausible match."""
    entries = load_registry()
    for entry in entries:
        if _score_entry(brief, entry) > 0:
            return GemSelectionResult(
                gem=None,
                validation_mode=ValidationMode.FBA,
                reason="Registry may support FBA — GEM resolved after literature search",
            )
    return GemSelectionResult(
        gem=None,
        validation_mode=ValidationMode.LITERATURE_PATHWAY,
        reason="No registry match — literature pathway validation",
    )


def select_gem(
    brief: ResearchBrief,
    discovery: GemDiscoveryResult,
    override_gem_id: str | None = None,
) -> GemSelectionResult:
    entries = load_registry()
    entry: GemEntry | None = None

    if override_gem_id:
        entry = next((e for e in entries if e.id == override_gem_id), None)
    else:
        entry = match_registry_entry(discovery, brief)

    if entry is None:
        return GemSelectionResult(
            gem=None,
            validation_mode=ValidationMode.LITERATURE_PATHWAY,
            reason=f"No local SBML for {discovery.model_name or 'discovered model'}",
            discovery=discovery,
        )

    gem, error = build_gem_profile(entry, brief, discovery=discovery, sbml_url=discovery.sbml_url)
    if gem is None:
        discovery.sbml_available_locally = False
        return GemSelectionResult(
            gem=None,
            validation_mode=ValidationMode.LITERATURE_PATHWAY,
            reason=error,
            discovery=discovery,
        )

    discovery.sbml_available_locally = True
    discovery.model_id = entry.id
    return GemSelectionResult(
        gem=gem,
        validation_mode=ValidationMode.FBA,
        reason=f"Resolved {entry.model_name} from cache ({gem.cache_source})",
        discovery=discovery,
    )


def registry_entry_by_id(gem_id: str) -> GemEntry | None:
    return next((e for e in load_registry() if e.id == gem_id), None)
