# utils.py

import json
import os
import random
import difflib

from lore.lore_ingame import get_message
from lore.lore_story import print_orders
from lore.user_interface import get_input, log_and_display
from constants import (NAMES, INITIAL_GAMESTATE, CONFIG_FILE, LOG_FILE, LOG_FILE_OLD, FEMALE, MALE, GENDERS, HUNGER, LOW_CHARGE_FLAG, IDLE_CHARGE_USAGE,
    NUM_HUMANS, NUM_DROIDS, HUNGER_WARNING, TASK_ASSIGNED, TASK_PLANTING, TASK_EATING, TASK_EXPLORING, TASK_MINING, TASK_CHARGING)


def get_pronouns(name, is_human):
    gender = GENDERS.get(name, 0)
    if not is_human:
        # Droids: always neuter regardless of name
        return {
            "p1": "They",
            "p2": "Them",
            "p3": "Its"
        }
    
    if gender == FEMALE:
        return {
            "p1": "She",
            "p2": "Her",
            "p3": "Her"
        }
    elif gender == MALE:
        return {
            "p1": "He",
            "p2": "Him",
            "p3": "His"
        }
    else:
        # Unknown or genderless human
        return {
            "p1": "They",
            "p2": "Them",
            "p3": "Their"
        }


def is_command_enabled(command, gamestate):
    return gamestate.get(command, False)


def increment_counter(package, key):
    package["counters"][key] += 1


def get_and_increment(package, key):
    value = package["counters"][key]
    package["counters"][key] += 1
    return value


def build_task_package(**kwargs):
    default_package = {
        "crops": {},
        "droids": {},
        "gamestate": {},
        "humans": {},
        "item": "",
        "resources": {},
        "shieldstate": {},
        "tasks": {},
        "task_data": {},
        "counters": {
            "turns": 0, 
            "task": 0, 
            "crop": 0, 
            "explore": 0, 
            "found_nil": 0, 
            },
    }
    
    default_package.update(kwargs)
    return default_package


def initialise_outpost(first_time):
    # Create a brand-new Outpost state.
    # NOTE: resources starts as an EMPTY LIST – nothing is discovered yet.

    name_pool = random.sample(NAMES, 8)

    empty_queue = {
        "1": {"task": "", "item": ""},
        "2": {"task": "", "item": ""},
        "3": {"task": "", "item": ""}
    }

    humans = {
        name_pool[i]: {
            "hunger": 0,
            "state": "Okay",
            "task": "",
            "item": "",
            "queue": empty_queue.copy()
        } for i in range(NUM_HUMANS)
    }

    droids = {
        name_pool[i + NUM_HUMANS]: {
            "charge": 0,
            "AncientCode": False,
            "task": "",
            "item": "",
            "queue": empty_queue.copy()
        } for i in range(NUM_DROIDS)
    }

    task_package = build_task_package(
        crops={},
        droids=droids,
        gamestate=INITIAL_GAMESTATE.copy(),
        humans=humans,
        resources=[],
        shieldstate={
            "shield_found": False,
            "manual_decoded": False,
            "ancient_droid_valid": False,
            "crystal_combo_valid": False,
            "shield_connected": False,
            "shield_active": False
        },
        tasks={}
    )

    if first_time:
        print_orders(task_package["gamestate"])

    return task_package


def save_config(task_package):
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    # Copy only keys we care about from task_package
    keys_to_save = [
        "crops", "droids", "gamestate", "humans", "item", "resources",  "shieldstate", "tasks", "task_data", "counters"
    ]

    for key in keys_to_save:
        if key in task_package:
            data[key] = task_package[key]

    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)

        return build_task_package(
            crops=data.get("crops", {}),
            droids=data.get("droids", {}),
            gamestate=data.get("gamestate", INITIAL_GAMESTATE.copy()),
            humans=data.get("humans", {}),
            resources=data.get("resources", []),
            shieldstate=data.get("shieldstate", {}),
            tasks=data.get("tasks", {}),
            task_data=data.get("task_data", {}),
            counters=data.get("counters", {"turns": 0, "task": 0, "crop": 0, "explore": 0, "found_nil": 0,}),
        )

    else:
        first_time = True
        task_package = initialise_outpost(first_time)

        save_config(task_package)
        return task_package


def reset_config(task_package):
    # Resets the config file as per the user's request
    print(get_message("reset", "start"))

    # Rename current log file if it exists
    if os.path.exists(LOG_FILE):
        os.replace(LOG_FILE, LOG_FILE_OLD)

    first_time = False
    task_package = initialise_outpost(first_time)

    # Save to config file
    save_config(task_package)

    print(get_message("reset", "done"))


