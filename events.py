# events.py

from constants import TURN_MESSAGE_LIMIT, AMBIENT_MSG_LIMITER
from lore.lore_ingame import get_turn_message
from lore.lore_story import get_story_message
from lore.user_interface import msg_info

def add_turn_event(task_package, event_type, priority, **data):
    """
    Add a structured event to the current turn.

    event_type:
        A short identifier describing what happened,
        e.g. "item_found", "fed", "charged", "task_completed".

    priority:
        Integer from 1 to 10.
        Lower numbers are more important.

    data:
        Event-specific fields such as character, item,
        amount, task_type, etc.
    """

    event = {
        "type": event_type,
        "priority": priority,
        **data
    }

    task_package.setdefault("turn_events", []).append(event)

    return task_package


def build_end_of_turn_message(task_package):
    """
    Build a concise end-of-turn narrative summary from structured turn events.

    For now:
    - sort events by priority
    - render Explore events
    - limit output to 5 sentences

    More renderers will be added later.
    """
    turns_elapsed = task_package["counters"]["turns"]

    grouped_events = {}
    events = task_package.get("turn_events", [])

    if events:
        # Lower number = higher priority.
        sorted_events = sorted(
            events,
            key=lambda event: event.get("priority", 10)
        )

        # Group the events and print them
        grouped_events = group_turn_events(sorted_events)

        for group in grouped_events:
            msg =  f"Grouped Event:  Type = {group["event_type"]} -- Result = {group["result"]}\n"
            msg += f"                Priority = {group["priority"]} -- Length = {len(group["events"])}"
            msg_info(msg, turns_elapsed)

    # Now do the all important selection of events
    lines = []
    lines = select_and_render_turn_events(grouped_events, task_package)

    return lines, task_package


def debug_display_turn_events(lines, task_package):
    turns_elapsed = task_package["counters"]["turns"]
    events = task_package.get("turn_events", [])
    if not events and not lines:
        msg_info("DEBUG - No end of turn events to display.", turns_elapsed)
        return

    msg_info(f"   Lines:", turns_elapsed)
    for line in lines:
        msg_info(f"      {line}\n", turns_elapsed)

    return task_package


def group_turn_events(events):
    groups = {}

    for event in events:
        event_type = event.get("type", "")
        result = event.get("result", "")

        # Additional grouping attributes
        subtype = None

        if event_type == "eat" and result == "started":
            subtype = event.get("meal_urgency", "normal")

        elif event_type == "examine":
            subtype = event.get("examine_type", "normal")

        # Shield events represent distinct story developments.
        # Towing has individual actor relationships.
        # Both are kept separate.
        if event_type in ("shield", "tow"):
            subtype = len(groups)

        group_key = (event_type, result, subtype)

        if group_key not in groups:
            groups[group_key] = {
                "event_type": event_type,
                "result": result,
                "priority": event.get("priority", 10),
                "events": []
            }

        group = groups[group_key]

        group["events"].append(event)

        group["priority"] = min(
            group["priority"],
            event.get("priority", 10)
        )

    return sorted(
        groups.values(),
        key=lambda group: group["priority"]
    )


def clear_turn_events(task_package):
    task_package["turn_events"] = []
    return task_package


def join_naturally(items):
    """
    Join a list of strings using natural English punctuation.

    Examples:
        ["Fen"] -> "Fen"
        ["Fen", "Mike"] -> "Fen and Mike"
        ["Fen", "Mike", "Carrie"] -> "Fen, Mike, and Carrie"
    """

    if not items:
        return ""

    if len(items) == 1:
        return items[0]

    if len(items) == 2:
        return f"{items[0]} and {items[1]}"

    return ", ".join(items[:-1]) + f", and {items[-1]}"


def lowercase_first(text):
    if not text:
        return text

    return text[0].lower() + text[1:]


def lowercase_first_minus_period(text):
    if not text:
        return text

    text = text.strip()

    if text.endswith("."):
        text = text[:-1]

    return text[0].lower() + text[1:]


