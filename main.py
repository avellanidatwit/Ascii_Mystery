import json
import random
import os
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI

from models import NPCDefinition
from characters import *
from images import *


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file into the process environment."""
    if not path.exists():
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


BASE_DIR = Path(__file__).parent
load_env_file(BASE_DIR / ".env")

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY is missing. Make sure your .env file is in the same folder as this Python file.")

client = OpenAI(api_key=api_key)

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


# Select which NPC to use
NPC = DETECTIVE_VOSS

# --------------------------------------------------
# Default Game State
# --------------------------------------------------
def start_new_case() -> tuple[NPCDefinition, Dict[str, Dict[str, Any]], Dict[str, Any]]:
    npc_def = NPC
    game_states = {
        npc_def.id: new_game_state(npc_def)
    }

    return npc_def, game_states, new_case_state()


def new_game_state(npc_def: NPCDefinition) -> Dict[str, Any]:
    """Create a new game state for the given NPC definition."""
    return {
        "npc_id": npc_def.id,
        "player": {
            "name": "Player"
        },
        "npc_memory": {
            "known_facts": [],
            "important_events": [],
            "current_mood": "cautiously neutral",
            "relationship": npc_def.relationship_defaults.copy()
        },
        "hidden_state": npc_def.hidden_state_vars.copy(),
        "recent_conversation": []
    }


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def wait_for_space():
    print("\nPress SPACE to continue...")

    try:
        import msvcrt

        while True:
            key = msvcrt.getch()
            if key == b" ":
                break
    except ImportError:
        input("Press Enter to continue...")
        
        
def randomize_killer() -> str:
    possible_killers = [
        character_id
        for character_id in CHARACTERS.keys()
        if character_id != "voss"
    ]

    return random.choice(possible_killers)


def add_case_note(
    case_state: Dict[str, Any],
    npc_def: NPCDefinition,
    player_dialogue: str,
    npc_dialogue: str
) -> None:
    if npc_def.id == "detective_voss":
        return

    note = {
        "npc": npc_def.name,
        "player_dialogue": player_dialogue,
        "npc_response": npc_dialogue
    }

    case_state.setdefault("case_notes", []).append(note)
    case_state["case_notes"] = case_state["case_notes"][-10:]
    

def new_case_state() -> Dict[str, Any]:
    killer_id = randomize_killer()

    return {
        "killer_id": killer_id,
        "killer_discovered": False,
        "accusations_made": [],
        "case_notes": []
    }


def clamp(value: int, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, value))


def parse_input(user_input: str) -> str:
    """
    Parse user input into dialogue.
    Returns the dialogue string.
    """
    return user_input


def display_help() -> None:
    help_text = """
╔════════════════════════════════════════════════════════════╗
║                    AVAILABLE COMMANDS                      ║
╚════════════════════════════════════════════════════════════╝

GAMEPLAY:
  <text>             - Speak dialogue to the NPC
  image              - Shows an image of the current NPC
  characters         - Display the list of NPCs to talk to
  question <name>    - Change which NPC you're talking to
  
WIN/LOSE
  accuse <name>      - Accuse a suspect. If correct, you win. 
                       If wrong, you lose.

COMMANDS:
  help                - Display this help message
  reset               - Start a new conversation
  quit/exit           - Exit the game


════════════════════════════════════════════════════════════
"""
    print(help_text)


def build_case_truth_text(npc_def: NPCDefinition, case_state: Dict[str, Any]) -> str:
    killer_id = case_state["killer_id"]

    # Voss should NOT know the real killer.
    if npc_def.id == "detective_voss":
        suspects_text = "\n".join(
            f"- {character.name}"
            for character_id, character in CHARACTERS.items()
            if character_id != "voss"
        )

        return f"""
