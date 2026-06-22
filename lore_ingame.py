# lore_ingame.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lore.user_interface import msg_help, msg_warn, log_and_display

import random

def print_splash():
    print(r"    _                         __ _                ___        _                   _   ")
    print(r"   / \  _   _ _ __  ___  ___ / _(_) __ _ _ __    / _ \ _   _| |_ _ __   ___  ___| |_ ")
    print(r"  / _ \| | | | '_ \/ __|/ _ \ |_| |/ _` | '_ \  | | | | | | | __| '_ \ / _ \/ __| __|")
    print(r" / ___ \ |_| | | | \__ \  __/  _| | (_| | | | | | |_| | |_| | |_| |_) | (_) \__ \ |_ ")
    print(r"/_/   \_\__, |_| |_|___/\___|_| |_|\__,_|_| |_|  \___/ \__,_|\__| .__/ \___/|___/\__|")
    print(r"        |___/                                                   |_|                  ")

def print_commands(turns):
    msg_help(get_message("help", "default"), turns, end='\n')

def print_help(gamestate, turns_elapsed):
    help_texts = {
        "cancel": "Cancel an existing or queued task for a character",
        "charge": "Charge a droid by name",
        "examine": "Examine something found",
        "explore": "Send a human or droid to explore",
        "feed": "Give a human some food",
        "help": "Show this help text",
        "next": "Advance to the next turn without doing anything",
        "quit": "Leave the outpost to decay and ruin and doom Aynsefian in the process",
        "read": "Read documents you have found",
        "replace": "Replace a character's current task with something else",
        "reset": "Start again from scratch",
        "list": "List various things relating to the Outpost",
        "assign": "Assign a task to someone",
        "mine": "Mine resources outside the base",
        "plant": "Plant seeds in a hydroponics bay or elsewhere (if available)",
        "reap": "Collect crops that have matured",
        "refuel": "Refuel the power supply with crystal dust",
        "repair": "Repair broken droids or resources",
    }

    msg_help(" List of available commands:", turns_elapsed)
    for cmd in gamestate:
        if gamestate[cmd]:
            if cmd == "endgame_reason" or cmd == "shield_active" or cmd == "game_over":
                continue
            message = f"   {cmd} - {help_texts.get(cmd, 'No help available')}"
            msg_help(message, turns_elapsed)
    log_and_display("", turns_elapsed, stamp=None)
    message = " Type 'help <command>' to get specific help on that command"
    msg_help(message, turns_elapsed)

