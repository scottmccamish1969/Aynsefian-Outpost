# commands.py

import random

from command_utils import create_task
from constants import (TASK_CHARGING, TASK_EXPLORING, TASK_PLANTING, TASK_REAPING, TASK_EXAMINING, TASK_MINING, TASK_ASSIGNED, TASK_EATING,
                       TASK_REFUELING, TASK_TOWING_DROID, CHARGE_DURATION, TASK_LENGTH, ASSIGNABLE_ITEMS, LOW_CHARGE_FLAG, IDLE_CHARGE_USAGE,
                       POWER_PER_RED, POWER_PER_INDIGO, POWER_PER_GOLD, NUM_DROIDS, FULL_CHARGE, TOW_TASK_LENGTH)
from lore.lore_ingame import get_message
from lore.user_interface import (get_input, msg_plant, msg_explore, msg_power, msg_crystal,
                                 msg_resource, msg_mine, msg_info, msg_shield, msg_error, msg_food)
from planting import determine_what_to_plant_and_where
from queuing import add_to_queue, is_idle
from resources import choose_vials_and_display_power_produced
from status import display_character_summary, list_crystals
from utils import (get_best_match, get_pronouns, can_character_act, set_shield_state, clear_task_for_character, set_task_status_for_character,
                   get_integer_input, parse_command_targets)


def set_task_length(task_type):
    low, high = TASK_LENGTH[task_type]
    return random.randint(low, high)


def handle_immediate_or_queued_task(action, qualifier, task_package):
    valid_command = True
    turns_elapsed = task_package["counters"]["turns"]

    # ---- TASK DISPATCH ----
    if action == "feed" or action == TASK_EATING:
        valid_command, task_package = initiate_feed_task(qualifier, task_package)

    elif action == "charge" or action == TASK_CHARGING:
        valid_command, task_package = initiate_charge_task(qualifier, task_package)

    elif action == "explore" or action == TASK_EXPLORING:
        valid_command, task_package = initiate_explore_task(qualifier, task_package)

    elif action == "examine" or action == TASK_EXAMINING:
        valid_command, task_package = initiate_examine_task(qualifier, task_package)

    elif action == "plant" or action == TASK_PLANTING:
        valid_command, task_package = initiate_plant_task(qualifier, task_package)

    elif action == "reap" or action == TASK_REAPING:
        valid_command, task_package = initiate_reap_task(qualifier, task_package)

    elif action == "mine" or action == TASK_MINING:
        valid_command, task_package = initiate_mine_task(qualifier, task_package)

    elif action == "assign" or action == TASK_ASSIGNED:
        valid_command, task_package = handle_assign_command(qualifier, task_package)

    elif action == "refuel" or action == TASK_REFUELING:
        valid_command, task_package = initiate_refuel_task(qualifier, task_package)

    else:
        msg_error(get_message("error", "unknown_command", command=action), turns_elapsed)
        valid_command = False

    return valid_command, task_package


def initiate_feed_task(qualifier, task_package):
    # Feed those humans (or droids?)
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_EATING
    valid_command = False

    # Step 1: Get targets (either from qualifier or prompt)
    if not qualifier:
        display_character_summary(humans, droids, task_type, turns_elapsed)
        feed_targets = get_input("input", "feed", turns_elapsed)
    else:
        feed_targets = parse_command_targets(qualifier, task_type, task_package)
        
    if not feed_targets:
        return valid_command, task_package

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
                humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
                continue

            # Else if they *are* idle, create the task
            return_msg, task_package = create_task(name, task_type, duration, task_package)
            
            msg_food(return_msg, turns_elapsed)
            valid_command = True

        return valid_command, task_package

    if feed_targets == ["hungry"]:
        hungry_people = [name for name, h in humans.items() if h["hunger"] >= 5]
        if not hungry_people:
            msg_food("feed", "no_hungry_humans", turns_elapsed, tone="warn")
            return valid_command, task_package
        
        for name in hungry_people:        
            # If they are not idle, add this action to their queue
            if not is_idle(name, humans, droids):
                humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
                continue

            # Else if they *are* idle, create the task
            return_msg, task_package = create_task(name, task_type, duration, task_package)
            msg_food(return_msg, turns_elapsed)
            valid_command = True
            
        return valid_command, task_package

    # Step 4: Handle individual targets
    for raw_target in feed_targets:
        name = get_best_match(raw_target, list(humans.keys()) + list(droids.keys()))

        # If they are not idle, add this action to their queue
        if not is_idle(name, humans, droids) and name in humans:
            valid_command = True
            humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
            continue

        # Else if they *are* idle, create the task
        is_human = name in humans
        if is_human:
            return_msg, task_package = create_task(name, task_type, duration, task_package)
            valid_command = True
        elif name in droids:
            msg_food(get_message("feed_droid", "responses", droid_name=name), turns_elapsed, tone="error")
        else:
            msg_error(get_message("error", "feed_invalid", person_name=raw_target), turns_elapsed)

        msg_food(return_msg, turns_elapsed)

    return valid_command, task_package


