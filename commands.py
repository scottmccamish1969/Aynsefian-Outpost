# commands.py

import random

from command_utils import (create_task, is_droid_being_charged_or_towed, get_refuel_power_supply_and_vials, 
                           remove_vials_from_store, calculate_refuel_power, get_refuel_days, get_pronouns, 
                           clear_task_for_character, set_task_status_for_character)
from constants import (TASK_CHARGING, TASK_EXPLORING, TASK_PLANTING, TASK_REAPING, TASK_EXAMINING, TASK_MINING, TASK_ASSIGNED,
                       TASK_EATING, TASK_REFUELING, TASK_TOWING_DROID, CHARGE_DURATION, TASK_LENGTH, ASSIGNABLE_ITEMS,
                       LOW_CHARGE_FLAG, IDLE_CHARGE_USAGE, POWER_PER_RED, POWER_PER_INDIGO, POWER_PER_GOLD, NUM_DROIDS,
                       FULL_DROID_CHARGE, TOW_TASK_LENGTH, COMMAND_MAP, TaskStartOutcome, NORMAL_MEAL_MULTIPLIER, 
                       EMERGENCY_MEAL_MULTIPLIER, ONE_DAY_HUNGRY)
from lore.lore_ingame import get_message
import lore.user_interface as ui_runtime
from lore.user_interface import (get_input, msg_plant, msg_explore, msg_power, msg_crystal, msg_resource, msg_mine, msg_info,
                                 msg_shield, msg_error, msg_warn, msg_food, get_confirm, get_integer_input)
from planting import determine_what_to_plant_and_where, finish_initiate_plant_task, select_and_reserve_meal
from queuing import add_to_queue, is_idle
from resources import get_power_required_for_full_charge, try_start_charge_task
from status import display_character_summary, list_crystals
from utils import get_best_match, can_character_act, set_shield_state, reset_config, save_config, parse_integer_answer


def set_task_length(task_type):
    low, high = TASK_LENGTH[task_type]
    return random.randint(low, high)


def parse_command_targets(qualifier, task_type, task_package):
    # Given a raw qualifier (name(s), group keyword, etc), task_type, and task_package,
    # return:
    #   - list of valid character names
    #   - None for invalid/no valid names
    #   - ui_runtime.GUI_PENDING if a GUI prompt has been issued and we are waiting

    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    # Set logic controls per task
    supports_all = task_type in (TASK_CHARGING, TASK_EATING, TASK_EXPLORING)
    supports_idle = task_type in (TASK_EXPLORING, TASK_MINING, TASK_PLANTING, TASK_EATING, TASK_CHARGING)
    supports_hungry = task_type == TASK_EATING
    supports_low = task_type == TASK_CHARGING

    # Prompt if no qualifier
    if not qualifier:
        display_character_summary(humans, droids, task_type, turns_elapsed)
        command_keyword = COMMAND_MAP.get(task_type, "action")

        if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
            ui_runtime.ACTIVE_UI.set_pending_question(
                callback=resume_action_command,
                context={
                    "task_package": task_package,
                    "task_type": task_type,
                }
            )

        qualifier = get_input("input", command_keyword, turns_elapsed)

        if qualifier == ui_runtime.GUI_PENDING:
            return ui_runtime.GUI_PENDING

    # Normalize
    if isinstance(qualifier, str):
        qualifier = qualifier.lower().strip()
        raw_names = [q.strip() for q in qualifier.replace(",", " ").split()]
    else:
        raw_names = qualifier

    targets = []
    found_valid_name = False

    if qualifier == "all" and supports_all:
        if task_type == TASK_CHARGING:
            targets = list(droids.keys())
        elif task_type == TASK_EATING:
            targets = list(humans.keys())
        else:
            available_droids = [
                d for d in droids
                if droids[d]["charge"] > 0 or droids[d]["task"] == TASK_CHARGING
            ]
            targets = list(humans.keys()) + available_droids
        found_valid_name = True

    elif qualifier == "idle" and supports_idle:
        idle_humans = [h for h in humans if humans[h]["task"] == ""]
        idle_droids = [d for d in droids if droids[d]["task"] == "" and droids[d]["charge"] > 0]
        targets = idle_humans + idle_droids
        found_valid_name = True

    elif qualifier == "hungry" and supports_hungry:
        targets = [h for h in humans if humans[h]["state"] in ("Hungry", "Starving", "NearDeath")]
        found_valid_name = True

    elif qualifier == "low" and supports_low:
        targets = [d for d in droids if droids[d]["charge"] <= LOW_CHARGE_FLAG * IDLE_CHARGE_USAGE]
        found_valid_name = True

    else:
        # Parse explicit names
        for name in raw_names:
            match = get_best_match(name, list(humans.keys()) + list(droids.keys()))
            if match:
                targets.append(match)
                found_valid_name = True

    if not found_valid_name:
        msg_error(get_message("error", "unknown_worker", name=qualifier), turns_elapsed)
        return None

    return targets


def resume_action_command(answer, context):
    task_package = context["task_package"]
    task_type = context["task_type"]

    valid_command = False
    outcome = TaskStartOutcome.INVALID

    if task_type == TASK_EXPLORING:
        valid_command, task_package = initiate_explore_task(answer, task_package)

    elif task_type == TASK_EATING:
        valid_command, task_package = initiate_feed_task(answer, task_package)

    elif task_type == TASK_CHARGING:
        valid_command, task_package = initiate_charge_task(answer, task_package)

    elif task_type == TASK_EXAMINING:
        valid_command, task_package = initiate_examine_task(answer, task_package)

    elif task_type == TASK_PLANTING:
        valid_command, task_package = initiate_plant_task(answer, task_package)

    elif task_type == TASK_REAPING:
        valid_command, task_package = initiate_reap_task(answer, task_package)

    elif task_type == TASK_MINING:
        valid_command, task_package = initiate_mine_task(answer, task_package)

    elif task_type == TASK_REFUELING:
        valid_command, task_package = initiate_refuel_task(answer, task_package)

    elif task_type == TASK_ASSIGNED:
        outcome, task_package = handle_assign_command(answer, task_package)
        if outcome == TaskStartOutcome.INVALID:
            valid_command = False
        elif outcome == TaskStartOutcome.STARTED:
            valid_command = True
        elif outcome == TaskStartOutcome.AWAITING_INPUT:
            return None     # We are awaiting input, so do not resume turn processing yet

    else:
        # Fallback for any task type that hasn't been wired yet
        turns_elapsed = task_package["counters"]["turns"]
        msg_error(get_message("error", "no_resume_handler", task_type=task_type), turns_elapsed)
        return None

    # If the resumed command was successful, return task_package
    # so on_submit() can call resume_turn_processing(task_package).
    if valid_command:
        return task_package

    # Invalid choice, no valid target, etc:
    # do not consume the turn, do not resume processing.
    return None


