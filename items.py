# items.py - all the game items, categorised

import copy
from constants import RATION_PACKS, INITIAL_CHARGE

# NOTE: If an item is marked as "replacable": True, it CAN be replaced IF that item listed as its replacement is FOUND first

# List of embedded resources
RESOURCES = [
    {
        "name": "FoodStore",
        "category": "essential",
        "category_counter": 1,
        "examinable": False,
        "examined": False,
        "examine_turns": 0,
        "replaceable": False,
        "replaced": False,
        "augmented": False,
        "prob": 0.0,
        "found": False,
        "rationPack": RATION_PACKS,
        "apple": 0,
        "cabbage": 0,
        "potato": 0,
        "soup": 0,
        "smoothie": 0,
        "stirFry": 0,
        "msg": "A place where you store your food. That's all you need to know.",
    },
    {
        "name": "PowerSupply",
        "category": "essential",
        "category_counter": 2,
        "examinable": True,
        "examined": False,
        "examine_turns": 3,
        "replaceable": False,
        "alternative_item": "SolarPanelArray",
        "replaced": False,
        "augmented": False,
        "prob": 0.0,
        "found": False,
        "amount": INITIAL_CHARGE,
        "msg": "The power supply will eventually need vials of crystal dust. Initial charge level: {amount} units.",
    },
    {
        "name": "SeedStash",
        "category": "essential",
        "category_counter": 3,
        "examinable": True,
        "examined": False,
        "examine_turns": 3,
        "replaceable": False,
        "replaced": False,
        "augmented": False,
        "prob": 0.7,
        "found": False,
        "apple": 0,
        "cabbage": 0,
        "potato": 0,
        "msg": "You found a seed vault! Many varieties for hydroponic growth. There are {A} apple seeds, {P} potato seeds and {C} cabbage seeds.",
    },
    {
        "name": "WaterSource",
        "category": "essential",
        "category_counter": 4,
        "examinable": False,
        "examined": False,
        "examine_turns": 0,
        "replaceable": False,
        "replaced": False,
        "augmented": False,
        "prob": 0.7,
        "found": False,
        "amount": 0,
        "msg": "An essential supply of aqua pura for varying uses in this fledgling Outpost.",
    },
    {
        "name": "HydroponicsRoom",
        "category": "essential",
        "category_counter": 5,
        "examinable": True,
        "examined": False,
        "examine_turns": 3,
        "replaceable": True,
        "alternative_item": "FertileSoil",
        "replaced": False,
        "augmented": False,
        "prob": 0.75,
        "found": False,
        "amount": 0,
        "msg": "This room inside the Outpost building can be used to plant crops.",
    },
    {
        "name": "CrystalField",
        "category": "essential",
        "category_counter": 6,
        "examinable": True,
        "examined": False,
        "examine_turns": 4,
        "replaceable": False,
        "replaced": False,
        "augmented": False,
        "prob": 0.8,
        "found": False,
        "amount": 0,
        "msg": "Amazing. These looked just like any other rocks. Milennia of dust will do that to a crystal. You may have something useful here. There are three different colours: red, indigo and gold.",
    },
    {
        "name": "MealMaker",
        "category": "essential",
        "category_counter": 7,
        "examinable": True,
        "examined": False,
        "examine_turns": 2,
        "replaceable": True,
        "alternative_item": "CampFire",
        "replaced": False,
        "augmented": False,
        "prob": 0.8,
        "found": False,
        "amount": 0,
        "msg": "You have found a curious looking machine that resembles a blender with 10% more sophistication. It is very dark inside of it.",
    },
    {
        "name": "CrystalProcessor",
        "category": "essential",
        "category_counter": 8,
        "examinable": True,
        "examined": False,
        "examine_turns": 2,
        "replaceable": True,
        "alternative_item": "CrystalMortarAndPestle",
        "replaced": False,
        "augmented": False,
        "prob": 0.85,
        "found": False,
        "amount": 0,
        "msg": "This thing looks like it could chew up ANYTHING that goes into it. Have you given everyone their annual health and safety brief?",
    },
    {
        "name": "ShieldManual",
        "category": "essential",
        "category_counter": 9,
        "examinable": True,
        "examined": False,
        "examine_turns": 4,
        "replaceable": True,
        "alternative_item": "ShieldOperatingCodes",
        "replaced": False,
        "augmented": False,
        "prob": 0.85,
        "found": False,
        "amount": 0,
        "msg": "Hmm, it's an old book of sorts. You can't understand the symbols on it. Someone is going to need to decode this.",
    },
    {
        "name": "OldTerminal",
        "category": "essential",
        "category_counter": 10,
        "examinable": True,
        "examined": False,
        "examine_turns": 2,
        "replaceable": True,
        "alternative_item": "BlackTablet",
        "replaced": False,
        "augmented": False,
        "prob": 0.9,
        "found": False,
        "amount": 0,
        "msg": "This terminal is surprisingly still working. It may hold important clues to getting the shields up, or else why is it here?"
        #Alt msg: "This terminal needs to be repaired. Assign someone to it - preferably a droid. It may be recoverable.",
    },
    {
        "name": "CloakingShield",
        "category": "essential",
        "category_counter": 11,
        "examinable": True,
        "examined": False,
        "examine_turns": 6,
        "replaceable": False,
        "replaced": False,
        "augmented": False,
        "prob": 0.9,
        "found": False,
        "amount": 0,
        "msg": "You've found it! The all important box that generates a cloaking shield outside of the cave entrace. This should block the MGC if done right. Get everyone onto this at once, Commander.",
    },
]