def initiate_charge_task(qualifier, task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_CHARGING
    valid_command = False

    power_resource = next((r for r in resources if r.get("name") == "PowerSupply"), None)

    if not power_resource or not power_resource.get("found", False):
        msg_power(get_message("charge", "nowhere_to_charge"), turns_elapsed, tone="warn")
        return valid_command, task_package

    if power_resource["amount"] < 100:
        msg_power(get_message("charge", "not_enough_power"), turns_elapsed, tone="error")
        return valid_command, task_package

    charge_targets = parse_command_targets(qualifier, task_type, task_package)
    if charge_targets is None:
        return valid_command, task_package

    duration = CHARGE_DURATION
    threshold = LOW_CHARGE_FLAG * IDLE_CHARGE_USAGE

    for name in charge_targets:
        if name in droids:
            droid = droids[name]
            charge_level = droid["charge"]
            first_charge = droid.get("first_charge", False)

            # Skip if already queued
            if not is_idle(name, humans, droids):
                valid_command = True
                humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
                continue

            if "low" in qualifier and charge_level > threshold:
                msg_power(get_message("charge", "charge_above_low", target=name), turns_elapsed)
                continue

            if charge_level >= 800:
                msg_power(get_message("charge", "charge_full", droid_name=name), turns_elapsed)
                continue

            # Handle zero-charge towing case
            if charge_level == 0 and not first_charge:
                idle_humans = [h for h in humans if is_idle(h, humans, droids)]

                if not idle_humans:
                    msg_power(get_message("charge", "droid_needs_towing", droid=name), turns_elapsed, tone="warn")
                    continue

                # Prompt player to choose human to tow
                chosen = get_input("input", "tow_droid", turns_elapsed, name=name, humans_to_tow=idle_humans)
                task_type = TASK_TOWING_DROID
                duration = TOW_TASK_LENGTH

                # First check if the character can do the task
                okay_to_act, is_human, human_to_tow = can_character_act(chosen, task_type, humans, droids, turns_elapsed)
                if not okay_to_act:
                    return valid_command, task_package

                if human_to_tow:
                    valid_command = True
                    task_package["item"] = name
                    return_msg, task_package = create_task(human_to_tow, task_type, duration, task_package)
                continue

            # Normal charge
            valid_command = True
            return_msg, task_package = create_task(name, task_type, duration, task_package)
            msg_power(return_msg, turns_elapsed)

        elif name in humans:
            pronouns = get_pronouns(name, is_human=True)
            msg_power(get_message("charge", "wrong_target", target=name, pronoun=pronouns["p1"].lower()), turns_elapsed, tone="error")

        else:
            msg_power(get_message("charge", "no_target"), turns_elapsed, tone="error")

    return valid_command, task_package


def initiate_explore_task(qualifier, task_package):
    # Send some character exploring on a mission to find *something*
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_EXPLORING
    valid_command = False

    explore_targets = parse_command_targets(qualifier, task_type, task_package)
    if explore_targets == None:
        return valid_command, task_package

    for raw_target in explore_targets:
        okay_to_act, is_human, name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed)
        if not okay_to_act:
            continue  # Skip to the next target

        # If they are not idle, add this action to their queue
        success = False
        if not is_idle(name, humans, droids):
            valid_command = True
            humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
            continue

        if is_human:
            duration = set_task_length("explore_human")
        else:
            duration = set_task_length("explore_droid")

        # Create the task
        return_msg, task_package = create_task(name, task_type, duration, task_package)
        msg_explore(return_msg, turns_elapsed)

    return valid_command, task_package


