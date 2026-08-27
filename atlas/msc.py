"""MSC 2020 subject derivation — pure, table-driven, conservative.

Three mappers, one per harvested library. All return a list of MSC 2020
top-level codes (two digits; "03E" is the single finer code we use, for set
theory proper). The contract is deliberately conservative: anything not
covered by an explicit table entry maps to [] — we never guess, because an
empty subject_codes is honest and a wrong one is not.

No I/O, no state: these are lookup functions over frozen data tables, safe to
call from any harvester.
"""

# --------------------------------------------------------------------------
# Metamath (set.mm)
#
# set.mm carries no subject metadata; the only structure is the banner
# comments (#*#* Part / =-=- Section) whose titles the metamath harvester
# stores in `module`. We map those titles by normalized phrase match.
# Titles are matched case-insensitively with collapsed whitespace, because
# Part banners are ALL CAPS in the source while harvests may titlecase them.
#
# Phrases are checked in order; first hit wins, so more specific phrases
# (e.g. "real and complex") must precede generic ones. A phrase matches if it
# occurs anywhere in the normalized title — set.mm titles embed qualifiers
# like "ZF (Zermelo-Fraenkel) set theory" that exact matching would miss.
_METAMATH_PHRASES = (
    # logic / foundations
    ("propositional calculus", ["03"]),
    ("predicate calculus", ["03"]),
    ("first-order logic", ["03"]),
    ("set theory", ["03E"]),          # ZF / ZFC / TG parts all say "set theory"
    # numbers and analysis (before generic single-word phrases)
    ("real and complex numbers", ["26", "30"]),
    ("real and complex analysis", ["26", "30"]),
    ("real and complex functions", ["26", "30"]),
    ("number theory", ["11"]),
    ("order theory", ["06"]),
    ("boolean algebras", ["06"]),
    ("algebraic structures", ["08"]),
    ("category theory", ["18"]),
    ("topology", ["54"]),
    ("graph theory", ["05"]),
    ("geometry", ["51"]),
    ("hilbert space", ["46"]),
)


def metamath_msc(section_title):
    """Map a set.mm part/section banner title to MSC codes. Unmapped -> []."""
    if not section_title:
        return []
    title = " ".join(section_title.lower().split())
    for phrase, codes in _METAMATH_PHRASES:
        if phrase in title:
            return list(codes)
    return []


# --------------------------------------------------------------------------
# Mathlib (mathlib4 doc-gen module paths)
#
# Longest dotted-prefix wins, so Mathlib.Algebra.Group -> 20 beats the
# generic Mathlib.Algebra -> 08. Deliberately unmapped top-level prefixes
# (infrastructure, not mathematics-classifiable): Mathlib.Data, .Tactic,
# .Init, .Util, .Lean, .Mathport, .Testing, .Control, .Deprecated.
_MATHLIB_PREFIXES = {
    "Mathlib.Logic": ["03"],
    "Mathlib.ModelTheory": ["03"],
    "Mathlib.Computability": ["03"],
    "Mathlib.SetTheory": ["03E"],
    "Mathlib.Order": ["06"],
    "Mathlib.Algebra": ["08"],
    "Mathlib.Algebra.Group": ["20"],
    "Mathlib.Algebra.Ring": ["13", "16"],
    "Mathlib.Algebra.Field": ["12"],
    "Mathlib.Algebra.Lie": ["17"],
    "Mathlib.Algebra.Homology": ["18"],
    "Mathlib.GroupTheory": ["20"],
    "Mathlib.RingTheory": ["13", "16"],
    "Mathlib.FieldTheory": ["12"],
    "Mathlib.LinearAlgebra": ["15"],
    "Mathlib.RepresentationTheory": ["20"],
    "Mathlib.NumberTheory": ["11"],
    "Mathlib.Analysis": ["26"],
    "Mathlib.Analysis.Complex": ["30"],
    "Mathlib.Analysis.SpecialFunctions": ["33"],
    "Mathlib.Analysis.Fourier": ["42"],
    "Mathlib.Analysis.Convex": ["52"],
    "Mathlib.Analysis.ODE": ["34"],
    "Mathlib.Analysis.Normed": ["46"],
    "Mathlib.Analysis.NormedSpace": ["46"],
    "Mathlib.Analysis.InnerProductSpace": ["46"],
    "Mathlib.Analysis.Distribution": ["46"],
    "Mathlib.MeasureTheory": ["28"],
    "Mathlib.Probability": ["60"],
    "Mathlib.Dynamics": ["37"],
    "Mathlib.Topology": ["54"],
    "Mathlib.Geometry": ["51"],
    "Mathlib.Geometry.Manifold": ["53"],
    "Mathlib.Geometry.RingedSpace": ["14"],
    "Mathlib.AlgebraicGeometry": ["14"],
    "Mathlib.AlgebraicTopology": ["55"],
    "Mathlib.CategoryTheory": ["18"],
    "Mathlib.Combinatorics": ["05"],
    "Mathlib.InformationTheory": ["94"],
    "Mathlib.Condensed": ["18"],
}


def mathlib_msc(module):
    """Map a Mathlib module path to MSC codes by longest prefix. Unmapped -> []."""
    if not module:
        return []
    parts = module.split(".")
    for depth in range(len(parts), 0, -1):
        codes = _MATHLIB_PREFIXES.get(".".join(parts[:depth]))
        if codes is not None:
            return list(codes)
    return []


# --------------------------------------------------------------------------
# Brockian (verified-registry module paths, e.g. Brockian.AbundantClosure)
#
# Two layers, both explicit: known whole-prefix entries for modules whose
# mathematical content we have verified by inspection, then a segment-name
# table for modules that self-describe their area in a path segment
# (Brockian.NumberTheory.*, Brockian.Topology.*, ...). Everything else -> [].
_BROCKIAN_PREFIXES = {
    "Brockian.AbundantClosure": ["11"],   # abundant/perfect-number divisibility
}

_BROCKIAN_SEGMENTS = {
    "NumberTheory": ["11"],
    "Combinatorics": ["05"],
    "Logic": ["03"],
    "SetTheory": ["03E"],
    "Order": ["06"],
    "Algebra": ["08"],
    "GroupTheory": ["20"],
    "RingTheory": ["13", "16"],
    "LinearAlgebra": ["15"],
    "Analysis": ["26"],
    "MeasureTheory": ["28"],
    "Probability": ["60"],
    "Dynamics": ["37"],
    "Topology": ["54"],
    "Geometry": ["51"],
    "CategoryTheory": ["18"],
}


def brockian_msc(module):
    """Map a Brockian registry module to MSC codes. Unmapped -> []."""
    if not module:
        return []
    parts = module.split(".")
    for depth in range(len(parts), 0, -1):
        codes = _BROCKIAN_PREFIXES.get(".".join(parts[:depth]))
        if codes is not None:
            return list(codes)
    for seg in parts:
        codes = _BROCKIAN_SEGMENTS.get(seg)
        if codes is not None:
            return list(codes)
    return []
