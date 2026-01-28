# endgame.py

import random
import sys
from constants import ENDGAME_REASONS
from lore.lore_ingame import get_message, print_commands
from lore.lore_story import get_story_message
from lore.user_interface import log_and_display, get_input
from status import print_status
from utils import initialise_outpost, check_shield_state


def check_endgame(task_package):
    # Checks for endgame conditions.
    # Returns (game_over: bool, message: str, task_package)

    gamestate = task_package["gamestate"]
    humans = task_package["humans"]
    resources = task_package["resources"]
    turns_elapsed = task_package["turns_elapsed"]

    # 1. Game already ended
    if gamestate.get("game_over"):
        reason_key = gamestate.get("endgame_reason", "")
        msg = get_story_message("endgame", reason_key)
        return True, msg, task_package

    # 2. All humans dead
    all_dead = all(h.get("state") == "Deceased" for h in humans.values())
    if all_dead:
        reason_key = "all_dead"
        gamestate["game_over"] = True
        gamestate["endgame_reason"] = reason_key
        msg = get_story_message("endgame", reason_key)
        return True, msg, task_package

    # 3. No power left
    powersupply = next((r for r in resources if r.get("name") == "PowerSupply"), None)
    if powersupply and powersupply.get("found") and powersupply.get("amount", 0) <= 0:
        reason_key = "no_power"
        gamestate["game_over"] = True
        gamestate["endgame_reason"] = reason_key
        msg = get_story_message("endgame", reason_key)
        return True, msg, task_package

    # 4. Ensure shield state is current
    task_package = check_shield_state(task_package)

    # 5. MGC arrival check
    chance = random.randint(1, 100)
    threshold = int(((turns_elapsed - 100) / 50) * 100)

    if threshold >= chance:
        return mgc_is_here_check_the_shield(task_package)

    return False, "", task_package


def mgc_is_here_check_the_shield(task_package):
    # Handles MGC arrival and determines win/loss.
    # Returns (game_over, message, task_package)

    gamestate = task_package["gamestate"]
    shieldstate = task_package["shieldstate"]

    if shieldstate.get("shield_active"):
        reason_key = "you_win?"
    else:
        reason_key = "mgc_arrival_no_shield"

    gamestate["game_over"] = True
    gamestate["endgame_reason"] = reason_key

    msg = get_story_message("endgame", reason_key)
    return True, msg, task_package


def handle_game_over_loop(task_package):
    # Handles user input after game over.
    #Returns updated task_package or exits.

    print_status(task_package)

    while True:
        choice = get_input("input", "endgame_choice", task_package["turns_elapsed"])
        reason_code = task_package["gamestate"].get("endgame_reason")

        if choice in ("reset", "r"):
            task_package = initialise_outpost(first_time=False)
            print_commands()
            return task_package

        if choice in ("quit", "exit", "q"):
            if reason_code == "you_win?":
                log_and_display(get_story_message("quit", "you_win?"), task_package["turns_elapsed"])
            else:
                log_and_display(get_story_message("quit", "fail"), task_package["turns_elapsed"])
            sys.exit(0)

        log_and_display(get_story_message("endgame", "restart"), task_package["turns_elapsed"])