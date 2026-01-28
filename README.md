# Aynsefian Outpost 🛸🌌

*A text-based survival and exploration game set in the far reaches of the Aynsefian system.*

## 🚀 Overview

You are the commander of a stranded human-droid team at an isolated outpost on a desolate planet.  
Survival is not guaranteed. You must manage food, energy, knowledge, and trust to reactivate the **Cloaking Shield** before it's too late...

Crafted with love, lore, and strategy, **Aynsefian Outpost** is a turn-based Python game combining:
- 🧠 Deep strategy and resource management
- 📚 Rich lore and uncoverable secrets
- 🤖 Human and droid character interactions
- ⏳ Urgency-driven decision making
- 🛠️ Modular, clean code designed for expandability

## 🧪 How to Run

### 🔧 Requirements
- Python 3.11+
- `colorama` (for terminal color support)

Install dependencies:
```bash
pip install colorama
```

### ▶️ Launch the Game
```bash
python main.py
```

(We recommend using **VS Code** or a terminal with wide screen support for best experience.)

## 🕹️ Gameplay Highlights

- 🔄 Command your team using simple text commands (`explore`, `mine`, `plant`, `feed`, `status`, etc.)
- 📦 Discover rare items, solve logic puzzles, and unlock the shield
- 🧍‍♀️🦾 Balance needs of humans and droids (hunger, power, morale)
- 🎯 Make or break decisions in an unfolding timeline
- 💡 Dynamic feedback, task queuing, and emergent events

## 📁 Project Structure

```
├── main.py                  # Game launcher
├── commands.py              # Command parsing and handling
├── tasks.py                 # All character task logic
├── queuing.py               # Queue system for human/droid actions
├── planting.py              # Hydroponics and food system
├── resources.py             # Mining and resource logic
├── status.py                # Status display and logging
├── utils.py                 # Shared utility functions
├── constants.py             # Global constants and settings
├── endgame.py               # Victory conditions
├── lore/                    # In-game story and UI flavour
└── outpost_config.json      # Player-facing config options
```

## 🛠️ Developer Notes

- Version: `v0.9.x` (nearing `v1.0`)
- Turn-based architecture with robust logging
- Code is modular and designed for collaborative extension
- Work in progress! Feedback and pull requests welcome

## 🌌 The Task is Before You

> “The Melcheisa Galactic Council does not right now know where we are. 
> We must keep our location a secret in case they decide to search this planet.
> The Shield at the cave entrance is the only way to do this.
> I am counting on you, Commander, to protect our fledgling society.
> You must succeed or we are all doomed. I have placed my faith in you."
> -- Sincerely, President Axin Fernea, leader of the new Aynsefian peoples

The Outpost is alive. You are not alone. But we need you to succeed.

## 🤝 Credits

**Lead Developer:** [Scott McCamish](https://github.com/scottmccamish1969)  
**AI Co-Creator & Lore Scribe:** Therie 🕯️  
Special thanks to the Builders who came before.

## 📜 License

This project is open-source under the [MIT License](LICENSE).
