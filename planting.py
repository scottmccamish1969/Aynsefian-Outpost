# planting.py

from multiprocessing import context
import random
import math
from unicodedata import name
from command_utils import create_task, get_pronouns
from constants import (FOOD_PER_DAY, HYDROPONICS_BED_MIN, HYDROPONICS_BED_MAX, SEED_PACKETS_USED, TASK_PLANTING, ONE_DAY_HUNGRY, NUM_HUMANS, 
                       TASK_LENGTH, CommandOutcome)
from events import add_turn_event, join_naturally, lowercase_first_minus_period
from lore.lore_ingame import get_message
import lore.user_interface as ui_runtime
from lore.user_interface import get_input, msg_plant, msg_food
from queuing import is_idle, add_to_queue
from status import display_character_summary
from utils import process_hunger_status, can_character_act, days_of_food_left, can_provide_a_meal


def select_and_reserve_meal(name, multiplier, hunger_reduction, task_package):
    """
    Select and reserve a raw-food meal for a human.

    Priority:
        1. Standard four-crop meal
        2. Three-crop alternatives
        3. Two-crop alternatives
        4. Single-crop meals
        5. Best available partial meal, supplemented by ration packs

    Ingredients are deducted from FoodStore immediately,
    reserving them for the eating task.

    The caller remains responsible for returning reserved food
    if the task is cancelled before consumption.
    """

    resources = task_package["resources"]
    turns_elapsed = task_package["counters"]["turns"]

    food_store = next((r for r in resources if r["name"] == "FoodStore"), None)
    task_data = {}
    nutrition_target = math.ceil(ONE_DAY_HUNGRY * multiplier)
    meal_type = "emergency" if multiplier > 1 else "normal"

    CROPS = ("potato", "onion", "apple", "avocado")

    # ---------------------------------------------------
    # 1) Check FoodStore
    # ---------------------------------------------------

    if not food_store:
        msg_food(get_message("feed", "no_foodstore"), turns_elapsed, tone="error")
        return {}, task_package

    how_much_food = days_of_food_left(resources)

    available = {
        item: food_store.get(item, 0)
        for item in CROPS
    }

    available["rationPack"] = food_store.get("rationPack", 0)

    served = {
        item: 0
        for item in (*CROPS, "rationPack")
    }

    # ---------------------------------------------------
    # 2) Nutrition calculation
    #
    # FOOD_PER_DAY defines how many of each crop
    # provide ONE_DAY_HUNGRY nutrition points.
    # ---------------------------------------------------

    def nutrition_per_item(item):
        return ONE_DAY_HUNGRY / FOOD_PER_DAY[item]

    def calculate_nutrition(items):
        return sum(
            qty * nutrition_per_item(item)
            for item, qty in items.items()
            if item in CROPS
        ) + items.get("rationPack", 0) * ONE_DAY_HUNGRY

    # ---------------------------------------------------
    # 3) Preferred meal combinations
    #
    # Each dictionary describes one normal raw meal.
    # Emergency meals scale the quantities by multiplier.
    #
    # Order matters: standard first, then alternatives.
    # ---------------------------------------------------

    MEAL_COMBINATIONS = [

        # Standard four-crop meal
        {"apple": 2, "onion": 1,
         "potato": 1, "avocado": 1},

        # Three crops: one crop missing
        {"onion": 1, "potato": 2, "avocado": 1},
        {"apple": 2, "potato": 2, "avocado": 1},
        {"apple": 2, "onion": 2, "avocado": 1},
        {"apple": 2, "onion": 2, "potato": 1},

        # Two crops: two crops missing
        {"potato": 2, "avocado": 2},
        {"onion": 2, "avocado": 2},
        {"onion": 2, "potato": 3},
        {"apple": 4, "avocado": 2},
        {"apple": 4, "potato": 2},
        {"apple": 5, "onion": 2},

        # Single-crop meals
        {"apple": 8},
        {"onion": 5},
        {"potato": 4},
        {"avocado": 3},
    ]

    # ---------------------------------------------------
    # 4) Find the first available full meal
    # ---------------------------------------------------

    full_meal_found = False

    for combination in MEAL_COMBINATIONS:

        required = {
            item: math.ceil(qty * multiplier)
            for item, qty in combination.items()
        }

        if all(
            available[item] >= qty
            for item, qty in required.items()
        ):
            served.update(required)
            full_meal_found = True
            break

    # ---------------------------------------------------
    # 5) No predefined full meal available
    #
    # Build a meal from remaining fresh produce,
    # then supplement with ration packs if needed.
    # ---------------------------------------------------

    if not full_meal_found:

        nutrition_remaining = float(nutrition_target)

        # Consume available fresh produce first.
        for item in CROPS:

            if nutrition_remaining <= 0:
                break

            quantity_available = available[item]

            if quantity_available <= 0:
                continue

            value_per_item = nutrition_per_item(item)

            quantity_needed = math.ceil(
                max(0, nutrition_remaining - 1e-9)
                / value_per_item
            )

            quantity_to_serve = min(
                quantity_available,
                quantity_needed
            )

            served[item] = quantity_to_serve

            nutrition_remaining -= (
                quantity_to_serve * value_per_item
            )

        # Supplement with ration packs if necessary.
        if (
            nutrition_remaining > 1e-9
            and available["rationPack"] > 0
        ):
            ration_packs_needed = math.ceil(
                (nutrition_remaining - 1e-9)
                / ONE_DAY_HUNGRY
            )

            served["rationPack"] = min(
                available["rationPack"],
                ration_packs_needed
            )

    # ---------------------------------------------------
    # 6) Calculate actual nutrition
    # ---------------------------------------------------

    total_nutrition = calculate_nutrition(served)

    if total_nutrition <= 0:
        msg_food(get_message("feed", "food_all_used_up", person_name=name), turns_elapsed, tone="error")

        event_priority = 1
        task_package = add_turn_event(task_package, "eat", event_priority, name=name, result="no_more_food")
        return {}, task_package

    # Never reduce hunger by more than the target.
    # Use whole hunger points, without rounding up
    # nutrition that has not actually been consumed.
    actual_hunger_reduction = min(
        nutrition_target,
        math.floor(total_nutrition + 1e-9)
    )

    if actual_hunger_reduction < nutrition_target:
        meal_type = "partial"

    # ---------------------------------------------------
    # 7) Verify available quantities before reserving
    # ---------------------------------------------------

    for item, qty in served.items():

        if qty > available[item]:
            msg_food(get_message("feed", "food_all_used_up", person_name=name), turns_elapsed, tone="error")

            event_priority = 1
            task_package = add_turn_event(task_package, "eat", event_priority, name=name, result="no_more_food")
            return {}, task_package

    # ---------------------------------------------------
    # 8) Reserve the food
    # ---------------------------------------------------

    for item, qty in served.items():
        if qty > 0:
            food_store[item] = food_store.get(item, 0) - qty

    # ---------------------------------------------------
    # 9) Warn if the last ration pack was reserved
    # ---------------------------------------------------

    if (served["rationPack"] > 0 and food_store.get("rationPack", 0) == 0):

        msg_food(get_message("feed", "last_ration", person_name=name), turns_elapsed, tone="warn")

        event_priority = 2
        task_package = add_turn_event(task_package, "eat", event_priority, name=name, result="last_ration")

    # ---------------------------------------------------
    # 10) Build task data
    # ---------------------------------------------------

    task_data = {
        "food_items": served.copy(),
        "hunger_reduction": actual_hunger_reduction,
        "meal_type": meal_type
    }

    # ---------------------------------------------------
    # 11) Check for low food supply
    # ---------------------------------------------------

    how_much_food_now = days_of_food_left(resources)

    if how_much_food_now < 2 and how_much_food >= 2:

        msg_food(get_message("feed", "low_food_warning", num_humans=NUM_HUMANS), turns_elapsed, tone="warn")

        event_priority = 3
        task_package = add_turn_event(task_package, "eat", event_priority, name=name, result="low_food")

    return task_data, task_package



