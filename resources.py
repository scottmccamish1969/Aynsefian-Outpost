# resources.py

import random
from lore.lore_ingame import get_message
from lore.user_interface import log_and_display
from utils import get_task_by_worker, set_shield_state, clear_task_for_character
from planting import initialise_hydroponics_room
from constants import (
    RATION_PACKS, MAJOR_RESOURCES_ORDER, CHAIN_RESOURCES_ORDER, GATING_RULES, NORMAL_ITEM_RARITY, GATE_ITEM_RARITY, POST_CRITICAL_ITEM_RARITY,
    IDLE_CHARGE_USAGE, FULL_CHARGE, INITIAL_CHARGE, INITIAL_SEED_STASH, SEED_PACKETS_USED, NUM_DROIDS, LOW_CHARGE_FLAG, 
    TASK_CHARGING, TASK_ASSIGNED, TASK_PLANTING
)
from items import REPLACEMENT, CHAIN, NOVELTY, JUNK, TAROT, ITEM_DB, get_item_template

def get_resource(resources, name):
    for res in resources:
        # Safety first: skip invalid items
        if not isinstance(res, dict):
            continue
        if res.get("name", "").lower() == name.lower():
            return res
    return None

def resource_is_discovered(resources, name) -> bool:
    # True if this item name already exists in the discovered resources list.
    return any(r.get("name") == name for r in resources)

def add_or_get_discovered_item(resources, name):
    # Ensure that an item with this name exists in the discovered list.
    # - If already there, return that instance and the unchanged list.
    # - If not, pull its template from ITEM_DB, clone, append, and return it.
    
    existing = get_resource(resources, name)
    if existing is not None:
        return existing, resources

    template = get_item_template(name)
    if template is None:
        # Unknown name: just ignore silently; caller should handle None if needed
        return None, resources

    resources.append(template)
    return template, resources

def all_major_resources_found(resources) -> bool:
    # True if all major essentials have been discovered.
    return all(resource_is_discovered(resources, name) for name in MAJOR_RESOURCES_ORDER)

def update_resource(resource_name, updates, resource_list):
    # Finds a resource in a list of resource dicts by name and updates its fields.
    for res in resource_list:
        if res.get("name") == resource_name:
            res.update(updates)
            break
        
    return resource_list

def is_resource_found(resources, resource_name):
    res = get_resource(resources, resource_name)
    return bool(res and res.get("found", False))

def all_chain_resources_found(resources):
    return all(
        is_resource_found(resources, name)
        for name in CHAIN_RESOURCES_ORDER
    )

def all_critical_resources_found(current_resources):
    # 'Critical' = all major essentials + all chain resources.
    # When this is True, exploring is pure flavour (Tarot / novelty / junk).
    return all_major_resources_found(current_resources) and all_chain_resources_found(current_resources)

def force_next_critical(current_resources):
    #Used when the not-found streak is too long (>= 12) OR we hit a gating rule.
    #Returns the next unfound major first, then chain resource; else None.

    # First try major essentials
    for name in MAJOR_RESOURCES_ORDER:
        res = get_resource(current_resources, name)
        if res is not None and not res.get("found", False):
            return res.get("name")

    # Then try chain resources
    for name in CHAIN_RESOURCES_ORDER:
        res = get_resource(current_resources, name)
        if res is not None and not res.get("found", False):
            return res.get("name")

    return None

def _pick_unfound_item(candidates):
    #Generic helper: from a list of item dicts (Tarot, replacement, etc.),
    #return a random unfound one, or None if none are available.
    unfound = [c for c in candidates if not c.get("found", False)]
    if not unfound:
        return None
    return random.choice(unfound)

