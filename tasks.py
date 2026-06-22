# tasks.py

import random

from actions import start_next_queued_task_for_character
from commands import initiate_charge_task, clear_task_for_character
from command_utils import create_task, get_pronouns, get_task_by_worker, remove_task_by_id, remove_task_by_name, choose_vials_and_display_power_produced
from constants import (TASK_EATING, TASK_CHARGING, TASK_EXPLORING, TASK_PLANTING, TASK_EXAMINING, TASK_REAPING, TASK_MINING, TASK_ASSIGNED, TASK_REFUELING, TASK_TOWING_DROID,
                       RATION_PACKS, GROWTH_TURNS, YIELD_RANGE, CRYSTAL_RATIO, BASE_CRYSTAL_YIELD, TASK_LENGTH, INITIAL_SEED_STASH, REAP_SEED_FRACTION, SEED_PACKETS_USED)
from lore.lore_ingame import get_message
import lore.user_interface as ui_runtime
from lore.user_interface import (get_input, msg_plant, msg_explore, msg_resource, msg_power, msg_food, msg_shield, msg_mine, msg_crystal,
                                 msg_error, msg_warn, log_and_display)
from planting import update_food_amount, feed_human
from queuing import get_character_status, do_auto_charge, do_auto_feed
from resources import charge_droid, attempt_exploration, react_to_found_resource, add_or_get_discovered_item
from utils import set_shield_state, set_examine_needed_after_explore, save_config


def advance_tasks(task_package):
    completed = []
    awaiting_input = False

    tasks = task_package["tasks"]
    humans = task_package["humans"]
    turns_elapsed = task_package["counters"]["turns"]

    # Don't decrement the task counter here, just check for completed tasks
    for task_id, task in tasks.items():
        if task["duration"] <= 1:       # We stop at one here, because the counters get decremented at the end of the turn (in complete_turn())
            completed.append(task_id)

    for task_id in completed:
        task = tasks[task_id]
        name = task["name"]
        task_type = task["type"]
        item_name = task.get("item_name", "")

        is_examining = nothing_found = False
        completed_msg = ""
        item_found = ""

        if task_type == TASK_EATING:
            completed_msg, task_package = complete_feed_task(name, task_package)
            msg_food(completed_msg, turns_elapsed)
        elif task_type == TASK_CHARGING:
            completed_msg, task_package = complete_charge_task(name, task_package)
            msg_power(completed_msg, turns_elapsed)
        elif task_type == TASK_EXPLORING:
            completed_msg, is_examining, nothing_found, awaiting_input, task_package = complete_explore_task(name, task_package)
            item_found = task_package["item"]
            if awaiting_input:
                remove_task_by_id(task_id, task_package)
                return awaiting_input, task_package
            elif is_examining or nothing_found or (item_found == "FoodStore"):
                msg_resource(completed_msg, turns_elapsed)
            else:  # This will be an auto-feed or auto-charge
                if name in humans:
                    msg_food(completed_msg, turns_elapsed)
                else:
                    msg_power(completed_msg, turns_elapsed)
                log_and_display("", turns_elapsed, stamp=None)
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
                completed_msg, task_package = complete_assign_process_task(name, task_package)
                msg_crystal(completed_msg, turns_elapsed)
            elif item_name == "ShieldManual":
                completed_msg, task_package = complete_assign_shieldmanual_task(name, task_package)
                msg_shield(completed_msg, turns_elapsed)
            else:
                completed_msg = get_message("assign", "cannot_complete_assign_task")
                msg_warn(completed_msg, turns_elapsed)
        elif task_type == TASK_REFUELING:
            completed_msg, task_package = complete_refuel_task(name, task_package)
            msg_crystal(completed_msg, turns_elapsed)
        elif task_type == TASK_TOWING_DROID:
            completed_msg, task_package = complete_towing_task(name, task_package)
            msg_power(completed_msg, turns_elapsed)
        else:
            completed_msg = get_message("task", "unknown", name=name, task_type=task_type.lower())
            msg_error(completed_msg, turns_elapsed)

        # Remove the task
        remove_task_by_id(task_id, task_package)

        if not is_examining:
            awaiting_input, task_package = start_next_queued_task_for_character(name, task_package)

        # Need to exit the loop early if we are needing a response from the player
        if awaiting_input:
            return awaiting_input, task_package

    return awaiting_input, task_package