# All of the In Game messages
def get_message(category, code, **kwargs):
    messages = {
        "assign": {
            "assignment_aborted": "You decide not to assign {target} to anything right now. Maybe a wise choice. Maybe not.",
            "cannot_complete_assign_task": "DEVELOPER NOTE: Unkown item - cannot complete the assign task.",
            "commenced": "You have now assigned {name} to the {item}. Stand back and see what happens. You can never predict how these things will turn out.",
            "CP_estimate": "From the CrystalProcessor, {target} will create an estimated power output of {total_power} units, which will keep {num} droids charged for {day} days.",
            "invalid_choice": "Please just provide a numbered response from the menu above. '{response}' is not a valid answer.",
            "nothing_assignable": "There are no items to which anyone can be assigned to at this stage. Maybe try again later?",
            "no_manual": "There is no available {item} that can be read to understand the Shield.",
            "no_processor": "There is no available {item} in which to process crystals.",
            "old_terminal_assigned": "{name} is now plugged in to the Droid Interface Port on the OldTerminal and is ready to communicate with this ancient device.",
            "process_completed": "{name} has finished using the {item}. As a result, {total_units} units of power have been generated.",
            "process_no_crystals": "Warning: {name} will be assigned to the {item} but there are no crystals to be processed. Are you expecting some to arrive soon, Commander?",
            "process_no_crystals_to_process": "{name} has waited at the {item} but there are no crystals anywhere to be found. You will need to get someone to do some mining. ⛏️",
            "process_no_power_supply": "DEVELOPER NOTE: When the crystals are processed, there is nowhere to store them.",
            "process_not_enough_crystals": "{name} was assigned to collect {needR} red, {needI} indigo and {needG} gold crystals but there are only {haveR} red, {haveI} indigo and {haveG} gold crystals in storage.",
            "reassigned": "{old} has been relieved of their duties on {item} and now {new} has taken over. {old} appreciates the chance to do something else.",
        },
        "cancel": {
            "cannot_interrupt": "{name} is currently {task}. That cannot be interrupted.",
            "current_cancelled": "{name}'s current task of {task} has been cancelled.",
            "invalid_choice": "'{choice}' is not a valid cancel option.",
            "invalid_queue_slot": "'{slot}' is not a valid queued task slot for {name}.",
            "nothing_to_cancel": "{name} is idle and has no queued tasks, so there is nothing to cancel.",
            "nothing_current": "{name} has no current task to cancel.",
            "not_cancelled": "No task cancellation has occurred for {name}.",
            "no_queued_tasks": "{name} has no queued tasks to cancel.",
            "queued_cancelled": "{name}'s queued task of {task} in slot {slot} has been removed.",
        },
        "charge": {
            "charge_above_low": "{target} is not considered low on charge, skipping.",
            "charge_full": [
                "I'm not sure small business is your thing. Overcharging is not cool, Commander. {droid_name} has just recently been charged.",
                "At least wait until {droid_name} has done something with what you just recently gave them. Sitting at the charging station repeatedly receiving power is possibly not the best use of their resources.",
                "{droid_name} just had a cable shoved into them not long ago and now it's happening again. Their sad droid eyes ask you to wait a little longer before recharging.",
                "Hovering around the power supply constantly charging droids is probably not the best use of your time, Commander. {droid_name} was just recently charged. Wait a bit longer?",
                "Commander, {droid_name} reports they are already sparkling with power. Perhaps *you* need a recharge instead?",
                "Overcharging protocols engaged. {droid_name} hums quietly in protest… and possibly judgment.",
                "You hear faint sizzling. {droid_name} may not enjoy being a toaster, Commander."
            ],
            "commenced": "Charging of {target} has commenced. It will complete in {turn_msg}.",
            "droid_needs_towing": "{target} is out of charge! They can only be taken to a charging station by a human and there are no idle humans. When one becomes available, they can do it.",
            "getting_low": [
                "{name} is getting low on charge. Consider hooking them up to the power supply before they stop mid-task.",
                "Could be time to recharge {name}. Running them into the ground is not the greatest strategy.",
                "Paying a little bit of attention to the charge level of {name} might be wise. They're getting low.",
                "It's time to fire up the PowerSupply and give {name} a recharge. Before they just stop where they are, possibly in everyone's way when that happens.",
                "Running devices on low charge is a risky exercise. Do you like living on the edge? Maybe it's time to recharge {name}."
            ],
            "low_power_warning": "WARNING: Your power supply has dropped below the amount required to charge all your droids. You need to find a way to get more power, Commander. Urgently!",
            "no_target": "Who or what are you attempting to charge?",
            "nowhere_to_charge": "There is nowhere to charge anything electrical.",
            "not_enough_power": "Not enough power left in the supply. You must find another way to generate power, or replenish what is here.",
            "success": "{droid_name} is now re-charged up to {new_charge} units.",
            "task_interrupt": "{name}'s lights flicker and fade. Their charge is exhausted. The {task_type} task they were doing ends where it stands.",
            "tow_successful": "{droid_towed} has been successfully towed by {name} to the charging station and will now be charged back to full power. You feel grateful for the intervention.",
            "towing": "{name} is now towing {droid_being_towed} to the charging station. They will be done with this task in {turn_msg}.",
            "wrong_target": [
                "{target} is asking what the charge is and protests innocence.",
                "After charging {target}, {pronoun} falls backwards to the ground and are mildly injured.",
                "There is no currency on this outpost, so {target} can't be charged.",
                "There is nowhere on this human to plug in a charge cable.",
                "{target} is now slightly electrified."
            ],
        },
        "error": {
            "can't_do_that_yet": "The '{command}' command is not yet enabled, Commander. There are a few things you need to do first.",
            "character_not_found": "DEVELOPER: the character named {name} does not exist.",
            "feed_invalid": "This is an invalid command usage. Choose either:  'feed all', 'feed <name>' or 'feed hungry'.",
            "invalid_auto_message": "DEVELOPER: Invalid auto feed / auto charge message for {name}.",
            "invalid_command": "DEVELOPER: Invalid command '{command}'",
            "invalid_command_from_function": "DEVELOPER NOTE: Invalid command returned from function - '{action}'.",
            "list_fail": "You cannot list this category of 'things'. Nice try though. A random shot in the dark has worked in other spheres of action.",
            "no_callback": "DEVELOPER: get_integer_input called in GUI mode without callback",
            "no_character": "{name} does not exist. Try again?",
            "no_CLI": "DEVELOPER: CLI not supported.",
            "no_config": "DEVELOPER: The configuration file is not present. Please restart the game.",
            "no_food_store" : "Unfortunately, you have no place in which to store food. This could present problems.",
            "no_existing_task": "DEVELOPER: Task does not exist for {name}.",
            "no_items": "You have not found any items yet, so you cannot list anything.",
            "no_power": "Ordinarily it would be a good move using {name} for this {task} task, but since they are out of charge, you can't do it.",
            "no_power_for_assign": "Ordinarily it would be a good assigning {name} to this item, but since they are out of charge, you can't do it.",
            "no_resume_handler": "DEVELOPER: No resume handler for task type: {task_type}",
            "power_not_found": "POWER STATUS:  No power supply found.",
            "too_hungry": "Poor old {name} simply can't do any {task} until {pronoun} has been give some food!",
            "too_hungry_for_assign": "Poor old {name} simply can't be assigned to any item until {pronoun} has been give some food!",
            "unknown_assign": "DEVELOPER:  Cannot assign or unassign character {name}.  Not found.",
            "unknown_command": [
                "Command '{command}' not recognised. You might have a typo, or you might be trying to do something that isn't available yet.",
                "Zarasena says: 'Did you just mash the keyboard for fun?' '{command}' doesn't cut the mustard here, buddy.",
                "Jinekali says: 'I am 98% sure that '{command}' is not a valid command. But I’ve been wrong before... once.'",
                "Warning: '{command}' is invalid. 📎 Clippy says: 'It looks like you're trying to destroy the universe. Need help?'",
                "'{command}' will not achieve anything. Greatness does, however, emerge from simple mistakes and accidents. Just ask Alexander Fleming about that.",
                "Your command '{command}' does not currently exist in the modern Aynsefian vernacular. Salvation sends you a 'woof' that means 'Try Again'.🐕"
                ],
            "unknown_worker": "Cannot get worker '{name}' to do {task}. This person does not exist.",
        },
        "examine": {
            "aborted": "Perhaps getting {target} to examine the {item} is the best move. You'll never know because you chose otherwise.",
            "commenced": [
                "{name} will have a close look at {item}. Don't hold your breath that anything useful will result. You think {pronoun} will need {turn_msg} to hopefully do something useful.",
                "{item} will now face a thorough examination from {name}, for {turn_msg}, using what {pronoun} says is a 'fine tooth comb', but you've never seen one of those before.",
                "Your subordinate ({name}) will now try to understand {item} in {turn_msg} or less. Probably not less. Likely that amount. Or more. Perhaps.",
                "{name} tells you 'don't worry, I've got this covered'. That worries you. Hopefully {item} will still be functional in {turn_msg}.",
                "There will be {turn_msg} where {name} is now engaged in trying to comprehend the deeper mysteries of '{item}'. At least {pronoun} won't set fire to anything for that amount of time.",
                "{name} says: 'It is a far, far better thing that I do, than I have ever done...' You just want answers on '{item}' in {turn_msg}. Not Dickens quotes.",
                "{name} is most likely not trained, qualified or emotionally stable enough to investigate '{item}' for {turn_msg} but there's nobody better, so... you decide {pronoun} can do it anyway."
            ],
            "pause_charging": "{name} has found **{item}**, but they leave it at your feet for the moment while they head off for a much needed charge. You stare it (the {item}), wondering what the heck it is.",
            "pause_eating": "{name} says {pronoun1} is *famished* and will maybe check out the **{item}** when {pronoun1}'s had some food. You can't blame {pronoun2} for this decision. You'd do the same.",
            "invalid_choice": "Please just provide a numbered response from the menu above. '{response}' is not a valid answer.",
            "no_item": "DEVELOPER NOTE: examine task completed but item '{item}' cannot be found!",
            "no_item_name": "DEVELOPER NOTE: examine task completed with no item name!",
            "not_doing": "You decide that {target} doesn't need to examine anything after all. Perhaps they can paint waterlillies or similar instead?",
            "not_found": "You cannot examine '{item}' as it is not found or not known to exist (yet). Maybe in some parallel universe. But not this one.",
            "nothing_examinable": "There are no items that haven't already been examined. Use 'list resources' to see the status of all items.",
            "reassigned": "{previous} is no longer examining the {item}. This role has been uncermoniously given to {new}.",
        },
        "explore": {
            "commenced": [
                "{target} has started looking around. Maybe {pronoun} will find something of use in {turn_msg}. Or {pronoun} may find nothing.",
                "You send {target} on a mission from God. That means it's possible {pronoun} could find something special in {turn_msg}.",
                "You're not sure if {target} will be remembered as one of the great explorers of human history, but {pronoun}'ll look for something useful in the Outpost for {turn_msg} anyway.",
                "Exploring assigned to {target}. Forlorn hopes of finding something important will end in {turn_msg}.",
                "You have sent {target} wandering aimlessly for {turn_msg}. Now go do something else, Commander, and hope for the best.",
                "Exploration underway. {target} is whistling a tune no one recognises. Results expected in {turn_msg}.",
                "You watch {target} walk off into the haze, mumbling about destiny. You think {pronoun}'ll return in {turn_msg}. Probably.",
                "{target} mutters something about mushrooms, then departs. With any luck, {pronoun}’ll probably check in after {turn_msg}.",
                "You have sent {target} to explore. It's either courage or confusion. Either way, we wait {turn_msg} to find out."
            ],
            "found_food": "{target} has found the FoodStore. It contains a stash of [{amount}] long-life ration packs. Your Outpost will find this particularly useful - in the short term.",
            "not_examined": "{target} chooses to leave {res_name} alone for now. Might be a wise move. Might not be.",
            "nothing_found": [
                "{target} reports that {pronoun} {has_have} explored the wider Outpost area but found nothing of value.",
                "After a thorough search, {target} has come back with nothing at all. Great. What now?",
                "You suspect {target} might have been having a nap somewhere because {pronoun} {has_have} returned from {pronoun2} search with absolutely nothing.",
                "There might be nothing left to find, or there might be nothing *useful* left to find, after {target} returns empty handed.",
            ],
            "unexpected_type": "DEVELOPER: unexpected type for discovered_name: {name}"
        },
        "feed": {
            "commenced": "{person_name} has gladly begun the task of finding and eating some food. {pronoun} will be back in {turn_msg}.",
            "fed_A_C_P": "With all fresh food available, {person_name} ate {A} apples, {P} potato, and {C} of a cabbage. {pronoun1} seems less vague than {pronoun2} was the day before. 🌱",
            "fed_A_C": "{person_name} had a rustic meal of {A} apples and {C} of a cabbage. It wasn’t tasty, but it did the job. 🥬",
            "fed_A_P": "{person_name} ate {A} crispy apples and {P} earthy potatoes. Raw food isn't ideal, but it's better than that ration pack rubbish. 💸",
            "fed_C_P": "Today {person_name} had {P} potatoes and {C} of a cabbage. Some fruit would've been nice, but this will do. 🥬",
            "fed_A": "With only apples available, {person_name} had {A} of them. Grow some more crops please, Commander. 🍏",
            "fed_C": "Cabbages are the only thing left. {person_name} had {C} of them. Still better than a ration pack. 😟",
            "fed_P": "It's the starch diet for {person_name}. {pronoun1} just had {P} potatoes today. Pray for them. 🥔",
            "fed_ration": [
                "{person_name} had a ration pack. It tasted like expired glue and regret. {pronoun1} was not grateful for what {pronoun2} was given. Grace was not said. 🍫",
                "{person_name} unwrapped another ration pack. The texture defied explanation. It was eaten in silence, eyes fixed on nothing. 🪵",
                "{person_name} consumed a ration pack. The chocolate had turned white and the meat tasted faintly of rust. {pronoun1} chewed slowly. 🍖",
                "{person_name} forced down a ration pack. Nobody spoke. Nobody asked how it was. It was... fine. Probably. 💬",
                "{person_name} ate their ration alone, seated on an empty crate. {pronoun1} checked the label: it expired more than two years ago. 🧾",
                "{person_name} had a ration pack. {pronoun1} peeled open the foil and found... cheese. Not cheese. A memory of cheese. 🧀"
            ],
            "food_all_used_up": "{person_name} cannot be fed as there is no food left! You will need to grow some crops quickly, Commander.",
            "no_foodstore": "There is no food readily available. Maybe send someone to look for some via the 'explore' command?",
            "no_hungry_humans": "There are no humans who are hungry or worse. Instead you can use 'feed all' if you wish to feed all humans earlier than planned.",
            "low_food_warning": "WARNING: Commander, food stores have fallen below two days' worth for {num_humans} humans. Hopefully you have some plants about to mature!",
        },
        "feed_droid": {
            "responses": [
                "{droid_name} tilts its head: 'I cannot accept this form of nourishment.'",
                "{droid_name} politely declines the food: 'Requesting battery charge instead.'",
                "{droid_name} emits a sad beep: 'Feeding protocol not supported.'",
                "No slot in {droid_name} in which to place food.",
                "Careful! Organic compounds can cause rust if inserted into droids."
            ]
        },
        "feed_full": {
            "response": [
                "Ye gods, man, stop feeding {person_name}. {pronoun} has already had enough food for now.",
                "It's only wafer thin... ({person_name} is full).",
                "{person_name} refuses food. {pronoun} just ate and would be ill any more food was consumed.",
                "Not a wise use of resources, Commander. {person_name} has just eaten.",
                "Gluttony in this outpost, or anywhere else, is a sin. {person_name} has had food not that long ago.",
                "You’re trying to make {person_name} explode? {pronoun} has no room for any more sustenance."
            ]
        },
        "help": {
            "default" : "Type 'help' for a list of commands or 'quit' to exit the game."
        },
        "hunger": {
            "Deceased": "{name} has died of starvation. R.I.P. {name}, you were one of the good ones.",
            "Near Death": "{name} is near death from lack of food! Find {pronoun} some nourishment somewhere, quickly!",
            "Starving": "{name} is starving! Unfortunately {pronoun} ability to do any sort of work is curtailed until food is provided.",
            "Hungry": "{name} is hungry and wants to eat.",
            "starving_warning": "{name} is getting very hungry. {pronoun} might soon be starving and will be no good to anyone, including you, Commander.",
            "near death_warning": "A hush goes over the Outpost. {name} might soon be in a 'Near Death' state from lack of food. {pronoun} urgently needs you to find some food. From *somewhere*. 😔",
            "deceased_warning": "It has been a very long time since {name} had any food. {pronoun} is approaching death from malnutrition. Please do something - if you can. 😟"
        },
        "mine": {
            "commenced": "The vital task of procuring necessary crystal for power and other things has been given to {target} for {turn_msg}. You hope this was a wise decision.",
            "started": "You have sent {name} to the CrystalField to mine some vitally important crystals. PPE: On. Pick: Carried. Outcome: Uncertain.",
            "completed": "{name} has returned from the CrystalField with {red} red, {indigo} indigo and {gold} gold crystals.",
            "cannot_store": "DEVELOPER NOTE: Cannot store crystals. PowerSupply does not exist. (This is where they were to be stashed)."
        },
        "penalty": {
            "reset_abort": "Reset aborted. Your hesitation has cost the colony 1 turn. 🔥"
        },
        "plant": {
            "aborted": "You have decided that {target} has more important things to do than plant. {pronoun} {is_are} dismayed at this decision. {pronoun}'ll get over it.",
            "bed_occupied": "Cannot plant anything in bed {bed}. It is already being used.",
            "commenced": "{target} has vanished into the planting area for {turn_msg} with a packet of seeds and not much else. Hoping for the best is all you can do at this stage.",
            "crop_matured": "🌱 {planter}'s {crop_type} crop in bed #{bed} has matured!",
            "crop_started": "{target} has somehow managed to plant fast growing {crop}s. Use the 'list food' command to view expected yield time(s).",
            "invalid_bed": "DEVELOPER NOTE: Bed {bed} does not exist. ",
            "invalid_response": "Invalid number of beds chosen: please choose between 0 and {free_beds}.",
            "low_seeds_warning": "WARNING: Commander, we only have 20%% of our initial seed stash left! Hopefully you have prepared wisely and you have enough food to last until the mission is successful.",
            "no_beds": "There are no free beds in which to plant crops. Planting has failed!",
            "no_hydro": "The HydroponicsRoom remains inaccessible. You'll need to find it before planting can begin. 💧",
            "no_seedstash": "You haven't located the SeedStash yet. Without seeds, there's nothing to plant. 🔍",
            "not_enough_seeds": "You do not have enough seeds to plant more {crop}s. You have {have} {crop} seeds and you need {need} {crop} seeds.",
            "not_enough_seeds_generic": "You do not have enough seeds to plant a standard crop of apple, cabbage and potato. Try a specific seed type.",
            "nothing_planted": "DEVELOPER NOTE: Nothing was planted due to bed allocation issues. Worker name: {target}.",
            "task_complete": "The planting task by {target} has now been completed. Successful crops planted: {number}.",
            "unknown_crop": "Unknown crop type '{crop}'. Try apple, cabbage, or potato.",
        },
        "queue": {
            "added": "{character} is currently {current_task}, so the task of {queue_task} has been added to {pronoun} queue.",
            "auto_charge": "{name} has headed to the charging station to recharge, lest it run out of juice before it completes its next task. It will be fully charged in {turn_msg}.",
            "auto_food": "{name} has gone off for {pronoun1} meal break. {pronoun2} will be back to work in {turn_msg}.",
            "cancel_current": "Cancelling current task: {task}.",
            "invalid_option": "Invalid option. Please choose from the menu.",
            "is_now": "--> {pronoun_str} now {task}.",
            "is_now_idle": "--> {pronoun_str} now --Idle--.",
            "no_tasks": "There are no tasks to reorder.",
            "not_queued": "Could not add {task} to {name}'s queue: it is full. Wait until they finish something first or use 'replace' or 'cancel' to modify their tasks.",
            "not_queued_already_queued": "{name} already has a task for {task}. Skipping this queue addition. Eating, Charging and Assigning can only be queued once.",
            "not_queued_error": "DEVELOPER NOTE:  Invalid name '{name}' for queuing.",
            "okay_then_charge": [
                "You can sense the fortitude in {name}'s circuits as they head off to their next task. They will power up later.",
                "Running your droids into the ground is okay in the short term, but sooner or later, {name} will need more juice.",
                "Stretching your resources to the limit, Commander? Maybe you're just good at math. {name} can charge after this task ends."
            ],
            "okay_then_food": [
                "{name} understands the gravity of the Shield situation. {pronoun} will push on and get sustenance later.",
                "{name}: on task and prioritising the shield over their stomach. You: brownie points lost. Hope you still have some left.",
                "You feel like a dictator as {name} heads off to whatever is next, stomach grumbling. {pronoun} probably won't send you a Christmas card this year."
            ],
            "queue_full": [
                "{character}'s queue is full and the {task} task cannot be added. Ye gods, man, ease up!  You can check a human or droid's queue by using 'edit queue'.",
                "{character} has already been loaded up with enough tasks. The {task} task  cannot be added to their queue. Use 'replace' or 'cancel' if you feel the need to modify their tasks.",
                "There is no more room on {character}'s task queue for any more taskings. You can't add '{task}' until later."
            ],
            "queued": "{name} is busy {now_doing}. {task} has been added to their queued tasks.",
            "queued_assign": "{name} is busy {now_doing}. The assignment to the {item} has been queued.",
            "queued_examine": "{name} is busy {now_doing}. The examining of the {item} has been queued.",
            "queued_with_item": "{name} is busy {now_doing}. The {task} task relating to the {item} has been queued.",
            "queued_with_task_data": "{name} is busy {now_doing}. The {task} task has been queued.",
            "removed_task": "{queued_task} task in position {pos} has been removed from {character}'s queue.", 
            "removed_task_abort": "You choose not to remove a task from {character}'s queue.", 
            "removed_task_invalid": "That is an invalid queue position. Select a number between 1 and 3.",
            "removed_task_no_task": "{character} does not have a task at queue position {position}.",
            "reorder_already_at_top": "That task ({task}) is already at the top of {character}'s queue. No changes made.",
            "reorder_invalid": "That is an invalid queue position. Select a number between 1 and 3.",
            "reorder_valid_number_needed": "Please enter a valid number.",
            "reordered_task": "Task {old_pos} ({task}) has been moved to slot {new_pos} in {character}'s queue.",
        },
        "quit": {
            "farewell": "\n-= Farewell, Commander. You gave it your best shot! The outpost will crumble and Aysnefian will be lost to history... =-\n\n",
            "final": "\n-= You abandon the outpost.  It's just a matter of time before the MGC finds us now...=-\n",
            "victory": "\n-= CONGRATULATIONS on defeating the Melcheisa Galactic Council! Will it be the same next time you try?=-\n"
        },
        "read" : {
            "here_it_is": [
                "For your consideration, Commander, here is your '{subject}' file.",
                "As requested, the '{subject}' file has been retrieved and will be displayed. Please proceed with caution.",
                "File '{subject}' is now accessed. Do not allow sentimentality to interfere with your mission.",
                "🔴 First Lady Zarasena says: 'Here’s the '{subject}' file you asked for. Are you taking *any* notes? At all?'",
                "🔴 First Lady Zarasena says: 'Stop readin' things and get workin'. Here's your '{subject}' file. Are you sure you know what you're doing?'",
                "By the authority of protocol Delta-Uniform-Mike-Bravo-2-3-4-5, '{subject}' has been declassified. This does not imply trust."
            ],
            "no_content": "No readable content found for '{subject}'.",
            "no_subject": "There is no '{subject}' file to read at this stage.",
            "nothing_further": "That is all that this file contains. Time to stop reading things and get that Shield up, Commander.",
            "quit": "You decide not to read anything. Reading is overrated. No-one ever built anything just by reading."
        },
        "reap": {
            "commenced": "{target} has gone to find as many mature raw produce items as possible. Wish them well. The Outpost's survival depends on their success. {pronoun} will be back in {turn_msg}.",
            "harvest_complete": "{target} has returned from the crops area with {items}. {seedsmsg}",
            "invalid_bed": "DEVELOPER NOTE: crop {crop} has invalid bed {bed}.",
            "no_mature_crops": "{target} has been sent out to collect crops, but nothing is mature yet. Presumably they will ripen very soon and you're just very good at planning.",
        },
        "refuel": {
            "aborted": "You have decided that {name} should not do any refuelling. That's totally fine, Commander. You're in charge.",
            "commenced": "You have sent {target} off to put more material into the {item}. Good luck with that.",
            "completed": "Congratulations, Commander! You have successfully engaged {name} in a task to refuel the PowerSupply, which has been completed.",
            "no_seedstash": "DEVELOPER NOTE: Seed stash not located - should not happen.",
            "no_vials_fail": "{name} cannot find any vials of crystal dust to refuel with. Try generating some",
            "no_vials": "You are aiming to send {name} to refuel the PowerSupply, but there are no vials of crystal dust to use for refuelling. You'll need to create some first.",
        },
        "replace" : {
            "cannot_interrupt": "{name} is currently {task}, and cannot be interrupted until they are finished. {new_task} has been placed at the top of their work queue.",
            "invalid_task": "{name} cannot be tasked with '{new_task}' as this is not a valid task. Try again. Maybe have a stimulant drink if you can find one?",
            "is_idle": "{name} is currently Idle, so there is nothing to replace. Just task them directly with whatever you want them to do.",
            "not_replaced": "You decide to leave {name} along for now. It seems they appreciate that sentiment.",
            "replacing": "Right you are, Commander. {name} will immediately stop {old_task} and go right to {new_task}.",
        },
        "reset": {
            "start": "Resetting the entire Aynsefian Outpost . . .",
            "done": " . . . the Outpost has been reset.",
        },
        "shield": {
            "assigned_to": "{target} has now been given the CRUCIAL role of keeping the Shield operational.\nWhile {target} is connected to the shield, they will remain fully charged.",
            "cannot_assign_human": "You cannot assign a non-mechanical entity to operate this Shield. The manual explicitly says so. Please choose someone other than {name}.",
            "code_not_found": "DEVELOPER: AncientDroidCode not found.",
            "combo_correct": "The correct combination of crystals have been extablished by {name} and have been loaded into the shield box. The system hums in response... Calibration signal confirmed.",
            "combo_correct_aborted": "The combination of crystals appears to be correct but you have chosen to not have {name} enter it into the OldTerminal",
            "combo_not_examined": "The CrystalCombination for the Shield has been found but not yet examined. Perhaps someone should study it first.",
            "manual_decoded": "With the help of the DecodeKey, the ShieldManual reveals its secrets. Instructions for gettting the Shield to power up are now clear.",
            "manual_not_found": "DEVELOPER: The ShieldManual was not found.",
            "no_combo": "The terminal prompts for input, if is asking {name} for an amount of three different crystals. No-one knows what to enter. You need more information from somewhere.",
            "no_combo_found": "DEVELOPER: The CrystalCombination was not found.",
            "no_decode": "{name} examines the ShieldManual, but {pronoun} can't understand the symbols. A decoding tool may be required.",
            "no_decode_examined": "The DecodeKey has been found, but not yet examined. Without understanding it, the ShieldManual remains unreadable.",
            "no_droid_with_code": "You have no droids in the Outpost to receive the ancient firmware. The code you just found remains unused.",
            "no_power": "WARNING: There is no power supply available to connect the Shield!",
            "not_enough_crystals": "You currently do not have enough crystals to insert into the Shield. You have {have_R} red, {have_I} indigo and {have_G} gold and you need {need_R} red, {need_I} indigo and {need_G} gold. Better send someone to do some mining, Commander.",
            "not_enough_crystals_with_combo": "You know how many crystals you need according to the combination, but there's not enough in storage. You have {have_R} red, {have_I} indigo and {have_G} gold. You need {need_R} red, {need_I} indigo and {need_G} gold.",
            "terminal_unreadable": "The terminal glows faintly... but without understanding the instructions from the ShieldManual, {name} cannot work out what {pronoun} should do next.",
            "terminal_for_droids_only": "The SheldManual says that assigning non-mechanical entities to operate this OldTerminal will fail. So please do not ask {name} to sit down at the keyboard. Any droid is fine.",
        },
        "task": {
            "cancelled": "The {task_type} task for {name} has been ended prematurely.",
            "check": "{name} is currently {task_type}. Do you want to:\n1. Cancel  2. Replace, or  3. Do nothing (continue existing task)?",
            "not_active": "{name} does not have an active task to be cancelled. Maybe give {pronoun} something to do first?",
            "replaced": [
                "{name} is no longer {task_type}. You'd better sort this out quickly: First Lady Zarasena will think you don't know what you're doing.",
                "You stop {name} from taking up any more of {pronoun} time {task_type}. That may or may not be wise.",
                "Archpriest Lanemu says: 'I have sent blessings to {name}, who thought {pronoun} task of {task_type} was noble and sacred and is now upset that it ended.'",
                "{name} is quietly pulled away from {pronoun} {task_type}, like a dream interrupted. Somewhere, out in the void, a lonely star winks out of existence.",
                "You've overridden {name}'s {task_type}. If it turns out badly, just tell the others it was Terri's fault.",
                "{name}'s {task_type} ends abruptly. The silence after echoes louder than the task itself.",
                "{name} returns from an interrupted session of {task_type} with a look that says: 'Again? Really?'"
            ],
            "unknown": "Unknown task assignment '{task_type}' completed by {name}.",
        },
        "usage": {
            "charge": "For the 'charge' command, the only additions allowed are a name or names, 'all' or 'low'. Have another go.",
            "feed": "For the 'feed' command, the only permitted following words are a name or names, 'all' or 'hungry'. Please re-do this command.",
            "explore": "For the 'explore' command, you may only add a name or names, 'all' or 'idle'. Please try again.",
            "mine": "For the 'mine' command, only a single character name (human or droid) is permitted.",
        },
    }

    entry = messages.get(category, {}).get(code)
    if isinstance(entry, list):
        entry = random.choice(entry)
    if isinstance(entry, str):
        return entry.format(**kwargs)
    return f"[Message not found:  {category} - {code}]"


