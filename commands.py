# commands.py

import random

from command_utils import create_task
from constants import (TASK_CHARGING, TASK_EXPLORING, TASK_PLANTING, TASK_REAPING, TASK_EXAMINING, TASK_MINING, TASK_ASSIGNED, TASK_EATING,
                       TASK_REFUELING, CHARGE_DURATION, TASK_LENGTH, ASSIGNABLE_ITEMS, LOW_CHARGE_FLAG, IDLE_CHARGE_USAGE,
                       POWER_PER_RED, POWER_PER_INDIGO, POWER_PER_GOLD, NUM_DROIDS, FULL_CHARGE)
from lore.lore_ingame import get_message
from lore.user_interface import get_input, log_and_display
from planting import determine_what_to_plant_and_where
from utils import (get_best_match, get_pronouns, can_character_act, set_shield_state, clear_task_for_character, set_task_status_for_character,
                   get_integer_input, parse_command_targets)
from queuing import add_to_queue, is_idle


def set_task_length(task_type):
    low, high = TASK_LENGTH[task_type]
    return random.randint(low, high)


def handle_immediate_or_queued_task(action, qualifier, task_package):
    valid_command = True

    # ---- TASK DISPATCH ----
    if action == "feed" or action == TASK_EATING:
        task_package = initiate_feed_task(qualifier, task_package)

    elif action == "charge" or action == TASK_CHARGING:
        task_package = initiate_charge_task(qualifier, task_package)

    elif action == "explore" or action == TASK_EXPLORING:
        task_package = initiate_explore_task(qualifier, task_package)

    elif action == "examine" or action == TASK_EXAMINING:
        task_package = initiate_examine_task(qualifier, task_package)

    elif action == "plant" or action == TASK_PLANTING:
        task_package = initiate_plant_task(qualifier, task_package)

    elif action == "reap" or action == TASK_REAPING:
        task_package = initiate_reap_task(qualifier, task_package)

    elif action == "mine" or action == TASK_MINING:
        task_package = initiate_mine_task(qualifier, task_package)

    elif action == "assign" or action == TASK_ASSIGNED:
        task_package = handle_assign_command(qualifier, task_package)

    elif action == "refuel" or action == TASK_REFUELING:
        task_package = initiate_refuel_task(qualifier, task_package)

    else:
        valid_command = False

    return valid_command, task_package


def initiate_feed_task(qualifier, task_package):
    # Feed those humans (or droids?)
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["turns_elapsed"]
    task_type = TASK_EATING

    # Step 1: Get targets (either from qualifier or prompt)
    if not qualifier:
        feed_targets = get_input("input", "feed", turns_elapsed)
    else:
        feed_targets = qualifier

    # Step 2: Normalise targets into a LIST
    # (so we never accidentally iterate over characters)
    if isinstance(feed_targets, str):
        feed_targets = feed_targets.split()

    duration = set_task_length("feed_human")

    # Step 3: Handle special keywords
    if feed_targets == ["all"]:
        for name in humans:

            # If they are not idle, add this action to their queue
            if not is_idle(name, humans, droids):
                success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
                if not success:
                    log_and_display(get_message("queue", "not_queued", name=name, task=task_type), turns_elapsed)
                continue

            is_human = True
            # Create the task
            return_msg, task_package = create_task(name, task_type, duration, task_package)
            
            log_and_display(return_msg, turns_elapsed)

        return task_package

    if feed_targets == ["hungry"]:
        hungry_people = [name for name, h in humans.items() if h["hunger"] >= 5]
        is_human = True
        if not hungry_people:
            log_and_display("feed", "no_hungry_humans", turns_elapsed)
            return task_package
        
        for name in hungry_people:        
            # If they are not idle, add this action to their queue
            if not is_idle(name, humans, droids):
                success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
                if not success:
                    log_and_display(get_message("queue", "not_queued", name=name, task=task_type), turns_elapsed)
                continue

            # Create the task
            return_msg, task_package = create_task(name, task_type, duration, task_package)
            log_and_display(return_msg, turns_elapsed)
            
        return task_package

    # Step 4: Handle individual targets
    for raw_target in feed_targets:
        target = get_best_match(raw_target, list(humans.keys()) + list(droids.keys()))

        # If they are not idle, add this action to their queue
        if not is_idle(target, humans, droids) and target in humans:
            success, humans, droids = add_to_queue(target, humans, droids, turns_elapsed, task_type)
            if not success:
                log_and_display(get_message("queue", "not_queued", name=target, task=task_type), turns_elapsed)
            continue

        is_human = target in humans
        if is_human:
            # Create the task
            return_msg, task_package = create_task(name, task_type, duration, task_package)
        elif target in droids:
            log_and_display(get_message("feed_droid", "responses", droid_name=target), turns_elapsed)
        else:
            log_and_display(get_message("error", "feed_invalid", person_name=raw_target), turns_elapsed)

        log_and_display(return_msg, turns_elapsed)

    return task_package