def select_and_render_turn_events(grouped_events, task_package, max_lines=5):
    """
    Select and render grouped turn events according to priority.

    Priority rules:
        1-3: Always display.
        4-6: Display if space remains.
        7-9: Display only if no priority 1-6 events exist.
        10:  Reserved for ambient lore.

    Returns:
        list[str]
    """
    EVENT_RENDERERS = {
        "shield": render_shield_events,
        "explore": render_explore_events,
        "examine": render_examine_events,
        "plant": render_plant_events,
        "eat": render_eating_events,
        "charge": render_charge_events,
        "mine": render_mine_events,
        "reap": render_reap_events,
        "refuel": render_refuel_events,
        "tow": render_tow_events,
        "assign": render_assign_events,
    }
    turns_elapsed = task_package["counters"]["turns"]

    lines = []

    # Groups are expected to arrive sorted, but ensure this.
    grouped_events = sorted(
        grouped_events,
        key=lambda group: group.get("priority", 10)
    )

    # Determine whether important events occurred.
    important_events_exist = any(
        group["priority"] <= 6
        for group in grouped_events
    )

    for group in grouped_events:

        priority = group["priority"]
        event_type = group["event_type"]
        result = group["result"]

        # -------------------------------------------------
        # PRIORITY 10 - Reserved for ambient lore
        # -------------------------------------------------
        if priority >= 10:
            continue

        # -------------------------------------------------
        # PRIORITY 7-9 - Only on quiet turns
        # -------------------------------------------------
        if priority >= 7 and important_events_exist:
            continue

        # -------------------------------------------------
        # PRIORITY 4-9 - Respect the line limit
        # -------------------------------------------------
        if priority >= 4 and len(lines) >= max_lines:
            continue

        # -------------------------------------------------
        # FIND THE APPROPRIATE RENDERER
        # -------------------------------------------------
        renderer = EVENT_RENDERERS.get(event_type)

        if renderer is None:
            print(
                f"DEBUG - No renderer for event type: {event_type}"
            )
            continue

        # Render only the events belonging to this group.
        rendered_lines = renderer(group["events"])

        # Remove any empty messages defensively.
        rendered_lines = [
            line for line in rendered_lines
            if isinstance(line, str) and line.strip()
        ]

        if not rendered_lines:
            continue

        # -------------------------------------------------
        # PRIORITY 1-3 - Always keep every line
        # -------------------------------------------------
        if priority <= 3:
            lines.extend(rendered_lines)

        # -------------------------------------------------
        # PRIORITY 4-9 - Use remaining space
        # -------------------------------------------------
        else:
            remaining = max_lines - len(lines)

            lines.extend(rendered_lines[:remaining])
       
        msg_info(f"DEBUG - Selected {event_type} / {result} | Priority {priority} | Total lines {len(lines)}", turns_elapsed)


    # ------------------------------------------------------------------------------------
    # AMBIENT LORE - Only when there is narrative space and if nothing major has happened
    # ------------------------------------------------------------------------------------
    critical_event_exists = any(
        group.get("priority", 10) <= 3
        for group in grouped_events
    )

    remaining = max_lines - len(lines)

    if (remaining >= AMBIENT_MSG_LIMITER and not critical_event_exists):
        ambient_msg = add_ambient_text(task_package)
        if ambient_msg:
            lines.append(ambient_msg)

    return lines


def add_ambient_text(task_package):
    # More sophisticated checking to occur in here later on - including analysing events, characters, etc.
    events = task_package.get("turn_events", [])

    # Only do this for now
    msg = get_story_message("ambient", "generic")

    return msg


def finalise_and_clear_turn_events(task_package):
    lines, task_package = build_end_of_turn_message(task_package)

    debug_display_turn_events(lines, task_package)

    task_package = clear_turn_events(task_package)

    return task_package


def render_shield_events(events):
    """
    Convert shield turn events into concise narrative lines.

    Returns:
        list[str]
    """

    shield_events = [
        event for event in events
        if event.get("type") == "shield"
    ]

    if not shield_events:
        return []
    lines = []

    # -- SHIELD ASSIGN EVENT ---
    shield_assign_events = [
        event for event in shield_events
        if (event.get("result") == "started")
    ]

    if shield_assign_events:
        for event in shield_assign_events:
            name = event.get("name", "Someone")
            lines.append(get_turn_message("shield", "assigned", name=name))

    return lines


