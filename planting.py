# planting.py

import random
from constants import SERVING_VALUE, HYDROPONICS_BED_MIN, HYDROPONICS_BED_MAX, SEED_PACKETS_USED, TASK_PLANTING
from lore.lore_ingame import get_message
from lore.user_interface import get_input, log_and_display
from utils import process_hunger_status, can_character_act


def feed_human(name, task_package):
    humans = task_package["humans"]
    resources = task_package["resources"]
    return_msg = ""
    food_store = next((r for r in resources if r["name"] == "FoodStore"), None)

    if not food_store:
        return_msg = get_message("feed", "no_foodstore")
        return return_msg, task_package

    available = {
        "apple": food_store.get("apple", 0),
        "potato": food_store.get("potato", 0),
        "cabbage": food_store.get("cabbage", 0),
        "rationPack": food_store.get("rationPack", 0)
    }

    served = {"apple": 0, "potato": 0, "cabbage": 0}

    # Try full meal combos
    if available["apple"] >= 4*SERVING_VALUE["apple"] and available["potato"] >= SERVING_VALUE["potato"] and available["cabbage"] >= SERVING_VALUE["cabbage"]:
        served.update({"apple": 4*SERVING_VALUE["apple"], "potato": SERVING_VALUE["potato"], "cabbage": SERVING_VALUE["cabbage"]})
    elif available["apple"] >= 4*SERVING_VALUE["apple"] and available["potato"] >= 2*SERVING_VALUE["potato"]:
        served.update({"apple": 4*SERVING_VALUE["apple"], "potato": 2*SERVING_VALUE["potato"]})
    elif available["apple"] >= 4*SERVING_VALUE["apple"] and available["cabbage"] >= 2*SERVING_VALUE["cabbage"]:
        served.update({"apple": 4*SERVING_VALUE["apple"], "cabbage": 2*SERVING_VALUE["cabbage"]})
    elif available["potato"] >= 2*SERVING_VALUE["potato"] and available["cabbage"] >= 2*SERVING_VALUE["cabbage"]:
        served.update({"potato": 2*SERVING_VALUE["potato"], "cabbage": 2*SERVING_VALUE["cabbage"]})
    elif available["apple"] >= 8*SERVING_VALUE["apple"]:
        served.update({"apple": 8*SERVING_VALUE["apple"]})
    elif available["potato"] >= 4*SERVING_VALUE["potato"]:
        served.update({"potato": 4*SERVING_VALUE["potato"]})
    elif available["cabbage"] >= 4*SERVING_VALUE["cabbage"]:
        served.update({"cabbage": 4*SERVING_VALUE["cabbage"]})
    elif available["rationPack"] >= 1:
        food_store["rationPack"] -= 1
        return_msg = get_message("feed", "fed_ration", person_name=name)
        humans[name]["hunger"] = max(0, humans[name]["hunger"] - 10)
        task_package = process_hunger_status(name, task_package)
        return return_msg, task_package

    # Fallback: partial feed with *any* food available
    else:
        total_nutrition = 0
        for item in ["apple", "potato", "cabbage"]:
            qty = available[item]
            if qty > 0:
                served[item] = qty
                total_nutrition += qty
                food_store[item] -= qty

        if total_nutrition == 0:
            return_msg = get_message("feed", "food_all_used_up", person_name=name)
            return return_msg, task_package

        message = f"{name} received a partial meal: "
        message += ", ".join([f"{v} {k} servings" for k, v in served.items() if v > 0])
        return_msg = message

        # Reduce hunger based on total items given
        hunger_reduction = min(total_nutrition, 10)
        humans[name]["hunger"] = max(0, humans[name]["hunger"] - hunger_reduction)

        task_package = process_hunger_status(name, task_package)
        return return_msg, task_package

    # Deduct served amounts
    for item, qty in served.items():
        food_store[item] -= qty

    # Log what was served
    message = f"{name} was fed: "
    message += ", ".join([f"{qty} {item} servings" for item, qty in served.items() if qty > 0])
    return_msg = message

    humans[name]["hunger"] = max(0, humans[name]["hunger"] - 10)
    
    task_package = process_hunger_status(name, task_package)
    return return_msg, task_package


def update_food_amount(resources, food_type, amount, turns_elapsed, allow_negative=False):
    # Updates the quantity of a specific food type in the FoodStore.
    # food_type (str): The type of food to update ("apple", "soup", etc.)
    # amount (float or int): Amount to add (positive) or subtract (negative).
    
    food_store = next((r for r in resources if r["name"] == "FoodStore"), None)
    if not food_store:
        log_and_display(get_message("error", "no_food_store"), turns_elapsed)

    if food_type not in food_store:
        food_store[food_type] = 0

    food_store[food_type] += amount

    if not allow_negative and food_store[food_type] < 0:
        food_store[food_type] = 0  # Clamp at zero

    return resources