def react_to_found_resource(resource_name, resources, droids, gamestate, shieldstate):
    for res in resources:
        if res["name"] == resource_name:
            res["found"] = True
            amount = res.get("amount")
            break

    if not gamestate["list"]: gamestate["list"] = True

    # Command unlock logic, plus setting of other variables
    if resource_name == "FoodStore" and amount is None:
        amount = RATION_PACKS

    elif resource_name == "PowerSupply" and amount is None:
        discovered, resources = add_or_get_discovered_item(resources, resource_name)
        discovered["amount"] = INITIAL_CHARGE
    
    elif resource_name == "SeedStash":
        discovered, resources = add_or_get_discovered_item(resources, resource_name)
        # Only randomise if first time discovered
        if not discovered.get("examined", False):

            # Use ratios from SEED_PACKETS_USED
            base_weights = SEED_PACKETS_USED
            total_weight = sum(base_weights.values())

            # Random variation factor (0.85–1.15 gives nice replayability)
            import random
            variation = {
                crop: random.uniform(0.85, 1.15)
                for crop in base_weights
            }

            # Compute weighted amounts
            apple_raw = base_weights["apple"] * variation["apple"]
            potato_raw = base_weights["potato"] * variation["potato"]
            cabbage_raw = base_weights["cabbage"] * variation["cabbage"]

            # Convert to proportional amounts of INITIAL_SEED_STASH
            total_raw = apple_raw + potato_raw + cabbage_raw

            apple_amount = int((apple_raw / total_raw) * INITIAL_SEED_STASH)
            potato_amount = int((potato_raw / total_raw) * INITIAL_SEED_STASH)
            cabbage_amount = INITIAL_SEED_STASH - apple_amount - potato_amount

            # Store them on the resource dict
            discovered["apple"] = apple_amount
            discovered["potato"] = potato_amount
            discovered["cabbage"] = cabbage_amount

        # Enable planting when the conditions are met
        if resource_is_discovered(resources, "WaterSource") and resource_is_discovered(resources, "HydroponicsRoom"):
            gamestate["plant"] = True
            gamestate["reap"] = True
            gamestate["assign"] = True

    elif resource_name == "HydroponicsRoom":
        resources = initialise_hydroponics_room(resources)
        if resource_is_discovered(resources, "WaterSource") and resource_is_discovered(resources, "SeedStash"):
            gamestate["plant"] = True
            gamestate["reap"] = True
            gamestate["assign"] = True

    elif resource_name == "WaterSource":
        if resource_is_discovered(resources, "HydroponicsRoom") and resource_is_discovered(resources, "SeedStash"):
            gamestate["plant"] = True
            gamestate["reap"] = True
            gamestate["assign"] = True

    elif resource_name == "MealMaker":
        gamestate["assign"] = True
        
    elif resource_name == "CrystalField":
        gamestate["mine"] = True
        
    elif resource_name == "CrystalProcessor":
        gamestate["assign"] = True
        gamestate["refuel"] = True

    elif resource_name == "CloakingShield":
        shieldstate = set_shield_state("A", droids, resources, shieldstate)
        gamestate["assign"] = True

    return resources, droids, shieldstate

