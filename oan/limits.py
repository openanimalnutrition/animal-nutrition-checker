"""The limits of one request: each nutrient's minimum, maximum and range high, and the type of
its range high.

Written from the formulas specification (ig-build impl/formulas/spec.md, sections 3-6 and 9),
the values specification (ai1/spec-values.md, sections 4 and 7) and the IG's band
computation page ("Caloric restriction", "The AAFCO dry matter factor", "Limits the
template sets or computes", "Maximum types"), in nutrition terms. The standards' limits come
from oan/table.py; the template's own figures and its four extra rows from data/template.csv
by their ids (FIGURES and ROWS below). The shape of each rule is here.

A limit is a number, None (the template's "none": no limit) or Unavailable, with a reason:
no requirement is chosen ("requirement-needed"), or the energy an MBW conversion needs is
not known (oan/energy.py REASONS). The code never produces the template's error codes.

The animal facts are the ones oan/inputs.py accepts, by input name; None means not entered.
The entries are {nutrient id: {"low": number or None, "high": number or None}}; only the low
entries have side effects (the protein low raises the arginine minimum, the energy density
low sets the AAFCO dry matter factor).
"""

from collections import namedtuple

from . import energy, table

# The figures of data/template.csv: id -> the unit the code reads it in ("" for a plain
# number: a share, a ratio or a factor).
FIGURES = {
    "vitamin-d2-per-vitamin-d": "",
    "arginine-per-protein-dog": "g/g",
    "arginine-per-protein-cat": "g/g",
    "la-ala-ratio-low": "",
    "la-ala-ratio-high-growth-reproduction": "",
    "la-ala-ratio-high-adult": "",
    "epa-share-max": "",
    "epa-share-range-low": "",
    "epa-share-range-high": "",
    "epa-share-max-dha-only": "",
    "large-breed-puppy-calcium-min": "g/Mcal",
    "large-breed-puppy-calcium-per-kg-body-weight": "g/kg BW",
    "large-breed-puppy-calcium-max": "g/Mcal",
    "large-breed-puppy-calcium-max-over-min": "",
    "aafco-energy-density": "kcal/g DM",
    "carbohydrate-max-protein-energy": "kcal/g",
    "carbohydrate-max-fat-energy": "kcal/g",
    "carbohydrate-max-carbohydrate-energy": "kcal/g",
    "la-aa-to-ala-epa-dha-ratio-max-default": "",
    "la-aa-to-epa-dha-ratio-max-default": "",
    "vitamin-c-min-default": "mg/Mcal",
    "carbohydrate-min-default": "g/Mcal",
    "fiber-total-min-default": "g/Mcal",
    "fiber-insoluble-min-default": "g/Mcal",
    "fiber-soluble-min-default": "g/Mcal",
    "water-max": "g/Mcal",
    "energy-density-min": "kcal/g DM",
    "energy-density-max": "kcal/g DM",
    "oxalate-min": "mg/Mcal",
    "purine-min": "mg/Mcal",
    "mct-max": "g/Mcal",
    "taurine-max-default": "g/Mcal",
}
# Figures that are a maximum themselves carry its type in data/template.csv.
MAXIMUM_FIGURES = (
    "large-breed-puppy-calcium-max",
    "large-breed-puppy-calcium-max-over-min",
    "la-aa-to-ala-epa-dha-ratio-max-default",
    "la-aa-to-epa-dha-ratio-max-default",
    "water-max",
    "energy-density-max",
    "mct-max",
    "taurine-max-default",
)
# The template's extra rows (data/template.csv): EPA alone (entered only for the EPA share
# checks, not banded), vitamin D2 for cats (per Mcal and MBW) and the calcium of NRC puppies
# 4-14 weeks old of a large expected size.
ROWS = ("epa", "vitamin-d2", "vitamin-d2-mbw", "calcium-large-breed-puppy")
NOT_BANDED = ("epa",)

