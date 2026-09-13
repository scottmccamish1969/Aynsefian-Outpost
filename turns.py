# turns.py

from os import name
import random
from datetime import datetime

from actions import handle_immediate_or_queued_task, start_next_queued_task_for_character
from commands import handle_reset_command, clear_task_for_character
from command_utils import handle_read_command,  get_task_by_worker, remove_task_by_id, get_pronouns
from constants import TASK_ASSIGNED, TASK_EXAMINING, TASK_CHARGING, TASK_EATING, ALL_TASKS, CommandOutcome
from endgame import check_endgame, handle_game_over_loop
from lore.lore_ingame import get_message, handle_help_command
from lore.lore_story import get_story_message
import lore.user_interface as ui_runtime
from lore.user_interface import msg_warn, msg_story, msg_error, msg_info, msg_food, get_input
from planting import update_crop_growth, return_reserved_meal
from queuing import get_character_status, feed_hungry_human
from resources import decrease_droid_charge, get_resource, try_start_charge_task
from status import handle_list_command
from tasks import check_completed_tasks, handle_examine_answer
from utils import (can_provide_a_meal, can_character_act, character_not_interruptible, is_command_enabled, load_config, process_hunger_status, check_shield_state, 
                   save_config, update_screen, get_best_match)


def process_command(command, task_package):
    tokens = command.strip().split()
    if not tokens:
        return CommandOutcome.INVALID, task_package

    action = tokens[0]
    qualifier = tokens[1] if len(tokens) > 1 else None

    turns_elapsed = task_package["counters"]["turns"]
    gamestate = task_package["gamestate"]

    outcome = CommandOutcome.INVALID

    # Restrict commands if game is over
    if gamestate.get("game_over", False) and action not in ["status", "help", "reset", "quit"]:
        msg_story(get_story_message("endgame", "restart"), turns_elapsed)
        return CommandOutcome.CANNOT_EXECUTE, task_package

    # Unknown command
    if action not in gamestate:
        msg_error(get_message("error", "unknown_command", command=action), turns_elapsed)
        return CommandOutcome.INVALID, task_package

    # Command not yet unlocked
    if not is_command_enabled(action, gamestate):
        msg_error(get_message("error", "can't_do_that_yet", command=command), turns_elapsed)
        return CommandOutcome.CANNOT_EXECUTE, task_package

    if action == "read":
        outcome, task_package = handle_read_command(task_package, turns_elapsed, qualifier)

    elif action == "replace":
        outcome, task_package = handle_replace_command(qualifier, task_package)

    elif action == "cancel":
        outcome, task_package = handle_cancel_command(qualifier, task_package)

    elif action == "list":
        outcome, task_package = handle_list_command(qualifier, task_package)

    elif action == "help":
        outcome, task_package = handle_help_command(task_package, qualifier=qualifier, gamestate=gamestate)

    elif action == "quit":
        msg_story(get_message("quit", "final"), turns_elapsed)
        msg_story(f"Session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", turns_elapsed)
        exit(0)

    elif action == "reset":
        outcome, task_package = handle_reset_command(task_package)

    # Else it is a more involved command, so requires special processing
    else:
        outcome, task_package = handle_immediate_or_queued_task(action, qualifier,  task_package)

    return outcome, task_package


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

    # --- Increment turn count ---
    task_package["counters"]["turns"] += 1

    # --- Calculate day count ---
    if task_package["counters"]["turns"] % 10 == 0:
        print_day_message(task_package["counters"]["turns"], task_package["droids"])

    # --- Deal with human hunger ---
    for name, stats in task_package["humans"].items():
        if stats.get("state") != "Deceased":
            stats["hunger"] += 1
            task_package = process_hunger_status(name, task_package)

    # --- Decrement droid charge ---
    task_package = decrease_droid_charge(task_package)

    # --- Update crop growth ---
    task_package = update_crop_growth(task_package)

    # --- Refresh shield state ---
    task_package = check_shield_state(task_package)

    # Future: weather, morale, events...

    return task_package


