# status.py

from constants import (ENDGAME_REASONS, FULL_CHARGE, HUNGER, NUM_HUMANS, NUM_DROIDS, LOW_CHARGE_FLAG, IDLE_CHARGE_USAGE, COMMAND_MAP,
                      TASK_ASSIGNED, TASK_EXAMINING, TASK_EATING, TASK_CHARGING, TASK_REAPING, TASK_PLANTING, ONE_DAY_HUNGRY)
import lore.user_interface as ui_runtime
from lore.user_interface import (log_and_display, get_input, msg_food, msg_power, msg_info, msg_plant,
                                 msg_error, msg_info, msg_crystal, msg_resource, msg_shield, DOMAIN_EMOJI)
from lore.lore_ingame import get_message

def count_resource_by_category(resources, category1=0, category2=0):
    sub_list = []
    count = 0
    for item in resources:
        if not category2 and item["category"] == category1:
            sub_list.append(item)
            count += 1
        elif item["category"] == category1 or item["category"] == category2:
            sub_list.append(item)
            count += 1
    return sub_list, count


# Text for the Outpost state panel of the GUI
def get_state_panel_text(task_package):
    return (
        get_humans_panel_text(task_package)
        + "\n\n"
        + get_droids_panel_text(task_package)
        + "\n\n"
        + get_resources_panel_text(task_package)
        + "\n\n"
        + get_crops_panel_text(task_package)
        + "\n\n"
        + get_shield_panel_text(task_package)
    )

# GUI function for humans
def get_humans_panel_text(task_package):
    humans = task_package.get("humans", {})
    lines = ["HUMANS"]
    for name, h in humans.items():
        state = h.get("state", "Unknown")
        hunger = int(h.get("hunger", 0)/(ONE_DAY_HUNGRY/10))
        task_and_queue = get_character_task_and_queue(name, task_package)
        lines.append(f"{name:<7} | Hunger: {hunger} ({state}) | {task_and_queue}")
    return "\n".join(lines)


