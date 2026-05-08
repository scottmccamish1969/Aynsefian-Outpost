# user_interface.py

import random, os

from constants import LOG_FILE
from datetime import datetime
from typing import Optional

ACTIVE_UI = None
UI_MODE = "console"
GUI_PENDING = "__GUI_PENDING__"

def get_input(category, code, turns_elapsed=0, end=None, **kwargs):
    questions = {
        "input": {
            "assign": "Who would you like to assign to an item? <name>",
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
            "list": "You can list the following items: {can_be_listed}. Which would you like? (Press enter to exit)",
            "manage": "Who would you like to manage (0 to abort)?",
            "manage_option": "Which of these would you like to do?",
            "manage_move_choice": "Enter the number of the task to move to the top of the queue",
            "manage_task_to_remove": "Enter the number of the task to remove: ",
            "mine": "Who should get out the pick and go mining? <name(s)>",
            "oldterminal": "The OldTerminal accepts your access. Do you wish to use the known CrystalCombination to attempt shield calibration? (y/n)",
            "plant": "Let's plant some real food! Who are you giving the trowel and some seeds to? <name(s)>",
            "plant_default": "You have at least 3 beds available, would you like the default plant (1 apple, 1 cabbage, 1 potato)? (y/n)",
            "plant_how_many": "Okay, how many beds do you wish to use (1 up to {available}, or 0 to abort)?",
            "plant_which_crop": "Which crop do you want in those beds? (apple, cabbage, potato)",
            "read": "What file are you interested in reading?  You can pick from: {files}",
            "reap": "Who do you want to do the reaping? <name>",
            "refuel": "Who are you sending to refuel the PowerSupply? <name>",
            "reset_confirm": "Are you absolutely, totally, completely sure you want to reset the outpost? (y/n)",
            "resume_examine": "{name} is still suggesting {pronoun1} should examine the **{item}**. Do you want {pronoun2} to? (y/n)",
            "tow_droid": "Which of these humans should be assigned to the task of towing poor {name} to the charging station? ({humans_to_tow})",
            "zero_charge": "{droid} is at zero charge. Droids are urgently needed at this outpost. Do you want to take them to the charging station right now? (y/n)",
        }
    }

    entry = questions.get(category, {}).get(code)
    if isinstance(entry, list):
        entry = random.choice(entry)

    if isinstance(entry, str):
        prompt_text = entry.format(**kwargs)
        msg_question(prompt_text, turns_elapsed, end='')

        if UI_MODE == "gui":
            return GUI_PENDING

        answer = input(" > ").strip()
        write_to_log("\n")
        return answer

    msg_error("[Input prompt not found]", turns_elapsed)
    return ""


def get_confirm(prompt, turns_elapsed, end=""):
    msg_question(prompt, turns_elapsed, end)
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


def write_to_log(log_entry, end=None):
    # Writes a ling to the log file

    # Determine if file exists
    file_exists = os.path.exists(LOG_FILE)

    # Open in append mode
    with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
        # If it's a brand-new log file, add a header timestamp
        if not file_exists:
            log_file.write("==============================================\n")
            log_file.write(f"🕓 Log started on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write("==============================================\n\n")

        log_file.write(log_entry)


# user_interface.py

from typing import Optional

# --- Emoji maps -------------------------------------------------------------

TONE_EMOJI = {
    "info": "",          # default: no extra tone marker
    "warn": "⚠️ ",
    "error": "❌ ",
    "success": "✅ ",
    "celebrate": "🎉 ",
    "panic": "🚨 ",
}

DOMAIN_EMOJI = {
    # Tone-neutral domains (the "colour" layer)
    "none": "",
    "info": "🧭 ",
    "story": "📜 ",
    "event": "🛑 ",
    "help": "ℹ️ ",

    "question": "❓ ",
    "resource": "📦 ",

    "explore": "🔎 ",
    "food": "🍏 ",
    "plant": "🌱 ",
    "power": "⚡ ",
    "mine": "⛏️ ",
    "crystal": "💎 ",
    "shield": "🛡️ ",
}


# --- Core output ------------------------------------------------------------

def emit(
    message: str,
    turn: int,
    *,
    domain: str = "none",
    tone: str = "info",
    end: str = '\n',
    log: bool = True,
    display: bool = True,
    stamp: bool = True,
) -> str:
    """
    Core output pipeline:
    - Adds emoji prefix based on domain + tone
    - Adds Day/Turn prefix ONLY for the log file
    - Prints display line (no day/turn) and/or writes log line (with day/turn)
    - Returns the *log line* (useful for tests)
    """

    # Day calculation: user-defined convention
    day = turn // 10

    # Defensive defaults
    domain_prefix = DOMAIN_EMOJI.get(domain, "")
    tone_prefix = TONE_EMOJI.get(tone, "")

    # Build the shared content (emoji + message)
    # Note: message should NOT include Day/Turn. emit() owns that.
    content = f"{tone_prefix}{domain_prefix}{message}"

    # Screen line is clean (no day/turn)
    display_line = content

    # Log line includes Day/Turn prefix
    if stamp:
        log_line = f"Day {day}, Turn {turn}: {content}"
    else:
        log_line = f" {content}"

    if display:
        print(display_line, end=end)

    if log:
        if end == '':
            write_to_log(log_line, end=end)
        else:
            write_to_log(log_line + "\n")

    if ACTIVE_UI is not None:
        ACTIVE_UI.append_log(display_line)

    return log_line


# --- Compatibility shim -----------------------------------------------------

def log_and_display(message: str, turn: int, end: str=None, stamp: bool = True) -> None:
    """
    Backwards compatible function so existing calls keep working.
    Default domain/tone is 'info'.
    """
    emit(message, turn, end=end, log=True, display=True, stamp=stamp)


# --- Wrappers ---------------------------------------------------------------
# Design: wrappers are thin routes into emit(). All take (message, turn, *, tone=...)

# Tone wrappers (optional, but handy)
def msg_info(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="info", tone=tone, end=end, stamp=stamp)

def msg_story(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="story", tone=tone, end=end, stamp=stamp)

def msg_event(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="event", tone=tone, end=end, stamp=stamp)

def msg_question(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="question", tone=tone, end=end, stamp=stamp)

def msg_success(message: str, turn: int, *, tone: str = "success", end='\n', stamp: bool = True) -> str:
    # Default to "success" tone
    return emit(message, turn, domain="info", tone=tone, end=end, stamp=stamp)

def msg_warn(message: str, turn: int, *, tone: str = "warn", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="info", tone=tone, end=end, stamp=stamp)

def msg_error(message: str, turn: int, *, tone: str = "error", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="info", tone=tone, end=end, stamp=stamp)

def msg_help(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="help", tone=tone, end=end, stamp=stamp)

# Domain wrappers
def msg_resource(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="resource", tone=tone, end=end, stamp=stamp)

def msg_explore(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="explore", tone=tone, end=end, stamp=stamp)

def msg_food(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="food", tone=tone, end=end, stamp=stamp)

def msg_plant(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="plant", tone=tone, end=end, stamp=stamp)

def msg_power(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="power", tone=tone, end=end, stamp=stamp)

def msg_mine(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="mine", tone=tone, end=end, stamp=stamp)

def msg_crystal(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="crystal", tone=tone, end=end, stamp=stamp)

def msg_shield(message: str, turn: int, *, tone: str = "info", end='\n', stamp: bool = True) -> str:
    return emit(message, turn, domain="shield", tone=tone, end=end, stamp=stamp)