REQUIREMENT_NEEDED = "requirement-needed"
NEEDS_MINIMUMS = "calculation-needs-a-missing-minimum"
NEEDS_NUMBER = "rule-needs-a-number"

# Minimums the template sets or keeps whatever the request (no lookup): None is "none".
FIXED_MINIMUMS = {
    "water": None,
    "oxalate": "oxalate-min",
    "purine": "purine-min",
    "energy-density": "energy-density-min",
}
FIXED_MAXIMUMS = {
    "water": "water-max",
    "oxalate": None,
    "purine": None,
    "energy-density": "energy-density-max",
    "mct": "mct-max",
    "mct-mbw": "mct-max",
}
# Minimums used as the standard prints them, or the template's default when it prints none.
DEFAULT_MINIMUMS = {
    "vitamin-c": "vitamin-c-min-default",
    "carbohydrate": "carbohydrate-min-default",
    "fiber-total": "fiber-total-min-default",
    "fiber-insoluble": "fiber-insoluble-min-default",
    "fiber-soluble": "fiber-soluble-min-default",
}
# Per-Mcal minimums neither a caloric restriction nor the AAFCO factor raises (besides the
# fixed and default ones above); fat takes the AAFCO factor only.
NOT_RAISED = ("ca-p-ratio",)
AAFCO_FACTOR_ONLY = ("fat",)
TAURINE = "taurine"
TAURINE_ROWS = ("taurine", "taurine-wet", "taurine-mbw", "taurine-wet-mbw")
LA_ALA_HIGH = ("la-ala-ratio-high-growth-reproduction", "la-ala-ratio-high-adult")
ARGININE_PER_PROTEIN = ("arginine-per-protein-dog", "arginine-per-protein-cat")

# The type of a range high (IG, "Maximum types"): the template's codes for the maximums it
# takes from a standard, TPL for one the template sets or computes, K for none (the range
# high is the minimum times K).
COMPUTED = "TPL"
NO_MAXIMUM = "K"
PROVENANCE = {
    "SUL": "authoritative",
    "SUL>": "authoritative",
    "SULm": "authoritative",
    "SULm>": "authoritative",
    "PSM": "authoritative",
    "AAFCO": "authoritative",
    "N": "authoritative",
    "N*": "conditional",
    "SULm*": "conditional",
    "L": "conditional",
    "FSL": "conditional",
    "EST": "template-set",
    "CALC": "template-set",
    COMPUTED: "template-set",
    NO_MAXIMUM: "derived-provisional",
}


class Unavailable:
    """A limit that cannot be computed, and why."""

    __slots__ = ("reason",)

    def __init__(self, reason):
        self.reason = reason

    def __eq__(self, other):
        return isinstance(other, Unavailable) and other.reason == self.reason

    def __hash__(self):
        return hash(self.reason)

    def __repr__(self):
        return "Unavailable(%r)" % self.reason


def unavailable(x):
    return isinstance(x, Unavailable)


def number(x):
    return type(x) is float


def _n(x):
    """The template's N(): a number is itself, "none" counts as 0, Unavailable stays."""
    return 0.0 if x is None else x


# One nutrient's limits. range_high and max_code are None when unavailable; max_code is the
# type of the range high (a template code, TPL or K).
Limits = namedtuple("Limits", "minimum maximum range_high max_code")


def provenance(code, aafco_factor):
    """The IG's maxProvenance of a range high's type for this request: AAFCO's maximums are
    conditional while the AAFCO dry matter factor is above 1."""
    if code is None:
        return None
    if code == "AAFCO" and number(aafco_factor) and aafco_factor > 1:
        return "conditional"
    return PROVENANCE[code]


def mbw_exponent(species):
    """The metabolic body weight exponent of the MBW rows' basis (kg BW^0.75 or BW^0.67)."""
    return float(table.MBW_BASIS[species].split("^")[1])


