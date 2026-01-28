#constants.py

# File names
CONFIG_FILE = "outpost_config.json"
LOG_FILE = "outpost_log.txt"
LOG_FILE_OLD = "outpost_log.old"

# Number of humans and droids
NUM_HUMANS = 4
NUM_DROIDS = 4

# Names and genders for humans and droids
NAMES = ["Carrie", "Hariet", "Karla", "Niobe", "Alex", "Mike", "Terry", "Rin"]
NO_GENDER = 0
FEMALE = 1
MALE = 2
GENDERS = {
    "Carrie" : FEMALE,
    "Hariet" : FEMALE,
    "Karla" : FEMALE,
    "Niobe" : FEMALE,
    "Alex" : MALE,
    "Mike" : MALE,
    "Terry": MALE,
    "Rin" : MALE
}

# Human hunger triggers
HUNGER = {
    "Okay": (0, 0),
    "Hungry": (7, 9),
    "Starving": (16, 18),
    "Near Death": (25, 27),
    "Deceased": (30, 33)
}

# Warning flags for hunger or power
HUNGER_WARNING = {
    "Starving": 14,
    "Near Death": 23,
    "Deceased": 28   
}

# Charging constants
INITIAL_CHARGE = 15000      # Enough for 15 droid charges (7.5 days for all charged, then 3 droids, then nothing - MUST then be mining crystals)
FULL_CHARGE = 1000          # The most a droid can be charged to
IDLE_CHARGE_USAGE = 50      # 50/turn leads to 500/day, leading to 2 days per full charge
LOW_CHARGE_FLAG = 6         # This is measured in turns (i.e. 6 turns before running out of charge - they get a warning message)

# Task names
TASK_EATING   = "Eating"
TASK_CHARGING  = "Charging"
TASK_EXPLORING = "Exploring"
TASK_EXAMINING = "Examining"
TASK_REPAIRING = "Repairing"
TASK_PLANTING  = "Planting"
TASK_REAPING   = "Reaping"
TASK_MINING    = "Mining"
TASK_ASSIGNED  = "Assigned"
TASK_REFUELING = "Refueling"

# Task timings (ranged)
TASK_LENGTH = {
    "feed_human": (1, 1),
    "explore_human": (2, 5),
    "examine_human": (1, 2), # This MUST be added to the item examine time
    "reap_human": (4, 6),
    "plant_human": (6, 8),
    "mine_human": (8, 10),
    "repair_human": (8, 10),
    "explore_droid": (3, 6),
    "examine_droid": (0, 1), # This MUST be added to the item examine time
    "reap_droid": (6, 8),
    "plant_droid": (8, 10),
    "mine_droid": (6, 8),
    "repair_droid": (4, 6),
    "assign_human_process": (3, 5),
    "assign_droid_process": (2, 4),
    "assign_human_cook": (4, 6),
    "assign_droid_cook": (5, 7),
    "assign_human_manual": (2, 4),
    "assign_droid_manual": (2, 4),
    "assign_human_terminal": (4, 6),
    "assign_droid_terminal": (2, 4),
    "refuel_human": (2, 4),
    "refuel_droid": (2, 4)
}
CHARGE_DURATION = 4  # No reason to make this variable

# Commands that may or may not be used
INITIAL_GAMESTATE = {
    "assign": False,
    "charge": True,
    "examine": True,
    "explore": True,
    "feed": True,
    "mine": False,
    "plant": False,
    "reap": False,
    "refuel": False,
    "repair": False,
    "list": True,
    "manage": True,
    "help": True,
    "next": True,
    "read": True,
    "reset": True,
    "status": True,
    "quit": True,
    "game_over": False,
    "endgame_reason": "null",
}

# Crop Growth Turns (+/- 10%)
GROWTH_TURNS = {
    "apple": 20,
    "cabbage": 32,
    "potato": 48
}

# Default planting amounts
SEED_PACKETS_USED = {
    "apple": 40,
    "cabbage": 11,
    "potato": 20
}
INITIAL_SEED_STASH = 400