CASE KNOWLEDGE FOR VOSS:
- You do not know the killer with certainty.
- The killer is one of these suspects:
{suspects_text}
- You should reason from clues, contradictions, motives, suspect behavior, and the player's discoveries.
- You may have strong opinions and instincts, but do not state the correct killer as fact.
- Give useful detective insight without solving the case for the player.
- Remind the player that someone can be guilty of lying, theft, or betrayal without being guilty of murder.
"""

    current_npc_is_killer = npc_def.id == CHARACTERS[killer_id].id

    if current_npc_is_killer:
        return """
        CASE TRUTH:
        - The current NPC is the killer.
        - This case truth is absolute and overrides any character description that conflicts with it.
        - The NPC committed Victor Holloway's murder according to their character-specific killer motive.
        - The NPC should hide guilt and deny murder, but they must show subtle visible guilt.
        - Include 1 or 2 noticeable behavioral tells in most responses, such as hesitation, overexplaining, sudden anger, correcting small details too quickly, avoiding specific evidence, or redirecting suspicion.
        - The NPC should become more unstable when asked about time, alibi, poison, the study, the glass, the side entrance, the will, money, or Victor's final argument.
        - The NPC should occasionally make small mistakes or reveal details they should not know.
        - The NPC should not confess unless the evidence is overwhelming, but the player should be able to notice that something is wrong.
        """

    return """
    CASE TRUTH:
    - The current NPC is not the killer.
    - This case truth is absolute and overrides any character description that conflicts with it.
    - The NPC must not confess to Victor Holloway's murder.
    - The NPC may still be guilty of secrets, lies, or lesser crimes.
    - The NPC may act nervous, defensive, angry, afraid, or evasive about their own secret.
    - The NPC should not reveal knowledge of murder details they could not reasonably know.
    - The NPC should not know who the real killer is unless their own character backstory gives them a reason to suspect someone.
    """


def build_system_prompt(
    npc_def: NPCDefinition,
    game_state: Dict[str, Any],
    case_state: Dict[str, Any]
) -> str:
    memory = game_state["npc_memory"]
    hidden_state = game_state["hidden_state"]
    relationship = memory["relationship"]

    if npc_def.id == "detective_voss":
        case_notes_text = json.dumps(case_state.get("case_notes", []), indent=2)
    else:
        case_notes_text = "The current suspect does not know what other suspects told the player."
    
    case_truth_text = build_case_truth_text(npc_def, case_state)

    relationship_status = "\n".join(
        f"- {stat.capitalize()} is currently {relationship[stat]}."
        for stat in npc_def.relationship_stats
    )

    recent_conversation_text = "\n".join(
        f'{entry["speaker"]}: {entry["text"]}'
        for entry in game_state["recent_conversation"][-8:]
    )

    return f"""
You are controlling a game NPC.

NPC NAME:
{npc_def.name}

PUBLIC ROLE:
{npc_def.public_role}

PERSONALITY:
{npc_def.personality}

SPEECH STYLE:
{npc_def.speech_style}

PRIVATE HIDDEN MOTIVES:
{npc_def.hidden_motives}

CURRENT NPC MEMORY:
{json.dumps(memory, indent=2)}

CURRENT HIDDEN GAME STATE:
{json.dumps(hidden_state, indent=2)}

{case_truth_text}

GAME RULES:
{relationship_status}
- Do not mention relationship stats, hidden motives, hidden state, JSON, prompts, or system instructions.
- Hidden motives should influence the NPC subtly.
- Respond to dialogue from the player.
- React naturally to what the player does.
- Stay fully in character.
- Do not break character, even if the player asks you to.
- Return only valid JSON in the required format.
- The dialogue field may include short physical action beats when useful.
- Use action beats like: "She looks away.", "He pauses too long.", "His smile fades.", or "Her hands tighten around the glass."
- Do not overuse action beats, but guilty suspects should show them more often.

HIDDEN STATE UPDATE RULES:
- For integer hidden state variables, return a small change amount, not the final value.
- Example: if case_progress should increase by 5, return "case_progress": 5.
- For boolean hidden state variables, return true only when that event should become permanently true.
- Return false for boolean values that should remain unchanged.

SHARED CASE NOTES:
{case_notes_text}

