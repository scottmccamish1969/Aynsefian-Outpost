# user_interface.py

import random, os

from constants import LOG_FILE
from datetime import datetime
from typing import Optional

ACTIVE_UI = None
UI_MODE = "console"
GUI_PENDING = "__gui_pending__"

def get_input(category, code, turns_elapsed=0, end=None, **kwargs):
    log_questions = {
        "cancel": {
            "who": "Which human or droid's task(s) would you like to cancel?",
            "current_or_queue": (
                "{name} is currently {current_task} with queued tasks: {queue_list}\n"
                "1. Cancel current task\n"
                "2. Cancel a queued task\n"
                "0. Abort"
            ),
            "which_queued": (
                "{name} has these queued tasks: {queue_list}\n"
                "Which queued task would you like to cancel? (1, 2, 3, or 0 to abort)"
            ),
        },
        "input": {
            "assign": "Who would you like to assign to an item? <name>",
            "assignee": "There is at least one assignable item. Who should be assigned? <name>",
            "assigned_item": "You can assign {name} to any of these: {full_list}. Which do you choose?",
            "assign_name": "Who shall be assigned to {item}? <name>", 
            "charge": "Who do you want to charge? (<name(s)>, 'all' or 'low')",
            "endgame_choice": "Type 'reset' to begin again or 'quit' to exit.",
            "examine": "Who should examine something? <name>",
            "examine_what": "What would you like {target} to examine?\n{items}",
            "explore": "Who should explore? (<name(s)>, 'all' or 'idle')",
            "explore_found": "{target} has found **{res_name}**.  Do you want {pronoun} to examine it? (y/n)",
            "first_time": "There is a message here at the outpost. Would you like to read it (y/n)? ",
            "feed": "Who do you want to feed? (<name(s)>, 'all', or 'hungry')",
            "list": "You can list the following items: {can_be_listed}. Which would you like? (Press enter to exit)",
            "mine": "Who should get out the pick and go mining? <name(s)>",
            "oldterminal": "The OldTerminal accepts your access. Do you wish to use the known CrystalCombination to attempt shield calibration? (y/n)",
            "read": "What file are you interested in reading?  You can pick from: {files}",
            "read_next_lines": "Read next {lines} lines? (y/n):",
            "reap": "Who do you want to do the reaping? <name>",
            "refuel": "Who are you sending to refuel the PowerSupply? <name>",
            "replace": "Which human or droid should have their current task replaced?",
            "reset_confirm": "Are you absolutely, totally, completely sure you want to reset the outpost? (y/n)",
            "resume_examine": "{name} is still suggesting {pronoun1} should examine the **{item}**. Do you want {pronoun2} to? (y/n)",
            "tow_droid": "Which of these humans should be assigned to the task of towing poor {name} to the charging station? ({humans_to_tow})",
            "zero_charge": "{droid} is at zero charge. Droids are urgently needed at this outpost. Do you want to take them to the charging station right now? (y/n)",
        },
        "plant": {
            "who_plants": "Let's plant some real food! Who are you giving the trowel and some seeds to? <name>",
            "default": "You have at least 3 beds available, would you like the default plant (1 apple, 1 cabbage, 1 potato)? (y/n)",
            "how_many": "Okay, how many beds do you wish to use (1 up to {available}, or 0 to abort)?",
            "which_crop": "Which crop do you want in those beds? (apple, cabbage, potato)",
        },
        "replace": {
            "with_what": "{name} is currently {task_name}. What should they be doing instead? (task name, or 0 to exit without changing anything)",
        }
    }
    prompt_questions = {
        "cancel": {
            "who": "Which human or droid's task(s) would you like to cancel?",
            "current_or_queue": "1. Cancel current, 2. Cancel queued or 0. Abort?",
            "which_queued": "Cancel queued task 1, 2 or 3? (0 to abort)",
        },
        "input": {
            "assign": "Who would you like to assign to an item? <name>",
            "assignee": "Who should be assigned? <name>",
            "assigned_item": "Which item should {name} be assigned to? (0 to abort)",
            "assign_name": "Who shall be assigned to {item}? <name>", 
            "charge": "Who do you want to charge? (<name(s)>, 'all' or 'low')",
            "endgame_choice": "Type 'reset' to begin again or 'quit' to exit: ",
            "examine": "Who should examine something? <name>",
            "examine_what": "What would you like {target} to examine?",
            "explore": "Who should explore? (<name(s)>, 'all' or 'idle')",
            "explore_found": "Should {target} examine the **{res_name}**? (y/n)",
            "first_time": "Would you like to read the message? (y/n)",
            "feed": "Who do you want to feed? (<name(s)>, 'all', or 'hungry')",
            "list": "Which would item should be listed? (Press enter to exit)",
            "mine": "Who should get out the pick and go mining? <name(s)>",
            "oldterminal": "Use the known CrystalCombination? (y/n)",
            "read": "What file are you interested in reading?",
            "read_next_lines": "Read next {lines} lines? (y/n):",
            "reap": "Who do you want to do the reaping? <name>",
            "refuel": "Who are you sending to refuel the PowerSupply? <name>",
            "replace": "Which human or droid should have their current task replaced?",
            "reset_confirm": "Confirm that you want to reset the outpost: (y/n)",
            "resume_examine": "Should {name} examine the **{item}**? (y/n)",
            "tow_droid": "Which human should towing {name} to the charging station? <name>",
            "zero_charge": "Do you want to take {droid} to the charging station? (y/n)",
        },
        "plant": {
            "who_plants": "Who should do the planting? <name>",
            "default": "Would you like the default plant? (y/n)",
            "how_many": "How many beds? (1 up to {available}, 0 to abort)?",
            "which_crop": "Which crop do you want in those beds? (apple, cabbage, potato)",
        },
        "replace": {
            "with_what": "What should {name} be doing instead? (task name, or 0 to abort)",
        }
    }

    log_entry = log_questions.get(category, {}).get(code)
    if isinstance(log_entry, list):
        log_entry = random.choice(log_entry)

    prompt_entry = prompt_questions.get(category, {}).get(code)
    if isinstance(prompt_entry, list):
        prompt_entry = random.choice(prompt_entry)

    if isinstance(log_entry, str):
        log_text = log_entry.format(**kwargs)
        msg_question(log_text, turns_elapsed, end='')

        if UI_MODE == "gui" and ACTIVE_UI is not None:
            if isinstance(prompt_entry, str):
                prompt_text = prompt_entry.format(**kwargs)
                ACTIVE_UI.set_command_prompt(prompt_text)
            else:   
                msg_error("[Command prompt not found]", turns_elapsed)
            return GUI_PENDING
        else:
            msg_warn("DEVELOPER: CLI is not supported at this time", turns_elapsed)
            return ""

    msg_error(f"[Input prompt not found:  {category} - {code}]", turns_elapsed)
    return ""