def render_explore_events(events):
    """
    Convert explore turn events into concise narrative lines.

    Returns:
        list[str]
    """

    explore_events = [
        event for event in events
        if event.get("type") == "explore"
    ]

    if not explore_events:
        return []

    found_events = [
        event for event in explore_events
        if event.get("result") == "found"
    ]

    nothing_events = [
        event for event in explore_events
        if event.get("result") == "nothing"
    ]

    started_events = [
        event for event in explore_events
        if event.get("result") == "started"
    ]

    lines = []

    # ---------------------------------------------------------
    # ITEMS FOUND
    # ---------------------------------------------------------
    if found_events:
        found_parts = []

        for event in found_events:
            name = event.get("name", "Someone")
            discovered = event.get("discovered", "something")
            category = event.get("category", "")
            item_class = event.get("item_class", "portable")

            if category == "essential":
                if item_class == "portable":
                    found_parts.append(get_turn_message("explore", "found_essential", name=name, item=discovered))
                elif item_class == "fixed_installation":
                    found_parts.append(get_turn_message("explore", "found_essential_fixed", name=name, item=discovered))
                elif item_class == "external_location":
                    found_parts.append(get_turn_message("explore", "found_essential_external", name=name, item=discovered))

            elif category in ("chain", "replacement"):
                if item_class == "portable":
                    found_parts.append(get_turn_message("explore", "found_replacement_or_chain", name=name, item=discovered))
                elif item_class == "fixed_installation":
                    found_parts.append(get_turn_message("explore", "found_replacement_or_chain_fixed", name=name, item=discovered))
                elif item_class == "external_location":
                    found_parts.append(get_turn_message("explore", "found_replacement_or_chain_external", name=name, item=discovered))

            else:
                # Junk / low-importance finds.
                if item_class == "portable":
                    found_parts.append(get_turn_message("explore", "found_junk", name=name, item=discovered))
                elif item_class == "fixed_installation":
                    found_parts.append(get_turn_message("explore", "found_junk_fixed", name=name, item=discovered))
                elif item_class == "external_location":
                    found_parts.append(get_turn_message("explore", "found_junk_external", name=name, item=discovered))

        if found_parts:
            lines.append(join_naturally(found_parts) + ".")

    # ---------------------------------------------------------
    # NOTHING FOUND
    # ---------------------------------------------------------
    if nothing_events:
        names = [
            event.get("name", "Someone")
            for event in nothing_events
        ]

        if len(names) == 1:
            lines.append(get_turn_message("explore", "nothing_single", name=names[0]))
        else:
            lines.append(get_turn_message("explore", "nothing_multiple", names=join_naturally(names)))
            
    # ---------------------------------------------------------
    # STARTED
    # ---------------------------------------------------------
    if started_events:
        names = [
            event.get("name", "Someone")
            for event in started_events
        ]

        if len(names) == 1:
            lines.append(get_turn_message("explore", "started_single", name=names[0]))
        else:
            lines.append(get_turn_message("explore", "started_multiple", names=join_naturally(names)))

    return lines