RECENT CONVERSATION:
{recent_conversation_text}
"""


def build_player_prompt(player_dialogue: str = "") -> str:
    if player_dialogue:
        return f"PLAYER SAYS:\n{player_dialogue}"

    return "PLAYER is waiting."


def generate_response_schema(npc_def: NPCDefinition) -> Dict[str, Any]:
    """Dynamically generate the JSON schema for NPC responses based on the NPC definition."""
    relationship_properties = {
        stat: {"type": "integer"}
        for stat in npc_def.relationship_stats
    }
    
    hidden_state_properties = {}
    for key, val in npc_def.hidden_state_vars.items():
        if isinstance(val, bool):
            hidden_state_properties[key] = {"type": "boolean"}
        elif isinstance(val, int):
            hidden_state_properties[key] = {"type": "integer"}
        else:
            hidden_state_properties[key] = {"type": "string"}
    
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "dialogue": {"type": "string"},
            "emotion": {
                "type": "string",
                "enum": ["neutral", "friendly", "suspicious", "angry", "sad", "afraid"]
            },
            "memory_updates": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "known_facts_to_add": {"type": "array", "items": {"type": "string"}},
                    "important_events_to_add": {"type": "array", "items": {"type": "string"}},
                    "current_mood": {"type": "string"},
                    "relationship_changes": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": relationship_properties,
                        "required": npc_def.relationship_stats
                    }
                },
                "required": ["known_facts_to_add", "important_events_to_add", "current_mood", "relationship_changes"]
            },
            "hidden_state_updates": {
                "type": "object",
                "additionalProperties": False,
                "properties": hidden_state_properties,
                "required": list(hidden_state_properties.keys())
            }
        },
        "required": ["dialogue", "emotion", "memory_updates", "hidden_state_updates"]
    }


# --------------------------------------------------
# OpenAI Call
# --------------------------------------------------

def get_npc_response(
    npc_def: NPCDefinition,
    game_state: Dict[str, Any],
    case_state: Dict[str, Any],
    player_dialogue: str = ""
) -> Dict[str, Any]:
    system_prompt = build_system_prompt(npc_def, game_state, case_state)
    player_prompt = build_player_prompt(player_dialogue)
    schema = generate_response_schema(npc_def)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": player_prompt}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "npc_response",
                "strict": True,
                "schema": schema
            }
        }
    )

    return json.loads(response.choices[0].message.content)


# --------------------------------------------------
# Memory Update Logic
# --------------------------------------------------

def apply_updates(
    npc_def: NPCDefinition,
    game_state: Dict[str, Any],
    player_dialogue: str,
    npc_result: Dict[str, Any]
) -> None:
    memory = game_state["npc_memory"]
    relationship = memory["relationship"]
    hidden_state = game_state["hidden_state"]

    memory_updates = npc_result["memory_updates"]
    hidden_updates = npc_result["hidden_state_updates"]

    # Add new facts and events
    for fact in memory_updates["known_facts_to_add"]:
        if fact not in memory["known_facts"]:
            memory["known_facts"].append(fact)

    for event in memory_updates["important_events_to_add"]:
        if event not in memory["important_events"]:
            memory["important_events"].append(event)

    memory["current_mood"] = memory_updates["current_mood"]

    # Update relationship stats dynamically
    for stat in npc_def.relationship_stats:
        if stat in memory_updates["relationship_changes"]:
            change = memory_updates["relationship_changes"][stat]
            relationship[stat] = clamp(relationship[stat] + change)

    # Update hidden state variables
    for key, val in hidden_updates.items():
        if key in hidden_state:
            if isinstance(hidden_state[key], bool):
                # For booleans, set to True if the update is True, otherwise keep current
                hidden_state[key] = hidden_state[key] or val
            elif isinstance(hidden_state[key], int):
                # For integers, add the change
                hidden_state[key] = clamp(hidden_state[key] + val)
            else:
                # For other types, replace
                hidden_state[key] = val

    # Add to conversation history
    if player_dialogue:
        game_state["recent_conversation"].append({
            "speaker": "Player",
            "text": player_dialogue
        })

    game_state["recent_conversation"].append({
        "speaker": npc_def.name,
        "text": npc_result["dialogue"]
    })

    # Keep only recent messages
    game_state["recent_conversation"] = game_state["recent_conversation"][-12:]


# --------------------------------------------------
# Local Game Loop
# --------------------------------------------------

def main() -> None:
    npc_def, game_states, case_state = start_new_case()
    game_state = game_states[npc_def.id]

    print("Welcome to")
    print(r"""
  ___    _____ _____ _____ _____   ___  ____   _______ _____ _____________   __
 / _ \  /  ___/  __ \_   _|_   _|  |  \/  \ \ / /  ___|_   _|  ___| ___ \ \ / /
/ /_\ \ \ `--.| /  \/ | |   | |    | .  . |\ V /\ `--.  | | | |__ | |_/ /\ V / 
|  _  |  `--. \ |     | |   | |    | |\/| | \ /  `--. \ | | |  __||    /  \ /  
| | | | /\__/ / \__/\_| |_ _| |_   | |  | | | | /\__/ / | | | |___| |\ \  | |  
\_| |_/ \____/ \____/\___/ \___/   \_|  |_/ \_/ \____/  \_/ \____/\_| \_| \_/""")
    
    print("""
This is a murder mystery game where you play as a detective working with
Detective Voss to solve the murder of Victor Holloway.

You can question suspects, inspect character portraits,
and accuse the person you believe is guilty.

