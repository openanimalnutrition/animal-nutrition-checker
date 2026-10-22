"""Test-side map from the data ids and input names to template cells (s02, the requirement
table; s01, the Standards tab).

Volunteers never edit this; it exists only to compare with the sheet."""

NUTRIENT_ROWS = {
    'protein': 5,
    'protein-mbw': 6,
    'protein-dm': 7,
    'arginine': 8,
    'arginine-mbw': 9,
    'histidine': 10,
    'histidine-mbw': 11,
    'isoleucine': 12,
    'isoleucine-mbw': 13,
    'leucine': 14,
    'leucine-mbw': 15,
    'lysine': 16,
    'lysine-mbw': 17,
    'methionine': 18,
    'methionine-mbw': 19,
    'methionine-cystine': 20,
    'methionine-cystine-mbw': 21,
    'phenylalanine': 22,
    'phenylalanine-mbw': 23,
    'phenylalanine-tyrosine': 24,
    'phenylalanine-tyrosine-mbw': 25,
    'threonine': 26,
    'threonine-mbw': 27,
    'tryptophan': 28,
    'tryptophan-mbw': 29,
    'valine': 30,
    'valine-mbw': 31,
    'taurine': 32,
    'taurine-mbw': 33,
    'taurine-wet': 34,
    'taurine-wet-mbw': 35,
    'fat': 36,
    'fat-mbw': 37,
    'linoleic-acid': 38,
    'linoleic-acid-mbw': 39,
    'alpha-linolenic-acid': 40,
    'alpha-linolenic-acid-mbw': 41,
    'arachidonic-acid': 42,
    'arachidonic-acid-mbw': 43,
    'epa-dha': 44,
    'epa-dha-mbw': 45,
    'la-aa-to-ala-epa-dha-ratio': 46,
    'la-aa-to-ala-epa-dha-ratio-mbw': 47,
    'la-aa-to-epa-dha-ratio': 48,
    'la-aa-to-epa-dha-ratio-mbw': 49,
    'mct': 50,
    'mct-mbw': 51,
    'calcium': 52,
    'calcium-mbw': 53,
    'phosphorus': 54,
    'phosphorus-mbw': 55,
    'ca-p-ratio': 56,
    'ca-p-ratio-mbw': 57,
    'potassium': 58,
    'potassium-mbw': 59,
    'sodium': 60,
    'sodium-mbw': 61,
    'chloride': 62,
    'chloride-mbw': 63,
    'magnesium': 64,
    'magnesium-mbw': 65,
    'iron': 66,
    'iron-mbw': 67,
    'copper': 68,
    'copper-mbw': 69,
    'copper-wet': 70,
    'copper-wet-mbw': 71,
    'manganese': 72,
    'manganese-mbw': 73,
    'zinc': 74,
    'zinc-mbw': 75,
    'iodine': 76,
    'iodine-mbw': 77,
    'selenium': 78,
    'selenium-mbw': 79,
    'selenium-wet': 80,
    'selenium-wet-mbw': 81,
    'retinol': 82,
    'retinol-mbw': 83,
    'vitamin-a': 84,
    'vitamin-a-mbw': 85,
    'vitamin-d': 86,
    'vitamin-d-mbw': 87,
    'vitamin-e': 88,
    'vitamin-e-mbw': 89,
    'vitamin-k1': 90,
    'vitamin-k1-mbw': 91,
    'thiamine': 92,
    'thiamine-mbw': 93,
    'riboflavin': 94,
    'riboflavin-mbw': 95,
    'pantothenic-acid': 96,
    'pantothenic-acid-mbw': 97,
    'niacin': 98,
    'niacin-mbw': 99,
    'pyridoxine': 100,
    'pyridoxine-mbw': 101,
    'folate': 102,
    'folate-mbw': 103,
    'biotin': 104,
    'biotin-mbw': 105,
    'cobalamin': 106,
    'cobalamin-mbw': 107,
    'choline': 108,
    'choline-mbw': 109,
    'vitamin-c': 110,
    'water': 111,
    'carbohydrate': 112,
    'fiber-total': 113,
    'fiber-insoluble': 114,
    'fiber-soluble': 115,
    'oxalate': 116,
    'purine': 117,
    'energy-density': 118,
    'glutamic-acid': 119,
}