def initiate_plant_task(qualifier, task_package):
    # Plant some real goddamn food
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    crops = task_package["crops"]
    task_data = task_package["task_data"]
    task_type = TASK_PLANTING
    queued_task = False
    valid_command = False

    if not task_data:   # This takes care of the 'initial task' versus a queued task
        good_order, name, crop_instructions, resources = determine_what_to_plant_and_where(
                qualifier, crops, resources, humans, droids, turns_elapsed)

        if not good_order:
            return valid_command, task_package
        else:
            task_data = crop_instructions
    else:
        crop_instructions = task_data
        name = qualifier
        queued_task = True
        valid_command = True

    # Update task_package
    task_package["task_data"] = task_data

    # Create plant task
    is_human = name in humans
    duration = set_task_length("plant_human")
    if not is_human: 
        duration = set_task_length("plant_droid")
    
    # If they are not idle, and this was not a queued task, add this action to their queue
    if not is_idle(name, humans, droids) and not queued_task:
        valid_command = True
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, task_data=crop_instructions)
        return valid_command, task_package

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    msg_plant(return_msg, turns_elapsed)

    return valid_command, task_package


def initiate_examine_task(raw_examiner, task_package):
    # Examine something - or just glance at it
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    item_name = task_package["item"]
    task_type = TASK_EXAMINING
    valid_command = False

    # Get targets (either from qualifier or prompt)
    if not raw_examiner:
        display_character_summary(humans, droids, task_type, turns_elapsed)
        raw_examiner = get_input("input", "examine", turns_elapsed)
    
    name = parse_command_targets(raw_examiner, task_type, task_package)
    if not name:
        return valid_command, task_package

    # First check if the character can do the examine
    okay_to_act, is_human, name = can_character_act(raw_examiner, task_type, humans, droids, turns_elapsed)
    if not okay_to_act:
        return valid_command, task_package
    
    if item_name == "":
        # Find discovered items that are examinable and haven't been examined yet
        examinable_items = [item["name"] for item in resources if (item["examinable"] and not item["examined"])]
    
        if not examinable_items:
            msg_resource(get_message("examine", "nothing_examinable"), turns_elapsed)
            return valid_command, task_package

        # If not accepted to assign, just return
        item_name, current_examinee, accepted = get_examinable_item(humans, droids, examinable_items, name, turns_elapsed)
        if not accepted:
            return valid_command, task_package

    # Find the target item
    item = next((r for r in resources if r["name"] == item_name), None)
    if not item:
        msg_resource(get_message("examine", "not_found", item=item_name), turns_elapsed)
        return valid_command, task_package
    
    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        valid_command = True
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item=item_name)
        return valid_command, task_package

    # Immediate?
    if item.get("examine_turns", 0) <= 0:
        new_msg = item["msg"].format(name=name, R=item.get("red", ""), I=item.get("indigo", ""), G=item.get("gold", ""),
                A=item.get("apple",""), C=item.get("cabbage",""), P=item.get("potato",""),  amount=item.get("amount", ""))
        formatted_msg = f"{item_name}: " + new_msg
        msg_resource(formatted_msg, turns_elapsed)
        item["examined"] = True
        item["msg"] = new_msg
        valid_command = True
        return valid_command, task_package

    valid_command = True

    # Unassign previous examiner, if any
    if current_examinee:
        humans, droids = clear_task_for_character(current_examinee, item_name, humans, droids)
        msg_resource(get_message("examine", "reassigned", item=item_name, previous=current_examinee, new=name), turns_elapsed)

    # Set the examine time, which is *quicker* for droids
    if is_human:
        duration = item.get("examine_turns", 0) + set_task_length("examine_human")
    else:
        duration = item.get("examine_turns", 0) + set_task_length("examine_droid")

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    msg_resource(return_msg, turns_elapsed)
    
    return valid_command, task_package


