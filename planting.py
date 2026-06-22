# planting.py

import random
from command_utils import create_task, get_pronouns
from constants import SERVING_VALUE, HYDROPONICS_BED_MIN, HYDROPONICS_BED_MAX, SEED_PACKETS_USED, TASK_PLANTING, FOOD_PER_DAY, NUM_HUMANS, TASK_LENGTH
from lore.lore_ingame import get_message
import lore.user_interface as ui_runtime
from lore.user_interface import get_input, msg_plant, msg_food
from queuing import is_idle, add_to_queue
from status import display_character_summary
from utils import process_hunger_status, can_character_act


def feed_human(name, task_package):
    humans = task_package["humans"]
    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]
    return_msg = ""
    food_store = next((r for r in resources if r["name"] == "FoodStore"), None)
    is_human = name in humans
    pronouns = get_pronouns(name, is_human)

    # Check days of food left
    how_much_food = days_of_food_left(resources)

    # Open the food store
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
        return_msg = get_message("feed", "fed_ration", person_name=name, pronoun1=pronouns["p1"], pronoun2=pronouns["p1"].lower())
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

    # Again check days of food left and warn if below two days' worth
    how_much_food_now = days_of_food_left(resources)
    if how_much_food_now < 2 and how_much_food >= 2:
        msg_food(get_message("feed", "low_food_warning"), turns_elapsed, num_humans=NUM_HUMANS, tone="warn")
    
    task_package = process_hunger_status(name, task_package)
    return return_msg, task_package


def update_food_amount(resources, food_type, amount, turns_elapsed, allow_negative=False):
    # Updates the quantity of a specific food type in the FoodStore.
    # food_type (str): The type of food to update ("apple", "soup", etc.)
    # amount (float or int): Amount to add (positive) or subtract (negative).
    
    food_store = next((r for r in resources if r["name"] == "FoodStore"), None)
    if not food_store:
        msg_plant(get_message("error", "no_food_store"), turns_elapsed, tone="error")

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


def days_of_food_left(resources):
    days_left = 0

    ration = get_food_amount(resources, "rationPack")
    apple = get_food_amount(resources, "apple")
    cabbage = get_food_amount(resources, "cabbage")
    potato = get_food_amount(resources, "potato")

    days_left = (ration + apple/FOOD_PER_DAY["apple"] + cabbage/FOOD_PER_DAY["cabbage"] + potato/FOOD_PER_DAY["potato"])/NUM_HUMANS

    return days_left


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
    turns_elapsed = task_package["counters"]["turns"]

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
            msg_plant(get_message("plant", "crop_matured", planter=crop.get("worker", "Someone"), 
                                        crop_type=crop["crop_type"], bed=bed), turns_elapsed)

    return task_package


def enough_seeds(seed_type, resources):
    # Seed check
    stash = next((r for r in resources if r["name"] == "SeedStash"), None)
    return stash[seed_type] >= SEED_PACKETS_USED[seed_type]


def get_bed_by_id(hydro, bed_id):
    return next((b for b in hydro["beds"] if b["id"] == bed_id), None)


def determine_what_to_plant_and_where(raw_target, task_package):
    task_type = TASK_PLANTING

    context = {
        "raw_target": raw_target,
        "task_package": task_package,
        "from_gui_callback": False,
    }

    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    # 1. Get worker name
    if not raw_target:
        display_character_summary(humans, droids, task_type, turns_elapsed)

        if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
            context["from_gui_callback"] = True
            ui_runtime.ACTIVE_UI.set_pending_question(
                callback=resume_plant_worker_selected,
                context=context
            )

        answer = get_input("plant", "who_plants", turns_elapsed)

        if answer == ui_runtime.GUI_PENDING:
            return None

        context["raw_target"] = answer
        return continue_determine_what_to_plant_and_where(context)

    return continue_determine_what_to_plant_and_where(context)


def resume_plant_worker_selected(answer, context):
    context["raw_target"] = answer
    context["from_gui_callback"] = True
    return continue_determine_what_to_plant_and_where(context)