def render_examine_events(events):
    """
    Convert examine turn events into concise narrative lines.

    Returns:
        list[str]
    """

    examine_events = [
        event for event in events
        if event.get("type") == "examine"
    ]

    if not examine_events:
        return []
    lines = []

    completed_events = [
        event for event in examine_events
        if event.get("result") == "completed"
    ]
    
    started_events = [
        event for event in examine_events
        if event.get("result") == "started"
    ]

    # -------------------------------------------------------
    # COMPLETED EVENTS
    # -------------------------------------------------------
    if completed_events:
        examine_msg = ""

        for event in completed_events:
            name = event.get("name", "Someone")
            item = event.get("item", "something")
            category = event.get("category", "")
            examine_type = event.get("examine_type", "normal")
            description = event.get("description", "in good condition.")
            item_class = event.get("item_class", "portable")

            if examine_type == "instant":
                if item_class == "portable":
                    examine_msg = get_turn_message("examine", "instant", name=name, item=item, description=description)
                elif item_class == "fixed_installation":
                    examine_msg = get_turn_message("examine", "instant_fixed", name=name, item=item, description=description)
                elif item_class == "external_location":
                    examine_msg = get_turn_message("examine", "instant_external", name=name, item=item, description=description)
                    
            elif category == "essential":
                if item_class == "portable":
                    examine_msg = get_turn_message("examine", "completed_essential", name=name, item=item, description=description)
                elif item_class == "fixed_installation":
                    examine_msg = get_turn_message("examine", "completed_essential_fixed", name=name, item=item, description=description)
                elif item_class == "external_location":
                    examine_msg = get_turn_message("examine", "completed_essential_external", name=name, item=item, description=description)

            elif category in ("chain", "replacement"):
                if item_class == "portable":
                    examine_msg = get_turn_message("examine", "completed_replacement_or_chain", name=name, item=item, description=description)
                elif item_class == "fixed_installation":
                    examine_msg = get_turn_message("examine", "completed_replacement_or_chain_fixed", name=name, item=item, description=description)
                elif item_class == "external_location":
                    examine_msg = get_turn_message("examine", "completed_replacement_or_chain_external", name=name, item=item, description=description)

            else:
                if item_class == "portable":
                    examine_msg = get_turn_message("examine", "completed_junk", name=name, item=item, description=description)
                elif item_class == "fixed_installation":
                    examine_msg = get_turn_message("examine", "completed_junk_fixed", name=name, item=item, description=description)
                elif item_class == "external_location":
                    examine_msg = get_turn_message("examine", "completed_junk_external", name=name, item=item, description=description)

            if examine_msg:
                lines.append(examine_msg)
       
    # ---------------------------------------------------------
    # STARTED
    # ---------------------------------------------------------
    if started_events:
        names_started = [
            event.get("name", "Someone")
            for event in started_events
        ]
        items_examined = [
            event.get("item", "an item")
            for event in started_events
        ]

        for name in names_started:
            item_name = items_examined[names_started.index(name)]
            lines.append(get_turn_message("examine", "started", name=name, item=item_name))

    return lines


def render_plant_events(events):
    """
    Convert plant turn events into concise narrative lines.

    Returns:
        list[str]
    """

    plant_events = [
        event for event in events
        if event.get("type") == "plant"
    ]

    if not plant_events:
        return []
    lines = []

    started_events = [
        event for event in plant_events
        if event.get("result") == "started"
    ]

    completed_events = [
        event for event in plant_events
        if event.get("result") == "completed"
    ]

    planted_parts = []
    if started_events:
        for event in started_events:
            name = event.get("name", "Someone")
            crop_message = event.get("crop_message", "some crops")

            planted_parts.append(get_turn_message("plant", "started", name=name, crop_message=crop_message))

    if completed_events:
        for event in completed_events:
            name = event.get("name", "Someone")
            crop_message = event.get("crop_message", "some crops")

            planted_parts.append(get_turn_message("plant", "completed", name=name, crop_message=crop_message))

    if planted_parts:
        lines.append(join_naturally(planted_parts))

    return lines


def render_eating_events(events):
    """
    Convert eating turn events into concise narrative lines.

    Returns:
        list[str]
    """

    eat_events = [
        event for event in events
        if event.get("type") == "eat"
    ]

    if not eat_events:
        return []
    lines = []

    # -- STARTED EATING EVENTS - Urgent ---
    started_urgent_events = [
        event for event in eat_events
        if (event.get("result") == "started" and event.get("meal_urgency", "normal") == "urgent")
    ]

    if started_urgent_events:
        names = [
            event.get("name", "Someone")
            for event in started_urgent_events
        ]

        if len(names) == 1:
            lines.append(get_turn_message("eat", "started_urgent_single", name=names[0]))
        else:
            lines.append(get_turn_message("eat", "started_urgent_multiple", names=join_naturally(names)))

    # -- STARTED EATING EVENTS - Normal ---
    started_normal_events = [
        event for event in eat_events
        if (event.get("result") == "started" and event.get("meal_urgency", "normal") == "normal")
    ]

    if started_normal_events:
        names = [
            event.get("name", "Someone")
            for event in started_normal_events
        ]

        if len(names) == 1:
            lines.append(get_turn_message("eat", "started_normal_single", name=names[0]))
        else:
            lines.append(get_turn_message("eat", "started_normal_multiple", names=join_naturally(names)))

    # -- COMPLETED EATING EVENTS ---
    completed_normal_events = [
        event for event in eat_events
        if (event.get("result") == "completed")
    ]

    if completed_normal_events:
        names = [
            event.get("name", "Someone")
            for event in completed_normal_events
        ]

        if len(names) == 1:
            lines.append(get_turn_message("eat", "completed_single", name=names[0]))
        else:
            lines.append(get_turn_message("eat", "completed_multiple", names=join_naturally(names)))

    return lines


