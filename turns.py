# turns.py

import random
from datetime import datetime

from commands import handle_immediate_or_queued_task
from command_utils import handle_read_command, handle_manage_command
from constants import NUM_HUMANS
from endgame import check_endgame, handle_game_over_loop
from lore.lore_ingame import get_message, handle_help_command
from lore.lore_story import get_story_message
import lore.user_interface as ui_runtime
from lore.user_interface import msg_story, msg_error
from OutpostUI import get_state_panel_text, get_top_bar_data
from planting import update_crop_growth
from resources import decrease_droid_charge
from status import print_status, handle_list_command
from tasks import advance_tasks
from utils import is_command_enabled, load_config, process_hunger_status, check_shield_state, reset_config, save_config, update_screen


def process_turn(command, task_package):
    tokens = command.strip().split()
    if not tokens:
        return False, task_package

    action = tokens[0]
    qualifier = tokens[1] if len(tokens) > 1 else None
    dock_a_turn = False
    valid_command = True

    turns_elapsed = task_package["counters"]["turns"]
    gamestate = task_package["gamestate"]

    # Restrict commands if game is over
    if gamestate.get("game_over", False) and action not in ["status", "help", "reset", "quit"]:
        msg_story(get_story_message("endgame", "restart"), turns_elapsed)
        return True, task_package

    # Unknown command
    if action not in gamestate:
        msg_error(get_message("error", "unknown_command", command=action), turns_elapsed)
        return False, task_package

    # Command not yet unlocked
    if not is_command_enabled(action, gamestate):
        msg_error(get_message("error", "can't_do_that_yet", command=command), turns_elapsed)
        return False, task_package

    # Handle known commands
    if action == "next":
        dock_a_turn = True

    elif action == "read":
        handle_read_command(turns_elapsed, qualifier)

    elif action == "manage":
        task_package = handle_manage_command(qualifier, task_package)

    elif action == "list":
        handle_list_command(qualifier, task_package)

    elif action == "status":
        task_package = load_config()
        print_status(task_package)

    elif action == "help":
        handle_help_command(task_package, qualifier=qualifier, gamestate=gamestate)

    elif action == "quit":
        msg_story(get_message("quit", "final"), turns_elapsed)
        msg_story(f"Session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", turns_elapsed)
        exit(0)

    elif action == "reset":
        reset_config(task_package)
        task_package = load_config()

    else:
        dock_a_turn, task_package = handle_immediate_or_queued_task(action, qualifier,  task_package)

    return dock_a_turn, task_package


def print_day_message(turns_elapsed, droids):
    # Prints a flavour message at the start of each new day.
    # Pulls from lore["daymessage"] if present, else uses generic.
    day = turns_elapsed // 10
    day_words = {
        1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
        6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"
    }

    day_str = ""
    day_key = day_words.get(day, "generic")
    if day_key == "generic":
        day_str = str(day)
    lore = get_story_message("daymessage", day_key, day=day_str)

    if not lore:
        lore = get_story_message("daymessage", "generic")

    if isinstance(lore, list):
        message = random.choice(lore)
    else:
        message = lore

    # Substitute day variable if present
    if "{day}" in message:
        message = message.format(day)

    msg_story("-"*60, turns_elapsed)
    msg_story(f"End of Day {day}: "+message, turns_elapsed)

    # Add extra narrative hint if droids still offline
    droids_online = False
    for dc in droids.values():
        if dc["charge"] > 0:
            droids_online = True
            break

    if day == 3 and not droids_online:
        msg_story(get_story_message("no_droids", "day_3"), turns_elapsed)

    elif day == 6 and not droids_online:
        msg_story(get_story_message("no_droids", "day_6"), turns_elapsed)

    msg_story("-"*60, turns_elapsed)


def progress_outpost(task_package):
    # Performs world progression that is NOT part of tasks or user commands.

    # Increment turn count
    task_package["counters"]["turns"] += 1

    if task_package["counters"]["turns"] % 10 == 0:
        print_day_message(task_package["counters"]["turns"], task_package["droids"])

    # --- Human hunger ---
    for name, stats in task_package["humans"].items():
        if stats.get("state") != "Deceased":
            stats["hunger"] += 1
            task_package = process_hunger_status(name, task_package)

    # --- Droid charge ---
    task_package = decrease_droid_charge(task_package)

    # --- Crop growth ---
    task_package = update_crop_growth(task_package)

    # --- Shield state refresh ---
    task_package = check_shield_state(task_package)

    # Future: weather, morale, events...

    return task_package


def process_user_input(command, resuming=False):
    task_package = load_config()
    turn_suspended = task_package["gamestate"].get("turn_suspended", False)

    # If this is a brand-new turn, process the command first
    if not resuming and not turn_suspended:
        count_as_turn, task_package = process_turn(command, task_package)

        # Invalid command / non-turn command: just save and return
        if not count_as_turn:
            save_config(task_package)
            update_screen(task_package)
            return task_package

        save_config(task_package)

    # Whether this is:
    # 1. a freshly processed turn command, or
    # 2. a resumed suspended turn after a GUI response,
    # continue the turn pipeline here.
    task_package = resume_turn_processing(task_package)
    return task_package


def resume_turn_processing(task_package):
    # Continue processing a turn after a command has already been accepted,
    # or after a GUI question/answer has resolved.
    awaiting_input, task_package = advance_tasks(task_package)

    if awaiting_input:
        task_package["gamestate"]["turn_suspended"] = True
        save_config(task_package)
        return task_package

    task_package["gamestate"]["turn_suspended"] = False
    complete_turn(task_package)
    save_config(task_package)
    return task_package


def complete_turn(task_package):
    # Progress the outpost
    task_package = progress_outpost(task_package)

    # Check for endgame
    game_over, end_msg, task_package = check_endgame(task_package)

    if game_over:
        task_package = handle_game_over_loop(end_msg)

    # Save and update always
    task_package["gamestate"]["turn_suspended"] = False
    save_config(task_package)
    update_screen(task_package)

    return task_package