# requirement id -> (MIN column, MAX column, max-type column)
REQUIREMENT_COLUMNS = {
    'nrc-dog-adult': ('E', 'F', 'AU'),
    'aafco-dog-adult': ('G', 'H', 'AV'),
    'fediaf-dog-adult-mer95': ('I', 'J', 'AW'),
    'fediaf-dog-adult-mer110': ('K', 'L', 'AX'),
    'nrc-cat-adult': ('M', 'N', 'AY'),
    'aafco-cat-adult': ('O', 'P', 'AZ'),
    'fediaf-cat-adult-mer75': ('Q', 'R', 'BA'),
    'fediaf-cat-adult-mer100': ('S', 'T', 'BB'),
    'nrc-puppy-4-14-wk': ('U', 'V', 'BC'),
    'nrc-puppy-14-wk-plus': ('W', 'X', 'BD'),
    'aafco-dog-growth-reproduction': ('Y', 'Z', 'BE'),
    'aafco-dog-growth-large-breed': ('AA', 'AB', 'BF'),
    'fediaf-dog-early-growth-reproduction': ('AC', 'AD', 'BG'),
    'fediaf-dog-late-growth': ('AE', 'AF', 'BH'),
    'nrc-kitten': ('AG', 'AH', 'BI'),
    'aafco-cat-growth-reproduction': ('AI', 'AJ', 'BJ'),
    'fediaf-cat-growth': ('AK', 'AL', 'BK'),
    'nrc-dog-gestation-lactation': ('AM', 'AN', 'BL'),
    'nrc-cat-late-gestation': ('AO', 'AP', 'BM'),
    'nrc-cat-peak-lactation': ('AQ', 'AR', 'BN'),
    'fediaf-cat-reproduction': ('AS', 'AT', 'BO'),
}

# The requirement table's other cells: the name (B) and unit (C) of each nutrient row, the
# requirement names in row 2 (repeated over the code columns by =E2, =G2, ...), and the
# table's fixed labels (layout, not data).
NAME_COLUMN = 'B'
UNIT_COLUMN = 'C'
NAME_ROW = 2
TABLE_LABELS = {
    'AU1': 'Max type of the MAX cells in columns F to AT (see the AU3 note)',
}
CODE_LABEL_ROW = 3
CODE_LABEL = 'MAX TYPE'

# Standards tab (s01) input cells -> the checker's input names (oan/inputs.py).
INPUT_CELLS = {
    'O1': 'requirement',
    'B3': 'body_weight_kg',
    'E3': 'mature_weight_kg',
    'G3': 'puppies_nursing',
    'K3': 'lactation_week',
    'M3': 'life_stage',
    'B4': 'adult_dog_type',
    'D4': 'adult_cat_type',
    'K4': 'energy_intake_kcal_per_day',
    'G10': 'caloric_restriction_percent',
    'G65': 'puppy_body_weight_kg',
}
# Cells that are no longer inputs: some older test scenarios still set them.
RETIRED_CELLS = {
    'I3': 'cleared by the energy changes of 21OCT26; no formula reads it',
}
# s01 entry columns: the Min entry is the low entry, the Max entry the high one.
ENTRY_COLUMNS = {'G': 'low', 'I': 'high'}
MULTIPLIER_COLUMN = 'K'