def get_best_match(name, candidates, cutoff=0.75):
    #Return the closest name match from candidates, or None if not close enough.
    name = name.lower()
    candidates_lower = [c.lower() for c in candidates]
    matches = difflib.get_close_matches(name, candidates_lower, n=1, cutoff=cutoff)
    if matches:
        # Return original-cased version from candidates
        index = candidates_lower.index(matches[0])
        return candidates[index]
    return None


def process_hunger_status(name, task_package):
    # Check if a human is advancing in hunger
    human = task_package["humans"][name]
    current_state = human["state"]
    hunger = human["hunger"]
    turns_elapsed = task_package["turns_elapsed"]

    # Helper: set hunger band if just fed
    def reset_hunger_band(hunger_value, current_state):
        correct_state = current_state
        previous_band = "Okay"
        previous_high = 0
        for band, (low, high) in HUNGER.items():
            if band == current_state and (previous_high < hunger_value < high):
                correct_state = previous_band
            previous_band = band
            previous_high = high
        return correct_state

    # Helper: determine hunger band
    def get_hunger_band(hunger_value, current_state):
        for band, (low, high) in HUNGER.items():
            if low <= hunger_value <= high:
                return band
        return current_state

    # --- Recalculate band if just fed ---
    current_state = reset_hunger_band(hunger, current_state)
    human["state"] = current_state
    new_band = get_hunger_band(hunger, current_state)

    # --- DEATH (always deterministic) ---
    if new_band == "Deceased":
        if current_state != "Deceased":
            log_and_display(get_message("hunger", "deceased", name=name), turns_elapsed)
            human["state"] = "Deceased"
        return task_package

    # --- WARNING PHASES ---
    if current_state != "Okay":
        for warning_state, warning_turn in HUNGER_WARNING.items():
            if hunger == warning_turn and current_state != warning_state:
                pronouns = get_pronouns(name, True)
                log_and_display(get_message("hunger", f"{warning_state.lower()}_warning", pronoun=pronouns["p1"], name=name), turns_elapsed)

    # --- NO CHANGE ---
    if new_band == current_state:
        return task_package

    low, high = HUNGER[new_band]

    # --- FORCED TRANSITION (upper bound) ---
    if hunger >= high:
        human["state"] = new_band
        if new_band != "Okay":
            pronouns = get_pronouns(name, True)
            log_and_display(get_message("hunger", new_band, pronoun=pronouns["p2"].lower(), name=name), turns_elapsed)
        return task_package

    # --- PROBABILISTIC TRANSITION (lower bound only) ---
    if hunger >= low and hunger < high:
        if random.random() < 0.5:
            human["state"] = new_band
            pronouns = get_pronouns(name, True)
            log_and_display(get_message("hunger", new_band, pronoun=pronouns["p2"].lower(), name=name), turns_elapsed)

            if new_band == "Starving":
                task_package = interrupt_task_if_starving(name, human, task_package)

    return task_package


def interrupt_task_if_starving(name, human, task_package):
    tasks = task_package["tasks"]
    resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]

    if human["state"] != "Starving":
        return tasks, humans, droids  # nothing to do

    task_id, task = get_task_by_worker(tasks, name)
    if not task:
        return task_package  # idle anyway

    task_type = task["type"].lower()

    log_and_display(f"{name} cannot continue {task_type}. Hunger overwhelms focus and strength. The task has been abandoned.", turns_elapsed)

    if task["type"] == TASK_PLANTING:
        hydro = next((r for r in resources if r["name"] == "HydroponicsRoom"), None)
            # Free the bed
        bed = {}
        for b in hydro["beds"]:
            if b["reserved_by"] == name:
                b["occupied"] = False
                b["crop_id"] = None
                b["name"] = ""
                b["reserved_by"] = ""

    humans, droids = clear_task_for_character(name, human["item"], humans, droids)
    del tasks[task_id]

    return task_package


def get_task_by_worker(tasks, worker_name):
    # Returns (task_id, task_data) for the active task assigned to worker_name, or (None, None) if not found.
    for tid, task in tasks.items():
        if task.get("name") == worker_name:
            return tid, task
    return None, None