def process_user_input(command, resuming=False):
    task_package = load_config()

    command_clean = command.strip().casefold()

    # ---------------------------------------------------------
    # END TURN
    # Only these commands are allowed to advance world time.
    # ---------------------------------------------------------
    if command_clean in ("end turn", "endturn", "next"):
        outcome, task_package = end_of_turn_processing(task_package)
        if outcome != CommandOutcome.SUCCESS:
            return outcome, task_package
        
        outcome, task_package = prepare_command_phase(task_package)

        save_config(task_package)
        update_screen(task_package)
        return outcome, task_package

    # ---------------------------------------------------------
    # ORDINARY COMMAND
    # Process the order, but DO NOT advance time.
    # ---------------------------------------------------------
    if not resuming:
        outcome, task_package = process_command(command, task_package)

        save_config(task_package)
        update_screen(task_package)

        return outcome, task_package

    # ---------------------------------------------------------
    # GUI callback / resumed command handling
    # No turn progression here either.
    # ---------------------------------------------------------
    save_config(task_package)
    update_screen(task_package)

    return CommandOutcome.SUCCESS, task_package


def end_of_turn_processing(task_package):
    # Complete the turn, save the config and update the screen
    outcome, task_package = complete_turn(task_package)
    save_config(task_package)
    update_screen(task_package)
    
    return outcome, task_package


def complete_turn(task_package):
    # Progress the outpost
    task_package = progress_outpost(task_package)
    tasks = task_package["tasks"]
    outcome = CommandOutcome.SUCCESS

    # Decrement the duration of all tasks in progress and check any that have completed
    for tid, task in tasks.items():
        task["duration"] -= 1
    task_package = check_completed_tasks(task_package)

    # Check for endgame
    game_over, end_msg, task_package = check_endgame(task_package)

    if game_over:
        outcome, task_package = handle_game_over_loop(task_package, end_msg)

    # Save and update always
    task_package["gamestate"]["turn_suspended"] = False
    save_config(task_package)
    update_screen(task_package)

    return outcome, task_package


def prepare_command_phase(task_package):
    # Run checks on all state variables and pending changes for the next turn.
    outcome, task_package = resolve_pending_problems(task_package)
    if outcome == CommandOutcome.AWAITING_INPUT:
        return outcome, task_package

    outcome, task_package = resolve_pending_examinations(task_package)
    if outcome == CommandOutcome.AWAITING_INPUT:
        return outcome, task_package

    outcome, task_package = anticipate_problems(task_package)
    if outcome == CommandOutcome.AWAITING_INPUT:
        return outcome, task_package

    outcome, task_package = start_pending_queued_tasks(task_package)
    return outcome, task_package


def resolve_pending_problems(task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]

    # First check for completed tasks and action as needed
    task_package = check_completed_tasks(task_package)

    # Iterate through humans and feed them if they are idle and hungry/starving/near death
    if can_provide_a_meal(resources):
        for name in humans:
            human = humans[name]
            is_idle = human.get("task", "") == ""
            if is_idle:
                state = get_character_status(name, humans, droids)
                if state in ("Hungry", "Starving", "NearDeath"):
                    task_package = feed_hungry_human(name, task_package)
            if not can_provide_a_meal(resources):   # Might now have run out of food
                break

    # Now do droids
    for name in droids:
        droid = droids[name]
        is_idle = droid.get("task", "") == ""

        if is_idle:
            state = get_character_status(name, humans, droids)
            if state in ("Low"):
                outcome, task_package = try_start_charge_task(name, task_package)

    return CommandOutcome.SUCCESS, task_package


def resolve_pending_examinations(task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]

    all_characters = list(humans.keys()) + list(droids.keys())

    for name in all_characters:
        character = humans.get(name) or droids.get(name)
        is_human = name in humans

        item_name = character.get("examine_needed", "")

        if not item_name:
            continue

        # If feeding, charging, towing, etc. has just begun,
        # leave the examination pending until the character is idle.
        if character.get("task", "") != "":
            continue

        discovered = get_resource(resources, item_name)
        pronouns = get_pronouns(name, is_human)

        if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
            ui_runtime.ACTIVE_UI.set_pending_question(
                callback=handle_examine_answer,
                context={
                    "task_package": task_package,
                    "character_name": name,
                    "item": discovered,
                    "item_name": item_name,
                    "is_human": is_human,
                    "is_examining": False
                },
                resume_turn=False,
                continue_command_phase=True
            )

        answer = get_input("input", "explore_found", turns_elapsed, target=name, res_name=item_name, pronoun=pronouns["p2"].lower())

        if answer == ui_runtime.GUI_PENDING:
            return CommandOutcome.AWAITING_INPUT, task_package

    return CommandOutcome.SUCCESS, task_package