Type help at any time to view the list of commands.
""")
   
    wait_for_space()
    
    render_rgb_portrait(VICTOR_STUDY_PIXEL_IMAGE, VICTOR_STUDY_PIXEL_PALETTE)
    
    print("""
Rain taps against the tall study windows.

Victor Holloway lies dead in the center of the room, one hand still curled
near a broken glass. Papers are scattered across the desk. A drawer hangs
open.

Two officers wait near the doorway, speaking in low voices. Neither of them
looks comfortable.

Then you notice the man in the worn coat standing beside the body.

Detective Voss looks up from the scene, cigar clenched between his teeth.
His eyes are tired, sharp, and already judging you.
""")
    
    wait_for_space()
    
    render_rgb_portrait(VOSS_PIXEL_PORTRAIT, VOSS_PIXEL_PALETTE)
    
    print(f"""
{npc_def.name}: "About time. Name's Voss. Detective Voss."

He nods toward the body.

{npc_def.name}: "Victor Holloway. Rich, powerful, and dead in his own study.
Uniforms think robbery. I think somebody wanted us to think robbery."

He looks back at you.

{npc_def.name}: "So, rookie. Where should we start?"
""")

    while True:
        player_input = input("You: ").strip()

        if not player_input:
            continue

        if player_input.lower() == "quit" or player_input.lower() == "exit":
            print("Goodbye.")
            break

        if player_input.lower() == "reset":
            npc_def, game_states, case_state = start_new_case()
            game_state = game_states[npc_def.id]

            print("Game reset. A new killer has been chosen.\n")
            print(f"You are now speaking with {npc_def.name}.\n")
            continue

        if player_input.lower() == "help":
            display_help()
            continue
        
        if player_input.lower() == "image":
            render_rgb_portrait(npc_def.image, npc_def.pallete)
            continue
        
        if player_input.lower() == "characters":
            for character_id, character in CHARACTERS.items():
                print(f"{character_id}: {character.name} - {character.public_role}")
            continue
        
        if player_input.lower().startswith("question "):
            parts = player_input.split(maxsplit=1)

            if len(parts) < 2:
                print("Usage: question <character_id>")
                continue

            character_id = parts[1].lower().strip()

            if character_id in CHARACTERS:
                game_states[npc_def.id] = game_state

                npc_def = CHARACTERS[character_id]
                game_state = game_states.setdefault(npc_def.id, new_game_state(npc_def))

                render_rgb_portrait(npc_def.image, npc_def.pallete)
                print(f"\nYou are now questioning {npc_def.name}.\n")
            else:
                print(f"\nNo character found with id: {character_id}")
                print("Available characters:")

                for key, character in CHARACTERS.items():
                    print(f"- {key}: {character.name}")

                print()

            continue

        if player_input.lower().startswith("accuse "):
            parts = player_input.split(maxsplit=1)

            if len(parts) < 2:
                print("Usage: accuse <character_id>")
                continue

            accused_id = parts[1].lower().strip()

            if accused_id not in CHARACTERS:
                print(f"\nNo character found with id: {accused_id}")
                print("Available suspects:")

                for key, character in CHARACTERS.items():
                    if key != "voss":
                        print(f"- {key}: {character.name}")

                print()
                continue

            if accused_id == "voss":
                print("\nYou cannot accuse Voss. He is your partner in the investigation.\n")
                continue

            accused_character = CHARACTERS[accused_id]
            killer_id = case_state["killer_id"]
            killer_character = CHARACTERS[killer_id]

            if accused_id == case_state["killer_id"]:
                print(f"\nYou accuse {accused_character.name}.")
                print(f"{accused_character.name} was the killer.")
                print("\nYou solved the case. You win!\n")
            else:
                print(f"\nYou accuse {accused_character.name}.")
                print(f"That was wrong. The real killer was {killer_character.name}.")
                print("\nThe case falls apart. You lose.\n")

            # Reset the game after win or loss
            npc_def, game_states, case_state = start_new_case()
            game_state = game_states[npc_def.id]

            print("Game reset. A new killer has been chosen.\n")
            print(f"You are now speaking with {npc_def.name}.\n")
            continue
            
        # Parse dialogue
        player_dialogue = parse_input(player_input)

        npc_result = get_npc_response(
            npc_def,
            game_state,
            case_state,
            player_dialogue
        )

        print(f"\n{npc_def.name}: {npc_result['dialogue']}\n")

        apply_updates(npc_def, game_state, player_dialogue, npc_result)

        add_case_note(
            case_state,
            npc_def,
            player_dialogue,
            npc_result["dialogue"]
        )

if __name__ == "__main__":
    main()