def initiate_reap_task(raw_target, task_package):
    # Reap those crops! Food is needed.
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    crops = task_package["crops"]
    task_type = TASK_REAPING
    valid_command = False

    # Get targets (either from qualifier or prompt)
    if not raw_target:
        display_character_summary(humans, droids, task_type, turns_elapsed)
        raw_target = get_input("input", "reap", turns_elapsed)

    reap_target = parse_command_targets(raw_target, task_type, task_package)
    if not reap_target:
        return valid_command, task_package

    okay_to_act, is_human, name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed)
    if not okay_to_act:
        return valid_command, task_package
        
    # Warn if nothing is ready
    mature_exists = any(crop.get("mature", False) for crop in crops.values())
    if not mature_exists:
        msg_plant(get_message("reap", "no_mature_crops", target=name), turns_elapsed)
        # Allow them to continue anyway (they may have a plan for this)

    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
        return valid_command, task_package

    valid_command = True

    # Now create the reap task
    duration = set_task_length("reap_human")
    if not is_human:
        duration = set_task_length("reap_droid")
        
    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    msg_plant(return_msg, turns_elapsed)
    
    return valid_command, task_package


def initiate_mine_task(qualifier, task_package):
    # Assign one or more characters to mine in the CrystalField
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_MINING
    valid_command = False

    mine_targets = parse_command_targets(qualifier, task_type, task_package)
    if mine_targets == None:
        return valid_command, task_package

    for raw_target in mine_targets:
        okay_to_act, is_human, name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed)
        if not okay_to_act:
            continue  # Skip invalid or busy characters

        # Initialise PowerSupply CrystalStore if not already done
        for r in resources:
            if r.get("name") == "PowerSupply":
                if "CrystalStore" not in r or not r["CrystalStore"]:
                    r["CrystalStore"] = {"red": 0, "indigo": 0, "gold": 0, 
                                         "total_found": {"red": 0, "indigo": 0, "gold": 0}, 
                                         "processed": {"red": 0, "indigo": 0, "gold": 0}}
                break

        # If they are not idle, add this action to their queue
        if not is_idle(name, humans, droids):
            valid_command = True
            humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
            return valid_command, task_package

        valid_command = True

        # Assign mining task
        duration = set_task_length("mine_human") if is_human else set_task_length("mine_droid")

        # Create the task
        return_msg, task_package = create_task(name, task_type, duration, task_package)
        msg_mine(return_msg, turns_elapsed)

    return valid_command, task_package


def initiate_refuel_task(raw_target, task_package):
    # Refuel the all-important power supply
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_REFUELING
    red = 0
    indigo = 0
    gold = 0
    valid_command = False

    # Get targets (either from qualifier or prompt)
    if not raw_target:
        display_character_summary(humans, droids, task_type, turns_elapsed)
        raw_target = get_input("input", "refuel", turns_elapsed)

    refuel_target = parse_command_targets(raw_target, task_type, task_package)
    if not refuel_target:
        return valid_command, task_package

    okay_to_act, is_human, name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed)
    if not okay_to_act:
        return valid_command, task_package

    # Find PowerSupply
    power_supply = next((r for r in resources if r.get("name") == "PowerSupply"), None)
    if not power_supply or not power_supply.get("found", False):
        msg_power(get_message("refuel", "no_power_supply"),
                        turns_elapsed, tone="warn")
        return valid_command, task_package

    # Warn if no vials (but allow assignment)
    vial_store = power_supply.get("VialStore", {})
    if not vial_store or all(v == 0 for v in vial_store.values()):
        msg_crystal(get_message("refuel", "no_vials", name=name), turns_elapsed, tone="warn")
        return valid_command, task_package
    
    else:   # Give them an estimate of the power they will produce with their selection
        return_msg, task_package, red, indigo, gold = choose_vials_and_display_power_produced(name, task_package)
        if return_msg != "":    # In other words, there was an error getting the power total
            msg_power(return_msg, turns_elapsed, tone="warn")
            return valid_command, task_package
        
        # They chose not to do any refuelling after seeing crystal totals
        if red == 0 and indigo == 0 and gold == 0:
            msg_power(return_msg, turns_elapsed)
            return valid_command, task_package
        
    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        valid_command = True
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
        return valid_command, task_package

    valid_command = True

    # Create task
    task_type = TASK_REFUELING
    key = "refuel_human" if is_human else "refuel_droid"
    duration = set_task_length(key)

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    msg_power(return_msg, turns_elapsed)

    return valid_command, task_package


