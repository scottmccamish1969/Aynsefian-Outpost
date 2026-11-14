# tasks.py

import random

from commands import initiate_charge_task, clear_task_for_character
from command_utils import (create_task, get_pronouns, get_task_by_worker, remove_task_by_id, choose_vials_and_display_power_produced)
from constants import (TASK_EATING, TASK_CHARGING, TASK_EXPLORING, TASK_PLANTING, TASK_EXAMINING, TASK_REAPING, TASK_MINING, TASK_ASSIGNED,
                       TASK_REFUELING, TASK_TOWING_DROID, RATION_PACKS, GROWTH_TURNS, YIELD_RANGE, CRYSTAL_RATIO, BASE_CRYSTAL_YIELD, 
                       TASK_LENGTH, INITIAL_SEED_STASH, REAP_SEED_FRACTION, SEED_PACKETS_USED, FULL_DROID_CHARGE, CommandOutcome)
from events import add_turn_event, lowercase_first
from lore.lore_ingame import get_message
import lore.user_interface as ui_runtime
from lore.user_interface import (get_input, msg_plant, msg_explore, msg_resource, msg_power, msg_food, msg_shield, msg_mine, msg_crystal,
                                 msg_error, msg_warn)
from planting import update_food_amount, build_crop_message
from resources import attempt_exploration, react_to_found_resource, add_or_get_discovered_item
from utils import set_shield_state, set_examine_needed_after_explore, can_character_act, process_hunger_status


def check_completed_tasks(task_package):
    completed = []
    tasks = task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]
    task_data = {}

    # Don't decrement the task counter here, just check for completed tasks
    for task_id, task in tasks.items():
        if task["duration"] <= 0:
            completed.append(task_id)

    for task_id in completed:
        task = tasks[task_id]
        name = task["name"]
        task_type = task["type"]
        item_name = task.get("item_name", "")
        task_data = task.get("task_data", {})
        completed_msg = ""

        if task_type == TASK_EATING:
            completed_msg, task_package = complete_feed_task(name, task_package)
            msg_food(completed_msg, turns_elapsed)
        elif task_type == TASK_CHARGING:
            completed_msg, task_package = complete_charge_task(name, task_package)
            msg_power(completed_msg, turns_elapsed)
        elif task_type == TASK_EXPLORING:
            completed_msg, task_package = complete_explore_task(name, task_package)
            msg_resource(completed_msg, turns_elapsed)
        elif task_type == TASK_PLANTING:
            completed_msg, task_package = complete_plant_task(name, task_package)
            msg_plant(completed_msg, turns_elapsed)
        elif task_type == TASK_EXAMINING:
            completed_msg, task_package = complete_examine_task(name, task_package)
            msg_resource(completed_msg, turns_elapsed)
        elif task_type == TASK_REAPING:
            completed_msg, task_package = complete_reap_task(name, task_package)
            msg_plant(completed_msg, turns_elapsed)
        elif task_type == TASK_MINING:
            completed_msg, task_package = complete_mine_task(name, task_package)
            msg_mine(completed_msg, turns_elapsed)
        elif task_type == TASK_ASSIGNED:
            if item_name == "CrystalProcessor":
                completed_msg, task_package = complete_assign_process_task(name, task_package, task_data=task_data)
                msg_crystal(completed_msg, turns_elapsed)
            elif item_name == "ShieldManual":
                completed_msg, task_package = complete_assign_shieldmanual_task(name, task_package)
                msg_shield(completed_msg, turns_elapsed)
            else:
                completed_msg = get_message("assign", "cannot_complete_assign_task")
                msg_warn(completed_msg, turns_elapsed)
        elif task_type == TASK_REFUELING:
            completed_msg, task_package = complete_refuel_task(name, task_package, task_data=task_data)
            msg_crystal(completed_msg, turns_elapsed)
        elif task_type == TASK_TOWING_DROID:
            completed_msg, task_package = complete_towing_task(name, task_package, task_data=task_data)
            msg_power(completed_msg, turns_elapsed)
        else:
            completed_msg = get_message("task", "unknown", name=name, task_type=task_type.lower())
            msg_error(completed_msg, turns_elapsed)

        # Remove the previous task
        remove_task_by_id(task_id, task_package)

    return task_package