# Crop Yield Range
YIELD_RANGE = {
    "apple": (50, 80),
    "cabbage": (8, 11),
    "potato": (28, 48)
}

# Serving values (food units needed to feed one person)
SERVING_VALUE = {
    "apple": 1,
    "cabbage": 0.25,
    "potato": 1
}

# How much of each will feed 1 human for 1 day if they only consume that food
FOOD_PER_DAY = {
    "apple":  8,
    "cabbage": 1,
    "potato": 4
}

# Ration Pack fallback
RATION_PACKS = 20  # initial stock (5 days' worth - MUST plant)

# Hydroponics bed limits
HYDROPONICS_BED_MIN = 4
HYDROPONICS_BED_MAX = 6

# Mining constants - this is how many we get from a mining run (fixed for now)
CRYSTAL_RATIO = {
    "red" : 0.5,
    "indigo": 0.3,
    "gold" : 0.2
}
BASE_CRYSTAL_YIELD = 10

POWER_PER_RED = 500
POWER_PER_INDIGO = 800
POWER_PER_GOLD = 1200

# Assigning constants
ASSIGN_TURNS = {
    "CrystalProcessor": 6,
}

ENDGAME_REASONS = {
    "all_dead" : "All humans have sadly perished.",
    "no_power":  "The Outpost has run out of power.",
    "mgc_arrival_no_shield": "The MGC has arrived and there was no active shield.",
    "mgc_arrival_shield_failed": "The MGC has arrived and the Outpost shield was inadequate.",
    "you_win?": "The MGC has arrrived and gone again. Your shield worked. CONGRATULATIONS. You have saved Aynsefian!"
}

MAJOR_RESOURCES_ORDER = [
    "SeedStash",
    "WaterSource",
    "HydroponicsRoom",
    "MealMaker",
    "CrystalField",
    "CrystalProcessor",
    "ShieldManual",
    "OldTerminal",
    "CloakingShield",
]

CHAIN_RESOURCES_ORDER = [
    "CrystalCombination",
    "DecodeKey",
    "AncientDroidCode",
]

# For when we find an essential item, if not found on day, turn
GATING_RULES = [
    ("SeedStash",      1, 10),
    ("WaterSource",    2, 20),
    ("HydroponicsRoom",2, 25),
    ("MealMaker",      3, 30),
    ("CrystalField",   4, 40),
    ("CrystalProcessor",4,45),
    ("ShieldManual",   5, 50),
    ("OldTerminal",    6, 60),
    ("CloakingShield",  7, 70),
]

# Base chances for a *single* explore, when we did NOT find an essential.
# These are *per explore*, not per-item. We try in order: tarot → replacement → novelty → (maybe junk).
NORMAL_ITEM_RARITY = {
    "tarot": 0.02,       # 2% chance each explore
    "replacement": 0.03, # 3% chance
    "novelty": 0.10,     # 10% chance (novelty or junk)
}

# Elevated chances when we're in a "gate streak" (3, 6, 9 failed essential attempts in a row).
GATE_ITEM_RARITY = {
    "tarot": 0.04,       # 4%
    "replacement": 0.05, # 5%
    "novelty": 0.20,     # 20% (else junk)
}

# After ALL essentials (including chain) are found, exploring becomes a "lore / flavour" hunt:
POST_CRITICAL_ITEM_RARITY = {
    "tarot": 0.20,       # 20% chance for a Tarot card
    "replacement": 0.00, # no more replacements needed
    "novelty": 0.30,     # 30% chance novelty, else junk
}

# These are ones humans or droids can be assigned to
ASSIGNABLE_ITEMS = {
    "CrystalProcessor": {
        "label": "CrystalProcessor",
        "type": "timed",
    },
    "ShieldManual": {
        "label": "ShieldManual",
        "type": "timed"
    },
    "OldTerminal": {
        "label": "OldTerminal",
        "type": "timed"   # for later
    },
    "CloakingShield": {
        "label": "CloakingShield",
        "type": "indefinite"
    }
}