# utils.py

import json
import os
import random
import difflib

from command_utils import clear_task_for_character, get_pronouns, get_task_by_worker, remove_task_by_id
from constants import (NAMES, INITIAL_GAMESTATE, CONFIG_FILE, LOG_FILE, LOG_FILE_OLD, FEMALE, MALE, GENDERS, HUNGER, LOW_CHARGE_FLAG, IDLE_CHARGE_USAGE,
    NUM_HUMANS, NUM_DROIDS, HUNGER_WARNING, TASK_ASSIGNED, TASK_PLANTING, TASK_EATING, TASK_EXPLORING, TASK_MINING, TASK_CHARGING, COMMAND_MAP)
from lore.lore_ingame import get_message
from lore.lore_story import print_orders
import lore.user_interface as ui_runtime
from lore.user_interface import get_input, msg_resource, msg_food, msg_error, msg_info, msg_power, log_and_display
from OutpostUI import get_top_bar_data
from status import display_character_summary, get_state_panel_text


def update_screen(task_package):
    #Update the screen with changes based on what happened
    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        top = get_top_bar_data(task_package)
        ui_runtime.ACTIVE_UI.set_top_stats(**top)

        state_text = get_state_panel_text(task_package)
        ui_runtime.ACTIVE_UI.set_state_text(state_text)


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
            "generated": False,
            "item": "",
            "examine_needed": "",
            "queue": empty_queue.copy()
        } for i in range(NUM_HUMANS)
    }

    droids = {
        name_pool[i + NUM_HUMANS]: {
            "charge": 0,
            "AncientCode": False,
            "task": "",
            "generated": False,
            "item": "",
            "examine_needed": "",
            "first_charge": True,
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

    # Save after initialising
    save_config(task_package)

    if first_time:
        print_orders(task_package["gamestate"])
        return None

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

        return task_package


def reset_config(task_package, context):
    task_package = context["task_package"]

    # Resets the config file as per the user's request
    msg_info(get_message("reset", "start"), 0, end='')

    # Rename current log file if it exists
    if os.path.exists(LOG_FILE):
        os.replace(LOG_FILE, LOG_FILE_OLD)

    first_time = False
    task_package = initialise_outpost(first_time)

    # Update the gui screen (if using) and save to config file
    if task_package:
        if ui_runtime.GUI_PENDING:
            update_screen(task_package)

    msg_info(get_message("reset", "done"), 0)


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


def process_hunger_status(name, task_package, warn=True):
    # Check if a human is advancing in hunger
    human = task_package["humans"][name]
    current_state = human["state"]
    hunger = human["hunger"]
    turns_elapsed = task_package["counters"]["turns"]

    # Helper: set hunger band if just fed (this may be clunky, but visually I need to SEE it)
    def reset_hunger_band(hunger_value, current_state):
        hungry_low = 0
        starving_low = 0
        near_death_low = 0
        correct_state = "Okay"
        for band, (low, high) in HUNGER.items():
            if band == "Hungry" and current_state == "Hungry":
                hungry_low = low
                if hunger_value < hungry_low:
                    correct_state = "Okay"
            elif band == "Starving" and current_state == "Starving":
                starving_low = low
                if hunger_value < starving_low:
                    correct_state = "Hungry"
                    if hunger_value < hungry_low:
                        correct_state = "Okay"
            elif band == "Near Death" and current_state == "Near Death":
                near_death_low = low
                if hunger_value < near_death_low:
                    correct_state = "Starving"
                    if hunger_value < starving_low:
                        correct_state = "Hungry"
                    if hunger_value < hungry_low:
                        correct_state = "Okay"

        return correct_state

    # Helper: determine hunger band
    def get_hunger_band(hunger_value, current_state):
        for band, (low, high) in HUNGER.items():
            if low <= hunger_value <= high:
                return band
        return current_state
    
    # If the human's state is greater than the lower band for their hunger level, nothing to do, so exit
    if get_hunger_band(hunger, current_state) == current_state:
        return task_package

    # --- Recalculate band if just fed ---
    human["state"] = reset_hunger_band(hunger, current_state)
    new_band = get_hunger_band(hunger, current_state)

    # --- DEATH (always deterministic) ---
    if new_band == "Deceased":
        if current_state != "Deceased":
            if warn:
                msg_food(get_message("hunger", "deceased", name=name), turns_elapsed, tone="warn")
            human["state"] = "Deceased"
        return task_package
    
    # If they are currently eating, don't check and don't warn, just exit
    if human["task"] == TASK_EATING:
        return task_package

    # --- WARNING PHASES ---
    if current_state != "Okay":
        for warning_state, warning_turn in HUNGER_WARNING.items():
            if hunger == warning_turn and current_state != warning_state:
                pronouns = get_pronouns(name, True)
                if warn:
                    msg_food(get_message("hunger", f"{warning_state.lower()}_warning", pronoun=pronouns["p1"], name=name),
                            turns_elapsed, tone="warn")

    # --- NO CHANGE ---
    if new_band == current_state:
        return task_package

    low, high = HUNGER[new_band]

    # --- FORCED TRANSITION (upper bound) ---
    if hunger >= high:
        human["state"] = new_band
        if new_band != "Okay":
            pronouns = get_pronouns(name, True)
            if warn:
                msg_food(get_message("hunger", new_band, pronoun=pronouns["p2"].lower(), name=name), 
                        turns_elapsed, tone="warn")
        return task_package

    # --- PROBABILISTIC TRANSITION (lower bound only) ---
    if hunger >= low and hunger < high:
        if random.random() < 0.5:
            human["state"] = new_band
            pronouns = get_pronouns(name, True)
            if warn:
                msg_food(get_message("hunger", new_band, pronoun=pronouns["p2"].lower(), name=name), turns_elapsed, tone="warn")

            if new_band == "Starving":
                task_package = interrupt_task_if_starving(name, human, task_package)

    return task_package


def interrupt_task_if_starving(name, human, task_package):
    tasks = task_package["tasks"]
    resources = task_package["resources"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    if human["state"] != "Starving":
        return task_package  # nothing to do

    task_id, task = get_task_by_worker(tasks, name)
    if not task:
        return task_package  # idle anyway
    
    task_type = task["type"].lower()

    # If they are eating, all good
    if task_type == TASK_EATING.lower():
        return task_package

    msg_food(f"{name} cannot continue {task_type}. Hunger overwhelms focus and strength. The task has been abandoned.", 
             turns_elapsed, tone="warn")

    if task_type == TASK_PLANTING.lower():
        hydro = next((r for r in resources if r["name"] == "HydroponicsRoom"), None)
            # Free the bed
        bed = {}
        for b in hydro["beds"]:
            if b["reserved_by"] == name:
                b["occupied"] = False
                b["crop_id"] = None
                b["name"] = ""
                b["reserved_by"] = ""

    remove_task_by_id(task_id, task_package)    # Remove the old task and clear the character's status

    return task_package


def can_character_act(character, task_name, humans, droids, turns_elapsed):
    # Generic checks to see if we can use this character (human or droid)

    target = get_best_match(character, list(humans.keys()) + list(droids.keys()))
    if not target:
        msg_error(get_message("error", "unknown_worker", name=character, task=task_name), turns_elapsed)
        return False, False, target

    is_human = target in humans

    # ---- Pre-condition checks ----
    if is_human and humans[target]["state"] in ["Starving", "Near Death", "Deceased"]:
        pronouns = get_pronouns(target, True)
        if task_name == TASK_ASSIGNED:
            msg_food(
                get_message("error", "too_hungry_for_assign", name=target, task=task_name.lower(), pronoun=pronouns["p1"]),
                turns_elapsed, tone="error")
        else:
            msg_food(
                get_message("error", "too_hungry", name=target, task=task_name.lower(), pronoun=pronouns["p1"]),
                turns_elapsed, tone="error")
        return False, is_human, target

    if not is_human:
        charge = droids[target]["charge"]
        current_task = droids[target]["task"]
        
        # Droids with 0 charge can only continue if they are currently charging
        if charge <= 0 and current_task != TASK_CHARGING:
            if task_name == TASK_ASSIGNED:
                msg_power(get_message("error", "no_power_for_assign", name=target, task=task_name.lower()), turns_elapsed, tone="error")
            else:
                msg_power(get_message("error", "no_power", name=target, task=task_name.lower()), turns_elapsed, tone="error")
            return False, is_human, target

    # If the character is idle (even if their queue is full) - they can act (maybe 'manage' was used to delete their current task)
    if is_human:
        if humans[target]["task"] == "":
            return True, is_human, target
    else:
        if droids[target]["task"] == "":
            return True, is_human, target

    # Check if their queue is full - can't act if that is the situation
    if is_human:
        queue = humans[target]["queue"]
    else:
        queue = droids[target]["queue"]
    queue_full = True
    for slot in ["1", "2", "3"]:
        if queue[slot]["task"] == "":
            queue_full = False
    if queue_full:
        msg_info(get_message("queue", "queue_full", character=target, task=task_name.lower()), turns_elapsed)
        return False, is_human, target

    return True, is_human, target


def check_shield_state(task_package):
    # Centralised synthesis check of shield state based on current droid and resource status

    shieldstate = task_package["shieldstate"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]

    # Find the shield and check if it exists
    shield = next((r for r in resources if r["name"] == "CloakingShield"), None)

    if shield:
        power_supply = next((r for r in resources if r["name"] == "PowerSupply"), None)
        if power_supply is not None and power_supply["amount"] <= 0:
            msg_power(get_message("shield", "no_power"), turns_elapsed, tone="warn")
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


def parse_integer_answer(answer, min_value=None, max_value=None):
    try:
        value = int(answer)
    except (TypeError, ValueError):
        return None, "invalid"

    if min_value is not None and value < min_value:
        return None, "too_low"

    if max_value is not None and value > max_value:
        return None, "too_high"

    return value, ""


def set_examine_needed_after_explore(name, task_package):
    # Stores the examine-needed item for a character after an explore task,
    # if feeding or charging is about to happen.
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    item = task_package.get("item", "")
    is_human = name in humans

    if is_human:
        humans[name]["examine_needed"] = item
        pronouns = get_pronouns(name, is_human)
        msg_resource(get_message("examine", "pause_eating", name=name, pronoun1=pronouns["p1"].lower(), pronoun2=pronouns["p2"].lower(), item=item), turns_elapsed)
    else:
        droids[name]["examine_needed"] = item
        msg_resource(get_message("examine", "pause_charging", name=name, item=item), turns_elapsed)
    return task_package


def clear_examine_needed_flag(name, task_package):
    # Clears the examine_needed flag for a character.
    humans = task_package["humans"]
    droids = task_package["droids"]

    if name in humans:
        humans[name]["examine_needed"] = None
    elif name in droids:
        droids[name]["examine_needed"] = None
    return task_package