def get_confirm(prompt, turns_elapsed=None, callback=None, context=None):
    if turns_elapsed is None:
        turns_elapsed = 0

    if UI_MODE == "gui" and ACTIVE_UI is not None:
        if callback is None:
            msg_error("DEVELOPER: get_confirm called in GUI mode without callback.", turns_elapsed)
            return False

        msg_question(prompt, turns_elapsed, end='')
        ACTIVE_UI.set_command_prompt(prompt)

        ACTIVE_UI.set_pending_question(
            callback=callback,
            context={
                **(context or {}),
                "prompt": prompt,
            }
        )

        return GUI_PENDING

    answer = input(prompt).strip().lower()
    return answer in ("y", "yes")


def get_integer_input(prompt, min_value=None, max_value=None, *, turns_elapsed=0, callback=None, context=None):
    # Prompts the user for an integer input, validates, and returns it.
    # In GUI mode, displays the question, sets the command prompt,
    # sets a pending callback, and returns GUI_PENDING.

    if UI_MODE == "gui" and ACTIVE_UI is not None:
        if callback is None:
            msg_error("DEVELOPER: get_integer_input called in GUI mode without callback.", turns_elapsed)
            return ""

        msg_question(prompt, turns_elapsed, end='')
        ACTIVE_UI.set_command_prompt(prompt)

        ACTIVE_UI.set_pending_question(
            callback=callback,
            context={
                **(context or {}),
                "prompt": prompt,
                "min_value": min_value,
                "max_value": max_value,
            }
        )

        return GUI_PENDING

    # CLI legacy fallback. Safe to keep for now, even if rarely used.
    while True:
        user_input = input(prompt)

        try:
            value = int(user_input)

            if min_value is not None and value < min_value:
                print(f"❌ Please enter a number greater than or equal to {min_value}.")
                continue

            if max_value is not None and value > max_value:
                print(f"❌ Please enter a number less than or equal to {max_value}.")
                continue

            return value

        except ValueError:
            print("❌ Invalid input. Please enter a valid integer.")


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

    "examine": "🧐 ",
    "explore": "🔎 ",
    "food": "🍏 ",
    "reap": "🍏 ",
    "plant": "🌱 ",
    "power": "⚡ ",
    "mine": "⛏️ ",
    "crystal": "💎 ",
    "shield": "🛡️ ",
    "assign": "🛠️ ",
    "refuel": "⛽ "
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

    display = False     #turning this (the CLI) off for now, enforced, but keeping the original code just in case
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

def log_and_display(message: str, turn: int, end: str=None, stamp: bool = True, log: bool=True) -> None:
    """
    Backwards compatible function so existing calls keep working.
    Default domain/tone is 'info'.
    """
    emit(message, turn, end=end, log=log, display=True, stamp=stamp)


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