def initiate_charge_task(qualifier, task_package):
    # Assign charging tasks to one or more droids if PowerSupply allows
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]
    task_type = TASK_CHARGING

    power_resource = next((r for r in resources if r.get("name") == "PowerSupply"), None)

    if not power_resource or not power_resource.get("found", False):
        log_and_display(get_message("charge", "nowhere_to_charge"), turns_elapsed)
        return task_package

    if power_resource["amount"] < 100:
        log_and_display(get_message("charge", "not_enough_power"), turns_elapsed)
        return task_package

    charge_targets = parse_command_targets(qualifier, humans, droids, turns_elapsed, task_type=TASK_CHARGING)
    if charge_targets == None:
        return task_package

    duration = CHARGE_DURATION
    threshold = LOW_CHARGE_FLAG * IDLE_CHARGE_USAGE

    for name in charge_targets:
        if name in droids:
            charge_level = droids[name]["charge"]

            # If they are not idle, add this action to their queue
            if not is_idle(name, humans, droids):
                success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
                if not success:
                    log_and_display(get_message("queue", "not_queued", name=name, task=task_type), turns_elapsed)
                continue

            if "low" in qualifier and charge_level > threshold:
                log_and_display(get_message("charge", "charge_above_low", target=name), turns_elapsed)
                continue

            if charge_level >= 800:
                log_and_display(get_message("charge", "charge_full", droid_name=name), turns_elapsed)
                continue

            # Create the task
            return_msg, task_package = create_task(name, task_type, duration, task_package)
            log_and_display(return_msg, turns_elapsed)

        elif name in humans:
            log_and_display(get_message("charge", "wrong_target", target=name), turns_elapsed)

        else:
            log_and_display(get_message("charge", "no_target"), turns_elapsed)

    return task_package


def initiate_explore_task(qualifier, task_package):
    # Send some character exploring on a mission to find *something*
    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["turns_elapsed"]
    task_type = TASK_EXPLORING

    explore_targets = parse_command_targets(qualifier, humans, droids, turns_elapsed, tasks, task_type=TASK_EXPLORING)
    if explore_targets == None:
        return task_package

    for raw_target in explore_targets:
        okay_to_act, is_human, name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed)
        if not okay_to_act:
            continue  # Skip to the next target

        # If they are not idle, add this action to their queue
        success = False
        if not is_idle(name, humans, droids):
            success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
            if not success:
                log_and_display(get_message("queue", "not_queued", name=name, task=task_type), turns_elapsed)
            continue

        if is_human:
            duration = set_task_length("explore_human")
        else:
            duration = set_task_length("explore_droid")

        # Create the task
        return_msg, task_package = create_task(name, task_type, duration, task_package)
        log_and_display(return_msg, turns_elapsed)

    return task_package


def initiate_plant_task(qualifier, task_package):
    # Plant some real goddamn food
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]
    crops = task_package["crops"]
    task_data = task_package["task_data"]
    task_type = TASK_PLANTING

    if not task_data:   # This takes care of the 'initial task' versus a queued task
        good_msg, name, crop_instructions, resources = determine_what_to_plant_and_where(
                qualifier, crops, resources, humans, droids, turns_elapsed)

        if not good_msg:
            return task_package
    else:
        crop_instructions = task_data

    # Create plant task
    is_human = name in humans
    duration = set_task_length("plant_human")
    if not is_human: 
        duration = set_task_length("plant_droid")
    
    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, task_data=crop_instructions)
        if not success:
            log_and_display(get_message("queue", "not_queued", name=name, task=task_type), turns_elapsed)
        return task_package

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    log_and_display(return_msg, turns_elapsed)

    return task_package