# s01 rows 12-130 -> nutrient id, for the rows that have a requirement table row. Not
# listed: the s01 rows with no table row (49, 50, 55-58, 65, 66, 98, 99), for phase 3.
S01_ROWS = {
    12: 'protein', 13: 'protein-mbw', 14: 'arginine', 15: 'arginine-mbw', 16: 'histidine',
    17: 'histidine-mbw', 18: 'isoleucine', 19: 'isoleucine-mbw', 20: 'leucine', 21: 'leucine-mbw',
    22: 'lysine', 23: 'lysine-mbw', 24: 'methionine', 25: 'methionine-mbw',
    26: 'methionine-cystine', 27: 'methionine-cystine-mbw', 28: 'phenylalanine',
    29: 'phenylalanine-mbw', 30: 'phenylalanine-tyrosine', 31: 'phenylalanine-tyrosine-mbw',
    32: 'threonine', 33: 'threonine-mbw', 34: 'tryptophan', 35: 'tryptophan-mbw', 36: 'valine',
    37: 'valine-mbw', 38: 'taurine', 39: 'taurine-mbw', 40: 'taurine-wet', 41: 'taurine-wet-mbw',
    42: 'glutamic-acid', 43: 'fat', 44: 'fat-mbw', 45: 'linoleic-acid', 46: 'linoleic-acid-mbw',
    47: 'alpha-linolenic-acid', 48: 'alpha-linolenic-acid-mbw', 51: 'arachidonic-acid',
    52: 'arachidonic-acid-mbw', 53: 'epa-dha', 54: 'epa-dha-mbw',
    59: 'la-aa-to-ala-epa-dha-ratio', 60: 'la-aa-to-epa-dha-ratio', 61: 'mct', 62: 'mct-mbw',
    63: 'calcium', 64: 'calcium-mbw', 67: 'phosphorus', 68: 'phosphorus-mbw', 69: 'ca-p-ratio',
    70: 'potassium', 71: 'potassium-mbw', 72: 'sodium', 73: 'sodium-mbw', 74: 'chloride',
    75: 'chloride-mbw', 76: 'magnesium', 77: 'magnesium-mbw', 78: 'iron', 79: 'iron-mbw',
    80: 'copper', 81: 'copper-mbw', 82: 'copper-wet', 83: 'manganese', 84: 'manganese-mbw',
    85: 'zinc', 86: 'zinc-mbw', 87: 'iodine', 88: 'iodine-mbw', 89: 'selenium',
    90: 'selenium-mbw', 91: 'selenium-wet', 92: 'retinol', 93: 'retinol-mbw', 94: 'vitamin-a',
    95: 'vitamin-a-mbw', 96: 'vitamin-d', 97: 'vitamin-d-mbw', 100: 'vitamin-e',
    101: 'vitamin-e-mbw', 102: 'vitamin-k1', 103: 'vitamin-k1-mbw', 104: 'thiamine',
    105: 'thiamine-mbw', 106: 'riboflavin', 107: 'riboflavin-mbw', 108: 'pantothenic-acid',
    109: 'pantothenic-acid-mbw', 110: 'niacin', 111: 'niacin-mbw', 112: 'pyridoxine',
    113: 'pyridoxine-mbw', 114: 'folate', 115: 'folate-mbw', 116: 'biotin', 117: 'biotin-mbw',
    118: 'cobalamin', 119: 'cobalamin-mbw', 120: 'choline', 121: 'choline-mbw', 122: 'vitamin-c',
    123: 'water', 124: 'carbohydrate', 125: 'fiber-total', 126: 'fiber-insoluble',
    127: 'fiber-soluble', 128: 'oxalate', 129: 'purine', 130: 'energy-density',
}

