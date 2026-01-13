import random
import os
import sys, gc
import time
import ujson
import machine
from lib import display
from lib.hydra import config
from lib.device import Device
from lib import userinput

from font import vga1_8x16 as midfont

# --- import graphics ---

try:
    from .gfx import moon
except ImportError:
    from apps.invocatio.gfx import  moon

try:
    from .gfx import ritual
except ImportError:
    from apps.invocatio.gfx import ritual

try:
    from .gfx import ritual_2
except ImportError:
    from apps.invocatio.gfx import  ritual_2

# --- globals for i/o ---

LOG_FILE = "log.txt"
LOG_ON   = 1
DBG_MODE = True

DISPLAY = display.Display()
CONFIG = config.Config()

COLOR_BG = CONFIG.palette[2]
COLOR_FG = CONFIG.palette[8]
COLOR_CTH_GREEN = 1120
COLOR_BLK = 0
COLOR_WHT = 65535
COLOR_RED = 47137
COLOR_ERR = CONFIG.palette[9]    # orange?

_DISPLAY_HEIGHT = Device.display_height
_DISPLAY_WIDTH  = Device.display_width

_CHAR_WIDTH = const(8)
_CHAR_HEIGHT = const(8)

CH_W = _CHAR_WIDTH
CH_H = _CHAR_HEIGHT

SH_Y = (CH_H*7)+5 # Y for second "half" of the screen
INTERLINE = 2

MAX_COL = _DISPLAY_WIDTH // _CHAR_WIDTH
MAX_ROW = _DISPLAY_HEIGHT // _CHAR_HEIGHT

INPUT = userinput.UserInput()

# --- log system ---

try:
    fullpath = __file__
    i = fullpath.rfind("/")     # find the last '/'
    if i == -1:
        SCRIPT_DIR = ""
    else:
        SCRIPT_DIR = fullpath[:i]
except:
    print("Exception rised for fullpath = __file__")
    SCRIPT_DIR = "/sd/apps"

LOG_FILE = SCRIPT_DIR + "/" + LOG_FILE

def file_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError as e:
        return False

def clean_log():
    if LOG_ON < 1:
        return
    try:
        os.remove(LOG_FILE)
    except:
        pass

def log(msg):
    if LOG_ON < 1:
        return
    try:
        timestamp = time.ticks_ms()
        with open(LOG_FILE, "a") as f:
            f.write("[{} ms] {}\n".format(timestamp, msg))
    except:
        pass

def delete_if_exists(txt_file):
    try:
        if not txt_file.startswith("/"):
            txt_file = "/" + txt_file
        full_path = SCRIPT_DIR + txt_file
        if file_exists(full_path):
            os.remove(full_path)
            if DBG_MODE: log("File {} deleted.".format(full_path))
        return 0
    except:
        pass

# --- close ---
def exit_game():
    print("exit_game() triggered")
    log("exit_game() triggered")
    machine.reset()

# --- output ---

def clear_screen():
    DISPLAY.fill(COLOR_BLK)

def refresh_screen():
    DISPLAY.show()

def clear_line(row):
    y = row * _CHAR_HEIGHT
    DISPLAY.rect(0, y, DISPLAY.width, _CHAR_HEIGHT, COLOR_BLK, fill=True)

def clear_from_line(row):
    y = row * (_CHAR_HEIGHT)
    log("clear_from_line({})".format(row))
    DISPLAY.rect(0, row, _DISPLAY_WIDTH, (_DISPLAY_HEIGHT-row), COLOR_BLK, fill=True)
    #DISPLAY.show()


def draw_text(x, y, txt, col=COLOR_FG):
    DISPLAY.text(txt, x, y, col)

def draw_text_ln(x: int, y: int, txt: str, clr=COLOR_FG):
    lines = txt.split("\n")
    cy = y
    for line in lines:
        DISPLAY.text(line, x, cy, clr)
        cy += CH_H + INTERLINE

def draw_h_line(x, y, length, color=COLOR_FG):
    DISPLAY.hline(x, y, length, color)
# --- input ---

