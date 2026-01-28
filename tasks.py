# tasks.py

import random

from commands import handle_immediate_or_queued_task
from command_utils import create_task
from constants import (TASK_EATING, TASK_CHARGING, TASK_EXPLORING, TASK_PLANTING, TASK_EXAMINING, TASK_REAPING, TASK_MINING, TASK_ASSIGNED, TASK_REFUELING,
                       RATION_PACKS, GROWTH_TURNS, YIELD_RANGE, CRYSTAL_RATIO, BASE_CRYSTAL_YIELD, POWER_PER_RED, POWER_PER_INDIGO, POWER_PER_GOLD)
from lore.lore_ingame import get_message
from lore.user_interface import log_and_display, get_input
from planting import update_food_amount, feed_human
from queuing import get_next_task_from_queue_if_any
from resources import charge_droid, attempt_exploration, react_to_found_resource, add_or_get_discovered_item
from utils import get_pronouns, set_shield_state, clear_task_for_character, get_task_by_worker


def advance_tasks(task_package):
    completed = []

    tasks = task_package["tasks"]
    turns_elapsed = task_package["turns_elapsed"]

    for task_id, task in tasks.items():
        task["duration"] -= 1
        if task["duration"] <= 0:
            completed.append(task_id)

    for task_id in completed:
        task = tasks[task_id]
        name = task["name"]
        task_type = task["type"]
        item_name = task.get("item_name", "")

        is_examining = False
        completed_msg = ""

        if task_type == TASK_EATING:
            completed_msg, task_package = complete_feed_task(name, task_package)
        elif task_type == TASK_CHARGING:
            completed_msg, task_package = complete_charge_task(name, task_package)
        elif task_type == TASK_EXPLORING:
            completed_msg, is_examining, task_package = complete_explore_task(name, task_package)
        elif task_type == TASK_PLANTING:
            completed_msg, task_package = complete_plant_task(name, task_package)
        elif task_type == TASK_EXAMINING:
            completed_msg, task_package = complete_examine_task(name, task_package)
        elif task_type == TASK_REAPING:
            completed_msg, task_package = complete_reap_task(name, task_package)
        elif task_type == TASK_MINING:
            completed_msg, task_package = complete_mine_task(name, task_package)
        elif task_type == TASK_ASSIGNED:
            if item_name == "CrystalProcessor":
                completed_msg, task_package = complete_assign_process_task(name, task_package)
            elif item_name == "ShieldManual":
                completed_msg, task_package = complete_assign_shieldmanual_task(name, task_package)
            else:
                completed_msg = get_message("assign", "cannot_complete_assign_task")
        elif task_type == TASK_REFUELING:
            completed_msg, task_package = complete_refuel_task(name, task_package)
        else:
            completed_msg = get_message("task", "unknown", name=name, task_type=task_type.lower())

        # Remove task from registry
        if task_id in tasks:
            del tasks[task_id]

        # Now try to pull from the queue (unless currently examining)
        if not is_examining:
            next_action, character, task_package = get_next_task_from_queue_if_any(name, completed_msg, task_package)

            # Attempt to initiate queued task (if any)
            if next_action:
                valid_command, task_package = handle_immediate_or_queued_task(next_action, character, task_package)
                if not valid_command:
                    log_and_display(get_message("error", "invalid_command_from_function", action=next_action), turns_elapsed)

    return task_package


def complete_feed_task(name, task_package):
    # Do the feed task after waiting the set amount of time
    return_msg = ""
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["turns_elapsed"]

    if name in humans:
        return_msg, task_package = feed_human(name, task_package)
        humans, droids = clear_task_for_character(name, "", humans, droids)
    elif name in droids:
        log_and_display(get_message("feed_droid", "responses", droid_name=name), turns_elapsed)
    else:
        log_and_display(get_message("error", "feed_invalid", person_name=name), turns_elapsed)

    return return_msg, task_package


def complete_charge_task(name, task_package):
    return_msg = ""
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]

    # Now we can charge the droid
    if name in droids:
        return_msg, droids, resources = charge_droid(name, droids, resources)
        humans, droids = clear_task_for_character(name, "", humans, droids)
    return return_msg, task_package


