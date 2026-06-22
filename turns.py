# turns.py

import random
from datetime import datetime

from actions import handle_immediate_or_queued_task, start_next_queued_task_for_character
from commands import handle_reset_command
from command_utils import handle_read_command,  get_task_by_worker, remove_task_by_id
from constants import TASK_ASSIGNED, TASK_EXAMINING, TASK_CHARGING, TASK_EATING, ALL_TASKS
from endgame import check_endgame, handle_game_over_loop
from lore.lore_ingame import get_message, handle_help_command
from lore.lore_story import get_story_message
import lore.user_interface as ui_runtime
from lore.user_interface import msg_warn, msg_story, msg_error, msg_info, get_input
from planting import update_crop_growth
from resources import decrease_droid_charge
from status import handle_list_command
from tasks import advance_tasks
from utils import is_command_enabled, load_config, process_hunger_status, check_shield_state, save_config, update_screen, get_best_match


def process_turn(command, task_package):
    tokens = command.strip().split()
    if not tokens:
        return False, task_package

    action = tokens[0]
    qualifier = tokens[1] if len(tokens) > 1 else None
    dock_a_turn = False

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
        awaiting_input, task_package = handle_read_command(task_package, turns_elapsed, qualifier)
        if awaiting_input:
            return dock_a_turn, task_package

    elif action == "replace":
        awaiting_input, task_package = handle_replace_command(qualifier, task_package)
        if awaiting_input:
            return dock_a_turn, task_package

    elif action == "cancel":
        awaiting_input, task_package = handle_cancel_command(qualifier, task_package)
        if awaiting_input:
            return dock_a_turn, task_package

    elif action == "list":
        handle_list_command(qualifier, task_package)

    elif action == "help":
        handle_help_command(task_package, qualifier=qualifier, gamestate=gamestate)

    elif action == "quit":
        msg_story(get_message("quit", "final"), turns_elapsed)
        msg_story(f"Session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", turns_elapsed)
        exit(0)

    elif action == "reset":
        awaiting_input, task_package = handle_reset_command(task_package)
        if awaiting_input:
            return dock_a_turn, task_package

    # Else it is a more involved command, so requires special processing
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
    tasks = task_package["tasks"]
    
    for tid, task in tasks.items():
        task["duration"] -= 1

    # Check for endgame
    game_over, end_msg, task_package = check_endgame(task_package)

    if game_over:
        task_package = handle_game_over_loop(end_msg)

    # Save and update always
    task_package["gamestate"]["turn_suspended"] = False
    save_config(task_package)
    update_screen(task_package)

    return task_package


def handle_replace_command(qualifier, task_package):
    # Handles the 'replace' command for characters. 
    # Which means (other than eating or charging), stop what you're doing and do this now
    turns_elapsed = task_package["counters"]["turns"]
    awaiting_input = False
    
    # They added a name at the end, so just resume processing
    if qualifier:
        name_input = qualifier.lower()
        context = {
            "task_package": task_package,
        }
        if not resume_replace_command(name_input, context):
            awaiting_input = True
        return awaiting_input, task_package

    # They didn't add a name, so prompt for it, and the resume happens through the callback
    else:
        if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
                ui_runtime.ACTIVE_UI.set_pending_question(
                    callback=resume_replace_command,
                    context={
                        "task_package": task_package,
                    }
                )
        answer = get_input("input", "replace", turns_elapsed).strip().lower()

        if answer and answer == ui_runtime.GUI_PENDING:
            awaiting_input = True
            return awaiting_input, task_package

        return awaiting_input, task_package


def resume_replace_command(answer, context):
    task_package = context["task_package"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]
    name_input = answer
    awaiting_input = False

    character = get_best_match(name_input, list(humans.keys()) + list(droids.keys()))
    if not character:
        msg_error(get_message("error", "no_character", name=name_input), turns_elapsed)
        return awaiting_input, task_package
    
    # Get their current task, display it, and ask what they'd like to replace it with
    task_id, task = get_task_by_worker(tasks, character)

    task_now_doing = "--Idle--"
    task_type = ""
    if task:
        task_type = task["type"]
        if task_type in (TASK_EXAMINING, TASK_ASSIGNED):
            item_name = task["item_name"]
            task_now_doing = f"{task_type} {item_name} ({task['duration']} turns remaining)"
        else:
            task_now_doing = f"{task_type} ({task['duration']} turns remaining)"

    else:
        msg_error(get_message("replace", "is_idle", name=character), turns_elapsed)
        return awaiting_input, task_package

    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
            ui_runtime.ACTIVE_UI.set_pending_question(
                callback=complete_replace_command,
                context={
                    "task_package": task_package,
                    "name": character
                }
            )
    answer = get_input("replace", "with_what", turns_elapsed, name=character, task_name=task_now_doing)

    if answer and answer != ui_runtime.GUI_PENDING:
        msg_warn(get_message("error", "no_CLI", turns_elapsed))

    return None     # Should always be this once we get to the question stage