def get_line():
    input_data = []
    while True:
        keys = INPUT.get_new_keys()
        keys = [x for x in keys if x not in ('ALT', 'CTL', 'FN', 'SHIFT', 'OPT')] # Strip invisible.

        if 'SPC' in keys:
            keys = list(map(lambda x: x if x != 'SPC' else ' ', keys)) # Expose spaces.

        while 'BSPC' in keys:
            if keys.index('BSPC') == 0:
                if len(input_data) > 0:
                    input_data.pop(-1)
                keys.pop(0)
            else:
                keys.pop(keys.index('BSPC') - 1)
                keys.pop(keys.index('BSPC'))

        if 'UP' in keys or 'DOWN' in keys:
            pass
        if 'LEFT' in keys or 'RIGHT' in keys:
            pass
        if 'ENT' in keys:
            before_ent = keys[:keys.index('ENT')]
            input_data.extend(before_ent)
            return ''.join(input_data)
        elif 'G0' in keys or 'ESC' in keys:
            input_data = []
        else:
            input_data.extend(keys)
            # print letter
            draw_text((len(input_data)*CH_W),(MAX_ROW-1)*CH_H, keys)
            refresh_screen()

def mh_input(msg, clr=COLOR_FG):
    row = ((MAX_ROW-1)*CH_H)-CH_H
    clear_line(row)
    draw_text(0, row, msg, clr)
    refresh_screen()
    u_input = get_line()
    return u_input

# --- GRAPHICS ---

def show_illustration(picture):
    illustrations = {
        "moon": (moon, 32, 16, 0),
        "ritual": (ritual, 98, 0, 65528),
        "ritual_2": (ritual_2, 98, 0, 65528)
    }
    if picture not in illustrations:
        return 1
    bitmap_data, width, y, key_val = illustrations[picture]
    x = (_DISPLAY_WIDTH - width) // 2
    clear_screen()
    DISPLAY.bitmap(bitmap_data, x, y, key=key_val)
    mh_input("Press [OK] to continue...")


# ---------- GAME ----------

TOWN_NAME = "Ashridge"
STATE_FILE = "state.txt"
YEAR = 1921

class settings:
    def __init__(self, town_name, state_file):
        self.town_name = town_name
        self.state_file = state_file

class game_state:
    def __init__(self, turn, year, month, population, faith, fear, favor, sacrifices, stored_food, ritual_materials, cult_power, insight):
        self.turn = turn
        self.year = year
        self.month = month
        self.population = population
        self.faith = faith
        self.fear = fear
        self.favor = favor
        self.sacrifices = sacrifices
        self.stored_food = stored_food
        self.ritual_materials = ritual_materials
        self.cult_power = cult_power
        self.insight = insight

cfg = settings(TOWN_NAME, STATE_FILE)
state = game_state(1, YEAR, "February", 120, 35, 15, 20, 0, 400, 3, 10, 0)

# --- EVENTS ---

events = [
    { 
        "text": "Child of a farmer disappeared.\nVillagers suspect the cult.",
        "options": [
            {"label": "Sacrifice another villager.", "effects": {"fear": -10, "faith": -5, "population": -1}},
            {"label": "Sacrifice the child.", "effects": {"favor": +15, "fear": +15, "population": -1}},
            {"label": "Ignore the situation.", "effects": {"fear": +10}},
        ]
    },
    {  
        "text": "Old man claims he hears voices\nand wants to join the cult.",
        "options": [
            {"label": "Accept and initiate him.", "effects": {"faith": +10}},
            {"label": "Sacrifice him.", "effects": {"favor": +10, "fear": +5}},
            {"label": "Expel him from the town.", "effects": {}},
        ]
    },
    {
        "text": "An eye shaped shadow appears.\nVillagers are frightened.",
        "options": [
            {"label": "A miracle! Hold a festival.", "effects": {"faith": +15, "stored_food": -30}},
            {"label": "Perform a clarification ritual.", "effects": {"favor": +10, "fear": +5}},
            {"label": "Paint over the shadow.", "effects": {"fear": -10, "faith": -10}},
        ]
    },
]

# --- GAME SAVE / LOAD ---

def save_state(file_name):
    try:
        with open(file_name, "w") as f:
            ujson.dump(state, f)
        draw_text(CH_W, (MAX_ROW-1)*CH_H, "Game saved.")
        refresh_screen()
    except Exception as e:
        draw_text(CH_W, (MAX_ROW-1)*CH_H, "Saving error.")
        log("save_state(): Saving error: {}".format(e))