def handle_assign_command(raw_target, task_package):
    # Assign a character to something useful (hopefully)
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    item_name = task_package["item"]
    task_type = TASK_ASSIGNED
    valid_command = False
    
    if item_name == "":
        # Find discovered assignable items
        discovered_items = [item["name"] for item in resources if item["name"] in ASSIGNABLE_ITEMS]
    
        if not discovered_items:
            msg_info(get_message("assign", "nothing_assignable"), turns_elapsed)
            return valid_command, task_package

    # Get targets (either from qualifier or prompt)
    if not raw_target:
        display_character_summary(humans, droids, task_type, turns_elapsed)
        raw_target = get_input("input", "assignee", turns_elapsed, full_list=discovered_items)

    assign_target = parse_command_targets(raw_target, task_type, task_package)
    if not assign_target:
        return valid_command, task_package
    
    okay_to_act, is_human, name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed)
    if not okay_to_act:
        return valid_command, task_package

    if item_name == "":
        # If not accepted to assign, just return
        item_name, current_assignee, accepted, humans, droids = get_new_assignee(humans, droids, discovered_items, name, turns_elapsed)
        if not accepted:
            return valid_command, task_package

    # ---- Begin assignment ----
    task_created = False

    if item_name == "CrystalProcessor":
        valid_command, task_package = initiate_assign_process_task(name, task_package)
    elif item_name == "ShieldManual":
        valid_command, task_package = initiate_assign_shieldmanual_task(name, task_package)
    elif item_name == "OldTerminal":
        # Instant assignment: no task, no turn consumed
        task_created = True
        msg_shield(get_message("assign", "old_terminal_assigned", name=name), turns_elapsed)
        valid_command, task_package = enter_oldterminal_commands(name, task_package)
    elif item_name == "CloakingShield":
        task_created = True
        valid_command, task_package = check_shield_assign(name, task_package)

    if task_created:
        # Unassign previous assignee, if any
        if current_assignee and current_assignee != name:   # i.e. not a reassign
            humans, droids = clear_task_for_character(current_assignee, item_name, humans, droids)
            msg_info(get_message("assign", "reassigned", item=item_name, old=current_assignee, new=name), turns_elapsed)

    return valid_command, task_package


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

    choice = msg_info("input", "assigned_item", turns_elapsed, name=target, full_list=menu)
    
    if not choice.isdigit():
        msg_error(get_message("assign", "invalid_choice"), turns_elapsed)
        accepted = False
        return "", "", accepted

    choice = int(choice)
    if choice == 0:
        msg_info(get_message("assign", "assignment_aborted"), turns_elapsed)
        accepted = False
    elif 1 <= choice <= len(discovered_items):
        item_name = discovered_items[choice - 1]
        current_assignee = assignees[item_name]
        accepted = True
        set_task_status_for_character(target, TASK_ASSIGNED, item_name, humans, droids, turns_elapsed)
    else:
        msg_error(get_message("assign", "invalid_choice"), turns_elapsed)
        accepted = False

    return item_name, current_assignee, accepted, humans, droids


