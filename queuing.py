# queuing.py
import random
import math

from command_utils import create_task, get_pronouns, set_task_status_for_character
from constants import (TASK_EATING, TASK_CHARGING, TASK_EXPLORING, TASK_ASSIGNED, TASK_EXAMINING, TASK_PLANTING, TASK_MINING, 
                       TASK_REAPING, TASK_TOWING_DROID, TASK_REFUELING, TASK_LENGTH, CHARGE_DURATION, LOW_CHARGE_FLAG, 
                       IDLE_CHARGE_USAGE, TOW_TASK_LENGTH, NORMAL_MEAL_MULTIPLIER, EMERGENCY_MEAL_MULTIPLIER, ONE_DAY_HUNGRY,
                       CommandOutcome)
from lore.lore_ingame import get_message
import lore.user_interface as ui_runtime
from lore.user_interface import msg_food, msg_power, msg_error,  msg_info, msg_explore, msg_mine, msg_plant, msg_resource
from utils import clear_examine_needed_flag, can_provide_a_meal, get_best_match

def is_idle(name, humans, droids):
    if name in humans:
        return humans[name]["task"] == ""
    if name in droids:
        return droids[name]["task"] == ""
    return False


def get_next_available_slot(queue):
    # Returns the key of the next available slot (1, 2, or 3) or None if full.
    for slot in ["1", "2", "3"]:
        if queue[slot]["task"] == "":
            return slot
    return None


def add_to_queue(name_input, humans, droids, turns_elapsed, task_type, item="", task_data=None):
    if task_data is None:
        task_data = {}

    # Adds a task to the next available queue slot for a human or droid.
    # Returns True if successful, False if the queue is full.
    name = get_best_match(name_input, list(humans.keys()) + list(droids.keys()))
    if name in humans:
        next_slot = get_next_available_slot(humans[name]["queue"])
    elif name in droids:
        next_slot = get_next_available_slot(droids[name]["queue"])
    else:
        msg_error(get_message("queue", "not_queued_error", name=name, task=task_type), turns_elapsed)
        return humans, droids
    
    # Check if this has already been added if it is:  EATING, CHARGING, ASSIGNED TO
    # They can do multiples of:  EXPLORE, EXAMINE, MINE, PLANT, REAP, REFUEL
    if task_type in (TASK_EATING, TASK_CHARGING, TASK_ASSIGNED):
        is_human = name in humans
        queue = humans[name]["queue"] if is_human else droids[name]["queue"]
        for slot in ["1", "2", "3"]:
            if queue[slot]["task"] == task_type:
                msg_info(get_message("queue", "not_queued_already_queued", name=name, task=task_type), turns_elapsed)
                return humans, droids

    # Queue the task
    target_queue = humans[name]["queue"] if name in humans else droids[name]["queue"]
    if next_slot:
        now_doing = humans[name]["task"].lower() if name in humans else droids[name]["task"].lower()
        target_queue[next_slot]["task"] = task_type
        target_queue[next_slot]["item"] = item
        if task_data != {}:
            target_queue[next_slot]["task_data"] = task_data
        if item == "":
            if task_type == TASK_EATING or task_type == TASK_REAPING:
                msg_food(get_message("queue", "queued", now_doing=now_doing, name=name, task=task_type), turns_elapsed)
            elif task_type in (TASK_CHARGING, TASK_REFUELING, TASK_TOWING_DROID):
                msg_power(get_message("queue", "queued", now_doing=now_doing, name=name, task=task_type), turns_elapsed)
            elif task_type == TASK_EXPLORING:
                msg_explore(get_message("queue", "queued", now_doing=now_doing, name=name, task=task_type), turns_elapsed)
            elif task_type == TASK_EXAMINING:
                msg_resource(get_message("queue", "queued", now_doing=now_doing, name=name, task=task_type), turns_elapsed)
            elif task_type == TASK_PLANTING:
                msg_plant(get_message("queue", "queued", now_doing=now_doing, name=name, task=task_type), turns_elapsed)
            elif task_type == TASK_MINING:
                msg_mine(get_message("queue", "queued", now_doing=now_doing, name=name, task=task_type), turns_elapsed)
            else:
                msg_info(get_message("queue", "queued", now_doing=now_doing, name=name, task=task_type), turns_elapsed)
        elif task_data == "":
            if task_type == TASK_ASSIGNED:
                msg_resource(get_message("queue", "queued_assign", now_doing=now_doing, name=name, item=item), turns_elapsed)
            elif task_type == TASK_EXAMINING:
                msg_resource(get_message("queue", "queued_examine", now_doing=now_doing, name=name, item=item), turns_elapsed)
            else:
                msg_info(get_message("queue", "queued_with_item", now_doing=now_doing, name=name, task=task_type.lower(), item=item), turns_elapsed)
        else:
            msg_info(get_message("queue", "queued_with_task_data", now_doing=now_doing, name=name, task=task_type, item=item), turns_elapsed)
        return humans, droids
    else:
        msg_info(get_message("queue", "not_queued", name=name, task=task_type), turns_elapsed)
        return humans, droids