def adjust_human_hunger(name, task_data, task_package):
    humans = task_package["humans"]

    food_items = task_data.get("food_items", {})
    hunger_reduction = task_data.get("hunger_reduction", 10)

    message = f"{name} was fed: "
    message += ", ".join(f"{quantity} {item} servings" for item, quantity in food_items.items() if quantity > 0)

    humans[name]["hunger"] = max(0, humans[name]["hunger"] - hunger_reduction)

    task_package = process_hunger_status(name, task_package)

    return message, task_package


def return_reserved_meal(task_data, task_package):
    resources = task_package["resources"]
    food_store = next((r for r in resources if r["name"] == "FoodStore"), None)

    if not food_store:
        return task_package

    for item, quantity in task_data.get("food_items", {}).items():
        food_store[item] = food_store.get(item, 0) + quantity

    return task_package


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

            # Add an event for this
            event_priority = 6
            task_package = add_turn_event(task_package, "reap", event_priority, name=name, result="mature_crop", crop_type=crop["crop_type"], bed=bed)

    return task_package


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
                context=context,
                resume_turn = False
            )

        answer = get_input("plant", "who_plants", turns_elapsed)

        if answer == ui_runtime.GUI_PENDING:
            return CommandOutcome.AWAITING_INPUT, task_package

        context["raw_target"] = answer
        return continue_determine_what_to_plant_and_where(context)

    return continue_determine_what_to_plant_and_where(context)


