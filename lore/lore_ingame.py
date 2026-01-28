# lore_ingame.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import random

def print_splash():
    print(r"    _                         __ _                ___        _                   _   ")
    print(r"   / \  _   _ _ __  ___  ___ / _(_) __ _ _ __    / _ \ _   _| |_ _ __   ___  ___| |_ ")
    print(r"  / _ \| | | | '_ \/ __|/ _ \ |_| |/ _` | '_ \  | | | | | | | __| '_ \ / _ \/ __| __|")
    print(r" / ___ \ |_| | | | \__ \  __/  _| | (_| | | | | | |_| | |_| | |_| |_) | (_) \__ \ |_ ")
    print(r"/_/   \_\__, |_| |_|___/\___|_| |_|\__,_|_| |_|  \___/ \__,_|\__| .__/ \___/|___/\__|")
    print(r"        |___/                                                   |_|                  ")

def print_commands():
    print(get_message("help","default"))

def print_help(gamestate):
    help_texts = {
        "charge": "Charge a droid by name",
        "examine": "Examine something found",
        "explore": "Send a human or droid to explore",
        "feed": "Give a human some food",
        "list": "List various things relating to the Outpost",
        "assign": "Assign a task to someone",
        "plant": "Plant seeds in a hydroponics bay or elsewhere (if available)",
        "reap": "Collect crops that have matured",
        "mine": "Mine resources outside the base",
        "read": "Read found documents or logs",
        "refuel": "Refuel the power supply with crystal dust",
        "repair": "Repair broken droids or resources",
        "manage": "Manage human and droid activity",
        "next": "Advance to the next turn without doing anything",
        "read" : "Read a document",
        "status": "Give the current status of the outpost",
        "reset": "Start again from scratch",
        "help": "Show this help text",
        "quit": "Leave the outpost to decay and ruin and doom Aynsefian in the process"
    }

    for cmd in gamestate:
        if gamestate[cmd]:
            if cmd == "endgame_reason" or cmd == "shield_active" or cmd == "game_over":
                continue
            else:
                print(f"   {cmd} - {help_texts.get(cmd, 'No help available')}")

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
            "not_queued": "Could not assign {character}: their task queue is full. Wait until they finish something first or use 'manage queue'.",
            "old_terminal_assigned": "{name} is now plugged in to the Droid Interface Port on the OldTerminal and is ready to communicate with this ancient device.",
            "process_completed": "{name} has finished using the {item}. As a result, {total_units} units of power have been generated.",
            "process_no_crystals": "Warning: {name} will be assigned to the {item} but there are no crystals to be processed. Are you expecting some to arrive soon, Commander?",
            "process_no_crystals_to_process": "{name} has waited at the {item} but there are no crystals anywhere to be found. You will need to get someone to do some mining. ⛏️",
            "process_no_power_supply": "DEVELOPER NOTE: When the crystals are processed, there is nowhere to store them.",
            "process_not_enough_crystals": "{name} was assigned to collect {needR} red, {needI} indigo and {needG} gold crystals but there are only {haveR} red, {haveI} indigo and {haveG} gold crystals in storage.",
            "reassigned": "{old} has been relieved of their duties on {item} and now {new} has taken over. {old} appreciates the chance to do something else.",
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
            "commenced": "Charging of {target} has commenced. It will complete in {turns} turns.",
            "getting_low": [
                "{name} is getting low on charge. Consider hooking them up to the power supply before they stop mid-task.",
                "Could be time to recharge {name}. Running them into the ground is not the greatest strategy.",
                "Paying a little bit of attention to the charge level of {name} might be wise. They're getting low.",
                "It's time to fire up the PowerSupply and give {name} a recharge. Before they just stop where they are, possibly in everyone's way when that happens.",
                "Running devices on low charge is a risky exercise. Do you like living on the edge? Maybe it's time to recharge {name}."
            ],
            "no_target": "Who or what are you attempting to charge?",
            "nowhere_to_charge": "There is nowhere to charge anything electrical.",
            "not_enough_power": "Not enough power left in the supply. You must find another way to generate power, or replenish what is here.",
            "success": "{droid_name} is now re-charged up to {new_charge} units.",
            "task_interrupt": "{name}'s lights flicker and fade. Their charge is exhausted. The {task_type} task they were doing ends where it stands.",
            "wrong_target": [
                "{target} is asking what the charge is and protests innocence.",
                "After charging {target}, they fall backwards to the ground and are mildly injured.",
                "There is no currency on this outpost, so {target} can't be charged.",
                "There is nowhere on this human to plug in a charge cable.",
                "{target} is now slightly electrified."
            ],
        },
        "error": {
            "can't_do_that_yet": "The '{command}' command is not yet enabled, Commander. There are a few things you need to do first.",
            "feed_invalid": "This is an invalid command usage. Choose either:  'feed all', 'feed <name>' or 'feed hungry'.",
            "invalid_command_from_function": "DEVELOPER NOTE: Invalid command returned from function - '{action}'.",
            "list_fail": "You cannot list this category of 'things'. Nice try though. A random shot in the dark has worked in other spheres of action.",
            "no_character": "{name} does not exist, so they cannot be managed. Try again?",
            "no_food_store" : "Unfortunately, you have no place in which to store food. This could present problems.",
            "no_items": "You have not found any items yet, so you cannot list anything.",
            "no_power": "Ordinarily it would be a good move using {name} for this {task} task, but since they are out of charge, you can't do it.",
            "no_power_for_assign": "Ordinarily it would be a good assigning {name} to this item, but since they are out of charge, you can't do it.",
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
                "Your command '{command}' does not currently exist in the modern Aysefian vernacular. Salvation sends you a 'woof' that means 'Try Again'.🐕"
                ],
            "unknown_worker": "Cannot get worker '{name}' to do {task}. This person does not exist.",
        },
        "examine": {
            "commenced": [
                "{name} will have a close look at {item}. Don't hold your breath that anything useful will result. You think {pronoun} will need {turns} turns to hopefully do something useful.",
                "{item} will now face a thorough examination from {name}, for {turns} turns, using what {pronoun} says is a 'fine tooth comb', but you've never seen one of those before.",
                "Your subordinate ({name}) will now try to understand {item} in {turns} turns or less. Probably not less. Likely that amount. Or more. Perhaps.",
                "{name} tells you 'don't worry, I've got this covered'. That worries you. Hopefully {item} will still be functional in {turns} turns.",
                "There will be {turns} turns where {name} is now engaged in trying to comprehend the deeper mysteries of '{item}'. At least {pronoun} won't set fire to anything for that amount of time.",
                "{name} says: 'It is a far, far better thing that I do, than I have ever done...' You just want answers on '{item}' in {turns} turns. Not Dickens quotes.",
                "{name} is most likely not trained, qualified or emotionally stable enough to investigate '{item}' for {turns} turns but there's nobody better, so... you decide {pronoun} can do it anyway."
            ],
            "examine_aborted": "Perhaps getting {target} to examine something is not the best move. You'll never know because you chose otherwise.",
            "invalid_choice": "Please just provide a numbered response from the menu above. '{response}' is not a valid answer.",
            "no_item": "DEVELOPER NOTE: examine task completed but item '{item}' cannot be found!",
            "no_item_name": "DEVELOPER NOTE: examine task completed with no item name!",
            "not_found": "You cannot examine '{item}' as it is not found or not known to exist (yet). Maybe in some parallel universe. But not this one.",
            "nothing_examinable": "There are no items that haven't already been examined. Use 'list resources' to see the status of all items.",
            "reassigned": "{previous} is no longer examining the {item}. This role has been uncermoniously given to {new}.",
        },
        "explore": {
            "commenced": [
                "{target} has started looking around. Maybe {pronoun} will find something of use in {turns} turns. Or {pronoun} may find nothing.",
                "You send {target} on a mission from God. Who knows what {pronoun} may turn up in {turns} turns.",
                "You're not sure if {target} will be remembered as one of the great explorers of human history, but {pronoun}'ll look for something useful in the Outpost for {turns} turns anyway.",
                "Exploring assigned to {target}. Folorn hopes of finding something important will end in {turns} turns.",
                "You have sent {target} wandering aimlessly for {turns} turns. Now go do something else, Commander, and hope for the best.",
                "Exploration underway. {target} is whistling a tune no one recognises. Results expected in {turns} turns.",
                "You watch {target} walk off into the haze, mumbling about destiny. You think {pronoun}'ll return in {turns} turns. Probably.",
                "{target} mutters something about mushrooms, then departs. With any luck, {pronoun}’ll probably check in after {turns} turns.",
                "You have sent {target} to explore. It's either courage or confusion. Either way, we wait {turns} turns to find out."
            ],
            "found_food": "{target} has found the FoodStore. It contains a stash of [{amount}] long-life ration packs. Your Outpost will find this particularly useful - in the short term.",
            "not_examined": "{target} chooses to leave {res_name} alone for now. Might be a wise move. Might not be.",
            "nothing_found": [
                "{target} explored the area but found nothing of value.",
                "After a thorough search, {target} has come back with nothing at all. Great. What now?",
                "You suspect {target} might have been having a nap somewhere because they have returned from their search with absolutely nothing.",
                "There might be nothing left to find, or there might be nothing *useful* left to find, after {target} returns empty handed.",
            ],
            "unexpected_type": "DEVELOPER: unexpected type for discovered_name: {name}"
        },
        "feed": {
            "commenced": "{person_name} has gladly begun the task of finding and eating some food. They will be back in {turn_msg}.",
            "fed_A_C_P": "With all fresh food available, {person_name} ate {A} apples, {P} potato, and {C} of a cabbage. They seem less vague than they were the day before. 🌱",
            "fed_A_C": "{person_name} had a rustic meal of {A} apples and {C} of a cabbage. It wasn’t tasty, but it did the job. 🥬",
            "fed_A_P": "{person_name} ate {A} crispy apples and {P} earthy potatoes. Raw food isn't ideal, but it's better than that ration pack rubbish. 💸",
            "fed_C_P": "Today {person_name} had {P} potatoes and {C} of a cabbage. Some fruit would've been nice, but this will do. 🥬",
            "fed_A": "With only apples available, {person_name} had {A} of them. Grow some more crops please, Commander. 🍏",
            "fed_C": "Cabbages are the only thing left. {person_name} had {C} of them. Still better than a ration pack. 😟",
            "fed_P": "It's the starch diet for {person_name}. They just had {P} potatoes today. Pray for them. 🥔",
            "fed_ration": [
                "{person_name} had a ration pack. It tasted like expired glue and regret. They were not grateful for what they were given. Grace was not said. 🍫",
                "{person_name} unwrapped another ration pack. The texture defied explanation. It was eaten in silence, eyes fixed on nothing. 🪵",
                "{person_name} consumed a ration pack. The chocolate had turned white and the meat tasted faintly of rust. They chewed slowly. 🍖",
                "{person_name} forced down a ration pack. Nobody spoke. Nobody asked how it was. It was... fine. Probably. 💬",
                "{person_name} ate their ration alone, seated on an empty crate. They checked the label: it expired more than two years ago. 🧾",
                "{person_name} had a ration pack. They peeled open the foil and found... cheese. Not cheese. A memory of cheese. 🧀"
            ],
            "food_all_used_up": "{person_name} cannot be fed as there is no food left! You will need to grow some crops quickly, Commander.",
            "no_foodstore": "There is no food readily available. Maybe send someone to look for some via the 'explore' command?",
            "no_hungry_humans": "There are no humans who are hungry or worse. Instead you can use 'feed all' if you wish to feed all humans earlier than planned.",
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
            "deceased_warning": "It has been a very long time since {name} had any food. They are approaching death from malnutrition. Please do something - if you can. 😟"
        },
        "mine": {
            "commenced": "The vital task of procuring necessary crystal for power and other things has been given to {target} for {turns} turns. You hope this was a wise decision.",
            "started": "You have sent {name} to the CrystalField to mine some vitally important crystals. PPE: On. Pick: Carried. Outcome: Uncertain.",
            "completed": "{name} has returned from the CrystalField with {red} red, {indigo} indigo and {gold} gold crystals.",
            "cannot_store": "DEVELOPER NOTE: Cannot store crystals. PowerSupply does not exist. (This is where they were to be stashed)."
        },
        "penalty": {
            "reset_abort": "Reset aborted. Your hesitation has cost the colony 1 turn. 🔥"
        },
        "plant": {
            "bed_occupied": "Cannot plant anything in bed {bed}. It is already being used.",
            "commenced": "{target} has vanished into the planting area with a packet of seeds and not much else. Hoping for the best is all you can do at this stage.",
            "crop_matured": "🌱 {planter}'s {crop_type} crop in bed #{bed} has matured!",
            "crop_started": "{target} has somehow managed to plant fast growing {crop}s. Use the 'list food' command to view expected yield time(s).",
            "invalid_bed": "DEVELOPER NOTE: Bed {bed} does not exist. ",
            "invalid_response": "Invalid number of beds chosen: please choose between 0 and {free_beds}.",
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
            "cancel_current": "Cancelling current task: {task}.",
            "invalid_option": "Invalid option. Please choose from the menu.",
            "is_now": "--> {pronoun_str} now {task}.",
            "is_now_idle": "--> {pronoun_str} now --Idle--.",
            "manage_finished": "Finished managing {character}.",
            "no_tasks": "There are no tasks to reorder.",
            "not_queued": "Could not add {task} to {name}'s queue: it is full. Wait until they finish something first or use 'manage queue'.",
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
            "queue_full": "{character}'s queue is full and nothing more can be added. Ye gods, man, ease up!  You can check a human or droid's queue by using 'edit queue'.",
            "queued": "{name} is busy {now_doing}. {task} has been added to their queued tasks.",
            "queued_assign": "{name} is busy {now_doing}. The assignment to the {item} has been queued. Queue management is done via the 'manage' command.",
            "queued_examine": "{name} is busy {now_doing}. The examining of the {item} has been queued.",
            "queued_with_item": "{name} is busy {now_doing}. The {task} task relating to the {item} has been queued.",
            "queued_with_task_data": "{name} is busy {now_doing}. The {task} task with these instructions [{task_data}] has been queued.",
            "removed_task": "{queued_task} task in position {pos} has been removed from {character}'s queue.", 
            "removed_task_abort": "You choose not to remove a task from {character}'s queue.", 
            "removed_task_invalid": "That is an invalid queue position. Select a number between 1 and 3.",
            "removed_task_no_task": "{character} does not have a task at queue position {position}.",
            "reorder_already_at_top": "That task ({task}) is already at the top of {character}'s queue. No changes made.",
            "reorder_invalid": "That is an invalid queue position. Select a number between 1 and 3.",
            "reorder_valid_number_needed": "Please enter a valid number.",
            "reordered_task": "Task {old_pos} ({task}) has been moved to slot {new_pos} in {character}'s queue.",
            "thanks_charge": [
                "{name} seems to blink in gratitude as it wheels off to its charging port. It will be ready to work again in {turns} turns.",
                "{name} will now go and get a much needed top up, and be absent for {turns} turns. Wise decision, Commander",
                "You may have just been spared the sight of {name} just running out of power mid task, and having to be carried manually to the charging ports. It costs {turns} turns, but it's worth it."
            ],
            "thanks_food": [
                "{name} thanks you for considering that {pronoun} might have an empty stomach. They will return to work in {turns} turns.",
                "{name} doesn't even look at you as {pronoun} rushes off to the kitchen to grab whatever is there. You feel underappreciated. In {turns} turns {pronoun} should be in a better mood.",
                "{name} appears chagrined at wanting to eat when there is work to be done, but {pronoun} is grateful for your decision. At least you think so. At least {pronoun} will be back in {turns} turns."
            ],
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
        },
        "reap": {
            "commenced": "{target} has gone to find as many mature raw produce items as possible. Wish them well. The Outpost's survival depends on their success. They will be back in {turns} turns.",
            "harvest_complete": "{target} has returned from the crops area with {items}.",
            "invalid_bed": "DEVELOPER NOTE: crop {crop} has invalid bed {bed}.",
            "no_mature_crops": "{target} has been sent out to collect crops, but nothing is mature yet. Presumably they will ripen very soon and you're just very good at planning.",
        },
        "refuel": {
            "commenced": "You have sent {target} off to put more material into the {item}. Good luck with that.",
            "completed": "Congratulations, Commander! You have successfully engaged {name} in a task to refuel the PowerSupply and they have succeeded.",
            "no_power_supply": "DEVELOPER NOTE: There is no PowerSupply. This shouldn't happen.",
            "no_vials_fail": "{name} has waited for vials to arrive for refueling, but there are still none available. Try again later?",
            "no_vials_warning": "You are sending {name} to refuel the PowerSupply, but with no vials yet created. Let's hope they are inbound. Soon.",
        },  
        "reset": {
            "start": "Resetting the entire Outpost...",
            "done": "\n...the outpost has been reset.\n",
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
            "no_decode": "{name} examines the ShieldManual, but they can't understand the symbols. A decoding tool may be required.",
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
            "explore": "For the 'explore' command, you may only add a name or names, 'all' or 'idle'. Please try again.",
            "mine": "For the 'mine' command, only a single character name (human or droid) is permitted.",
        },
    }

    entry = messages.get(category, {}).get(code)
    if category == "orders" and code == "message":
        return entry
    if isinstance(entry, list):
        entry = random.choice(entry)
    if isinstance(entry, str):
        return entry.format(**kwargs)
    return "[Message not found]"


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