# main.py

from endgame import check_endgame, handle_game_over_loop
from lore.lore_ingame import print_commands
from lore.lore_story import get_story_message
from OutpostUI import OutpostUI, get_state_panel_text, get_top_bar_data
from turns import process_user_input
from utils import load_config, save_config

import tkinter as tk

def main():
    root = tk.Tk()
    ui = OutpostUI(root)

    import lore.user_interface as ui_runtime
    ui_runtime.UI_MODE = "gui"
    ui_runtime.ACTIVE_UI = ui
    
    task_package = load_config()
    turns_elapsed = task_package["counters"]["turns"]

    if not task_package["gamestate"]["game_over"]:
        print(get_story_message("start", "opening_message"))

    # Initial endgame check
    game_over, end_msg, task_package = check_endgame(task_package)

    if game_over:
        task_package = handle_game_over_loop(end_msg)
    else:
        print_commands(turns_elapsed)

    # Set some of the GUI requirements
    top = get_top_bar_data(task_package)
    ui.set_top_stats(**top)

    state_text = get_state_panel_text(task_package)
    ui.set_state_text(state_text)

    def command_callback(command):
        ui.append_log(f">> {command}")
        process_user_input(command)

    ui.set_command_callback(command_callback)

    root.mainloop()


if __name__ == "__main__":
    main()