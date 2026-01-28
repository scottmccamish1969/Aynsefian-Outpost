# command_utils.py

import os

from constants import (TASK_ASSIGNED, TASK_CHARGING, TASK_EXAMINING, TASK_EXPLORING, TASK_EATING, TASK_MINING,
                       TASK_PLANTING, TASK_REAPING, TASK_REFUELING)
from lore.lore_ingame import get_message
from lore.lore_story import get_story_message
from lore.user_interface import get_input
from utils import log_and_display, get_pronouns, get_best_match, get_task_by_worker, clear_task_for_character, set_task_status_for_character


def local_get_next_available_slot(queue):
    # Returns the key of the next available slot (1, 2, or 3) or None if full.
    for slot in ["1", "2", "3"]:
        if queue[slot]["task"] == "":
            return slot
    return None


def local_add_to_queue(character, humans, droids, task, item=""):
    # Adds a task to the next available queue slot for a human or droid.
    # Returns True if successful, False if the queue is full.
    if character in humans:
        next_slot = local_get_next_available_slot(humans[character]["queue"])
    elif character in droids:
        next_slot = local_get_next_available_slot(droids[character]["queue"])
    else:
        return False, humans, droids

    if next_slot:
        if character in humans:
            humans[character]["queue"][next_slot]["task"] = task
            humans[character]["queue"][next_slot]["item"] = item
        elif character in droids:
            droids[character]["queue"][next_slot]["task"] = task
            droids[character]["queue"][next_slot]["item"] = item
        return True, humans, droids
    else:
        return False, humans, droids