def complete_replace_command(answer, context):
    task_package = context["task_package"]
    character = context["name"]
    tasks = task_package["tasks"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    if answer and answer == "0":
        msg_info(get_message("replace", "not_replaced", name=character), turns_elapsed)
        return None    # This will not dock a turn
    elif not answer:
        msg_info(get_message("replace", "aborted"), turns_elapsed)
        return None    # This will not dock a turn

    # Now go ahead and process the new task
    new_task = answer
    task_id, task = get_task_by_worker(tasks, character)
    current_task = task["type"]

    # If the character is eating or charging, they can't use 'replace'
    if current_task in (TASK_EATING, TASK_CHARGING):
        msg_warn(get_message("replace", "cannot_interrupt", name=character, task=answer), turns_elapsed)

        # Put the new task at the top of the queue and delete the third queued task
        if character in humans:
            queue = humans[character]["queue"]
        elif character in droids:
            queue = droids[character]["queue"]
        else:
            msg_warn(get_message("error", "character_not_found", name=character), turns_elapsed)
            return task_package

        # Now remove the first queued task and make that slot empty 
        # (to be picked up later by add_to_queue, within handle_immediate_or_queued_task)
        queue["3"] = queue["2"].copy()
        queue["2"] = queue["1"].copy()
        queue["1"] = {"task": "", "item": ""}
    
    # It's a valid task, go ahead with it
    if new_task in ALL_TASKS:
        remove_task_by_id(task_id, task_package)    # Remove the old task and clear the character's status
        old_task = task["type"]
        msg_info(get_message("replace", "replacing", name=character, old_task=old_task, new_task=new_task), turns_elapsed)

    # It's an invalid task e.g. 'save_the_universe'
    else:
        msg_error(get_message("replace", "invalid_task", name=character, new_task=new_task), turns_elapsed)
        return None   # This means it won't cost them a turn

    # Now process the new command
    qualifier = character
    valid_command, task_package = handle_immediate_or_queued_task(new_task , qualifier, task_package)

    if valid_command:
        task_package = resume_turn_processing(task_package)
        return task_package
    else:
        return None    # This is likely to be because we are in the middle of sorting out the new command


def handle_cancel_command(qualifier, task_package):
    # Handles the 'cancel' command for characters.
    # This may mean:
    # 1. cancel the current task, or
    # 2. remove a queued task

    turns_elapsed = task_package["counters"]["turns"]

    if qualifier:
        context = {
            "task_package": task_package,
        }
        return resume_cancel_command(qualifier.lower(), context)

    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=resume_cancel_command,
            context={
                "task_package": task_package,
            }
        )

    answer = get_input("cancel", "who", turns_elapsed).strip().lower()

    if answer and answer == ui_runtime.GUI_PENDING:
        awaiting_input = True
        return awaiting_input, task_package

    return resume_cancel_command(answer, {"task_package": task_package})


def resume_cancel_command(answer, context):
    task_package = context["task_package"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]

    character = get_best_match(answer, list(humans.keys()) + list(droids.keys()))
    if not character:
        msg_error(get_message("error", "no_character", name=answer), turns_elapsed)
        return False, task_package

    task_id, task = get_task_by_worker(tasks, character)

    if character in humans:
        queue = humans[character]["queue"]
    elif character in droids:
        queue = droids[character]["queue"]
    else:
        msg_error(get_message("error", "character_not_found", name=character), turns_elapsed)
        return False, task_package

    has_current_task = task is not None
    queued_slots = [slot for slot in ("1", "2", "3") if queue[slot]["task"] != ""]
    has_queue = len(queued_slots) > 0

    if not has_current_task and not has_queue:
        msg_error(get_message("cancel", "nothing_to_cancel", name=character), turns_elapsed)
        return False, task_package

    current_task_desc = "--Idle--"
    current_task_type = ""

    if has_current_task:
        current_task_type = task["type"]
        if current_task_type in (TASK_EXAMINING, TASK_ASSIGNED):
            item_name = task.get("item_name", "")
            current_task_desc = f"{current_task_type} {item_name} ({task['duration']} turns remaining)"
        else:
            current_task_desc = f"{current_task_type} ({task['duration']} turns remaining)"

    queue_desc = []
    for slot in queued_slots:
        queued_task = queue[slot]["task"]
        queued_item = queue[slot].get("item", "")
        if queued_item:
            queue_desc.append(f"{slot}:{queued_task} {queued_item}")
        else:
            queue_desc.append(f"{slot}:{queued_task}")

    queue_string = ", ".join(queue_desc) if queue_desc else "(none)"

    # If no current task, skip straight to queued removal
    if not has_current_task and has_queue:
        if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
            ui_runtime.ACTIVE_UI.set_pending_question(
                callback=complete_cancel_command,
                context={
                    "task_package": task_package,
                    "name": character,
                    "task_id": None,
                    "current_task_type": "",
                    "queued_slots": queued_slots,
                    "mode": "queue_only",
                }
            )

        answer = get_input("cancel", "which_queued", turns_elapsed, name=character, queue_list=queue_string)

        if answer and answer == ui_runtime.GUI_PENDING:
            return None

        task_package = complete_cancel_command(answer, {
            "task_package": task_package,
            "name": character,
            "task_id": None,
            "current_task_type": "",
            "queued_slots": queued_slots,
            "mode": "queue_only",
        })
        return False, task_package

    # Otherwise ask whether to cancel current or queued
    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=complete_cancel_command,
            context={
                "task_package": task_package,
                "name": character,
                "task_id": task_id,
                "current_task_type": current_task_type,
                "queued_slots": queued_slots,
                "mode": "choose_cancel_type",
            }
        )

    answer = get_input("cancel", "current_or_queue", turns_elapsed, name=character, current_task=current_task_desc, queue_list=queue_string)

    if answer and answer  == ui_runtime.GUI_PENDING:
        return None

    task_package = complete_cancel_command(answer, {
        "task_package": task_package,
        "name": character,
        "task_id": task_id,
        "current_task_type": current_task_type,
        "queued_slots": queued_slots,
        "mode": "choose_cancel_type",
    })
    return False, task_package


