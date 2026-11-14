# Configuration Editor (CE)

from ast import While
from importlib import resources
import json
from pathlib import Path


CROPS = ("potato", "onion", "apple", "avocado")

SHIELD_FLAGS = (
    "shield_found",
    "manual_decoded",
    "ancient_droid_valid",
    "crystal_combo_valid",
    "shield_connected",
    "shield_active",
)


def find_resource(config, name):
    resources = config.get("resources", [])

    if not isinstance(resources, list):
        return None

    return next(
        (res for res in resources
         if res.get("name") == name),
        None
    )


def ask_nonnegative_integer(prompt):
    while True:
        answer = input(prompt).strip()

        if answer == "0" or answer.isdecimal():
            return int(answer)

        if answer.lower() == "x":
            return None

        print("Enter a non-negative integer, or X to cancel.")


def edit_counters(config):
    counters = config.get("counters", {})

    while True:
        print("\nCOUNTERS")
        names = list(counters.keys())

        for i, name in enumerate(names, 1):
            print(f"{i}. {name}: {counters[name]}")

        choice = input("Counter number (0 to return): ").strip()

        if choice == "0":
            return

        if not choice.isdecimal() or not 1 <= int(choice) <= len(names):
            print("Invalid selection.")
            continue

        name = names[int(choice) - 1]

        value = ask_nonnegative_integer(
            f"New value for {name} (X to cancel): "
        )

        if value is not None:
            counters[name] = value
            print(f"{name} updated to {value}.")


def edit_seeds(config):
    stash = find_resource(config, "SeedStash")

    if stash is None:
        print("SeedStash not present in this configuration.")
        return

    while True:
        print("\nSEED STASH")

        for i, crop in enumerate(CROPS, 1):
            print(f"{i}. {crop}: {stash.get(crop, 0)}")

        choice = input("Crop number (0 to return): ").strip()

        if choice == "0":
            return

        if not choice.isdecimal() or not 1 <= int(choice) <= 4:
            print("Invalid selection.")
            continue

        crop = CROPS[int(choice) - 1]

        value = ask_nonnegative_integer(
            f"New {crop} seed count (X to cancel): "
        )

        if value is not None:
            stash[crop] = value
            print(f"{crop} seeds updated to {value}.")


def edit_shieldstate(config):
    shieldstate = config.get("shieldstate", {})

    while True:
        print("\nSHIELD STATE")

        for i, flag in enumerate(SHIELD_FLAGS, 1):
            print(f"{i}. {flag}: {shieldstate.get(flag, False)}")

        choice = input("Flag number (0 to return): ").strip()

        if choice == "0":
            return

        if not choice.isdecimal() or not 1 <= int(choice) <= len(SHIELD_FLAGS):
            print("Invalid selection.")
            continue

        flag = SHIELD_FLAGS[int(choice) - 1]

        answer = input(
            f"Set {flag} (1=True, 0=False, X=cancel): "
        ).strip().lower()

        if answer in ("0", "1"):
            shieldstate[flag] = (answer == "1")
            print(f"{flag} = {shieldstate[flag]}")
        elif answer != "x":
            print("Invalid value.")


def show_summary(config):
    print("\nCONFIGURATION SUMMARY")
    print("=====================")

    counters = config.get("counters", {})
    print(f"Turn: {counters.get('turns', 0)}")
    print(f"Active tasks: {len(config.get('tasks', {}))}")
    print(f"Growing crops: {len(config.get('crops', {}))}")

    stash = find_resource(config, "SeedStash")

    if stash:
        total_seeds = sum(
            stash.get(crop, 0) for crop in CROPS
        )
        print(f"Available seeds: {total_seeds}")

    resources = config.get("resources", [])
    found = [
        res["name"] for res in resources
        if res.get("found", False)
    ]

    print(f"Discovered resources: {len(found)}")
    print(", ".join(found) if found else "None")

    print(
        "Shield active:",
        config.get("shieldstate", {}).get("shield_active", False)
    )


FOOD_FIELDS = (
    "rationPack",
    "potato",
    "onion",
    "apple",
    "avocado",
    "smoothie",
    "soup",
    "salad",
    "stirFry",
)


def edit_resource_amounts(config):
    """Edit stored food and total power."""

    while True:
        print("\nFOOD AND POWER")
        print("1. Edit PowerSupply amount")
        print("2. Edit FoodStore quantities")
        print("0. Return")

        choice = input("Select option: ").strip()

        if choice == "0":
            return

        if choice == "1":
            power = find_resource(config, "PowerSupply")

            if power is None:
                print("PowerSupply not found in configuration.")
                continue

            value = ask_nonnegative_integer(
                "New power amount (X to cancel): "
            )

            if value is not None:
                power["amount"] = value
                print(f"Power updated to {value}.")

        elif choice == "2":
            food_store = find_resource(config, "FoodStore")

            if food_store is None:
                print("FoodStore not found in configuration.")
                continue

            while True:
                print("\nFOODSTORE")

                for i, food in enumerate(FOOD_FIELDS, 1):
                    print(
                        f"{i}. {food}: "
                        f"{food_store.get(food, 0)}"
                    )

                selected = input(
                    "Food number (0 to return): "
                ).strip()

                if selected == "0":
                    break

                if (
                    not selected.isdecimal()
                    or not 1 <= int(selected) <= len(FOOD_FIELDS)
                ):
                    print("Invalid selection.")
                    continue

                food = FOOD_FIELDS[int(selected) - 1]

                value = ask_nonnegative_integer(
                    f"New quantity for {food} (X to cancel): "
                )

                if value is not None:
                    food_store[food] = value
                    print(f"{food} updated to {value}.")

        else:
            print("Invalid selection.")


