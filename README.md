# ASCII Mystery

**ASCII Mystery** is a terminal-based murder mystery game built in Python. The player takes the role of a detective working with Detective Voss to solve the murder of Victor Holloway by questioning suspects, tracking contradictions, and eventually accusing the killer.

The game uses AI-generated NPC dialogue to make each interrogation feel dynamic. Each character has a distinct personality, hidden motives, relationship stats, and memory of the conversation.

## Story

Victor Holloway has been found dead in his study.

The scene looks like a robbery: scattered papers, an open drawer, and a broken glass near the body. But Detective Voss does not believe the scene is that simple.

The player must question the people closest to Victor, compare their stories, and decide who is lying about more than they admit.

## Features

- Terminal-based murder mystery gameplay
- AI-powered NPC conversations
- Multiple suspects with unique personalities and secrets
- Randomized killer each case
- Detective Voss as a recurring partner and investigation guide
- Character portraits rendered with colored ASCII pixel art
- Relationship stats such as trust, suspicion, respect, and pressure
- Hidden state variables that track clues, confessions, and suspect behavior
- Shared case notes so Voss can react to information gathered from suspects
- Win/loss accusation system

## Characters

### Detective Voss

Your reluctant investigative partner. Voss is blunt, cynical, experienced, and protective in his own rough way. He helps the player reason through motives and contradictions without directly solving the case.

### Evelyn Holloway

Victor Holloway's daughter. Nervous, defensive, and emotionally exhausted. She is hiding financial secrets and may have had a serious conflict with Victor before his death.

### Martin Hale

Victor Holloway's lawyer. Calm, polished, careful, and manipulative. He knows how to control a conversation and redirect suspicion away from himself.

### Clara Whitcomb

The Holloway family housekeeper. Quiet, bitter, guarded, and observant. She has worked in the house for years and knows more than she first admits.

## Requirements

- Python 3.10 or newer recommended
- An OpenAI API key
- Internet connection for AI dialogue generation

Python packages:

```bash
pip install openai
```

If your version uses `python-dotenv`, also install:

```bash
pip install python-dotenv
```

## Setup

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/ascii-mystery.git
cd ascii-mystery
```

Install dependencies:

```bash
pip install openai
```

Set your OpenAI API key.

### Option 1: Environment variable

On Windows Command Prompt:

```cmd
set OPENAI_API_KEY=your_api_key_here
python main.py
```

On PowerShell:

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
python main.py
```

On macOS/Linux:

```bash
export OPENAI_API_KEY=your_api_key_here
python main.py
```

### Option 2: `.env` file

Create a file named `.env` in the same folder as `main.py`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o
```

Then run:

```bash
python main.py
```

## Running the Game

From the project folder:

```bash
python main.py
```

The game starts with an introduction to the crime scene. Press space to continue through the opening scenes.

## Commands

| Command | Description |
|---|---|
| `<text>` | Speak to the current NPC |
| `characters` | Show available characters |
| `question <name>` | Switch to another NPC |
| `image` | Display the current NPC portrait |
| `accuse <name>` | Accuse a suspect |
| `help` | Show the command list |
| `reset` | Start a new case |
| `quit` / `exit` | Exit the game |

Example commands:

```text
question evelyn
Where were you when Victor died?
question martin
Did Victor change his will recently?
question voss
Evelyn is hiding something, but I am not sure it is murder.
accuse clara
```

## Suspect IDs

Use these names with `question` and `accuse`:

```text
evelyn
martin
clara
```

Voss cannot be accused because he is the player's partner.

## How the Game Works

At the start of each case, the game randomly chooses the killer from the suspect list. The player does not know who the killer is.

Each NPC has:

- A public role
- A personality
- A speech style
- Hidden motives
- Relationship stats
- Hidden state variables
- Recent conversation memory

The AI receives the current character state and responds in JSON. The game then updates memory, relationship stats, hidden states, and shared case notes.

Detective Voss does not receive the actual killer's identity. Instead, he receives shared case notes and gives detective-style reasoning based on what the player has discovered.

## Development Notes

Ideas for future improvements:

- Add clue inspection commands
- Add a case notebook command
- Add locations such as the study, kitchen, library, and side entrance
- Add physical evidence items
- Add endings based on how much evidence the player found
- Add a local AI mode using GPT4All, llama.cpp, or Ollama
- Add save/load support for longer cases
- Add difficulty settings that affect how easily suspects reveal information
