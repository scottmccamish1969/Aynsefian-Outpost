# user_interface.py

import random, os
from datetime import datetime
from constants import LOG_FILE

def get_input(category, code, turns_elapsed=0, **kwargs):
    questions = {
        "input": {
            "assignee": "There is at least one assignable item. Who should be assigned? <name>",
            "assigned_item": "You can assign {name} to any of these: {full_list}. Which do you choose?",
            "assign_name": "Who shall be assigned to {item}? <name>", 
            "charge": "Which droid(s) do you want to charge? (<name(s)> or 'all')",
            "confirm_examine": [
                "Do you want them to examine it? (y/n)",
                "Examine now, or skip for later? (y/n)",
                "Go straight to examining this item, or defer for now? (y/n)",
            ],
            "endgame_choice": "Type 'reset' to begin again or 'quit' to exit.",
            "examine": "Who should examine something? <name>",
            "examine_what": "What would you like {target} to examine?\n{items}",
            "explore": "Who should explore? (<name(s)>, 'all' or 'idle')",
            "explore_found": "{target} has found **{res_name}**.  Do you want {pronoun} to examine it? (y/n)",
            "feed": "Who do you want to feed (<name(s)>, 'all', or 'hungry')?",
            "list": "You can list the following items: {can_be_listed}. Which would you like?",
            "manage": "Who would you like to manage (0 to abort)?",
            "manage_option": "Which of these would you like to do?",
            "manage_move_choice": "Enter the number of the task to move to the top of the queue",
            "manage_task_to_remove": "Enter the number of the task to remove: ",
            "mine": "Who should get out the pick and go mining? <name(s)",
            "oldterminal": "The OldTerminal accepts your access. Do you wish to use the known CrystalCombination to attempt shield calibration? (y/n)",
            "plant": "Let's plant some real food! Who are you giving the trowel and some seeds to? <name(s)",
            "plant_default": "You have at least 3 beds available, would you like the default plant (1 apple, 1 cabbage, 1 potato)? (y/n)",
            "plant_how_many": "Okay, how many beds do you wish to use (1 up to {available}, or 0 to abort)?",
            "plant_which_crop": "Which crop do you want in those beds? (apple, cabbage, potato)",
            "read": "What file are you interested in reading?  You can pick from: {files}",
            "reap": "Who do you want to do the reaping? <name>",
            "reset_confirm": "Are you absolutely, totally, completely sure you want to reset the outpost? (y/n)",
        }
    }

    entry = questions.get(category, {}).get(code)
    if isinstance(entry, list):
        entry = random.choice(entry)
    if isinstance(entry, str):
        log_and_display(entry.format(**kwargs), turns_elapsed, end="")
        return input(" > ").strip()

    log_and_display("[Input prompt not found]", turns_elapsed)
    return ""


def get_confirm(prompt, turns_elapsed, end=""):
    log_and_display(prompt, turns_elapsed, end)
    response = input(" > ").strip().lower()
    return response in ["y", "yes"]


def normalise_command(command_str):
    # Interprets and expands shorthand commands. Returns normalised command parts.
    # Examples:
    #    'e a' -> ['explore', 'all']
    #    'x' -> ['examine']
    #    'm I' -> ['mine', 'idle']

    aliases = {
        'e': 'explore',
        'x': 'examine',
        'm': 'mine',
        'f': 'feed',
        'c': 'charge',
        'r': 'reap',
        'p': 'plant',
        'l': 'list',
        'a': 'assign',
        'h': 'help',
        's': 'status',
        'n': 'next',
        'read': 'read',
        'reset': 'reset',
        'refuel': 'refuel',
        'q': 'quit',
    }

    objects = {
        'a': 'all',
        'i': 'idle',
        'h': 'hungry',
        'l': 'low',
        'r': 'resources',
        'f': 'food',
        'p': 'power'
    }

    parts = command_str.strip().split()
    if not parts:
        return []

    expanded = []
    for part in parts:
        key = part.lower()
        expanded.append(aliases.get(key, objects.get(key, key)))  # fallback to original

    return expanded

def get_command_from_player():
    raw_command = input(">> ").strip()
    return " ".join(normalise_command(raw_command))


def log_and_display(message, turn, include_time=False, end=None):
    # NEW:  just derive the day from the turn
    day = turn // 10

    #Prints a message and logs it to file with optional timestamps
    print(message, end=end)

    # Determine if file exists
    file_exists = os.path.exists(LOG_FILE)

    # Format the log entry
    log_entry = f"Day {day}, Turn {turn}: {message.strip()}\n"

    # Open in append mode
    with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
        # If it's a brand-new log file, add a header timestamp
        if not file_exists:
            log_file.write("==============================================\n")
            log_file.write(f"🕓 Log started on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write("==============================================\n\n")

        # Optional timestamp prefix per line (set include_time=True if desired)
        if include_time:
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            log_file.write(timestamp + log_entry)
        else:
            log_file.write(log_entry)