# Decide what (if anything) an exploration run discovers.
def attempt_exploration(task_package, allow_chain_early=True):
    current_resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]
    explore_count = task_package["explore_count"]
    found_nothing_count = task_package["found_nothing_count"]
    day = turns_elapsed // 10

    # Every call increments the explore counter
    explore_count += 1

    # ---------------------------------------------------
    # 1) Scripted early finds: FoodStore and PowerSupply
    # ---------------------------------------------------
    if not resource_is_discovered(current_resources, "FoodStore"):
        found_nothing_count = 0
        return "FoodStore", task_package

    if not resource_is_discovered(current_resources, "PowerSupply"):
        found_nothing_count = 0
        return "PowerSupply", task_package

    # ---------------------------------------------------
    # 2) Day/turn-based GATING_RULES for essentials
    #    ("If day>1 and explore_count>10, make sure SeedStash exists", etc.)
    # ---------------------------------------------------
    for name, min_day, min_explores in GATING_RULES:
        if day > min_day and explore_count > min_explores:
            if not resource_is_discovered(current_resources, name):
                # Force-discover this item
                found_nothing_count = 0
                return name, task_package

    # ---------------------------------------------------
    # 3) Try soft discovery of major essentials
    # ---------------------------------------------------
    
    major_candidates = [
        name for name in MAJOR_RESOURCES_ORDER
        if not resource_is_discovered(current_resources, name)
    ]

    found_resource = None
    if major_candidates:

        next_major_name = major_candidates[0]
        next_major = ITEM_DB[next_major_name]   # ← turn name into dict

        roll = random.random()

        # Classic spreadsheet logic: roll > prob = find
        if roll > next_major.get("prob", 1.0):
            found_resource = next_major

    # ---------------------------------------------------
    # 4) Chain resources (CrystalCombination → DecodeKey → AncientDroidCode)
    #    - Only considered once ALL major essentials are found.
    # ---------------------------------------------------
    if not found_resource and all_major_resources_found(current_resources):
        chain_to_consider = None

        if not resource_is_discovered(current_resources, "CrystalCombination"):
            chain_to_consider = "CrystalCombination"
        elif not resource_is_discovered(current_resources, "DecodeKey"):
            chain_to_consider = "DecodeKey"
        elif not resource_is_discovered(current_resources, "AncientDroidCode"):
            chain_to_consider = "AncientDroidCode"

        if chain_to_consider and allow_chain_early:
            chain_roll = random.random()
            # 25% chance per explore attempt to get the next chain item
            if chain_roll < 0.25:
                found_resource = chain_to_consider

    # ---------------------------------------------------
    # 5) If we got a critical (essential/chain) resource, return it.
    # ---------------------------------------------------
    if found_resource:
        name_of_found_resource = (
            found_resource if isinstance(found_resource, str)
            else found_resource.get("name", "")
        )
        found_nothing_count = 0
        return name_of_found_resource, task_package

    # 6) No major item found -> update 'found_nothing_count'
    found_nothing_count += 1

    # Streak-based gating
    is_gate_streak = found_nothing_count in (3, 6, 9)
    force_critical_by_streak = found_nothing_count >= 12

    # If we've hit 12+ failed critical attempts, force next critical.
    if force_critical_by_streak:
        forced = force_next_critical(current_resources)
        if forced:
            found_nothing_count = 0 # reset streak
            return forced, task_package 

    # If ALL critical resources are found, we are in "post critical" mode:
    # exploring is pure lore / flavour.
    in_post_critical_mode = all_critical_resources_found(current_resources)

    # Choose the rarity table
    if in_post_critical_mode:
        rarity = POST_CRITICAL_ITEM_RARITY
    elif is_gate_streak:
        rarity = GATE_ITEM_RARITY
    else:
        rarity = NORMAL_ITEM_RARITY

    # ---------------------------------------------------
    # 7) Try Tarot, then Replacement, then Novelty/Junk
    #    Important: these do NOT reset 'found_nothing_count' for criticals.
    # ---------------------------------------------------

    # 7a) Tarot cards
    tarot_chance = rarity.get("tarot", 0.0)
    tarot_item = _pick_unfound_item(TAROT)
    if tarot_item and random.random() < tarot_chance:
        tarot_item["found"] = True
        tarot_name = tarot_item["name"]
        found_nothing_count = 0
        return tarot_name, task_package

    # 7b) Replacement items
    replacement_chance = rarity.get("replacement", 0.0)
    replacement_item = _pick_unfound_item(REPLACEMENT)
    if replacement_item and random.random() < replacement_chance:
        replacement_item["found"] = True
        replacement_name = replacement_item["name"]
        found_nothing_count = 0
        return replacement_name, task_package

    # 7c) Novelty / Junk
    novelty_chance = rarity.get("novelty", 0.0)
    novelty_item = _pick_unfound_item(NOVELTY)

    # At gates (3/6/9) we guarantee *something* non-critical:
    #  - Try novelty first with elevated chance
    #  - If that fails (or none left), fall through to junk.
    if is_gate_streak:
        if novelty_item and random.random() < novelty_chance:
            novelty_item["found"] = True
            novelty_item_name = novelty_item["name"]
            found_nothing_count = 0
            return novelty_item_name, task_package

        # If we didn't get novelty, give junk (if any) as a consolation prize.
        junk_item = _pick_unfound_item(JUNK)
        if junk_item:
            junk_item["found"] = True
            junk_item_name = junk_item["name"]
            found_nothing_count = 0
            return junk_item_name, task_package

        # If no junk left either, just fall through to "no find".
        return None, task_package

    # Non-gate normal exploration:
    if novelty_item and random.random() < novelty_chance:
        novelty_item["found"] = True
        novelty_item_name = novelty_item["name"]
        found_nothing_count = 0
        return novelty_item_name, task_package


    # Small chance to get junk even on non-gate runs to keep things spicy
    junk_item = _pick_unfound_item(JUNK)
    if junk_item and random.random() < 0.05:
        junk_item["found"] = True
        junk_item_name = junk_item["name"]
        return junk_item_name, task_package

    # ---------------------------------------------------
    # 8) Absolutely nothing found this time.
    # ---------------------------------------------------
    return None, task_package


