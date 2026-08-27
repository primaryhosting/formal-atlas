"""MSC 2020 subject derivation — pure mappers, conservative (unmapped -> [])."""
from atlas.msc import brockian_msc, mathlib_msc, metamath_msc


# --- metamath_msc: set.mm part/section banner titles ---

def test_metamath_propositional_calculus():
    assert metamath_msc("Propositional calculus") == ["03"]

def test_metamath_predicate_calculus():
    assert metamath_msc("Predicate calculus with equality") == ["03"]

def test_metamath_set_theory_parts():
    assert metamath_msc("ZF (Zermelo-Fraenkel) set theory") == ["03E"]
    assert metamath_msc("TG (Tarski-Grothendieck) set theory") == ["03E"]

def test_metamath_real_and_complex_numbers():
    assert metamath_msc("Real and complex numbers") == ["26", "30"]

def test_metamath_number_theory():
    assert metamath_msc("Elementary number theory") == ["11"]

def test_metamath_case_and_whitespace_insensitive():
    # Part banners in set.mm are often ALL CAPS.
    assert metamath_msc("  ELEMENTARY NUMBER THEORY ") == ["11"]

def test_metamath_more_parts():
    assert metamath_msc("Basic order theory") == ["06"]
    assert metamath_msc("Basic algebraic structures") == ["08"]
    assert metamath_msc("Basic topology") == ["54"]
    assert metamath_msc("Basic real and complex analysis") == ["26", "30"]
    assert metamath_msc("Elementary geometry") == ["51"]
    assert metamath_msc("Graph theory") == ["05"]
    assert metamath_msc("Basic category theory") == ["18"]

def test_metamath_unmapped_returns_empty():
    assert metamath_msc("Guides and Miscellanea") == []
    assert metamath_msc("Logical equivalence") == []  # finer section, no confident code
    assert metamath_msc("") == []
    assert metamath_msc(None) == []


# --- mathlib_msc: Mathlib module path, longest-prefix wins ---

def test_mathlib_top_level_prefixes():
    assert mathlib_msc("Mathlib.NumberTheory.ADEInequality") == ["11"]
    assert mathlib_msc("Mathlib.Topology.Basic") == ["54"]
    assert mathlib_msc("Mathlib.MeasureTheory.Measure.Lebesgue") == ["28"]
    assert mathlib_msc("Mathlib.Probability.Martingale.Basic") == ["60"]
    assert mathlib_msc("Mathlib.Combinatorics.SimpleGraph.Basic") == ["05"]
    assert mathlib_msc("Mathlib.Geometry.Euclidean.Angle") == ["51"]
    assert mathlib_msc("Mathlib.CategoryTheory.Functor.Basic") == ["18"]
    assert mathlib_msc("Mathlib.Logic.Basic") == ["03"]
    assert mathlib_msc("Mathlib.SetTheory.Ordinal.Basic") == ["03E"]
    assert mathlib_msc("Mathlib.Order.Lattice") == ["06"]

def test_mathlib_algebra_general_vs_subarea():
    assert mathlib_msc("Mathlib.Algebra.BigOperators.Basic") == ["08"]
    # longest prefix wins over the generic Algebra -> 08 rule
    assert mathlib_msc("Mathlib.Algebra.Group.AddChar") == ["20"]
    assert mathlib_msc("Mathlib.GroupTheory.Sylow") == ["20"]
    assert mathlib_msc("Mathlib.RingTheory.Ideal.Basic") == ["13", "16"]
    assert mathlib_msc("Mathlib.FieldTheory.Galois") == ["12"]
    assert mathlib_msc("Mathlib.LinearAlgebra.Determinant") == ["15"]

def test_mathlib_analysis_subareas():
    assert mathlib_msc("Mathlib.Analysis.Calculus.Deriv.Basic") == ["26"]
    assert mathlib_msc("Mathlib.Analysis.Complex.Basic") == ["30"]
    assert mathlib_msc("Mathlib.Analysis.SpecialFunctions.Gamma.Basic") == ["33"]
    assert mathlib_msc("Mathlib.Analysis.Fourier.FourierTransform") == ["42"]
    assert mathlib_msc("Mathlib.Analysis.Convex.Basic") == ["52"]
    # generic Analysis fallback
    assert mathlib_msc("Mathlib.Analysis.Asymptotics.Asymptotics") == ["26"]

def test_mathlib_geometry_subareas():
    assert mathlib_msc("Mathlib.Geometry.Manifold.ChartedSpace") == ["53"]
    assert mathlib_msc("Mathlib.AlgebraicGeometry.Scheme") == ["14"]
    assert mathlib_msc("Mathlib.AlgebraicTopology.SimplicialSet") == ["55"]

def test_mathlib_unmapped_returns_empty():
    assert mathlib_msc("Mathlib.Tactic.Ring") == []
    assert mathlib_msc("Mathlib.Data.List.Basic") == []
    assert mathlib_msc("Mathlib.Init.Order") == []
    assert mathlib_msc("NotMathlib.NumberTheory.Foo") == []
    assert mathlib_msc("") == []
    assert mathlib_msc(None) == []


# --- brockian_msc: Brockian module path ---

def test_brockian_known_modules():
    assert brockian_msc("Brockian.AbundantClosure") == ["11"]
    assert brockian_msc("Brockian.NumberTheory.Primes") == ["11"]

def test_brockian_segment_keywords():
    assert brockian_msc("Brockian.Combinatorics.Foo") == ["05"]
    assert brockian_msc("Brockian.Topology.Bar") == ["54"]

def test_brockian_unmapped_returns_empty():
    assert brockian_msc("Brockian.Mystery.Widget") == []
    assert brockian_msc("") == []
    assert brockian_msc(None) == []
