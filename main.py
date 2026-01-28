# main.py

from utils import load_config, save_config
from endgame import check_endgame, handle_game_over_loop
from tasks import advance_tasks
from turns import process_turn, progress_outpost
from lore.lore_ingame import print_splash, print_commands
from lore.lore_story import get_story_message
from lore.user_interface import get_command_from_player


def main():
    print_splash()
    task_package = load_config()

    if task_package["gamestate"]["game_over"] != True:
        print(get_story_message("start", "opening_message"))

    # Initial endgame check
    game_over, end_msg, task_package = check_endgame(task_package)

    if game_over:
        task_package = handle_game_over_loop(end_msg)
    else:
        print_commands()

    while True:
        command = get_command_from_player()

        # Process the turn
        count_as_turn, task_package = process_turn(command, task_package)

        if count_as_turn:
            save_config(task_package)

            # Advance tasks
            task_package = advance_tasks(task_package)

            # Progress the outpost
            task_package = progress_outpost(task_package)

            # Check for endgame
            game_over, end_msg, task_package = check_endgame(task_package)

            if game_over:
                task_package = handle_game_over_loop(end_msg)

        # Save always
        save_config(task_package)


if __name__ == "__main__":
    main()