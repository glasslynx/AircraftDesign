"""
Dino runner game - no installs needed (uses tkinter, which comes with Python).

Controls
    Space / Up / W     jump (also starts the game; double jump if you own it)
    Down / S           duck; in the air it makes you dive down fast
    X                  use a slow-mo (if you have one)
    B                  open the shop (start / game-over screen)
    In the shop:       Up/Down to choose, Space/Enter to buy or equip, B/Esc back
    Q / Esc            quit

Coins, upgrades and the high score are saved in dino_save.json next to this file.

Run with:  python dino_game.py
"""
import json
import math
import random
import time
import tkinter as tk
from pathlib import Path

# ---------------------------------------------------------------- settings ---
WIDTH, HEIGHT = 900, 300
GROUND_Y = 250                 # y of the ground line
DT = 1 / 60                    # fixed physics step (game runs the same on any PC)
GRAVITY = 0.9
JUMP_SPEED = -15.5
DIVE_SPEED = 9.0               # downward speed when you duck in the air
START_SPEED = 8.0
SPEED_GAIN = 0.0016            # speed increase per frame
MAX_SPEED = 22.0
LEVEL_LENGTH = 400             # distance points per level (new obstacles unlock)
DAY_LENGTH = 400               # distance points between day and night
BOOST_TIME = 330               # frames a UFO boost lasts (5.5 s)
SOUND = True                   # system "bell" on new level / record
SAVE_FILE = Path(__file__).resolve().parent / "dino_save.json"

COIN_DAY, COIN_NIGHT = "#e6a700", "#ffd23f"
CONFETTI = ["#ff5c5c", "#ffb84d", "#ffe14d", "#5cd65c", "#4db8ff", "#b366ff"]

# landscapes: colours for day and night, plus the background decoration
LANDS = {
    "land_desert": {"name": "Desert", "decor": "dunes",
                    "day": {"bg": "#f7f7f7", "fg": "#535353", "cloud": "#e0e0e0",
                            "hill": "#ece6d8"},
                    "night": {"bg": "#16181d", "fg": "#d7d7d7", "cloud": "#2c3038",
                              "hill": "#22252c"}},
    "land_forest": {"name": "Forest", "decor": "trees",
                    "day": {"bg": "#dcefff", "fg": "#2f4a2f", "cloud": "#ffffff",
                            "hill": "#a6d39a"},
                    "night": {"bg": "#0e1822", "fg": "#cfe8cf", "cloud": "#1c2a36",
                              "hill": "#173022"}},
    "land_snow": {"name": "Snow", "decor": "snow",
                  "day": {"bg": "#e6f1fa", "fg": "#3d4a5c", "cloud": "#ffffff",
                          "hill": "#fbfdff"},
                  "night": {"bg": "#0f1726", "fg": "#dfe8f5", "cloud": "#243146",
                            "hill": "#2a3850"}},
    "land_mars": {"name": "Mars", "decor": "craters",
                  "day": {"bg": "#f2c7a5", "fg": "#5a2a1a", "cloud": "#e8b08a",
                          "hill": "#d9895c"},
                  "night": {"bg": "#1d0f0f", "fg": "#f0c0a0", "cloud": "#3a1f1a",
                            "hill": "#3d1d14"}},
}

# shop: id, name, description, price (list = price per level), kind, max
SHOP = [
    ("shield", "Shield", "survive one hit (used automatically)", 30, "stack", 3),
    ("slowmo", "Slow-mo", "press X: world at half speed for 4 s", 25, "stack", 3),
    ("doublejump", "Double jump", "jump again once in mid-air", 120, "perm", 1),
    ("magnet", "Coin magnet", "pulls coins towards you (3 levels)", [60, 120, 240],
     "level", 3),
    ("coinx2", "Double coins", "every coin is worth 2", 200, "perm", 1),
    ("ufo_luck", "UFO radar", "the UFO visits twice as often", 150, "perm", 1),
    ("land_desert", "World: Desert", "the classic dunes", 0, "land", 1),
    ("land_forest", "World: Forest", "green hills and pine trees", 80, "land", 1),
    ("land_snow", "World: Snow", "white hills and falling snow", 120, "land", 1),
    ("land_mars", "World: Mars", "red planet, craters, two moons", 200, "land", 1),
    ("skin_classic", "Skin: Classic", "the original", 0, "skin", 1),
    ("skin_green", "Skin: Green", "a fresh green dino", 50, "skin", 1),
    ("skin_ghost", "Skin: Ghost", "spooky and blue", 150, "skin", 1),
    ("skin_gold", "Skin: Gold", "pure flex", 400, "skin", 1),
]
SKIN_COLOR = {"skin_classic": None, "skin_green": "#3fae49",
              "skin_ghost": "#8fa8ff", "skin_gold": "#e0a800"}

# UFO boosts: name, colour
BOOSTS = [("STAR POWER", "#ffd23f"), ("SUPER MAGNET", "#ff5c5c"),
          ("DOUBLE SCORE", "#5cd65c"), ("MOON JUMP", "#b366ff"),
          ("TINY DINO", "#4db8ff"), ("COIN FRENZY", "#ffb84d")]