CHAIN = [
    {
        "name": "CrystalCombination", # DO NOT FIND THIS EARLY - only after CloakingShield is found: Crystals Ratio for the Shield
        "category": "chain",
        "category_counter": 1,
        "examinable": True,
        "examined": False,
        "examine_turns": 2,
        "replaceable": True,
        "alternative_item": "HandWrittenNote",
        "replaced": False,
        "augmented": False,
        "prob": 0.7,
        "found": False,
        "red": 0,   # These are the ratios of Crystal Colours (e.g 1 part red, 3 parts indigo, 2 parts gold... etc.)
        "indigo": 0,
        "gold": 0,
        "msg": "This professionally typed booklet describes the correct combination of crystals to make the shield operate effectively. It is: {R} red, {I} indigo and {G} gold.",
    },
    {
        "name": "DecodeKey", # DO NOT FIND THIS EARLY - only after CrystalCombination is found: Cannot understand ShieldManual otherwise
        "category": "chain",
        "category_counter": 2,
        "examinable": True,  # Further note: tells the user they need CrystalCombination *and* AncientDroidCode to run the shield.
        "examined": False,
        "examine_turns": 2,
        "replaceable": True,
        "alternative_item": "CypherCardInsert",
        "replaced": False,
        "augmented": False,
        "prob": 0.7,
        "found": False,
        "amount": 0,
        "msg": "Aha! This explains how to decode the ShieldManual. Give it to one of the droids. It's too complex for humans. Well, your humans, anyway.",
    },
    {
        "name": "AncientDroidCode",# DO NOT FIND THIS EARLY - only after DecodeKey is found: Identifies which of the 4 droids can activate the shield and run it
        "category": "chain",
        "category_counter": 3,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "replaceable": True,
        "alternative_item": "DroidPlugInModule",
        "replaced": False,
        "augmented": False,
        "prob": 0.7,
        "found": False,
        "droidName": "null", # We randomly assign this (between the 4 droids) once this code is found and *matches the droid's firmware*
        "amount": 0,
        "msg": "Inside the Shield Manual you see firmware specs — rare, old ones. You try each of your droids, and you are fortunate that the only droid that has a matching code is {name}. They need to be assigned to the Shield.",
    }
]