def applies(row, requirement):
    """Whether a template.csv row applies to a requirement (a requirements.csv row, or None
    when none is chosen): "*", a species, or requirement ids."""
    tokens = row["applies_to"].split()
    if "*" in tokens:
        return True
    if requirement is None:
        return False
    return requirement["id"] in tokens or requirement["species"] in tokens


class Request:
    """Every limit of one request, computed on demand and kept.

    requirement_id: a requirements.csv id, or None when none is chosen (then every limit the
    template looks up is Unavailable, and only its fixed limits are numbers)."""

    def __init__(self, data, requirement_id, facts, entries):
        self.data = data
        self.facts = facts
        self.entries = entries
        self.template = data["template"]
        self.nutrients = {n["id"]: n for n in data["nutrients"]}
        self.requirement = None
        self.standard = None
        if requirement_id is not None:
            self.requirement = next(r for r in data["requirements"] if r["id"] == requirement_id)
            self.standard = table.compute_limits(data, requirement_id,
                                                 facts.get("mature_weight_kg"))
            self.energy_requirement = energy.requirement_energy(data, requirement_id, facts)
            self.energy = energy.energy_used(self.energy_requirement,
                                             facts.get("energy_intake_kcal_per_day"))
        else:
            self.energy_requirement = self.energy = energy.Energy(None, REQUIREMENT_NEEDED)
        restriction = facts.get("caloric_restriction_percent")
        self.restricted = restriction is not None and restriction > 0
        # The restriction factor, computed first (IG, "Caloric restriction").
        self.restriction_factor = 1 / (1 - (restriction / 100)) if self.restricted else 1.0
        self.aafco_factor = self._aafco_factor()
        self._min, self._max = {}, {}

    # Figures and lookups.

    def figure(self, fid):
        return float(self.template[fid]["figure"])

    def applies(self, fid):
        return applies(self.template[fid], self.requirement)

    def low(self, nid):
        return self.entries.get(nid, {}).get("low")

    def std(self, nid, bound):
        """The standard's limit (oan/table.py), or Unavailable when no requirement is chosen."""
        if self.standard is None:
            return Unavailable(REQUIREMENT_NEEDED)
        return self.standard[nid][0 if bound == "min" else 1]

    def std_code(self, nid):
        return self.data["limits"][self.requirement["id"]][nid]["max_type"] or None

    def _aafco_factor(self):
        """4 / the energy density entered as low, under the AAFCO requirements, when that is
        above 0 and below 4; else 1 (spec section 4)."""
        if self.requirement is None:
            return Unavailable(REQUIREMENT_NEEDED)
        density = self.low("energy-density")
        presumed = self.figure("aafco-energy-density")
        if self.applies("aafco-energy-density") and density is not None and \
                0 < density < presumed:
            return presumed / density
        return 1.0

    @property
    def mbw_factor(self):
        """((BW^n / the energy used) x 1000): converts a limit per kg BW^n to per Mcal."""
        if self.requirement is None:
            return Unavailable(REQUIREMENT_NEEDED)
        if self.energy.kcal is None:
            return Unavailable(self.energy.reason)
        bw = self.facts.get("body_weight_kg")
        if bw is None:
            return Unavailable("body-weight-needed")
        return (bw ** mbw_exponent(self.requirement["species"]) / self.energy.kcal) * 1000

    def mbw(self, v):
        """A limit per kg BW^n per day converted to per Mcal; "none" stays none."""
        if v is None or unavailable(v):
            return v
        m = self.mbw_factor
        return m if unavailable(m) else v * m

    def raised(self, v, by_restriction=True):
        """A standard's per-Mcal minimum raised by the AAFCO factor and, unless told
        otherwise, the restriction factor: (a x f) x the minimum (spec sections 5.1, 5.2)."""
        if unavailable(v):
            return v
        f = self.restriction_factor if by_restriction else 1.0
        a = self.aafco_factor
        if ((by_restriction and self.restricted) or a != 1) and number(v):
            return (a * f) * v
        return v

    @property
    def intake_shortfall(self):
        """The share an entered intake is below the requirement's energy, or None
        (information only: no limit uses it; the template's N4)."""
        need = self.energy_requirement.kcal
        intake = self.facts.get("energy_intake_kcal_per_day")
        if need is None or intake is None or not (need > 0 and intake > 0 and intake < need):
            return None
        return (need - intake) / need

    # Minimums.

    def minimum(self, nid):
        if nid not in self._min:
            self._min[nid] = self._minimum(nid)
        return self._min[nid]

    def _minimum(self, nid):
        if nid in FIXED_MINIMUMS:
            fid = FIXED_MINIMUMS[nid]
            return None if fid is None else self.figure(fid)
        rule = MINIMUM_RULES.get(nid)
        if rule is not None:
            return rule(self)
        nutrient = self.nutrients[nid]
        v = self.std(nid, "min")
        if nutrient["basis"] == "per-mbw":
            return self.mbw(v)
        if nid in DEFAULT_MINIMUMS:
            return self.figure(DEFAULT_MINIMUMS[nid]) if v is None else v
        if nid in NOT_RAISED or nutrient["basis"] != "per-mcal":
            return v
        return self.raised(v, by_restriction=nid not in AAFCO_FACTOR_ONLY)

    def arginine_base(self, nid):
        """The arginine minimum before the protein increase (the template's AS1 and AS2)."""
        if nid == "arginine":
            return self.raised(self.std(nid, "min"))
        return self.mbw(self.std(nid, "min"))

    def _arginine(self, nid, protein_id):
        """NRC and FEDIAF: the arginine minimum rises by a figure for each g of protein
        entered as low above the protein minimum (spec section 5.3)."""
        base = self.arginine_base(nid)
        fid = next((f for f in ARGININE_PER_PROTEIN if self.applies(f)), None)
        if fid is None:
            return base
        protein_min = self.minimum(protein_id)
        if unavailable(protein_min):
            return protein_min
        protein = _n(self.low(protein_id))
        if number(protein_min) and protein > protein_min:
            if not number(base):
                return base if unavailable(base) else Unavailable(NEEDS_NUMBER)
            return ((protein - protein_min) * self.figure(fid)) + base
        return base

    def _la_ala_high(self):
        return next((f for f in LA_ALA_HIGH if self.applies(f)), None)

    def _ala(self):
        """ALA: the standard's minimum, raised like the others; under the NRC dog
        requirements at least the LA minimum / NRC's highest LA:ALA ratio (spec 5.4)."""
        r = self.raised(self.std("alpha-linolenic-acid", "min"))
        fid = self._la_ala_high()
        la = self.minimum("linoleic-acid")
        if unavailable(la):
            return la
        if fid is not None and _n(la) > 0:
            if not number(r):
                return r if unavailable(r) else Unavailable(NEEDS_NUMBER)
            return max(r, _n(la) / self.figure(fid))
        return r

    def _ala_mbw(self):
        """The ALA MBW minimum: as ALA, from the LA MBW minimum; never raised (spec 5.4a)."""
        x = self.std("alpha-linolenic-acid-mbw", "min")
        la = self.minimum("linoleic-acid-mbw")
        if unavailable(la):
            return la
        fid = self._la_ala_high()
        if fid is not None and _n(la) > 0:
            converted = self.mbw(x)
            if not number(converted):
                return converted if unavailable(converted) else Unavailable(NEEDS_NUMBER)
            return max(converted, _n(la) / self.figure(fid))
        return self.mbw(x)

    def _ratio_min_all(self):
        """LA + AA : ALA + EPA + DHA: the standard's, else (LA + AA minimums) / (ALA + EPA +
        DHA maximums), none when that divisor is 0 (spec 5.7)."""
        v = self.std("la-aa-to-ala-epa-dha-ratio", "min")
        if v is not None:
            return v
        terms = [self.maximum("alpha-linolenic-acid"), self.maximum("epa-dha"),
                 self.minimum("linoleic-acid"), self.minimum("arachidonic-acid")]
        bad = next((t for t in terms if unavailable(t)), None)
        if bad is not None:
            return bad
        divisor = _n(terms[0]) + _n(terms[1])
        if divisor == 0:
            return None
        return (_n(terms[2]) + _n(terms[3])) / divisor

    def _ratio_min_epa_dha(self):
        """LA + AA : EPA + DHA: the standard's, else (LA + AA minimums) / the EPA + DHA
        maximum, none when that is 0."""
        v = self.std("la-aa-to-epa-dha-ratio", "min")
        if v is not None:
            return v
        terms = [self.maximum("epa-dha"), self.minimum("linoleic-acid"),
                 self.minimum("arachidonic-acid")]
        bad = next((t for t in terms if unavailable(t)), None)
        if bad is not None:
            return bad
        if _n(terms[0]) == 0:
            return None
        return (_n(terms[1]) + _n(terms[2])) / _n(terms[0])

    def _large_breed_puppy_calcium(self):
        """The larger of the calcium figure and the body weight term (g per kg BW a day,
        converted with the energy used), each raised by the restriction; the body weight
        term not when an intake is entered (spec 5.5)."""
        if not applies(self.template["calcium-large-breed-puppy"], self.requirement):
            return None
        f = self.restriction_factor
        least = self.figure("large-breed-puppy-calcium-min") * f
        puppy = self.facts.get("puppy_body_weight_kg")
        if puppy is None or not puppy > 0:
            return least
        if self.energy.kcal is None:
            return Unavailable(self.energy.reason)
        g = 1.0 if self.facts.get("energy_intake_kcal_per_day") is not None else f
        term = ((self.figure("large-breed-puppy-calcium-per-kg-body-weight") * puppy) /
                (self.energy.kcal / 1000)) * g
        return max(least, term)

    def _vitamin_d2(self, of):
        """Cats: the vitamin D minimum / the D2 efficiency (spec 5.7); none for dogs."""
        if not applies(self.template["vitamin-d2"], self.requirement):
            return None
        d = self.minimum(of)
        if d is None or unavailable(d):
            return d
        return d / self.figure("vitamin-d2-per-vitamin-d")

    # Maximums: (value, the type of the maximum or None).

    def maximum(self, nid):
        return self.maximum_typed(nid)[0]

    def maximum_typed(self, nid):
        if nid not in self._max:
            self._max[nid] = self._maximum(nid)
        return self._max[nid]

    def _fixed(self, fid):
        return self.figure(fid), self.template[fid]["max_type"]

    def _from_standard(self, v, nid):
        if v is None or unavailable(v):
            return v, None
        return v, self.std_code(nid)

    def _maximum(self, nid):
        if nid in FIXED_MAXIMUMS:
            fid = FIXED_MAXIMUMS[nid]
            return (None, None) if fid is None else self._fixed(fid)
        rule = MAXIMUM_RULES.get(nid)
        if rule is not None:
            return rule(self)
        nutrient = self.nutrients[nid]
        v = self.std(nid, "max")
        if nutrient["basis"] == "per-mbw":
            v = self.mbw(v)
        return self._from_standard(v, nid)

    def _taurine_max(self, nid):
        """0.67 on all four taurine rows when the taurine (per Mcal) minimum is none; else
        each row's own maximum, an MBW row's none when its own minimum is none (spec 6)."""
        general = self.minimum(TAURINE)
        if unavailable(general):
            return general, None
        if general is None:
            return self._fixed("taurine-max-default")
        if self.nutrients[nid]["basis"] == "per-mbw":
            own = self.minimum(nid)
            if own is None or unavailable(own):
                return own, None
            return self._from_standard(self.mbw(self.std(nid, "max")), nid)
        return self._from_standard(self.std(nid, "max"), nid)

    def _ala_max(self, nid, la_id, convert):
        """Under the NRC dog requirements the larger of the standard's ALA maximum (0 when
        none) and the LA maximum / NRC's lowest LA:ALA ratio (spec 6, E47 and E48)."""
        la = self.maximum(la_id)
        if unavailable(la):
            return la, None
        v = self.std(nid, "max")
        if unavailable(v):
            return v, None
        if self.applies("la-ala-ratio-low") and _n(la) > 0:
            own = self.mbw(v if number(v) else 0.0) if convert else (v if number(v) else 0.0)
            if unavailable(own):
                return own, None
            from_la = _n(la) / self.figure("la-ala-ratio-low")
            if number(v) and own >= from_la:
                return own, self.std_code(nid)
            return max(own, from_la), COMPUTED
        return self._from_standard(self.mbw(v) if convert else v, nid)

    def _ratio_max_all(self):
        """LA + AA : ALA + EPA + DHA: the standard's, else (LA + AA maximums) / (ALA + EPA +
        DHA minimums), the template's default when either sum is 0."""
        nid = "la-aa-to-ala-epa-dha-ratio"
        v = self.std(nid, "max")
        if v is not None:
            return self._from_standard(v, nid)
        terms = [self.minimum("alpha-linolenic-acid"), self.minimum("epa-dha"),
                 self.maximum("linoleic-acid"), self.maximum("arachidonic-acid")]
        bad = next((t for t in terms if unavailable(t)), None)
        if bad is not None:
            return bad, None
        n3 = _n(terms[0]) + _n(terms[1])
        n6 = _n(terms[2]) + _n(terms[3])
        if n3 == 0 or n6 == 0:
            return self._fixed("la-aa-to-ala-epa-dha-ratio-max-default")
        return n6 / n3, COMPUTED

    def _ratio_max_epa_dha(self):
        """LA + AA : EPA + DHA: the standard's, else (LA + AA maximums) / the EPA + DHA
        minimum, the template's default when that minimum or the ratio is 0."""
        nid = "la-aa-to-epa-dha-ratio"
        v = self.std(nid, "max")
        if v is not None:
            return self._from_standard(v, nid)
        terms = [self.minimum("epa-dha"), self.maximum("linoleic-acid"),
                 self.maximum("arachidonic-acid")]
        bad = next((t for t in terms if unavailable(t)), None)
        if bad is not None:
            return bad, None
        if _n(terms[0]) == 0:
            return self._fixed("la-aa-to-epa-dha-ratio-max-default")
        ratio = (_n(terms[1]) + _n(terms[2])) / _n(terms[0])
        if ratio == 0:
            return self._fixed("la-aa-to-epa-dha-ratio-max-default")
        return ratio, COMPUTED

    def _ca_p_max(self):
        """Ca:P: the standard's, else the calcium maximum / the phosphorus minimum when both
        are numbers and the minimum is above 0, else none (spec-values section 4.3)."""
        v = self.std("ca-p-ratio", "max")
        if unavailable(v) or number(v):
            return self._from_standard(v, "ca-p-ratio")
        calcium, phosphorus = self.maximum("calcium"), self.minimum("phosphorus")
        if number(calcium) and number(phosphorus):
            return (calcium / phosphorus, COMPUTED) if phosphorus > 0 else (None, None)
        return None, None

    def _carbohydrate_max(self):
        """The standard's, else the larger of 0 and (1000 - (protein minimum x 4 + fat
        minimum x 9)) / 4 (spec 6, E124)."""
        v = self.std("carbohydrate", "max")
        if v is not None:
            return self._from_standard(v, "carbohydrate")
        protein, fat = self.minimum("protein"), self.minimum("fat")
        for t in (protein, fat):
            if unavailable(t):
                return t, None
            if not number(t):
                return Unavailable(NEEDS_MINIMUMS), None
        energy_left = 1000 - ((protein * self.figure("carbohydrate-max-protein-energy")) +
                              (fat * self.figure("carbohydrate-max-fat-energy")))
        return max(0.0, energy_left / self.figure("carbohydrate-max-carbohydrate-energy")), \
            COMPUTED

    def _large_breed_puppy_calcium_max(self):
        """None when the minimum is none; the calcium maximum, or the minimum x 1.1 when the
        minimum is above it (spec 6, E66)."""
        least = self.minimum("calcium-large-breed-puppy")
        if least is None or unavailable(least):
            return least, None
        if least > self.figure("large-breed-puppy-calcium-max"):
            return least * self.figure("large-breed-puppy-calcium-max-over-min"), \
                self.template["large-breed-puppy-calcium-max-over-min"]["max_type"]
        return self._fixed("large-breed-puppy-calcium-max")

    def _vitamin_d2_max(self, of):
        """Cats: the vitamin D maximum, with its type; none for dogs."""
        if not applies(self.template["vitamin-d2"], self.requirement):
            return None, None
        return self.maximum_typed(of)

    # One nutrient.

    def limits(self, nid):
        """The Limits of one nutrient: its minimum, maximum, range high and the type of the
        range high (IG band computation, "Inputs for one nutrient")."""
        low = self.minimum(nid)
        high, code = self.maximum_typed(nid)
        if unavailable(low) or unavailable(high):
            return Limits(low, high, None, None)
        if nid in NOT_BANDED:
            return Limits(low, high, None, None)
        if high is not None:
            return Limits(low, high, high, code)
        k = self.multiplier(nid)
        if k is None:
            raise table.DataError("%s has no maximum and no multiplier K" % nid)
        return Limits(low, high, _n(low) * k, NO_MAXIMUM)

    def multiplier(self, nid):
        """The multiplier K, or None where the template gives none."""
        row = self.nutrients.get(nid) or self.template[nid]
        try:
            return float(row["k"])
        except ValueError:
            return None