def get_food_amount(resources, food_type):
    # Returns the current quantity of a given food type from the FoodStore.
    food_store = next((r for r in resources if r["name"] == "FoodStore"), None)
    if not food_store:
        return 0

    return food_store.get(food_type, 0)


def update_multiple_foods(resources, allow_negative=False, **kwargs):
    # Updates multiple food types at once.
    # **kwargs: Food types and amounts to update, e.g. apple=4, soup=-1.

    for food_type, amount in kwargs.items():
        resources = update_food_amount(resources, food_type, amount, allow_negative)
    return resources


def initialise_hydroponics_room(resources):
    #  Ensure the HydroponicsRoom resource has beds, powered flag, and power_usage.
    # Safe to call multiple times – will only initialise once.
    for r in resources:
        if r.get("name") == "HydroponicsRoom":
            # Already initialised? Leave it.
            if "beds" in r and r["beds"]:
                return resources

            bed_count = random.randint(HYDROPONICS_BED_MIN, HYDROPONICS_BED_MAX)

            r["beds"] = [
                {
                    "id": i + 1,
                    "occupied": False,
                    "reserved": False,
                    "crop_id": None  # will point into crops dict later
                }
                for i in range(bed_count)
            ]

            # Preserve your existing flags; just set defaults if missing
            r.setdefault("replaced", False)
            r.setdefault("augmented", False)

            # Power-related fields – these will matter when we wire the power system
            r.setdefault("powered", True)
            r.setdefault("power_usage", 10)  # tweak later for balance

            return resources

    # If there is no HydroponicsRoom yet, just return.
    return resources

def get_hydroponics_summary(resources, crops):
    # Returns a dict summary of the HydroponicsRoom beds and their crops.
    # Also optionally logs a nice description if you want to call it directly.
    
    room = next((r for r in resources if r.get("name") == "HydroponicsRoom"), None)
    if not room or "beds" not in room:
        # Nothing to show
        return None

    beds = room["beds"]
    total = len(beds)
    occupied = sum(1 for b in beds if b.get("occupied"))
    free = total - occupied

    # Build detail lines from crops dict (which we’ll flesh out later)
    details = []
    for bed in beds:
        if bed.get("occupied") and bed.get("crop_id") in crops:
            crop = crops[bed["crop_id"]]
            crop_type = crop.get("type", "unknown crop")
            worker = crop.get("worker", "someone")
            turns_remaining = crop.get("turns_remaining", "?")
            details.append(
                f"Bed #{bed['id']}: {crop_type} "
                f"(planted by {worker}, {turns_remaining} turns remaining)"
            )

    summary = {
        "total_beds": total,
        "occupied_beds": occupied,
        "free_beds": free,
        "details": details,
        "powered": room.get("powered", True),
        "power_usage": room.get("power_usage", 0),
    }

    return summary


def update_crop_growth(task_package):
    #Decreases turns_remaining on all crops.
    #Handles growth pausing if hydroponics is unpowered.
    #Announces crops that have matured.
    crops = task_package["crops"]
    resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]

    hydro = next((r for r in resources if r.get("name") == "HydroponicsRoom"), None)
    if not hydro:
        return task_package

    # If hydroponics is unpowered: growth pauses (failure chance added later)
    if not hydro.get("powered", True):
        return task_package

    # Normal growth
    for crop_id, crop in crops.items():
        if crop.get("mature", False):
            continue  # already done

        crop["turns_remaining"] -= 1

        if crop["turns_remaining"] <= 0:
            crop["mature"] = True
            crop["turns_remaining"] = 0

            # Narrative message
            bed = crop["bed_id"]["id"]
            log_and_display(get_message("plant", "crop_matured", planter=crop.get("worker", "Someone"), 
                                        crop_type=crop["crop_type"], bed=bed), turns_elapsed)

    return task_package


def enough_seeds(seed_type, resources):
    # Seed check
    stash = next((r for r in resources if r["name"] == "SeedStash"), None)
    return stash[seed_type] >= SEED_PACKETS_USED[seed_type]


def get_bed_by_id(hydro, bed_id):
    return next((b for b in hydro["beds"] if b["id"] == bed_id), None)