def load_state(file_name):
    global state
    full_path = SCRIPT_DIR + file_name
    if file_exists(full_path):
        choice = mh_input("Save state found. Load state? (y/n): ").strip().lower()
        if choice == "y":
            try:
                with open(file_name, "r") as f:
                    state = ujson.loads(f)
                draw_text(CH_W, (MAX_ROW-1)*CH_H, "State loaded.")
            except Exception as e:
                draw_text(CH_W, (MAX_ROW-1)*CH_H, "Loading error.")
                state = game_state(1, YEAR, "February", 120, 35, 15, 20, 0, 400, 3, 10, 0)
        else:
            state = game_state(1, YEAR, "February", 120, 35, 15, 20, 0, 400, 3, 10, 0)
    else:
        state = game_state(1, YEAR, "February", 120, 35, 15, 20, 0, 400, 3, 10, 0)

# --- CORE FUNCTIONS ---


def random_number(a, b):
    if a >= b:
        log("random_number(): ERROR: Smaller number should by specified first. Returning -1.")
        return -1
    return random.randint(a, b)

def present_info():
    DISPLAY.rect(8*CH_W, 0, len(cfg.town_name)*CH_W, CH_H, COLOR_CTH_GREEN, fill=True)
    draw_text(0,0, f"Town of {cfg.town_name} – Turn {state.turn}/12") # 🌘
    draw_h_line(0, CH_H+2, _DISPLAY_WIDTH, COLOR_CTH_GREEN)
    draw_text(0, (CH_H*2)+3, f"Population: {state.population} | Faith: {state.faith}")
    draw_text(0, (CH_H*3)+3, f"Fear: {state.fear} | Fav: {state.favor} | Food: {state.stored_food}")
    draw_text(0, (CH_H*4)+3, f"Food: {state.stored_food} | Ritual Tools: {state.ritual_materials}")
    draw_text(0, (CH_H*5)+3, f"Cult Power: {state.cult_power} | Insight: {state.insight}")
    draw_h_line(0, (CH_H*6)+5, _DISPLAY_WIDTH, COLOR_CTH_GREEN)


def apply_effects(state_object, effects):
    for attribute_name, value_change in effects.items():
        current_value = getattr(state_object, attribute_name)
        new_value = current_value + value_change
        final_value = max(0, new_value)
        setattr(state_object, attribute_name, final_value)

def check_risk():
    clear_from_line(SH_Y)
    if state.fear >= 80 and state.faith <= 30:
        draw_text_ln(0, SH_Y+CH_H+INTERLINE,"The villagers are on the verge\nof rebellion!") # ⚠️
    if state.fear >= 100:
        clear_line(3)
        draw_text(0, SH_Y+(CH_H*3)+INTERLINE, "REBELLION! The people rise up!") # 🔥
        draw_text_ln(0, SH_Y+(CH_H*4)+INTERLINE, "ENDING:\nYou were killed by the mob.") # 💀
        get_line()
        delete_if_exists(cfg.state_file)
        exit_game()

def end_game():
    clear_from_line(SH_Y)
    draw_text(0,SH_Y+CH_H+INTERLINE, f"END OF GAME – Year {state.year}") # 🔚
    if state.favor > 95 and state.fear > 90:
        draw_text_ln(0, SH_Y+(CH_H*2)+INTERLINE, "They came... but not as you hoped.\nYour mind could not handle it.") # 🤯
    elif state.favor > 80 and state.faith > 70 and state.fear < 50:
        draw_text_ln(0, SH_Y+(CH_H*2)+INTERLINE, "The Descent of the Depths has occurred.\nThe cult triumphs.") # 🌑
    elif state.favor > 50 and state.fear < 60:
        draw_text_ln(0, SH_Y+(CH_H*2)+INTERLINE, "Silence Beyond. You survived.\nBut you're unsure it was worth it.") # 🕯️
    else:
        draw_text_ln(0, SH_Y+CH_H, "Town’s Doom.\nYou were not worthy.") # 🔥
    delete_if_exists(cfg.state_file)
    exit_game()

# --- TURN FUNCTIONS ---