def complete_cancel_command(answer, context):
    task_package = context["task_package"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]

    character = context["name"]
    task_id = context["task_id"]
    current_task_type = context["current_task_type"]
    queued_slots = context["queued_slots"]
    mode = context["mode"]

    if character in humans:
        queue = humans[character]["queue"]
        is_human = True
    elif character in droids:
        queue = droids[character]["queue"]
        is_human = False
    else:
        msg_error(get_message("error", "character_not_found", name=character), turns_elapsed)
        return task_package

    # Stage 1: choose current vs queued
    if mode == "choose_cancel_type":
        choice = answer.strip()

        if choice == "0":
            msg_info(get_message("cancel", "not_cancelled", name=character), turns_elapsed)
            return task_package

        if choice == "1":
            if current_task_type in (TASK_EATING, TASK_CHARGING):
                msg_warn(get_message("cancel", "cannot_interrupt", name=character, task=current_task_type), turns_elapsed)
                return task_package

            if task_id is None or task_id not in tasks:
                msg_error(get_message("cancel", "nothing_current", name=character), turns_elapsed)
                return task_package

            old_task = tasks[task_id]["type"]
            remove_task_by_id(task_id, task_package)

            msg_info(get_message("cancel", "current_cancelled", name=character, task=old_task), turns_elapsed)

            if not queued_slots:
                msg_info(get_message("cancel", "no_queued_tasks", name=character), turns_elapsed)
                return task_package

            awaiting_input, task_package = start_next_queued_task_for_character(character, task_package)

            if awaiting_input:
                return None

            return task_package

        if choice == "2":
            if not queued_slots:
                msg_error(get_message("cancel", "no_queued_tasks", name=character), turns_elapsed)
                return task_package

            if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
                ui_runtime.ACTIVE_UI.set_pending_question(
                    callback=complete_cancel_command,
                    context={
                        "task_package": task_package,
                        "name": character,
                        "task_id": task_id,
                        "current_task_type": current_task_type,
                        "queued_slots": queued_slots,
                        "mode": "queue_only",
                    }
                )

            answer = get_input("cancel", "which_queued", turns_elapsed, name=character, queue_list=", ".join(queued_slots))

            if answer and answer  == ui_runtime.GUI_PENDING:
                task_package["gamestate"]["turn_suspended"] = True
                save_config(task_package)
                return None

            return complete_cancel_command(answer, {
                "task_package": task_package,
                "name": character,
                "task_id": task_id,
                "current_task_type": current_task_type,
                "queued_slots": queued_slots,
                "mode": "queue_only",
            })

        msg_error(get_message("cancel", "invalid_choice", choice=choice), turns_elapsed)
        return task_package

    # Stage 2: remove queued task
    if mode == "queue_only":
        slot = answer.strip()

        if slot == "0":
            msg_info(get_message("cancel", "not_cancelled", name=character), turns_elapsed)
            return task_package

        if slot not in ("1", "2", "3") or slot not in queued_slots:
            msg_error(get_message("cancel", "invalid_queue_slot", slot=slot, name=character), turns_elapsed)
            return task_package

        removed_task = queue[slot]["task"]

        # Shift left after removal
        if slot == "1":
            queue["1"] = queue["2"].copy()
            queue["2"] = queue["3"].copy()
            queue["3"] = {"task": "", "item": ""}
        elif slot == "2":
            queue["2"] = queue["3"].copy()
            queue["3"] = {"task": "", "item": ""}
        elif slot == "3":
            queue["3"] = {"task": "", "item": ""}

        msg_info(get_message("cancel", "queued_cancelled", name=character, task=removed_task, slot=slot), turns_elapsed)
        return task_package

    msg_error("[Cancel command mode not recognised]", turns_elapsed)
    return task_package