MINIMUM_RULES = {
    "arginine": lambda r: r._arginine("arginine", "protein"),
    "arginine-mbw": lambda r: r._arginine("arginine-mbw", "protein-mbw"),
    "alpha-linolenic-acid": Request._ala,
    "alpha-linolenic-acid-mbw": Request._ala_mbw,
    "la-aa-to-ala-epa-dha-ratio": Request._ratio_min_all,
    "la-aa-to-epa-dha-ratio": Request._ratio_min_epa_dha,
    "calcium-large-breed-puppy": Request._large_breed_puppy_calcium,
    "vitamin-d2": lambda r: r._vitamin_d2("vitamin-d"),
    "vitamin-d2-mbw": lambda r: r._vitamin_d2("vitamin-d-mbw"),
    "epa": lambda r: None,
}
MAXIMUM_RULES = {
    "taurine": lambda r: r._taurine_max("taurine"),
    "taurine-wet": lambda r: r._taurine_max("taurine-wet"),
    "taurine-mbw": lambda r: r._taurine_max("taurine-mbw"),
    "taurine-wet-mbw": lambda r: r._taurine_max("taurine-wet-mbw"),
    "alpha-linolenic-acid": lambda r: r._ala_max("alpha-linolenic-acid", "linoleic-acid",
                                                 False),
    "alpha-linolenic-acid-mbw": lambda r: r._ala_max("alpha-linolenic-acid-mbw",
                                                     "linoleic-acid-mbw", True),
    "la-aa-to-ala-epa-dha-ratio": Request._ratio_max_all,
    "la-aa-to-epa-dha-ratio": Request._ratio_max_epa_dha,
    "ca-p-ratio": Request._ca_p_max,
    "carbohydrate": Request._carbohydrate_max,
    "calcium-large-breed-puppy": Request._large_breed_puppy_calcium_max,
    "vitamin-d2": lambda r: r._vitamin_d2_max("vitamin-d"),
    "vitamin-d2-mbw": lambda r: r._vitamin_d2_max("vitamin-d-mbw"),
    "epa": lambda r: (None, None),
}


def nutrient_ids(data):
    """The nutrients a request describes: every enterable row of nutrients.csv and the
    template's rows."""
    return [n["id"] for n in data["nutrients"] if n["enterable"] == "yes"] + list(ROWS)
