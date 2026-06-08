# command_utils.py

import os

from constants import (TASK_ASSIGNED, TASK_CHARGING, TASK_EXAMINING, TASK_EXPLORING, TASK_EATING, TASK_MINING, TASK_PLANTING, TASK_REAPING, 
                       TASK_REFUELING, TASK_TOWING_DROID, AVAILABLE_FILES, POWER_PER_RED, POWER_PER_INDIGO, POWER_PER_GOLD, FULL_CHARGE)
from lore.lore_ingame import get_message
from lore.lore_story import get_story_message
import lore.user_interface as ui_runtime
from lore.user_interface import get_input, msg_story, msg_info, log_and_display, get_confirm, get_integer_input
from utils import get_pronouns, clear_task_for_character, set_task_status_for_character


def create_task(name, task_type, duration, task_package):
    tasks = task_package["tasks"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    item_name = task_package["item"]
    task_data = task_package["task_data"]
    return_msg = ""
    is_human = name in humans
    pronouns = get_pronouns(name, is_human=is_human)

    # Now display the user message
    # Need to adust for duration as the tasks will be decremented at the end of the turn.
    if duration-1 == 1:
        turn_msg = "1 turn"
    else:
        turn_msg = f"{duration-1} turns"
    if task_type == TASK_EATING:
        return_msg = get_message("feed", "commenced", person_name=name, turn_msg=turn_msg, pronoun=pronouns["p1"])
    elif task_type == TASK_CHARGING:
        return_msg = get_message("charge", "commenced", target=name, turn_msg=turn_msg)
    elif task_type == TASK_EXPLORING:
        return_msg = get_message("explore", "commenced", target=name, turn_msg=turn_msg, pronoun=pronouns["p1"].lower())
    elif task_type == TASK_PLANTING:
        return_msg = get_message("plant", "commenced", target=name, turn_msg=turn_msg)
    elif task_type == TASK_REAPING:
        return_msg = get_message("reap", "commenced", target=name, turn_msg=turn_msg, pronoun=pronouns["p1"])
    elif task_type == TASK_EXAMINING:
        return_msg = get_message("examine", "commenced", name=name, turn_msg=turn_msg, item=item_name, pronoun=pronouns["p1"].lower())
    elif task_type == TASK_MINING:
        return_msg = get_message("mine", "commenced", target=name, turn_msg=turn_msg)
    elif task_type == TASK_ASSIGNED:
        return_msg = get_message("assign", "commenced", name=name, turn_msg=turn_msg, item=item_name)
    elif task_type == TASK_REFUELING:
        return_msg = get_message("refuel", "commenced", target=name, turn_msg=turn_msg, item=item_name)
    elif task_type == TASK_TOWING_DROID:
        return_msg = get_message("charge", "towing", name=name, droid_being_towed=item_name, turn_msg=turn_msg)
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
    elif task_type == TASK_PLANTING or task_type == TASK_REFUELING:
        tasks[str(task_id)]["task_data"] = task_data

    # Set the status for the character
    set_task_status_for_character(name, task_type, item_name, humans, droids, task_package["counters"]["turns"])

    return return_msg, task_package


def handle_read_command(task_package, turns_elapsed, subject=None):
    # If no subject specified, enter local sub-loop
    can_read_these = []
    if subject is None:
        # Only list files that exist or are always-available lore entries
        for key, filename in AVAILABLE_FILES.items():
            if key == "orders" or os.path.exists(filename):
                choice = f"{key}"
                can_read_these.append(choice)

        can_read_these.append('quit: read nothing')
        if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
                ui_runtime.ACTIVE_UI.set_pending_question(
                    callback=resume_read_command,
                    context={
                        "task_package": task_package,
                    }
                )
        answer = get_input("input", "read", turns_elapsed, files=can_read_these)

        if answer and answer == ui_runtime.GUI_PENDING:
            return None


def resume_read_command(subject, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    if subject == "quit":
        log_and_display("", turns_elapsed)
        msg_info(get_message("read", "quit"), turns_elapsed)
        return
    
    # Now continue as before
    if subject in AVAILABLE_FILES:
        if subject == "orders":
            msg_story(get_message("read", "here_it_is", subject=subject), turns_elapsed)
            messages = get_story_message("orders", "message")
            for line in messages:
                log_and_display("\n" + line, turns_elapsed, log=False)  # Don't re-display this in the log
        else:
            filename = AVAILABLE_FILES[subject]

            with open(filename, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if os.path.exists(filename):
                msg_story(get_message("read", "here_it_is", subject=subject), turns_elapsed)
                log_and_display("".join(lines), turns_elapsed, log=False)
            else:
                msg_info(get_message("read", "no_subject", subject=subject), turns_elapsed)

        log_and_display("", turns_elapsed)
        msg_info(get_message("read", "nothing_further"), turns_elapsed)
    else:
        msg_info(get_message("read", "no_content", subject=subject), turns_elapsed)


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
    # Moves the task in the given slot to the top of the queue.
    selected = queue[slot_to_move]
    new_order = [selected]
    for slot in ["1", "2", "3"]:
        if slot != slot_to_move and queue[slot]["task"]:
            new_order.append(queue[slot])
    for idx, slot in enumerate(["1", "2", "3"]):
        queue[slot] = new_order[idx] if idx < len(new_order) else {"task": "", "item": ""}
    return queue


def is_droid_being_charged_or_towed(droid_name, task_package):
    droids = task_package["droids"]
    humans = task_package["humans"]

    if any(droids[d]["task"] == TASK_CHARGING and d == droid_name for d in droids):
        return True

    if any(humans[h]["task"] == TASK_TOWING_DROID and humans[h]["item"] == droid_name for h in humans):
        return True

    return False


def get_refuel_power_supply_and_vials(name, task_package):
    resources = task_package["resources"]
    humans = task_package["humans"]
    droids = task_package["droids"]

    power_supply = next((r for r in resources if r.get("name") == "PowerSupply"), None)

    if not power_supply:
        return_msg = get_message("refuel", "no_power_supply")
        humans, droids = clear_task_for_character(name, "", humans, droids)
        return None, None, return_msg

    vial_store = power_supply.get("VialStore", {})

    if not vial_store or all(v == 0 for v in vial_store.values()):
        return_msg = get_message("refuel", "no_vials_fail", name=name)
        humans, droids = clear_task_for_character(name, "", humans, droids)
        return power_supply, None, return_msg

    return power_supply, vial_store, ""


def choose_vials_and_display_power_produced(name, task_package, amount_only=False):
    # Estimate how much power this will produce, or apply power after refuelling.
    turns_elapsed = task_package["counters"]["turns"]
    task_data = task_package.get("task_data", {})

    return_msg = ""
    total_power = 0
    red = indigo = gold = 0

    power_supply, vial_store, error_msg = get_refuel_power_supply_and_vials(name, task_package)

    if error_msg:
        return error_msg, total_power, task_package, red, indigo, gold

    if amount_only:
        # We are summarising after the fact, from complete_refuel_task().
        if task_data:
            red = task_data.get("red", 0)
            indigo = task_data.get("indigo", 0)
            gold = task_data.get("gold", 0)

        total_power = (
            red * POWER_PER_RED +
            indigo * POWER_PER_INDIGO +
            gold * POWER_PER_GOLD
        )

        power_supply["amount"] += total_power

        if total_power == 0:
            return_msg = "As there were no vials of crystal dust chosen, no power can be generated."
        else:
            return_msg = (
                f"Total power added to the PowerSupply from {red} red crystal vials, "
                f"{indigo} indigo crystal vials and {gold} gold crystal vials was {total_power} units."
            )

        return return_msg, total_power, task_package, red, indigo, gold

    # CLI fallback path only.
    return choose_vials_for_refuel_cli(name, task_package, power_supply, vial_store)


def choose_vials_for_refuel_cli(name, task_package, power_supply, vial_store):
    turns_elapsed = task_package["counters"]["turns"]

    return_msg = ""
    total_power = 0
    red = indigo = gold = 0

    red_avail = vial_store.get("red", 0)
    indigo_avail = vial_store.get("indigo", 0)
    gold_avail = vial_store.get("gold", 0)

    use_all = get_confirm("Would you like to use all available crystal vials for refuelling? (y/n): ", turns_elapsed)

    if use_all:
        red = red_avail
        indigo = indigo_avail
        gold = gold_avail

        total_power = calculate_refuel_power(red, indigo, gold)
        num_days = total_power // FULL_CHARGE

        summary_msg = (
            f"Using all vials will create {total_power} units of power "
            f"(enough to charge a single droid for {num_days} days). Proceed? (y/n)"
        )

        if get_confirm(summary_msg, turns_elapsed):
            remove_vials_from_store(vial_store, red, indigo, gold)

            return_msg = (
                f"{name} will now proceed to use all available vials to refuel the PowerSupply "
                f"and add an extra {total_power} units and {num_days} days' worth of droid charges."
            )

            return return_msg, total_power, task_package, red, indigo, gold

    while True:
        red = get_integer_input(f"How many RED crystals to use for refuelling? (0–{red_avail}): ", 0, red_avail)
        indigo = get_integer_input(f"How many INDIGO crystals to use for refuelling? (0–{indigo_avail}): ", 0, indigo_avail)
        gold = get_integer_input(f"How many GOLD crystals to use for refuelling? (0–{gold_avail}): ", 0, gold_avail )

        if red == 0 and indigo == 0 and gold == 0:
            return_msg = "No crystals selected for processing. Task cancelled."
            return return_msg, total_power, task_package, red, indigo, gold

        total_power = calculate_refuel_power(red, indigo, gold)
        num_days = total_power // FULL_CHARGE

        summary_msg = (
            f"Summary: {red} red, {indigo} indigo, {gold} gold vials will create "
            f"{total_power} units of power "
            f"(enough to charge 1 droid for {num_days} days). Proceed? (y/n)"
        )

        if get_confirm(summary_msg, turns_elapsed):
            break

        retry = get_confirm("Would you like to choose different amounts? (y/n): ", turns_elapsed)

        if not retry:
            return_msg = get_message("refuel", "aborted", name=name)
            return return_msg, total_power, task_package, red, indigo, gold

    return_msg = (
        f"{name} is now going to refuel the PowerSupply with only the amounts you have chosen. "
        f"This will add {total_power} units of power to the system. "
        f"Enough to charge a single droid for {num_days} days."
    )

    remove_vials_from_store(vial_store, red, indigo, gold)

    return return_msg, total_power, task_package, red, indigo, gold


def calculate_refuel_power(red, indigo, gold):
    return (
        red * POWER_PER_RED +
        indigo * POWER_PER_INDIGO +
        gold * POWER_PER_GOLD
    )


def remove_vials_from_store(vial_store, red, indigo, gold):
    vial_store["red"] -= red
    vial_store["indigo"] -= indigo
    vial_store["gold"] -= gold


def get_refuel_days(total_power):
    return total_power // FULL_CHARGE