def charge_droid(droid_name, droids, resources):
    user_message = ""
    power_resource = next((r for r in resources if r.get("name") == "PowerSupply"), None)

    if not power_resource or not power_resource.get("found", False):
        user_message = get_message("charge", "nowhere_to_charge", droid_name=droid_name)
        return user_message, droids, resources

    if power_resource["amount"] < FULL_CHARGE:
        user_message = get_message("charge", "not_enough_power", droid_name=droid_name)
        return user_message, droids, resources

    current_charge = droids[droid_name]["charge"]

    # Prevent overcharging above 80%
    if current_charge >= 0.8*FULL_CHARGE:
        user_message = get_message("charge", "charge_full", droid_name=droid_name)
        return user_message, droids, resources

    if current_charge >= FULL_CHARGE:
        user_message = get_message("charge", "already_full", droid_name=droid_name)
        return user_message, droids, resources

    # Calculate actual amount to charge
    charge_amount = min((FULL_CHARGE+IDLE_CHARGE_USAGE) - current_charge, FULL_CHARGE+IDLE_CHARGE_USAGE)
    droids[droid_name]["charge"] += charge_amount
    power_resource["amount"] -= charge_amount-IDLE_CHARGE_USAGE

    user_message = get_message("charge", "success", droid_name=droid_name, new_charge=FULL_CHARGE)
    return user_message, droids, resources


def decrease_droid_charge(task_package):
    droids =  task_package["droids"]
    humans =  task_package["humans"]
    resources =  task_package["resources"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["turns_elapsed"]
        
    for i in range(NUM_DROIDS):
        droid_name = list(droids.keys())[i]
        droid_stats = droids[droid_name]
        if droid_stats["charge"] > 0 and droid_stats["item"] != "CloakingShield":
            droid_stats["charge"] = max(0, droid_stats["charge"] - IDLE_CHARGE_USAGE)

        # Warn if the charge drops below a certain level, but only warn once or twice at most (future proof for power usage)
        if (LOW_CHARGE_FLAG - 1) * IDLE_CHARGE_USAGE < droid_stats["charge"] <= LOW_CHARGE_FLAG * IDLE_CHARGE_USAGE:
            log_and_display(get_message("charge", "getting_low", name=droid_name), turns_elapsed)

        if droid_stats["charge"] <= 0:
            tasks, droids, humans, resources = interrupt_task_if_no_power(droid_name, droids, humans, resources, tasks, turns_elapsed)

    return task_package


def interrupt_task_if_no_power(name, droids, humans, resources, tasks, turns_elapsed):
    droid = droids[name]

    if droid["charge"] > 0:
        return tasks, droids, humans, resources

    task_id, task = get_task_by_worker(tasks, name)
    if not task:
        return tasks, droids, humans, resources

    task_type = task["type"].lower()

    if task["type"] != TASK_CHARGING: # Only interrupt a task if the task is not charging
        log_and_display(get_message("charge", "task_interrupt", name=name, task_type=task_type), turns_elapsed)
        if task["type"] == TASK_ASSIGNED:
            item_name = task.get("item_name", "")
        elif task["type"] == TASK_PLANTING:
            hydro = next((r for r in resources if r["name"] == "HydroponicsRoom"), None)
                        # Free the bed
            bed = {}
            for b in hydro["beds"]:
                if b["reserved_by"] == name:
                    b["occupied"] = False
                    b["crop_id"] = None
                    b["name"] = ""
                    b["reserved_by"] = ""

        humans, droids = clear_task_for_character(name, item_name, humans, droids)
        del tasks[task_id]

    return tasks, droids, humans, resources