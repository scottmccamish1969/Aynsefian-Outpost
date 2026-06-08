# main.py

from endgame import check_endgame, handle_game_over_loop
from lore.lore_ingame import print_commands, get_message
from lore.lore_story import get_story_message, msg_story
from lore.user_interface import msg_warn
from OutpostUI import OutpostUI
from turns import process_user_input
from utils import load_config, update_screen

import tkinter as tk

def main():
    root = tk.Tk()
    ui = OutpostUI(root)

    import lore.user_interface as ui_runtime
    ui_runtime.UI_MODE = "gui"
    ui_runtime.ACTIVE_UI = ui
    awaiting_input = False

    def command_callback(command):
        ui.append_log(f">> {command}")
        process_user_input(command)

    ui.set_command_callback(command_callback)

    task_package = load_config()
    if task_package:
        turns_elapsed = task_package["counters"]["turns"]

        if not task_package["gamestate"]["game_over"]:
            msg_story(get_story_message("start", "opening_message"), turns_elapsed)

        # Initial endgame check
        game_over, end_msg, task_package = check_endgame(task_package)

        if game_over:
            awaiting_input, task_package = handle_game_over_loop(end_msg)
            if not awaiting_input:
                if not task_package:
                    msg_warn(get_message("error", "no_config"), 0)
        else:
            print_commands(turns_elapsed)

    # Load the config again (as we might be a brand new game OR a reset) and update the screen
    task_package = load_config()
    update_screen(task_package)

    root.mainloop()

if __name__ == "__main__":
    main()