def initiate_assign_process_task(name, task_package):
    # Assign a human or droid to process selected crystals using the CrystalProcessor.
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_ASSIGNED
    item_name = "CrystalProcessor"
    valid_command = False

    # Find the PowerSupply and ensure it has CrystalStore
    power_supply = next((r for r in resources if r.get("name") == "PowerSupply"), None)
    if not power_supply or "CrystalStore" not in power_supply:
        msg_crystal(get_message("assign", "process_no_crystals", name=name, item=item_name), turns_elapsed, tone="error")
        return valid_command, task_package

    crystal_store = power_supply["CrystalStore"]
    if all(crystal_store[color] == 0 for color in ["red", "indigo", "gold"]):
        msg_crystal(get_message("assign", "process_no_crystals", name=name, item=item_name), turns_elapsed, tone="error")
        return valid_command, task_package

    # Find the CrystalProcessor
    processor = next((r for r in resources if r.get("name") == item_name and r.get("found", False)), None)
    if not processor:
        msg_crystal(get_message("assign", "no_processor", item=item_name), turns_elapsed, tone="error")
        return valid_command, task_package

    # Ensure VialStore exists
    if "VialStore" not in power_supply:
        power_supply["VialStore"] = {"red": 0, "indigo": 0, "gold": 0}

    # Prompt for quantity of each crystal type
    red_avail = crystal_store["red"]
    indigo_avail = crystal_store["indigo"]
    gold_avail = crystal_store["gold"]

    # List the crystals and vials in storage
    list_crystals(task_package)

    # Now get the amounts
    red = get_integer_input(f"How many RED crystals to process? (0–{red_avail}): ", 0, red_avail)
    indigo = get_integer_input(f"How many INDIGO crystals to process? (0–{indigo_avail}): ", 0, indigo_avail)
    gold = get_integer_input(f"How many GOLD crystals to process? (0–{gold_avail}): ", 0, gold_avail)

    if red == 0 and indigo == 0 and gold == 0:
        msg_crystal("No crystals selected for processing. Task cancelled.", turns_elapsed)
        return valid_command, task_package

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
    msg_crystal(get_message("assign", "CP_estimate", target=name, total_power=total_power, num=num_droids, day=num_days), turns_elapsed)

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
        valid_command = True
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item=item_name, task_data=task_data)
        return valid_command, task_package

    valid_command = True

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    msg_crystal(return_msg, turns_elapsed)

    return valid_command, task_package


def initiate_assign_shieldmanual_task(name, task_package):
    # Assign a human or droid to the Shield Manual
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_ASSIGNED
    item_name = "ShieldManual"
    valid_command = False

    # ---- Find ShieldManual ----
    manual = next((r for r in resources if r.get("name") == item_name), None)
    if not manual or not manual.get("found", False):
        msg_shield(get_message("assign", "no_manual", item=item_name), turns_elapsed)
        return valid_command, task_package
    
    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        valid_command = True
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item=item_name)
        return valid_command, task_package

    valid_command = True

    # ---- Create task ----
    is_human = name in humans

    if is_human:
        duration = set_task_length("assign_human_manual")
    else:
        duration = set_task_length("assign_droid_manual")

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package)
    msg_shield(return_msg, turns_elapsed)
    
    return valid_command, task_package


def check_shield_assign(name, task_package):
    # Check who is assigned to the Shield
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    is_droid = name in droids
    task_type = TASK_ASSIGNED
    valid_command = False

    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        valid_command = True
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
        return valid_command, task_package

    if is_droid or not shieldstate["manual_decoded"]: # Can allow anyone to be assigned to the shield IF the manual is NOT decoded, but only droids if it is
        msg_shield(get_message("shield", "assigned_to", target=name), turns_elapsed)

        # Check that it was the droid with the Anicent Code that we assigned
        ancient_code = next((r for r in resources if r["name"] == "AncientDroidCode"), None)
        if ancient_code:
            if ancient_code["droidName"] == name:
                valid_command = True
                shieldstate = set_shield_state("C", droids, resources, shieldstate)
                droids[name]["charge"] = FULL_CHARGE  # When they are connected they have full charge
        else:
            msg_shield(get_message("shield", "code_not_found", name=name), turns_elapsed, tone="warn")

    else:
        msg_shield(get_message("shield", "cannot_assign_human", target=name), turns_elapsed, tone="warn")
      
    return valid_command, task_package