# Replacement items - for game variability (9 in total)
REPLACEMENT = [
    {
        "name": "FertileSoil",
        "category": "replacement",
        "category_counter": 1,
        "examinable": True,
        "examined": False,
        "examine_turns": 4,
        "replaces": "HydroponicsRoom",
        "found": False,
        "msg": "This soil lookes like it will hold crops. Arylyss and Cindlyss are standing by for advice. They are planetary experts, you realise. Or maybe not? You know now!"
    },
    {
        "name": "SolarPanelArray",
        "category": "replacement",
        "category_counter": 2,
        "examinable": True,
        "examined": False,
        "examine_turns": 4,
        "replaces": "PowerSupply",
        "found": False,
        "msg": "A bunch of one-third effective Shockley-Queisser solar panels that will give you some augmentation to your existing power needs."
    },
    {
        "name": "CrystalMortarAndPestle",
        "category": "replacement",
        "category_counter": 3,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "replaces": "CrystalProcessor",
        "found": False,
        "msg": "A dual purpose item. 1. It turns crystals into crystal dust and 2. Provides anger management therapy for you or one of your humans.",
    },
    {
        "name": "SelfPoweringStoveAndPot",
        "category": "replacement",
        "category_counter": 4,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "replaces": "MealMaker",
        "found": False,
        "msg": "A gleaming metal stove hums quietly. It seems to generate heat on its own. There's a pot on top — empty, for now. It's almost begging to have food put in it.",
    },
    {
        "name": "ShieldOperatingCodes",
        "category": "replacement",
        "category_counter": 5,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "replaces": "ShieldManual",
        "found": False,
        "msg": "Now then. What are THESE? Could these numbers and letters be the way in which to bluff the OldTerminal into doing your bidding? Anathusa, via the comms terminal says: 'Don't be too overconfident'. You're unsure what she means by that.",
    },
    {
        "name": "BlackTablet",
        "category": "replacement",
        "category_counter": 6,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "replaces": "OldTerminal",
        "found": False,
        "msg": "It's dark and mysterious. Like one of your former romantic partners, long since departed. Give this to one of the droids. They'll figure it out.",
    },
    {
        "name": "DroidPlugInModule",
        "category": "replacement",
        "category_counter": 7,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "replaces": "AncientDroidCode",
        "found": False,
        "msg": "It looks like some sort of bypass mechanism. Could be very handy indeed. Check it out a bit more closely, says Jinekali.",
    },
    {
        "name": "CypherCardInsert",
        "category": "replacement",
        "category_counter": 8,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "replaces": "DecodeKey",
        "found": False,
        "msg": "Okay. This plugs in... somewhere. Try any number of holes and slots and see how it goes but be careful not to hurt anyone or anything in the process.",
    },
    {
        "name": "HandWrittenNote",
        "category": "replacement",
        "category_counter": 9,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "replaces": "CrystalCombination",
        "found": False,
        "msg": "A mysterious note in some sort of obscure language. You will have to give this to one of the droids and hope that they know this language. Or ask Arylss and Cindlyss. Likely they might know.",
    },
]