def complete_feed_task(name, task_package):
    # Do the feed task after waiting the set amount of time
    return_msg = ""
    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks= task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]

    # We are now using the task_data inside the task, rather than the global task_data dict
    task_id, task = get_task_by_worker(tasks, name)
    if not task:
        msg_error(get_message("error", "no_existing_task", name=name), turns_elapsed)
        return return_msg, task_package

    task_data = task.get("task_data", {})
    if not task_data:
        msg_error(get_message("error", "missing_food_task_data", name=name), turns_elapsed)
        return return_msg, task_package

    # Unpack the task_data dict
    #     Reminder of the structure:   food_items = {"rationPack": 0, "potato": 0, "onion": 0, "apple": 0, "avocado": 0, }
    food_items = task_data["food_items"]
    hunger_reduction = task_data["hunger_reduction"]
    meal_type = task_data["meal_type"]

    if name in humans:
        # Feed the human
        humans[name]["hunger"] = max(0, humans[name]["hunger"] - hunger_reduction)

        # Adjust their hunger
        task_package = process_hunger_status(name, task_package)

        # Build the message
        return_msg = format_feed_message(name, humans, food_items, meal_type)

        # Add the event
        event_priority = 7
        task_package = add_turn_event(task_package, "eat", event_priority, name=name, result="completed")
        
        # Clear the flags
        humans[name]["awaiting_food"] = False
        humans[name]["food_wait_declined"] = False

    # Now do the fun message for a droid they tried to feed, or an error if the wrong name (should not happen)
    elif name in droids:
        msg_power(get_message("feed_droid", "responses", droid_name=name), turns_elapsed)

    else:
        msg_food(get_message("error", "feed_invalid", person_name=name), turns_elapsed, tone="error")

    return return_msg, task_package


def format_feed_message(name, humans, food_items, meal_type):
    pronouns = get_pronouns(name, True)

    fed_ration = food_items.get("rationPack", 0)
    fed_potato = food_items.get("potato", 0)
    fed_onion = food_items.get("onion", 0)
    fed_apple = food_items.get("apple", 0)
    fed_avocado = food_items.get("avocado", 0)

    meal_type_strings = {
        "normal": "a normal meal of",
        "emergency": "a significant meal due to extreme hunger of",
        "partial": "a rather inadequate partial meal of",
    }

    meal_type_string = meal_type_strings.get(meal_type, "a meal of")

    produce_quantities = {
        "P": fed_potato,
        "O": fed_onion,
        "A": fed_apple,
        "V": fed_avocado,
    }

    active_produce = frozenset(key for key, quantity in produce_quantities.items() if quantity > 0)

    produce_servings = ", ".join(
        f"{quantity} {item} servings"
        for item, quantity in food_items.items()
        if quantity > 0 and item != "rationPack"
    )

    common_fields = {
        "person_name": name,
        "meal_type": meal_type_string,
        "P": fed_potato,
        "O": fed_onion,
        "A": fed_apple,
        "V": fed_avocado,
        "pronoun1": pronouns["p1"],
        "pronoun2": pronouns["p1"].lower(),
    }

    # Ration packs, either alone or combined with produce.
    if fed_ration > 0:
        if active_produce:
            return get_message("feed", "fed_ration_and_produce", **common_fields, real_food=produce_servings)

        ration_key = (
            "fed_ration"
            if fed_ration == 1
            else "fed_two_rations"
        )

        return get_message("feed", ration_key, **common_fields)

    produce_message_keys = {
        frozenset({"A"}): "fed_A",
        frozenset({"C"}): "fed_C",
        frozenset({"P"}): "fed_P",
        frozenset({"A", "C"}): "fed_A_C",
        frozenset({"A", "P"}): "fed_A_P",
        frozenset({"C", "P"}): "fed_C_P",
        frozenset({"A", "C", "P"}): "fed_A_C_P",
    }

    message_key = produce_message_keys.get(active_produce, "fed_a_meal")

    return get_message("feed", message_key, **common_fields)


def complete_charge_task(name, task_package):
    droids = task_package["droids"]
    tasks = task_package["tasks"]

    task_id, task = get_task_by_worker(tasks, name)
    task_data = task.get("task_data", {})

    target_charge = task_data.get("target_charge", FULL_DROID_CHARGE)

    droids[name]["charge"] = target_charge
    droids[name]["awaiting_power"] = False
    droids[name]["power_wait_declined"] = False

    return_msg = get_message("charge", "success", droid_name=name, new_charge=target_charge)

    # Add the event    
    event_priority = 7
    task_package = add_turn_event(task_package, "charge", event_priority, name=name, result="completed", new_charge=target_charge)

    return return_msg, task_package