def can_character_act(character, task_name, humans, droids, turns_elapsed):
    # Generic checks to see if we can use this character (human or droid)

    target = get_best_match(character, list(humans.keys()) + list(droids.keys()))
    if not target:
        log_and_display(get_message("error", "unknown_worker", name=character, task=task_name),
                        turns_elapsed)
        return False, False, target

    is_human = target in humans

    # ---- Pre-condition checks ----
    if is_human and humans[target]["state"] in ["Starving", "Near Death", "Deceased"]:
        pronouns = get_pronouns(target, True)
        if task_name == TASK_ASSIGNED:
            log_and_display(
                get_message("error", "too_hungry_for_assign", name=target, task=task_name.lower(), pronoun=pronouns["p1"]),
                turns_elapsed)
        else:
            log_and_display(
                get_message("error", "too_hungry", name=target, task=task_name.lower(), pronoun=pronouns["p1"]),
                turns_elapsed)
        return False, is_human, target

    if not is_human:
        charge = droids[target]["charge"]
        current_task = droids[target]["task"]
        
        # Droids with 0 charge can only continue if they are currently charging
        if charge <= 0 and current_task != TASK_CHARGING:
            if task_name == TASK_ASSIGNED:
                log_and_display(get_message("error", "no_power_for_assign", name=target, task=task_name.lower()), turns_elapsed)
            else:
                log_and_display(get_message("error", "no_power", name=target, task=task_name.lower()), turns_elapsed)
            return False, is_human, target

    return True, is_human, target


def check_shield_state(task_package):
    # Centralised synthesis check of shield state based on current droid and resource status

    shieldstate = task_package["shieldstate"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]

    # Find the shield and check if it exists
    shield = next((r for r in resources if r["name"] == "CloakingShield"), None)

    if shield:
        power_supply = next((r for r in resources if r["name"] == "PowerSupply"), None)
        if power_supply is not None and power_supply["amount"] <= 0:
            log_and_display(get_message("shield", "no_power"), turns_elapsed)
            s = shieldstate
            s["shield_connected"] = False
            shieldstate["shield_active"] = (
                s["shield_found"]
                and s["manual_decoded"]
                and s["ancient_droid_valid"]
                and s["crystal_combo_valid"]
                and s["shield_connected"]
            )
            task_package["shieldstate"] = shieldstate
            return task_package
    else:
        return task_package  # If no shield exists at all, nothing to update

    # Check for connected droid
    connected_droid_found = False
    for droid_name, droid in droids.items():
        if droid.get("task") == TASK_ASSIGNED and droid.get("item") == "CloakingShield":
            if droid.get("charge", 0) > 0:
                connected_droid_found = True
            break

    s = shieldstate
    s["shield_connected"] = connected_droid_found

    shieldstate["shield_active"] = (
        s["shield_found"]
        and s["manual_decoded"]
        and s["ancient_droid_valid"]
        and s["crystal_combo_valid"]
        and s["shield_connected"]
    )

    task_package["shieldstate"] = shieldstate
    return task_package


def set_shield_state(requirement, droids, resources, shieldstate):
    # Set the shield state based on a number of requirements
    if requirement == "A":
        shieldstate["shield_found"] = any(
            item.get("name") == "CloakingShield" for item in resources
        )

    elif requirement == "B":
        for item in resources:
            if item.get("name") == "ShieldManual" and item.get("decoded"):
                shieldstate["manual_decoded"] = True
                break

    elif requirement == "C":
        for droid in droids.values():
            if droid.get("AncientCode") and droid.get("task") == TASK_ASSIGNED and droid.get("item") == "CloakingShield":
                shieldstate["ancient_droid_valid"] = True
                break

    elif requirement == "D":
        shieldstate["crystal_combo_valid"] = any(
            item.get("name") == "CrystalCombination" for item in resources
        )

    elif requirement == "E":
        for droid in droids.values():
            if droid.get("task") == TASK_ASSIGNED and droid.get("item") == "OldTerminal":
                shieldstate["shield_connected"] = True
                break

    # Final synthesis: is the shield ACTIVE?
    s = shieldstate
    shieldstate["shield_active"] = (
        s["shield_found"] and
        s["manual_decoded"] and
        s["ancient_droid_valid"] and
        s["crystal_combo_valid"] and
        s["shield_connected"]
    )

    return shieldstate


def set_task_status_for_character(name, task_type, item_name, humans, droids, turns_elapsed):
    #Updates a character's task and item fields to reflect what they're doing.
    
    if name in humans:
        humans[name]["task"] = task_type
        humans[name]["item"] = item_name
    elif name in droids:
        droids[name]["task"] = task_type
        droids[name]["item"] = item_name
    else:
        log_and_display(get_message("error", "unknown_assign", name=name), turns_elapsed)

    return humans, droids