def resume_plant_worker_selected(answer, context):
    context["raw_target"] = answer
    context["from_gui_callback"] = True
    return continue_determine_what_to_plant_and_where(context)


def continue_determine_what_to_plant_and_where(context):
    VALID_CROPS = ["potato", "onion", "apple", "avocado", ]

    task_package = context["task_package"]
    raw_target = context["raw_target"]

    crops = task_package["crops"]
    resources = task_package["resources"]
    humans = task_package["humans"]
    turns_elapsed = task_package["counters"]["turns"]

    okay_to_act, task_package = can_character_act(raw_target, TASK_PLANTING, task_package)
    if not okay_to_act:
        return return_plant_failure(context)

    context["worker_name"] = raw_target
    context["is_human"] = raw_target in humans

    food_store = next((r for r in resources if r.get("name") == "FoodStore"), None)

    if not food_store:
        msg_plant("No FoodStore found.", turns_elapsed, tone="error")
        return return_plant_failure(context)

    food_lines = [
        "FOOD IN STORAGE:",
        f"  Ration Packs: {food_store.get('rationPack', 0)}",
        f"  Potatoes: {food_store.get('potato', 0)}  Onions: {food_store.get('onion', 0)}  Apples: {food_store.get('apple', 0)}  Avocado: {food_store.get('avocado', 0)}  ",
        f"  Smoothies: {food_store.get('smoothie', 0)}  Soup Servings: {food_store.get('soup', 0)}  Salads: {food_store.get('salad', 0)}  Stir Fries: {food_store.get('stirFry', 0)}  "
    ]

    if crops:
        crop_lines = ["CROPS:"]
        for crop in crops.values():
            bed_id = crop["bed_id"]["id"]
            crop_type = crop["crop_type"]
            crop_lines.append(f"  Bed #{bed_id}: {crop_type}")
    else:
        crop_lines = ["CROPS:  None growing"]

    seeds_per_bed_msg = f"SEEDS NEEDED PER BED:  10 each (per crop)"

    seeds = next((r for r in resources if r.get("name") == "SeedStash"), None)

    if not seeds:
        msg_plant(get_message("plant", "no_seedstash"), turns_elapsed, tone="error")
        return return_plant_failure(context)

    seed_msg = (
        f"AVAILABLE SEEDS:  "
        f"Potato: {seeds.get('potato', 0)}  "
        f"Onion: {seeds.get('onion', 0)}  "
        f"Apple: {seeds.get('apple', 0)}  "
        f"Avocado: {seeds.get('avocado', 0)}  "
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

    return ask_plant_how_many(context)


def return_plant_failure(context):
    task_package = context["task_package"]

    if context.get("from_gui_callback", False):
        return CommandOutcome.CANNOT_EXECUTE, task_package

    return CommandOutcome.CANNOT_EXECUTE, task_package


def ask_plant_how_many(context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]
    free_beds = context["free_beds"]

    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        context["from_gui_callback"] = True
        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=resume_plant_how_many,
            context=context,
            resume_turn = False
        )

    response = get_input("plant", "how_many", turns_elapsed, available=free_beds)

    if response == ui_runtime.GUI_PENDING:
        return CommandOutcome.AWAITING_INPUT, task_package

    return resume_plant_how_many(response, context)