def complete_feed_task(name, task_package):
    # Do the feed task after waiting the set amount of time
    return_msg = ""
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    if name in humans:
        return_msg, task_package = feed_human(name, task_package)
        humans, droids = clear_task_for_character(name, "", humans, droids)
    elif name in droids:
        msg_power(get_message("feed_droid", "responses", droid_name=name), turns_elapsed)
    else:
        msg_food(get_message("error", "feed_invalid", person_name=name), turns_elapsed, tone="error")

    return return_msg, task_package


def complete_charge_task(name, task_package):
    return_msg = ""
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]

    # Now we can charge the droid
    if name in droids:
        return_msg, droids, resources = charge_droid(name, droids, resources, turns_elapsed)
    
    return return_msg, task_package


def complete_explore_task(name, task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    gamestate = task_package["gamestate"]
    shieldstate = task_package["shieldstate"]
    return_msg = ""
    is_examining = awaiting_input = nothing_found = False
        
    def set_task_length(task_type):
        low, high = TASK_LENGTH[task_type]
        return random.randint(low, high)
    
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

        # React to the newly found resourc
        resources, droids, shieldstate = react_to_found_resource(res_name, resources, droids, gamestate, shieldstate)

        # Is this a human or droid?
        is_human = name in humans
        pronouns = get_pronouns(name, is_human)
        task_package["item"] = res_name
        
        # Handle the post "find" tasks, excluding the examine
        if res_name == "FoodStore":
            return_msg = get_message("explore", "found_food", target=name, amount=RATION_PACKS, res_name=res_name)
            discovered["examinable"] = False
            humans, droids = clear_task_for_character(name, "", humans, droids) # Clear task if not examinable
        else:
            # If the character is hungry or low on charge, put a pause on the examine and feed or charge them
            state = get_character_status(name, humans, droids)
            if state in ("Hungry", "Starving", "Low", "Out"):
                is_examining = False
                task_package = set_examine_needed_after_explore(name, task_package)
                if is_human: 
                    return_msg, task_package = do_auto_feed(name, task_package)
                else: 
                    return_msg, task_package = do_auto_charge(name, task_package)
                return return_msg, is_examining, nothing_found, awaiting_input, task_package
            
            # They are okay with regards to food or charge, so continue to respond to what was found
            discovered["examinable"] = True

            if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
                ui_runtime.ACTIVE_UI.set_pending_question(
                    callback=handle_examine_answer,
                    context={
                        "task_package": task_package,
                        "character_name": name,
                        "item": discovered,
                        "item_name": res_name,
                        "is_human": is_human,
                        "is_examining": False
                    }
                )
            answer = get_input("input", "explore_found", turns_elapsed, target=name, res_name=res_name, pronoun=pronouns["p2"].lower())

            if answer and answer == ui_runtime.GUI_PENDING:
                awaiting_input = True
                return return_msg, is_examining, nothing_found, awaiting_input, task_package
            else:
                msg_warn(get_message("error", "no_CLI"), turns_elapsed)
    else:
        nothing_found =True
        is_human = name in humans
        pronouns = get_pronouns(name, is_human=is_human)
        if is_human: 
            has_have = "has" 
        else: 
            has_have = "have"
        return_msg = get_message("explore", "nothing_found", target=name, pronoun=pronouns["p1"].lower(), pronoun2=pronouns["p3"].lower(), has_have=has_have)
        humans, droids = clear_task_for_character(name, "", humans, droids)  # Clear the task if they found nothing

    return return_msg, is_examining, nothing_found, awaiting_input, task_package


# Process the response from the user as to whether or not they should examine an item that was just found
def handle_examine_answer(answer, context):
    task_package = context["task_package"]
    name = context["character_name"]
    item = context["item"]
    item_name = context["item_name"]
    is_human = context["is_human"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]

    if answer and answer.lower() in ("y", "yes"):
        return_msg, is_examining, task_package = examine_after_explore(task_package, name, item, item_name, is_human, False)
        msg_resource(return_msg, turns_elapsed)

        # If they are not now engaged in a new examine task,
        # allow them to pull the next queued task immediately.
        if not is_examining:                
            awaiting_input, task_package = start_next_queued_task_for_character(name, task_package)
            if awaiting_input:
                return task_package

    else:
        humans = task_package["humans"]
        droids = task_package["droids"]

        return_msg = get_message("explore", "not_examined", target=name, res_name=item["name"])
        msg_resource(return_msg, turns_elapsed)

        humans, droids = clear_task_for_character(name, "", humans, droids)
        task_package["humans"] = humans
        task_package["droids"] = droids

        # Remove the existing explore task
        remove_task_by_name(name, task_package)
  
        awaiting_input, task_package = start_next_queued_task_for_character(name, task_package)
        if awaiting_input:
            return task_package

    # The question is now resolved, so the suspended turn may continue.
    task_package["gamestate"]["turn_suspended"] = False
    save_config(task_package)

    return task_package


def examine_after_explore(task_package, character_name, item, item_name, is_human, is_examining):
    # Handler for what to do after an explore has completed
    tasks = task_package["tasks"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    
    def set_task_length(task_type):
        low, high = TASK_LENGTH[task_type]
        return random.randint(low, high)

    if item.get("examine_turns", 0) > 0:
        task_type = TASK_EXAMINING
        duration = 0
                    
        # Do human or droid specific things
        if is_human:
            duration = item["examine_turns"] + set_task_length("examine_human")
            task_now_doing = humans[character_name]["task"]
            humans[character_name]["generated"] = True
        else:
            duration = item["examine_turns"] + set_task_length("examine_droid")
            task_now_doing = droids[character_name]["task"]
            droids[character_name]["generated"] = True

        # Create the Examine task
        return_msg, task_package = create_task(character_name, task_type, duration, task_package)
        is_examining = True
    else:
        # Instant examine
        new_msg = item["msg"].format(name=character_name, 
                R=item.get("red", ""), I=item.get("indigo", ""), G=item.get("gold", ""),
                A=item.get("apple",""), C=item.get("cabbage",""), P=item.get("potato",""), 
                amount=item.get("amount", ""))
        formatted_msg = f"{item_name}: " + new_msg
        return_msg = formatted_msg
        item["examined"] = True
        item["msg"] = new_msg
            
        humans, droids = clear_task_for_character(character_name, "", humans, droids) # Clear the task if instant examine
                    
    return return_msg, is_examining, task_package


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
    total_seeds_before = stash.get('apple', 0) + stash.get('cabbage', 0) + stash.get('potato', 0)

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

    # Clear the task_data in the config file
    task_data = {}

    # Now check how many seeds we have and warn if low (below 20% of the initial stash)
    total_seeds_after = stash.get('apple', 0) + stash.get('cabbage', 0) + stash.get('potato', 0)
    if total_seeds_after < INITIAL_SEED_STASH * 0.2 and total_seeds_before >= INITIAL_SEED_STASH * 0.2:
        msg_plant(get_message("plant", "low_seeds_warning"), turns_elapsed, low_count=INITIAL_SEED_STASH * 0.2, tone="warn")

    return return_msg, task_package


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
    turns_elapsed = task_package["counters"]["turns"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    crops = task_package["crops"]
    return_msg = ""
    appleseeds = cabbageseeds = potatoseeds = 0

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
            if ctype == "apple":
                appleseeds += int(REAP_SEED_FRACTION * SEED_PACKETS_USED["apple"])
            elif ctype == "cabbage":
                cabbageseeds += int(REAP_SEED_FRACTION * SEED_PACKETS_USED["cabbage"])
            elif ctype == "potato":
                potatoseeds += int(REAP_SEED_FRACTION * SEED_PACKETS_USED["potato"])


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

    # Now update the seeds, generated by reaping
    stash = next((r for r in resources if r["name"] == "SeedStash"), None)
    if not stash:
        return_msg = get_message("reap", "no_seedstash")
        return return_msg, task_package

    seed_parts = []
    if appleseeds > 0:
        stash["apple"] += appleseeds
        seed_parts.append(f"{appleseeds} apple seeds")
    if cabbageseeds > 0:
        stash["cabbage"] += cabbageseeds
        seed_parts.append(f"{cabbageseeds} cabbage seeds")
    if potatoseeds > 0:
        stash["potato"] += potatoseeds
        seed_parts.append(f"{potatoseeds} potato seeds")

    seedsmsg = ""
    if seed_parts:
        if len(seed_parts) == 1:
            seedsmsg = f" You have retrieved {seed_parts[0]} from the reaping."
        elif len(seed_parts) == 2:
            seedsmsg = f" You have retrieved {seed_parts[0]} and {seed_parts[1]} from the reaping."
        else:
            seedsmsg = f" You have retrieved {seed_parts[0]}, {seed_parts[1]} and {seed_parts[2]} from the reaping."

    return_msg = get_message("reap", "harvest_complete", target=name, items=joined_msg, seedsmsg=seedsmsg)

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

    # Add to the 'total_found' tally, as later these might be processed for various reasons (power, shield, other?) 
    crystal_store["total_found"]["red"] += red
    crystal_store["total_found"]["indigo"] += indigo
    crystal_store["total_found"]["gold"] += gold

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

    crystal_store["processed"]["red"] += red
    crystal_store["processed"]["indigo"] += indigo
    crystal_store["processed"]["gold"] += gold

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
    else:
       return_msg = get_message("shield", "manual_not_found", name=name)

    humans, droids = clear_task_for_character(name, "ShieldManual", humans, droids)   # Clear the task

    return return_msg, task_package


def complete_refuel_task(name, task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]

    amount_only = True

    return_msg, total_power, task_package, red, indigo, gold = choose_vials_and_display_power_produced(name, task_package, amount_only=amount_only)

    if return_msg != "" and total_power == 0:
        humans, droids = clear_task_for_character(name, "", humans, droids)
        return return_msg, task_package

    return_msg = get_message("refuel", "completed", name=name, power=total_power)

    humans, droids = clear_task_for_character(name, "", humans, droids)

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
            break

    if not item_found:
        msg_shield(get_message("shield", "no_combo_found"), turns_elapsed, tone="warn")
        return resources, shieldstate
    
    # Count available crystals (assuming you track this way)
    available_crystals = get_available_crystals(resources)
    if item["red"] > available_crystals.get("red",0) or item["indigo"] > available_crystals.get("indigo",0) or item["gold"] > available_crystals.get("gold",0):
        msg_shield(get_message("shield", "not_enough_crystals", 
                                    need_R=item["red"], need_I=item["indigo"], need_G=item["gold"], 
                                    have_R=available_crystals.get("red",0), have_I=available_crystals.get("indigo",0), have_G=available_crystals.get("gold",0)),
                                    turns_elapsed, tone="error")

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


def complete_towing_task(name, task_package):
    tasks = task_package["tasks"]
    return_msg = ""

    task_id, task = get_task_by_worker(tasks, name)
    droid_to_be_charged = task["item_name"]

    task_package = initiate_charge_task(droid_to_be_charged, task_package)
    return_msg = get_message("charge", "tow_successful", name=name, droid_towed=droid_to_be_charged)

    return return_msg, task_package