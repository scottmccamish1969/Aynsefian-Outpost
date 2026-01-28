# lore_story.py
import random

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from constants import INITIAL_GAMESTATE

def print_orders(gamestate):
    # This is the opening message (from President Axin) the NEW player gets at game start for the first time
    if gamestate == INITIAL_GAMESTATE:
        print(get_story_message("orders", "first_time"))
        answer = input(">> ").strip().lower() 
        if answer == 'y':
            message = get_story_message("orders", "message")
            # If the message is a list of lines, print them one by one
            if isinstance(message, list):
                for line in message:
                    print(line)
            # Otherwise, just print the whole thing
            else:
                print(message)
        else:
            print(get_story_message("orders", "chose_not_to"))

# When they have all 6 tarot cards  
def tarot_set_complete_message():
    return (
        "As you place the final tarot card beside the others, a gentle vibration "
        "moves through the Outpost. The cards align themselves into a silent mandala.\n\n"
        "Lanemu appears in your mind’s periphery, serene and luminous:\n"
        "'You have gathered all six. Though they grant no certainty, "
        "their presence is auspicious. The Outpost remembers.\n"
        "Walk your path with clarity. The Shield listens.'"
    )


# The core of the lore
def get_story_message(category, code, **kwargs):
    messages = {
    "daymessage": {
            "one": [
                "The outpost has come online. The wind outside howls like an old memory. Inside, droids hum and humans try not to shiver. This is day one.",
                "Lanemu’s final words echo in your mind: 'Darkness first. Then form. Then purpose.' You’re not sure which one you’re in yet.",
                "A strange poetry echoes across the comms line: 'For we are no longer seedlings in the soil 🌱 — we are the keepers of our own sky.'"
            ],
            "two": [
                "All valid actions cost turns. Invalid ones? The droid bumped the console again. We understand.",
                "You sit back and stare at the inventory list again. Why is there a crate labelled 'EMERGENCY MUSHROOMS'? Who approved this?"
            ],
            "three": [
                "It's day three and President Axin says that if you don't sort things out soon, he's sending the First Lady — and you REALLY don't want that.",
                "Jinekali’s daily report has come through. It’s just a single line: 'Stop feeding the droids' He added no punctuation. You feel judged.",
                "Salvation’s latest transmission contained one bark, two static bursts, and a long sigh. Somehow, it made more sense than the last five status updates combined."
            ],
            "four": [
                "Did somebody say MGC? First Lady Zarasena: 'Stop eating all the ration packs and start making that blasted shield active!'",
                "The wind is louder today. Carrie swears she heard it say her name. Mike hasn’t slept since. Maybe because he's a droid? Or is he that human over there in the corner, cowering?",
                "Niobe and Karla have entered something called 'Philosophical Standby Mode'. They’ve been staring at the wall for hours. It’s making everyone else nervous."
            ],
            "five": [
                "'Day 5 and we are no closer to establishing a safe outpost' says President Axin Fernea. 'Please make all haste and get it done.",
                "You can feel First Counsel Anathusa's concern from here. She's usually never wrong. It's day 5. MGC will be inbound in maybe 5 days, and not much more. She's bound to be worried.",
                "Your 5th day. You could send a human or a droid out onto the planetary surface and explore, but all they'd find would be howling winds and dust. Don't do that."
            ],
            "six": [
                "Archpriest Lanemu: 'As the principal Aynsefian spiritual advisor, I warn you that I cannot hold time for this many people. You must help *me* now.'",
                "Chief Engineer Jinekali says that once you've found the seeds, the water and the hydroponics room you can plant crops. That's in case there's not enough food there.",
                "One of the droids has rolled through something *sticky* and it's now all over the main floor of the Outpost. Watch your step."
            ],
            "seven": [
                "It's day 7. A whole week. Have you created any bathrooms yet? That might be a good idea.",
                "The Inconflencia MealMaker can make over 1000 meals with minimal ingredients. Yours is set to only three. We don't wish to complicate your life any more than necessary.",
                "Jinekali says that there should be a semi-operational terminal there somewhere that will assist you in getting the shield up."
            ],
            "eight": [
                "First Lady Zarasena: 'I'm counting on you, Commander. You're my only hope.' You picture her in a white shift in a grainy video image. Not appropriate, Commander.",
                "'Hey bud. First Lady Zarasena here. Day eight, huh? Better be doing okay there. You don't want *me* to pay a visit do you?'",
                "When in doubt, cook. When fear is felt, pray. When loud sounds and debris are coming from one section of your compound, run in the opposite direction."
            ],
            "nine": [
                "MGC signals detected on the far edge of the Melcheisa Galaxy. Stay alert.",
                "First Lady Zarasena's voice crackles through static: 'The MGC is coming. I know it. Hold the line.'",
                "IR84U data logs show heightened subspace noise. MGC arrival is now probable.",
                "Chief Engineer Jinekali’s encoded message arrives: 'Cloak everything. The MGC are most likely scouting.'"
            ],
            "ten": [
                "Day 10. The final quiet before the storm?",
                "It's MGC day, otherwise known as day ten. If you’ve enabled the shield, double-check it. If not... pray.",
                "The air is heavy with expectation. The MGC are due, if not overdue. It's day ten, Commander.",
                "President Axin: 'It's day 10. If this message reaches you, Commander, stay hidden. They see more than we thought.'"
            ],
            "generic": [
                "Aryliss and Cyndliss, the Purlinian guardians of ancient Aysnefian lore, welcome you to day {day} and hope that history will treat you kindly.",
                "Jinekali's voice crackles over the comms line: 'Systems green. Power minimal. Do not — I repeat — do not overcharge the droids.'",
                "It is now day {day}. Hope you have that shield up, Commander. The MGC could arrive at any given moment.",
                "'This is President Axin of the Aynsefian society back in the Main City. Status report, Commander. It is day {day}. I'm a bit nervous.'",
                "A loud, thundering boom sounded outside the cave entrance today (day {day}). No-one knows what it was. All structures are still intact, but tensions are heightened.",
                "Zarasena says: 'Uh, it's day {day}. Have you killed any of your humans or blown up any droids yet?'",
                "MGC arrival imminent. Day {day}. They are *overdue*. If shield=none, then prepare to die 💀",
                "Day {day}. Still no sign of the MGC. Maybe they gave up? Yeah, right.",
                "Jinekali reports a long-range scan spike. Day {day}. Cloaking advised. If you have no cloaking, behaving like a teapot is acceptable.",
                "Commander's Log, Day {day}: Paranoia levels rising. The sky... feels wrong.",
                "Satellite 3 just went offline. it is thought to be from a particularly nasty storm. Not good. Day {day}.",
                "Day {day}. A stillness settles. The kind before something breaks. Please don't blame the droids. They are easy targets.",
                "It is now day {day}. The silence is deafening and the droids have begun to rock back and forth.",
                "You have made it to day {day}. We are getting indications that your status is uncertain. Present Axin is most concerned. First Lady Zarasena has gone silent. That is bad.",
                "The wind howls outside the cave entrance. You can even hear it from here today, it's that bad. Is this a sign that day {day} is actually MGC Day?",
                "Salvation can't save you now, Commander, if you don't have that shield up. Do you? We are not getting diagnostics here in the main city.",
                "First Counsel Anathusa says that the MGC is unlikely to ask questions before shooting. It is day {day} and she hopes you will keep that in mind.",
                "A message crackles in over comms. It's Jinekali. You ask who that is. No one answers. The message simply says: 'It's day {day}. Don’t mess up the hydro systems.'"
            ]
        },
        "endgame": {
            "all_dead": "Silence falls upon the Outpost. Every human is gone, and only the hum of cooling circuits remains...\n\n"
                        "Youou must find an *effective* scheme by which to feed your team and keep them alive so that they\n"
                        "can keep working towards establishing effective shielding from the Melcheisa Galactic Council.\n\n"
                        "--== Commander, you have sadly failed in your task of protecting Aysnefian 💀😔 ==--",
            "no_power": "The lights flicker one last time. Power reserves are all gone. The Outpost drifts into eternal night.\n"
                        "With no power to run the Outpost's equipment, the whole scene becomes gradually darker and dustier.\n"
                        "There is no way to power up the Outpost's shield and therefore no defense against the MGC.\n\n"
                        "--== Commander, you have sadly failed in your task of protecting Aysnefian 💀😔 ==--",
            "mgc_arrival_no_shield": "A vast shadow sweeps across the horizon. The MGC has arrived. The Outpost holds its breath... \n"
                                      "... and, the shield was not active. Setting up the shield was your primary goal, Commander.\n"
                                      "At least now, you know this... from the *other side*.\n\n"
                                      "--== Commander, you have sadly failed in your task of protecting Aysnefian 💀😔 ==--",
            "mgc_arrival_shield_failed": "The MGC have found us. The shield kick in to gear with alarming urgency... and.... \n"
                                          "... the shield has failed. The Outpost was exposed. A vital component must have been missing.\n"
                                          "Please check your ShieldManual to make sure you put into the shield EXACTLY what was needed.\n\n"
                                          "--== Commander, you have sadly failed in your task of protecting Aysnefian 💀😔 ==--",
            "restart": "\n===================================================================\n"
                       "GAME OVER — thanks for playing Aynsefian Outpost.\n\nPlease choose the 'reset' command to start again\n"
                       "===================================================================\n",
            "you_win?": "A sky-rending hum floods the Outpost… the MGC has arrived. Have you done enough to thwart them?\n"
                        "This time, your shield flares to life — brilliant, defiant... and totally undetectable.\n"
                        "The Melcheisa Galactic Council hovers for a few hours, then leaves.\n"
                        "President Axin's voice crackles over the comms. 'Congratulations, Commander. Your shield worked.'\n"
                        "You have survived the first pass. For now. 🎉\n\n"
                        "The question is: will the MGC return? Are you willing to bet that they won't? 🧑‍🚀\n\n"
        },
        "orders": {
            "first_time": "\nThere is a message here at the outpost. Would you like to read it (y/n)?",
            "chose_not_to": "Okay then. You're going to wing it. I hope you know what you're doing, Commander.",
            "message": [
                "These orders come directly from your President, Axin Fernea, of the main city of Aynsefian:\n\nWelcome to the Aynsefian Outpost.\n"
                "Commander, this is the rear entrance to the 500km-plus cave we now call home. The front is already guarded — but this\n"
                "rear entrance you are at needs protection. The surrounding rock isn’t stable. You’ll have to improvise.\n\n"
                "Fortunately, there’s an ancient structure here. I've asked Nikse to drop supplies, but don’t assume they’ll be in obvious\n"
                "places. She did her best with what her scout-class gear could manage. No crew. No support. Just you. We don’t have time\n"
                "to be there to help you. Every other human and droid is needed in the main city. Anathusa believes the MGC could be here\n"
                "in 10–15 days. The countdown has started.\n\n"     
                "If they find us, they will kill us. First Lady Zarasena knows — she used to fly with them. She’s my wife. Don’t let her down.\n"
                "She won’t take kindly to screw-ups. This is a one-way line. We’ll send a single message at the end of each day, drawn from\n"
                "your diagnostics. That’s all the power we can spare.\n\nYou’re 200 km away. You’re on your own.\n\n"
                "Chief Engineer Jinekali says you *should* have what you need to get the shield online. We don’t know if it’ll work.\n"
                "Nobody’s coming to help. Not me, not Jinekali, not even Nikse. This is your station to hold.\n\n"        
                "Arlyss and Cindlyss send their regards. Salvation might transmit now and then — listen for him. Lanemu says the signs are\n"
                "unclear. That’s got Zarasena spooked more than anything else.\n\n"
                "You’ve got four humans and four droids. Each has a name. Each human has a threshold. Resources are scarce. Trust, even scarcer.\n"
                "Work. Watch. Wait. I believe in you.\n\n"
                "First Lady Zarasena... 🔥 does not.\n\n"
                "You may re-read these orders any time by typing `read orders`. Messages and logs will be stored for future access.\n"
                "Make this work... or we all meet our Creator together."
            ]
        },
        "no_droids": {
            "day_3": "🟡 Jinekali wants to know why the droids aren't online yet.\n'It's kind of crazy brave to man this outpost without them.\nHave you found the Power Supply yet?'",
            "day_6": "🔴 First Lady Zarasena is getting impatient.\n'Still no droids? You *do* realise they’re the only ones who can decrypt messages, right?\nThe shield, too. Don't be a dumbass. Get those droids workin', man!'"
        },
        "quit": {
            "you_win?": "CONGRATULATIONS on defeating the Melcheisa Galactic Council! Will the result be the same if you try again?",
            "fail": "You did you best, Commander. Maybe events just conspired against you. Give it another try?",
        },
        "start": {
            "opening_message": "\nYou are in charge of this outpost, Commander. It will protect all of Aynsefian.\nYou must keep it running, or we will all die at the hands of the MGC. Please don't fail us!\n"
        }
    }

    entry = messages.get(category, {}).get(code)
    if category == "orders" and code == "message":
        return entry
    if isinstance(entry, list):
        entry = random.choice(entry)
    if isinstance(entry, str):
        return entry.format(**kwargs)
    return "[Message not found]"