def anticipate_problems(task_package):
    # UNDER CONSTRUCTION
    return CommandOutcome.SUCCESS, task_package


def start_pending_queued_tasks(task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]

    all_characters = list(humans.keys()) + list(droids.keys())

    for name in all_characters:
        character = humans.get(name) or droids.get(name)

        task = character.get("task", "")
        is_idle = task == ""
        if not is_idle:
            continue

        outcome, task_package = start_next_queued_task_for_character(name, task_package)

        if outcome == CommandOutcome.AWAITING_INPUT:
            return outcome, task_package

    return CommandOutcome.SUCCESS, task_package


def handle_replace_command(qualifier, task_package):
    # Handles the 'replace' command for characters. 
    # Which means (other than eating or charging), stop what you're doing and do this now
    turns_elapsed = task_package["counters"]["turns"]
    
    # They added a name at the end, so just resume processing
    if qualifier:
        name_input = qualifier.lower()
        context = {
            "task_package": task_package,
        }
        outcome, task_package = resume_replace_command(name_input, context)
        return outcome, task_package

    # They didn't add a name, so prompt for it, and the resume happens through the callback
    else:
        if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
                ui_runtime.ACTIVE_UI.set_pending_question(
                    callback=resume_replace_command,
                    context={
                        "task_package": task_package,
                    },
                    resume_turn = False
                )
        answer = get_input("input", "replace", turns_elapsed).strip().lower()

        if answer and answer == ui_runtime.GUI_PENDING:
            return CommandOutcome.AWAITING_INPUT, task_package

        return CommandOutcome.CANNOT_EXECUTE, task_package


def resume_replace_command(answer, context):
    task_package = context["task_package"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]
    name_input = answer

    character = get_best_match(name_input, list(humans.keys()) + list(droids.keys()))
    if not character:
        msg_error(get_message("error", "no_character", name=name_input), turns_elapsed)
        return CommandOutcome.INVALID, task_package
    
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
        return CommandOutcome.CANNOT_EXECUTE, task_package

    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
            ui_runtime.ACTIVE_UI.set_pending_question(
                callback=complete_replace_command,
                context={
                    "task_package": task_package,
                    "name": character
                },
                resume_turn = False
            )
    answer = get_input("replace", "with_what", turns_elapsed, name=character, task_name=task_now_doing)

    if answer and answer != ui_runtime.GUI_PENDING:
        msg_warn(get_message("error", "no_CLI", turns_elapsed))

    return CommandOutcome.AWAITING_INPUT, task_package     # Should always be this once we get to the question stage