def get_next_task_from_queue_if_any(name, task_package):
    # Simply inspect the next queued task for a character.

    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    queue_result = {
        "next_action": "",
        "character": name,
        "task_data": {},
        "item_name": "",
    }

    # Resolve the supplied name to the canonical character name.
    human_name = next((key for key in humans if key.casefold() == name.casefold()), None)
    droid_name = next((key for key in droids if key.casefold() == name.casefold()), None)

    if human_name is not None:
        name = human_name
        character = humans[name]

    elif droid_name is not None:
        name = droid_name
        character = droids[name]

    else:
        msg_error(get_message("error", "character_not_found", name=name), turns_elapsed)
        return queue_result, task_package

    queue_result["character"] = name

    queue = character["queue"]

    # Nothing queued.
    if queue["1"]["task"] == "":
        return queue_result, task_package

    # IMPORTANT:
    # Peek at the queued task only.
    # Do not remove it until we know it can actually start.
    next_task = queue["1"]

    queue_result["next_action"] = next_task.get("task", "")
    queue_result["task_data"] = next_task.get("task_data", {})
    queue_result["item_name"] = next_task.get("item_name", "")

    return queue_result, task_package


def delete_task_from_queue(name, task_type, humans, droids):
    # Removes the first queued task of a certain type from character's queue
    is_human = name in humans
    queue = humans[name]["queue"] if is_human else droids[name]["queue"]

    for slot in ["1", "2", "3"]:
        if queue[slot]["task"] == task_type:
            queue[slot] = {"task": "", "item": ""}
            break  # Only remove the first occurrence

    # Now reorder the queue if needed
    reorder = False
    if queue["1"]["task"] == "":
        queue["1"] = queue["2"].copy()
        queue["2"] = queue["3"].copy()
        reorder = True
    if queue["2"]["task"] == "":    # Unlikely that both 1 and 2 will be vacant with 3 occupied, but do it anyway
        queue["2"] = queue["3"].copy()
        reorder = True
    if reorder:
        queue["3"] = {"task": "", "item": ""}  # Just to be sure

    return humans, droids


def remove_first_queued_task(name, task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]

    if name in humans:
        queue = humans[name]["queue"]
    elif name in droids:
        queue = droids[name]["queue"]
    else:
        return task_package

    queue["1"] = queue["2"].copy()
    queue["2"] = queue["3"].copy()
    queue["3"] = {
        "task": "",
        "item": "",
        "item_name": "",
        "task_data": {}
    }

    return task_package


def resume_delayed_examine_processing(answer, context):
    task_package = context["task_package"]
    name = context["name"]
    item_to_examine = context["item"]
    turns_elapsed = task_package["counters"]["turns"]

    if answer.lower() in ("y", "yes"):
        task_package["item"] = item_to_examine
        restart_examine(name, task_package, item_name=item_to_examine)
    else:
        msg_resource(get_message("examine", "aborted", target=name, item=item_to_examine), turns_elapsed)
        # From here, they should just pick up the next queued task. We'll see.

    # Either way, clear the flag
    task_package = clear_examine_needed_flag(name, task_package)
    
    return CommandOutcome.SUCCESS, task_package