# The energy row (s01 row 11): its entries G11 and I11 are the diet's energy (kcal/day).
ENERGY_ROW = 11
# The energy cells: s01 G4 is the selected requirement's energy (s02 row 4), C11 the energy
# the checker uses, E11 the energy row's maximum (none).
ENERGY_REQUIREMENT_CELL = 'G4'
ENERGY_USED_CELL = 'C11'
ENERGY_MAX_CELL = 'E11'
# The template's messages for the core's reasons (oan/energy.py REASONS), and for a missing
# or unknown requirement.
ENERGY_MESSAGES = {
    'life-stage-not-covered': 'Standards Sheet Needs A Life Stage This Selection Covers',
    'lactation-week-and-puppies-needed': 'Standards Sheet Needs Lactation Wk & Puppy #',
    'no-estimate-after-lactation-week-4': 'No NRC/FEDIAF Estimate After Lactation Wk 4: Use K4',
    'mature-weight-below-body-weight': 'Expected Mature BW Must Be At Least Current BW',
    'lactation-week-and-kittens-needed': 'Standards Sheet Needs Lactation Wk & Kitten #',
    'mature-weight-needed': 'Expected Mature BW in Standards Sheet Needed',
    'adult-dog-type-needed': 'No Dog Type Selection on Standards Sheet',
    'adult-cat-type-needed': 'No Cat Type Selection on Standards Sheet',
}
SELECT_REQUIREMENT = 'Select A Requirement In O1'
# The export's inputs (energy spec section 6); the row 11 cases keep them for the inputs they
# do not list.
EXPORT_INPUTS = {
    'O1': 'NRC RA Dog Maintenance',
    'B3': 15.0,
    'E3': None,
    'G3': 0,
    'K3': 0,
    'M3': 'None',
    'B4': 'Average laboratory or active (130 * kg BW^0.75)',
    'D4': 'Not selected or a cat',
    'K4': None,
}
# Row 11's band edge cells: the lower edges the bands use (oan/bands.py), and the upper edge
# the template shows just below each (display only), as fractions of the minimum (P-W) or of
# the range (X-AO); AP is the range high.
ROW11_BELOW_MIN = [('P', 0.249999999), ('Q', 0.25), ('R', 0.499999999), ('S', 0.5),
                   ('T', 0.749999999), ('U', 0.75), ('V', 0.999999999)]
ROW11_MIN = 'W'
ROW11_DECILES = [('X', 0.099999999), ('Y', 0.1), ('Z', 0.199999999), ('AA', 0.2),
                 ('AB', 0.299999999), ('AC', 0.3), ('AD', 0.399999999), ('AE', 0.4),
                 ('AF', 0.499999999), ('AG', 0.5), ('AH', 0.599999999), ('AI', 0.6),
                 ('AJ', 0.699999999), ('AK', 0.7), ('AL', 0.799999999), ('AM', 0.8),
                 ('AN', 0.899999999), ('AO', 0.9)]
ROW11_RANGE_HIGH = 'AP'
# Row 11's descriptions: L of the Min entry (G), N of the Max entry (I), M joins them.
ROW11_DESCRIPTIONS = {'G': 'L', 'I': 'N'}
ROW11_JOIN = ('M', 'to')

# s01 row 2: the band names (layout, not data), by the IG's band code.
BAND_LABELS = {
    'below-min-lt25': 'Very Severely Restricted (<25% of Min)',  # s01!O2
    'below-min-25-50': 'Severely Restricted (25 to <50% of Min)',  # s01!Q2
    'below-min-50-75': 'Moderately Restricted (50 to <75% of Min)',  # s01!S2
    'below-min-75-100': 'Slightly Restricted (75 to <100% of Min)',  # s01!U2
    'range-d1': 'Lowest/Just Above Min (Min to <10% of Range)',  # s01!W2
    'range-d2': 'Lower (10 to <20% of Range)',  # s01!Y2
    'range-d3': 'Low (20 to <30% of Range)',  # s01!AA2
    'range-d4': 'Low Moderate (30 to <40% of Range)',  # s01!AC2
    'range-d5': 'Mid Moderate (40 to <50% of Range)',  # s01!AE2
    'range-d6': 'High Moderate (50 to <60% of Range)',  # s01!AG2
    'range-d7': 'High (60 to <70% of Range)',  # s01!AI2
    'range-d8': 'Higher (70 to <80% of Range)',  # s01!AK2
    'range-d9': 'Near Highest (80 to <90% of Range)',  # s01!AM2
    'range-d10': 'Highest (90% of Range or Greater)',  # s01!AO2
}
NO_RANGE_LABEL = 'No range'