def render_charge_events(events):
    """
    Convert charge turn events into concise narrative lines.

    Returns:
        list[str]
    """

    charge_events = [
        event for event in events
        if event.get("type") == "charge"
    ]

    if not charge_events:
        return []
    lines = []

    # -- NO POWER EVENTS --
    no_power_events = [
        event for event in charge_events
        if (event.get("result") == "no_power")
    ]

    if no_power_events:
        names = [
            event.get("name", "Someone")
            for event in no_power_events
        ]
        if len(names) == 1:
            lines.append(get_turn_message("charge", "no_power_single", name=names[0]))
        else:
            lines.append(get_turn_message("charge", "no_power_multiple", names=join_naturally(names)))

    # -- STARTED CHARGING EVENTS ---
    started_events = [
        event for event in charge_events
        if (event.get("result") == "started")
    ]

    if started_events:
        names = [
            event.get("name", "Someone")
            for event in started_events
        ]

        if len(names) == 1:
            lines.append(get_turn_message("charge", "started_single", name=names[0]))
        else:
            lines.append(get_turn_message("charge", "started_multiple", names=join_naturally(names)))

    # -- COMPLETED CHARGING EVENTS ---
    completed_events = [
        event for event in charge_events
        if (event.get("result") == "completed")
    ]

    if completed_events:
        names = [
            event.get("name", "Someone")
            for event in completed_events
        ]

        if len(names) == 1:
            lines.append(get_turn_message("charge", "completed_single", name=names[0]))
        else:
            lines.append(get_turn_message("charge", "completed_multiple", names=join_naturally(names)))

    return lines



def render_mine_events(events):
    """
    Convert mine turn events into concise narrative lines.

    Returns:
        list[str]
    """

    mine_events = [
        event for event in events
        if event.get("type") == "mine"
    ]

    if not mine_events:
        return []
    lines = []

    # -- STARTED MINING EVENTS ---
    started_events = [
        event for event in mine_events
        if (event.get("result") == "started")
    ]

    if started_events:
        names = [
            event.get("name", "Someone")
            for event in started_events
        ]

        if len(names) == 1:
            lines.append(get_turn_message("mine", "started_single", name=names[0]))
        else:
            lines.append(get_turn_message("mine", "started_multiple", names=join_naturally(names)))

    # -- COMPLETED MINING EVENTS ---
    completed_events = [
        event for event in mine_events
        if (event.get("result") == "completed")
    ]

    if completed_events:
        red = indigo = gold = 0
        names = [
            event.get("name", "Someone")
            for event in completed_events
        ]
        for event in completed_events:
            red += event.get("red", 0)
            indigo += event.get("indigo", 0)
            gold += event.get("gold", 0)

        if len(names) == 1:
            lines.append(get_turn_message("mine", "completed_single", name=names[0], R=red, I=indigo, G=gold))
        else:
            lines.append(get_turn_message("mine", "completed_multiple", names=join_naturally(names), R=red, I=indigo, G=gold))


    return lines