def clear_task_for_character(name, item, humans, droids):
    # Clears a character's task and item fields, and handles any special cases like the shield.
    
    if name in humans:
        humans[name]["task"] = ""
        humans[name]["item"] = ""
    elif name in droids:
        droids[name]["task"] = ""
        droids[name]["item"] = ""
    else:
        log_and_display(get_message("error", "unknown_assign", name=name))
        return humans, droids

    # Handle shield logic (if no one else is still assigned to it)
    if item == "CloakingShield":
        still_assigned = any(
            char.get("item") == "CloakingShield"
            for char in list(humans.values()) + list(droids.values())
        )
        if not still_assigned:
            # If needed, update shieldstate externally in calling function
            pass  # Replace with logic if desired

    return humans, droids


def get_integer_input(prompt, min_value=None, max_value=None):
    # Prompts the user for an integer input, validates, and returns it.
    # Accepts optional min and max values.
    
    while True:
        user_input = input(prompt)
        try:
            value = int(user_input)
            if min_value is not None and value < min_value:
                print(f"❌ Please enter a number greater than or equal to {min_value}.")
                continue
            if max_value is not None and value > max_value:
                print(f"❌ Please enter a number less than or equal to {max_value}.")
                continue
            return value
        except ValueError:
            print("❌ Invalid input. Please enter a valid integer.")


def parse_command_targets(qualifier, humans, droids, turns_elapsed, tasks=None, task_type=None):
    # Get appropriate input message key based on task_type
    input_prompts = {
        TASK_CHARGING: "charge",
        TASK_EXPLORING: "explore",
        TASK_MINING: "mine",
        TASK_EATING: "feed",
    }

    # If no qualifier provided, prompt the player using the correct input message
    if not qualifier:
        key = input_prompts.get(task_type, "charge")  # default to "charge" if task_type unknown
        qualifier = get_input("input", key, turns_elapsed)

    # Normalise to lowercase and strip spaces
    qualifier = qualifier.lower().strip()
    found_valid_name = False

    # Handle special groupings
    if qualifier == "all":
        if task_type == TASK_CHARGING:
            targets = list(droids.keys())  # Only droids can be charged

        elif task_type == TASK_EATING:
            targets = list(humans.keys())  # Only humans can be fed

        elif task_type == TASK_EXPLORING:
            # Only assign droids with charge > 0
            valid_humans = list(humans.keys())
            valid_droids = [d for d in droids if (droids[d]["charge"] > 0 or droids[d]["task"] == TASK_CHARGING)]
            targets = valid_humans + valid_droids

        found_valid_name = True


    elif qualifier == "idle" and task_type == TASK_EXPLORING:
        idle_humans = [h for h in humans if humans[h]["task"] == ""]
        idle_droids = [d for d in droids if (droids[d]["task"] == "" and droids[d]["charge"] > 0)]
        targets = idle_humans + idle_droids
        found_valid_name = True
        
    elif qualifier == "low" and task_type == TASK_CHARGING:
        targets = [d for d in droids if droids[d]["charge"] <= LOW_CHARGE_FLAG*IDLE_CHARGE_USAGE ]
        found_valid_name = True

    else:
        # Treat as name(s), split on comma or space
        if isinstance(qualifier, str):
            raw_names = [q.strip() for q in qualifier.replace(",", " ").split()]
        else:
            raw_names = qualifier  # Already a list (e.g. from handle_command)
        
        # Build filtered target list
        targets = []
        for name in raw_names:
            match = get_best_match(name, list(humans.keys()) + list(droids.keys()))
            if match:
                found_valid_name = True
                if task_type == TASK_EATING and match in droids:
                    continue  # Skip droids during feeding
                if task_type == TASK_CHARGING and match in humans:
                    continue  # Skip humans during charging
                targets.append(match)

    if not found_valid_name:
        if task_type == TASK_EXPLORING:
            log_and_display(get_message("usage", "explore"), turns_elapsed)
            return None
        elif task_type == TASK_CHARGING:
            log_and_display(get_message("usage", "charge"), turns_elapsed)
            return None
        elif task_type == TASK_MINING:
            log_and_display(get_message("usage", "mine"), turns_elapsed)
            return None

    return targets


def check_if_hungry_or_starving(name: str, humans: dict):
    # Returns 'Hungry' or 'Starving' if the human is at that state. Otherwise returns None.
    hunger = humans[name]["hunger"]
    state = humans[name]["state"]

    return state


def check_if_low_or_out_of_power(name: str, droids: dict):
    # Returns 'Low' or 'Out' if the droid has low or no power. Otherwise returns None.
    charge = droids[name]["charge"]

    if (1 <= charge <= IDLE_CHARGE_USAGE*LOW_CHARGE_FLAG):
        return "Low"
    elif charge <= 0:
        return "Out"
    return None