# GUI function for droids
def get_droids_panel_text(task_package):
    droids = task_package.get("droids", {})
    lines = ["DROIDS"]
    for name, d in droids.items():
        charge = int(d.get("charge", 0)//(FULL_CHARGE/100))
        task_and_queue = get_character_task_and_queue(name, task_package)
        lines.append(f"{name:<7} | Charge: {charge}% | {task_and_queue}")
    return "\n".join(lines)


def get_character_task_and_queue(name, task_package):
    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    turns_to_complete = task_str = queue_str = ""

    if name in humans or name in droids:
        task = get_task_data(tasks, name)
        if task:
            plural = "s" if task["duration"] != 1 else ""
            turns_to_complete = f"({task["duration"]} turn{plural})"
        else:
            turns_to_complete = ""

        if name in humans:
            task_name = humans[name]["task"]
            task_item = humans[name]["item"]
            queue = humans[name]["queue"]
            if not task_name:
                task_str = "--Idle--"
        else:
            task_name = droids[name]["task"]
            task_item = droids[name]["item"]
            queue = droids[name]["queue"]
            if not task_name:
                task_str = "--Unutilised--"

        if task_name:
            command_keyword = COMMAND_MAP.get(task_name, "action")
            emoji = DOMAIN_EMOJI.get(command_keyword, "")
            if task_name in (TASK_ASSIGNED, TASK_EXAMINING):
                task_str = emoji + task_name + f": {task_item} {turns_to_complete}"
            else:
                task_str = emoji + task_name + f": {turns_to_complete}"

        queue_str = ""
        queued_tasks = []
        for slot in ["1", "2", "3"]:
            queue_task = queue[slot]["task"]
            if queue_task:
                command_keyword = COMMAND_MAP.get(queue_task, "action")
                emoji = DOMAIN_EMOJI.get(command_keyword, "⛔ ")
                if emoji:
                    queued_tasks.append(emoji)
        if queued_tasks:
            queue_str = f" | Queued: {','.join(queued_tasks)}"
    
    return task_str + queue_str


def get_task_data(tasks, name):
    # Returns (task_id, task_data) for the active task assigned to worker_name, or (None, None) if not found.
    for tid, task in tasks.items():
        if task.get("name") == name:
            return task
    return None


# GUI function for crops
def get_crops_panel_text(task_package):
    crops = task_package.get("crops", {})
    gamestate = task_package.get("gamestate", {})
    lines = ["CROPS"]

    if gamestate:
        if gamestate.get("plant", False):
            planting_enabled = "*Planting is enabled*"
        else:
            planting_enabled = "(cannot plant yet)"
    else:
        planting_enabled = "--Gamestate configuration error (planting)--"

    if not crops:
        lines.append("No crops growing  " + planting_enabled)
    else:
        for _, crop in crops.items():
            crop_type = crop.get("crop_type", "Unknown").capitalize()
            worker = crop.get("worker", "Unknown")
            turns_remaining = crop.get("turns_remaining", 0)
            lines.append(f"{crop_type:<7} | {worker:<7} | {turns_remaining} turns")
    return "\n".join(lines)


def get_resources_panel_text(task_package):
    resources = task_package.get("resources", [])
    gamestate = task_package.get("gamestate", {})
    lines = ["RESOURCES"]
    
    # Resource Summary
    food = get_resource_amount("FoodStore", resources)
    power = get_resource_amount("PowerSupply", resources)
    seeds = get_resource_amount("SeedStash", resources)
    crystals = get_resource_amount("CrystalStore", resources)
    vials = get_resource_amount("VialStore", resources)

    if not resources:
        lines.append("*No resources found yet*")
    else:
        lines.append(f"Sustainment:   Power - {power}\tFood - {food}\tSeeds - {seeds}")

    if gamestate:
        if gamestate.get("mine", False):
            mining_enabled = "*Mining is enabled*"
        else:
            mining_enabled = "(Mining: cannot mine yet)"
    else:
        mining_enabled = "--Gamestate configuration error (mining)--"
    
    if not crystals and resources:
        lines.append(f"No crystals found yet  \t{mining_enabled}")
    elif crystals:
        lines.append(f"Crystals:\tCurrent - {crystals}\tVials - {vials}\t{mining_enabled}")
 
    # Discovered Resources
    discovered = get_discovered_resources(resources)
    if discovered:        
        important, num_important = count_resource_by_category(resources, category1="essential", category2="chain")
        useful, num_useful = count_resource_by_category(resources, category1="replacement", category2="novelty")
        junk, num_junk = count_resource_by_category(resources, category1="junk")

        lines.append(f"Resources:     Important {num_important}, Useful {num_useful}, Junk {num_junk}")
        crystal_processor = next((r for r in resources if r.get("name") == "CrystalProcessor"), None)
        meal_maker = next((r for r in resources if r.get("name") == "MealMaker"), None)
        old_terminal = next((r for r in resources if r.get("name") == "OldTerminal"), None)
        cloaking_shield = next((r for r in resources if r.get("name") == "CloakingShield"), None)

        assignables = []
        if crystal_processor:
            assignables.append("CrystalProcessor")
        if meal_maker:
            assignables.append("MealMaker")
        if old_terminal:
            assignables.append("OldTerminal")
        if cloaking_shield:
            assignables.append("CloakingShield")

        if assignables:
            lines.append(f"Assignable items:  {', '.join(assignables)}")

    return "\n".join(lines)


def get_resource_amount(name, resources):
    for res in resources:
        if res.get("name") == "FoodStore" and res.get("found") and name == "FoodStore" :
            total_food = res.get("rationPack") + res.get("apple") + res.get("cabbage") + res.get("potato") +\
                            res.get("soup") + res.get("smoothie") + res.get("stirFry")
            return total_food
        elif res.get("name") == "SeedStash" and name == "SeedStash" and res.get("found"):
            seeds_amount = res.get("apple") + res.get("cabbage") + res.get("potato")
            return seeds_amount
        elif res.get("name") == "PowerSupply" and res.get("found") and name == "PowerSupply":
            power_amount = res.get("amount")
            return power_amount
        elif res.get("name") == "PowerSupply" and res.get("found") and name == "CrystalStore":
            crystal_store = res.get("CrystalStore", "")
            total_crystals = 0
            if crystal_store:
                total_crystals = crystal_store["red"] + crystal_store["indigo"] + crystal_store["gold"]
            return total_crystals
        elif res.get("name") == "PowerSupply" and res.get("found") and name == "VialStore":
            vial_store = res.get("VialStore", "")
            total_vials = 0
            if vial_store:
                total_vials = vial_store["red"] + vial_store["indigo"] + vial_store["gold"]
            return total_vials
        elif res.get("name") == name and res.get("found"):
            return res.get("amount", "None")
    return 0


def get_discovered_resources(resources):
    return [
        res["name"]
        for res in resources
        if res.get("found", False)
    ]

    
def get_shield_panel_text(task_package):
    resources = task_package.get("resources", [])
    shieldstate = task_package.get("shieldstate", {})
    lines = ["SHIELD"]

    cloaking_shield = next((r for r in resources if r.get("name") == "CloakingShield" and r.get("found")), None)
    shield_manual = next((r for r in resources if r.get("name") == "ShieldManual" and r.get("found")), None)
    decode_key = next((r for r in resources if r.get("name") == "DecodeKey" and r.get("found")), None)
    crystal_combination = next((r for r in resources if r.get("name") == "CrystalCombination" and r.get("found")), None)
    droid_code = next((r for r in resources if r.get("name") == "AncientDroidCode" and r.get("found")), None)

    # Hide shield panel entirely until the shield itself is found
    if not cloaking_shield:
        return ""

    shield_status = "Active" if shieldstate.get("shield_active", False) else "Inactive"
    lines.append(f"Status: {shield_status}")

    items = ["CloakingShield"]

    if shield_manual:
        if shield_manual.get("decoded") and decode_key:
            items.append("ShieldManual(decoded)")
        else:
            items.append("ShieldManual(unreadable)")

    if decode_key:
        items.append("DecodeKey")

    if crystal_combination:
        red = crystal_combination.get("red", 0)
        indigo = crystal_combination.get("indigo", 0)
        gold = crystal_combination.get("gold", 0)
        items.append(f"ShieldCombination(R:{red}, I:{indigo}, G:{gold})")

    if droid_code:
        ancient_droid_name = droid_code.get("droidName", "null")
        if ancient_droid_name != "null":
            items.append(f"DroidCode({ancient_droid_name})")
        else:
            items.append("DroidCode(not known)")

    lines.append("Shield Items: " + ", ".join(items))
    return "\n".join(lines)


def handle_list_command(qualifier, task_package):
    # List lots of things (eventually)
    turns_elapsed = task_package["counters"]["turns"]
    can_be_listed = "'food', 'power', 'resources', 'crystals'"

    # Step 1: Get targets (either from qualifier or prompt)
    if not qualifier:
        if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
            ui_runtime.ACTIVE_UI.set_pending_question(
                callback=resume_list_command,
                context={
                    "task_package": task_package,
                }
            )
        answer = get_input("input", "list", turns_elapsed, can_be_listed=can_be_listed)

        if answer == ui_runtime.GUI_PENDING:
            return None
    
    else:
        resume_list_command(qualifier, {"task_package": task_package,})

    return None


def resume_list_command(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]
    to_be_listed = answer

    # List food and food-related systems
    if to_be_listed == "food":
        list_food(task_package)
    elif to_be_listed == "power":
        list_power(task_package)
    elif to_be_listed == "resources":
        list_resources(task_package)
    elif to_be_listed == "crystals":
        list_crystals(task_package)
    elif to_be_listed != "":
        # Invalid command
        msg_error(get_message("error", "list_fail"), turns_elapsed)

    return


def list_food(task_package):
    # List food and food-related systems
    resources = task_package["resources"]
    humans = task_package["humans"]
    crops = task_package["crops"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]

    # --- FOOD STORE ---
    food_store = next((r for r in resources if r.get("name") == "FoodStore"), None)
    if not food_store:
        msg_food(" FOOD STATUS:", turns_elapsed)
        msg_food("  No FoodStore found.", turns_elapsed)
        return

    msg_food(" FOOD STATUS:", turns_elapsed)

    msg_food(f"  Ration Packs: {food_store.get('rationPack', 0)}", turns_elapsed)
    msg_food(
        f"  Apples: {food_store.get('apple', 0)} | "
        f"Cabbages: {food_store.get('cabbage', 0)} | "
        f"Potatoes: {food_store.get('potato', 0)}",
        turns_elapsed
    )
    msg_food(
        f"  Soup: {food_store.get('soup', 0)} | "
        f"Smoothies: {food_store.get('smoothie', 0)} | "
        f"Stir Fry: {food_store.get('stirFry', 0)}",
        turns_elapsed
    )

    # --- HUMAN HUNGER ---
    hungry = []
    starving = []
    near_death = []
    deceased = []

    for name, h in humans.items():
        hunger = h.get("hunger", 0)
        if hunger >= HUNGER["Deceased"][0]:
            deceased.append(name)
        elif hunger >= HUNGER["Near Death"][0]:
            near_death.append(name)
        elif hunger >= HUNGER["Starving"][0]:
            starving.append(name)
        elif hunger >= HUNGER["Hungry"][0]:
            hungry.append(name)

    msg_food("", turns_elapsed)
    msg_food(" HUMAN HUNGER:", turns_elapsed)

    if not hungry and not starving and not near_death:
        msg_food("  Everyone is currently fed and happy. Well, fed, anyway.", turns_elapsed)
    else:
        if hungry:
            msg_food(f"  Hungry: {', '.join(hungry)}", turns_elapsed)
        if starving:
            msg_food(f"  Starving: {', '.join(starving)}", turns_elapsed, tone="warn")
        if near_death:
            msg_food(f"  Near Death: {', '.join(near_death)}", turns_elapsed, tone="warn")
        if deceased:
            msg_food(f"  Dead 💀: {', '.join(deceased)}", turns_elapsed, tone="error")

    # --- CROPS GROWING ---
    log_and_display("", turns_elapsed, stamp=None)
    msg_plant(" CROPS GROWING:", turns_elapsed)

    if not crops:
        msg_plant("  No crops are currently growing.", turns_elapsed)
    else:
        for crop in crops.values():
            bed_id = crop["bed_id"]["id"]
            crop_type = crop["crop_type"]
            turns = crop["turns_remaining"]
            msg_plant(f"  Bed #{bed_id}: {crop_type} ({turns} turns remaining)", turns_elapsed)

    # --- SEEDS AVAILABLE ---
    log_and_display("", turns_elapsed, stamp=None)
    msg_plant(" SEEDS:", turns_elapsed)

    seeds = next((r for r in resources if r.get("name") == "SeedStash"), None)
    if seeds:
        msg_plant(
            f"  Apple: {seeds.get('apple', 0)} | "
            f"Cabbage: {seeds.get('cabbage', 0)} | "
            f"Potato: {seeds.get('potato', 0)}",
            turns_elapsed
        )
    else:
        msg_plant("  No seeds have been found so far.", turns_elapsed)

    # --- MATURE CROPS ---
    msg_plant("", turns_elapsed)
    msg_plant(" MATURE CROPS:", turns_elapsed)
    mature_count = 0
    for crop in crops:
        if crop.get("mature", False):
            mature_count += 1
    if mature_count == 0:
        msg_plant(f"  No mature crops", turns_elapsed)
    else:
        msg_plant(f"  *Mature crops = {mature_count}*", turns_elapsed)
        for tid, task in tasks.items():
            if task[tid]["type"] == TASK_REAPING:
                msg_plant(f"Crops being reaped by: {task["name"]}")

    # --- HYDROPONICS STATUS ---
    hydro = next((r for r in resources if r.get("name") == "HydroponicsRoom"), None)
    if hydro:
        beds = hydro.get("beds", [])
        free = sum(1 for b in beds if not b["occupied"] and not b["reserved"])
        reserved = sum(1 for b in beds if b["reserved"])
        occupied = sum(1 for b in beds if b["occupied"])

        log_and_display("", turns_elapsed, stamp=None)
        msg_plant(" HYDROPONICS:", turns_elapsed)
        msg_plant(f"  Beds — Free: {free}, Reserved: {reserved}, In Use: {occupied}", turns_elapsed)

    # --- MEAL PREPARATION ---
    meal_maker = next((r for r in resources if r.get("name") == "MealMaker"), None)

    log_and_display("", turns_elapsed, stamp=None)
    msg_food(" FOOD PREPARATION:", turns_elapsed)

    if not meal_maker:
        msg_food("  No food preparation equipment found.", turns_elapsed)
    else:
        status = "AVAILABLE"
        if meal_maker.get("in_use"):
            status = "IN USE"
        elif meal_maker.get("broken"):
            status = "BROKEN"

        msg_food(f"  MealMaker: {status}", turns_elapsed)

    return


def list_power(task_package):
    # List everything relating to power, including Droid charge levels
    resources = task_package["resources"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    turns_elapsed = task_package["counters"]["turns"]

    # List power status
    FULL = FULL_CHARGE  # from constants.py

    # --- Power Supply ---
    power = next((r for r in resources if r["name"] == "PowerSupply"), None)
    if not power:
        msg_power(get_message("error", "power_not_found"), turns_elapsed)
        return

    amount = power.get("amount", 0)

    if amount >= FULL * 2 * NUM_DROIDS:
        power_status = "OKAY"
    elif amount >= FULL * NUM_DROIDS:
        power_status = "LOW"
    else:
        power_status = "CRITICAL"

    msg_power("POWER STATUS:", turns_elapsed)
    msg_power(f"  PowerSupply: {power_status} ({amount} units)", turns_elapsed)

    # --- Droids ---
    msg_power("\nDROID CHARGE LEVELS:", turns_elapsed)

    for name, data in droids.items():
        charge = data.get("charge", 0)/(FULL_CHARGE/100)
        ratio = charge / 100 if FULL else 0

        if ratio >= 1.0:
            status = "FULL"
        elif ratio >= 0.3:
            status = "OK"
        elif ratio > 0:
            status = "LOW"
        else:
            status = "CRITICAL"

        msg_power(f"  {name:<10} {status} ({charge:.0f}%)", turns_elapsed)

    # --- Crystals ---
    msg_crystal("\nCRYSTALS IN STORAGE:", turns_elapsed)
    crystals = power.get("CrystalStore", {})
    if crystals:
        red = crystals.get("red", 0)
        indigo = crystals.get("indigo", 0)
        gold = crystals.get("gold", 0)
        msg_crystal(f"  Red: {red}   Indigo: {indigo}   Gold: {gold}", turns_elapsed)
    else:
        msg_crystal("  No crystals in storage.", turns_elapsed)

    # --- Vials ---
    msg_crystal("\nVIALS IN STORAGE:", turns_elapsed)
    vials = power.get("VialStore", {})
    if vials:
        red = vials.get("red", 0)
        indigo = vials.get("indigo", 0)
        gold = vials.get("gold", 0)
        msg_crystal(f"  Red: {red}   Indigo: {indigo}   Gold: {gold}", turns_elapsed)
    else:
        msg_crystal("  No vials in storage.", turns_elapsed)

    # --- Crystal Processing ---
    processor = next((r for r in resources if r["name"] == "CrystalProcessor"), None)
    mortar = next((r for r in resources if r["name"] == "CrystalMortarAndPestle"), None)

    msg_crystal("\nCRYSTAL PROCESSING:", turns_elapsed)

    if processor and processor.get("found"):
        msg_crystal("  CrystalProcessor: AVAILABLE", turns_elapsed)
    elif mortar and mortar.get("found"):
        msg_crystal("  Mortar & Pestle: AVAILABLE (manual processing)", turns_elapsed)
    else:
        msg_crystal("  No processing equipment available.", turns_elapsed)
    cp_assigned = ""
    for tid, task in tasks.items():
        if task["type"] == TASK_ASSIGNED:
            if task["item_name"] == "CrystalProcessor":
                cp_assigned = task["name"]
    if cp_assigned != "":
        msg_crystal(f"  Assigned to the Crystal Processor:  {cp_assigned}")

    # --- Refuel ---
    msg_power("\nREFUEL:", turns_elapsed)
    msg_power("  Use 'refuel <name>' to convert crystal vials into power.", turns_elapsed)

    return


def list_resources(task_package):
    # List all of the resources, in groups

    def get_display_msg(res):
        display_msg = "-- No need to examine this item --"
        if res["examined"] or not res["examinable"]:
            display_msg = res["msg"]
        elif res["examinable"]:
            display_msg = "-= Not examined yet =-"
        return display_msg
    
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]

    if not resources:
        msg_resource(get_message("error", "no_items"), turns_elapsed)
        return

    important, num_important = count_resource_by_category(resources, category1="essential", category2="chain")
    useful, num_useful = count_resource_by_category(resources, category1="replacement", category2="novelty")
    junk, num_junk = count_resource_by_category(resources, category1="junk")
        
    msg_resource("IMPORTANT RESOURCES:", turns_elapsed)
    for i, res in enumerate(important):
        display_msg = get_display_msg(res)
        item_name = res["name"]
        log_and_display(f" {item_name}:".ljust(30) + f"{display_msg}", turns_elapsed)
    if num_important == 0: msg_resource("(none found yet)\n", turns_elapsed)
    else: log_and_display("", turns_elapsed, stamp=None)

    msg_resource("USEFUL RESOURCES:", turns_elapsed)
    for i, res in enumerate(useful):
        display_msg = get_display_msg(res)
        item_name = res["name"]
        msg_resource(f" {item_name}:".ljust(30) + f"{display_msg}", turns_elapsed)
    if num_useful == 0: log_and_display("(none found yet)\n", turns_elapsed)
    else: log_and_display("", turns_elapsed, stamp=None)

    msg_resource("JUNK:", turns_elapsed)
    for i, res in enumerate(junk):
        display_msg = get_display_msg(res)
        item_name = res["name"]
        msg_resource(f" {item_name}:".ljust(30) + f"{display_msg}", turns_elapsed)
    if num_junk == 0: log_and_display("(none found yet)", turns_elapsed, stamp=None)

    return


def list_crystals(task_package):
    # List just the crystals
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]

    # List power status
    FULL = FULL_CHARGE  # from constants.py

    # --- Power Supply ---
    power = next((r for r in resources if r["name"] == "PowerSupply"), None)
    if not power:
        msg_power(get_message("error", "power_not_found"), turns_elapsed)
        return

    amount = power.get("amount", 0)

    # --- Crystals ---
    msg_crystal("CRYSTALS IN STORAGE:", turns_elapsed)
    crystals = power.get("CrystalStore", {})
    if crystals:
        red = crystals.get("red", 0)
        indigo = crystals.get("indigo", 0)
        gold = crystals.get("gold", 0)
        msg_crystal(f"  Red: {red}   Indigo: {indigo}   Gold: {gold}", turns_elapsed)
    else:
        msg_crystal("  -- No crystals found yet --", turns_elapsed)

    # --- Vials ---
    log_and_display("", turns_elapsed, stamp = False)
    msg_crystal("VIALS IN STORAGE:", turns_elapsed)
    vials = power.get("VialStore", {})
    if vials:
        red = vials.get("red", 0)
        indigo = vials.get("indigo", 0)
        gold = vials.get("gold", 0)
        msg_crystal(f"  Red: {red}   Indigo: {indigo}   Gold: {gold}", turns_elapsed)
    else:
        msg_crystal("  No vials in storage.", turns_elapsed)

    # --- Totals ---
    if crystals:
        msg_crystal("\nTOTAL CRYSTALS FOUND:")
        msg_crystal(f"   Red: {crystals["total_found"]["red"]}  Indigo: {crystals["total_found"]["indigo"]}  Gold: {crystals["total_found"]["gold"]}")
        msg_crystal("\nTOTAL CRYSTALS PROCESSED:")
        msg_crystal(f"   Red: {crystals["processed"]["red"]}  Indigo: {crystals["processed"]["indigo"]}  Gold: {crystals["processed"]["gold"]}")

    # --- Crystal combination - if found ---
    crystal_combination = next((r for r in resources if r.get("name") == "CrystalCombination"), None)
    red = indigo = gold = 0
    if crystal_combination: 
        red = crystal_combination["red"]
        indigo = crystal_combination["indigo"]
        gold = crystal_combination["gold"]
        msg_shield(f"CLOAKING SHIELD CRYSTALS NEEDED:\n**CloakingShield** CrystalCombination:- Red: {red}  Indigo: {indigo}  Gold: {gold}", turns_elapsed)

    return


