import streamlit as st
import json
from pathlib import Path
import random

# ────────────────────────────── CONFIG ──────────────────────────────
DEFAULT_MAX_PLAYERS = 20
DEFAULT_NUM_COURTS = 3
DATA_FILE = Path("pickleball_data.json")
CONFIG_FILE = Path("pickleball_config.json")

# ────────────────────────────── HELPERS ──────────────────────────────
def load_json(path, default):
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def rerun_app():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ────────────────────────────── LOAD CONFIG & DATA ──────────────────────────────
config = load_json(CONFIG_FILE, {"max_players": DEFAULT_MAX_PLAYERS, "num_courts": DEFAULT_NUM_COURTS})
data = load_json(DATA_FILE, {
    "players": [],
    "queue": [],
    "courts": [[] for _ in range(config["num_courts"])],
    "streaks": {},
    "history": []
})

# ────────────────────────────── CORE LOGIC ──────────────────────────────
def initialize_queue():
    if not data["players"]:
        st.warning("Add players first.")
        return
    data["queue"] = data["players"][:]
    random.shuffle(data["queue"])
    save_json(DATA_FILE, data)
    rerun_app()

def assign_all_courts():
    for i in range(config["num_courts"]):
        if len(data["queue"]) < 4:
            break
        data["courts"][i] = [data["queue"].pop(0) for _ in range(4)]
        for p in data["courts"][i]:
            data["streaks"][p] = 1
    save_json(DATA_FILE, data)
    rerun_app()

def process_court_result(court_index, winning_team):
    court = data["courts"][court_index]
    if len(court) < 4:
        st.warning("Not enough players on this court.")
        return

    winners = court[:2] if winning_team == "Team 1" else court[2:]
    losers = court[2:] if winning_team == "Team 1" else court[:2]

    # Update streaks
    for w in winners:
        data["streaks"][w] = data["streaks"].get(w, 0) + 1
    for l in losers:
        data["streaks"][l] = 0

    # Winners stay on (split), but max 2 games
    staying = []
    for w in winners:
        if data["streaks"][w] < 3:
            staying.append(w)
        else:
            data["streaks"][w] = 0
            data["queue"].append(w)

    if len(staying) == 2:
        new_court = [staying[0]]
        if len(data["queue"]) >= 3:
            new_court += [data["queue"].pop(0), data["queue"].pop(0), staying[1]]
        else:
            new_court += staying
    else:
        new_court = []

    for l in losers:
        data["queue"].append(l)

    data["courts"][court_index] = new_court
    data["history"].append({
        "court": court_index + 1,
        "winners": winners,
        "losers": losers
    })
    save_json(DATA_FILE, data)
    rerun_app()

def reset_all_data():
    if DATA_FILE.exists():
        DATA_FILE.unlink()
    st.session_state.clear()
    rerun_app()

# ────────────────────────────── UI ──────────────────────────────
st.set_page_config(page_title="🏓 Pickleball Open Play Scheduler", layout="wide")
st.title("🏓 Pickleball Open Play Scheduler")

# Sidebar Config
with st.sidebar:
    st.header("⚙️ Configuration")

    st.write("### Session Settings")
    max_players = st.slider("Max Players", 8, 30, config["max_players"], 1)
    num_courts = st.slider("Number of Courts", 1, 5, config["num_courts"], 1)

    if st.button("💾 Save Config"):
        config["max_players"] = max_players
        config["num_courts"] = num_courts
        save_json(CONFIG_FILE, config)
        # Reset courts if changed
        data["courts"] = [[] for _ in range(config["num_courts"])]
        save_json(DATA_FILE, data)
        rerun_app()

    st.divider()

    new_player = st.text_input("Add player name:")
    if st.button("Add Player"):
        if len(data["players"]) >= config["max_players"]:
            st.warning("Maximum player limit reached.")
        elif new_player and new_player not in data["players"]:
            data["players"].append(new_player)
            data["queue"].append(new_player)
            save_json(DATA_FILE, data)
            rerun_app()

    if st.button("Initialize Queue"):
        initialize_queue()
    if st.button("Assign all courts"):
        assign_all_courts()
    if st.button("Reset everything"):
        reset_all_data()

# Display Queue
st.subheader("🎯 Player Queue")
if data["queue"]:
    st.write(", ".join(data["queue"]))
else:
    st.write("Queue is empty — add players or initialize.")

# Display Courts
st.subheader("🏟️ Courts")
cols = st.columns(config["num_courts"])
for i, col in enumerate(cols):
    with col:
        st.markdown(f"### Court {i+1}")
        if not data["courts"][i]:
            st.info("No game assigned.")
        else:
            court = data["courts"][i]
            st.write(f"**Team 1:** {court[0]} & {court[1]}")
            st.write(f"**Team 2:** {court[2]} & {court[3]}")
            winner = st.radio(
                f"Select winner for Court {i+1}",
                ["None", "Team 1", "Team 2"],
                key=f"winner_{i}"
            )
            if winner != "None":
                if st.button(f"Submit result for Court {i+1}", key=f"submit_{i}"):
                    process_court_result(i, winner)

# History
st.subheader("📜 Match History")
if data["history"]:
    for match in reversed(data["history"][-10:]):
        st.write(
            f"**Court {match['court']}** — Winners: {', '.join(match['winners'])} | "
            f"Losers: {', '.join(match['losers'])}"
        )
else:
    st.write("No matches played yet.")