# Send back the first droid that is out of charge or has been flagged as needing a tow. If none, return an empty string.
def get_out_of_charge_droid(droids):
    for name, d in droids.items():
        if d.get("charge", 0) == 0 and not d.get("first_charge", False):
            if not d.get("tow_declined", False):
                return name
        if d.get("needs_tow", False):
            return name
    return ""


def get_character_status(name, humans, droids):
    # Helper to return hunger or charge state
    status = ""
    if name in humans:
        status = humans[name]["state"]
    elif name in droids:
        if droids[name]["charge"] <= LOW_CHARGE_FLAG*IDLE_CHARGE_USAGE:
            status = "Low"
        elif droids[name]["charge"] <= 0:
            status = "Out"
        else:
            status = "Okay"
    return status


def feed_hungry_human(name, task_package):
    from planting import select_and_reserve_meal

    # Automatically feeds a hungry human, removing any queued feeding tasks first.
    # Returns updated task_package and message if action taken, else None.
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    return_msg = ""
    task_data = {}
    multiplier = NORMAL_MEAL_MULTIPLIER
    hunger_reduction = 0

    # Check first that we have food
    if not can_provide_a_meal(resources):
        return_msg = get_message("feed", "food_all_used_up", person_name=name)
        return return_msg, task_package 

    # We are okay to continue and feed the human if they're wanting or needing food
    state = get_character_status(name, humans, droids)
    if state in ("Hungry", "Starving", "NearDeath"):
        # Reserve the food
        if humans[name]["state"] in ("Starving", "Near Death"):
            multiplier = EMERGENCY_MEAL_MULTIPLIER
        else:
            multiplier = NORMAL_MEAL_MULTIPLIER
        hunger_reduction = math.ceil(multiplier * ONE_DAY_HUNGRY)
        task_data, task_package = select_and_reserve_meal(name, multiplier, hunger_reduction, task_package)
        if not task_data:
            return_msg = get_message("feed", "unable_to_reserve_food", name=name)
            msg_food(return_msg, turns_elapsed, tone="warn")
            return task_package

        # Now create the task
        task_length_key = ("feed_human_emergency" if multiplier == EMERGENCY_MEAL_MULTIPLIER else "feed_human")
        low, high = TASK_LENGTH[task_length_key]
        duration = random.randint(low, high)
        task_type = TASK_EATING
        humans[name]["awaiting_food"] = False
        humans[name]["food_wait_declined"] = False
        return_msg, task_package = create_task(name, task_type, duration, task_package, task_data=task_data)

        pronouns = get_pronouns(name, is_human=True)
        if duration-1 == 1:
            turn_msg = "1 turn"
        else:
            turn_msg = f"{duration-1} turns"
        return_msg = get_message("queue", "auto_food", name=name, pronoun1=pronouns["p3"].lower(), pronoun2=pronouns["p1"], turn_msg=turn_msg)
        
        item_name = ""
        set_task_status_for_character(name, task_type, item_name, humans, droids, task_package["counters"]["turns"])

    msg_food(return_msg, turns_elapsed, stamp=False)
    return task_package


def restart_examine(name, task_package, item_name=""):
    # Restart the examine task if it was previously paused (to eat or charge)
    task_type = TASK_EXAMINING
    resources = task_package["resources"]
    humans = task_package["humans"]
    turns_elapsed = task_package["counters"]["turns"]
    
    def set_task_length(task_type):
        low, high = TASK_LENGTH[task_type]
        return random.randint(low, high)

    item = next((r for r in resources if r["name"] == item_name), None)
    if not item:
        msg_resource(get_message("examine", "not_found", item=item_name), turns_elapsed)
        return task_package

    # Set the examine time, which is *quicker* for droids
    duration = 0
    if name in humans:
        duration = item.get("examine_turns", 0) + set_task_length("examine_human")
    else:
        duration = item.get("examine_turns", 0) + set_task_length("examine_droid")

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package, item_name=item_name)
    msg_resource(return_msg, turns_elapsed)

    # Clear the flag
    task_package = clear_examine_needed_flag(name,task_package)

    return task_package