def display_character_summary(humans, droids, task_type, turns):
    # Prints a summary of all characters, grouped by availability:
    # Idle, Busy (with current task), or Unavailable (e.g., starving or out of order).
    # For feed/charge tasks, shows hunger/charge and allows filtering by condition.

    idle_list = []
    busy_list = []
    unavailable_list = []

    # Humans
    if task_type != TASK_CHARGING:
        for name, h in humans.items():
            hunger = h.get("hunger", 0)
            state = h.get("state", "")
            current_task = h.get("task", "")
            tag = "(H)"

            if task_type == TASK_EATING:
                extra = f"{hunger}/10 ({state})"
                line = f"{name} {tag} - {extra}"
            else:
                extra = ""
                line = f"{name} {tag}"

            if state == "Starving":
                unavailable_list.append(f"{line} - Starving")
            elif h["task"] == "":
                idle_list.append(line)
            else:
                task_str = f"{current_task}"
                busy_list.append(f"{line} - {task_str}")

    # Droids
    if task_type != TASK_EATING:
        for name, d in droids.items():
            charge = d.get("charge", 0)
            current_task = d.get("task", "")
            tag = "(D)"
            charge_state = ""

            if task_type == TASK_CHARGING:
                if (d["charge"] <= LOW_CHARGE_FLAG*IDLE_CHARGE_USAGE): 
                    charge_state="Low" 
                else: 
                    charge_state = "Okay"
                extra = f"{charge}% ({charge_state})"
                line = f"{name} {tag} - {extra}"
            else:
                extra = ""
                line = f"{name} {tag}"

            if charge == 0:
                unavailable_list.append(f"{line} - Out of Order")
            elif d["task"] == "":
                idle_list.append(line)
            else:
                task_str = f"{current_task}"
                busy_list.append(f"{line} - {task_str}")

    if task_type == TASK_EATING:
        msg_food("Humans (H) available for giving food to:", turns)
    elif task_type == TASK_CHARGING:
        msg_power("Droids (D) available for charging:", turns)
    elif task_type == TASK_PLANTING:
        msg_plant("Humans (H) and Droids (D) available for planting:", turns)
    else:
        msg_info("Humans (H) and Droids (D) for this task:", turns)
    if idle_list:
        msg_info("Idle:\t\t" + ", ".join(idle_list), turns)
    if busy_list:
        msg_info("Busy:\t\t" + ", ".join(busy_list), turns)
    if unavailable_list:
        msg_info("Unavailable:\t" + ", ".join(unavailable_list), turns)