def complete_explore_task(name, task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    tasks = task_package["tasks"]
    task_number = task_package["task_number"]
    turns_elapsed = task_package["turns_elapsed"]
    gamestate = task_package["gamestate"]
    shieldstate = task_package["shieldstate"]
    return_msg = ""
    task_created_msg = ""
    is_examining = False
    
    # Resolve the end of an explore task for `character`.
    discovered_name, task_package = attempt_exploration(task_package)

    if discovered_name:
        if isinstance(discovered_name, dict):
            discovered_name = discovered_name.get("name", None)
        elif not isinstance(discovered_name, str):
            log_and_display(get_message("explore", "unexpected_type", name=discovered_name), turns_elapsed)
            discovered_name = None

        # Ensure the discovered item exists in the resources list
        discovered, resources = add_or_get_discovered_item(resources, discovered_name)
        res_name = discovered["name"]

        # React to the newly found resourc
        resources, droids, shieldstate = react_to_found_resource(res_name, resources, droids, gamestate, shieldstate)

        # Is this a human or droid?
        is_human = name in humans
        pronouns = get_pronouns(name, is_human)
        
        if res_name == "FoodStore":
            return_msg = get_message("explore", "found_food", target=name, amount=RATION_PACKS, res_name=res_name)
            discovered["examinable"] = False
            humans, droids = clear_task_for_character(name, "", humans, droids) # Clear task if not examinable
        else:
            discovered["examinable"] = True
            answer = get_input("input", "explore_found", turns_elapsed, target=name, res_name=res_name, pronoun=pronouns["p2"].lower())

            if answer == 'y':
                if discovered.get("examine_turns", 0) > 0:
                    # Remove the existing explore task
                    if is_human:
                        task_now_doing = humans[name]["task"]
                    else:
                        task_now_doing = droids[name]["task"]
                    if task_now_doing in tasks:
                        del tasks[task_now_doing]

                    # Create examine task
                    is_human = name in humans
                    task_type = TASK_EXAMINING
                    task_created_msg, tasks, task_number, humans, droids = create_task(tasks, task_number, task_type, humans, droids, name, is_human,
                                                     discovered["examine_turns"], turns_elapsed, item_name=discovered["name"])
                    
                    # We do a log and display here, because this is where we transition to an examine
                    is_examining = True
                    log_and_display(f"{return_msg} {task_created_msg}", turns_elapsed)
                else:
                    # Instant examine
                    new_msg = discovered["msg"].format(name=name, 
                            R=discovered.get("red", ""), I=discovered.get("indigo", ""), G=discovered.get("gold", ""),
                            A=discovered.get("apple",""), C=discovered.get("cabbage",""), P=discovered.get("potato",""), 
                            amount=discovered.get("amount", ""))
                    formatted_msg = f"{discovered_name}: " + new_msg
                    return_msg = formatted_msg
                    discovered["examined"] = True
                    discovered["msg"] = new_msg
                    humans, droids = clear_task_for_character(name, "", humans, droids) # Clear the task if instant examine
            else:
                return_msg = get_message("explore", "not_examined", target=name, res_name=discovered["name"])
                humans, droids = clear_task_for_character(name, "", humans, droids) # Clear the task if they are not examining
    else:
        return_msg = get_message("explore", "nothing_found", target=name)
        humans, droids = clear_task_for_character(name, "", humans, droids)  # Clear the task if they found nothing

    return return_msg, is_examining, task_package


def complete_plant_task(name, task_package):
    task_data = task_package["task_data"]
    resources = task_package["resources"]
    crops = task_package["crops"]
    crop_number = task_package["crop_number"]
    turns_elapsed = task_package["turns_elapsed"]
    return_msg = ""

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

    total_planted = 0

    for order in orders:
        crop_type = order["crop"]
        beds_requested = order["beds"]

        for bed_id in beds_requested:

            # 🔎 Find the actual bed object by ID
            bed = next((b for b in hydro["beds"] if b == bed_id), None)

            if bed is None:
                log_and_display(get_message("plant", "invalid_bed", bed=bed_id), turns_elapsed)
                continue

            # 🚫 Bed not available (for now we assume bed is reserved properly - so we don't check for that)
            if bed["occupied"]:
                log_and_display(get_message("plant", "bed_occupied", bed=bed_id), turns_elapsed)
                continue

            # 🌱 Seed check
            if stash.get(crop_type, 0) <= 0:
                log_and_display(get_message("plant", "not_enough_seeds", crop=crop_type), turns_elapsed)
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

            # 🌿 Per-crop feedback
            log_and_display(get_message("plant", "crop_started", target=worker, crop=crop_type, bed=bed_id), turns_elapsed)

    # 📢 Summary message
    if total_planted == 0:
        return_msg = get_message("plant", "nothing_planted", target=worker)
    else:
        return_msg = get_message("plant", "task_complete", target=worker, number=total_planted)

    # Clear the task
    humans, droids = clear_task_for_character(worker, "", humans, droids)

    return return_msg, task_package


def complete_examine_task(name, task_package):
    return_msg = ""
    tasks = task_package["tasks"]
    resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]
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
                A=item.get("apple",""), C=item.get("cabbage",""), P=item.get("potato",""),
                amount=item.get("amount", ""))
        formatted_msg = f"{name} has finished examining **{item_name}**: " + new_msg

        return_msg = formatted_msg
        item["msg"] = new_msg

    # Mark examined
    item["examined"] = True

    # Save back into list
    for r in resources:
        if r["name"] == item_name:
            r.update(item)

    # Clear the task
    humans, droids = clear_task_for_character(name, "", humans, droids)

    return return_msg, task_package