# Plato's Tarot Cards - should be included with the Novelty Items
TAROT = [
    {
        "name": "PlatoTarot_TheHermit",
        "category": "tarot",
        "category_counter": 1,
        "examinable": True,
        "examined": False,
        "examine_turns": 3,
        "found": False,
        "isCritical": False,
        "msg": (
            "A solitary figure holding a faint blue lantern. The card hums softly when "
            "you touch it. Scribbled beneath the image are the words: "
            "'Seek the silent one. One alone knows the path to light the sky.'\n"
            "Lanemu whispers: 'This may speak of the one droid whose firmware can "
            "truly awaken the shield.'"
        )
    },
    {
        "name": "PlatoTarot_TheTower",
        "category": "tarot",
        "category_counter": 2,
        "examinable": True,
        "examined": False,
        "examine_turns": 3,
        "found": False,
        "isCritical": False,
        "msg": (
            "Lightning strikes a tall obsidian structure. At the base you see "
            "fragments of carved symbols, impossible to read by eye. "
            "'All falls apart unless the inner code is understood,' the caption reads.\n"
            "Lanemu murmurs: 'This may hint at decoding the ancient manual… not all is "
            "obvious in the ShieldManual.'"
        )
    },
    {
        "name": "PlatoTarot_TheStar",
        "category": "tarot",
        "category_counter": 3,
        "examinable": True,
        "examined": False,
        "examine_turns": 3,
        "found": False,
        "isCritical": False,
        "msg": (
            "A robed figure kneels beneath three glowing stars—red, indigo, and gold—"
            "arranged in a precise geometry. "
            "'Three lights, one pattern. Align them, and truth emerges.'\n"
            "Lanemu quietly says: 'This may whisper of crystal ratios and harmonics… "
            "listen well.'"
        )
    },
    {
        "name": "PlatoTarot_TheChariot",
        "category": "tarot",
        "category_counter": 4,
        "examinable": True,
        "examined": False,
        "examine_turns": 3,
        "found": False,
        "isCritical": False,
        "msg": (
            "A sleek, otherworldly machine glides across a barren plain, powered "
            "not by wheels but by shifting currents of light. "
            "'Direction matters. Momentum matters more.'\n"
            "Lanemu observes: 'This may nudge you toward the sequence needed to "
            "initiate dormant systems… like the Shield itself.'"
        )
    },
    {
        "name": "PlatoTarot_Judgement",
        "category": "tarot",
        "category_counter": 5,
        "examinable": True,
        "examined": False,
        "examine_turns": 3,
        "found": False,
        "isCritical": False,
        "msg": (
            "A horn sounds from a distant silver horizon. Silhouettes rise from the "
            "ground, startled awake. "
            "'When the call comes, only readiness determines fate.'\n"
            "Lanemu warns: 'This is an omen of approaching presence… the MGC does not "
            "delay forever.'"
        )
    },
    {
        "name": "PlatoTarot_TheSun",
        "category": "tarot",
        "category_counter": 6,
        "examinable": True,
        "examine_turns": 3,
        "found": False,
        "isCritical": False,
        "msg": (
            "A radiant sphere rises over crystalline fields. Warm, fierce, undeniable. "
            "Beneath it: 'Illumination breaks all shadows.'\n"
            "Lanemu smiles softly: 'This card may point to the final revelation—"
            "the moment when all preparations meet purpose.'"
        )
    }
]

# Novelty items 6 in total
NOVELTY = [
    {
        "name": "AstrologyWheel",
        "category": "novelty",
        "category_counter": 1,
        "examinable": True,
        "examined": False,
        "examine_turns": 4,
        "found": False,
        "isCritical": False,
        "msg": "This item is made of recycled plastic and has what you *think* are astrology symbols on it. This could be evil, could be helpful. Toss a coin as to which it is."
    },
    {
        "name": "MultiFunctionTool",
        "category": "novelty",
        "category_counter": 2,
        "examinable": True,
        "examined": False,
        "examine_turns": 4,
        "found": False,
        "isCritical": False,
        "msg": "This thing could possibly rebuild the entire Outpost by itself. If anyone knew how to use it. Even the Droids have no idea about how to use this item, and that has you concerned. A little."
    },
    {
        "name": "DiscoInfernoBall",
        "category": "novelty",
        "category_counter": 3,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "found": False,
        "isCritical": False,
        "msg": "This is not just ANY mirror ball. This one promises a 'Disco Inferno'. Don't let Mike go anywhere near it. That didn't turn out well the last time something like this showed up."
    },
    {
        "name": "RadarOfDestiny",
        "category": "novelty",
        "category_counter": 4,
        "examinable": True,
        "examined": False,
        "examine_turns": 3,
        "found": False,
        "isCritical": False,
        "msg": "A hand-held radar device that is pinging faintly. It points towards vague doom. It could potentially be indicating total destruction, but it isn't. Very encouraging."
    },
    {
        "name": "BoxOfDynamite",
        "category": "novelty",
        "category_counter": 5,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "found": False,
        "isCritical": False,
        "msg": "'Yeah great', says Zarasena, on hearing of this find. 'You found something that will blow up the entire Outpost. Good job. Quality work. Please hide that somewhere.'"
    },
    {
        "name": "InformerPilatesBench",
        "category": "novelty",
        "category_counter": 6,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "found": False,
        "isCritical": False,
        "msg": "Looks like some sort of place where would-be criminals sit and do exercises while waiting to speak to law enforcement. Usefulness: likely very low."
    },
]