def continue_determine_what_to_plant_and_where(context):
    VALID_CROPS = ["apple", "cabbage", "potato"]
    task_type = TASK_PLANTING

    task_package = context["task_package"]
    raw_target = context["raw_target"]

    crops = task_package["crops"]
    resources = task_package["resources"]
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    okay_to_act, is_human, worker_name = can_character_act(raw_target, task_type, humans, droids, turns_elapsed )

    if not okay_to_act:
        return return_plant_failure(context)

    context["worker_name"] = worker_name
    context["is_human"] = is_human

    food_store = next((r for r in resources if r.get("name") == "FoodStore"), None)

    if not food_store:
        msg_plant("No FoodStore found.", turns_elapsed, tone="error")
        return return_plant_failure(context)

    food_lines = [
        "FOOD IN STORAGE:",
        f"  Ration Packs: {food_store.get('rationPack', 0)}",
        f"  Apples: {food_store.get('apple', 0)}  Cabbages: {food_store.get('cabbage', 0)}  Potatoes: {food_store.get('potato', 0)}",
        f"  Soup servings: {food_store.get('soup', 0)}  Stir Fries: {food_store.get('stirFry', 0)}  Smoothies: {food_store.get('smoothie', 0)}"
    ]

    if crops:
        crop_lines = ["CROPS:"]
        for crop in crops.values():
            bed_id = crop["bed_id"]["id"]
            crop_type = crop["crop_type"]
            crop_lines.append(f"  Bed #{bed_id}: {crop_type}")
    else:
        crop_lines = ["CROPS:  None growing"]

    seeds_per_bed_msg = (
        f"SEEDS NEEDED PER BED:  "
        f"Apple: {SEED_PACKETS_USED['apple']}  "
        f"Cabbage: {SEED_PACKETS_USED['cabbage']}  "
        f"Potato: {SEED_PACKETS_USED['potato']}"
    )

    seeds = next((r for r in resources if r.get("name") == "SeedStash"), None)

    if not seeds:
        msg_plant(get_message("plant", "no_seedstash"), turns_elapsed, tone="error")
        return return_plant_failure(context)

    seed_msg = (
        f"AVAILABLE SEEDS:  "
        f"Apple: {seeds.get('apple', 0)}  "
        f"Cabbage: {seeds.get('cabbage', 0)}  "
        f"Potato: {seeds.get('potato', 0)}"
    )

    hydro = next((r for r in resources if r.get("name") == "HydroponicsRoom"), None)

    if not hydro:
        msg_plant(get_message("plant", "no_hydro"), turns_elapsed, tone="error")
        return return_plant_failure(context)

    beds = hydro.get("beds", [])
    available_beds = [b for b in beds if not b["occupied"] and not b["reserved"]]
    free_beds = len(available_beds)

    if free_beds == 0:
        msg_plant(get_message("plant", "no_beds"), turns_elapsed, tone="warn")
        return return_plant_failure(context)

    free_beds_msg = f"FREE BEDS AVAILABLE FOR PLANTING: {free_beds}"

    full_planting_msg = "\n".join(crop_lines + [seeds_per_bed_msg, seed_msg, free_beds_msg] + food_lines)

    msg_plant(full_planting_msg, turns_elapsed, tone="success")

    context["VALID_CROPS"] = VALID_CROPS
    context["available_beds"] = available_beds
    context["free_beds"] = free_beds

    if free_beds >= 3:
        if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
            context["from_gui_callback"] = True
            ui_runtime.ACTIVE_UI.set_pending_question(
                callback=resume_plant_default,
                context=context
            )

        response = get_input("plant", "default", turns_elapsed)

        if response == ui_runtime.GUI_PENDING:
            return None

        return resume_plant_default(response, context)

    return ask_plant_how_many(context)


def return_plant_failure(context):
    task_package = context["task_package"]

    if context.get("from_gui_callback", False):
        return task_package

    return None


def resume_plant_default(answer, context):
    answer = str(answer).strip().lower() if answer else ""

    if answer in ("y", "yes"):
        context["crops_requested"] = context["VALID_CROPS"][:]
        context["num_beds_needed"] = 3
        return finish_planting_selection(context)

    return ask_plant_how_many(context)


def ask_plant_how_many(context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]
    free_beds = context["free_beds"]

    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        context["from_gui_callback"] = True
        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=resume_plant_how_many,
            context=context
        )

    response = get_input("plant", "how_many", turns_elapsed, available=free_beds)

    if response == ui_runtime.GUI_PENDING:
        return None

    return resume_plant_how_many(response, context)