def initiate_feed_task(qualifier, task_package):
    # Feed those humans (or droids?)
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_EATING
    valid_command = False
    task_data = {}
    multiplier = NORMAL_MEAL_MULTIPLIER
    hunger_reduction = 0

    feed_targets = parse_command_targets(qualifier, task_type, task_package)

    if feed_targets == ui_runtime.GUI_PENDING:
        return valid_command, task_package

    if feed_targets is None:
        return valid_command, task_package

    # Step 2: Normalise targets into a LIST
    # (so we never accidentally iterate over characters)
    if isinstance(feed_targets, str):
        feed_targets = feed_targets.split()

    task_length_key = ("feed_human_emergency" if multiplier == EMERGENCY_MEAL_MULTIPLIER else "feed_human")
    low, high = TASK_LENGTH[task_length_key]
    duration = random.randint(low, high)

    # Step 3: Handle special keywords
    if feed_targets == ["all"]:
        for name in humans:
            # Skip a deceased human 🪦
            if humans[name]["state"] == "Deceased":
                continue

            # Reserve the food
            if humans[name]["state"] in ("Starving", "NearDeath"):
                multiplier = EMERGENCY_MEAL_MULTIPLIER
            else:
                multiplier = NORMAL_MEAL_MULTIPLIER
            hunger_reduction = multiplier * ONE_DAY_HUNGRY
            task_data, task_package = select_and_reserve_meal(name, multiplier, hunger_reduction, task_package)
            if not task_data:
                continue

            # If they are not idle, add this action to their queue
            if not is_idle(name, humans, droids):
                humans[name]["awaiting_food"] = False
                humans[name]["food_wait_declined"] = False
                humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, task_data=task_data)
                continue

            # Clear the flags - food is now reserved for them
            humans[name]["awaiting_food"] = False
            humans[name]["food_wait_declined"] = False

            # Create the task
            return_msg, task_package = create_task(name, task_type, duration, task_package, task_data=task_data)
            
            msg_food(return_msg, turns_elapsed)
            valid_command = True

        return valid_command, task_package

    if feed_targets == ["hungry"]:
        hungry_people = [name for name, h in humans.items() if h["hunger"] >= 5]
        if not hungry_people:
            msg_food("feed", "no_hungry_humans", turns_elapsed, tone="warn")
            return valid_command, task_package
        
        for name in hungry_people:
            # Reserve the food
            if humans[name]["state"] in ("Starving", "NearDeath"):
                multiplier = EMERGENCY_MEAL_MULTIPLIER
            else:
                multiplier = NORMAL_MEAL_MULTIPLIER
            hunger_reduction = multiplier * ONE_DAY_HUNGRY
            task_data, task_package = select_and_reserve_meal(name, multiplier, hunger_reduction, task_package)
            if not task_data:
                continue

            # If they are not idle, add this action to their queue
            if not is_idle(name, humans, droids):
                humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, task_data=task_data)
                continue

            # Else if they *are* idle, create the task
            return_msg, task_package = create_task(name, task_type, duration, task_package, task_data=task_data)
            msg_food(return_msg, turns_elapsed)
            valid_command = True
            
        return valid_command, task_package

    # Step 4: Handle individual targets
    for raw_target in feed_targets:
        name = get_best_match(raw_target, list(humans.keys()) + list(droids.keys()))

        # Reserve the food
        if humans[name]["state"] in ("Starving", "NearDeath"):
            multiplier = EMERGENCY_MEAL_MULTIPLIER
        else:
            multiplier = NORMAL_MEAL_MULTIPLIER
        hunger_reduction = multiplier * ONE_DAY_HUNGRY
        task_data, task_package = select_and_reserve_meal(name, multiplier, hunger_reduction, task_package)
        if not task_data:
            continue

        # If they are not idle, add this action to their queue
        if not is_idle(name, humans, droids) and name in humans:
            valid_command = True
            humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, task_data=task_data)
            continue

        # Else if they *are* idle, create the task
        is_human = name in humans
        if is_human:
            return_msg, task_package = create_task(name, task_type, duration, task_package, task_data=task_data)
            msg_food(return_msg, turns_elapsed)
            valid_command = True
        elif name in droids:
            msg_food(get_message("feed_droid", "responses", droid_name=name), turns_elapsed, tone="error")
        else:
            msg_error(get_message("error", "feed_invalid", person_name=raw_target), turns_elapsed)

    return valid_command, task_package


def initiate_charge_task(qualifier, task_package):
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_CHARGING

    power_resource = next((r for r in resources if r.get("name") == "PowerSupply"),None)

    if not power_resource or not power_resource.get("found", False):
        msg_power(get_message("charge", "nowhere_to_charge"), turns_elapsed, tone="warn")
        return False, task_package

    if power_resource["amount"] < 100:
        msg_power(get_message("charge", "not_enough_power"), turns_elapsed, tone="error")
        return False, task_package

    charge_targets = parse_command_targets(qualifier, task_type, task_package)

    if charge_targets == ui_runtime.GUI_PENDING:
        return False, task_package

    if charge_targets is None:
        return False, task_package

    outcome, task_package = process_charge_targets(charge_targets, qualifier, task_package)

    # Preserve the existing public contract for charging.
    return outcome == TaskStartOutcome.STARTED, task_package