def feed_population():
    consumed = state.population * 2
    state.stored_food -= consumed
    draw_text(0, SH_Y, f"Consumed {consumed} food.") # 🍽️ 
    if state.stored_food < 0:
        draw_text(0, SH_Y+CH_H+INTERLINE,"Not enough food!") # ⚠️
        draw_text_ln(0, SH_Y+(CH_H*2)+INTERLINE,"People are starving,\nfaith drops!")
        state.faith = max(0, state.faith - 10)
        state.fear += 10
        state.population = max(0, state.population - 5)
        state.stored_food = 0
    t = mh_input("Press [OK] to continue...")

def perform_sacrifices():
    try:
        s = int(mh_input("How many people sacrifice?")) # 👁️
        s = max(0, min(s, 10, state.population))
    except ValueError:
        s = 0
    state.sacrifices = s
    state.population -= s
    state.favor += s * 3
    state.fear += s * 2
    state.cult_power += s
    clear_from_line(SH_Y)
    draw_text(0,SH_Y+CH_H+INTERLINE, f"{s} sacrificed. Favor +{s*3}") # 🩸
    draw_text(0,SH_Y+(CH_H*2)+INTERLINE, f"Fear +{s*2}, Cult Power +{s}")
    refresh_screen()
    t = mh_input("Press [OK] to continue...")

def choose_action():
    draw_text(0, SH_Y,"Choose an additional action:") # ⚙️
    draw_text(0, SH_Y+CH_H,"1. Gather food")
    draw_text(0, SH_Y+(CH_H*2)+INTERLINE,"2. Search for ritual materials") # (+1 material)
    draw_text(0, SH_Y+(CH_H*3)+INTERLINE,"3. Knowledge ritual (+ins, -m)") # (+1 insight, -1 material)
    draw_text(0, SH_Y+(CH_H*4)+INTERLINE,"4. Power ritual (+fav, -m)    ") # (+5 favor, -2 materials)
    try:
        action = int(mh_input("Your choice: "))
        if action == 1:
            # state.stored_food += 50
            rnd_nmbr = random_number((state.stored_food//2),(state.population*2))
            state.stored_food += rnd_nmbr
            draw_text(0, SH_Y+(CH_H*5)+INTERLINE, f"Gathered food: {rnd_nmbr}") # 🥔
        elif action == 2:
            state.ritual_materials += 1
        elif action == 3 and state.ritual_materials >= 1:
            show_illustration("ritual")
            state.ritual_materials -= 1
            state.insight += 1
        elif action == 4 and state.ritual_materials >= 2:
            show_illustration("ritual_2")
            state.ritual_materials -= 2
            state.favor += 5
            state.cult_power += 2
    except ValueError:
        pass

def trigger_event():
    event = random.choice(events)
    E_Y = SH_Y - (2*CH_H) # print event info from this point
    clear_from_line(E_Y)
    refresh_screen()
    draw_text(0, E_Y, "Event:") # 📜 may need line breaks here
    #draw_text(0, SH_Y+CH_H+INTERLINE, f"{event["text"]}")
    draw_text_ln(0, E_Y+CH_H+INTERLINE, f"{event["text"]}")
    for i, opt in enumerate(event["options"]):
        draw_text(0, (E_Y+(CH_H*4)+INTERLINE)+(CH_H*i), f" {i+1}. {opt['label']}")
    try:
        choice = int(mh_input("Your choice: ")) - 1
        if 0 <= choice < len(event["options"]):
            apply_effects(state, event["options"][choice]["effects"])
    except ValueError:
        pass

# --- MAIN LOOP ---

def main():
    clean_log()
    log("Game started.")
    load_state(cfg.state_file)
    while state.turn <= 12:
        # --- new round, report on feeding population ---
        clear_screen()
        present_info()
        feed_population()
        # --- monthly sacrifices ---
        show_illustration("moon")
        clear_screen()
        present_info()
        perform_sacrifices()
        # -------------
        clear_screen()
        present_info()
        choose_action()
        # -------------
        clear_screen()
        present_info()
        trigger_event()
        check_risk()
        state.cult_power = max(0, state.cult_power - 1)
        save_state(cfg.state_file)
        state.turn += 1
    # -----------------
    clear_screen()
    present_info()
    end_game()


main()