def resume_plant_how_many(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]
    free_beds = context["free_beds"]
    name = context["worker_name"]
    humans = task_package["humans"]
    is_human = name in humans

    try:
        num_beds_needed = int(answer)
    except (TypeError, ValueError):
        msg_plant(get_message("plant", "invalid_response", free_beds=free_beds), turns_elapsed, tone="error")
        return return_plant_failure(context)

    if num_beds_needed == 0:
        context["from_gui_callback"] = False
        is_are = "are" if not is_human else "is"
        pronoun = get_pronouns(name, is_human)['p1']
        msg_plant(get_message("plant", "aborted", target=name, pronoun=pronoun, is_are=is_are), turns_elapsed, tone="error")
        return return_plant_failure(context)

    if num_beds_needed < 0 or num_beds_needed > free_beds:
        msg_plant(get_message("plant", "invalid_response", free_beds=free_beds), turns_elapsed, tone="error")
        return return_plant_failure(context)

    context["num_beds_needed"] = num_beds_needed

    return ask_plant_which_crop(context)


def ask_plant_which_crop(context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        context["from_gui_callback"] = True
        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=resume_plant_which_crop,
            context=context
        )

    response = get_input("plant", "which_crop", turns_elapsed)

    if response == ui_runtime.GUI_PENDING:
        return None

    return resume_plant_which_crop(response, context)


def resume_plant_which_crop(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]
    worker_name = context["worker_name"]
    VALID_CROPS = context["VALID_CROPS"]

    if not answer:
        msg_plant(get_message("plant", "unknown_crop", crop=""), turns_elapsed, tone="error")
        return return_plant_failure(context)

    crops_requested = str(answer).lower().split()

    if not crops_requested:
        msg_plant(get_message("plant", "unknown_crop", crop=""), turns_elapsed, tone="error")
        return return_plant_failure(context)

    for crop in crops_requested:
        if crop not in VALID_CROPS:
            msg_plant(get_message("plant", "unknown_crop", crop=crop), turns_elapsed, tone="error" )
            return return_plant_failure(context)

    context["crops_requested"] = crops_requested

    return finish_planting_selection(context)


def finish_planting_selection(context):
    task_package = context["task_package"]

    worker_name, crop_instructions, task_package = build_planting_instructions(context)

    if context.get("from_gui_callback", False):
        valid_command, task_package = finish_initiate_plant_task(
            name=worker_name,
            crop_instructions=crop_instructions,
            task_package=task_package,
            queued_task=False
        )
        return task_package

    return True, worker_name, crop_instructions, task_package


def build_planting_instructions(context):
    task_package = context["task_package"]
    worker_name = context["worker_name"]
    available_beds = context["available_beds"]
    crops_requested = context["crops_requested"]
    num_beds_needed = context["num_beds_needed"]

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

    if extra > 0:
        for i in range(extra):
            planting_orders[i % len(planting_orders)]["beds"].append(
                beds_to_reserve[bed_index]
            )
            bed_index += 1

    instructions = {
        "worker": worker_name,
        "orders": planting_orders
    }

    return worker_name, instructions, task_package


def finish_initiate_plant_task(name, crop_instructions, task_package, queued_task=False):
    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]
    task_type = TASK_PLANTING
    valid_command = True
    
    # --- Inline functions ported from commands.py to avoid circular references ---
    def set_task_length(task_type):
        low, high = TASK_LENGTH[task_type]
        return random.randint(low, high)

    task_package["task_data"] = crop_instructions

    is_human = name in humans
    duration = set_task_length("plant_human") if is_human else set_task_length("plant_droid")

    # If they are not idle, and this was not a queued task, add this action to their queue
    if not is_idle(name, humans, droids) and not queued_task:
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, task_type, task_data=crop_instructions )
        return valid_command, task_package

    return_msg, task_package = create_task(name, task_type, duration, task_package)
    msg_plant(return_msg, turns_elapsed)

    # Now that the task has been created, we can clear the task_data in task_package 
    # because this data is now in the task
    task_package["task_data"] = {}

    return valid_command, task_package