def complete_replace_command(answer, context):
    task_package = context["task_package"]
    character = context["name"]
    tasks = task_package["tasks"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    if answer and answer == "0":
        msg_info(get_message("replace", "not_replaced", name=character), turns_elapsed)
        return CommandOutcome.CANNOT_EXECUTE, task_package
    elif not answer:
        msg_info(get_message("replace", "aborted"), turns_elapsed)
        return CommandOutcome.INVALID, task_package

    # Now go ahead and process the new task
    new_task = answer
    task_id, task = get_task_by_worker(tasks, character)
    current_task = task["type"]

    # If the character is eating, charging or towing a droid they can't use 'replace'
    if character_not_interruptible(character, current_task, task_package):
        msg_warn(get_message("replace", "cannot_interrupt", name=character, new_task=answer, task=current_task), turns_elapsed)

        # Put the new task at the top of the queue and delete the third queued task
        if character in humans:
            queue = humans[character]["queue"]
        elif character in droids:
            queue = droids[character]["queue"]
        else:
            msg_warn(get_message("error", "character_not_found", name=character), turns_elapsed)
            return CommandOutcome.INVALID, task_package

        # Now remove the first queued task and make that slot empty (to be picked up later)
        queue["3"] = queue["2"].copy()
        queue["2"] = queue["1"].copy()
        queue["1"] = {"task": "", "item": ""}

        return CommandOutcome.CANNOT_EXECUTE, task_package
    
    # It's a valid task, go ahead with it
    if new_task in ALL_TASKS:
        remove_task_by_id(task_id, task_package)    # Remove the old task and clear the character's status
        old_task = task["type"]
        msg_info(get_message("replace", "replacing", name=character, old_task=old_task, new_task=new_task), turns_elapsed)

    # It's an invalid task e.g. 'save_the_universe'
    else:
        msg_error(get_message("replace", "invalid_task", name=character, new_task=new_task), turns_elapsed)
        return CommandOutcome.INVALID, task_package

    # Now process the new command
    qualifier = character
    outcome, task_package = handle_immediate_or_queued_task(new_task , qualifier, task_package)

    return outcome, task_package


def handle_cancel_command(qualifier, task_package):
    # Handles the 'cancel' command for characters.
    # This may mean:
    # 1. cancel the current task, or
    # 2. remove a queued task

    turns_elapsed = task_package["counters"]["turns"]

    if qualifier:
        context = {"task_package": task_package,}
        return resume_cancel_command(qualifier.lower(), context)

    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=resume_cancel_command,
            context={
                "task_package": task_package,
            },
            resume_turn = False
        )

    answer = get_input("cancel", "who", turns_elapsed).strip().lower()

    if answer and answer == ui_runtime.GUI_PENDING:
        return CommandOutcome.AWAITING_INPUT, task_package

    return resume_cancel_command(answer, {"task_package": task_package})