def enter_oldterminal_commands(name, task_package):
    # Process commands to get the shield combination into the Shield
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_ASSIGNED
    valid_command = False

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
    item_name = "OldTerminal"
    if not is_idle(name, humans, droids):
        valid_command = True
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item=item_name)
        return valid_command, task_package

    if not shieldstate.get("manual_decoded", False):
        is_human = name in humans
        pronouns = get_pronouns(name, is_human)
        msg_shield(get_message("shield", "terminal_unreadable", name=name, pronoun=pronouns["p1"].lower()), turns_elapsed)
        valid_command = True    # We dock a turn anyway - this is a learning process
        return valid_command, task_package

    crystal_combo = next((r for r in resources if r["name"] == "CrystalCombination"), None)

    if not crystal_combo:
        msg_shield(get_message("shield", "need_combo", name=name), turns_elapsed, tone="warn")
        return task_package

    if not crystal_combo.get("examined", False):
        msg_shield(get_message("shield", "combo_not_examined", name=name), turns_elapsed, tone="warn")
        valid_command = True   # Dock a turn here also
        return valid_command, task_package

    # Offer to use the combination
    response = get_input("input", "oldterminal", turns_elapsed)

    # Count available crystals and abort if there aren't enough
    available_crystals = do_we_have_enough(resources)
    if crystal_combo["red"] > available_crystals.get("red",0) or crystal_combo["indigo"] > available_crystals.get("indigo",0) or crystal_combo["gold"] > available_crystals.get("gold",0):
        msg_crystal(get_message("shield", "not_enough_crystals_with_combo", 
                                    need_R=crystal_combo["red"], need_I=crystal_combo["indigo"], need_G=crystal_combo["gold"], 
                                    have_R=available_crystals.get("red",0), have_I=available_crystals.get("indigo",0), have_G=available_crystals.get("gold",0)),
                                    turns_elapsed, tone="warn")
        valid_command = True    # And here also
        return valid_command, task_package
    
    # All good, so send the message to the player
    elif response in ["yes", "y"]:
        msg_shield(get_message("shield", "combo_correct", name=name), turns_elapsed, tone="success")
        shieldstate = set_shield_state("D", droids, resources, shieldstate)

        # Remove the crystals from the crystal store
        power_supply = next((r for r in resources if r["name"] == "PowerSupply"), None)
        crystal_store = power_supply["CrystalStore"]
        crystal_store["red"] -= crystal_combo["red"]
        crystal_store["indigo"] -= crystal_combo["indigo"]
        crystal_store["gold"] -= crystal_combo["gold"]
        valid_command = True
    else:
        msg_shield(get_message("shield", "combo_correct_aborted", name=name), turns_elapsed, tone="warn")
        return valid_command, task_package

    valid_command = True
    is_droid = name in droids
    if is_droid:    # Any droid can be assigned to the OldTerminal
        shieldstate = set_shield_state("E", droids, resources, shieldstate)
    else:
        msg_shield(get_message("shield", "terminal_cannot_assign_human", target=name), turns_elapsed, tone="warn")

    return valid_command, task_package


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

    choice = get_input("input", "examine_what", turns_elapsed, target=target, items=menu)

    if not choice.isdigit():
        msg_error(get_message("examine", "invalid_choice"), turns_elapsed)
        accepted = False
        return "", "", accepted

    choice = int(choice)
    if choice == 0:
        msg_resource(get_message("examine", "aborted"), turns_elapsed)
        accepted = False
    elif 1 <= choice <= len(examinable_items):
        item_name = examinable_items[choice - 1]
        current_examiner = examinees[item_name]
    else:
        msg_resource(get_message("examine", "invalid_choice"), turns_elapsed)
        accepted = False

    return item_name, current_examiner, accepted