def mix(c1, c2, t):
    """Blend two hex colours, t = 0 -> c1, t = 1 -> c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    t = min(max(t, 0.0), 1.0)
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def load_save():
    data = {"high": 0, "coins": 0, "shield": 0, "slowmo": 0, "doublejump": 0,
            "magnet": 0, "coinx2": 0, "ufo_luck": 0,
            "skins": ["skin_classic"], "skin": "skin_classic",
            "lands": ["land_desert"], "land": "land_desert"}
    try:
        data.update(json.loads(SAVE_FILE.read_text()))
    except Exception:
        pass
    return data


class DinoGame:
    def __init__(self, root):
        self.root = root
        root.title("Dino Runner")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                highlightthickness=0)
        self.canvas.pack()
        root.bind("<KeyPress>", self.key_press)
        root.bind("<KeyRelease>", self.key_release)

        self.save = load_save()
        self.stars = [(random.randint(0, WIDTH), random.randint(10, 160),
                       random.choice([1, 1, 2])) for _ in range(40)]
        self.shop_index = 0
        self.shop_scroll = 0
        self.message = ""
        self.reset()
        self.state = "start"       # start -> running -> over ; shop
        self.last_time = time.perf_counter()
        self.acc = 0.0
        self.loop()

    # ------------------------------------------------------------ game state ---
    def reset(self):
        self.dino_x = 60
        self.dino_y = GROUND_Y     # y of the dino's feet
        self.vel_y = 0.0
        self.ducking = False
        self.duck_held = False
        self.air_jumps = 0
        self.speed = START_SPEED
        self.distance = 0.0
        self.bonus = 0
        self.combo = 0
        self.run_coins = 0
        self.obstacles = []
        self.coins = []
        self.particles = []
        self.popups = []
        self.next_spawn = 70
        self.next_coin = 100
        self.clouds = [[random.randint(0, WIDTH), random.randint(30, 120)]
                       for _ in range(4)]
        self.hills = []
        x = -50
        while x < WIDTH + 200:
            x = self.add_hill(x)
        self.snow = [[random.uniform(0, WIDTH), random.uniform(0, GROUND_Y),
                      random.uniform(0.6, 1.6)] for _ in range(45)]
        self.ground_offset = 0
        self.frame = 0
        self.night_t = 0.0
        self.level = 1
        self.shake = 0
        self.invuln = 0            # frames of invulnerability after a shield hit
        self.slowmo = 0            # frames of slow-mo left
        self.record_beaten = False
        self.banner = None         # (text, frames left, colour)
        # random encounters and the UFO
        self.event = None          # (name, frames left)
        self.next_event = random.randint(700, 1100)
        self.ufo = None
        self.next_ufo = self.ufo_interval()
        self.orb = None            # boost capsule dropped by the UFO
        self.boost = None          # (name, frames left, colour)

    def ufo_interval(self):
        lo, hi = (500, 900) if self.save["ufo_luck"] else (1000, 1800)
        return random.randint(lo, hi)

    def add_hill(self, x):
        w = random.randint(160, 320)
        h = random.randint(25, 70)
        trees = [random.uniform(0.15, 0.85) for _ in range(random.randint(1, 4))]
        crater = random.uniform(0.25, 0.7)
        self.hills.append(dict(x=x, w=w, h=h, trees=trees, crater=crater))
        return x + w * random.uniform(0.55, 0.9)

    @property
    def score(self):
        return int(self.distance) + self.bonus

    def write_save(self):
        try:
            SAVE_FILE.write_text(json.dumps(self.save, indent=1))
        except Exception:
            pass

    def boost_is(self, name):
        return self.boost is not None and self.boost[0] == name

    # ----------------------------------------------------------------- input ---
    def key_press(self, e):
        k = e.keysym.lower()
        if self.state == "shop":
            self.shop_key(k)
            return
        if k in ("q", "escape"):
            self.root.destroy()
        elif k in ("space", "up", "w"):
            self.on_jump()
        elif k in ("down", "s"):
            self.duck_press()
        elif k == "x":
            self.use_slowmo()
        elif k == "b" and self.state in ("start", "over") and not self.shake:
            self.state, self.message = "shop", ""

    def key_release(self, e):
        if e.keysym.lower() in ("down", "s"):
            # Linux key auto-repeat sends release+press pairs while held:
            # only stop ducking if no new press arrives within a moment.
            self.duck_held = False
            self.root.after(40, self._duck_check)

    def _duck_check(self):
        if not self.duck_held:
            self.ducking = False

    def on_jump(self):
        if self.state in ("start", "over"):
            if self.shake:
                return
            self.reset()
            self.state = "running"
        elif self.state == "running":
            jump = JUMP_SPEED * (1.2 if self.boost_is("MOON JUMP") else 1.0)
            if self.on_ground():
                self.vel_y = jump
                self.air_jumps = self.save["doublejump"]
                self.dust(self.dino_x + 15, GROUND_Y, 6)
            elif self.air_jumps > 0:
                self.air_jumps -= 1
                self.vel_y = jump * 0.85
                self.burst(self.dino_x + 18, self.dino_y, 8, ["#ffffff", "#bbbbbb"],
                           speed=3, life=15)

    def duck_press(self):
        self.duck_held = True
        self.ducking = True
        if self.state == "running" and not self.on_ground():
            self.vel_y = max(self.vel_y, DIVE_SPEED)     # dive down

    def use_slowmo(self):
        if self.state == "running" and self.save["slowmo"] > 0 and not self.slowmo:
            self.save["slowmo"] -= 1
            self.write_save()
            self.slowmo = 240
            self.show_banner("SLOW-MO", color="#4db8ff")

    def on_ground(self):
        return self.dino_y >= GROUND_Y

    # ------------------------------------------------------------------ shop ---
    def item_price(self, item):
        iid, _, _, price, kind, mx = item
        if kind == "level":
            lvl = self.save[iid]
            return price[lvl] if lvl < mx else None
        return price

    def owned_list(self, kind):
        return self.save["skins"] if kind == "skin" else self.save["lands"]

    def item_status(self, item):
        iid, _, _, _, kind, mx = item
        if kind in ("skin", "land"):
            if self.save[kind] == iid:
                return "EQUIPPED"
            return "owned" if iid in self.owned_list(kind) else ""
        if kind == "perm":
            return "owned" if self.save[iid] else ""
        return f"{self.save[iid]}/{mx}"

    def shop_key(self, k):
        if k in ("up", "w"):
            self.shop_index = (self.shop_index - 1) % len(SHOP)
        elif k in ("down", "s"):
            self.shop_index = (self.shop_index + 1) % len(SHOP)
        elif k in ("b", "escape"):
            self.state = "start"
        elif k in ("space", "return"):
            self.buy(SHOP[self.shop_index])
        visible = 9
        if self.shop_index < self.shop_scroll:
            self.shop_scroll = self.shop_index
        elif self.shop_index >= self.shop_scroll + visible:
            self.shop_scroll = self.shop_index - visible + 1

    def buy(self, item):
        iid, name, _, _, kind, mx = item
        if kind in ("skin", "land") and iid in self.owned_list(kind):
            self.save[kind] = iid
            self.message = f"{name} equipped"
            self.write_save()
            return
        if kind in ("perm", "stack", "level") and self.save[iid] >= mx:
            self.message = "Already maxed out"
            return
        price = self.item_price(item)
        if self.save["coins"] < price:
            self.message = f"Not enough coins (need {price})"
            return
        self.save["coins"] -= price
        if kind in ("skin", "land"):
            self.owned_list(kind).append(iid)
            self.save[kind] = iid
        else:
            self.save[iid] += 1
        self.message = f"Bought {name}!"
        self.burst(WIDTH / 2, 60, 30, CONFETTI, speed=5, life=40)
        self.write_save()

    # ------------------------------------------------------------- effects ---
    def beep(self):
        if SOUND:
            try:
                self.root.bell()
            except Exception:
                pass

    def popup(self, text, x, y, color=None, size=13):
        self.popups.append(dict(text=text, x=x, y=y, life=45, color=color, size=size))

    def show_banner(self, text, frames=90, color="#ff5c5c"):
        self.banner = (text, frames, color)

    def dust(self, x, y, n):
        for _ in range(n):
            self.add_particle(x, y, random.uniform(-2.5, 0.5),
                              random.uniform(-2.5, -0.5), 20, None, 3)

    def burst(self, x, y, n, colors, speed=5.0, life=40):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(1, speed)
            self.add_particle(x, y, v * math.cos(a), v * math.sin(a) - 2, life,
                              random.choice(colors), random.choice([3, 4, 5]))

    def add_particle(self, x, y, vx, vy, life, color, size):
        if len(self.particles) < 150:          # keeps the game smooth
            self.particles.append(dict(x=x, y=y, vx=vx, vy=vy, life=life,
                                       color=color, size=size))

    # ------------------------------------------------------------- geometry ---
    def dino_box(self):
        """Hitbox (x1, y1, x2, y2), slightly smaller than the drawing."""
        if self.ducking:
            box = (4, -26, 54, 0)
        else:
            box = (6, -44, 36, 0)
        s = 0.55 if self.boost_is("TINY DINO") else 1.0
        return (self.dino_x + box[0] * s, self.dino_y + box[1] * s,
                self.dino_x + box[2] * s, self.dino_y + box[3] * s)

    @staticmethod
    def overlap(a, b):
        return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]

    @staticmethod
    def obstacle_box(ob):
        return (ob["x"] + 3, ob["y"] - ob["h"] + 3, ob["x"] + ob["w"] - 3, ob["y"])

    # ---------------------------------------------------------- spawning ---
    def add_obstacle(self, kind, x, y, w, h, **extra):
        ob = dict(kind=kind, x=x, y=y, w=w, h=h, passed=False, gap=999)
        ob.update(extra)
        self.obstacles.append(ob)

    def add_cactus(self, x):
        n = random.choice([1, 1, 2, 2, 3, 4] if self.level >= 3 else [1, 1, 2, 3])
        tall = random.random() < 0.5
        w, h = (18, 46) if tall else (14, 32)
        if self.level >= 5 and random.random() < 0.2:
            w, h = 22, 58                       # giant cactus
        self.add_obstacle("cactus", x, GROUND_Y, n * (w + 4) - 4, h, n=n, cw=w)

    def add_bird(self, x, height=None):
        # low: jump over / mid: duck under / high: don't jump into it
        height = height or random.choice(["low", "mid", "mid", "high"])
        y = GROUND_Y - {"low": 20, "mid": 38, "high": 72}[height]
        self.add_obstacle("bird", x, y, 42, 26, base_y=y)

    def add_meteor(self, tx):
        fall = math.sqrt(2 * (GROUND_Y + 40) / 0.5)       # frames to fall
        self.add_obstacle("meteor", tx + self.speed * fall, -40, 24, 22,
                          vy=0.0, target_x=tx)

    def spawn_obstacle(self):
        lvl = self.level
        options = ["cactus"] * 4
        if lvl >= 2:
            options += ["bird"] * 3
        if lvl >= 3:
            options += ["cactus_bird", "swoop", "swoop"]
        if lvl >= 4:
            options += ["meteor", "meteor"]
        if lvl >= 5:
            options += ["double_cactus", "bird_wall"]
        pick = random.choice(options)
        x = WIDTH + 10

        if pick == "cactus":
            self.add_cactus(x)
        elif pick == "bird":
            self.add_bird(x)
        elif pick == "cactus_bird":
            self.add_cactus(x)
            self.add_bird(x + self.speed * 42, random.choice(["low", "mid"]))
        elif pick == "swoop":
            self.add_obstacle("swoop", x, GROUND_Y - 40, 42, 26,
                              phase=random.uniform(0, 6), base_y=GROUND_Y - 40)
        elif pick == "meteor":
            self.add_meteor(random.uniform(WIDTH * 0.45, WIDTH * 0.8))
        elif pick == "double_cactus":
            self.add_cactus(x)
            self.add_cactus(x + self.speed * 40)           # land and jump again
        elif pick == "bird_wall":
            self.add_bird(x, "mid")
            self.add_bird(x + 50, "high")                  # duck, don't jump

        lo = max(40, 74 - 4 * lvl)
        hi = max(lo + 20, 128 - 8 * lvl)
        self.next_spawn = random.randint(lo, hi)
        if pick in ("cactus_bird", "double_cactus"):
            self.next_spawn += 40

    def add_coin(self, x, y, value=1, vy=0.0, big=False):
        self.coins.append(dict(x=x, y=y, phase=random.uniform(0, 6), value=value,
                               vy=vy, big=big))

    def spawn_coins(self):
        n = random.choice([3, 4, 5, 6])
        base = GROUND_Y - random.choice([30, 70, 100])
        for i in range(n):
            arc = -22 * math.sin(math.pi * i / (n - 1))
            self.add_coin(WIDTH + i * 26, base + arc)
        self.next_coin = random.randint(120, 260)
        if self.boost_is("COIN FRENZY"):
            self.next_coin = 25

    # ------------------------------------------------- random encounters ---
    def start_event(self):
        options = ["COIN RAIN", "TREASURE", "BONUS ZONE", "ECLIPSE"]
        if self.level >= 2:
            options += ["BIRD FLOCK"]
        if self.level >= 3:
            options += ["METEOR SHOWER"]
        name = random.choice(options)
        frames = {"COIN RAIN": 300, "BONUS ZONE": 420, "ECLIPSE": 500,
                  "METEOR SHOWER": 260, "BIRD FLOCK": 1, "TREASURE": 1}[name]
        self.event = (name, frames)
        subtitle = {"COIN RAIN": "grab them!", "TREASURE": "big coin ahead (+15)",
                    "BONUS ZONE": "score x2", "ECLIPSE": "lights out...",
                    "METEOR SHOWER": "watch the red shadows!",
                    "BIRD FLOCK": "here they come"}[name]
        self.show_banner(f"{name}: {subtitle}", 110, "#b366ff")
        self.beep()
        if name == "TREASURE":
            self.add_coin(WIDTH + 40, GROUND_Y - 105, value=15, big=True)
        elif name == "BIRD FLOCK":
            for i in range(random.randint(3, 5)):
                self.add_bird(WIDTH + 20 + i * self.speed * 45,
                              random.choice(["low", "mid"]))
            self.next_spawn = 45 * 5 + 40
        elif name == "METEOR SHOWER":
            self.next_spawn = 280                   # no other obstacles meanwhile
        self.next_event = random.randint(1100, 1900)

    def update_event(self, ws):
        if self.event is None:
            self.next_event -= ws
            if self.next_event <= 0 and self.state == "running":
                self.start_event()
            return
        name, left = self.event
        if name == "COIN RAIN" and self.frame % 9 == 0:
            self.add_coin(random.uniform(250, WIDTH), -10,
                          vy=random.uniform(2.5, 4.0))
        elif name == "METEOR SHOWER" and self.frame % 55 == 0 and left > 40:
            self.add_meteor(random.uniform(WIDTH * 0.4, WIDTH * 0.85))
        left -= ws
        self.event = (name, left) if left > 0 else None

    # ------------------------------------------------------------------ UFO ---
    def update_ufo(self, v, ws):
        if self.ufo is None:
            self.next_ufo -= ws
            if self.next_ufo <= 0:
                self.ufo = dict(x=WIDTH + 60, y=55, phase="enter", t=0)
                self.show_banner("A UFO APPEARS!", 70, "#5cd65c")
            return
        u = self.ufo
        u["t"] += 1
        if u["phase"] == "enter":
            u["x"] -= 6
            if u["x"] <= 480:
                u["phase"], u["t"] = "hover", 0
        elif u["phase"] == "hover":
            u["x"] = 480 + 25 * math.sin(u["t"] * 0.08)
            if u["t"] == 50:                    # drop the boost capsule
                self.orb = dict(x=u["x"], y=u["y"] + 18, vy=1.5, t=0)
            if u["t"] > 90:
                u["phase"] = "leave"
        else:
            u["x"] += 8
            u["y"] -= 2.5
            if u["x"] > WIDTH + 80:
                self.ufo = None
                self.next_ufo = self.ufo_interval()

    def update_orb(self, v, box):
        o = self.orb
        if o is None:
            return
        o["t"] += 1
        o["x"] -= v * 0.8
        if o["y"] < GROUND_Y - 55:
            o["y"] += o["vy"]
            o["vy"] += 0.15
        else:
            o["y"] = GROUND_Y - 55 + 6 * math.sin(o["t"] * 0.15)   # float at jump height
        if self.overlap(box, (o["x"] - 13, o["y"] - 13, o["x"] + 13, o["y"] + 13)):
            name, color = random.choice(BOOSTS)
            self.boost = (name, BOOST_TIME, color)
            self.show_banner(f"BOOST: {name}!", 90, color)
            self.burst(o["x"], o["y"], 40, [color, "#ffffff"], speed=6, life=40)
            self.beep()
            self.orb = None
        elif o["x"] < -30:
            self.orb = None

    # --------------------------------------------------------------- update ---
    def update(self):
        self.frame += 1
        self.speed = min(self.speed + SPEED_GAIN, MAX_SPEED)
        ws = 0.5 if self.slowmo else 1.0             # world speed factor
        v = self.speed * ws
        mult = 2 if (self.boost_is("DOUBLE SCORE")
                     or (self.event and self.event[0] == "BONUS ZONE")) else 1
        self.distance += v * 0.02 * mult
        self.slowmo = max(0, self.slowmo - 1)
        self.invuln = max(0, self.invuln - 1)
        if self.boost:
            name, left, color = self.boost
            self.boost = (name, left - 1, color) if left > 1 else None

        new_level = 1 + int(self.distance // LEVEL_LENGTH)
        if new_level > self.level:
            self.level = new_level
            self.show_banner(f"LEVEL {self.level}")
            self.burst(WIDTH / 2, 80, 25, CONFETTI, speed=5, life=40)
            self.beep()

        # dino physics
        was_in_air = not self.on_ground()
        g = GRAVITY * (2.5 if self.ducking and was_in_air else 1.0)
        if self.boost_is("MOON JUMP") and not self.ducking:
            g *= 0.75
        self.vel_y += g
        self.dino_y += self.vel_y
        if self.dino_y >= GROUND_Y:
            self.dino_y, self.vel_y = GROUND_Y, 0.0
            if was_in_air:
                self.dust(self.dino_x + 15, GROUND_Y, 5)
        elif self.frame % 8 == 0 and self.on_ground():
            self.dust(self.dino_x + 4, GROUND_Y, 1)

        self.update_event(ws)
        self.update_ufo(v, ws)

        # obstacles
        self.next_spawn -= ws
        if self.next_spawn <= 0:
            self.spawn_obstacle()
        box = self.dino_box()
        for ob in self.obstacles:
            self.move_obstacle(ob, v, ws)
            ob_box = self.obstacle_box(ob)
            if self.overlap(box, ob_box) and not self.invuln:
                if self.boost_is("STAR POWER"):           # smash through it
                    ob["x"] = -999
                    self.bonus += 10
                    self.popup("SMASH +10", self.dino_x + 50, self.dino_y - 60,
                               "#ffb84d")
                    self.burst(ob_box[0], ob_box[1], 15, CONFETTI, speed=5, life=25)
                    continue
                if self.save["shield"] > 0:
                    self.save["shield"] -= 1
                    self.write_save()
                    self.invuln = 90
                    ob["x"] = -999
                    self.combo = 0
                    self.show_banner("SHIELD SAVED YOU!", 60, "#4db8ff")
                    self.burst(self.dino_x + 25, self.dino_y - 25, 30,
                               ["#4db8ff", "#ffffff"], speed=6, life=35)
                    continue
                self.die()
                return
            if ob_box[0] < box[2] and ob_box[2] > box[0]:
                gap = min(abs(box[3] - ob_box[1]), abs(ob_box[3] - box[1]))
                ob["gap"] = min(ob["gap"], gap)
            if not ob["passed"] and ob_box[2] < box[0]:
                ob["passed"] = True
                self.cleared(ob)
        self.obstacles = [ob for ob in self.obstacles if ob["x"] + ob["w"] > -10]

        # coins
        self.next_coin -= ws
        if self.next_coin <= 0:
            self.spawn_coins()
        magnet = [0, 50, 95, 150][self.save["magnet"]]
        if self.boost_is("SUPER MAGNET"):
            magnet = 320
        cx0, cy0 = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        kept = []
        for c in self.coins:
            c["x"] -= v
            c["phase"] += 0.15
            if c["vy"]:                               # falling coin (coin rain)
                c["y"] += c["vy"]
                if c["y"] >= GROUND_Y - 15:
                    c["y"], c["vy"] = GROUND_Y - 15, 0.0
            dx, dy = cx0 - c["x"], cy0 - c["y"]
            dist = math.hypot(dx, dy) or 1.0
            if magnet and dist < magnet:
                pull = 11 if magnet > 200 else 9
                c["x"] += dx / dist * pull
                c["y"] += dy / dist * pull
            r = 14 if c["big"] else 9
            if self.overlap(box, (c["x"] - r, c["y"] - r, c["x"] + r, c["y"] + r)):
                value = c["value"] * (2 if self.save["coinx2"] else 1)
                self.run_coins += value
                self.save["coins"] += value
                if c["big"]:
                    self.popup(f"TREASURE +{value}", c["x"], c["y"] - 20, self.coin_col())
                    self.burst(c["x"], c["y"], 30, [self.coin_col(), "#fff2a8"],
                               speed=5, life=35)
                else:
                    self.burst(c["x"], c["y"], 5, [self.coin_col(), "#fff2a8"],
                               speed=2.5, life=15)
            elif c["x"] > -20:
                kept.append(c)
        self.coins = kept

        self.update_orb(v, box)

        if (not self.record_beaten and self.save["high"] > 0
                and self.score > self.save["high"]):
            self.record_beaten = True
            self.show_banner("NEW RECORD!")
            self.burst(WIDTH / 2, 80, 60, CONFETTI, speed=7, life=70)
            self.beep()

        self.update_world(v)

    def move_obstacle(self, ob, v, ws):
        kind = ob["kind"]
        if kind == "bird":
            ob["x"] -= v * 1.1
        elif kind == "swoop":
            ob["x"] -= v * 1.05
            ob["phase"] += 0.06 * ws
            ob["y"] = ob["base_y"] + 30 * math.sin(ob["phase"])
        elif kind == "meteor":
            ob["x"] -= v
            ob["target_x"] -= v
            ob["vy"] += 0.5 * ws
            ob["y"] += ob["vy"] * ws
            if ob["y"] >= GROUND_Y:                    # impact -> becomes a rock
                ob.update(kind="rock", y=GROUND_Y, w=26, h=20)
                self.shake = max(self.shake, 8)
                self.burst(ob["x"] + 12, GROUND_Y, 20, ["#ff7b29", "#ffcf3f", "#8a8a8a"],
                           speed=5, life=30)
        else:                                           # cactus, rock
            ob["x"] -= v

    def cleared(self, ob):
        """Small reward for getting past an obstacle; bigger for close calls."""
        if ob["kind"] == "meteor":
            return
        self.combo += 1
        self.bonus += 2 * min(self.combo, 10)
        if ob["gap"] < 10:
            self.bonus += 25
            self.popup("CLOSE CALL! +25", self.dino_x + 50, self.dino_y - 60, "#ff9f1a")
            self.burst(self.dino_x + 20, self.dino_y - 30, 10, ["#ff9f1a", "#ffe14d"],
                       speed=4, life=25)
        if self.combo in (15, 30, 50, 75, 100):
            self.bonus += self.combo * 5
            self.show_banner(f"COMBO x{self.combo}!  +{self.combo * 5}", color="#4db8ff")
            self.burst(WIDTH / 2, 95, 35, CONFETTI, speed=5, life=45)

    def die(self):
        self.state = "over"
        self.shake = 20
        self.ducking = False
        self.boost = None
        self.burst(self.dino_x + 25, self.dino_y - 25, 40,
                   [self.col("fg"), "#ff5c5c", "#ffb84d"], speed=6, life=45)
        if self.score > self.save["high"]:
            self.save["high"] = self.score
        self.write_save()

    def update_world(self, v=0.0):
        """Things that keep moving, also on the menu screens."""
        eclipse = self.event is not None and self.event[0] == "ECLIPSE"
        target = 1.0 if (eclipse or (int(self.distance) // DAY_LENGTH) % 2) else 0.0
        self.night_t += (target - self.night_t) * 0.025
        for c in self.clouds:
            c[0] -= v * 0.2
            if c[0] < -60:
                c[0], c[1] = WIDTH + random.randint(0, 200), random.randint(30, 120)
        for hl in self.hills:
            hl["x"] -= v * 0.25
        self.hills = [hl for hl in self.hills if hl["x"] + hl["w"] > -20]
        last = max(hl["x"] + hl["w"] * 0.7 for hl in self.hills) if self.hills else 0
        while last < WIDTH + 100:
            last = self.add_hill(last)
        for f in self.snow:
            f[0] -= v * 0.35 + 0.4
            f[1] += f[2]
            if f[1] > GROUND_Y or f[0] < 0:
                f[0], f[1] = random.uniform(0, WIDTH + 100), -5
        self.ground_offset = (self.ground_offset + v) % 40
        for p in self.particles:
            p["x"] += p["vx"] - v * 0.3
            p["y"] += p["vy"]
            p["vy"] += 0.2
            p["life"] -= 1
        self.particles = [p for p in self.particles if p["life"] > 0]
        for t in self.popups:
            t["y"] -= 0.8
            t["life"] -= 1
        self.popups = [t for t in self.popups if t["life"] > 0]
        if self.banner:
            text, left, color = self.banner
            self.banner = (text, left - 1, color) if left > 1 else None
        self.shake = max(0, self.shake - 1)

    def step(self):
        if self.state == "running":
            self.update()
        else:
            self.update_world()

    # ----------------------------------------------------------------- draw ---
    def col(self, name):
        land = LANDS.get(self.save["land"], LANDS["land_desert"])
        return mix(land["day"][name], land["night"][name], self.night_t)

    def coin_col(self):
        return mix(COIN_DAY, COIN_NIGHT, self.night_t)

    def draw_background(self, bg, fg):
        cv = self.canvas
        decor = LANDS.get(self.save["land"], LANDS["land_desert"])["decor"]
        # sky
        if self.night_t > 0.05:
            star = mix(bg, "#ffffff", self.night_t)
            for sx, sy, s in self.stars:
                if (self.frame // 20 + sx) % 7:
                    cv.create_rectangle(sx, sy, sx + s, sy + s, fill=star, width=0)
            moon = mix(bg, "#f2f2d0", self.night_t)
            cv.create_oval(WIDTH - 140, 40, WIDTH - 110, 70, fill=moon, width=0)
            cv.create_oval(WIDTH - 132, 36, WIDTH - 104, 64, fill=bg, width=0)
            if decor == "craters":                 # Mars has two moons
                cv.create_oval(WIDTH - 220, 70, WIDTH - 208, 82,
                               fill=mix(bg, "#e0b090", self.night_t), width=0)
        else:
            sun = "#ff9f6b" if decor == "craters" else "#ffe9a3"
            cv.create_oval(WIDTH - 140, 36, WIDTH - 104, 72, fill=sun, width=0)
        for cx, cy in self.clouds:
            cv.create_oval(cx, cy, cx + 50, cy + 16, fill=self.col("cloud"), width=0)

        # hills (parallax layer) with landscape decoration
        hill = self.col("hill")
        dark = mix(hill, fg, 0.35)
        for hl in self.hills:
            x, w, h = hl["x"], hl["w"], hl["h"]
            cv.create_oval(x, GROUND_Y - h, x + w, GROUND_Y + h, fill=hill, width=0)
            if decor == "trees":
                for t in hl["trees"]:
                    tx = x + w * t
                    top = GROUND_Y - h * math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2))
                    cv.create_polygon(tx - 9, top + 6, tx + 9, top + 6, tx, top - 22,
                                      fill=dark)
            elif decor == "craters":
                cx = x + w * hl["crater"]
                cv.create_oval(cx - 14, GROUND_Y - h * 0.5, cx + 14, GROUND_Y - h * 0.5 + 8,
                               fill=dark, width=0)
            elif decor == "snow":
                cv.create_oval(x + w * 0.35, GROUND_Y - h, x + w * 0.65,
                               GROUND_Y - h * 0.75, fill="#ffffff", width=0)
        cv.create_rectangle(0, GROUND_Y, WIDTH, HEIGHT, fill=bg, width=0)
        if decor == "snow":
            flake = mix("#9fb3c8", "#ffffff", self.night_t)
            for fx, fy, s in self.snow:
                cv.create_oval(fx, fy, fx + 2 + s, fy + 2 + s, fill=flake, width=0)

    def draw_dino(self, ox, oy, fg, bg):
        cv = self.canvas
        x, y = self.dino_x + ox, self.dino_y + oy
        body = SKIN_COLOR.get(self.save["skin"]) or fg
        if self.boost_is("STAR POWER"):
            body = CONFETTI[(self.frame // 4) % len(CONFETTI)]
        if self.invuln and (self.invuln // 4) % 2:
            return                                    # blink after a shield hit
        s = 0.55 if self.boost_is("TINY DINO") else 1.0

        def R(x1, y1, x2, y2, c):
            cv.create_rectangle(x + x1 * s, y + y1 * s, x + x2 * s, y + y2 * s,
                                fill=c, width=0)

        running = self.state == "running"
        legs_up = (self.frame // 5) % 2 == 0 and self.on_ground() and running
        dead = self.state == "over"
        if self.ducking:
            R(0, -26, 46, -8, body)
            R(40, -30, 60, -14, body)
            R(50, -26, 53, -23, bg)
        else:
            R(4, -34, 30, -12, body)
            R(20, -50, 44, -32, body)
            if dead:
                cv.create_line(x + 25 * s, y - 47 * s, x + 31 * s, y - 41 * s,
                               fill=bg, width=2)
                cv.create_line(x + 31 * s, y - 47 * s, x + 25 * s, y - 41 * s,
                               fill=bg, width=2)
            else:
                R(26, -46, 30, -42, bg)
            R(30, -28, 36, -24, body)
            R(-6, -30, 6, -22, body)
        l1 = 0 if legs_up else 6
        l2 = 6 if legs_up else 0
        R(8, -12, 13, -l1, body)
        R(20, -12, 25, -l2, body)
        if self.save["shield"] > 0 and running:
            cv.create_oval(x - 10 * s, y - 62 * s, x + 62 * s, y + 6 * s,
                           outline="#4db8ff", width=2)

    def draw_obstacle(self, ob, ox, oy, fg):
        cv = self.canvas
        x, y, w, h = ob["x"] + ox, ob["y"] + oy, ob["w"], ob["h"]
        kind = ob["kind"]
        if kind == "cactus":
            cw = ob["cw"]
            for i in range(ob["n"]):
                cx = x + i * (cw + 4)
                cv.create_rectangle(cx + cw * 0.3, y - h, cx + cw * 0.7, y,
                                    fill=fg, width=0)
                cv.create_rectangle(cx, y - h * 0.65, cx + cw * 0.3, y - h * 0.45,
                                    fill=fg, width=0)
                cv.create_rectangle(cx, y - h * 0.85, cx + cw * 0.15, y - h * 0.5,
                                    fill=fg, width=0)
                cv.create_rectangle(cx + cw * 0.7, y - h * 0.55, cx + cw, y - h * 0.35,
                                    fill=fg, width=0)
                cv.create_rectangle(cx + cw * 0.85, y - h * 0.75, cx + cw, y - h * 0.4,
                                    fill=fg, width=0)
        elif kind in ("bird", "swoop"):
            color = fg if kind == "bird" else "#c0392b"
            cv.create_rectangle(x + 8, y - 16, x + 36, y - 8, fill=color, width=0)
            cv.create_polygon(x, y - 14, x + 10, y - 18, x + 10, y - 10, fill=color)
            if (self.frame // 8) % 2:
                cv.create_polygon(x + 16, y - 16, x + 28, y - 16, x + 22, y - h,
                                  fill=color)
            else:
                cv.create_polygon(x + 16, y - 8, x + 28, y - 8, x + 22, y, fill=color)
        elif kind == "meteor":
            sx = ob["target_x"] + ox
            cv.create_oval(sx - 4, GROUND_Y - 3, sx + 30, GROUND_Y + 3,
                           fill="#ff5c5c", width=0)
            for i in range(4):
                cv.create_oval(x + 6 + i * 5, y - h - 10 - i * 9, x + 18 + i * 5,
                               y - h + 2 - i * 9,
                               fill=["#ffcf3f", "#ff9f1a", "#ff7b29", "#ff5c5c"][i],
                               width=0)
            cv.create_oval(x, y - h, x + w, y, fill="#7a5c48", width=0)
        else:                                          # rock
            cv.create_polygon(x, y, x + 4, y - h + 6, x + 12, y - h, x + w - 4,
                              y - h + 4, x + w, y, fill="#7a7a7a", outline=fg)

    def draw_ufo(self, fg):
        cv = self.canvas
        if self.ufo:
            x, y = self.ufo["x"], self.ufo["y"]
            if self.ufo["phase"] == "hover":       # tractor beam
                cv.create_polygon(x - 10, y + 8, x + 10, y + 8, x + 40, GROUND_Y,
                                  x - 40, GROUND_Y, fill=mix(self.col("bg"), "#5cd65c", 0.25),
                                  width=0)
            cv.create_oval(x - 14, y - 16, x + 14, y + 4, fill="#9fe8ff", outline=fg)
            cv.create_oval(x - 34, y - 6, x + 34, y + 10, fill="#8a8f99", outline=fg)
            for i in range(-2, 3):
                on = (self.frame // 6 + i) % 2
                cv.create_oval(x + i * 12 - 3, y, x + i * 12 + 3, y + 5,
                               fill="#ffe14d" if on else "#ff5c5c", width=0)
        if self.orb:
            o = self.orb
            glow = CONFETTI[(self.frame // 5) % len(CONFETTI)]
            cv.create_oval(o["x"] - 16, o["y"] - 16, o["x"] + 16, o["y"] + 16,
                           outline=glow, width=3)
            cv.create_oval(o["x"] - 11, o["y"] - 11, o["x"] + 11, o["y"] + 11,
                           fill="#ffffff", outline=fg)
            cv.create_text(o["x"], o["y"], text="?", fill="#b366ff",
                           font=("Courier", 14, "bold"))

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        bg, fg = self.col("bg"), self.col("fg")
        cv.configure(bg=bg)
        ox = random.randint(-5, 5) if self.shake else 0
        oy = random.randint(-4, 4) if self.shake else 0

        if self.state == "shop":
            self.draw_shop(bg, fg)
            return

        self.draw_background(bg, fg)
        if self.slowmo:
            cv.create_rectangle(0, 0, WIDTH, HEIGHT, outline="#4db8ff", width=6)
        if self.boost:
            cv.create_rectangle(0, 0, WIDTH, HEIGHT, outline=self.boost[2], width=4)

        cv.create_line(0, GROUND_Y + oy, WIDTH, GROUND_Y + oy, fill=fg, width=2)
        for gx in range(-int(self.ground_offset), WIDTH, 40):
            cv.create_line(gx + ox, GROUND_Y + 8 + oy, gx + 6 + ox, GROUND_Y + 8 + oy,
                           fill=fg)

        coin_col = self.coin_col()
        for c in self.coins:
            R = 14 if c["big"] else 8
            r = R * abs(math.cos(c["phase"])) + 2
            cv.create_oval(c["x"] - r + ox, c["y"] - R + oy, c["x"] + r + ox,
                           c["y"] + R + oy, fill=coin_col, outline=fg,
                           width=2 if c["big"] else 1)
        for ob in self.obstacles:
            self.draw_obstacle(ob, ox, oy, fg)
        self.draw_ufo(fg)
        self.draw_dino(ox, oy, fg, bg)

        for p in self.particles:
            s = p["size"]
            cv.create_rectangle(p["x"], p["y"], p["x"] + s, p["y"] + s,
                                fill=p["color"] or fg, width=0)
        for t in self.popups:
            cv.create_text(t["x"], t["y"], text=t["text"], fill=t["color"] or fg,
                           font=("Courier", t["size"], "bold"))
        self.draw_hud(fg)

    def draw_hud(self, fg):
        cv = self.canvas
        cv.create_text(WIDTH - 20, 18, anchor="ne", fill=fg,
                       font=("Courier", 16, "bold"),
                       text=f"HI {self.save['high']:05d}  {self.score:05d}")
        cv.create_text(WIDTH - 20, 42, anchor="ne", fill=self.coin_col(),
                       font=("Courier", 13, "bold"),
                       text=f"coins {self.save['coins']}")
        if self.state == "running":
            info = f"LVL {self.level}"
            if self.combo >= 5:
                info += f"   combo {self.combo}"
            if self.save["shield"]:
                info += f"   shield x{self.save['shield']}"
            if self.save["slowmo"]:
                info += f"   slow-mo x{self.save['slowmo']} [X]"
            cv.create_text(20, 18, anchor="nw", fill=fg, font=("Courier", 12, "bold"),
                           text=info)
            if self.boost:                              # boost timer bar
                name, left, color = self.boost
                cv.create_text(20, 40, anchor="nw", fill=color,
                               font=("Courier", 12, "bold"), text=name)
                cv.create_rectangle(170, 43, 170 + 120, 53, outline=fg, width=1)
                cv.create_rectangle(170, 43, 170 + 120 * left / BOOST_TIME, 53,
                                    fill=color, width=0)
            if self.event and self.event[1] > 1:
                cv.create_text(20, 62, anchor="nw", fill="#b366ff",
                               font=("Courier", 11, "bold"), text=self.event[0])
        if self.banner:
            text, left, color = self.banner
            cv.create_text(WIDTH / 2, 90, text=text, fill=color,
                           font=("Courier", 20, "bold"))

        mid = HEIGHT / 2
        land = LANDS[self.save["land"]]["name"]
        if self.state == "start":
            cv.create_text(WIDTH / 2, mid - 50, fill=fg, font=("Courier", 18, "bold"),
                           text="Press SPACE to start")
            cv.create_text(WIDTH / 2, mid - 22, fill=fg, font=("Courier", 12),
                           text="Jump: Space/Up   Duck/dive: Down/S   Slow-mo: X")
            cv.create_text(WIDTH / 2, mid, fill=self.coin_col(),
                           font=("Courier", 12, "bold"),
                           text=f"Press B for the SHOP      world: {land}")
        elif self.state == "over":
            cv.create_text(WIDTH / 2, mid - 55, fill=fg, font=("Courier", 24, "bold"),
                           text="G A M E   O V E R")
            cv.create_text(WIDTH / 2, mid - 25, fill=fg, font=("Courier", 13),
                           text=f"Score {self.score}   level {self.level}   "
                                f"+{self.run_coins} coins")
            if self.record_beaten or (self.save["high"] == self.score and self.score):
                cv.create_text(WIDTH / 2, mid - 3, fill="#ff5c5c",
                               font=("Courier", 14, "bold"), text="NEW HIGH SCORE!")
            if not self.shake:
                cv.create_text(WIDTH / 2, mid + 20, fill=fg, font=("Courier", 12),
                               text="SPACE: play again     B: shop")

    def draw_shop(self, bg, fg):
        cv = self.canvas
        cv.create_text(WIDTH / 2, 22, text="S H O P", fill=fg,
                       font=("Courier", 20, "bold"))
        cv.create_text(WIDTH / 2, 46, text=f"coins: {self.save['coins']}",
                       fill=self.coin_col(), font=("Courier", 14, "bold"))
        top, row, visible = 70, 20, 9
        for vi in range(visible):
            i = self.shop_scroll + vi
            if i >= len(SHOP):
                break
            item = SHOP[i]
            iid, name, desc, _, kind, mx = item
            y = top + vi * row
            if i == self.shop_index:
                cv.create_rectangle(40, y - 9, WIDTH - 40, y + 10,
                                    fill=mix(bg, "#4db8ff", 0.25), width=0)
            price = self.item_price(item)
            owned = kind in ("skin", "land") and iid in self.owned_list(kind)
            maxed = kind not in ("skin", "land") and self.save[iid] >= mx
            ptxt = "-" if (owned or maxed or price is None) else f"{price} c"
            cv.create_text(55, y, anchor="w", fill=fg, font=("Courier", 12, "bold"),
                           text=name)
            cv.create_text(250, y, anchor="w", fill=fg, font=("Courier", 11), text=desc)
            cv.create_text(WIDTH - 160, y, anchor="e", fill=self.coin_col(),
                           font=("Courier", 12, "bold"), text=ptxt)
            cv.create_text(WIDTH - 55, y, anchor="e", fill=fg,
                           font=("Courier", 11), text=self.item_status(item))
        if self.shop_scroll > 0:
            cv.create_text(WIDTH - 25, top - 8, text="^", fill=fg,
                           font=("Courier", 12, "bold"))
        if self.shop_scroll + visible < len(SHOP):
            cv.create_text(WIDTH - 25, top + visible * row - 10, text="v", fill=fg,
                           font=("Courier", 12, "bold"))
        cv.create_text(WIDTH / 2, HEIGHT - 28, fill="#ff5c5c",
                       font=("Courier", 12, "bold"), text=self.message)
        cv.create_text(WIDTH / 2, HEIGHT - 9, fill=fg, font=("Courier", 10),
                       text="Up/Down: choose   Space/Enter: buy or equip   B/Esc: back")
        for p in self.particles:
            s = p["size"]
            cv.create_rectangle(p["x"], p["y"], p["x"] + s, p["y"] + s,
                                fill=p["color"] or fg, width=0)

    # ----------------------------------------------------------------- loop ---
    def loop(self):
        now = time.perf_counter()
        self.acc += now - self.last_time
        self.last_time = now
        steps = 0
        while self.acc >= DT and steps < 5:
            self.step()
            self.acc -= DT
            steps += 1
        if steps == 5:
            self.acc = 0.0                 # computer too slow: don't spiral
        self.draw()
        self.root.after(8, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    DinoGame(root)
    root.mainloop()
