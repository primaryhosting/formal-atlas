$( set_mm_excerpt.mm - trimmed excerpt of set.mm (Metamath) for parser tests.
   Follows genuine set.mm conventions: chapter headers, $c/$v/$f declarations,
   description comments, ${ ... $} scoping blocks with $e hypotheses. $)

$( Declare the primitive constant symbols for propositional calculus. $)
$c ( $.  $( Left parenthesis $)
$c ) $.  $( Right parenthesis $)
$c -> $. $( Right arrow (read:  "implies") $)
$c -. $. $( Right handle (read:  "not") $)
$c <-> $. $( Double arrow (read:  "if and only if") $)
$c wff $. $( Well-formed formula symbol $)
$c |- $. $( Turnstile (read:  "the following symbol sequence is provable") $)

$( Introduce some variable names we will use to represent well-formed
   formulas. $)
$v ph $.  $( Greek phi $)
$v ps $.  $( Greek psi $)

$(
#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*
  Propositional calculus
#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*
$)

$( Specify some variables that we will use to represent wffs. $)
wph $f wff ph $.
wps $f wff ps $.

$( Axiom _Simp_.  Axiom A1 of [Margaris] p. 49.  One of the 3 axioms of
   propositional calculus. $)
ax-1 $a |- ( ph -> ( ps -> ph ) ) $.

$( Define the biconditional (logical "iff").  Definition of [Margaris]
   p. 49. $)
df-bi $a |- -. ( ( ( ph <-> ps ) -> -. ( ( ph -> ps ) -> -. ( ps -> ph ) ) ) -> -. ( -. ( ( ph -> ps ) -> -. ( ps -> ph ) ) -> ( ph <-> ps ) ) ) $.

$( Principle of identity.  Theorem *2.08 of [WhiteheadRussell] p. 101.
   (Contributed by NM, 29-Dec-1992.) $)
id $p |- ( ph ->
    ph ) $=
  ( wi ax-1 mpd ) AAABZAAACAECD $.

$(
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
  Logical equivalence
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
$)

${
  mpbi.min $e |- ph $.
  mpbi.maj $e |- ( ph <-> ps ) $.
  $( An inference from a biconditional, related to modus ponens.
     (Contributed by NM, 11-May-1999.) $)
  mpbi $p |- ps $=
    ( bi1 ax-mp ) ACABABDEF $.
$}