def process_charge_targets(charge_targets, qualifier, task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    threshold = LOW_CHARGE_FLAG * IDLE_CHARGE_USAGE
    started_anything = False

    qualifier_text = str(qualifier).strip()
    broad_qualifiers = ("low", "idle", "all")

    explicit_target = qualifier_text.casefold() not in broad_qualifiers

    for index, name in enumerate(charge_targets):
        
        droid = droids.get(name)
        if explicit_target:
            droid["tow_declined"] = False

        if name in humans:
            pronouns = get_pronouns(name, is_human=True)

            msg_power(get_message("charge", "wrong_target", target=name, pronoun=pronouns["p1"].lower()), turns_elapsed, tone="error")
            continue

        if name not in droids:
            msg_power(get_message("charge", "no_target", name=name), turns_elapsed, tone="error")
            continue

        droid = droids[name]
        charge_level = droid["charge"]

        # A stranded droid must be retrieved before a charge task can begin.
        # This check must occur before the normal "busy / queue it" check.     
        if droid.get("needs_tow", False):
            # The player previously declined an automatic rescue.
            # Only an explicit "charge <name>" command should clear this flag.
            if droid.get("tow_declined", False):
                continue

            if is_droid_being_charged_or_towed(name, task_package):
                started_anything = True
                continue

            idle_humans = [
                human_name
                for human_name in humans
                if is_idle(human_name, humans, droids)
            ]

            if not idle_humans:
                msg_power(get_message("charge", "droid_needs_towing", name=name), turns_elapsed, tone="warn")
                continue

            remaining_charge_targets = charge_targets[index + 1:]

            return offer_tow_for_stranded_droid(name, idle_humans, remaining_charge_targets, qualifier, task_package)

        # Set the task_data
        power_required = get_power_required_for_full_charge(droid)
        task_data = {
            "reserved_power": power_required,
            "starting_charge": droid["charge"],
            "target_charge": FULL_DROID_CHARGE
        }

        # Ordinary busy droids can receive a charge order in their queue.
        if not is_idle(name, humans, droids):
            humans, droids = add_to_queue(name, humans, droids, turns_elapsed, TASK_CHARGING, task_data=task_data)

            task_package["humans"] = humans
            task_package["droids"] = droids
            started_anything = True
            continue

        if (isinstance(qualifier, str)
            and "low" in qualifier
            and charge_level > threshold):
            msg_power(get_message("charge", "charge_above_low", target=name), turns_elapsed)
            continue

        # Don't charge if they are above 80% of full charge
        if charge_level >= 0.8*FULL_DROID_CHARGE:
            msg_power(get_message("charge", "charge_full", droid_name=name), turns_elapsed)
            continue

        return_msg, task_package = create_task(name, TASK_CHARGING, CHARGE_DURATION, task_package, task_data=task_data)

        outcome, return_msg, task_package = try_start_charge_task(name, task_package)

        if return_msg:
            tone = ("warn" if outcome != TaskStartOutcome.STARTED else None)
            msg_power(return_msg, turns_elapsed, tone=tone)

        if outcome == TaskStartOutcome.STARTED:
            started_anything = True

    if started_anything:
        return TaskStartOutcome.STARTED, task_package

    return TaskStartOutcome.INVALID, task_package


def offer_tow_for_stranded_droid(droid_name, idle_humans, remaining_charge_targets, qualifier, task_package):
    turns_elapsed = task_package["counters"]["turns"]

    context = {
        "task_package": task_package,
        "droid_needing_tow": droid_name,
        "remaining_charge_targets": remaining_charge_targets,
        "qualifier": qualifier,
    }

    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=resume_tow_command,
            context=context,
            humans_to_tow=idle_humans
        )

    answer = get_input("input", "tow_droid", turns_elapsed, name=droid_name, humans_to_tow=idle_humans)

    if answer == ui_runtime.GUI_PENDING:
        return TaskStartOutcome.AWAITING_INPUT, task_package

    # CLI / immediate path.
    return continue_tow_command(answer, context)


def resume_tow_command(answer, context):
    outcome, task_package = continue_tow_command(answer, context)

    # Another GUI question has opened. Do not resume turn processing yet.
    if outcome == TaskStartOutcome.AWAITING_INPUT:
        return None

    # Invalid human selection or cancelled action: do not dock a turn.
    if outcome == TaskStartOutcome.INVALID:
        return None

    return task_package


def continue_tow_command(answer, context):
    task_package = context["task_package"]
    droid_needing_tow = context["droid_needing_tow"]
    human_to_tow = answer
    remaining_charge_targets = context["remaining_charge_targets"]
    qualifier = context["qualifier"]
    turns_elapsed = task_package["counters"]["turns"]

    # Continue with the towing process
    okay_to_act, task_package = can_character_act(human_to_tow, TASK_TOWING_DROID, task_package)
    if not okay_to_act:
        return TaskStartOutcome.INVALID, task_package

    # Safety check: do not begin a duplicate tow task.
    if is_droid_being_charged_or_towed(droid_needing_tow, task_package):
        return TaskStartOutcome.INVALID, task_package

    # The towing task belongs to the human.
    # The droid being recovered is stored with the task so completion can
    # clear needs_tow and immediately begin charging.
    task_data = {
        "droid_to_tow": droid_needing_tow,
        "charge_after_tow": True,
    }

    return_msg, task_package = create_task(human_to_tow, TASK_TOWING_DROID, TOW_TASK_LENGTH, task_package, task_data=task_data)

    task_package["item"] = ""
    task_package["task_data"] = {}

    msg_power(return_msg, turns_elapsed)

    # Carry on with other targets in a broad command such as "charge low".
    # The towing task itself already counts as a successful action.
    if remaining_charge_targets:
        follow_up_outcome, task_package = process_charge_targets(remaining_charge_targets, qualifier, task_package)

        if follow_up_outcome == TaskStartOutcome.AWAITING_INPUT:
            return TaskStartOutcome.AWAITING_INPUT, task_package

    return TaskStartOutcome.STARTED, task_package


def initiate_explore_task(qualifier, task_package):
    # Send some character exploring on a mission to find *something*
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_EXPLORING
    valid_command = False
    is_human = qualifier in humans

    explore_targets = parse_command_targets(qualifier, task_type, task_package)

    if explore_targets == ui_runtime.GUI_PENDING:
        return valid_command, task_package

    if explore_targets is None:
        return valid_command, task_package

    for name in explore_targets:
        okay_to_act, task_package = can_character_act(name, TASK_EXPLORING, task_package)
        if not okay_to_act:
            continue

        # If they are not idle, add this action to their queue
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
        valid_command = True
        msg_explore(return_msg, turns_elapsed)

    return valid_command, task_package


def initiate_plant_task(qualifier, task_package, task_data=None):
    # plant some real food! (or whatever the player has chosen to plant)
    if task_data is None:
        task_data = {}
    queued_task = False
    valid_command = False

    is_queued_plant_task = (
        task_data.get("worker", "").casefold() == str(qualifier).casefold()
        and bool(task_data.get("orders"))
    )

    if is_queued_plant_task:
        crop_instructions = task_data
        name = qualifier
        queued_task = True
        valid_command = True

    else:
        answer = determine_what_to_plant_and_where(qualifier, task_package)
        if not answer:
            return valid_command, task_package

        crop_instructions = answer
        name = qualifier

    return finish_initiate_plant_task(name=name, crop_instructions=crop_instructions, task_package=task_package, queued_task=queued_task)