# NOTE: This is now a legacy function and has been disabled.
#       It needs to be retained as there is a lot of useful code in here.
def print_status(task_package):
    # Print the main status screen
    humans = task_package["humans"]
    droids = task_package["droids"]
    tasks = task_package["tasks"]
    resources = task_package["resources"]
    crops = task_package["crops"]
    gamestate = task_package["gamestate"]
    turns_elapsed = task_package["counters"]["turns"]
    shieldstate = task_package["shieldstate"]

    # Convert turns to day/turn display
    day = turns_elapsed // 10
    turn = turns_elapsed

    def get_resource_amount(name, resources):
        for res in resources:
            if res.get("name") == "FoodStore" and res.get("found") and name == "FoodStore" :
                total_food = res.get("rationPack") + res.get("apple") + res.get("cabbage") + res.get("potato") +\
                             res.get("soup") + res.get("smoothie") + res.get("stirFry")
                return total_food
            elif res.get("name") == "SeedStash" and name == "SeedStash" and res.get("found"):
                seeds_amount = res.get("apple") + res.get("cabbage") + res.get("potato")
                return seeds_amount
            elif res.get("name") == "PowerSupply" and res.get("found") and name == "PowerSupply":
                power_amount = res.get("amount")
                return power_amount
            elif res.get("name") == "PowerSupply" and res.get("found") and name == "CrystalStore":
                crystal_store = res.get("CrystalStore", "")
                total_crystals = 0
                if crystal_store:
                    total_crystals = crystal_store["red"] + crystal_store["indigo"] + crystal_store["gold"]
                return total_crystals
            elif res.get("name") == "PowerSupply" and res.get("found") and name == "VialStore":
                vial_store = res.get("VialStore", "")
                total_vials = 0
                if vial_store:
                    total_vials = vial_store["red"] + vial_store["indigo"] + vial_store["gold"]
                return total_vials
            elif res.get("name") == name and res.get("found"):
                return res.get("amount", "None")
        return 0

    def format_human_status(stats, task_name=None):
        state = stats.get("state", "Okay")
        hunger = stats.get("hunger", 0)

        if state == "Deceased":
            return f"{'DEAD':<26}  *Buried*"
    
        base = f"{state:<7} - Hunger: {hunger}"
        task_str = f"{task_name}" if task_name else "--Idle--"
        return f"{base:<20}  {task_str}"

    def format_droid_status(stats, task_name=None):
        charge = int(stats.get("charge", 0) / 10)
        state = ""
        if charge == 0:
            state = "Silent"
        else:
            state = "Ready"

        task_str = f"{task_name}" if task_name else "--Idle--"
        return f"{state} - Charge: {charge}%  ".ljust(14) + task_str

    def get_task_data(tasks, worker_name):
        # Returns (task_id, task_data) for the active task assigned to worker_name, or (None, None) if not found.
        for tid, task in tasks.items():
            if task.get("name") == worker_name:
                return task
        return None

    # Header
    print("-" * 85)
    print(f"Aynsefian Outpost Status  (Day {day+1}, Turn {turn})\n")

    # Human and Droid Display
    print("Humans:")
    more_turns = ""
    plural = ""
    for i in range(NUM_HUMANS):
        human_name = list(humans.keys())[i]
        task = get_task_data(tasks, human_name)
        if task:
            plural = "s." if task["duration"] != 1 else "."
            more_turns = f" for {task["duration"]} more turn{plural}"
        else:
            more_turns = ""

        human_stats = humans[human_name]
        if human_stats["task"] == TASK_ASSIGNED:
            human_task = human_stats["task"] + " to the " + human_stats["item"] + more_turns
        elif human_stats["task"] == TASK_EXAMINING:
            human_task = human_stats["task"] + " the " + human_stats["item"] + more_turns
        else:
            human_task = human_stats["task"] + more_turns
        print(f"   {human_name.ljust(8)} {format_human_status(human_stats, human_task)}")
        queue = human_stats["queue"]
        queue_str = ""
        if queue["1"]["task"] != "" or queue["2"]["task"] != "" or queue["3"]["task"] != "":
            if queue["1"]["task"] != "":
                queue_str += queue["1"]["task"]
            if queue["2"]["task"] != "":
                queue_str += ", " + queue["2"]["task"]
            if queue["3"]["task"] != "":
                queue_str += ", " + queue["3"]["task"]
            print(f"                                  Queued:  {queue_str}")

    print("Droids:")
    for i in range(NUM_DROIDS):
        droid_name = list(droids.keys())[i]
        task = get_task_data(tasks, droid_name)
        if task:
            plural = "s." if task["duration"] != 1 else "."
            more_turns = f" for {task["duration"]} more turn{plural}"
        else:
            more_turns = ""

        droid_stats = droids[droid_name]
        if droid_stats["task"] == TASK_ASSIGNED:
            droid_task = droid_stats["task"] + " to the " + droid_stats["item"] + more_turns
        elif droid_stats["task"] == TASK_EXAMINING:
            droid_task = droid_stats["task"] + " the " + droid_stats["item"] + more_turns
        else:
            droid_task = droid_stats["task"] + more_turns
        print(f"   {droid_name.ljust(8)}  {format_droid_status(droid_stats, droid_task).ljust(24)}")
        queue = droid_stats["queue"]
        queue_str = ""
        if queue["1"]["task"] != "" or queue["2"]["task"] != "" or queue["3"]["task"] != "":
            if queue["1"]["task"] != "":
                queue_str += queue["1"]["task"]
            if queue["2"]["task"] != "":
                queue_str += ", " + queue["2"]["task"]
            if queue["3"]["task"] != "":
                queue_str += ", " + queue["3"]["task"]
            print(f"                                  Queued:  {queue_str}")

    # Resource Summary
    food = get_resource_amount("FoodStore", resources)
    power = get_resource_amount("PowerSupply", resources)
    seeds = get_resource_amount("SeedStash", resources)
    crystals = get_resource_amount("CrystalStore", resources)
    vials = get_resource_amount("VialStore", resources)
    print()
    print(f"Sustainment:   Power - {power}\tFood - {food}\tSeeds - {seeds}")

    print("Crops:         ", end='')
    if gamestate.get("plant", False):
        planting_enabled = "Planting: Enabled"
    else:
        planting_enabled = "Planting: --Cannot plant yet--"
    apple = cabbage = potato = 0
    for crop in crops.values():
        crop_type = crop["crop_type"]
        if crop_type == "apple": apple += 1
        if crop_type == "cabbage": cabbage += 1
        if crop_type == "potato": potato += 1
    if apple>0 or cabbage>0 or potato>0: 
        print(f"Apples - {apple}  Cabbages - {cabbage}  Potatoes - {potato}    {planting_enabled}")
    else:
        print(f"-- No crops currently growing --    {planting_enabled}")

    if gamestate.get("mine", False):
        mining_enabled = "Mining: Enabled"
    else:
        mining_enabled = "Mining: --cannot mine yet--"
    print(f"Crystals:\tCurrent - {crystals}\tVials - {vials}\t{mining_enabled}")

    # Discovered Resources
    discovered = get_discovered_resources(resources)
    if discovered:        
        important, num_important = count_resource_by_category(resources, category1="essential", category2="chain")
        useful, num_useful = count_resource_by_category(resources, category1="replacement", category2="novelty")
        junk, num_junk = count_resource_by_category(resources, category1="junk")

        print(f"Resources:     Important - {num_important}\tUseful - {num_useful}\tJunk - {num_junk}")

        assignable_string = "-- nothing assignable yet --"
        crystal_processor = next((r for r in resources if r.get("name") == "CrystalProcessor"), None)
        if crystal_processor:
            assignable_string = "CrystalProcessor"
        meal_maker = next((r for r in resources if r.get("name") == "MealMaker"), None)
        if meal_maker:
            if not crystal_processor:
                assignable_string = "MealMaker"
            else:
                assignable_string += ", MealMaker"
        old_terminal = next((r for r in resources if r.get("name") == "OldTerminal"), None)
        if old_terminal:
            if not (crystal_processor and meal_maker):
                assignable_string = "OldTerminal"
            else:
                assignable_string += ", OldTerminal"
        cloaking_shield = next((r for r in resources if r.get("name") == "CloakingShield"), None)
        if cloaking_shield:
            if not (crystal_processor and meal_maker and old_terminal):
                assignable_string = "CloakingShield"
            else:
                assignable_string += ", CloakingShield"
        print(f"Assignable items:  {assignable_string}")
    else:
        print("Resources:     -- Nothing discovered --")
    
    shield = "Inactive"
    if shieldstate["shield_active"]:
        shield = "Active"
    
    shield_located = "--Not found yet--"
    manual_status = "--Not found yet--"
    decode_status = "--Not found yet--"
    combi_status = "--Not found yet--"
    combi_text = ""
    droidcode_status = "--Not found yet--"
    ancient_droid_name = "--Not known--"
    shield_manual = decode_key = crystal_combination = droid_code = None

    if discovered:  
        cloaking_shield = next((r for r in resources if r.get("name") == "CloakingShield"), None)
        if cloaking_shield: shield_located = "* Shield Found *"

        shield_manual = next((r for r in resources if r.get("name") == "ShieldManual"), None)
        if shield_manual: 
            manual_status = "On the main desk in the outpost"

        decode_key = next((r for r in resources if r.get("name") == "DecodeKey"), None)
        if decode_key: decode_status = "Usable by the droids"
        if shield_manual:
            if shield_manual["decoded"] and decode_key: manual_status = "-- Decoded and usable --"

        crystal_combination = next((r for r in resources if r.get("name") == "CrystalCombination"), None)
        red = indigo = gold = 0
        combi_text = ""
        if crystal_combination: 
            combi_status = "Found:"
            red = crystal_combination["red"]
            indigo = crystal_combination["indigo"]
            gold = crystal_combination["gold"]
            combi_text = f"- Red: {red}  Indigo: {indigo}  Gold: {gold}"

        droid_code = next((r for r in resources if r.get("name") == "AncientDroidCode"), None)
        if droid_code: 
            droidcode_status = "Found: "
            ancient_droid_name = droid_code["droidName"]
            if ancient_droid_name == "null":
                ancient_droid_name = "--Not known--"

    if shield_located:
        print(f"\n\t\tSHIELD STATUS:  {shield}\n  *Cloaking Shield*:\t\t{shield_located}")
    else:
        print(f"\n\t\tSHIELD STATUS:  --not located yet--")
    if shield_manual:
        print(f"  Shield Manual:\t\t{manual_status}")
    if decode_key:
        print(f"  Shield Manual Decode Key:\t{decode_status}")
    if crystal_combination:
        print(f"  Crystal Combination:\t\t{combi_status} {combi_text}")
    if droid_code:
        print(f"  Ancient Droid Code:\t\t{droidcode_status}   Droid with code: {ancient_droid_name}")

    print("-" * 85)

    if gamestate.get("game_over", False):
        reason_code = gamestate.get("endgame_reason")
        endgame_msg = ENDGAME_REASONS[reason_code]
        if (reason_code != "you_win?"):
            print(f"\n--== GAME OVER: you have sadly failed in your task of protecting Aysnefian 💀😔 ==--\nReason for GAME OVER:  {endgame_msg}\n")
        else:
            print(f"\n--== GAME OVER: You have *foiled* the Melcheisa Galactic Council 🎉 ==--\nReason for GAME OVER:  {endgame_msg}\n")

    return