def resume_plant_how_many(answer, context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]
    free_beds = context["free_beds"]
    name = context["worker_name"]
    humans = task_package["humans"]
    is_human = name in humans

    context["name"] = name

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

    # Start a fresh list of crop choices.
    # Each entry represents one bed to be planted.
    context["num_beds_needed"] = num_beds_needed
    context["crops_requested"] = []
    context["planting_choices"] = []

    # Ask for the first crop.
    return ask_plant_which_crop(context)


def ask_plant_which_crop(context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    crops_requested = context["crops_requested"]
    num_beds_needed = context["num_beds_needed"]

    # Number of beds already assigned a crop.
    beds_selected = len(crops_requested)

    # All beds now have crops assigned.
    if beds_selected >= num_beds_needed:
        return finish_planting_selection(context)

    # Next bed to be assigned.
    bed_number = beds_selected + 1

    # Set up GUI callback.
    if ui_runtime.UI_MODE == "gui" and ui_runtime.ACTIVE_UI is not None:
        context["from_gui_callback"] = True

        ui_runtime.ACTIVE_UI.set_pending_question(
            callback=resume_plant_which_crop,
            context=context,
            resume_turn=False
        )

    # Ask which crop to plant in this bed.
    response = get_input("plant", "which_crop", turns_elapsed, bed_number=bed_number, num_beds=num_beds_needed)

    if response == ui_runtime.GUI_PENDING:
        return CommandOutcome.AWAITING_INPUT, task_package

    return resume_plant_which_crop(response, context)


def resume_plant_which_crop(answer, context):
    task_package = context["task_package"]
    humans = task_package["humans"]
    turns_elapsed = task_package["counters"]["turns"]

    valid_crops = context["VALID_CROPS"]
    crops_requested = context["crops_requested"]
    planting_choices = context["planting_choices"]
    num_beds_needed = context["num_beds_needed"]
    name = context["name"]
    is_human = name in humans

    crop = str(answer).strip().lower() if answer is not None else ""

    # ---------------------------------------------------
    # 1. Allow the player to abort.
    # ---------------------------------------------------

    if crop == "0":
        is_are = "are" if not is_human else "is"
        pronoun = get_pronouns(name, is_human)['p1']
        msg_plant(get_message("plant", "aborted", target=name, pronoun=pronoun, is_are=is_are), turns_elapsed, tone="error")
        return return_plant_failure(context)

    # ---------------------------------------------------
    # 2. Validate crop.
    # ---------------------------------------------------

    if crop not in valid_crops:
        msg_plant(get_message("plant", "unknown_crop", crop=crop), turns_elapsed, tone="error")

        # Re-ask instead of abandoning the whole plan.
        return ask_plant_which_crop(context)

    # ---------------------------------------------------
    # 3. Check how many seeds can be used.
    # ---------------------------------------------------

    seeds_to_plant = check_seeds_for_planting(crop, context)
    if seeds_to_plant == 0:
        msg_plant(get_message("plant", "not_enough_seeds_left_choose_another", crop=crop), turns_elapsed, tone="warn")

        return ask_plant_which_crop(context)

    # ---------------------------------------------------
    # 4. Accept crop selection.
    # ---------------------------------------------------

    crops_requested.append(crop)

    planting_choices.append({
        "crop": crop,
        "seeds": seeds_to_plant
    })

    # ---------------------------------------------------
    # 5. Notify player about a partial crop.
    # ---------------------------------------------------

    if seeds_to_plant < SEED_PACKETS_USED:
        msg_plant(get_message("plant", "partial_crop", name=context["worker_name"], crop=crop, seeds_to_plant=seeds_to_plant), turns_elapsed, tone="warn")

    # ---------------------------------------------------
    # 6. Continue or finish.
    # ---------------------------------------------------

    if len(planting_choices) < num_beds_needed:
        return ask_plant_which_crop(context)

    return finish_planting_selection(context)



def finish_planting_selection(context):
    task_package = context["task_package"]
    outcome = CommandOutcome.SUCCESS

    worker_name, crop_instructions, task_package = build_planting_instructions(context)

    if context.get("from_gui_callback", False):
        outcome, task_package = finish_initiate_plant_task(
            name=worker_name,
            crop_instructions=crop_instructions,
            task_package=task_package,
            queued_task=False
        )
        return outcome, task_package

    return outcome, task_package


def finish_planting_selection(context):
    task_package = context["task_package"]
    turns_elapsed = task_package["counters"]["turns"]

    worker_name, crop_instructions, task_package = build_planting_instructions(context)
    if crop_instructions is None:
        msg_plant(get_message("plant", "cant_reserve"), turns_elapsed, tone="error")
        return CommandOutcome.CANNOT_EXECUTE, task_package

    if context.get("from_gui_callback", False):
        return finish_initiate_plant_task(
            name=worker_name,
            crop_instructions=crop_instructions,
            task_package=task_package,
            queued_task=False
        )

    return CommandOutcome.SUCCESS, task_package



def build_planting_instructions(context):
    task_package = context["task_package"]
    worker_name = context["worker_name"]

    available_beds = context["available_beds"]
    planting_choices = context["planting_choices"]
    num_beds_needed = context["num_beds_needed"]

    resources = task_package["resources"]

    stash = next((r for r in resources if r.get("name") == "SeedStash"), None)
    if stash is None:
        return worker_name, None, task_package

    beds_to_reserve = available_beds[:num_beds_needed]

    # ---------------------------------------------------
    # 1. Verify the entire plan before changing state.
    # ---------------------------------------------------

    if len(planting_choices) != num_beds_needed:
        return worker_name, None, task_package

    if len(beds_to_reserve) != num_beds_needed:
        return worker_name, None, task_package

    if any(
        bed.get("occupied") or bed.get("reserved")
        for bed in beds_to_reserve
    ):
        return worker_name, None, task_package

    seeds_needed = {}

    for choice in planting_choices:
        crop = choice["crop"]
        qty = choice["seeds"]

        if qty <= 0 or qty > SEED_PACKETS_USED:
            return worker_name, None, task_package

        seeds_needed[crop] = (
            seeds_needed.get(crop, 0) + qty
        )

    # Confirm enough seeds still exist.
    for crop, qty in seeds_needed.items():
        if stash.get(crop, 0) < qty:
            return worker_name, None, task_package

    # ---------------------------------------------------
    # 2. Commit seed reservations.
    # ---------------------------------------------------

    for crop, qty in seeds_needed.items():
        stash[crop] -= qty

    # ---------------------------------------------------
    # 3. Reserve beds and record seed allocations.
    # ---------------------------------------------------

    planting_orders = []

    for bed, choice in zip(
        beds_to_reserve,
        planting_choices
    ):
        bed["reserved"] = True
        bed["reserved_by"] = worker_name

        planting_orders.append({
            "crop": choice["crop"],
            "beds": [bed],
            "seeds": choice["seeds"]
        })

    instructions = {
        "worker": worker_name,
        "orders": planting_orders
    }

    return worker_name, instructions, task_package



def check_seeds_for_planting(crop, context):
    """
    Return how many seeds can be allocated to the next bed.

    Accounts for crop choices already made in this
    planting selection, without deducting seeds yet.
    """
    task_package = context["task_package"]
    resources = task_package["resources"]

    stash = next((r for r in resources if r.get("name") == "SeedStash"), None)
    if stash is None:
        return 0

    # Seeds already promised to earlier beds.
    already_allocated = sum(
        choice["seeds"]
        for choice in context.get("planting_choices", [])
        if choice["crop"] == crop
    )

    remaining = max(0, stash.get(crop, 0) - already_allocated)

    # A bed can use up to ten seeds,
    # but a partial crop is permitted.
    return min(remaining, SEED_PACKETS_USED)



def finish_initiate_plant_task(name, crop_instructions, task_package, queued_task=False):

    humans = task_package["humans"]
    droids = task_package["droids"]
    turns_elapsed = task_package["counters"]["turns"]

    is_human = name in humans

    # ---------------------------------------------------
    # Calculate planting duration from the number of beds.
    #
    # Humans: 2 turns per bed
    # Droids: 3 turns per bed
    # ---------------------------------------------------

    num_beds = sum(
        len(order.get("beds", []))
        for order in crop_instructions.get("orders", [])
    )

    if num_beds == 0:
        msg_plant("No beds were selected for planting.", turns_elapsed, tone="error")
        return CommandOutcome.CANNOT_EXECUTE, task_package

    turns_per_bed = 2 if is_human else 3
    duration = num_beds * turns_per_bed

    # ---------------------------------------------------
    # Queue the task if the character is already busy.
    # ---------------------------------------------------

    if not is_idle(name, humans, droids) and not queued_task:
        humans, droids = add_to_queue(name, humans, droids, turns_elapsed, TASK_PLANTING, task_data=crop_instructions)

        return CommandOutcome.SUCCESS, task_package

    # ---------------------------------------------------
    # Start the planting task.
    # ---------------------------------------------------

    return_msg, task_package = create_task(name, TASK_PLANTING, duration, task_package, task_data=crop_instructions)

    msg_plant(return_msg, turns_elapsed)

    # ---------------------------------------------------
    # Record the planting event.
    # ---------------------------------------------------

    item_priority = 5
    crop_message = build_crop_message(crop_instructions, stage="start")
    task_package = add_turn_event(task_package, "plant", item_priority, name=name, result="started", crop_message=crop_message)

    return CommandOutcome.SUCCESS, task_package


def build_crop_message(task_data, stage="start"):
    crop_order = ["potato", "onion", "apple", "avocado"]

    number_words = {
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
    }

    # Count how many beds are being planted with each crop
    crop_counts = {
        "potato": 0,
        "onion": 0,
        "apple": 0,
        "avocado": 0,
    }

    for order in task_data.get("orders", []):
        crop = order.get("crop")

        if crop in crop_counts:
            crop_counts[crop] += len(order.get("beds", []))

    # Remove crops that are not being planted
    active_crops = [
        crop for crop in crop_order
        if crop_counts[crop] > 0
    ]

    if not active_crops:
        return "no crops"

    total_crops = sum(crop_counts.values())

    # ---------------------------------------------------------
    # COMMENCING PLANTING
    # ---------------------------------------------------------
    if stage == "start":

        # One single crop
        if total_crops == 1:
            crop = active_crops[0]

            if crop == "apple":
                return "an apple crop"

            return f"a {crop} crop"

        # One of each crop
        if (
            active_crops == [ "potato", "onion", "apple", "avocado"]
            and all(crop_counts[crop] == 1 for crop in active_crops)
        ):
            return "these four crops: potato, onion, apple, and avocado"

        # Everything else
        parts = []

        for crop in active_crops:
            count = crop_counts[crop]
            number = number_words.get(count, str(count))

            crop_word = "crop" if count == 1 else "crops"

            parts.append(
                f"{number} {crop} {crop_word}"
            )

        return lowercase_first_minus_period(join_naturally(parts))

    # ---------------------------------------------------------
    # COMPLETED PLANTING
    # ---------------------------------------------------------
    if stage == "complete":

        # Only one crop planted in total
        if total_crops == 1:
            return f"{active_crops[0]} crop"

        # Multiple crops, but all the same type
        if len(active_crops) == 1:
            return f"{active_crops[0]} crops"

        # Multiple crop types
        return f"{join_naturally(active_crops)} crops"

    return "crops"


def return_reserved_planting(task_data, task_package):
    """
    Return seeds and release beds reserved by a cancelled
    planting task.

    Works with active or queued planting tasks.
    Only releases beds still reserved by this task's worker.
    """

    if not task_data or not task_data.get("orders"):
        return task_package

    resources = task_package["resources"]
    worker_name = task_data.get("worker", "")

    seed_stash = next((r for r in resources if r.get("name") == "SeedStash"), None)
    hydro = next((r for r in resources if r.get("name") == "HydroponicsRoom"), None)

    if seed_stash is None or hydro is None:
        return task_package

    # Look up the live bed records by their IDs.
    beds_by_id = {
        bed["id"]: bed
        for bed in hydro.get("beds", [])
    }

    for order in task_data["orders"]:
        crop = order.get("crop")
        seeds_reserved = order.get("seeds", 0)

        if crop not in ("potato", "onion", "apple", "avocado"):
            continue

        for reserved_bed in order.get("beds", []):
            bed_id = reserved_bed.get("id")
            bed = beds_by_id.get(bed_id)

            if bed is None:
                continue

            # Do not release occupied or already-free beds.
            if bed.get("occupied", False):
                continue

            if not bed.get("reserved", False):
                continue

            # Prevent releasing another worker's reservation.
            if (
                str(bed.get("reserved_by", "")).casefold()
                != worker_name.casefold()
            ):
                continue

            # Return the seeds belonging to this bed.
            seed_stash[crop] = (
                seed_stash.get(crop, 0) + seeds_reserved
            )

            # Release the bed.
            bed["reserved"] = False
            bed["reserved_by"] = ""
            bed["crop_id"] = None

    return task_package