# ALWAYS junk. Can never be part of the solution. 
JUNK = [
    {
        "name": "HouseBrick",
        "category": "junk",
        "category_counter": 1,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Just a regular sized red house brick. It has the initials NDG stamped on it. Jinekali says this means 'No Damn Good' but you're not sure if he's joking or not."
    },
    {
        "name": "HalfMeltedTrumpet",
        "category": "junk",
        "category_counter": 2,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "This is a standard issue trumpet that might have been exposed to extreme heat at some point in the past. {name} insists that it 'still has one good note in it'."
    },
    {
        "name": "BagOfSand",
        "category": "junk",
        "category_counter": 3,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "A plastic bag containing sand. It has a hole in it. Near the bottom. Best to put it down somewhere. Preferably outside, if you can."
    },
    {
        "name": "RadicalPolicyDocument",
        "category": "junk",
        "category_counter": 4,
        "examinable": True,
        "examined": False,
        "examine_turns": 4,
        "found": False,
        "isCritical": False,
        "msg": "This looks on the surface to prescribe peace to all, love before war, and rewards for kindness. It will require further study. No-one thinks they've seen anything like it before."
    },
    {
        "name": "AdjustableSpannerInTheWorks",
        "category": "junk",
        "category_counter": 5,
        "examinable": True,
        "examined": False,
        "examine_turns": 2,
        "found": False,
        "isCritical": False,
        "msg": "The perfect gift for Father's Day. A chrome-plated adjustable spanner/wrench. It has a hint of mischief about it. You could put it good use (maybe) but it's equally possible that it will put YOU to good use."
    }, 
    {
        "name": "IsoBarStool",
        "category": "junk",
        "category_counter": 6,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "found": False,
        "isCritical": False,
        "msg": "A bar stool with measurements printed along the legs. A meteorologist’s worst attempt at furniture."
    },
    {
        "name": "CopperHammer",
        "category": "junk",
        "category_counter": 7,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "isCritical": False,
        "msg": "A hammer made of copper. Okay. The hammer head is hollow. One strike against a hard surface and it will crumple into uselessness. Go on. Do it."
    },    
    {
        "name": "GlowingPumpkin",
        "category": "junk",
        "category_counter": 8,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "isCritical": False,
        "msg": "A pumpkin emitting a very faint bioluminescent glow. Probably harmless. Probably. Better do a health check on {name} just to be sure."
    },
    {
        "name": "TimeToGiveUpMachine",
        "category": "junk",
        "category_counter": 9,
        "examinable": True,
        "examined": False,
        "examine_turns": 1,
        "found": False,
        "isCritical": False,
        "msg": "You can actually turn this on with a red switch. Against all advice, you do. All it says on the screen is: 'Time to give up, loser'."
    },
    {
        "name": "BentSpoon",
        "category": "junk",
        "category_counter": 10,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "It bends just by looking at it. You are *absolutely* sure this is unrelated to psychic forces. Probably."
    },
    {
        "name": "CrackedSnowGlobe",
        "category": "junk",
        "category_counter": 11,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "A miniature winter scene inside... except the water has leaked out. Sad flakes cling to the glass."
    },
    {
        "name": "BrokenHourGlass",
        "category": "junk",
        "category_counter": 12,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Sand everywhere. Time is meaningless. Clean-up effort: not worth it. {name} says there's 'no time' to fix it anyway. You don't find this funny at all."
    },
    {
        "name": "FadedNoteBook",
        "category": "junk",
        "category_counter": 13,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Looks like it's been here for eight hundred years. Almsot every page contains the word 'WHY?' written repeatedly. Burning it is probably the best option."
    },
    {
        "name": "EmptyTeaTin",
        "category": "junk",
        "category_counter": 14,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Still smells faintly of Earl Grey. Comforting but useless."
    },
    {
        "name": "WarmRock",
        "category": "junk",
        "category_counter": 15,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Suspiciously warm to the touch. Does this mean it's radioactive? You wished you paid attention in your high school chemistry class."
    },
    {
        "name": "CoilOfWire",
        "category": "junk",
        "category_counter": 16,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "You have a hardware store back at home that would probably try to sell this. Hard to say how this might be useful. But hang onto it anyway."
    },
    {
        "name": "PokerFace",
        "category": "junk",
        "category_counter": 17,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Yes. It's a mask. For poker players. Unlikely to save the Outpost but {name} says it could be useful 'once the shield is up and we're all in maintenance mode.'"
    },
    {
        "name": "PartialBowlOfNuts",
        "category": "junk",
        "category_counter": 18,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "The bowl is partial. Not the nuts. It is a partial bowl, with nuts in it. You wonder why {name} thought this would actually be useful for the mission. The nuts look partially okay though."
    },
    {
        "name": "CampingShower",
        "category": "junk",
        "category_counter": 19,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "A wonderful addition to your next camping trip. A place to have a wash with luke warm water flowing at glacial speed. Not likely to be useful in getting the shield up."
    },
    {
        "name": "CarJack",
        "category": "junk",
        "category_counter": 20,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "There are no cars here at the Outpost. But if there were, you could jack them up reasonably well with this thing."
    },
    {
        "name": "BeerCoaster1975",
        "category_counter": 21,
        "category": "junk",
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "A beer coaster showing a man and a woman with flared jeans and massive collars. You wonder who put this here."
    },
    {
        "name": "NuclearBobbleHead",
        "category": "junk",
        "category_counter": 22,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "A smiling bobble-head toy of a 1950s looking man with an unnaturally happy grin on his face."
    },
    {
        "name": "MineCraftKeepSake",
        "category": "junk",
        "category_counter": 23,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "An utterly useless blocky pop-culture item that is past its Use-By date. Burning this would create toxic fumes, so don't even do that. Just tell {name} to bury it somewhere."
    },
    {
        "name": "CricketBall",
        "category": "junk",
        "category_counter": 24,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "What is THIS doing here? You don't even understand cricket. Maybe one of the droids can roll it around for a bit and keep everyone else entertained."
    },
    {
        "name": "Shades",
        "category": "junk",
        "category_counter": 25,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Could be Oakley. Might be a dollar-store brand. It's hard to tell. Those fakes are *so good* these days. Wear them. At least you'll look cool if the MGC obliterates you."
    },
    {
        "name": "PotOfRainbow",
        "category": "junk",
        "category_counter": 26,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "This is a bit disturbing. A pot of 'rainbow' at the end of the 'gold'. Is this is a metaphor for what happens when you run of money?"
    },
    {
        "name": "CrankHandle",
        "category": "junk",
        "category_counter": 27,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Might fit an old car. Or a backup generator. Or it's just junk. You'll have to ponder this for a while. Don't spend too much time on it."
    },
    {
        "name": "ProphetOfProfitTome",
        "category": "junk",
        "category_counter": 28,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "This book is probably a 8 inches thick. Someone took the time to write a ridiculously long treatise on how to make money. What good is that here? Useful for starting lots of fires. That's about it."
    },
    {
        "name": "PlasticToyTank",
        "category": "junk",
        "category_counter": 29,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Reminds you of your childhood. Playing war games. Utterly useless skill now. To find this object here in the Outpost makes you feel like you've slipped into a parallel universe for a moment."
    },
    {
        "name": "MothManKeepsake",
        "category": "junk",
        "category_counter": 31,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "A horrendous action figure that scares the Bejesus out of everyone. This might mean it's important. But probably not."
    },
    {
        "name": "DiceOfYesAndNo",
        "category": "junk",
        "category_counter": 32,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "An oversized pair of dice: one with YES on all six faces, the other with NO on all six faces. This should please those who like to answer a question with: 'Yes and No...'"
    },
    {
        "name": "CircuitBreaker",
        "category": "junk",
        "category_counter": 33,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "A circuit breaker handle that fits into a fuse box. Now, if you can only find the fuse box it came from, you'll have an alternate electrical protection system for the one you already have."
    },
    {
        "name": "MacksFastFoodVoucher",
        "category": "junk",
        "category_counter": 34,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "A voucher for a free small soft drink from Mack's Fast Food Emporium. Which universe did THIS come from? Unhealthy, pointless and sad, all at the same time."
    },
    {
        "name": "FirstAidBox",
        "category": "junk",
        "category_counter": 35,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "At first glance it appears useful, but on inspection, it appears to be four or five hundred years old and contains nothing but dust. {name}'s hopes are shattered. This DID look like a good find. But it's not."
    },
    {
        "name": "RustyMetalWheel",
        "category": "junk",
        "category_counter": 36,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "{name} says that it looks like it could be thousands of years old. Could be. But then again, maybe it's just a metal that rusts easily. You may never know. Pondering this will keep you awake at night."
    },
    {
        "name": "BoxOfBiscuits",
        "category": "junk",
        "category_counter": 37,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "These are dog biscuits. Not edible for humans. Even if starving. It says so on the box. You could give them to Salvation but: 1. He's a surface probe turned into a pretend dog and 2. He's not here."
    },
    {
        "name": "BrokenMP3Player",
        "category": "junk",
        "category_counter": 38,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Utterly useless and superseded by modern technology. It's broken anyway. You could get a droid to repair it but what then? You don't even have any MP3s. Shield, Commander, Shield. Focus."
    },
    {
        "name": "JigsawOfTheCosmos",
        "category": "junk",
        "category_counter": 39,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "An entire map of the cosmos. 853 pieces. Putting it together will take two whole days. At least. Don't do that. Plant some crops or do some mining instead."
    },
    {
        "name": "DiscardedAndBrokenToiletSeat",
        "category": "junk",
        "category_counter": 40,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "No matter where you travel in the Universe, there's always one of these to be found, sooner or later. Aynsefian is no exception to this rule."
    },
    {
        "name": "ScentedCandleBlack",
        "category": "junk",
        "category_counter": 41,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "A scented candle that is black. Yes, it is black wax. You sniff it and it smells like burning rubber. This appears to be someone's idea of a joke."
    },
    {
        "name": "NoHitchHikingSign",
        "category": "junk",
        "category_counter": 42,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Now where's the fun in this? Someone decided hitch hiking on a remote planet was a bad idea! There should be a Vogon transport along any time soon. Surely!"
    },
    {
        "name": "YouSpinMeRightRoundBabyRightRound",
        "category": "junk",
        "category_counter": 43,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "...like a record, baby, right round, round, round. 80s music always gets better with time. It's a 45 on red vinyl. Not even scratched! Now, you just need a record player..."
    },
    {
        "name": "VinylRecordPlayer",
        "category": "junk",
        "category_counter": 44,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "People still want these? Pray tell why? It's even got a compatabile power plug, but the needle is missing. Oh well. Back to planting, mining, and getting the shield up."
    },
    {
        "name": "ReplacementNeedle",
        "category": "junk",
        "category_counter": 45,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "For a vinyl record player! Priceless. Out here, in the back waters of the galaxy, you find THIS."
    },
    {
        "name": "GlassBeerStein",
        "category": "junk",
        "category_counter": 46,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Still intact. Distinctly weathered appearance. Needs a good soak in antibacterials before using. If you had beer, that is. You don't."
    },
    {
        "name": "16DifferentPipeCleaners",
        "category": "junk",
        "category_counter": 47,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "All different colours. Can be used for just about anything! Apparently."
    },
    {
        "name": "StackOfOldWood",
        "category": "junk",
        "category_counter": 48,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Why did you bother examining this? It's a stack of wood. Old wood. Exactly as described."
    },
    {
        "name": "OpenMikeNightInvitation",
        "category": "junk",
        "category_counter": 49,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Somebody, back in the far reaches, had an Open Mike night. Here in this outpost building. Must have been some long days back whenever this was printed."
    },
    {
        "name": "WaterGun",
        "category": "junk",
        "category_counter": 50,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Someone is going to get squirted. You'd better dispose of this item before that happens. Or at least hide it."
    },
    {
        "name": "UltimateFrisbee",
        "category": "junk",
        "category_counter": 51,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "First there was normal frisbee then 'good frisbee', 'improved frisbee', and 'big league frisbee'. Apparently. After Ultimate Frisbee, there's nowhere else to go. Not a wise name choice."
    },
    {
        "name": "BorrowedSugar",
        "category": "junk",
        "category_counter": 52,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "That's what it says on the jar. When you borrow someone's sugar, do you have to give back what you don't use? And why is it always sugar? Why not whiskey? Or cheesecake?"
    },
    {
        "name": "AGoodExcuse",
        "category": "junk",
        "category_counter": 53,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "Something you have always wanted. Better than a BadExcuse. Use it wisely. When the MGC arrives, it may not be enough. It's worth a try, though."
    },
    {
        "name": "8PrisonBars",
        "category": "junk",
        "category_counter": 54,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "{name} swears that these are prison bars: 8 of them. You wonder how they know this. Your trust in them goes down a few levels. Oh well. Press on, Commander."
    },
    {
        "name": "8Ball",
        "category": "junk",
        "category_counter": 55,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "It's a black pool ball with the number 8 on it. Put it somewhere safe. Someone will go head over tail if it's on the floor and they step on it. Even the droids are nervous about this sort of thing."
    },
    {
        "name": "PlasticVikingHelmet",
        "category": "junk",
        "category_counter": 56,
        "examinable": True,
        "examined": False,
        "examine_turns": 0,
        "found": False,
        "msg": "This looks *so* good you decide to wear it around the Outpost for a while. Karla is giving you funny looks. Maybe you ARE a bit unhinged."
    },
]


# items.py – master item registry

# If your items are split into several lists, build a single flat list here.
# Adjust this if your list names differ.
ALL_ITEMS = []

ALL_ITEMS.extend(RESOURCES)
ALL_ITEMS.extend(CHAIN)
ALL_ITEMS.extend(REPLACEMENT)
ALL_ITEMS.extend(NOVELTY)
ALL_ITEMS.extend(JUNK)
ALL_ITEMS.extend(TAROT)

# Map from name -> template dict
ITEM_DB = {item["name"]: item for item in ALL_ITEMS}


def get_item_template(name: str):
    # Return a DEEP COPY of the template for an item with this name, or None if not found.
    # We deep-copy so that mutations to discovered items don't affect the DB.
    
    template = ITEM_DB.get(name)
    if template is None:
        return None

    clone = copy.deepcopy(template)

    # Normalise some fields so discovered instances are always consistent:
    #clone["found"] = True          # any entry in resources is, by definition, found
    if "examined" not in clone:
        clone["examined"] = False

    return clone