def complete_reap_task(name, task_package):
    resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    crops = task_package["crops"]
    return_msg = ""

    hydro = next((r for r in resources if r["name"] == "HydroponicsRoom"), None)

    harvested_total = 0
    harvested_by_type = {"apple": 0, "cabbage": 0, "potato": 0}

    # --- Prepare to collect results ---
    harvest_summary = {}  # e.g. {"apple": 180, "cabbage": 14}

    # --- Process each mature crop ---
    for cid in list(crops.keys()):
        crop = crops[cid]

        if crop["mature"]:
            ctype = crop["crop_type"]

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
    harvest_parts = []
    for ctype, total_amount in harvest_summary.items():
        if total_amount == 1:
            harvest_parts.append(f"{total_amount} {ctype}")
        else:
            if ctype != "potato":
                harvest_parts.append(f"{total_amount} {ctype}s")
            else:
                harvest_parts.append(f"{total_amount} {ctype}es")

    joined_msg = ", ".join(harvest_parts)

    return_msg = get_message("reap", "harvest_complete", target=name, items=joined_msg)

    # Clear the task
    humans, droids = clear_task_for_character(name, "", humans, droids)

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

    return_msg = get_message("mine", "completed", name=name, red=red, indigo=indigo, gold=gold)
    
    # Clear the task
    humans, droids = clear_task_for_character(name, "", humans, droids)

    return return_msg, task_package


def complete_assign_process_task(name, task_package):
    # Converts selected quantities of raw crystals into vials, preserving unprocessed ones.
    resources = task_package["resources"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    item_name = task_package["item"]
    task_data = task_package["task_data"]
    return_msg = ""

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

    total_units = red + indigo + gold
    return_msg = get_message("assign", "process_completed", name=name, item=item_name, total_units=total_units)

    # Clear the task and assignment
    humans, droids = clear_task_for_character(name, item_name, humans, droids)

    return return_msg, task_data


def complete_assign_shieldmanual_task(name, task_package):
    resources = task_package["resources"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    return_msg = ""

    # 1. Check for DecodeKey in resources
    decode_key = next((r for r in resources if r["name"] == "DecodeKey"), None)
    shield_manual = next((r for r in resources if r["name"] == "ShieldManual"), None)

    if not decode_key:
        return_msg = get_message("shield", "no_decode", name=name)
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
    else:
       return_msg = get_message("shield", "manual_not_found", name=name)

    humans, droids = clear_task_for_character(name, "ShieldManual", humans, droids)   # Clear the task

    return return_msg, task_package


def complete_refuel_task(name, task_package):
    resources = task_package["resources"]
    return_msg = ""

    power_supply = next((r for r in resources if r.get("name") == "PowerSupply"), None)
    if not power_supply:
        return_msg = get_message("refuel", "no_power_supply")
        humans, droids = clear_task_for_character(name, "", humans, droids)  # Clear the task
        return return_msg, task_package

    vial_store = power_supply.get("VialStore", {})
    if not vial_store or all(v == 0 for v in vial_store.values()):
        return_msg = get_message("refuel", "no_vials_fail", name=name)
        humans, droids = clear_task_for_character(name, "", humans, droids)  # Clear the task
        return return_msg, task_package

    red = vial_store.get("red", 0)
    indigo = vial_store.get("indigo", 0)
    gold = vial_store.get("gold", 0)

    total_power = (
        red * POWER_PER_RED +
        indigo * POWER_PER_INDIGO +
        gold * POWER_PER_GOLD
    )

    # Apply
    power_supply["amount"] += total_power
    vial_store["red"] = 0
    vial_store["indigo"] = 0
    vial_store["gold"] = 0

    return_msg = get_message("refuel", "completed", name=name, power=total_power)
    humans, droids = clear_task_for_character(name, "", humans, droids)  # Clear the task

    return return_msg, task_package


def choose_droid_with_ancient_code(resources, droids, shieldstate, turns_elapsed):
    eligible_droids = list(droids.keys())
    if not eligible_droids:
        log_and_display(get_message("shield", "no_droid_with_code"), turns_elapsed)
        return resources, droids, shieldstate

    chosen_droid = random.choice(eligible_droids)
    droids[chosen_droid]["AncientCode"] = True

    msg = f"Inside the Shield Manual you see firmware specs — rare, old ones. You try each of your droids, and you are fortunate that the only droid that has a matching code is {chosen_droid}. This droid needs to be assigned to the Shield for it to work."
    log_and_display(msg, turns_elapsed)

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
            log_and_display(msg, turns_elapsed)
            break

    if not item_found:
        log_and_display(get_message("shield", "no_combo_found"), turns_elapsed)
        return resources, shieldstate
    
    # Count available crystals (assuming you track this way)
    available_crystals = get_available_crystals(resources)
    if item["red"] > available_crystals.get("red",0) or item["indigo"] > available_crystals.get("indigo",0) or item["gold"] > available_crystals.get("gold",0):
        log_and_display(get_message("shield", "not_enough_crystals", 
                                    need_R=item["red"], need_I=item["indigo"], need_G=item["gold"], 
                                    have_R=available_crystals.get("red",0), have_I=available_crystals.get("indigo",0), have_G=available_crystals.get("gold",0)), turns_elapsed)

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