# status.py

from constants import ENDGAME_REASONS, FULL_CHARGE, HUNGER, NUM_HUMANS, NUM_DROIDS, TASK_ASSIGNED, TASK_EXAMINING
from lore.user_interface import log_and_display, get_input
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


def print_status(task_package):

    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    gamestate = task_package["gamestate"]
    turns_elapsed = task_package["turns_elapsed"]
    shieldstate = task_package["shieldstate"]

    # Convert turns to day/turn display
    day = turns_elapsed // 10
    turn = turns_elapsed

    def get_resource_amount(name, resources):
        for res in resources:
            if res.get("name") == "FoodStore" and name == "FoodStore" and res.get("found"):
                total_food = res.get("rationPack") + res.get("apple") + res.get("cabbage") + res.get("potato") +\
                             res.get("soup") + res.get("smoothie") + res.get("stirFry")
                return total_food
            elif res.get("name") == "SeedStash" and name == "SeedStash" and res.get("found"):
                seeds_amount = res.get("apple") + res.get("cabbage") + res.get("potato")
                return seeds_amount
            elif res.get("name") == "PowerSupply" and res.get("found"):
                crystal_store = res.get(name)
                total_crystals = 0
                if crystal_store:
                    total_crystals = crystal_store["red"] + crystal_store["indigo"] + crystal_store["gold"]
                return total_crystals
            elif res.get("name") == "PowerSupply" and name == "VialStore" and res.get("found"):
                vial_store = res.get(name)
                total_vials = 0
                if vial_store:
                    total_vials = vial_store["red"] + vial_store["indigo"] + vial_store["gold"]
                return total_vials
            elif res.get("name") == name and res.get("found"):
                return res.get("amount", "None")
        return "None"

    def get_discovered_resources(resources):
        return [
            res["name"]
            for res in resources
            if res.get("found", False)
        ]

    def format_human_status(stats, task_name=None):
        state = stats.get("state", "Okay")
        hunger = stats.get("hunger", 0)

        if state == "Deceased":
            return f"{'DEAD':<26}  *Buried*"

        base = f"{state} ({hunger})"
        task_str = f"Task: {task_name}" if task_name else "--Idle--"
        return f"{base:<11}  {task_str:<15}"

    def format_droid_status(stats, task_name=None):
        charge = int(stats.get("charge", 0) / 10)
        task = stats.get("task", "Idle")
        if charge == 0:
            task = "OutOfOrder"
        else:
            task = "Ready"

        task_str = f"Task: {task_name}" if task_name else "--Idle--"
        return f"{task} ({charge}%)  ".ljust(15) + task_str.ljust(13)

    # Header
    print("-" * 85)
    print(f"Aynsefian Outpost Status  (Day {day+1}, Turn {turn})\n")

    # Human and Droid Display
    print("Humans:")
    for i in range(NUM_HUMANS):
        human_name = list(humans.keys())[i]
        human_stats = humans[human_name]
        if human_stats["task"] == TASK_ASSIGNED:
            human_task = human_stats["task"] + " to the " + human_stats["item"]
        elif human_stats["task"] == TASK_EXAMINING:
            human_task = human_stats["task"] + " the " + human_stats["item"]
        else:
            human_task = human_stats["task"]
        print(f"   {human_name.ljust(8)} {format_human_status(human_stats, human_task)}")

    print("Droids:")
    for i in range(NUM_DROIDS):
        droid_name = list(droids.keys())[i]
        droid_stats = droids[droid_name]
        if droid_stats["task"] == TASK_ASSIGNED:
            droid_task = droid_stats["task"] + " to the " + droid_stats["item"]
        elif droid_stats["task"] == TASK_EXAMINING:
            droid_task = droid_stats["task"] + " the " + droid_stats["item"]
        else:
            droid_task = droid_stats["task"]
        print(f"   {droid_name.ljust(8)} {format_droid_status(droid_stats, droid_task)}")

    # Resource Summary
    food = get_resource_amount("FoodStore", resources)
    power = get_resource_amount("PowerSupply", resources)
    seeds = get_resource_amount("SeedStash", resources)
    crystals = get_resource_amount("CrystalStore", resources)
    vials = get_resource_amount("VialStore", resources)
    print()
    print(f"Power:  {power}\tFood:  {food}\tSeeds:  {seeds}\tCrystals: {crystals}\tVials: {vials}\n")

    # Discovered Resources
    discovered = get_discovered_resources(resources)
    if discovered:        
        important, num_important = count_resource_by_category(resources, category1="essential", category2="chain")
        useful, num_useful = count_resource_by_category(resources, category1="replacement", category2="novelty")
        special, num_special = count_resource_by_category(resources, category1="tarot")
        junk, num_junk = count_resource_by_category(resources, category1="junk")

        print(f"                        RESOURCES\n" +
              f"Important: {num_important}       Useful: {num_useful}          Special: {num_special}         Junk: {num_junk}")

    else:
        print("Discovered:   Nothing...at this stage.")
    
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

    if discovered:  
        cloaking_shield = next((r for r in resources if r.get("name") == "CloakingShield"), None)
        if cloaking_shield: shield_located = "* Shield Found *"

        shield_manual = next((r for r in resources if r.get("name") == "ShieldManual"), None)
        if shield_manual: manual_status = "On the main desk in the outpost"

        decode_key = next((r for r in resources if r.get("name") == "DecodeKey"), None)
        if decode_key: decode_status = "Usable by the droids"

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

    print(f"\n\t\tSHIELD STATUS:  {shield}\n\n  *Cloaking Shield*:\t\t{shield_located}")
    print(f"  Shield Manual:\t\t{manual_status}")
    print(f"  Shield Manual Decode Key:\t{decode_status}")
    print(f"  Crystal Combination:\t\t{combi_status} {combi_text}")
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