def initiate_examine_task(raw_examiner, task_package):
    # Examine something - or just glance at it
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]
    item_name = task_package["item"]
    task_type = TASK_EXAMINING

    # Get targets (either from qualifier or prompt)
    if not raw_examiner:
        raw_examiner = get_input("input", "examine", turns_elapsed)

    # First check if the character can do the examine
    okay_to_act, is_human, name = can_character_act(raw_examiner, task_type, humans, droids, turns_elapsed)
    if not okay_to_act:
        return task_package
    
    if item_name == "":
        # Find discovered items that are examinable and haven't been examined yet
        examinable_items = [item["name"] for item in resources if (item["examinable"] and not item["examined"])]
    
        if not examinable_items:
            log_and_display(get_message("examine", "nothing_examinable"), turns_elapsed)
            return task_package

        # If not accepted to assign, just return
        item_name, current_examinee, accepted = get_examinable_item(humans, droids, examinable_items, name, turns_elapsed)
        if not accepted:
            return task_package

    # Find the target item
    item = next((r for r in resources if r["name"] == item_name), None)
    if not item:
        log_and_display(get_message("examine", "not_found", item=item_name), turns_elapsed)
        return task_package
    
    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item=item_name)
        if not success:
            log_and_display(get_message("queue", "not_queued", name=name, task=task_type), turns_elapsed)
        return task_package

    # Immediate?
    if item.get("examine_turns", 0) <= 0:
        new_msg = item["msg"].format(name=name, R=item.get("red", ""), I=item.get("indigo", ""), G=item.get("gold", ""),
                A=item.get("apple",""), C=item.get("cabbage",""), P=item.get("potato",""),  amount=item.get("amount", ""))
        formatted_msg = f"{item_name}: " + new_msg
        log_and_display(formatted_msg, turns_elapsed)
        item["examined"] = True
        item["msg"] = new_msg
        return task_package

    # Unassign previous examiner, if any
    if current_examinee:
        humans, droids = clear_task_for_character(current_examinee, item_name, humans, droids)
        log_and_display(get_message("examine", "reassigned", item=item_name, previous=current_examinee, new=name), turns_elapsed)

    # Create the task
    return_msg, task_package = create_task(name, task_type, item.get("examine_turns", 0), task_package)
    log_and_display(return_msg, turns_elapsed)
    
    return task_package


def initiate_reap_task(raw_target, task_package):
    # Reap those crops! Food is needed.
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["turns_elapsed"]
    crops = task_package["crops"]
    task_type = TASK_REAPING

    # Get targets (either from qualifier or prompt)
    if not raw_target:
        raw_target = get_input("input", "reap", turns_elapsed)

    okay_to_act, is_human, name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed)
    if not okay_to_act:
        return task_package
        
    # Warn if nothing is ready
    mature_exists = any(crop.get("mature", False) for crop in crops.values())
    if not mature_exists:
        log_and_display(get_message("reap", "no_mature_crops", target=name), turns_elapsed)
        # Allow them to continue anyway (they may have a plan for this)

    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
        if not success:
            log_and_display(get_message("queue", "not_queued", name=name, task=task_type), turns_elapsed)
        return task_package

    # Now create the reap task
    duration = set_task_length("reap_human")
    if not is_human:
        duration = set_task_length("reap_droid")
        
    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    log_and_display(return_msg, turns_elapsed)
    
    return task_package