def determine_what_to_plant_and_where(raw_target, crops, resources, humans, droids, turns_elapsed):
    VALID_CROPS = ["apple", "cabbage", "potato"]
    plant_options = []

    # 1. Get worker name
    if not raw_target:
        raw_target = get_input("input", "plant", turns_elapsed)

    task_type = TASK_PLANTING
    okay_to_act, is_human, worker_name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed)
    if not okay_to_act:
        return False, None, None, resources

    # 2. Resource display and checks
    food_store = next((r for r in resources if r.get("name") == "FoodStore"), None)
    food_lines = [
        "FOOD IN STORAGE:",
        f"  Ration Packs: {food_store.get('rationPack', 0)}",
        f"  Apples: {food_store.get('apple', 0)}  Cabbages: {food_store.get('cabbage', 0)}  Potatoes: {food_store.get('potato', 0)}",
        f"  Soup servings: {food_store.get('soup', 0)}  Stir Fries: {food_store.get('stirFry', 0)}  Smoothies: {food_store.get('smoothie', 0)}"
    ]

    # Crop status
    if crops:
        crop_lines = ["CROPS:"]
        for crop in crops.values():
            bed_id = crop["bed_id"]["id"]
            crop_type = crop["crop_type"]
            crop_lines.append(f"  Bed #{bed_id}: {crop_type}")
    else:
        crop_lines = ["CROPS:  None growing"]

    # Seeds needed per bed
    seeds_per_bed_msg = f"SEEDS NEEDED PER BED:  Apple: {SEED_PACKETS_USED['apple']}  Cabbage: {SEED_PACKETS_USED['cabbage']}  Potato: {SEED_PACKETS_USED['potato']}"

    # Seed stash check
    seeds = next((r for r in resources if r.get("name") == "SeedStash"), None)
    if not seeds:
        log_and_display(get_message("plant", "no_seedstash"), turns_elapsed)
        return False, None, None, resources

    seed_msg = f"AVAILABLE SEEDS:  Apple: {seeds.get('apple', 0)}  Cabbage: {seeds.get('cabbage', 0)}  Potato: {seeds.get('potato', 0)}"

    # Hydroponics + free beds
    hydro = next((r for r in resources if r.get("name") == "HydroponicsRoom"), None)
    if not hydro:
        log_and_display(get_message("plant", "no_hydro"), turns_elapsed)
        return False, None, None, resources

    beds = hydro.get("beds", [])
    available_beds = [b for b in beds if not b["occupied"] and not b["reserved"]]
    free_beds = len(available_beds)

    if free_beds == 0:
        log_and_display(get_message("plant", "no_beds"), turns_elapsed)
        return False, None, None, resources

    free_beds_msg = f"FREE BEDS AVAILABLE FOR PLANTING: {free_beds}"

    # 3. Display summary and prompt
    full_planting_msg = "\n".join(
        crop_lines + [seeds_per_bed_msg, seed_msg, free_beds_msg] + food_lines
    )
    log_and_display(full_planting_msg, turns_elapsed)

    crops_requested = []
    num_beds_needed = 0

    if free_beds >= 3:
        response = get_input("input", "plant_default", turns_elapsed)
        if response.lower() in ["y", "yes"]:
            plant_options.append("default")

    if not plant_options:
        try:
            num_beds_needed = int(get_input("input", "plant_how_many", turns_elapsed, available=free_beds))
        except ValueError:
            log_and_display(get_message("plant", "invalid_response", free_beds=free_beds), turns_elapsed)
            return False, None, None, resources

        if num_beds_needed == 0:   # They wish to abort
            return False, None, None, resources

        if num_beds_needed < 0 or num_beds_needed > free_beds:
            log_and_display(get_message("plant", "invalid_response", free_beds=free_beds), turns_elapsed)
            return False, None, None, resources

        crops_requested = get_input("input", "plant_which_crop", turns_elapsed).lower().split()
        if crops_requested == {} or crops_requested == "":
            log_and_display(get_message("plant", "unknown_crop", crop=crop), turns_elapsed)
            return False, worker_name, None, resources
        
        for crop in crops_requested:
            if crop == "" or crop not in VALID_CROPS:
                log_and_display(get_message("plant", "unknown_crop", crop=crop), turns_elapsed)
                return False, worker_name, None, resources

    # 4. Build planting instructions
    if plant_options and plant_options[0] == "default":
        crops_requested = VALID_CROPS[:]
        num_beds_needed = 3

    beds_to_reserve = available_beds[:num_beds_needed]
    for bed in beds_to_reserve:
        bed["reserved"] = True
        bed["reserved_by"] = worker_name

    planting_orders = []
    beds_per_crop = num_beds_needed // len(crops_requested)
    extra = num_beds_needed % len(crops_requested)

    bed_index = 0
    for crop in crops_requested:
        beds_for_this_crop = beds_to_reserve[bed_index: bed_index + beds_per_crop]
        bed_index += beds_per_crop
        planting_orders.append({
            "crop": crop,
            "beds": beds_for_this_crop
        })

    # Distribute any leftover beds
    if extra > 0:
        for i in range(extra):
            planting_orders[i % len(planting_orders)]["beds"].append(beds_to_reserve[bed_index])
            bed_index += 1

    instructions = {
        "worker": worker_name,
        "orders": planting_orders
    }

    return True, worker_name, instructions, resources