def render_reap_events(events):
    """
    Convert reap turn events into concise narrative lines.

    Returns:
        list[str]
    """

    reap_events = [
        event for event in events
        if event.get("type") == "reap"
    ]

    if not reap_events:
        return []
    lines = []

    # -- STARTED REAPING EVENTS ---
    started_events = [
        event for event in reap_events
        if (event.get("result") == "started")
    ]

    if started_events:
        names = [
            event.get("name", "Someone")
            for event in started_events
        ]

        if len(names) == 1:
            lines.append(get_turn_message("reap", "started_single", name=names[0]))
        else:
            lines.append(get_turn_message("reap", "started_multiple", names=join_naturally(names)))

    # -- COMPLETED REAPING EVENTS ---
    completed_events = [
        event for event in reap_events
        if (event.get("result") == "completed")
    ]

    if completed_events:
        potatoes = onions = apples = avocados = 0
        names = [
            event.get("name", "Someone")
            for event in completed_events
        ]
        produce = []
        for event in completed_events:
            potatoes += event.get("potatoes", 0)
            onions += event.get("onions", 0)
            apples += event.get("apples", 0)
            avocados += event.get("avocados", 0)

        if potatoes > 0:
            produce.append(f"{potatoes} potatoes")
        if onions > 0:
            produce.append(f"{onions} onions")
        if apples > 0:
            produce.append(f"{apples} apples")
        if potatoes > 0:
            produce.append(f"{avocados} avocados")

        if len(names) == 1:
            lines.append(get_turn_message("reap", "completed_single", name=names[0], food_collection=join_naturally(produce)))
        else:
            lines.append(get_turn_message("reap", "completed_multiple", names=join_naturally(names), food_collection=join_naturally(produce)))


    return lines


def render_refuel_events(events):
    """
    Convert refuel turn events into concise narrative lines.

    Returns:
        list[str]
    """

    refuel_events = [
        event for event in events
        if event.get("type") == "refuel"
    ]

    if not refuel_events:
        return []
    lines = []

    # -- STARTED REFUELING EVENTS ---
    started_events = [
        event for event in refuel_events
        if (event.get("result") == "started")
    ]

    if started_events:
        names = [
            event.get("name", "Someone")
            for event in started_events
        ]
        red = indigo = gold = total_power = 0
        for event in started_events:
            red += event.get("red", 0)
            indigo += event.get("indigo", 0)
            gold += event.get("gold", 0)
            total_power += event.get("total_power", 0)

        if len(names) == 1:
            lines.append(get_turn_message("refuel", "started_single", name=names[0], R=red, I=indigo, G=gold, total_power=total_power))
        else:
            lines.append(get_turn_message("refuel", "started_multiple", names=join_naturally(names), R=red, I=indigo, G=gold, total_power=total_power))

    # -- COMPLETED REFUELING EVENTS ---
    completed_events = [
        event for event in refuel_events
        if (event.get("result") == "completed")
    ]

    if completed_events:
        names = [
            event.get("name", "Someone")
            for event in completed_events
        ]
        total_power = 0
        for event in completed_events:
            total_power += event.get("total_power", 0)

        if len(names) == 1:
            lines.append(get_turn_message("refuel", "completed_single", name=names[0], total_power=total_power))
        else:
            lines.append(get_turn_message("refuel", "completed_multiple", names=join_naturally(names), total_power=total_power))


    return lines


def render_tow_events(events):
    """
    Convert tow turn events into concise narrative lines.

    Returns:
        list[str]
    """

    tow_events = [
        event for event in events
        if event.get("type") == "tow"
    ]

    if not tow_events:
        return []
    lines = []

    # -- NO IDLE HUMAN EVENTS --
    no_idle_human_events = [
        event for event in tow_events
        if (event.get("result") == "no_idle_humans")
    ]

    if no_idle_human_events:
        names = [
            event.get("name", "Someone")
            for event in no_idle_human_events
        ]
        if len(names) == 1:
            lines.append(get_turn_message("charge", "no_idle_humans_single", name=names[0]))
        else:
            lines.append(get_turn_message("charge", "no_idle_humans_multiple", names=join_naturally(names)))

    # -- STARTED TOWING EVENTS ---
    started_events = [
        event for event in tow_events
        if (event.get("result") == "started")
    ]

    if started_events:
        names = [
            event.get("name", "Someone")
            for event in started_events
        ]
        droids_towed = [
            event.get("droid_towed", "a droid") 
            for event in started_events
            ]

        for name in names:
            droid_towed = droids_towed[names.index(name)]
            lines.append(get_turn_message("tow", "started", name=name, droid=droid_towed))

    # -- COMPLETED TOWING EVENTS ---
    completed_events = [
        event for event in tow_events
        if (event.get("result") == "completed")
    ]

    if completed_events:
        names = [
            event.get("name", "Someone")
            for event in completed_events
        ]
        droids_towed = [
            event.get("droid_towed", "a droid")
            for event in completed_events
        ]

        for name in names:
            droid_towed = droids_towed[names.index(name)]
            lines.append(get_turn_message("tow", "completed", name=name, droid=droid_towed))

    return lines