used_explore_messages = set()
def get_unique_message(messages):
    # Returns a random non-repeating message from a list. Resets when exhausted.
    available = [m for m in messages if m not in used_explore_messages]
    if not available:
        used_explore_messages.clear()
        available = messages
    choice = random.choice(available)
    used_explore_messages.add(choice)
    return choice


def handle_help_command(task_package, qualifier=None, gamestate=None):
    turns_elapsed = task_package["counters"]["turns"]

    # Deals with the generic help command as well as specific help for all commands
    if not qualifier:
        print_help(gamestate, turns_elapsed)
    elif qualifier == "assign":
        if gamestate.get("assign", False):
            msg_help(" Humans or droids can be assigned to particular stations or items within the Outpost.", turns_elapsed)
            msg_help(" To assign a human or droid, and get a list of assignable items, just type 'assign'.", turns_elapsed)
        else:
            msg_warn(" Assigning is valid in the Outpost, but there are no 'assignable' items that have been found at this stage.", turns_elapsed)
    elif qualifier == "charge":
        msg_help(" Droids need to be regularly charged so that they can function effectively.", turns_elapsed)
        msg_help(" To enable charging, just type 'charge', or 'charge <name>' or 'charge all'.", turns_elapsed)
    elif qualifier == "cancel":
        msg_help(" Use this command to cancel a queued task, or the current active task.", turns_elapsed)
        msg_help(" You can either type 'cancel <character>' or just 'cancel' and follow the prompts.", turns_elapsed)
    elif qualifier == "feed":
        msg_help(" Humans will regularly go for food when they're hungry, but they can also be fed manually.", turns_elapsed)
        msg_help(" To feed someone, you can use 'feed', 'feed <name>' or 'feed all'.", turns_elapsed)
    elif qualifier == "examine":
        msg_help(" Items can be examined once they are found, or the examination can be deferred until later.", turns_elapsed)
        msg_help(" To examine an item that was not looked at upon finding it, just type 'examine', or 'examine <name>'.", turns_elapsed)
    elif qualifier == "explore":
        msg_help(" This is your first Outpost action, now that you're here. Find useful things. And use them.", turns_elapsed)
        msg_help(" You can send a human or droid exploring simply by typing 'explore', 'explore <name>' or 'explore all'.", turns_elapsed)
    elif qualifier == "help":
        msg_help(" 'help' is a valid command, and thanks to your resourcefulness, you have discovered how to use it. Congratulations!", turns_elapsed)
    elif qualifier == "list":
        msg_help(" You can obtain more detailed information about certain aspects of the Outpost via this command.", turns_elapsed)
        msg_help(" This is done via 'list' or 'list <area>', where area is a specific part of the Outpost.", turns_elapsed)
    elif qualifier == "mine":
        if gamestate.get("mine", False):
            msg_help(" Now that a crystal field has been found, you can send a human or droid to extract these vital resources.", turns_elapsed)
            msg_help(" This is achieved by typing either 'mine' or 'mine <name>'.", turns_elapsed)
        else:
            msg_warn(" You can 'mine', but not just at the moment.", turns_elapsed)
    elif qualifier == "next":
        msg_help(" You may advance to the next turn by using this command, if there is nothing you can or want to do at this stage.", turns_elapsed)
        msg_help(" To do this, simply type 'next'.", turns_elapsed)
    elif qualifier == "plant":
        if gamestate.get("plant", False):
            msg_help(" Planting is available when you have found three things: a growing location, a water source, and useful seeds.", turns_elapsed)
            msg_help(" Once these conditions have been met, you can send a human or droid to the planting area by typing either 'plant' or 'plant <name>'.", turns_elapsed)
        else:
            msg_warn(" 'plant' is a valid command, but it cannot be used yet.", turns_elapsed)
    elif qualifier == "quit":
        msg_help(" Quitting doesn't mean forever. But it does create space in which you can pause and rethink things.", turns_elapsed)
        msg_help(" To exit the Outpost and into an alternate dimension (i.e. your waking life), just type 'quit' and hit Enter.", turns_elapsed)
    elif qualifier == "read":
        msg_help(" You may read stored documents on your server console in the Outpost via this command.", turns_elapsed)
        msg_help(" Reading is carried out via 'read <thing>' if you know the name of the document, or just 'read', to get a list.", turns_elapsed)
    elif qualifier == "reap":
        if gamestate.get("reap", False):
            msg_help(" Once your crops have matured, humans or droids can collect the food via this command.", turns_elapsed)
            msg_help(" Reaping crops is done via 'reap' or 'reap <name>'.", turns_elapsed)
        else:
            msg_warn(" You can 'reap', but only when you have mature crops.", turns_elapsed)
    elif qualifier == "replace":
        msg_help(" Use this command to replace the current task being performed by a human or droid with another task.", turns_elapsed)
        msg_help(" To do this, type 'replace' or 'replace <character>' and follow the prompts.", turns_elapsed)
    elif qualifier == "refuel":
        if gamestate.get("refuel", False):
            msg_help(" Once you have found crystals and converted them into crystal dust, you can use them to top up the PowerSupply.", turns_elapsed)
            msg_help(" This is done via either 'refuel' or 'refuel <name>'.", turns_elapsed)
        else:
            msg_warn(" You can 'refuel', but not until the necessary pre-requisites are available.", turns_elapsed)
    elif qualifier == "reset":
        msg_help(" Sometimes life just gets in the way and things get messed up. A 'reset' lets you have another go at this Outpost thing.", turns_elapsed)
        msg_help(" To give up and start again - and there's no shame in this - just type 'reset' and you will be asked to confirm before proceeding.", turns_elapsed)
    else:
        msg_help(" Help on that command is either not available yet, or that is not actually a command. Type 'help' for a list of available commands.", turns_elapsed)

    return