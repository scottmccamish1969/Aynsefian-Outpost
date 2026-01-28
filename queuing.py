# queuing.py
import random

from constants import TASK_EATING, TASK_CHARGING, TASK_ASSIGNED, TASK_EXAMINING, TASK_LENGTH, CHARGE_DURATION
from lore.lore_ingame import get_message
from lore.user_interface import get_confirm
from command_utils import create_task
from utils import log_and_display, check_if_hungry_or_starving, check_if_low_or_out_of_power, get_pronouns


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


def add_to_queue(character, humans, droids, turns_elapsed, task, item="", task_data=""):
    # Adds a task to the next available queue slot for a human or droid.
    # Returns True if successful, False if the queue is full.
    if character in humans:
        next_slot = get_next_available_slot(humans[character]["queue"])
    elif character in droids:
        next_slot = get_next_available_slot(droids[character]["queue"])
    else:
        return False, humans, droids

    target_queue = humans[character]["queue"] if character in humans else droids[character]["queue"]
    if next_slot:
        now_doing = humans[character]["task"].lower() if character in humans else droids[character]["task"].lower()
        target_queue[next_slot]["task"] = task
        target_queue[next_slot]["item"] = item
        if task_data != "":
            target_queue[next_slot]["task_data"] = task_data
        if item == "":
            log_and_display(get_message("queue", "queued", now_doing=now_doing, name=character, task=task), turns_elapsed)
        elif task_data == "":
            if task == TASK_ASSIGNED:
                log_and_display(get_message("queue", "queued_assign", now_doing=now_doing, name=character, item=item), turns_elapsed)
            elif task == TASK_EXAMINING:
                log_and_display(get_message("queue", "queued_examine", now_doing=now_doing, name=character, item=item), turns_elapsed)
            else:
                log_and_display(get_message("queue", "queued_with_item", now_doing=now_doing, name=character, task=task.lower(), item=item), turns_elapsed)
        else:
            log_and_display(get_message("queue", "queued_with_task_data", now_doing=now_doing, name=character, task=task, item=item), turns_elapsed)
        return True, humans, droids
    else:
        return False, humans, droids


def remove_task_from_queue(name, task_type, humans, droids):
    # Removes the first queued task of a certain type from character's queue
    is_human = name in humans
    queue = humans[name]["queue"] if is_human else droids[name]["queue"]

    for slot in ["1", "2", "3"]:
        if queue[slot]["task"] == task_type:
            queue[slot] = {"task": "", "item": ""}
            break  # Only remove the first occurrence

    return humans, droids


def get_next_task_from_queue_if_any(name, completed_msg, task_package):
    # The heart of queuing - get in line
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["turns_elapsed"]
    tasks = task_package["tasks"]
    task_number = task_package["task_number"]
    is_human = name in humans

    # Handles task transition after completing one, including queue and urgent needs.
    if is_human:
        queue = humans[name]["queue"]
    else:
        queue = droids[name]["queue"]

    # Part 1: Check for critical needs before continuing
    if is_human:
        state = check_if_hungry_or_starving(name, humans)
    else:
        state = check_if_low_or_out_of_power(name, droids)

    if is_human and state in ("Hungry", "Staving"):
        pronouns = get_pronouns(name, is_human)
        prompt = f"{name} is hungry. Do you want to feed {pronouns['p2'].lower()} before doing anything else?"
        confirmed = get_confirm(prompt, turns_elapsed, end="")
        if confirmed:
            humans, droids = remove_task_from_queue(name, TASK_EATING, humans, droids)  # remove any existing queued feed task
            # Create the feed task
            low, high = TASK_LENGTH["feed_human"]
            duration = random.randint(low, high)
            return_msg, tasks, task_number, humans, droids = create_task(tasks, task_number, TASK_EATING, humans, droids, name, is_human, duration, turns_elapsed)
            log_and_display(get_message("queue", "thanks_food", name=name, pronoun=pronouns["p1"].lower(), turns=duration), turns_elapsed)
            return "", name, task_package
        else:
            log_and_display(get_message("queue", "okay_then_food", name=name, pronoun=pronouns["p1"]), turns_elapsed)

    elif not is_human and state in ("Low", "Out"):
        prompt = f"{name} is low on power. Do you want to charge them before doing anything else?"
        confirmed = get_confirm(prompt, turns_elapsed, end='')
        if confirmed:
            humans, droids = remove_task_from_queue(name, TASK_CHARGING, humans, droids)  # remove any existing queued charge task
            # Create the charge task
            return_msg, tasks, task_number, humans, droids = create_task(tasks, task_number, TASK_CHARGING, humans, droids, name, is_human, CHARGE_DURATION, turns_elapsed)
            log_and_display(get_message("queue", "thanks_charge", name=name, turns=CHARGE_DURATION), turns_elapsed)
            return "", name, task_package
        else:
            log_and_display(get_message("queue", "okay)then_charge", name=name), turns_elapsed)

    # Part 2: Now print the completed message first
    if completed_msg:
        log_and_display(completed_msg, turns_elapsed, end='')  # We'll add the next part inline

    # Part 3: No tasks left — set to Idle 
    #    OR   We send back the next task in the queue
    if queue["1"]["task"] == "":
        is_are = "are"
        if is_human: is_are = "is"
        pronoun_str = f"{get_pronouns(name, is_human)["p1"]} {is_are}"
        log_and_display(get_message("queue", "is_now_idle", pronoun_str=pronoun_str), turns_elapsed)
        # No need to set idle as this is already done in the create_*_task() functions
        return "", name, task_package
    else:
        next_task = queue["1"].copy()
        queue["1"] = queue["2"].copy()
        queue["2"] = queue["3"].copy()
        queue["3"]["task"] = ""
        queue["3"]["item"] = ""
        task_package["item"] = next_task["item"]
        is_are = "are"
        if is_human: is_are = "is" 
        pronoun_str = f"{get_pronouns(name, is_human)["p1"]} {is_are}"
        log_and_display(get_message("queue", "is_now", pronoun_str=pronoun_str, task=next_task["task"]), turns_elapsed)
        return next_task["task"], name, task_package