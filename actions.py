#actions.py - separating out the actions that can be taken by characters in the game, to keep commands.py cleaner and more focused on command handling

from commands import (initiate_explore_task, initiate_feed_task, initiate_charge_task, initiate_examine_task, initiate_plant_task, initiate_reap_task,
                      initiate_mine_task, initiate_refuel_task, handle_assign_command)
from constants import TASK_EATING, TASK_CHARGING, TASK_EXPLORING, TASK_PLANTING, TASK_EXAMINING, TASK_REAPING, TASK_MINING, TASK_ASSIGNED, TASK_REFUELING
from lore.user_interface import msg_error
from lore.lore_ingame import get_message
from queuing import get_next_task_from_queue_if_any

def handle_immediate_or_queued_task(action, qualifier, task_package):
    valid_command = True
    turns_elapsed = task_package["counters"]["turns"]

    # ---- TASK DISPATCH ----
    if action == "explore" or action == TASK_EXPLORING:
        valid_command, task_package = initiate_explore_task(qualifier, task_package)

    elif action == "feed" or action == TASK_EATING:
        valid_command, task_package = initiate_feed_task(qualifier, task_package)

    elif action == "charge" or action == TASK_CHARGING:
        valid_command, task_package = initiate_charge_task(qualifier, task_package)

    elif action == "examine" or action == TASK_EXAMINING:
        valid_command, task_package = initiate_examine_task(qualifier, task_package)

    elif action == "plant" or action == TASK_PLANTING:
        valid_command, task_package = initiate_plant_task(qualifier, task_package)

    elif action == "reap" or action == TASK_REAPING:
        valid_command, task_package = initiate_reap_task(qualifier, task_package)

    elif action == "mine" or action == TASK_MINING:
        valid_command, task_package = initiate_mine_task(qualifier, task_package)

    elif action == "refuel" or action == TASK_REFUELING:
        valid_command, task_package = initiate_refuel_task(qualifier, task_package)

    elif action == "assign" or action == TASK_ASSIGNED:
        valid_command, task_package = handle_assign_command(qualifier, task_package)

    else:
        msg_error(get_message("error", "unknown_command", command=action), turns_elapsed)
        valid_command = False

    return valid_command, task_package


def start_next_queued_task_for_character(name, task_package):
    # Pull and initiate the next queued task for a character.
    
    awaiting_input = False

    next_action, character, awaiting_input, task_package = (
        get_next_task_from_queue_if_any(name, task_package)
    )

    if awaiting_input:
        return True, task_package

    if next_action:
        valid_command, task_package = handle_immediate_or_queued_task(next_action, character, task_package)

        # A queued task should normally be valid, but retain the result
        # for debugging rather than assuming silently.
        if not valid_command:
            return False, task_package

    return False, task_package