def create_task(name, task_type, duration, task_package):
    tasks = task_package["tasks"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    item_name = task_package["item"]
    task_data = task_package["task_data"]
    item_name=None
    task_data=None
    return_msg = ""
    is_human = name in humans

    # Before assigning a task to `name`, check if they're doing something else
    if is_human:
        character_idle = humans[name]["task"] == ""
        if not character_idle:
            task_type_now_doing = humans[name]["task"]
    else:
        character_idle = droids[name]["task"] == ""
        if not character_idle:
            task_type_now_doing = droids[name]["task"]

    okay_to_transition = False
    if task_type == TASK_EXAMINING and task_type_now_doing == TASK_EXPLORING:
        okay_to_transition = True

    if not character_idle and not okay_to_transition:
        success, humans, droids = local_add_to_queue(name, humans, droids, task_type, item_name)
        if success:
            pronouns = get_pronouns(name, is_human)
            return_msg = get_message("queue", "added", character=name, current_task=task_type_now_doing, queue_task=task_type, pronoun=pronouns["p3"].lower())
        else:
            return_msg = get_message("queue", "queue_full", character=name)
        
        return return_msg, task_package

    if task_type == TASK_EATING:
        if duration == 1:
            turn_msg = "1 turn"
        else:
            turn_msg = f"{duration} turns"
        return_msg = get_message("feed", "commenced", person_name=name, turn_msg=turn_msg)
    elif task_type == TASK_CHARGING:
        return_msg = get_message("charge", "commenced", target=name, turns=duration)
    elif task_type == TASK_EXPLORING:
        pronouns = get_pronouns(name, is_human)
        return_msg = get_message("explore", "commenced", target=name, turns=duration, pronoun=pronouns["p1"].lower())
    elif task_type == TASK_PLANTING:
        return_msg = get_message("plant", "commenced", target=name)
    elif task_type == TASK_REAPING:
        return_msg = get_message("reap", "commenced", target=name, turns=duration)
    elif task_type == TASK_EXAMINING:
        pronouns = get_pronouns(name, is_human)
        return_msg = get_message("examine", "commenced", name=name, turns=duration, item=item_name, pronoun=pronouns["p1"].lower())
    elif task_type == TASK_MINING:
        return_msg = get_message("mine", "commenced", target=name, turns=duration)
    elif task_type == TASK_ASSIGNED:
        return_msg = get_message("assign", "commenced", name=name, item=item_name)
    elif task_type == TASK_REFUELING:
        return_msg = get_message("refuel", "commenced", target=name, item=item_name)
    else:
        return_msg = get_message("task", "unknown", name=name, task_type=task_type)

    # Now go ahead and assign the task
    task_package["counters"]["task"] += 1
    task_id = task_package["counters"]["task"]   # task_id (changed to be distinct) now only used locally when creating the task

    tasks[str(task_id)] = {
        "type": task_type,
        "name": name,
        "human": is_human,
        "duration": duration
    }

    # Store extra items in the task
    if task_type == TASK_EXAMINING:
        tasks[str(task_id)]["item_name"] = item_name
    elif task_type == TASK_MINING:
        tasks[str(task_id)]["worker"] = name
    elif task_type == TASK_ASSIGNED:
        tasks[str(task_id)]["item_name"] = item_name
        if task_data:
            tasks[str(task_id)]["task_data"] = task_data
    elif task_type == TASK_PLANTING:
        tasks[str(task_id)]["task_data"] = task_data

    # Set the status for the character
    set_task_status_for_character(name, task_type, item_name, humans, droids, task_package["counters"]["turns"])

    return return_msg, task_package


def handle_read_command(turns_elapsed, subject=None):
    available_files = {
        "orders": "",
        "log": "outpost_log.txt",
        "log_old": "outpost_log.old"
    }

    # If no subject specified, enter local sub-loop
    can_read_these = []
    if subject is None:
        # Only list files that exist or are always-available lore entries
        for key, filename in available_files.items():
            if key == "orders" or os.path.exists(filename):
                choice = f"{key}"
                can_read_these.append(choice)

        can_read_these.append('quit: read nothing')
        subject = get_input("input", "read", turns_elapsed, files=can_read_these)

    if subject == "quit":
        return
    
    # Now continue as before
    elif subject in available_files:
        if subject == "orders":
            log_and_display(get_message("read", "here_it_is", subject=subject), turns_elapsed)
            messages = get_story_message("orders", "message")
            for line in messages:
                print("\n" + line)
        else:
            filename = available_files[subject]
            if os.path.exists(filename):
                log_and_display(get_message("read", "here_it_is", subject=subject), turns_elapsed)
                with open(filename, "r", encoding="utf-8") as f:
                    print(f.read())
            else:
                print(get_message("read", "no_subject", subject=subject))
    else:
        print(get_message("read", "no_content", subject=subject))


def handle_manage_command(qualifier, task_package):
    # Handles the 'manage' command for characters. Allows cancelling tasks, reordering queue, or removing queued tasks.

    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    task_number = task_package["task_number"]
    turns_elapsed = task_package["turns_elapsed"]

    char_msg = ""
    queue_str = ""
    # Step 1: If no qualifier, prompt for who should be managed
    all_chars = list(humans.keys()) + list(droids.keys())
    log_and_display("Current status of humans and droids:", turns_elapsed)
    
    if not qualifier:
        for name in all_chars:
            char_msg, queue_str = get_full_character_tasks(name, humans, droids)
            log_and_display(f"- {char_msg}", turns_elapsed)
    else:
        name_input = qualifier.lower()

    valid_character = False
    # Step 2: Match name, get task and define the queue
    while True:
        char_msg, queue_str = get_full_character_tasks(name, humans, droids)   # Refresh in case we deleted a task or moved one

        if not qualifier and not valid_character:
            name_input = get_input("input", "manage").strip().lower()

            if name_input == "0":
                return task_package

        character = get_best_match(name_input, list(humans.keys()) + list(droids.keys()))
        if character:
            valid_character = True
            char_msg, queue_str = get_full_character_tasks(character.capitalize(), humans, droids)
            if character in humans:
                queue = humans[character]["queue"]
            elif character in droids:
                queue = droids[character]["queue"]
            else:
                queue = []

        else:
            log_and_display(get_message("error", "no_character", name=name_input), turns_elapsed)
            if qualifier:   # Return if they typed something 'manage rubbish'
                return task_package
            continue        # else continue, because they mistyped the character's name

        # Step 3: Show manage menu
        # Get the current task for this character
        task_id, task = get_task_by_worker(tasks, character)
        char_msg, queue_str = get_full_character_tasks(character.capitalize(), humans, droids)   # Refresh the queue string (queue_str)
        task_now_doing = "--Idle--"
        if task:
            task_type = task["type"]
            if task_type in (TASK_EXAMINING, TASK_ASSIGNED):
                item_name = task["item_name"]
                task_now_doing = f"{task_type} {item_name} ({task["duration"]} turns remaining)"
            else:
                task_now_doing = f"{task_type} ({task["duration"]} turns remaining)"

        # Status
        log_and_display(f"** {character} **: {task_now_doing}  --  ", turns_elapsed, end='')
        log_and_display(f"  {queue_str}", turns_elapsed)

        # Menu options
        log_and_display("1. Cancel current task", turns_elapsed)
        if queue and queue["1"]["task"] != "":
            log_and_display("2. Move a queued task to the top", turns_elapsed)
            log_and_display("3. Remove a queued task", turns_elapsed)
        log_and_display("0. Quit managing this character", turns_elapsed)

        choice = get_input("input", "manage_option")

        if choice == "1":
            if task_now_doing != "--Idle--":
                item_name = humans[character]["item"] if character in humans else droids[character]["item"]
                log_and_display(get_message("queue", "cancel_current", task=task_now_doing), turns_elapsed)
                del tasks[task_id]
                humans, droids = clear_task_for_character(character, item_name, humans, droids)
            else:
                log_and_display("Character is already --Idle--.", turns_elapsed)

        elif queue and queue["1"]["task"] != "" and choice == "2":
            valid_tasks = [(slot, q["task"]) for slot, q in queue.items() if q["task"]]
            if not valid_tasks:
                log_and_display(get_message("queue", "no_tasks"), turns_elapsed)
                continue

            # Show queue and prompt
            for slot, task in valid_tasks:
                log_and_display(f"{slot}. {task}", turns_elapsed)
            log_and_display("0. Abort reordering", turns_elapsed)

            move_input = get_input("input", "manage_move_choice")

            if move_input.isdigit():
                if move_input == "0":
                    log_and_display(get_message("queue", "reorder_abort", character=character), turns_elapsed)
                    continue
                elif move_input == "1":
                    log_and_display(get_message("queue", "reorder_already_at_top", character=character, task=queue["1"]["task"]), turns_elapsed)
                    continue
                elif move_input in queue and queue[move_input]["task"]:
                    # Move selected task to top
                    selected = queue[move_input]
                    new_order = [selected]

                    # Append all other tasks (skipping the moved one)
                    for slot in ["1", "2", "3"]:
                        if slot != move_input and queue[slot]["task"]:
                            new_order.append(queue[slot])

                    # Rebuild the queue dict in order
                    for idx, slot in enumerate(["1", "2", "3"]):
                        if idx < len(new_order):
                            queue[slot] = new_order[idx]
                        else:
                            queue[slot] = {"task": "", "item": ""}

                    log_and_display(get_message("queue", "reordered_task", character=character, task=selected["task"], new_pos="1", old_pos=move_input), turns_elapsed)
                else:
                    log_and_display(get_message("queue", "reorder_invalid", character=character, pos=move_input), turns_elapsed)
            else:
                log_and_display("queue", "reorder_valid_number_needed", turns_elapsed)

        elif queue and queue["1"]["task"] != "" and choice == "3":
            valid_tasks = [(slot, q["task"]) for slot, q in queue.items() if q["task"]]
            if not valid_tasks:
                log_and_display(get_message("queue", "no_tasks"), turns_elapsed)
                continue
            
            # Show queue and prompt
            for slot, task in valid_tasks:
                log_and_display(f"{slot}. {task}", turns_elapsed)
            log_and_display("0. Abort reordering", turns_elapsed)

            del_input = get_input("input", "manage_task_to_remove")
            index = int(del_input)
            if del_input.isdigit():
                if 0 < index <= len(queue):
                    # Clear selected task
                    removed = queue[del_input]["task"]
                    queue[del_input]["task"] = ""
                    queue[del_input]["item"] = ""
                    new_order = []

                    # Append all other tasks (skipping the moved one)
                    for slot in ["1", "2", "3"]:
                        if queue[slot]["task"]:
                            new_order.append(queue[slot])

                    # Rebuild the queue dict in order
                    for idx, slot in enumerate(["1", "2", "3"]):
                        if idx < len(new_order):
                            queue[slot] = new_order[idx]
                        else:
                            queue[slot] = {"task": "", "item": ""}

                    log_and_display(get_message("queue", "removed_task", character=character, pos=del_input, queued_task=removed), turns_elapsed)
                elif index == 0:
                    log_and_display(get_message("queue", "removed_task_abort", character=character), turns_elapsed)
                else:
                    log_and_display(get_message("queue", "removed_task_invalid", character=character, position=del_input), turns_elapsed)
            else:
                log_and_display(get_message("queue", "removed_task_invalid", character=character, position=del_input), turns_elapsed)

        elif choice == "0":
            log_and_display(get_message("queue", "manage_finished", character=character), turns_elapsed)
            break

        else:
            log_and_display(get_message("queue", "invalid_option"), turns_elapsed)

    return task_package


def get_full_character_tasks(name, humans, droids):
    if name in humans:
        status = humans[name]["state"]
        current = humans[name]["task"] if humans[name]["task"] else "--Idle--"
        queue = humans[name]["queue"]
    elif name in droids:
        from constants import FULL_CHARGE
        charge = droids[name]["charge"]
        status = f"{int((charge / FULL_CHARGE) * 100)}%"
        current = droids[name]["task"] if droids[name]["task"] else "--Idle--"
        queue = droids[name]["queue"]
    else:
        return "", ""

    # Build queue entries
    queue_items = []
    for i in ["1", "2", "3"]:
        task = queue[i]["task"]
        queue_items.append(task.capitalize() if task else "--none--")

    queued_msg = f"Queued:  1:{queue_items[0]:<10}  2:{queue_items[1]:<10}  3:{queue_items[2]:<10}"

    # Format with fixed widths
    msg = f"{name:<10} ({status:<5})  {current:<10}  --  {queued_msg}"
    return msg, queued_msg


def reorder_queue_to_top(queue, slot_to_move):
    """Moves the task in the given slot to the top of the queue."""
    selected = queue[slot_to_move]
    new_order = [selected]
    for slot in ["1", "2", "3"]:
        if slot != slot_to_move and queue[slot]["task"]:
            new_order.append(queue[slot])
    for idx, slot in enumerate(["1", "2", "3"]):
        queue[slot] = new_order[idx] if idx < len(new_order) else {"task": "", "item": ""}
    return queue