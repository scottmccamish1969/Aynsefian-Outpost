# queuing.py
import random

from command_utils import create_task
from constants import (TASK_EATING, TASK_CHARGING, TASK_EXPLORING, TASK_ASSIGNED, TASK_EXAMINING, TASK_PLANTING, TASK_MINING, TASK_REAPING, TASK_TOWING_DROID,
                       TASK_REFUELING, TASK_LENGTH, CHARGE_DURATION, LOW_CHARGE_FLAG, IDLE_CHARGE_USAGE, TOW_TASK_LENGTH)
from lore.lore_ingame import get_message
import lore.user_interface as ui_runtime
from lore.user_interface import (get_input, msg_food, msg_power, msg_error,  msg_info, msg_explore, msg_crystal, msg_mine, msg_plant, msg_resource,
                                msg_shield, msg_warn, log_and_display)
from utils import get_pronouns, clear_examine_needed_flag, process_hunger_status

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


def add_to_queue(name, humans, droids, turns_elapsed, task_type, item="", task_data=""):
    # Adds a task to the next available queue slot for a human or droid.
    # Returns True if successful, False if the queue is full.
    if name in humans:
        next_slot = get_next_available_slot(humans[name]["queue"])
    elif name in droids:
        next_slot = get_next_available_slot(droids[name]["queue"])
    else:
        msg_info(get_message("queue", "not_queued_error", name=name, task=task_type), turns_elapsed)
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
        if task_data != "":
            target_queue[next_slot]["task_data"] = task_data
        if item == "":
            if task_type == TASK_EATING:
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


def remove_task_from_queue(name, task_type, humans, droids):
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


def get_next_task_from_queue_if_any(name, task_package):
    # The heart of queuing - get in line
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    is_human = name in humans
    next_task_name = ""
    awaiting_input = False

    # Check and potentially reset hunger status if this is a human
    if is_human:
        task_package = process_hunger_status(name, task_package, warn=False)

    # If the character is hungry or low on charge, pause normal queue handling
    # NOTE: If a droid is "Out" of charge, they must be towed by a human
    state = get_character_status(name, humans, droids)

    if state in ("Hungry", "Starving", "Near Death", "Low"):
        if is_human:
            # They may already be eating after an explore with a paused examine
            if humans[name]["task"] == TASK_EATING:
                return next_task_name, name, awaiting_input, task_package

            humans[name]["generated"] = True
            return_msg, task_package = do_auto_feed(name, task_package)

            if return_msg != "":
                msg_food(return_msg, turns_elapsed, stamp=False)

        else:
            # They may already be charging after an explore with a paused examine
            if droids[name]["task"] == TASK_CHARGING:
                return next_task_name, name, awaiting_input, task_package

            droids[name]["generated"] = True
            return_msg, task_package = do_auto_charge(name, task_package)

            if return_msg != "":
                msg_power(return_msg, turns_elapsed, end='\n', stamp=False)

        if return_msg == "":
            msg_error(get_message("error", "invalid_auto_msg", name=name), turns_elapsed)

        return next_task_name, name, awaiting_input, task_package

    # If it's a human, they can tow a droid if one has run out of charge
    if is_human:
        droid_at_zero = get_out_of_charge_droid(droids)

        if droid_at_zero != "":
            if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
                ui_runtime.ACTIVE_UI.set_pending_question(
                    callback=resume_towing_if_human_available,
                    context={
                        "task_package": task_package,
                        "name": name,
                        "droid_at_zero": droid_at_zero,
                    }
                )

            answer = get_input("input", "zero_charge", turns_elapsed, droid=droid_at_zero)

            if answer and answer == ui_runtime.GUI_PENDING:
                return None

            # CLI path, or non-pending path
            return resume_towing_if_human_available(answer, {"task_package": task_package, "name": name, "droid_at_zero": droid_at_zero,})

    # No towing interruption needed, so continue normally
    return continue_get_next_task_from_queue_if_any(name, task_package)


