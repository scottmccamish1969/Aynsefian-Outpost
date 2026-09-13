# OutpostUI.py
### Shell code for the UI   

import tkinter as tk
from tkinter import ttk


class OutpostUI:
    def __init__(self, root):
        global ACTIVE_UI
        ACTIVE_UI = self

        self.root = root
        self.root.title("Aynsefian Outpost")
        self.root.geometry("1280x760")
        self.root.minsize(1000, 650)

        # --- Main layout ----------------------------------------------------
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.top_frame = ttk.Frame(self.root, padding=(10, 8))
        self.top_frame.grid(row=0, column=0, sticky="ew")

        self.main_frame = ttk.Frame(self.root, padding=(10, 0, 10, 0))
        self.main_frame.grid(row=1, column=0, sticky="nsew")

        self.bottom_frame = ttk.Frame(self.root, padding=(10, 8))
        self.bottom_frame.grid(row=2, column=0, sticky="ew")

        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=3)   # Log pane
        self.main_frame.columnconfigure(1, weight=2)   # State pane

        # --- Top strip ------------------------------------------------------
        self.top_frame.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(
            self.top_frame,
            text="Aynsefian Outpost",
            font=("Courier New", 16, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.stats_label = ttk.Label(
            self.top_frame,
            text="Day 0 | Turn 0 | Power 0 | Food 0 | Seeds 0 | Crystals 0",
            font=("Courier New", 11)
        )
        self.stats_label.grid(row=0, column=1, sticky="e")

        # --- Left pane: log -------------------------------------------------
        self.log_frame = ttk.LabelFrame(self.main_frame, text="Outpost Log", padding=8)
        self.log_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(8, 8))

        self.log_frame.rowconfigure(0, weight=1)
        self.log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(
            self.log_frame,
            wrap="word",
            state="disabled",
            font=("Courier New", 11),
            padx=8,
            pady=8
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        self.log_scrollbar = ttk.Scrollbar(
            self.log_frame,
            orient="vertical",
            command=self.log_text.yview
        )
        self.log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=self.log_scrollbar.set)

        # --- Right pane: state ----------------------------------------------
        self.state_frame = ttk.LabelFrame(self.main_frame, text="Outpost State", padding=8)
        self.state_frame.grid(row=0, column=1, sticky="nsew", pady=(8, 8))

        self.state_frame.rowconfigure(0, weight=1)
        self.state_frame.columnconfigure(0, weight=1)

        self.state_text = tk.Text(
            self.state_frame,
            wrap="none",
            state="disabled",
            font=("Courier New", 11),
            padx=8,
            pady=8,
            width=60
        )
        self.state_text.grid(row=0, column=0, sticky="nsew")

        self.state_scrollbar = ttk.Scrollbar(
            self.state_frame,
            orient="vertical",
            command=self.state_text.yview
        )
        self.state_scrollbar.grid(row=0, column=1, sticky="ns")
        self.state_text.configure(yscrollcommand=self.state_scrollbar.set)

        # --- Bottom command entry -------------------------------------------
        self.bottom_frame.columnconfigure(1, weight=1)

        self.command_prompt_var = tk.StringVar(value="What is your next action?")

        self.command_label = ttk.Label(
            self.bottom_frame,
            textvariable=self.command_prompt_var,
            font=("Courier New", 11, "bold")
        )
        self.command_label.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.end_turn_button = tk.Button(
            self.bottom_frame,
            text="END TURN",
            command=lambda: self.command_callback("end turn"),
            bg="#d7c58a",
            activebackground="#eadca9",
            fg="#202020",
            padx=12,
            pady=4,
            relief="raised",
            borderwidth=2
        )

        self.end_turn_button.grid(
            row=0,
            column=3,
            sticky="e",
            padx=(10, 0)
        )

        self.command_entry = ttk.Entry(
            self.bottom_frame,
            font=("Courier New", 11)
        )
        self.command_entry.grid(row=0, column=1, sticky="ew")
        self.command_entry.focus_set()

        self.submit_button = ttk.Button(
            self.bottom_frame,
            text="Enter",
            command=self.on_submit
        )
        self.submit_button.grid(row=0, column=2, sticky="e", padx=(8, 0))

        self.command_entry.bind("<Return>", self.on_submit)
        # Placeholder command handler - replace later
        self.command_callback = None

        # For user questions
        self.pending_question = None

    # ----------------------------------------------------------------------
    # Public helper methods
    # ----------------------------------------------------------------------

    def set_top_stats(self, *, day, turn, power, food, seeds, crystals):
        self.stats_label.config(text=f"Day {day} | Turn {turn} | Power {power} | Food {food} | Seeds {seeds} | Crystals {crystals}")

    def set_state_text(self, text):
        self.state_text.config(state="normal")
        self.state_text.delete("1.0", tk.END)
        self.state_text.insert(tk.END, text)
        self.state_text.config(state="disabled")

    def append_log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, "\n"+text)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def clear_command_entry(self):
        self.command_entry.delete(0, tk.END)

    def set_command_callback(self, callback):
        # callback should be a function taking one argument: command (str)
        self.command_callback = callback

    def set_command_prompt(self, text):
        self.command_prompt_var.set(text)

    def clear_command_prompt(self):
        self.command_prompt_var.set("What is your next action?")

    # ----------------------------------------------------------------------
    # Question handling methods
    # ----------------------------------------------------------------------

    def set_pending_question(self, callback, context=None, resume_turn=False, continue_command_phase=False):
        self.pending_question = {
            "callback": callback,
            "context": context or {},
            "resume_turn": resume_turn,
            "continue_command_phase": continue_command_phase
        }

    def clear_pending_question(self):
        self.pending_question = None

    # ----------------------------------------------------------------------
    # Internal event handling
    # ----------------------------------------------------------------------

    def on_submit(self, event=None):
        
        from constants import CommandOutcome
        from turns import prepare_command_phase
        from utils import save_config, update_screen

        command = self.command_entry.get().strip()
        if not command:
            return
        
        self.clear_command_entry()

        # ---------------------------------------------------------
        # RESPONSE TO A PENDING GUI QUESTION
        # ---------------------------------------------------------
        if self.pending_question is not None:
            callback = self.pending_question["callback"]
            context = self.pending_question.get("context", {})
            continue_command_phase = self.pending_question.get("continue_command_phase", False)
            self.clear_pending_question()
            self.clear_command_prompt()
            outcome, updated_task_package = callback(command, context)

            if updated_task_package is None:
                return

            # The callback itself has asked another question.
            if outcome == CommandOutcome.AWAITING_INPUT:
                return

            if continue_command_phase:
                outcome, updated_task_package = prepare_command_phase(updated_task_package)
            
            save_config(updated_task_package)
            update_screen(updated_task_package)

            return

        # ---------------------------------------------------------
        # NORMAL PLAYER COMMAND
        # ---------------------------------------------------------
        if self.command_callback:
            self.command_callback(command)
            

### Helper functions for populating the GUI ###

def get_top_bar_data(task_package):
    counters = task_package.get("counters", {})
    resources = task_package.get("resources", [])

    turn = counters.get("turns", 0)
    day = turn // 10

    power = 0
    food = 0
    seeds = 0
    crystals = 0

    for r in resources:
        if r.get("name") == "PowerSupply":
            power = r.get("amount", 0)
            crystal_store = r.get("CrystalStore", {})
            crystals = (
                crystal_store.get("red", 0)
                + crystal_store.get("indigo", 0)
                + crystal_store.get("gold", 0)
            )

        elif r.get("name") == "FoodStore":
            food = (
                r.get("rationPack", 0)
                + r.get("apple", 0)
                + r.get("cabbage", 0)
                + r.get("potato", 0)
                + r.get("soup", 0)
                + r.get("smoothie", 0)
                + r.get("stirFry", 0)
            )

        elif r.get("name") == "SeedStash":
            seeds = (
                r.get("apple", 0)
                + r.get("cabbage", 0)
                + r.get("potato", 0)
            )

    return {
        "day": day,
        "turn": turn,
        "power": power,
        "food": food,
        "seeds": seeds,
        "crystals": crystals,
    }