def initiate_mine_task(qualifier, task_package):
    # Assign one or more characters to mine in the CrystalField
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["turns_elapsed"]
    task_type = TASK_MINING

    mine_targets = parse_command_targets(qualifier, humans, droids, turns_elapsed, tasks, task_type=TASK_MINING)
    if mine_targets == None:
        return task_package

    for raw_target in mine_targets:
        okay_to_act, is_human, name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed)
        if not okay_to_act:
            continue  # Skip invalid or busy characters

        # Initialise PowerSupply CrystalStore if not already done
        for r in resources:
            if r.get("name") == "PowerSupply":
                if "CrystalStore" not in r or not r["CrystalStore"]:
                    r["CrystalStore"] = {"red": 0, "indigo": 0, "gold": 0}
                break

        # If they are not idle, add this action to their queue
        if not is_idle(name, humans, droids):
            success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
            if not success:
                log_and_display(get_message("queue", "not_queued", name=name, task=task_type), turns_elapsed)
            return task_package

        # Assign mining task
        duration = set_task_length("mine_human") if is_human else set_task_length("mine_droid")

        # Create the task
        return_msg, task_package = create_task(name, task_type, duration, task_package)

        log_and_display(return_msg, turns_elapsed)

    return task_package


def initiate_refuel_task(raw_target, task_package):
    # Refuel the all-important power supply
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]
    task_type = TASK_REFUELING

    # Get targets (either from qualifier or prompt)
    if not raw_target:
        raw_target = get_input("input", "refuel", turns_elapsed)

    okay_to_act, is_human, name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed)
    if not okay_to_act:
        return task_package

    # Find PowerSupply
    power_supply = next((r for r in resources if r.get("name") == "PowerSupply"), None)
    if not power_supply or not power_supply.get("found", False):
        log_and_display(get_message("refuel", "no_power_supply"),
                        turns_elapsed)
        return task_package

    # Warn if no vials (but allow assignment)
    vial_store = power_supply.get("VialStore", {})
    if not vial_store or all(v == 0 for v in vial_store.values()):
        log_and_display(get_message("refuel", "no_vials_warning", name=name), turns_elapsed)

    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
        if not success:
            log_and_display(get_message("queue", "not_queued", name=name, task=task_type), turns_elapsed)
        return task_package

    # Create task
    task_type = TASK_REFUELING
    key = "refuel_human" if is_human else "refuel_droid"
    duration = set_task_length(key)

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    log_and_display(return_msg, turns_elapsed)

    return task_package


def handle_assign_command(raw_target, task_package):
    # Assign a character to something useful (hopefully)
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    tasks = task_package["tasks"]
    task_number = task_package["task_number"]
    turns_elapsed = task_package["turns_elapsed"]
    shieldstate = task_package["shieldstate"]
    item_name = task_package["item"]
    task_name = TASK_ASSIGNED
    
    if item_name == "":
        # Find discovered assignable items
        discovered_items = [item["name"] for item in resources if item["name"] in ASSIGNABLE_ITEMS]
    
        if not discovered_items:
            log_and_display(get_message("assign", "nothing_assignable"), turns_elapsed)
            return task_package

    # Get targets (either from qualifier or prompt)
    target = ""
    if not raw_target:
        raw_target = get_input("input", "assignee", turns_elapsed, full_list=discovered_items)
    
    okay_to_act, is_human, target = can_character_act(raw_target, task_name, humans, droids, turns_elapsed)
    if not okay_to_act:
        return task_package

    if item_name == "":
        # If not accepted to assign, just return
        item_name, current_assignee, accepted, humans, droids = get_new_assignee(humans, droids, discovered_items, target, turns_elapsed)
        if not accepted:
            return task_package

    # ---- Begin assignment ----
    task_created = False

    if item_name == "CrystalProcessor":
        task_created, tasks, task_number, humans, droids = initiate_assign_process_task(target, humans, droids, resources, tasks, task_number, turns_elapsed)
    elif item_name == "ShieldManual":
        task_created, tasks, task_number, humans, droids = initiate_assign_shieldmanual_task(target, humans, droids, resources, tasks, task_number, turns_elapsed)
    elif item_name == "OldTerminal":
        # Instant assignment: no task, no turn consumed
        task_created = True
        log_and_display(get_message("assign", "old_terminal_assigned", name=target), turns_elapsed)
        humans, droids, resources, shieldstate = enter_oldterminal_commands(target, humans, droids, resources, turns_elapsed, shieldstate)
    elif item_name == "CloakingShield":
        task_created = True
        droids, shieldstate, humans = check_shield_assign(target, droids, humans, resources, shieldstate, turns_elapsed)

    if task_created:
        # Unassign previous assignee, if any
        if current_assignee and current_assignee != target:   # i.e. not a reassign
            humans, droids = clear_task_for_character(current_assignee, item_name, humans, droids)
            log_and_display(get_message("assign", "reassigned", item=item_name, old=current_assignee, new=target), turns_elapsed)

    return task_package