def handle_list_command(qualifier, task_package):
    # List lots of things (eventually)

    humans = task_package["humans"]
    droids = task_package["droids"]
    resources = task_package["resources"]
    crops = task_package["crops"]
    turns_elapsed = task_package["turns_elapsed"]

    can_be_listed = "'food', 'power', 'resources'"

    def get_display_msg(res):
        display_msg = "-- No need to examine this item --"
        if res["examined"] or not res["examinable"]:
            display_msg = res["msg"]
        elif res["examinable"]:
            display_msg = "-= Not examined yet =-"
        return display_msg

    # Step 1: Get targets (either from qualifier or prompt)
    if not qualifier:
        to_be_listed = get_input("input", "list", turns_elapsed, can_be_listed=can_be_listed)
    else:
        to_be_listed = qualifier

    # List food and food-related systems
    if to_be_listed == "food":
        # --- FOOD STORE ---
        food_store = next((r for r in resources if r.get("name") == "FoodStore"), None)
        if not food_store:
            log_and_display(" FOOD STATUS:", turns_elapsed)
            log_and_display("  No FoodStore found.", turns_elapsed)
            return

        log_and_display(" FOOD STATUS:", turns_elapsed)

        log_and_display(f"  Ration Packs: {food_store.get('rationPack', 0)}", turns_elapsed)
        log_and_display(
            f"  Apples: {food_store.get('apple', 0)} | "
            f"Cabbages: {food_store.get('cabbage', 0)} | "
            f"Potatoes: {food_store.get('potato', 0)}",
            turns_elapsed
        )
        log_and_display(
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

        log_and_display("", turns_elapsed)
        log_and_display(" HUMAN HUNGER:", turns_elapsed)

        if not hungry and not starving and not near_death:
            log_and_display("  Everyone is currently fed and happy. Well, fed, anyway.", turns_elapsed)
        else:
            if hungry:
                log_and_display(f"  Hungry: {', '.join(hungry)}", turns_elapsed)
            if starving:
                log_and_display(f"  Starving: {', '.join(starving)}", turns_elapsed)
            if near_death:
                log_and_display(f"  Near Death: {', '.join(near_death)}", turns_elapsed)
            if deceased:
                log_and_display(f"  Dead 💀: {', '.join(deceased)}", turns_elapsed)

        # --- CROPS GROWING ---
        log_and_display("", turns_elapsed)
        log_and_display(" CROPS GROWING:", turns_elapsed)

        if not crops:
            log_and_display("  No crops are currently growing.", turns_elapsed)
        else:
            for crop in crops.values():
                bed_id = crop["bed_id"]["id"]
                crop_type = crop["crop_type"]
                turns = crop["turns_remaining"]
                log_and_display(
                    f"  Bed #{bed_id}: {crop_type} ({turns} turns remaining)",
                    turns_elapsed
                )

        # --- SEEDS AVAILABLE ---
        log_and_display("", turns_elapsed)
        log_and_display(" SEEDS:", turns_elapsed)

        seeds = next((r for r in resources if r.get("name") == "SeedStash"), None)
        if seeds:
            log_and_display(
                f"  Apple: {seeds.get('apple', 0)} | "
                f"Cabbage: {seeds.get('cabbage', 0)} | "
                f"Potato: {seeds.get('potato', 0)}",
                turns_elapsed
            )
        else:
            log_and_display("  No seeds have been found so far.", turns_elapsed)

        # --- HYDROPONICS STATUS ---
        hydro = next((r for r in resources if r.get("name") == "HydroponicsRoom"), None)
        if hydro:
            beds = hydro.get("beds", [])
            free = sum(1 for b in beds if not b["occupied"] and not b["reserved"])
            reserved = sum(1 for b in beds if b["reserved"])
            occupied = sum(1 for b in beds if b["occupied"])

            log_and_display("", turns_elapsed)
            log_and_display(" HYDROPONICS:", turns_elapsed)
            log_and_display(
                f"  Beds — Free: {free}, Reserved: {reserved}, In Use: {occupied}",
                turns_elapsed
            )

        # --- MEAL PREPARATION ---
        meal_maker = next((r for r in resources if r.get("name") == "MealMaker"), None)

        log_and_display("", turns_elapsed)
        log_and_display(" FOOD PREPARATION:", turns_elapsed)

        if not meal_maker:
            log_and_display("  No food preparation equipment found.", turns_elapsed)
        else:
            status = "AVAILABLE"
            if meal_maker.get("in_use"):
                status = "IN USE"
            elif meal_maker.get("broken"):
                status = "BROKEN"

            log_and_display(f"  MealMaker: {status}", turns_elapsed)

    # List power status
    elif to_be_listed == "power":
        FULL = FULL_CHARGE  # from constants.py

        # --- Power Supply ---
        power = next((r for r in resources if r["name"] == "PowerSupply"), None)
        if not power:
            log_and_display(get_message("error", "power_not_found"), turns_elapsed)
            return

        amount = power.get("amount", 0)

        if amount >= FULL * 2 * NUM_DROIDS:
            power_status = "OKAY"
        elif amount >= FULL * NUM_DROIDS:
            power_status = "LOW"
        else:
            power_status = "CRITICAL"

        log_and_display("POWER STATUS:", turns_elapsed)
        log_and_display(f"  PowerSupply: {power_status} ({amount} units)", turns_elapsed)

        # --- Droids ---
        log_and_display("\nDROID CHARGE LEVELS:", turns_elapsed)

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

            log_and_display(f"  {name:<10} {status} ({charge:.0f}%)", turns_elapsed)

        # --- Crystals ---
        log_and_display("\nCRYSTALS IN STORAGE:", turns_elapsed)
        crystals = power.get("CrystalStore", {})
        if crystals:
            red = crystals.get("red", 0)
            indigo = crystals.get("indigo", 0)
            gold = crystals.get("gold", 0)
            log_and_display(f"  Red: {red}   Indigo: {indigo}   Gold: {gold}", turns_elapsed)
        else:
            log_and_display("  No crystals in storage.", turns_elapsed)

        # --- Vials ---
        log_and_display("\nVIALS IN STORAGE:", turns_elapsed)
        vials = power.get("VialStore", {})
        if vials:
            red = vials.get("red", 0)
            indigo = vials.get("indigo", 0)
            gold = vials.get("gold", 0)
            log_and_display(f"  Red: {red}   Indigo: {indigo}   Gold: {gold}", turns_elapsed)
        else:
            log_and_display("  No vials in storage.", turns_elapsed)

        # --- Crystal Processing ---
        processor = next((r for r in resources if r["name"] == "CrystalProcessor"), None)
        mortar = next((r for r in resources if r["name"] == "CrystalMortarAndPestle"), None)

        log_and_display("\nCRYSTAL PROCESSING:", turns_elapsed)

        if processor and processor.get("found"):
            log_and_display("  CrystalProcessor: AVAILABLE", turns_elapsed)
        elif mortar and mortar.get("found"):
            log_and_display("  Mortar & Pestle: AVAILABLE (manual processing)", turns_elapsed)
        else:
            log_and_display("  No processing equipment available.", turns_elapsed)

        # --- Refuel ---
        log_and_display("\nREFUEL:", turns_elapsed)
        log_and_display("  Use 'refuel <name>' to convert crystal vials into power.", turns_elapsed)

    # List all of the resources, in groups
    elif to_be_listed == "resources":
        if not resources:
            log_and_display(get_message("error", "no_items"), turns_elapsed)
            return

        important, num_important = count_resource_by_category(resources, category1="essential", category2="chain")
        useful, num_useful = count_resource_by_category(resources, category1="replacement", category2="novelty")
        special, num_special = count_resource_by_category(resources, category1="tarot")
        junk, num_junk = count_resource_by_category(resources, category1="junk")
        
        log_and_display("IMPORTANT RESOURCES:", turns_elapsed)
        for i, res in enumerate(important):
            display_msg = get_display_msg(res)
            item_name = res["name"]
            log_and_display(f" {item_name}:".ljust(30) + f"{display_msg}", turns_elapsed)
        if num_important == 0: log_and_display("(none found yet)\n", turns_elapsed)
        else: log_and_display("", turns_elapsed)

        log_and_display("USEFUL RESOURCES:", turns_elapsed)
        for i, res in enumerate(useful):
            display_msg = get_display_msg(res)
            item_name = res["name"]
            log_and_display(f" {item_name}:".ljust(30) + f"{display_msg}", turns_elapsed)
        if num_useful == 0: log_and_display("(none found yet)\n", turns_elapsed)
        else: log_and_display("", turns_elapsed)

        log_and_display("SPECIAL ITEMS:", turns_elapsed)
        for i, res in enumerate(special):
            display_msg = get_display_msg(res)
            item_name = res["name"]
            log_and_display(f" {item_name}:".ljust(30) + f"{display_msg}", turns_elapsed)
        if num_special == 0: log_and_display("(none found yet)\n", turns_elapsed)
        else: log_and_display("", turns_elapsed)

        log_and_display("JUNK:", turns_elapsed)
        for i, res in enumerate(junk):
            display_msg = get_display_msg(res)
            item_name = res["name"]
            log_and_display(f" {item_name}:".ljust(30) + f"{display_msg}", turns_elapsed)
        if num_junk == 0: log_and_display("(none found yet)", turns_elapsed)

    # Nothing else to be listed at this stage
    else:
        log_and_display(get_message("error", "list_fail"), turns_elapsed)

    return