def initiate_examine_task(qualifier, task_package, item_name=""):
    # Examine something - or just glance at it
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]

    raw_examiner = qualifier
    task_type = TASK_EXAMINING
    valid_command = False
    awaiting_input = False

    # Get the examiner
    name_list = parse_command_targets(raw_examiner, task_type, task_package)

    if name_list == ui_runtime.GUI_PENDING:
        return valid_command, task_package

    if not name_list:
        return valid_command, task_package
    name = name_list[0]

    # Check whether the character can act
    okay_to_act, task_package = can_character_act(name, TASK_EXAMINING, task_package)
    if not okay_to_act:
        return valid_command, task_package
    is_human = name in humans

    # No item supplied, so ask the player to choose one
    if not item_name:
        examinable_items = [
            item["name"]
            for item in resources
            if item.get("examinable", False)
            and not item.get("examined", False)
        ]

        if not examinable_items:
            msg_resource(get_message("examine", "nothing_examinable"), turns_elapsed)
            return valid_command, task_package

        awaiting_input, item_name, task_package = get_examinable_item(task_package, examinable_items, name, is_human)
        if awaiting_input:
            return valid_command, task_package
        
        if not item_name:
            msg_error(get_message("examine", "no_item_name"), turns_elapsed)
            return valid_command, task_package

    # Find the target resource
    item = next(
        (resource for resource in resources
         if resource.get("name") == item_name),
        None
    )

    if not item:
        msg_resource(get_message("examine", "not_found", item=item_name), turns_elapsed)
        return valid_command, task_package

    # Busy character: queue the examination
    if not is_idle(name, humans, droids):
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item=item_name)
        valid_command = True
        return valid_command, task_package

    # Items with no examination duration are examined immediately
    if item.get("examine_turns", 0) <= 0:
        new_msg = item["msg"].format(name=name,
            R=item.get("red", ""), I=item.get("indigo", ""), G=item.get("gold", ""),
            A=item.get("apple", ""), C=item.get("cabbage", ""), P=item.get("potato", ""), amount=item.get("amount", ""))
        formatted_msg = f"{item_name}: {new_msg}"
        msg_resource(formatted_msg, turns_elapsed)

        item["examined"] = True
        item["msg"] = new_msg

        valid_command = True
        return valid_command, task_package

    # Set examination duration. Droids are quicker.
    if is_human:
        duration = (item.get("examine_turns", 0) + set_task_length("examine_human"))
    else:
        duration = (item.get("examine_turns", 0) + set_task_length("examine_droid"))
    valid_command = True

    # Create the examination task
    return_msg, task_package = create_task(name, task_type, duration, task_package, item=item_name)
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

    # Get target, either from qualifier or prompt
    reap_targets = parse_command_targets(raw_target, task_type, task_package)
    if reap_targets == ui_runtime.GUI_PENDING:
        return valid_command, task_package

    if not reap_targets:
        return valid_command, task_package

    # Reaping currently uses one worker.
    name = reap_targets[0]
    is_human = name in humans

    # Check if they can act
    okay_to_act, task_package = can_character_act(name, TASK_REAPING, task_package)
    if not okay_to_act:
        return valid_command, task_package
        
    # Warn if nothing is ready
    mature_exists = any(crop.get("mature", False) for crop in crops.values())
    if not mature_exists:
        msg_plant(get_message("reap", "no_mature_crops", target=name), turns_elapsed, tone="warn")
        # Allow them to continue anyway (they may have a plan for this)

    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type)
        valid_command = True
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
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_MINING
    valid_command = False

    mine_targets = parse_command_targets(qualifier, task_type, task_package)

    if mine_targets == ui_runtime.GUI_PENDING:
        return valid_command, task_package

    if mine_targets == None:
        return valid_command, task_package

    for name in mine_targets:
        is_human = name in humans
        okay_to_act, task_package = can_character_act(name, TASK_MINING, task_package)
        if not okay_to_act:
            continue  # Skip invalid characters

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


def initiate_refuel_task(raw_target, task_package, task_data=None):
    # Refuel the all-important power supply.
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_REFUELING
    valid_command = False

    # If task_data is provided, we are resuming a queued refuel task,
    # otherwise we are initiating a new refuel task.
    if task_data is not None and task_data != {}:
        # If task_data is provided, we are resuming a queued refuel task.
        total_power = task_data.get("total_power", 0)
        context = {
            "name": task_data.get("name", ""),
            "is_human": task_data.get("is_human", False),
            "task_package": task_package,
            "red": task_data.get("red", 0),
            "indigo": task_data.get("indigo", 0),
            "gold": task_data.get("gold", 0),
            "total_power": total_power,
            "num_days": get_refuel_days(total_power),
            "selection_mode": task_data.get("selection_mode", "all"),
        }
        task_package = finish_initiate_refuel_task(context)
        valid_command = True
        return valid_command, task_package
    
    elif task_data is None:
        task_data = {}

    refuel_target = parse_command_targets(raw_target, task_type, task_package)

    if refuel_target == ui_runtime.GUI_PENDING:
        return valid_command, task_package

    if not refuel_target:
        return valid_command, task_package
    name = refuel_target[0]     # Only one target for refuelling
    is_human = name in humans

    okay_to_act, task_package = can_character_act(name, TASK_REFUELING, task_package)
    if not okay_to_act:
        return valid_command, task_package

    power_supply = next((r for r in resources if r.get("name") == "PowerSupply"), None)
    if not power_supply or not power_supply.get("found", False):
        msg_power(get_message("refuel", "no_power_supply"), turns_elapsed, tone="warn" )
        return valid_command, task_package

    vial_store = power_supply.get("VialStore", {})

    if not vial_store or all(v == 0 for v in vial_store.values()):
        msg_crystal(get_message("refuel", "no_vials", name=name), turns_elapsed, tone="warn" )
        return valid_command, task_package

    context = {
        "name": name,
        "raw_target": raw_target,
        "is_human": is_human,
        "task_package": task_package,
    }

    return begin_refuel_vial_selection(context)


def begin_refuel_vial_selection(context):
    name = context["name"]
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    power_supply, vial_store, error_msg = get_refuel_power_supply_and_vials(name, task_package, require_vials=True)

    if error_msg:
        msg_power(error_msg, turns_elapsed, tone="warn")
        return False, task_package

    context["power_supply"] = power_supply
    context["vial_store"] = vial_store

    use_all = get_confirm("Would you like to use all available crystal vials for refuelling? (y/n): ", turns_elapsed=turns_elapsed, 
                          callback=resume_refuel_use_all, context=context )

    if use_all == ui_runtime.GUI_PENDING:
        return False, task_package

    return resume_refuel_use_all("yes" if use_all else "no", context)


def resume_refuel_use_all(answer, context):
    name = context["name"]
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    use_all = answer and str(answer).lower() in ("y", "yes", "true")

    if use_all:
        vial_store = context["vial_store"]

        red = vial_store.get("red", 0)
        indigo = vial_store.get("indigo", 0)
        gold = vial_store.get("gold", 0)

        total_power = calculate_refuel_power(red, indigo, gold)
        num_days = get_refuel_days(total_power)

        context["red"] = red
        context["indigo"] = indigo
        context["gold"] = gold
        context["total_power"] = total_power
        context["num_days"] = num_days
        context["selection_mode"] = "all"

        summary_msg = (
            f"Using all vials will create {total_power} units of power "
            f"(enough to charge a single droid for {num_days} days). Proceed? (y/n)"
        )

        proceed = get_confirm(summary_msg, turns_elapsed=turns_elapsed, callback=resume_refuel_confirm_all, context=context)

        if proceed == ui_runtime.GUI_PENDING:
            return None   # We are awaiting input, so do not resume turn processing yet

        return resume_refuel_confirm_all("yes" if proceed else "no", context)

    return ask_refuel_red(context)