def get_new_assignee(humans, droids, discovered_items, target, turns_elapsed):
    accepted = True
    item_name = ""
    current_assignee = ""

    menu = []
    assignees = {}
    for i, item in enumerate(discovered_items):
        assigned = None
        for h in humans:
            if humans[h].get("task") == TASK_ASSIGNED:
                if humans[h].get("item") == item:
                    assigned = h
                    break
        if not assigned:
            for d in droids:
                if droids[d].get("task") == TASK_ASSIGNED:
                    if droids[d].get("item") == item:
                        assigned = d
                        break
        assignees[item] = assigned
        label = f"{i+1}. {item}"
        if assigned:
            label += f" (currently assigned: {assigned})"
        menu.append(label)

    # Add abort option
    menu.append("0. Cancel assignment")

    choice = get_input("input", "assigned_item", turns_elapsed, name=target, full_list=menu)
    
    if not choice.isdigit():
        log_and_display(get_message("assign", "invalid_choice"), turns_elapsed)
        accepted = False
        return "", "", accepted

    choice = int(choice)
    if choice == 0:
        log_and_display(get_message("assign", "assignment_aborted"), turns_elapsed)
        accepted = False
    elif 1 <= choice <= len(discovered_items):
        item_name = discovered_items[choice - 1]
        current_assignee = assignees[item_name]
        accepted = True
        set_task_status_for_character(target, TASK_ASSIGNED, item_name, humans, droids, turns_elapsed)
    else:
        log_and_display(get_message("assign", "invalid_choice"), turns_elapsed)
        accepted = False

    return item_name, current_assignee, accepted, humans, droids


def initiate_assign_process_task(name, humans, droids, resources, tasks, task_number, turns_elapsed):
    # Assign a human or droid to process selected crystals using the CrystalProcessor.
    task_type = TASK_ASSIGNED
    item_name = "CrystalProcessor"

    # Find the PowerSupply and ensure it has CrystalStore
    power_supply = next((r for r in resources if r.get("name") == "PowerSupply"), None)
    if not power_supply or "CrystalStore" not in power_supply:
        log_and_display(get_message("assign", "process_no_crystals", name=name, item=item_name), turns_elapsed)
        return False, tasks, task_number, humans, droids

    crystal_store = power_supply["CrystalStore"]
    if all(crystal_store[color] == 0 for color in ["red", "indigo", "gold"]):
        log_and_display(get_message("assign", "process_no_crystals", name=name, item=item_name), turns_elapsed)
        return False, tasks, task_number, humans, droids

    # Find the CrystalProcessor
    processor = next((r for r in resources if r.get("name") == item_name and r.get("found", False)), None)
    if not processor:
        log_and_display(get_message("assign", "no_processor", item=item_name), turns_elapsed)
        return False, tasks, task_number, humans, droids

    # Ensure VialStore exists
    if "VialStore" not in power_supply:
        power_supply["VialStore"] = {"red": 0, "indigo": 0, "gold": 0}

    # Prompt for quantity of each crystal type
    red_avail = crystal_store["red"]
    indigo_avail = crystal_store["indigo"]
    gold_avail = crystal_store["gold"]

    red = get_integer_input(f"How many RED crystals to process? (0–{red_avail}): ", 0, red_avail)
    indigo = get_integer_input(f"How many INDIGO crystals to process? (0–{indigo_avail}): ", 0, indigo_avail)
    gold = get_integer_input(f"How many GOLD crystals to process? (0–{gold_avail}): ", 0, gold_avail)

    if red == 0 and indigo == 0 and gold == 0:
        log_and_display("No crystals selected for processing. Task cancelled.", turns_elapsed)
        return False, tasks, task_number, humans, droids

    total_power = red*POWER_PER_RED + indigo*POWER_PER_INDIGO + gold*POWER_PER_GOLD
    full_charge_all = NUM_DROIDS*FULL_CHARGE
    num_days=total_power/full_charge_all
    days_per_full_charge = FULL_CHARGE/(10*IDLE_CHARGE_USAGE)
    if full_charge_all > total_power:
        num_days = 1
        num_droids = total_power // 10*IDLE_CHARGE_USAGE
    else:
        num_days = total_power//(full_charge_all/days_per_full_charge)
        num_droids = NUM_DROIDS
    log_and_display(get_message("assign", "CP_estimate", target=name, total_power=total_power, num=num_droids, day=num_days), turns_elapsed)

    # Determine duration and create task
    is_human = name in humans
    duration = set_task_length("assign_human_process") if is_human else set_task_length("assign_droid_process")

    task_data = {
        "process_red": red,
        "process_indigo": indigo,
        "process_gold": gold
    }

    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item=item_name, task_data=task_data)
        if not success:
            log_and_display(get_message("assign", "not_queued", name=name), turns_elapsed)
        return True, tasks, task_number, humans, droids

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    log_and_display(return_msg, turns_elapsed)

    return True, tasks, task_number, humans, droids