def continue_get_next_task_from_queue_if_any(name, task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    is_human = name in humans
    next_task_name = ""
    awaiting_input = False

    # Check to see if there is an Examine task that was paused due to auto-feed or auto-charge
    if is_human:
        examine_is_needed = humans[name]["examine_needed"]
        item_to_examine = humans[name]["examine_needed"]
    else:
        examine_is_needed = droids[name]["examine_needed"]
        item_to_examine = droids[name]["examine_needed"]

    if examine_is_needed:
        pronouns = get_pronouns(name, is_human)
        log_and_display("", turns_elapsed, stamp=None)

        if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
            ui_runtime.ACTIVE_UI.set_pending_question(
                callback=resume_delayed_examine_processing,
                context={
                    "task_package": task_package,
                    "name": name,
                    "item": item_to_examine,
                    "next_action": next_task_name,
                }
            )

        answer = get_input("input", "resume_examine", turns_elapsed, name=name, pronoun1=pronouns["p1"].lower(), pronoun2=pronouns["p2"].lower(), item=item_to_examine)

        if answer and answer == ui_runtime.GUI_PENDING:
            awaiting_input = True
        else:
            msg_error(get_message("error", "no_CLI"), turns_elapsed)

        return next_task_name, name, awaiting_input, task_package

    # We are able to continue with the next queued task
    queue = humans[name]["queue"] if is_human else droids[name]["queue"]

    # Set the generated flag appropriately
    if is_human:
        humans[name]["generated"] = True
    else:
        droids[name]["generated"] = True

    # No tasks left: Idle
    if queue["1"]["task"] == "":
        is_are = "are" if not is_human else "is"
        pronoun_str = f"{get_pronouns(name, is_human)['p1']} {is_are}"
        msg_info(
            get_message("queue", "is_now_idle", pronoun_str=pronoun_str),
            turns_elapsed,
            stamp=False
        )
        return next_task_name, name, awaiting_input, task_package

    # Shift queue
    next_task = queue["1"].copy()
    next_task_name = next_task["task"]

    queue["1"] = queue["2"].copy()
    queue["2"] = queue["3"].copy()
    queue["3"] = {"task": "", "item": ""}

    task_package["item"] = next_task["item"]

    task_data = next_task.get("task_data", "")
    if task_data:
        task_package["task_data"] = task_data

    is_are = "are" if not is_human else "is"
    pronoun_str = f"{get_pronouns(name, is_human)['p1']} {is_are}"

    if next_task_name == TASK_EATING:
        msg_food(get_message("queue", "is_now", pronoun_str=pronoun_str, task=next_task["task"]), turns_elapsed, stamp=False)

    elif next_task_name in (TASK_CHARGING, TASK_REFUELING, TASK_TOWING_DROID):
        msg_power(get_message("queue", "is_now", pronoun_str=pronoun_str, task=next_task["task"]), turns_elapsed, stamp=False)

    elif next_task_name == TASK_EXPLORING:
        msg_explore(get_message("queue", "is_now", pronoun_str=pronoun_str, task=next_task["task"]), turns_elapsed, stamp=False)

    elif next_task_name == TASK_EXAMINING:
        msg_resource(get_message("queue", "is_now", pronoun_str=pronoun_str, task=next_task["task"]), turns_elapsed, stamp=False)

    elif next_task_name == TASK_PLANTING:
        msg_plant(get_message("queue", "is_now", pronoun_str=pronoun_str, task=next_task["task"]), turns_elapsed, stamp=False)

    elif next_task_name == TASK_MINING:
        msg_mine(get_message("queue", "is_now", pronoun_str=pronoun_str, task=next_task["task"]), turns_elapsed, stamp=False)

    else:
        msg_info(get_message("queue", "is_now", pronoun_str=pronoun_str, task=next_task["task"]), turns_elapsed, stamp=False)
                 
    return next_task_name, name, awaiting_input, task_package


def resume_delayed_examine_processing(answer, context):
    task_package = context["task_package"]
    name = context["name"]
    item_to_examine = context["item"]
    next_action = context["next_action"]
    turns_elapsed = task_package["counters"]["turns"]

    if answer and answer.lower() in ("y", "yes"):
        task_package["item"] = item_to_examine
        restart_examine(name, task_package)
    else:
        msg_resource(get_message("examine", "aborted", target=name, item=item_to_examine), turns_elapsed)
        # From here, they should just pick up the next queued task. We'll see.

    # Either way, clear the flag
    task_package = clear_examine_needed_flag(name, task_package)
    
    return task_package


# Send back the first droid that is out of charge and this is not the first time they are being charged
def get_out_of_charge_droid(droids):
    for name, d in droids.items():
        if d.get("charge", 0) == 0 and not d.get("first_charge", False):
            return name
    return ""


def resume_towing_if_human_available(answer, context):
    task_package = context["task_package"]
    name = context["name"]
    droid_at_zero = context["droid_at_zero"]

    humans = task_package["humans"]
    turns_elapsed = task_package["counters"]["turns"]
    awaiting_input = False
    next_task_name = ""

    if answer and answer and answer.lower() in ("y", "yes"):
        duration = TOW_TASK_LENGTH
        task_type = TASK_TOWING_DROID

        msg_power(get_message("charge", "towing", name=name, droid_being_towed=droid_at_zero, turns=duration), turns_elapsed)

        # Create the tow task
        task_package["item"] = droid_at_zero  # In this case the item is actually the droid
        humans[name]["generated"] = True

        return_msg, task_package = create_task(name, task_type, duration, task_package)

        if return_msg != "":
            msg_power(return_msg, turns_elapsed)

        return next_task_name, name, awaiting_input, task_package

    # Player refused to tow the powerless droid.
    # Technically allowed. Morally entered into the ancient ledger.
    return continue_get_next_task_from_queue_if_any(name, task_package)


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


def do_auto_feed(name, task_package):
    # Automatically feeds a hungry human, removing any queued feeding tasks first.
    # Returns updated task_package and message if action taken, else None.

    humans = task_package["humans"]
    droids = task_package["droids"]
    return_msg = ""

    state = get_character_status(name, humans, droids)
    if state in ("Hungry", "Starving", "Near Death"):
        # If the player already has a queue 'feed' task, remove it
        humans, droids = remove_task_from_queue(name, TASK_EATING, humans, droids)
        task_package["humans"] = humans
        task_package["droids"] = droids

        low, high = TASK_LENGTH["feed_human"]
        duration = random.randint(low, high)
        task_type = TASK_EATING
        return_msg, task_package = create_task(name, task_type, duration, task_package)

        pronouns = get_pronouns(name, is_human=True)
        if duration-1 == 1:
            turn_msg = "1 turn"
        else:
            turn_msg = f"{duration-1} turns"
        return_msg = get_message("queue", "auto_food", name=name, pronoun1=pronouns["p3"].lower(), pronoun2=pronouns["p1"], turn_msg=turn_msg)

    return return_msg, task_package


def do_auto_charge(name, task_package):
    # Automatically charges a low-power droid, removing any queued charge tasks first.
    # Returns updated task_package and message if action taken, else None.

    droids = task_package["droids"]
    humans = task_package["humans"]
    return_msg = ""

    state = get_character_status(name, droids, droids)
    if state == "Low":      # A droid out of charge must be towed by a human
        droids, humans = remove_task_from_queue(name, TASK_CHARGING, droids, humans)
        task_package["droids"] = droids
        task_package["humans"] = humans

        duration = CHARGE_DURATION
        task_type = TASK_CHARGING
        return_msg, task_package = create_task(name, task_type, duration, task_package)

        if duration-1 == 1:
            turn_msg = "1 turn"
        else:
            turn_msg = f"{duration-1} turns"
        return_msg = get_message("queue", "auto_charge", name=name, turn_msg=turn_msg)

    return return_msg, task_package


def restart_examine(name, task_package):
    # Restart the examine task if it was previously paused (to eat or charge)
    task_type = TASK_EXAMINING
    resources = task_package["resources"]
    item_name = task_package["item"]
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
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    msg_resource(return_msg, turns_elapsed)

    # Clear the flag
    task_package = clear_examine_needed_flag(name,task_package)

    return task_package