def render_assign_events(events):
    """
    Convert assign turn events into concise narrative lines.

    Returns:
        list[str]
    """

    assign_events = [
        event for event in events
        if event.get("type") == "assign"
    ]

    if not assign_events:
        return []
    lines = []

    # -- STARTED ASSIGN EVENTS ---
    started_events = [
        event for event in assign_events
        if (event.get("result") == "started")
    ]

    if started_events:
        for event in started_events:
            name = event.get("name", "Someone")
            item_name = event.get("item_name", "an item")
            if event.get("item_name") == "CrystalProcessor":
                red = event.get("red", 0)
                indigo = event.get("indigo", 0)
                gold = event.get("gold", 0)
                lines.append(get_turn_message("assign", "started_CP", name=name, item=item_name, red=red, indigo=indigo, gold=gold))
            elif event.get("item_name") == "ShieldManual":
                lines.append(get_turn_message("assign", "started_SM", name=name, item=item_name))

    # -- COMPLETED ASSIGN EVENTS ---
    completed_events = [
        event for event in assign_events
        if (event.get("result") == "completed")
    ]

    if completed_events:
        for event in completed_events:
            name = event.get("name", "Someone")
            item_name = event.get("item_name", "an item")
            if event.get("item_name") == "CrystalProcessor":
                red = event.get("red", 0)
                indigo = event.get("indigo", 0)
                gold = event.get("gold", 0)
                lines.append(get_turn_message("assign", "completed_CP", name=name, item=item_name, red=red, indigo=indigo, gold=gold))
            elif event.get("item_name") == "ShieldManual":
                lines.append(get_turn_message("assign", "completed_SM", name=name, item=item_name))

    # -- OLD_TERMINAL EVENTS ---
    old_terminal_events = [
        event for event in assign_events
        if event.get("item_name") == "OldTerminal" and event.get("result") == "combo_correct"
    ]

    if old_terminal_events:
        for event in old_terminal_events:
            name = event.get("name", "Someone")
            red = event.get("red", 0)
            indigo = event.get("indigo", 0)
            gold = event.get("gold", 0)
            lines.append(get_turn_message("assign", "completed_OT", name=name, red=red, indigo=indigo, gold=gold))

    return lines


# Keep just in case
"""
    # ---------------------------------------------------------
    # EVENT RENDERERS
    # ---------------------------------------------------------
    shield_lines = render_shield_events(sorted_events)
    if shield_lines:
        lines.extend(shield_lines)
    explore_lines = render_explore_events(sorted_events)
    if explore_lines != []:
        lines.extend(explore_lines)
    examine_lines = render_examine_events(sorted_events)
    if examine_lines:
        lines.extend(examine_lines)
    plant_lines = render_plant_events(sorted_events)
    if plant_lines:
        lines.extend(plant_lines)
    eating_lines = render_eating_events(sorted_events)
    if eating_lines:
        lines.extend(eating_lines)
    charge_lines = render_charge_events(sorted_events)
    if charge_lines:
        lines.extend(charge_lines)
    mine_lines = render_mine_events(sorted_events)
    if mine_lines:
        lines.extend(mine_lines)
    reap_lines = render_reap_events(sorted_events)
    if reap_lines:
        lines.extend(reap_lines)
    refuel_lines = render_refuel_events(sorted_events)
    if refuel_lines:
        lines.extend(refuel_lines)
    tow_lines = render_tow_events(sorted_events)
    if tow_lines:
        lines.extend(tow_lines)
    assign_lines = render_assign_events(sorted_events)
    if assign_lines:
        lines.extend(assign_lines)
"""