def initiate_assign_shieldmanual_task(name, humans, droids, resources, tasks, task_number, turns_elapsed):

    task_type = TASK_ASSIGNED
    item_name = "ShieldManual"

    # ---- Find ShieldManual ----
    manual = next((r for r in resources if r.get("name") == item_name), None)
    if not manual or not manual.get("found", False):
        log_and_display(get_message("assign", "no_manual", item=item_name), turns_elapsed)
        return False, tasks, task_number, humans, droids
    
    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        success, humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item=item_name)
        if not success:
            log_and_display(get_message("assign", "not_queued", name=name), turns_elapsed)
        return True, tasks, task_number, humans, droids

    # ---- Create task ----
    is_human = name in humans

    if is_human:
        duration = set_task_length("assign_human_manual")
    else:
        duration = set_task_length("assign_droid_manual")

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    
    return True, tasks, task_number, humans, droids


def check_shield_assign(target, droids, humans, resources, shieldstate, turns_elapsed):
    is_droid = target in droids
    task_type = TASK_ASSIGNED

    # If they are not idle, add this action to their queue
    if not is_idle(target, humans, droids):
        success, humans, droids = add_to_queue(target, humans, droids, turns_elapsed, task_type)
        if not success:
            log_and_display(get_message("queue", "not_queued", name=target, task=task_type), turns_elapsed)
        return droids, shieldstate, humans

    if is_droid or not shieldstate["manual_decoded"]: # Can allow anyone to be assigned to the shield IF the manual is NOT decoded, but only droids if it is
        log_and_display(get_message("shield", "assigned_to", target=target), turns_elapsed)

        # Check that it was the droid with the Anicent Code that we assigned
        ancient_code = next((r for r in resources if r["name"] == "AncientDroidCode"), None)
        if ancient_code:
            if ancient_code["droidName"] == target:
                shieldstate = set_shield_state("C", droids, resources, shieldstate)
                droids[target]["charge"] = FULL_CHARGE  # When they are connected they have full charge
        else:
            log_and_display(get_message("shield", "code_not_found", name=target), turns_elapsed)

    else:
        log_and_display(get_message("shield", "cannot_assign_human", target=target), turns_elapsed)
      
    return droids, shieldstate, humans