def resume_refuel_confirm_all(answer, context):
    proceed = answer and str(answer).lower() in ("y", "yes", "true")

    if not proceed:
        return ask_refuel_red(context)

    vial_store = context["vial_store"]
    red = context["red"]
    indigo = context["indigo"]
    gold = context["gold"]

    remove_vials_from_store(vial_store, red, indigo, gold)

    return finish_initiate_refuel_task(context)


def ask_refuel_red(context):
    task_package = context["task_package"]
    vial_store = context["vial_store"]
    turns_elapsed = task_package["counters"]["turns"]
    red_avail = vial_store.get("red", 0)

    red = get_integer_input(f"How many RED crystals to use for refuelling? (0–{red_avail}): ", 0, red_avail, turns_elapsed=turns_elapsed,
                            callback=resume_refuel_red, context=context )

    if red == ui_runtime.GUI_PENDING:
        return False, task_package

    context["red"] = red
    return ask_refuel_indigo(context)


def resume_refuel_red(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    min_value = context.get("min_value")
    max_value = context.get("max_value")

    red, error = parse_integer_answer(answer, min_value, max_value)

    if error:
        msg_error(f"Invalid RED vial amount. Please enter a number from {min_value} to {max_value}.", turns_elapsed)
        return ask_refuel_red(context)

    context["red"] = red
    return ask_refuel_indigo(context)


def ask_refuel_indigo(context):
    task_package = context["task_package"]
    vial_store = context["vial_store"]
    turns_elapsed = task_package["counters"]["turns"]
    indigo_avail = vial_store.get("indigo", 0)

    indigo = get_integer_input(f"How many INDIGO crystals to use for refuelling? (0–{indigo_avail}): ", 0, indigo_avail, turns_elapsed=turns_elapsed,
                               callback=resume_refuel_indigo, context=context )

    if indigo == ui_runtime.GUI_PENDING:
        return False, task_package

    context["indigo"] = indigo
    return ask_refuel_gold(context)


def resume_refuel_indigo(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    min_value = context.get("min_value")
    max_value = context.get("max_value")

    indigo, error = parse_integer_answer(answer, min_value, max_value)

    if error:
        msg_error(f"Invalid INDIGO vial amount. Please enter a number from {min_value} to {max_value}.", turns_elapsed)
        return ask_refuel_indigo(context)

    context["indigo"] = indigo
    return ask_refuel_gold(context)


def ask_refuel_gold(context):
    task_package = context["task_package"]
    vial_store = context["vial_store"]
    turns_elapsed = task_package["counters"]["turns"]
    gold_avail = vial_store.get("gold", 0)

    gold = get_integer_input(f"How many GOLD crystals to use for refuelling? (0–{gold_avail}): ", 0, gold_avail, turns_elapsed=turns_elapsed,
                             callback=resume_refuel_gold, context=context)

    if gold == ui_runtime.GUI_PENDING:
        return False, task_package

    context["gold"] = gold
    return confirm_manual_refuel_selection(context)


def resume_refuel_gold(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    min_value = context.get("min_value")
    max_value = context.get("max_value")

    gold, error = parse_integer_answer(answer, min_value, max_value)

    if error:
        msg_error(f"Invalid GOLD vial amount. Please enter a number from {min_value} to {max_value}.", turns_elapsed)
        return ask_refuel_gold(context)

    context["gold"] = gold
    return confirm_manual_refuel_selection(context)


def confirm_manual_refuel_selection(context):
    name = context["name"]
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    red = context.get("red", 0)
    indigo = context.get("indigo", 0)
    gold = context.get("gold", 0)

    if red == 0 and indigo == 0 and gold == 0:
        msg_power("No crystals selected for processing. Task cancelled.", turns_elapsed)
        return False, task_package

    total_power = calculate_refuel_power(red, indigo, gold)
    num_days = get_refuel_days(total_power)

    context["total_power"] = total_power
    context["num_days"] = num_days
    context["selection_mode"] = "manual"

    summary_msg = (
        f"Summary: {red} red, {indigo} indigo, {gold} gold vials will create "
        f"{total_power} units of power "
        f"(enough to charge 1 droid for {num_days} days). Proceed? (y/n)"
    )

    proceed = get_confirm(summary_msg, turns_elapsed=turns_elapsed, callback=resume_refuel_confirm_manual, context=context)

    if proceed == ui_runtime.GUI_PENDING:
        return False, task_package

    return resume_refuel_confirm_manual("yes" if proceed else "no", context)


def resume_refuel_confirm_manual(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    proceed = answer and str(answer).lower() in ("y", "yes", "true")

    if proceed:
        vial_store = context["vial_store"]

        red = context["red"]
        indigo = context["indigo"]
        gold = context["gold"]

        remove_vials_from_store(vial_store, red, indigo, gold)

        return finish_initiate_refuel_task(context)

    retry = get_confirm("Would you like to choose different amounts? (y/n): ", turns_elapsed=turns_elapsed, 
                        callback=resume_refuel_retry_manual, context=context)

    if retry == ui_runtime.GUI_PENDING:
        return False, task_package

    return resume_refuel_retry_manual("yes" if retry else "no", context)


def resume_refuel_retry_manual(answer, context):
    name = context["name"]
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    retry = answer and str(answer).lower() in ("y", "yes", "true")

    if retry:
        context.pop("red", None)
        context.pop("indigo", None)
        context.pop("gold", None)
        context.pop("total_power", None)
        context.pop("num_days", None)
        return ask_refuel_red(context)

    msg_power(get_message("refuel", "aborted", name=name), turns_elapsed)
    return False, task_package


def finish_initiate_refuel_task(context):
    name = context["name"]
    is_human = context["is_human"]
    task_package = context["task_package"]

    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    task_type = TASK_REFUELING

    red = context.get("red", 0)
    indigo = context.get("indigo", 0)
    gold = context.get("gold", 0)
    total_power = context.get("total_power", calculate_refuel_power(red, indigo, gold))
    num_days = context.get("num_days", get_refuel_days(total_power))

    task_data = {
        "name": name,
        "is_human": is_human,
        "red": red,
        "indigo": indigo,
        "gold": gold,
        "total_power": total_power,
        "num_days": num_days,
        "selection_mode": context.get("selection_mode", "all"),
    }

    if context.get("selection_mode", "") == "all":
        msg_power(
            f"{name} will now proceed to use all available vials to refuel the PowerSupply "
            f"and add an extra {total_power} units and {num_days} days' worth of droid charges.", turns_elapsed)
    else:
        msg_power(
            f"{name} is now going to refuel the PowerSupply with only the amounts you have chosen. "
            f"This will add {total_power} units of power to the system. "
            f"Enough to charge a single droid for {num_days} days.", turns_elapsed)

    if not is_idle(name, humans, droids):
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, task_data=task_data)
        return task_package

    key = "refuel_human" if is_human else "refuel_droid"
    duration = set_task_length(key)

    return_msg, task_package = create_task(name, task_type, duration, task_package, task_data=task_data, item_name="PowerSupply")
    msg_power(return_msg, turns_elapsed)

    return task_package


def handle_assign_command(raw_target, task_package, task_data=None, item_name=""):
    # Assign a character to something useful (hopefully)
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_ASSIGNED
    valid_command = False
    if task_data is None:
        task_data = {}

    # Find discovered assignable items
    discovered_items = [item["name"] for item in resources if item["name"] in ASSIGNABLE_ITEMS]
    if not task_data:       # i.e. not a queued assign
        if not discovered_items:
            msg_info(get_message("assign", "nothing_assignable"), turns_elapsed)
            return valid_command, task_package

    assign_target = parse_command_targets(raw_target, task_type, task_package)

    if assign_target == ui_runtime.GUI_PENDING:
        return valid_command, task_package

    if not assign_target:
        return valid_command, task_package
    name = assign_target[0]

    okay_to_act, task_package = can_character_act(name, TASK_ASSIGNED, task_package)
    if not okay_to_act:
        return valid_command, task_package

    # This call handles both the queued and manual assign tasks
    outcome, task_package = get_new_assignee(discovered_items, name, task_package, task_data=task_data, item_name=item_name)

    return outcome, task_package


def get_new_assignee(discovered_items, target, task_package, task_data=None, item_name=""):
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    if task_data is None:
        task_data = {}

    menu = []
    assignees = {}

    # If this was a queued task, we'll have task_data
    if task_data:
        item_name = task_data.get("item_name", "")

    # Build the assignment menu and record any current assignee for each item.
    for index, item in enumerate(discovered_items, start=1):
        assigned = None

        for human_name in humans:
            if (humans[human_name].get("task") == TASK_ASSIGNED and humans[human_name].get("item") == item):
                assigned = human_name
                break

        if assigned is None:
            for droid_name in droids:
                if (droids[droid_name].get("task") == TASK_ASSIGNED and droids[droid_name].get("item") == item):
                    assigned = droid_name
                    break

        assignees[item] = assigned

        label = f"{index}. {item}"
        if assigned:
            label += f" (currently assigned: {assigned})"

        menu.append(label)

    # Queued task path:
    # The queued task already knows which item is being assigned.
    if item_name:
        if item_name not in assignees:
            msg_error(get_message("assign", "invalid_choice"), turns_elapsed)
            return TaskStartOutcome.INVALID, task_package

        current_assignee = assignees[item_name]

        awaiting_input, task_package = begin_assignment_for_item(target, item_name, current_assignee, task_package, task_data=task_data.copy())

        if awaiting_input:
            return TaskStartOutcome.AWAITING_INPUT, task_package

        return TaskStartOutcome.STARTED, task_package

    # Manual assignment path:
    # No item has been supplied, so ask the player to choose one.
    menu.append("0. Cancel assignment")

    context = {
        "task_package": task_package,
        "discovered_items": discovered_items,
        "target": target,
        "assignees": assignees,
    }

    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=resume_get_new_assignee,
            context=context
        )

    answer = get_input("input", "assigned_item", turns_elapsed, name=target, full_list=menu)

    if answer == ui_runtime.GUI_PENDING:
        return TaskStartOutcome.AWAITING_INPUT, task_package

    # CLI compatibility:
    # The resumed function will need to return the same Enum contract.
    outcome, task_package = resume_get_new_assignee(answer, context)

    return outcome, task_package


def resume_get_new_assignee(choice, context):
    task_package = context["task_package"]
    discovered_items = context["discovered_items"]
    target = context["target"]
    assignees = context["assignees"]
    turns_elapsed = task_package["counters"]["turns"]

    choice = choice.strip()

    if not choice.isdigit():
        msg_error(get_message("assign", "invalid_choice"),turns_elapsed)
        return task_package

    choice = int(choice)

    if choice == 0:
        msg_info(get_message("assign", "assignment_aborted", target=target), turns_elapsed)
        return task_package

    if not 1 <= choice <= len(discovered_items):
        msg_error(get_message("assign", "invalid_choice"), turns_elapsed)
        return task_package

    item_name = discovered_items[choice - 1]
    current_assignee = assignees[item_name]

    awaiting_input, task_package = begin_assignment_for_item(target, item_name, current_assignee, task_package)

    if awaiting_input:
        return None

    return task_package


def begin_assignment_for_item(target, item_name, current_assignee, task_package, task_data=None):
    #Begin assignment for a known item.
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    task_created = False

    if item_name == "CrystalProcessor":
        valid_command, task_package = initiate_assign_process_task(target, task_package, task_data=task_data)
        if not valid_command:
            return True, task_package
        task_created = True

    elif item_name == "ShieldManual":
        valid_command, task_package = initiate_assign_shieldmanual_task(target, task_package)
        if not valid_command:
            return True, task_package
        task_created = True

    elif item_name == "OldTerminal":
        msg_shield(get_message("assign", "old_terminal_assigned", name=target), turns_elapsed)
        valid_command, task_package = enter_oldterminal_commands(target, current_assignee, task_package)
        if not valid_command:
            return True, task_package
        task_created = True

    elif item_name == "CloakingShield":
        valid_command, task_package = check_shield_assign(target, task_package)
        if not valid_command:
            return True, task_package
        task_created = True

    else:
        msg_error(get_message("assign", "invalid_choice"), turns_elapsed)
        return False, task_package

    if task_created:
        if current_assignee and current_assignee != target:
            humans, droids = clear_task_for_character(current_assignee, item_name, humans, droids)

            msg_info(get_message("assign", "reassigned", item=item_name, old=current_assignee, new=target), turns_elapsed)

    return False, task_package    


def initiate_assign_process_task(name, task_package, task_data=None):
    # Assign a human or droid to process selected crystals using the CrystalProcessor.
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    item_name = "CrystalProcessor"
    valid_command = False
    if task_data is None:
        task_data = {}

    # Queued assign - the selection work has already been done
    if task_data:
        context = {
            "task_package": task_package,
            "name": name,
        }
        task_package = finish_assign_process_task(context, task_data=task_data)
        valid_command = True
        return valid_command, task_package

    # Else, continue with the initiation process

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

    # List the crystals and vials in storage
    list_crystals(task_package)

    red_avail = crystal_store["red"]

    context = {
        "name": name,
        "task_package": task_package,
    }

    red = get_integer_input(f"How many RED crystals to process? (0–{red_avail}): ",  0, red_avail, turns_elapsed=turns_elapsed,
                            callback=resume_assign_process_red, context=context)

    if red == ui_runtime.GUI_PENDING:
        return valid_command, task_package

    context["red"] = red
    return ask_assign_process_indigo(context)


def resume_assign_process_red(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    min_value = context.get("min_value")
    max_value = context.get("max_value")

    red, error = parse_integer_answer(answer, min_value, max_value)

    if error:
        msg_error(f"Invalid RED crystal amount. Please enter a number from {min_value} to {max_value}.", turns_elapsed)
        return initiate_assign_process_task(context["name"], task_package)

    context["red"] = red
    return ask_assign_process_indigo(context)


def ask_assign_process_indigo(context):
    task_package = context["task_package"]
    turns_elapsed= task_package["counters"]["turns"]
    crystal_store = next(
        r for r in task_package["resources"]
        if r.get("name") == "PowerSupply"
    )["CrystalStore"]

    indigo_avail = crystal_store["indigo"]

    indigo = get_integer_input(f"How many INDIGO crystals to process? (0–{indigo_avail}): ", 0, indigo_avail,  turns_elapsed=turns_elapsed,
                               callback=resume_assign_process_indigo, context=context)

    if indigo == ui_runtime.GUI_PENDING:
        return None     # Has to be none here, because this is a callback for the GUI

    context["indigo"] = indigo
    return ask_assign_process_gold(context)


def resume_assign_process_indigo(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    min_value = context.get("min_value")
    max_value = context.get("max_value")

    indigo, error = parse_integer_answer(answer, min_value, max_value)

    if error:
        msg_error(f"Invalid INDIGO crystal amount. Please enter a number from {min_value} to {max_value}.", turns_elapsed)
        return ask_assign_process_indigo(context)

    context["indigo"] = indigo
    return ask_assign_process_gold(context)


def ask_assign_process_gold(context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]
    crystal_store = next(
        r for r in task_package["resources"]
        if r.get("name") == "PowerSupply"
    )["CrystalStore"]

    gold_avail = crystal_store["gold"]

    gold = get_integer_input(f"How many GOLD crystals to process? (0–{gold_avail}): ", 0, gold_avail,  turns_elapsed=turns_elapsed,
                             callback=resume_assign_process_gold,  context=context)

    if gold == ui_runtime.GUI_PENDING:
        return None     # Has to be none here, because this is a callback for the GUI

    context["gold"] = gold
    return finish_assign_process_task(context)


def resume_assign_process_gold(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    min_value = context.get("min_value")
    max_value = context.get("max_value")

    gold, error = parse_integer_answer(answer, min_value, max_value)

    if error:
        msg_error(f"Invalid GOLD crystal amount. Please enter a number from {min_value} to {max_value}.", turns_elapsed)
        return ask_assign_process_gold(context)

    context["gold"] = gold
    return finish_assign_process_task(context)


def finish_assign_process_task(context, task_data=None):
    name = context["name"]
    task_package = context["task_package"]
    if task_data is None:
        task_data = {}

    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    task_type = TASK_ASSIGNED
    item_name = "CrystalProcessor"
    is_human = name in humans
    red = indigo = gold = 0
    duration = set_task_length("assign_human_process") if is_human else set_task_length("assign_droid_process")

    # If this is not a queued task (task_data={}) then finalise everything
    if not task_data:
        red = context.get("red", 0)
        indigo = context.get("indigo", 0)
        gold = context.get("gold", 0)

        if red == 0 and indigo == 0 and gold == 0:
            msg_crystal("No crystals selected for processing. Task cancelled.", turns_elapsed)
            return task_package

        total_power = red * POWER_PER_RED + indigo * POWER_PER_INDIGO + gold * POWER_PER_GOLD
        FULL_DROID_CHARGE_all = NUM_DROIDS * FULL_DROID_CHARGE
        days_per_FULL_DROID_CHARGE = FULL_DROID_CHARGE / (10 * IDLE_CHARGE_USAGE)

        if FULL_DROID_CHARGE_all > total_power:
            num_days = 1
            num_droids = total_power // (10 * IDLE_CHARGE_USAGE)

        else:
            num_days = total_power // (FULL_DROID_CHARGE_all / days_per_FULL_DROID_CHARGE)
            num_droids = NUM_DROIDS

        msg_crystal(get_message("assign", "CP_estimate", target=name, total_power=total_power, num=num_droids, day=num_days), turns_elapsed)

        # Put the task on the queue, or create it, whichever is appropriate
        task_data = {
            "item_name": item_name,
            "process_red": red,
            "process_indigo": indigo,
            "process_gold": gold
        }

        # If they are not idle, add this action to their queue
        if not is_idle(name, humans, droids):
            humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item=item_name, task_data=task_data)
            return task_package

        task_package["item"] = item_name
        task_package["task_data"] = task_data

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package, task_data=task_data, item_name=item_name)
    msg_crystal(return_msg, turns_elapsed)

    return task_package


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
    return_msg, task_package = create_task(name, task_type, duration, task_package, item_name=item_name)
    msg_shield(return_msg, turns_elapsed)
    
    return valid_command, task_package


def check_shield_assign(name, task_package):
    # Check who is assigned to the Shield
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    shieldstate = task_package["shieldstate"]
    is_droid = name in droids
    task_type = TASK_ASSIGNED
    valid_command = False

    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        valid_command = True
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item="CloakingShield")
        return valid_command, task_package

    if is_droid or not shieldstate["manual_decoded"]: # Can allow anyone to be assigned to the shield IF the manual is NOT decoded, but only droids if it is
        msg_shield(get_message("shield", "assigned_to", target=name), turns_elapsed)

        # Check that it was the droid with the Anicent Code that we assigned
        ancient_code = next((r for r in resources if r["name"] == "AncientDroidCode"), None)
        if ancient_code:
            if ancient_code["droidName"] == name:
                item_name = "CloakingShield"
                set_task_status_for_character(name, task_type, item_name, humans, droids, task_package["counters"]["turns"])
                valid_command = True
                shieldstate = set_shield_state("C", droids, resources, shieldstate)
                droids[name]["charge"] = FULL_DROID_CHARGE  # When they are connected they have full charge
        else:
            msg_shield(get_message("shield", "code_not_found", name=name), turns_elapsed, tone="warn")

    else:
        msg_shield(get_message("shield", "cannot_assign_human", target=name), turns_elapsed, tone="warn")
      
    return valid_command, task_package


def enter_oldterminal_commands(name, current_assignee, task_package):
    # Process commands to get the shield combination into the Shield
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    shieldstate = task_package["shieldstate"]
    task_type = TASK_ASSIGNED
    valid_command = False

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
    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=resume_enter_old_terminal_commands,
            context={
                "task_package": task_package,
                "name": name,
                "crystal_combo": crystal_combo,
                "item_name": item_name,
                "current_assignee": current_assignee
            }
        )
        
    answer = get_input("input", "oldterminal", turns_elapsed)
    if answer and answer == ui_runtime.GUI_PENDING:
        valid_command = False
        return valid_command, task_package


def resume_enter_old_terminal_commands(answer, context):
    task_package = context["task_package"]
    name = context["name"]
    crystal_combo = context["crystal_combo"]
    item_name = context["item_name"]
    current_assignee = context["current_assignee"]
    resources = task_package["resources"]
    droids = task_package["droids"]
    humans = task_package["humans"]
    shieldstate = task_package["shieldstate"]
    turns_elapsed = task_package["counters"]["turns"]
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
    
    if answer and answer and answer.lower() not in ("y", "yes"):
        msg_shield(get_message("shield", "combo_correct_aborted", name=name), turns_elapsed, tone="warn")
        return valid_command, task_package
    
    else:
        # Count available crystals and abort if there aren't enough
        available_crystals = do_we_have_enough(resources)
        if crystal_combo["red"] > available_crystals.get("red",0) or crystal_combo["indigo"] > available_crystals.get("indigo",0) or crystal_combo["gold"] > available_crystals.get("gold",0):
            msg_crystal(get_message("shield", "not_enough_crystals_with_combo", 
                                    need_R=crystal_combo["red"], need_I=crystal_combo["indigo"], need_G=crystal_combo["gold"], 
                                    have_R=available_crystals.get("red",0), have_I=available_crystals.get("indigo",0), have_G=available_crystals.get("gold",0)),
                                    turns_elapsed, tone="warn")
            valid_command = True    # They tried to use the crystal combination, but there aren't enough crystals. Penalise them! (by docking a turn)
            return valid_command, task_package
    
        # All good, so send the message to the player
        msg_shield(get_message("shield", "combo_correct", name=name), turns_elapsed, tone="success")
        shieldstate = set_shield_state("D", droids, resources, shieldstate)

        # Remove the crystals from the crystal store
        power_supply = next((r for r in resources if r["name"] == "PowerSupply"), None)
        crystal_store = power_supply["CrystalStore"]
        crystal_store["red"] -= crystal_combo["red"]
        crystal_store["indigo"] -= crystal_combo["indigo"]
        crystal_store["gold"] -= crystal_combo["gold"]

    valid_command = True
    is_droid = name in droids
    if is_droid:    # Any droid can be assigned to the OldTerminal
        task_type = TASK_ASSIGNED
        set_task_status_for_character(name, task_type, item_name, humans, droids, task_package["counters"]["turns"])
        shieldstate = set_shield_state("E", droids, resources, shieldstate)
    else:
        # A human cannot be assigned, but they don't know this - although they will after THIS message!
        msg_shield(get_message("shield", "terminal_cannot_assign_human", target=name), turns_elapsed, tone="warn")
        
    # Unassign previous assignee, if any
    if current_assignee and current_assignee != name:   # i.e. not a reassign
        humans, droids = clear_task_for_character(current_assignee, item_name, humans, droids)
        msg_info(get_message("assign", "reassigned", item=item_name, old=current_assignee, new=name), turns_elapsed)

    return task_package


def get_examinable_item(task_package, examinable_items, target, is_human):
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    awaiting_input = False

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

    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
            ui_runtime.ACTIVE_UI.set_pending_question(
                callback=resume_examine_task,
                context={
                    "task_package": task_package,
                    "examinable_items": examinable_items,
                    "examinees": examinees,
                    "target": target,
                    "is_human": is_human
                }
            )
    answer = get_input("input", "examine_what", turns_elapsed, target=target, items=menu)

    if answer and answer == ui_runtime.GUI_PENDING:
        awaiting_input = True
    else:
        awaiting_input = False
        msg_warn(get_message("error", "no_CLI"), turns_elapsed)

    return awaiting_input, "", task_package


def resume_examine_task(answer, context):
    task_package = context["task_package"]
    examinable_items = context["examinable_items"]
    examinees = context["examinees"]
    name = context["target"]
    is_human = context["is_human"]
    resources = task_package["resources"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    item_name = ""
    valid_command = False
    task_type = TASK_EXAMINING

    if not answer.isdigit():
        msg_error(get_message("examine", "invalid_choice"), turns_elapsed)
        valid_command = False
        return task_package

    if answer:
        answer = int(answer)
    if answer and answer == 0:
        msg_resource(get_message("examine", "not_doing", target=name), turns_elapsed)
        return valid_command, task_package
    
    elif answer and 1 <= answer <= len(examinable_items):
        item_name = examinable_items[answer - 1]
        current_examiner = examinees[item_name]

    else:
        msg_resource(get_message("examine", "invalid_choice", response=answer), turns_elapsed)
        return task_package

    # Find the target item
    item = next((r for r in resources if r["name"] == item_name), None)
    if not item:
        msg_resource(get_message("examine", "not_found", item=item_name), turns_elapsed)
        return task_package
    
    # If they are not idle, add this action to their queue
    if not is_idle(name, humans, droids):
        valid_command = True
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, item=item_name)
        return task_package

    # Immediate?
    if item.get("examine_turns", 0) <= 0:
        new_msg = item["msg"].format(name=name, R=item.get("red", ""), I=item.get("indigo", ""), G=item.get("gold", ""),
                A=item.get("apple",""), C=item.get("cabbage",""), P=item.get("potato",""),  amount=item.get("amount", ""))
        formatted_msg = f"{item_name}: " + new_msg
        msg_resource(formatted_msg, turns_elapsed)
        item["examined"] = True
        item["msg"] = new_msg
        valid_command = True
        return task_package

    # Unassign previous examiner, if any
    if current_examiner:
        humans, droids = clear_task_for_character(current_examiner, item_name, humans, droids)
        msg_resource(get_message("examine", "reassigned", item=item_name, previous=current_examiner, new=name), turns_elapsed)

    # Set the examine time, which is *quicker* for droids
    if is_human:
        duration = item.get("examine_turns", 0) + set_task_length("examine_human")
    else:
        duration = item.get("examine_turns", 0) + set_task_length("examine_droid")

    # Create the task
    return_msg, task_package = create_task(name, task_type, duration, task_package, item=item_name)
    msg_resource(return_msg, turns_elapsed)
    
    # The question is now resolved, so the suspended turn may continue.
    task_package["gamestate"]["turn_suspended"] = False
    save_config(task_package)

    return task_package


def handle_reset_command(task_package):
    awaiting_input = False
    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=reset_config,
            context={
                "task_package": task_package,
            }
        )
    turns_elapsed = task_package["counters"]["turns"]

    # Confirm that they really want to do this
    answer = get_input("input", "reset_confirm", turns_elapsed)

    if answer and answer == ui_runtime.GUI_PENDING:
        return awaiting_input, task_package
    else:
        msg_error(get_message("error", "no_CLI"), turns_elapsed)

    return awaiting_input, task_package