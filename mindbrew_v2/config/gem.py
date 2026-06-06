"""GEM registry and selector — query-driven model_ref selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from mindbrew_v2.models import GemProfile, GemSelectionResult, ResearchBrief, ValidationMode

REGISTRY_PATH = Path(__file__).parent / "gem_registry.yaml"
VENDOR_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class GemEntry:
    id: str
    model_ref: str | None
    organism_aliases: list[str]
    product_classes: list[str]
    feedstock_classes: list[str]
    scenarios: dict
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
                organism_aliases=[a.lower() for a in g.get("organism_aliases", [])],
                product_classes=[p.lower() for p in g.get("product_classes", [])],
                feedstock_classes=[f.lower() for f in g.get("feedstock_classes", [])],
                scenarios=g.get("scenarios", {}),
                priority=g.get("priority", 0),
                enabled=g.get("enabled", True),
            )
        )
    return sorted(entries, key=lambda e: -e.priority)


def _normalize(s: str) -> str:
    return s.lower().strip()


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


def resolve_scenario(entry: GemEntry, feedstock_class: str) -> str:
    scenarios = entry.scenarios
    default = scenarios.get("default", "")
    by_feed = scenarios.get("by_feedstock", {})
    fc = _normalize(feedstock_class)
    for key, val in by_feed.items():
        if key.lower() in fc or fc in key.lower():
            if not val.startswith("vendor/"):
                return str(VENDOR_ROOT / "vendor/FBA_Analysis/scenarios" / val)
            return str(VENDOR_ROOT / val.replace("vendor/", "vendor/"))
    if default.startswith("vendor/"):
        return str(VENDOR_ROOT / default.replace("vendor/", "vendor/"))
    return default


def select_gem(brief: ResearchBrief, override_gem_id: str | None = None) -> GemSelectionResult:
    entries = load_registry()
    if override_gem_id:
        for e in entries:
            if e.id == override_gem_id and e.model_ref:
                fc = brief.feedstock.compound_class or "plant_oil"
                return GemSelectionResult(
                    gem=GemProfile(
                        gem_id=e.id,
                        model_ref=e.model_ref,
                        scenario=resolve_scenario(e, fc),
                        organism=brief.organism[0] if brief.organism else "",
                        feedstock_class=fc,
                    ),
                    validation_mode=ValidationMode.FBA,
                    reason=f"Human override: {override_gem_id}",
                )

    feedstock_class = brief.feedstock.compound_class or "plant_oil"
    target_class = brief.target.compound_class or ""

    best: GemEntry | None = None
    best_score = 0

    for entry in entries:
        if not entry.model_ref:
            continue
        score = _organism_match(brief, entry)
        if target_class and not _class_match(target_class, entry.product_classes):
            if score == 0:
                continue
            score += 1
        if feedstock_class and not _class_match(feedstock_class, entry.feedstock_classes):
            if score == 0:
                continue
            score += 1
        if score > best_score:
            best_score = score
            best = entry

    if best is None or best_score == 0:
        inferred = _infer_default_gem(brief, entries)
        if inferred:
            best = inferred
            best_score = 1

    if best is None or not best.model_ref:
        return GemSelectionResult(
            gem=None,
            validation_mode=ValidationMode.LITERATURE_PATHWAY,
            reason="No GEM matches organism/feedstock/product classes in registry",
        )

    model_path = best.model_ref
    if not Path(model_path).is_absolute():
        model_path = str(VENDOR_ROOT / model_path.replace("vendor/FBA_Analysis/", "").replace("vendor/", ""))

    return GemSelectionResult(
        gem=GemProfile(
            gem_id=best.id,
            model_ref=model_path,
            scenario=resolve_scenario(best, feedstock_class),
            organism=brief.organism[0] if brief.organism else best.organism_aliases[0],
            feedstock_class=feedstock_class,
        ),
        validation_mode=ValidationMode.FBA,
        reason=f"Matched {best.id} (score={best_score})",
    )


def _infer_default_gem(brief: ResearchBrief, entries: list[GemEntry]) -> GemEntry | None:
    """Infer Y. lipolytica + plant oil for lipid/wax tickets when organism omitted."""
    text = _normalize(brief.raw_brief + " " + brief.target_function)
    lipid_signals = any(
        k in text
        for k in (
            "plant oil",
            "wax",
            "lipid",
            "silicone",
            "dimethicone",
            "cuticle",
            "ceramide",
            "emollient",
        )
    )
    microbiome_signals = any(k in text for k in ("microbiome", "dandruff", "scalp", "postbiotic"))
    if microbiome_signals:
        return None
    if lipid_signals:
        for e in entries:
            if e.id == "iyli647":
                return e
    return None