def edit_crops(config):
    """Edit planted crops."""

    crops = config.get("crops", [])
    resources = config.get("resources", [])
    lines = [""]

    while True:
        print("CROPS EDITOR")
        print("============")

        i = 0
        while i < len(crops):
            idx = f"{i}"
            crop_type = crops[idx].get("crop_type", "Unknown").capitalize()
            bed_id = crops[idx].get("bed_id", "Unknown")["id"]
            worker = crops[idx].get("worker", "Unknown")
            turns_remaining = crops[idx].get("turns_remaining", 0)
            lines.append(f"{i+1}. {crop_type:<8} | {worker:<10} | Bed: {bed_id} | {turns_remaining} turns")
            i += 1
        for line in lines:
            print(line)


        while True:
            choice = input("Select crop (0 to exit): ").strip()
            if choice == "0":
                return

            elif not choice.isdecimal() or not 1 <= int(choice) <= len(crops):
                print("Invalid selection.")
                choice = input("Select crop (0 to exit): ").strip()
                continue

            else:
                crop_index = f"{int(choice) - 1}"
                crop = crops[crop_index]

                print("1. Change crop type")
                print("2. Change turns remaining")
                print("3. Delete crop")
                print("0. Return")

                sub_choice = input("Select option: ").strip()

                while True:
                    if sub_choice == "0":
                        return

                    elif sub_choice == "1":
                        new_type = input("Enter new crop type: ").strip().lower()
                        if new_type in CROPS:
                            crop["crop_type"] = new_type
                            print(f"Crop type updated to {new_type}.")
                        else:
                            print("Invalid crop type.")

                    elif sub_choice == "2":
                        new_turns = ask_nonnegative_integer("Enter new turns remaining: ")
                        if new_turns is not None:
                            crop["turns_remaining"] = new_turns
                            print(f"Turns remaining updated to {new_turns}.")

                    elif sub_choice == "3":
                        reserved_bed = crop.get("bed_id")
                        if reserved_bed is None:
                            print("Warning: Crop does not have a reserved bed.")
                        
                        hydro = next((r for r in resources if r.get("name") == "HydroponicsRoom"), None)
                        if hydro:
                            # Look up the live bed records by their IDs.
                            beds_by_id = {
                                bed["id"]: bed
                                for bed in hydro.get("beds", [])
                            }
                            bed_id = reserved_bed.get("id")
                            bed = beds_by_id.get(bed_id)

                            # Release the bed.
                            bed["reserved"] = False
                            bed["reserved_by"] = ""
                            bed["crop_id"] = None
                            bed["occupied"] = False
                            
                            crops.pop(crop_index)
                            print("Crop deleted.")
                            break
                        
                        else:
                            print("Warning: HydroponicsRoom not found in resources.")

                    else:
                        print("Invalid selection.")
                        sub_choice = input("Select option: ").strip()


def main():
    print("AYNSEFIAN OUTPOST CONFIG EDITOR")
    print("==============================")

    config_file = input("Enter configuration filename (with or without .json): ").strip()

    if not config_file:
        print("No filename provided. Exiting.")
        return
    elif not config_file.endswith(".json"):
        config_file += ".json"

    source = Path(config_file)
    
    if not source.is_file():
        print(f"Configuration file '{config_file}' not found.")
        return

    try:
        with source.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Unable to load configuration: {exc}")
        return

    if not isinstance(config, dict):
        print("Invalid configuration: expected a JSON object.")
        return

    while True:
        print("\nMAIN MENU")
        print("1. Edit counters")
        print("2. Edit seeds")
        print("3. Edit Shield state")
        print("4. Edit resource amounts")
        print("5. Edit crops")
        print("6. View summary")
        print("7. Save as test configuration")
        print("0. Exit")

        choice = input("Select option: ").strip()

        if choice == "1":
            edit_counters(config)
        elif choice == "2":
            edit_seeds(config)
        elif choice == "3":
            edit_shieldstate(config)
        elif choice == "4":
            edit_resource_amounts(config)
        elif choice == "5":
            edit_crops(config)
        elif choice == "6":
            show_summary(config)
        elif choice == "7":
            destination = Path(
                input("New test configuration filename: ").strip()
            )
            if destination.suffix != ".json":
                destination = destination.with_suffix(".json")

            if destination.resolve() == source.resolve():
                print("Please choose a different filename.")
                continue

            if destination.exists():
                print("Destination already exists. Choose another name.")
                continue

            try:
                with destination.open("x", encoding="utf-8") as file:
                    json.dump(config, file, indent=4)

                print(f"Saved: {destination}")

            except OSError as exc:
                print(f"Save failed: {exc}")

        elif choice == "0":
            print("Exiting Config Editor.")
            return
        else:
            print("Invalid selection.")


if __name__ == "__main__":
    main()