def enter_oldterminal_commands(worker_name, humans, droids, resources, turns_elapsed, shieldstate):

    # Inline function - can't import from tasks.py - creates conflicts
    def do_we_have_enough(resources):
        available_crystals = {"red": 0, "indigo": 0, "gold": 0}
        for res in resources:
            if res.get("name") == "PowerSupply" and res.get("found"):
                crystal_store = res.get("CrystalStore")
                if crystal_store:
                    available_crystals["red"] = crystal_store["red"]
                    available_crystals["indigo"] = crystal_store["indigo"]
                    available_crystals["gold"] = crystal_store["gold"]
        return available_crystals

    # If they are not idle, add this action to their queue
    task_type = TASK_ASSIGNED
    item_name = "OldTerminal"
    if not is_idle(worker_name, humans, droids):
        success, humans, droids = add_to_queue(worker_name, humans, droids, turns_elapsed, task_type, item=item_name)
        if not success:
            log_and_display(get_message("assign", "not_queued", name=worker_name), turns_elapsed)
        return humans, droids, resources, shieldstate

    if not shieldstate.get("manual_decoded", False):
        if worker_name in droids:
            is_human = False
        pronouns = get_pronouns(worker_name, is_human)
        log_and_display(get_message("shield", "terminal_unreadable", name=worker_name, pronoun=pronouns["p1"].lower()), turns_elapsed)
        return humans, droids, resources, shieldstate

    crystal_combo = next((r for r in resources if r["name"] == "CrystalCombination"), None)

    if not crystal_combo:
        log_and_display(get_message("shield", "need_combo", name=worker_name), turns_elapsed)
        return humans, droids, resources, shieldstate

    if not crystal_combo.get("examined", False):
        log_and_display(get_message("shield", "combo_not_examined", name=worker_name), turns_elapsed)
        return humans, droids, resources, shieldstate

    # Offer to use the combination
    response = get_input("input", "oldterminal", turns_elapsed)

    # Count available crystals and abort if there aren't enough
    available_crystals = do_we_have_enough(resources)
    if crystal_combo["red"] > available_crystals.get("red",0) or crystal_combo["indigo"] > available_crystals.get("indigo",0) or crystal_combo["gold"] > available_crystals.get("gold",0):
        log_and_display(get_message("shield", "not_enough_crystals_with_combo", 
                                    need_R=crystal_combo["red"], need_I=crystal_combo["indigo"], need_G=crystal_combo["gold"], 
                                    have_R=available_crystals.get("red",0), have_I=available_crystals.get("indigo",0), have_G=available_crystals.get("gold",0)), turns_elapsed)
        return humans, droids, resources, shieldstate
    
    # All good, so send the message to the player
    elif response in ["yes", "y"]:
        log_and_display(get_message("shield", "combo_correct", name=worker_name), turns_elapsed)
        shieldstate = set_shield_state("D", droids, resources, shieldstate)

        # Remove the crystals from the crystal store
        power_supply = next((r for r in resources if r["name"] == "PowerSupply"), None)
        crystal_store = power_supply["CrystalStore"]
        crystal_store["red"] -= crystal_combo["red"]
        crystal_store["indigo"] -= crystal_combo["indigo"]
        crystal_store["gold"] -= crystal_combo["gold"]

    else:
        log_and_display(get_message("shield", "combo_correct_aborted", name=worker_name), turns_elapsed)
        return humans, droids, resources, shieldstate

    is_droid = worker_name in droids
    if is_droid:    # Any droid can be assigned to the OldTerminal
        shieldstate = set_shield_state("E", droids, resources, shieldstate)
    else:
        log_and_display(get_message("shield", "terminal_cannot_assign_human", target=worker_name), turns_elapsed)

    return humans, droids, resources, shieldstate


def get_examinable_item(humans, droids, examinable_items, target, turns_elapsed):
    accepted = True
    item_name = ""
    current_examiner = ""

    examinable_items.sort()
    menu = []
    examinees = {}
    for i, item in enumerate(examinable_items):
        already_being_examined = None
        for h in humans:
            if humans[h].get("item") == item:
                already_being_examined = h
                break
        if not already_being_examined:
            for d in droids:
                if droids[d].get("item") == item:
                    already_being_examined = d
                    break
        examinees[item] = already_being_examined
        label = f"{i+1}. {item}"
        if already_being_examined:
            label += f" (currently being examined by: {already_being_examined})"
        menu.append(label)

    # Add abort option
    menu.insert(0, "0. Cancel examine task")

    choice = get_input("inpit", "examine_what", turns_elapsed, target=target, items=menu)

    if not choice.isdigit():
        log_and_display(get_message("examine", "invalid_choice"), turns_elapsed)
        accepted = False
        return "", "", accepted

    choice = int(choice)
    if choice == 0:
        log_and_display(get_message("examine", "examine_aborted"), turns_elapsed)
        accepted = False
    elif 1 <= choice <= len(examinable_items):
        item_name = examinable_items[choice - 1]
        current_examiner = examinees[item_name]
    else:
        log_and_display(get_message("examine", "invalid_choice"), turns_elapsed)
        accepted = False

    return item_name, current_examiner, accepted