def complete_explore_task(name, task_package):
    humans = task_package["humans"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    return_msg = ""
    item_priority = 0
        
    # Resolve the end of an explore task for `character`.
    discovered_name, task_package = attempt_exploration(task_package)

    if discovered_name:
        if isinstance(discovered_name, dict):
            discovered_name = discovered_name.get("name", None)
        elif not isinstance(discovered_name, str):
            msg_explore(get_message("explore", "unexpected_type", name=discovered_name), turns_elapsed)
            discovered_name = None

        # Ensure the discovered item exists in the resources list
        discovered, resources = add_or_get_discovered_item(resources, discovered_name)
        res_name = discovered["name"]

        # Add to the events list
        item_category = discovered.get("category", "essential")
        category_counter = discovered.get("category_counter", 0)
        examine_turns = discovered.get("examine_turns", 0)
        item_description = lowercase_first(discovered.get("msg", "in good condition."))
        item_class = discovered.get("item_class", "portable")
        if item_category== "essential":
            item_priority = 4
        elif item_category in ("chain", "replacement"):
            item_priority = 5
        else:   # "junk" item
            item_priority = 6

        # React to the newly found resource
        task_package = react_to_found_resource(res_name, task_package)
        
        # Handle the post "find" tasks, excluding the examine
        if res_name == "FoodStore":
            return_msg = get_message("explore", "found_food", target=name, amount=RATION_PACKS, res_name=res_name)
            discovered["examinable"] = False
            
            # Add the turn event
            item_priority = 4
            item_category = "essential"
            task_package = add_turn_event(task_package, "examine", item_priority, name=name, examine_type="instant", description=item_description,
                                          item="FoodStore", category=item_category, item_class=item_class, result="completed")
            
        else:
            if examine_turns > 0:
                task_package = add_turn_event(task_package, "explore", item_priority, name=name, result="found", 
                                              discovered=discovered_name, examine_turns=examine_turns, item_class=item_class,
                                              category=item_category, category_counter=category_counter)
            # If examine_turns = 0 we add a different type of event in the examine handler
            
            task_package = set_examine_needed_after_explore(name, res_name, task_package)
            discovered["examinable"] = True

    else:
        is_human = name in humans
        pronouns = get_pronouns(name, is_human=is_human)
        if is_human: 
            has_have = "has" 
        else: 
            has_have = "have"
        return_msg = get_message("explore", "nothing_found", target=name, pronoun=pronouns["p1"].lower(), pronoun2=pronouns["p3"].lower(), has_have=has_have)

        item_priority = 8  # Lower priority for "nothing found" events
        task_package = add_turn_event(task_package, "explore", item_priority, name=name, item_class="",
                                      result="nothing", discovered="", examine_turns=0,
                                      category="", category_counter=0)

    return return_msg, task_package


def handle_examine_answer(answer, context):
    task_package = context["task_package"]
    name = context["character_name"]
    item = context["item"]
    item_name = context["item_name"]
    is_human = context["is_human"]
    turns_elapsed = task_package["counters"]["turns"]

    humans = task_package["humans"]
    droids = task_package["droids"]

    # ---------------------------------------------------------
    # YES - examine the discovered item
    # ---------------------------------------------------------
    if answer and answer.lower() in ("y", "yes"):
        return_msg, is_examining, task_package = examine_after_explore(task_package, name, item, item_name, is_human, False)

        msg_resource(return_msg, turns_elapsed)

        # The pending discovery has now been dealt with.
        if is_human:
            humans[name]["examine_needed"] = ""
        else:
            droids[name]["examine_needed"] = ""

        if is_examining:
            return CommandOutcome.SUCCESS, task_package

        # The request was understood but the Examine task
        # could not actually be started.
        return CommandOutcome.CANNOT_EXECUTE, task_package

    # ---------------------------------------------------------
    # NO - leave the item unexamined
    # ---------------------------------------------------------
    return_msg = get_message("explore", "not_examined", target=name, res_name=item["name"])
    msg_resource(return_msg, turns_elapsed)

    # Add an event
    event_priority = 9
    task_package = add_turn_event(task_package, "examine", event_priority, name=name, result="aborted")

    # The Commander has deliberately declined the examination,
    # so clear the pending prompt.
    if is_human:
        humans[name]["examine_needed"] = ""
    else:
        droids[name]["examine_needed"] = ""

    return CommandOutcome.SUCCESS, task_package


def examine_after_explore(task_package, character_name, item, item_name, is_human, is_examining):
    # Handler for what to do after an explore has completed
    humans = task_package["humans"]
    droids = task_package["droids"]
    
    def set_task_length(task_type):
        low, high = TASK_LENGTH[task_type]
        return random.randint(low, high)

    if item.get("examine_turns", 0) > 0:
        duration = 0
                    
        # Do human or droid specific things
        if is_human:
            duration = item["examine_turns"] + set_task_length("examine_human")
            humans[character_name]["generated"] = True
        else:
            duration = item["examine_turns"] + set_task_length("examine_droid")
            droids[character_name]["generated"] = True

        # Create the Examine task
        return_msg, task_package = create_task(character_name, TASK_EXAMINING, duration, task_package, item_name=item_name)
        is_examining = True
    else:
        # Instant examine
        new_msg = item["msg"].format(name=character_name, 
                R=item.get("red", ""), I=item.get("indigo", ""), G=item.get("gold", ""),
                P=item.get("potato",""), O=item.get("onion",""), A=item.get("apple",""), V=item.get("avocado", ""), 
                amount=item.get("amount", ""))
        formatted_msg = f"{item_name}: " + new_msg
        return_msg = formatted_msg
        item["examined"] = True
        item["msg"] = new_msg

        # Add the turn event
        item_priority = 6
        item_category = item.get("category", "junk")
        item_description = lowercase_first(item.get("msg", "in good condition."))
        item_class = item.get("item_class", "portable")
        task_package = add_turn_event(task_package, "examine", item_priority, name=character_name, examine_type="instant", description=item_description,
                                      item=item_name, category=item_category, item_class=item_class, result="completed")
            
        humans, droids = clear_task_for_character(character_name, "", humans, droids) # Clear the task if instant examine
                    
    return return_msg, is_examining, task_package


def complete_examine_task(name, task_package):
    return_msg = ""
    tasks = task_package["tasks"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    shieldstate = task_package["shieldstate"]

    task_id, task = get_task_by_worker(tasks, name)
    item_name = task["item_name"]

    if not item_name:
        # Should never happen now — but safety first.
        return_msg = get_message("examine", "no_item_name")
        humans, droids = clear_task_for_character(name, "", humans, droids)   # Clear the task
        return return_msg, task_package

    # Find the item in resources
    item = next((r for r in resources if r["name"] == item_name), None)
    if not item:
        return_msg = get_message("examine", "no_item", item=item_name)
        humans, droids = clear_task_for_character(name, "", humans, droids)   # Clear the task
        return return_msg, task_package

    if item_name == "AncientDroidCode":
        resources, droids, shieldstate = choose_droid_with_ancient_code(resources, droids, shieldstate, turns_elapsed)

    elif item_name == "CrystalCombination":
        resources, shieldstate = define_crystal_combination(resources, shieldstate, turns_elapsed)

    else:
        # Print the message
        new_msg = item["msg"].format(name=name, 
                R=item.get("red", ""), I=item.get("indigo", ""), G=item.get("gold", ""),
                P=item.get("potato",""), O=item.get("onion",""), A=item.get("apple",""), V=item.get("avocado", ""), 
                amount=item.get("amount", ""))
        formatted_msg = f"{name} has finished examining **{item_name}**: " + new_msg

        return_msg = formatted_msg
        item["msg"] = new_msg

    # Add the turn event
    item_category = item.get("category", "junk")
    item_priority = (4 if item_category == "essential" else 5)
    item_priority = (6 if item_category == "junk" else 5)
    item_description = lowercase_first(item.get("msg", "in good condition."))
    item_class = item.get("item_class", "portable")
    task_package = add_turn_event(task_package, "examine", item_priority, name=name, examine_type="normal", description=item_description,
                                  item=item_name, category=item_category, item_class=item_class, result="completed")

    # Mark examined
    item["examined"] = True

    # Save back into list
    for r in resources:
        if r["name"] == item_name:
            r.update(item)

    # Clear the task
    humans, droids = clear_task_for_character(name, "", humans, droids)

    return return_msg, task_package


def complete_plant_task(name, task_package):
    tasks = task_package["tasks"]
    resources = task_package["resources"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    crops = task_package["crops"]
    crop_number = task_package["counters"]["crop"]
    turns_elapsed = task_package["counters"]["turns"]
    return_msg = ""

    # We are now using the task_data inside the task, rather than the global task_data dict
    task_id, task = get_task_by_worker(tasks, name)
    if not task:
        msg_error(get_message("error", "no_existing_task", name=name), turns_elapsed)
        return return_msg, task_package
    task_data = tasks[task_id]["task_data"]
    
    # Complete the planting of what was advised
    orders = task_data["orders"]
    worker = task_data["worker"]

    # Locate hydroponics room
    hydro = next((r for r in resources if r["name"] == "HydroponicsRoom"), None)
    if not hydro:
        return_msg = get_message("plant", "no_hydroponics")
        return return_msg, task_package

    # Locate seed stash
    stash = next((r for r in resources if r["name"] == "SeedStash"), None)
    if not stash:
        return_msg = get_message("plant", "no_seedstash")
        humans, droids = clear_task_for_character(worker, "", humans, droids)   # Clear the task
        return return_msg, task_package
    
    # Count the seeds before we do the actual planting
    total_seeds_before = stash.get('potato', 0) + stash.get('onion', 0) + stash.get('apple', 0) + stash.get('avocado', 0)

    total_planted = 0

    for order in orders:
        crop_type = order["crop"]
        beds_requested = order["beds"]

        for bed_id in beds_requested:

            # 🔎 Find the actual bed object by ID
            bed = next((b for b in hydro["beds"] if b == bed_id), None)

            if bed is None:
                msg_plant(get_message("plant", "invalid_bed", bed=bed_id), turns_elapsed, tone="error")
                continue

            # 🚫 Bed not available (for now we assume bed is reserved properly - so we don't check for that)
            if bed["occupied"]:
                msg_plant(get_message("plant", "bed_occupied", bed=bed_id), turns_elapsed, tone="error")
                continue

            # 🌱 Seed check
            if stash.get(crop_type, 0) <= 0:
                msg_plant(get_message("plant", "not_enough_seeds", crop=crop_type), turns_elapsed, tone="warn")
                continue

            # ⏱ Growth time
            base = GROWTH_TURNS[crop_type]
            deviation = int(base * 0.1)
            turns_to_complete = random.randint(base - deviation, base + deviation)

            # 🌾 Register crop
            crops[str(crop_number)] = {
                "crop_id": crop_number,
                "crop_type": crop_type,
                "bed_id": bed_id,
                "worker": worker,
                "turns_remaining": turns_to_complete,
                "mature": False
            }

            # 🛏 Update THIS bed only
            bed["reserved"] = False
            bed["occupied"] = True
            bed["crop_id"] = crop_number

            # 🌰 Deduct seed
            stash[crop_type] -= 1
            if stash[crop_type] < 0:
                stash[crop_type] = 0

            total_planted += 1
            crop_number += 1
            task_package["counters"]["crop"] = crop_number

            # 🌿 Per-crop feedback
            msg_plant(get_message("plant", "crop_started", target=worker, crop=crop_type, bed=bed_id), turns_elapsed, tone="success")

    # 📢 Summary message
    if total_planted == 0:
        return_msg = get_message("plant", "nothing_planted", target=worker)
    else:
        return_msg = get_message("plant", "task_complete", target=worker, number=total_planted)

    # Clear the task
    humans, droids = clear_task_for_character(worker, "", humans, droids)

    # Create the turn event
    item_priority = 3
    crop_message = build_crop_message(task_data, stage="complete")
    task_package = add_turn_event(task_package, "plant", item_priority, name=name, result="completed", crop_message=crop_message)

    # Clear the task_data in the config file
    task_data = {}

    # Now check how many seeds we have and warn if low (below 20% of the initial stash)
    total_seeds_after = stash.get('potato', 0) + stash.get('onion', 0) + stash.get('apple', 0) + stash.get('avocado', 0)
    if total_seeds_after < INITIAL_SEED_STASH * 0.2 and total_seeds_before >= INITIAL_SEED_STASH * 0.2:
        msg_plant(get_message("plant", "low_seeds_warning"), turns_elapsed, low_count=INITIAL_SEED_STASH * 0.2, tone="warn")

    return return_msg, task_package


def complete_reap_task(name, task_package):
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    crops = task_package["crops"]
    return_msg = ""
    potatoseeds = onionseeds = appleseeds = avocadoseeds = 0

    hydro = next((r for r in resources if r["name"] == "HydroponicsRoom"), None)

    harvested_total = 0
    harvested_by_type = {"potato": 0, "onion": 0, "apple": 0, "avocado": 0}

    # --- Prepare to collect results ---
    harvest_summary = {}  # e.g. {"apple": 180, "avocado": 14}

    # --- Process each mature crop ---
    for cid in list(crops.keys()):
        crop = crops[cid]

        if crop["mature"]:
            ctype = crop["crop_type"]
            if ctype == "potato":
                potatoseeds += int(REAP_SEED_FRACTION * SEED_PACKETS_USED["potato"])
            if ctype == "onion":
                onionseeds += int(REAP_SEED_FRACTION * SEED_PACKETS_USED["onion"])
            if ctype == "apple":
                appleseeds += int(REAP_SEED_FRACTION * SEED_PACKETS_USED["apple"])
            elif ctype == "avocado":
                avocadoseeds += int(REAP_SEED_FRACTION * SEED_PACKETS_USED["avocado"])


            low, high = YIELD_RANGE[ctype]
            yield_amount = random.randint(low, high)

            # Track totals for the final message
            harvest_summary[ctype] = harvest_summary.get(ctype, 0) + yield_amount

            harvested_total += yield_amount
            harvested_by_type[ctype] += yield_amount

            # --- Add to FoodStore ---
            resources = update_food_amount(resources, ctype, yield_amount, turns_elapsed, allow_negative=False)

            # Free the bed
            bed = {}
            for b in hydro["beds"]:
                if b["id"] == crop["bed_id"]["id"]:
                    bed = b
                    break
            if not bed:
                return_msg = get_message("reap", "invalid_bed", crop=crop["id"], bed=crop["bed_id"]["id"])
                return return_msg, task_package

            bed["occupied"] = False
            bed["crop_id"] = None

            del crops[cid]

    # --- Build harvest message ---
    potatoes = onions = apples = avocados = 0
    harvest_parts = []
    for ctype, total_amount in harvest_summary.items():
        if total_amount == 1:
            harvest_parts.append(f"{total_amount} {ctype}")
        else:
            if ctype != "potato":
                harvest_parts.append(f"{total_amount} {ctype}s")
            else:
                harvest_parts.append(f"{total_amount} {ctype}es")
        if ctype == "potato":
            potatoes += total_amount
        elif ctype == "onion":
            onions += total_amount
        elif ctype == "apple":
            apples += total_amount
        elif ctype == "avocado":
            avocados += total_amount

    joined_msg = ", ".join(harvest_parts)

    # Now update the seeds, generated by reaping
    stash = next((r for r in resources if r["name"] == "SeedStash"), None)
    if not stash:
        return_msg = get_message("reap", "no_seedstash")
        return return_msg, task_package

    seed_parts = []
    if potatoseeds > 0:
        stash["potato"] += potatoseeds
        seed_parts.append(f"{potatoseeds} potato seeds")
    if onionseeds > 0:
        stash["onion"] += potatoseeds
        seed_parts.append(f"{onionseeds} onion seeds")
    if appleseeds > 0:
        stash["apple"] += appleseeds
        seed_parts.append(f"{appleseeds} apple seeds")
    if avocadoseeds > 0:
        stash["avocado"] += avocadoseeds
        seed_parts.append(f"{avocadoseeds} avocado seeds")

    seedsmsg = ""
    if seed_parts:
        if len(seed_parts) == 1:
            seedsmsg = f" You have retrieved {seed_parts[0]} from the reaping."
        elif len(seed_parts) == 2:
            seedsmsg = f" You have retrieved {seed_parts[0]} and {seed_parts[1]} from the reaping."
        elif len(seed_parts) == 3:
            seedsmsg = f" You have retrieved {seed_parts[0]}, {seed_parts[1]} and {seed_parts[2]} from the reaping."
        else:
            seedsmsg = f" You have retrieved {seed_parts[0]}, {seed_parts[1]}, {seed_parts[2]} and {seed_parts[3]} from the reaping."

    return_msg = get_message("reap", "harvest_complete", target=name, items=joined_msg, seedsmsg=seedsmsg)

    # Clear the task
    humans, droids = clear_task_for_character(name, "", humans, droids)

    # Add the event
    event_priority = 2
    task_package = add_turn_event(task_package, "reap", event_priority, name=name, result="completed",
                                  potatoes=potatoes, onions=onions, apples=apples, avocados=avocados)

    return return_msg, task_package


def complete_mine_task(name, task_package):
    resources = task_package["resources"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    return_msg = ""

    # Store the crystals in the PowerSupply (the player won't see this anyway)
    power_supply = next((r for r in resources if r["name"] == "PowerSupply"), None)
    if not power_supply and not power_supply["CrystalStore"]:
        return_msg = get_message("mine", "cannot_store")
        humans, droids = clear_task_for_character(name, "", humans, droids)   # Clear the task
        return return_msg, task_package
    else:
        crystal_store = power_supply["CrystalStore"]

    red = int(BASE_CRYSTAL_YIELD * CRYSTAL_RATIO["red"])
    indigo = int(BASE_CRYSTAL_YIELD * CRYSTAL_RATIO["indigo"])
    gold = BASE_CRYSTAL_YIELD - red - indigo

    crystal_store["red"] += red
    crystal_store["indigo"] += indigo
    crystal_store["gold"] += gold

    # Add to the 'total_found' tally, as later these might be processed for various reasons (power, shield, other?) 
    crystal_store["total_found"]["red"] += red
    crystal_store["total_found"]["indigo"] += indigo
    crystal_store["total_found"]["gold"] += gold

    return_msg = get_message("mine", "completed", name=name, red=red, indigo=indigo, gold=gold)
    
    # Clear the task
    humans, droids = clear_task_for_character(name, "", humans, droids)

    # Add the event
    event_priority = 2
    task_package = add_turn_event(task_package, "mine", event_priority, name=name, result="completed", red=red, indigo=indigo, gold=gold)

    return return_msg, task_package


def complete_assign_process_task(name, task_package, task_data=None):
    # Converts selected quantities of raw crystals into vials, preserving unprocessed ones.
    resources = task_package["resources"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    return_msg = ""
    if task_data is None:
        task_data = {}

    task_id, task = get_task_by_worker(tasks, name)
    item_name = task.get("item_name", "")
    task_data = task.get("task_data", {})
    if not task_data or not item_name:
        return_msg = get_message("assign", "process_no_task_data", name=name)
        humans, droids = clear_task_for_character(name, "", humans, droids)   # Clear the task
        return return_msg, task_data

    power_supply = next((r for r in resources if r["name"] == "PowerSupply"), None)
    if not power_supply:
        return_msg = get_message("assign", "process_no_power_supply")
        humans, droids = clear_task_for_character(name, "", humans, droids)   # Clear the task
        return return_msg, task_data

    # Ensure CrystalStore exists
    if "CrystalStore" not in power_supply:
        return_msg = get_message("assign", "process_no_crystals_to_process", name=name, item=item_name)
        humans, droids = clear_task_for_character(name, "", humans, droids)   # Clear the task
        return return_msg, task_data

    crystal_store = power_supply["CrystalStore"]

    # Initialise VialStore if needed
    if "VialStore" not in power_supply:
        power_supply["VialStore"] = {"red": 0, "indigo": 0, "gold": 0}

    vial_store = power_supply["VialStore"]

    # Retrieve how many crystals were assigned to be processed
    red = task_data.get("process_red", 0)
    indigo = task_data.get("process_indigo", 0)
    gold = task_data.get("process_gold", 0)

    if red == 0 and indigo == 0 and gold == 0:
        return_msg = get_message("assign", "process_no_crystals_to_process", name=name, item=item_name)
        humans, droids = clear_task_for_character(name, "", humans, droids)   # Clear the task
        return return_msg, task_data

    # Ensure there's enough in store (fail gracefully if not)
    if red > crystal_store["red"] or indigo > crystal_store["indigo"] or gold > crystal_store["gold"]:
        return_msg = get_message("assign", "process_not_enough_crystals", name=name,
                                 haveR=crystal_store["red"], haveI=crystal_store["indigo"], haveG=crystal_store["gold"], 
                                 needR=red, needI=indigo, needG=gold)
        humans, droids = clear_task_for_character(name, item_name, humans, droids)
        return return_msg, task_data

    # Process selected crystals
    vial_store["red"] += red
    vial_store["indigo"] += indigo
    vial_store["gold"] += gold

    crystal_store["red"] -= red
    crystal_store["indigo"] -= indigo
    crystal_store["gold"] -= gold

    crystal_store["processed"]["red"] += red
    crystal_store["processed"]["indigo"] += indigo
    crystal_store["processed"]["gold"] += gold

    total_units = red + indigo + gold
    return_msg = get_message("assign", "process_completed", name=name, item=item_name, total_units=total_units)

    # Add the event
    event_priority = 3
    task_package = add_turn_event(task_package, "assign", event_priority, name=name, result="completed", item=item_name, red=red, indigo=indigo, gold=gold)

    # Clear the task and assignment
    humans, droids = clear_task_for_character(name, item_name, humans, droids)

    return return_msg, task_package


def complete_assign_shieldmanual_task(name, task_package):
    resources = task_package["resources"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    shieldstate = task_package["shieldstate"]
    return_msg = ""
    is_human = name in humans
    pronouns = get_pronouns(name, is_human=is_human)

    # 1. Check for DecodeKey in resources
    decode_key = next((r for r in resources if r["name"] == "DecodeKey"), None)
    shield_manual = next((r for r in resources if r["name"] == "ShieldManual"), None)

    if not decode_key:
        return_msg = get_message("shield", "no_decode", name=name, pronoun=pronouns["p1"].lower())
        humans, droids = clear_task_for_character(name, "ShieldManual", humans, droids)   # Clear the task
        return return_msg, task_package

    if not decode_key.get("examined", False):
        return_msg = get_message("shield", "no_decode_examined", name=name)
        humans, droids = clear_task_for_character(name, "ShieldManual", humans, droids)   # Clear the task
        return return_msg, task_package

    # 2. Decode success
    if shield_manual:
        shield_manual["decoded"] = True
        return_msg = get_message("shield", "manual_decoded", name=name)
        shieldstate = set_shield_state("B", droids, resources, shieldstate)
       
        # Add the event
        event_priority = 3
        task_package = add_turn_event(task_package, "shield", event_priority, name=name, result="completed", item="ShieldManual", decoded=True)
    else:
       return_msg = get_message("shield", "manual_not_found", name=name)

    humans, droids = clear_task_for_character(name, "ShieldManual", humans, droids)   # Clear the task

    return return_msg, task_package


def complete_refuel_task(name, task_package, task_data=None):
    humans = task_package["humans"]
    droids = task_package["droids"]
    if not task_data:
        task_data = {}

    amount_only = True

    return_msg, total_power, task_package = choose_vials_and_display_power_produced(name, task_package, amount_only=amount_only, task_data=task_data)

    if return_msg != "" and total_power == 0:
        humans, droids = clear_task_for_character(name, "", humans, droids)
        return return_msg, task_package

    return_msg = get_message("refuel", "completed", name=name, power=total_power)

    humans, droids = clear_task_for_character(name, "", humans, droids)

    # Add the event
    event_priority = 2
    task_package = add_turn_event(task_package, "refuel", event_priority, name=name, result="completed", total_power=total_power)

    return return_msg, task_package



def choose_droid_with_ancient_code(resources, droids, shieldstate, turns_elapsed):
    eligible_droids = list(droids.keys())
    if not eligible_droids:
        msg_shield(get_message("shield", "no_droid_with_code"), turns_elapsed)
        return resources, droids, shieldstate

    chosen_droid = random.choice(eligible_droids)
    droids[chosen_droid]["AncientCode"] = True

    msg = f"Inside the Shield Manual you see firmware specs — rare, old ones. You try each of your droids, and you are fortunate that the only droid that has a matching code is {chosen_droid}. This droid needs to be assigned to the Shield for it to work."
    msg_shield(msg, turns_elapsed)

    # Add the event
    event_priority = 2
    task_package = add_turn_event(task_package, "shield", event_priority, item="ShieldManual", result="ancient_code_found", droid=chosen_droid)

    # Set the message inside the item - for display
    ancient_code = next((r for r in resources if r.get("name") == "AncientDroidCode"), None)
    ancient_code["msg"] = msg
    ancient_code["droidName"] = chosen_droid

    return resources, droids, shieldstate


def define_crystal_combination(resources, shieldstate, turns_elapsed):
    item_found = False
    for item in resources:
        if item.get("name") == "CrystalCombination":
            item["examined"] = True
            item["red"] = random.randint(1, 10)
            item["indigo"] = random.randint(1, 10)
            item["gold"] = random.randint(1, 10)
            msg = f"This professionally typed booklet describes the correct combination of crystals to make the shield operate effectively: {item['red']} red, {item['indigo']} indigo, and {item['gold']} gold crystals."
            item_found = True
            msg_shield(msg, turns_elapsed)

            # Add the event
            event_priority = 2
            task_package = add_turn_event(task_package, "shield", event_priority, item="CrystalCombination", result="combination_found", red=item["red"], indigo=item["indigo"], gold=item["gold"])
            break

    if not item_found:
        msg_shield(get_message("shield", "no_combo_found"), turns_elapsed, tone="warn")
        return resources, shieldstate
    
    return resources, shieldstate


def get_available_crystals(resources):
    available_crystals = {"red": 0, "indigo": 0, "gold": 0}
    for res in resources:
        if res.get("name") == "PowerSupply" and res.get("found"):
            crystal_store = res.get("CrystalStore")
            if crystal_store:
                available_crystals["red"] = crystal_store["red"]
                available_crystals["indigo"] = crystal_store["indigo"]
                available_crystals["gold"] = crystal_store["gold"]
    return available_crystals


def complete_towing_task(name, task_package, task_data=None):
    tasks = task_package["tasks"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    if not task_data:
        task_data = {}
    outcome = None

    task_id, task = get_task_by_worker(tasks, name)

    if not task:
        return_msg = get_message("error", "no_existing_task", name=name)
        return return_msg, task_package

    # Prefer task_data if present, but fall back to item_name for compatibility.
    task_data = task.get("task_data", {})
    droid_to_be_charged = task_data.get("droid_to_tow", task.get("item_name", ""))

    if not droid_to_be_charged or droid_to_be_charged not in droids:
        return_msg = get_message("charge", "tow_failed", name=name, droid_to_tow=droid_to_be_charged)
        return return_msg, task_package

    # The droid has now been physically returned to the PowerSupply area.
    # It may still be at 0%, but it no longer needs towing.
    droids[droid_to_be_charged]["needs_tow"] = False

    return_msg = get_message("charge", "tow_successful", name=name, droid_towed=droid_to_be_charged)

    msg_power(return_msg, turns_elapsed)

    # Add the event
    event_priority = 5
    task_package = add_turn_event(task_package, "tow", event_priority, name=name, droid_towed=droid_to_be_charged, result="completed")

    # The original player intent was "charge this droid",
    # so begin the charge automatically after towing succeeds.
    outcome, task_package = initiate_charge_task(droid_to_be_charged, task_package)

    if outcome != CommandOutcome.SUCCESS:
        msg_power(get_message("charge", "tow_complete_but_charge_failed", droid=droid_to_be_charged), turns_elapsed, tone="warn")

    return return_msg, task_package