def resume_cancel_command(answer, context):
    task_package = context["task_package"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]
    awaiting_input = False
    task_now_doing = ""

    character = get_best_match(answer, list(humans.keys()) + list(droids.keys()))
    if not character:
        msg_error(get_message("error", "no_character", name=answer), turns_elapsed)
        return CommandOutcome.INVALID, task_package

    # Get queue and task information    
    if character in humans:
        queue = humans[character]["queue"]
        task_now_doing = humans[character].get("task", "")
    elif character in droids:
        queue = droids[character]["queue"]
        task_now_doing = droids[character].get("task", "")
    else:
        msg_error(get_message("error", "character_not_found", name=character), turns_elapsed)
        return CommandOutcome.INVALID, task_package
    
    task_id, task = get_task_by_worker(tasks, character)
    if not task and not task_now_doing:
        msg_error(get_message("cancel", "nothing_to_cancel", name=character), turns_elapsed)
        return CommandOutcome.CANNOT_EXECUTE, task_package

    if task:
        if character_not_interruptible(character, task["type"], task_package):
            return CommandOutcome.CANNOT_EXECUTE, task_package

    has_current_task = task is not None or task_now_doing != ""
    queued_slots = [slot for slot in ("1", "2", "3") if queue[slot]["task"] != ""]
    has_queue = len(queued_slots) > 0

    if not has_current_task and not has_queue:
        msg_error(get_message("cancel", "nothing_to_cancel", name=character), turns_elapsed)
        return CommandOutcome.CANNOT_EXECUTE, task_package

    current_task_desc = "--Idle--"
    current_task_type = ""

    if task:
        current_task_type = task["type"]
        if current_task_type in (TASK_EXAMINING, TASK_ASSIGNED):
            item_name = task.get("item_name", "")
            current_task_desc = f"{current_task_type} {item_name} ({task['duration']} turns remaining)"
        else:
            current_task_desc = f"{current_task_type} ({task['duration']} turns remaining)"
    # If the character has no task, but is assigned or is showing a task, we can clear it and return to idle
    elif task_now_doing:
        humans, droids = clear_task_for_character(name, "", humans, droids)
        return CommandOutcome.SUCCESS, task_package

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
                },
                resume_turn = False
            )

        answer = get_input("cancel", "which_queued", turns_elapsed, name=character, queue_list=queue_string)

        if answer and answer == ui_runtime.GUI_PENDING:
            return CommandOutcome.AWAITING_INPUT, task_package

        task_package = complete_cancel_command(answer, {
            "task_package": task_package,
            "name": character,
            "task_id": None,
            "current_task_type": "",
            "queued_slots": queued_slots,
            "mode": "queue_only",
        })
        return CommandOutcome.AWAITING_INPUT, task_package

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
            },
            resume_turn = False
        )

    answer = get_input("cancel", "current_or_queue", turns_elapsed, name=character, current_task=current_task_desc, queue_list=queue_string)

    if answer and answer  == ui_runtime.GUI_PENDING:
        return CommandOutcome.AWAITING_INPUT, task_package

    task_package = complete_cancel_command(answer, {
        "task_package": task_package,
        "name": character,
        "task_id": task_id,
        "current_task_type": current_task_type,
        "queued_slots": queued_slots,
        "mode": "choose_cancel_type",
    })
    return CommandOutcome.SUCCESS, task_package


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
        return CommandOutcome.CANNOT_EXECUTE, task_package

    # Stage 1: choose current vs queued
    if mode == "choose_cancel_type":
        choice = answer.strip()

        if choice == "0":
            msg_info(get_message("cancel", "not_cancelled", name=character), turns_elapsed)
            return CommandOutcome.CANNOT_EXECUTE, task_package

        if choice == "1":
            if current_task_type in (TASK_EATING, TASK_CHARGING):
                msg_warn(get_message("cancel", "cannot_interrupt", name=character, task=current_task_type), turns_elapsed)
                return CommandOutcome.CANNOT_EXECUTE, task_package

            if task_id is None or task_id not in tasks:
                msg_error(get_message("cancel", "nothing_current", name=character), turns_elapsed)
                return CommandOutcome.CANNOT_EXECUTE, task_package

            old_task = tasks[task_id]["type"]
            remove_task_by_id(task_id, task_package)

            msg_info(get_message("cancel", "current_cancelled", name=character, task=old_task), turns_elapsed)

            if not queued_slots:
                msg_info(get_message("cancel", "no_queued_tasks", name=character), turns_elapsed)
                return CommandOutcome.CANNOT_EXECUTE, task_package

            return CommandOutcome.SUCCESS, task_package

        if choice == "2":
            if not queued_slots:
                msg_error(get_message("cancel", "no_queued_tasks", name=character), turns_elapsed)
                return CommandOutcome.CANNOT_EXECUTE, task_package

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
                    },
                    resume_turn = False
                )

            answer = get_input("cancel", "which_queued", turns_elapsed, name=character, queue_list=", ".join(queued_slots))

            if answer and answer  == ui_runtime.GUI_PENDING:
                task_package["gamestate"]["turn_suspended"] = True
                save_config(task_package)
                return CommandOutcome.AWAITING_INPUT, task_package

            return complete_cancel_command(answer, {
                "task_package": task_package,
                "name": character,
                "task_id": task_id,
                "current_task_type": current_task_type,
                "queued_slots": queued_slots,
                "mode": "queue_only",
            })

        msg_error(get_message("cancel", "invalid_choice", choice=choice), turns_elapsed)
        return CommandOutcome.INVALID, task_package

    # Stage 2: remove queued task
    if mode == "queue_only":
        return_food = False
        slot = answer.strip()

        if slot == "0":
            msg_info(get_message("cancel", "not_cancelled", name=character), turns_elapsed)
            return CommandOutcome.SUCCESS, task_package

        if slot not in ("1", "2", "3") or slot not in queued_slots:
            msg_error(get_message("cancel", "invalid_queue_slot", slot=slot, name=character), turns_elapsed)
            return CommandOutcome.INVALID, task_package

        # Capture everything before shifting the queue.
        removed_record = queue[slot].copy()
        removed_task = removed_record.get("task", "")
        task_data = removed_record.get("task_data", {})

        # Return reserved food only for a queued Eating task.
        if removed_task == TASK_EATING:
            if task_data:
                task_package = return_reserved_meal(task_data, task_package)
                msg_food(get_message("feed", "food_returned", name=character), turns_elapsed, tone="warn")
            else:
                msg_food(get_message("feed", "food_not_returned", name=character), turns_elapsed, tone="warn")

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
        return CommandOutcome.SUCCESS, task_package

    msg_error("[Cancel command mode not recognised]", turns_elapsed)
    return CommandOutcome.CANNOT_EXECUTE, task_package