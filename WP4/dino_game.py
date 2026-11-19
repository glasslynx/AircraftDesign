"""
Dino runner game - no installs needed (uses tkinter, which comes with Python).

Controls
    Space / Up / W     jump (also starts the game; double jump if you own it)
    Down / S           duck; in the air it makes you dive down fast
    X                  use a slow-mo (if you have one)
    B                  open the shop (start / game-over screen)
    In the shop:       Up/Down to choose, Space/Enter to buy or equip, B/Esc back
    Q / Esc            quit

Every 2000 points a boss shows up: dodge its attacks and grab the yellow stars
it drops to shoot it down.

Coins, upgrades and the high score are saved in dino_save.json next to this file.

Run with:  python dino_game.py
"""
import array
import json
import math
import random
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import wave
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
BOSS_EVERY = 2000              # a boss fight every 2000 points
SOUND = True                   # system "bell" on new level / record
VERSION = "v22"
SAVE_FILE = Path(__file__).resolve().parent / "dino_save.json"
MUSIC_FILE = Path(__file__).resolve().parent / "dino_motivation_music_v3.wav"
VOICE_DIR = Path(__file__).resolve().parent / "dino_voice_cache"
GAME_MUSIC = Path(__file__).resolve().parent / "dino_music_game_v2.wav"
MENU_MUSIC = Path(__file__).resolve().parent / "dino_music_menu_v1.wav"

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
    ("shield", "Shield", "survive one hit (used automatically, max 3)", 60, "stack", 3),
    ("slowmo", "Slow-mo", "press X: world at half speed for 4 s (max 3)", 40, "stack", 3),
    ("doublejump", "Double jump", "a small extra jump in mid-air, recharges in 3 s",
     500, "perm", 1),
    ("magnet", "Coin magnet", "pulls nearby coins to you (3 levels)", [100, 220, 400],
     "level", 3),
    ("coinx2", "Double coins", "every coin you pick up is worth 2", 600, "perm", 1),
    ("ufo_luck", "UFO radar", "the UFO visits twice as often", 300, "perm", 1),
    ("trophy", "Golden Trophy", "the ultimate flex: shines on your main menu forever",
     9999, "perm", 1),
    ("land_desert", "World: Desert", "the classic dunes", 0, "land", 1),
    ("land_forest", "World: Forest", "green hills and pine trees", 80, "land", 1),
    ("land_snow", "World: Snow", "white hills and falling snow", 120, "land", 1),
    ("land_mars", "World: Mars", "red planet, craters, two moons", 200, "land", 1),
    ("acc_none", "No accessory", "just the dino", 0, "acc", 1),
    ("acc_flag_hu", "Hungarian flag", "carry the red-white-green with pride", 75,
     "acc", 1),
    ("acc_flag_nl", "Dutch flag", "red, white and blue - hup Holland!", 75, "acc", 1),
    ("acc_flag_tr", "Turkish flag", "red with the white crescent and star", 75,
     "acc", 1),
    ("acc_partyhat", "Party hat", "every run is a party", 40, "acc", 1),
    ("acc_shades", "Sunglasses", "too cool for cacti", 60, "acc", 1),
    ("acc_crown", "Crown", "king of the desert", 250, "acc", 1),
    ("hair_none", "Hair: Bald", "the classic smooth dino", 0, "hair", 1),
    ("hair_quiff", "Hair: Blond quiff", "blond-brown and swept up", 60, "hair", 1),
    ("hair_long", "Hair: Long brown", "long brown hair down the back", 60, "hair", 1),
    ("hair_ponytail", "Hair: Ginger ponytail", "bounces when you run", 70, "hair", 1),
    ("hair_curly", "Hair: Black curls", "big curly fro", 80, "hair", 1),
    ("hair_mohawk", "Hair: Pink mohawk", "punk rock dino", 120, "hair", 1),
    ("eyes_classic", "Eyes: Classic", "plain dot eyes", 0, "eyes", 1),
    ("eyes_green", "Eyes: Green", "bright green eyes", 40, "eyes", 1),
    ("eyes_brown", "Eyes: Dark brown", "deep dark eyes", 40, "eyes", 1),
    ("eyes_blue", "Eyes: Blue", "ice blue eyes", 40, "eyes", 1),
    ("outfit_none", "Outfit: None", "nothing to wear", 0, "outfit", 1),
    ("outfit_scarf", "Outfit: Scarf", "a cosy blue scarf that flaps", 50, "outfit", 1),
    ("outfit_bowtie", "Outfit: Bow tie", "classy", 60, "outfit", 1),
    ("outfit_suit", "Outfit: Shirt & tie", "ready for the job interview", 90,
     "outfit", 1),
    ("outfit_tutu", "Outfit: Tutu", "pink and fabulous", 90, "outfit", 1),
    ("outfit_cape", "Outfit: Hero cape", "a red cape that waves behind you", 180,
     "outfit", 1),
    ("couple", "Couple run", "run hand in hand with your dino girlfriend "
     "(buy, then press again to turn on/off)", 350, "toggle", 1),
    ("skin_classic", "Skin: White", "the standard dino, bright white", 0, "skin", 1),
    ("skin_grey", "Skin: Retro grey", "the old-school grey dino", 0, "skin", 1),
    ("skin_green", "Skin: Green", "a fresh green dino", 50, "skin", 1),
    ("skin_ghost", "Skin: Ghost", "spooky and blue", 150, "skin", 1),
    ("skin_gold", "Skin: Gold", "pure flex", 400, "skin", 1),
]
STYLE_KINDS = ("acc", "hair", "eyes", "outfit", "skin", "toggle")
# two shops: power-ups & worlds, and a wardrobe for the dino's looks
SHOP_POWER = [it for it in SHOP if it[4] not in STYLE_KINDS]
SHOP_STYLE = ([it for it in SHOP if it[4] == "toggle"] +
              [it for k in ("hair", "eyes", "outfit", "acc", "skin")
               for it in SHOP if it[4] == k])
SHOPS = {"power": ("P O W E R - U P S", SHOP_POWER),
         "style": ("D I N O   S T Y L E", SHOP_STYLE)}
COSMETIC = ("skin", "land", "acc", "hair", "eyes", "outfit")
SLOT_LIST = {"skin": "skins", "land": "lands", "acc": "accs", "hair": "hairs",
             "eyes": "eyes_owned", "outfit": "outfits"}
HAIR = {"hair_none": None, "hair_quiff": ("quiff", "#b08a4f"),
        "hair_long": ("long", "#6b3e22"), "hair_ponytail": ("ponytail", "#d9772b"),
        "hair_curly": ("curly", "#2b1d14"), "hair_mohawk": ("mohawk", "#ff4fa3")}
EYES = {"eyes_classic": None, "eyes_green": "#3c9a4a", "eyes_brown": "#3b2010",
        "eyes_blue": "#3a8be0"}
# the couple: he has blond-brown hair and green eyes, she has brown hair and dark eyes
HIM = dict(hair=("quiff", "#b08a4f"), eyes="#3c9a4a")
HER = dict(hair=("long", "#6b3e22"), eyes="#2a1408", lashes=True, bow=True)
SKIN_COLOR = {"skin_classic": "#f7f7f2", "skin_grey": None, "skin_green": "#3fae49",
              "skin_ghost": "#8fa8ff", "skin_gold": "#e0a800"}

# UFO boosts: name, colour
BOOSTS = [("STAR POWER", "#ffd23f"), ("SUPER MAGNET", "#ff5c5c"),
          ("DOUBLE SCORE", "#5cd65c"), ("MOON JUMP", "#b366ff"),
          ("TINY DINO", "#4db8ff"), ("COIN FRENZY", "#ffb84d")]
# flags: horizontal stripes top to bottom (Turkey is drawn separately)
FLAGS = {"acc_flag_hu": ("#ce2939", "#ffffff", "#477050"),
         "acc_flag_nl": ("#ae1c28", "#ffffff", "#21468b"),
         "acc_flag_tr": ("#e30a17", "#e30a17", "#e30a17")}

# Motivation room: quotes (text, who). "attributed" = widely credited, wording
# not found in their own writings.
QUOTES = [
    ("The impediment to action advances action. What stands in the way becomes "
     "the way.", "Marcus Aurelius, Meditations"),
    ("Waste no more time arguing about what a good man should be. Be one.",
     "Marcus Aurelius, Meditations"),
    ("Confine yourself to the present.", "Marcus Aurelius, Meditations"),
    ("Impossible is a word to be found only in the dictionary of fools.",
     "Napoleon Bonaparte (attributed)"),
    ("Victory belongs to the most persevering.", "Napoleon Bonaparte (attributed)"),
    ("Never give in, never give in, never, never, never, never.",
     "Winston Churchill, 1941"),
    ("Opportunities multiply as they are seized.", "Sun Tzu, The Art of War"),
    ("I will either find a way, or make one.", "Hannibal Barca (attributed)"),
    ("I came, I saw, I conquered.", "Julius Caesar"),
    ("There is nothing impossible to him who will try.",
     "Alexander the Great (attributed)"),
    ("Difficulties strengthen the mind, as labour does the body.", "Seneca"),
    ("No man is free who is not master of himself.", "Epictetus"),
]
AFFIRMATIONS = [
    "Every run makes you better.",
    "The cactus is temporary. Your high score is forever.",
    "You have survived every bad run so far.",
    "Losing is just practice wearing a disguise.",
    "Your thumbs are faster than you think.",
    "Breathe. Focus. Jump.",
    "Champions are made of runs that went wrong.",
    "The boss fears you more than you fear the boss.",
]

# the Dino Mine: miners dig coins for you (also while the game is closed)
MINER_COSTS = [1, 2, 3, 5, 7, 10, 14]   # diamonds to hire miner 2, 3, ... 8
PICK_COSTS = [2, 4, 7, 11, 16]          # better pickaxe, level 1..5
CART_COSTS = [1, 3, 6, 10]              # bigger cart, level 1..4
MINE_MAX_OFFLINE = 12 * 3600            # miners work at most 12 h while you're away

BOSSES = [("MECHA-PTERO", "#6b6f7a"), ("CACTUS KING", "#3f8f3f"),
          ("STORM DRAGON", "#5a4fcf"), ("LAVA BAT", "#c0392b")]


class Audio:
    """Music and voice.
    Music: composed by the game itself the first time it starts (saved as a .wav).
    Voice: a natural neural voice if the free 'edge-tts' package is installed
    (press V in the Motivation Room to install it), otherwise the computer's
    own speech engine (Windows speech, Mac 'say', Linux espeak)."""

    NEURAL_VOICE = "en-US-ChristopherNeural"     # deep, calm, warm narrator

    def __init__(self):
        self.platform = sys.platform
        self.music_on = False
        self.music_proc = None
        self.voice_proc = None
        self.status = ""
        self.voice_status = ""
        self.music_thread = None
        self.track = None
        self.music_gen = 0
        self.ready = {}
        self.speak_id = 0
        self.installing = None
        VOICE_DIR.mkdir(exist_ok=True)

    # ----------------------------------------------------------------- music ---
    def track_file(self, name):
        return {"game": GAME_MUSIC, "menu": MENU_MUSIC, "epic": MUSIC_FILE}[name]

    def prepare_music(self):
        """Compose all three tracks in the background (only the first time)."""
        if self.music_thread:
            return
        self.ready = {}

        def work():
            for name, maker in (("menu", make_menu_music), ("game", make_game_music),
                                ("epic", None)):
                path = self.track_file(name)
                if not path.exists():
                    self.status = f"composing {name} music..."
                    try:
                        if maker:
                            maker(path)
                        else:
                            try:
                                make_epic_music(path)          # with numpy
                            except ImportError:
                                make_epic_music_pure(path)
                            set_volume(path, 0.4)      # quieter, so the voice is clear
                    except Exception as err:
                        self.status = f"music error: {err}"
                        continue
                self.ready[name] = True
            self.status = "music ready"
        self.music_thread = threading.Thread(target=work, daemon=True)
        self.music_thread.start()

    def play_track(self, name):
        """Switch the background music; name None = silence."""
        if name == self.track:
            return
        self.stop_music()
        self.track = name
        if name:
            gen = self.music_gen
            threading.Thread(target=self._music_loop, args=(name, gen), daemon=True).start()

    def _music_loop(self, name, gen):
        self.prepare_music()
        while not self.ready.get(name):                 # wait until composed
            if gen != self.music_gen or not self.music_thread.is_alive() \
                    and not self.ready.get(name):
                return
            time.sleep(0.1)
        if gen != self.music_gen:
            return
        path = self.track_file(name)
        if self.platform.startswith("win"):
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME |
                               winsound.SND_ASYNC | winsound.SND_LOOP)
            return
        player = (["afplay"] if self.platform == "darwin" else
                  ["paplay"] if shutil.which("paplay") else
                  ["aplay", "-q"] if shutil.which("aplay") else None)
        if not player:
            self.status = "no audio player found (install pulseaudio or alsa-utils)"
            return
        try:
            with wave.open(str(path)) as w:
                length = w.getnframes() / w.getframerate()
        except Exception:
            length = None
        while gen == self.music_gen:                    # loop the track
            try:
                proc = subprocess.Popen(player + [str(path)], stderr=subprocess.DEVNULL)
                self.music_proc = proc
                if length:                              # start the next copy ~60 ms
                    end = time.time() + length - 0.06   # early to hide the start-up gap
                    while time.time() < end and gen == self.music_gen:
                        time.sleep(0.02)
                    if gen != self.music_gen:
                        self._kill(proc)
                else:
                    proc.wait()
            except Exception:
                return

    def stop_music(self):
        self.music_gen += 1
        self.track = None
        if self.platform.startswith("win"):
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:
                pass
        self._kill(self.music_proc)
        self.music_proc = None

    # ----------------------------------------------------------------- voice ---
    @staticmethod
    def neural_available():
        import importlib.util
        return importlib.util.find_spec("edge_tts") is not None

    def voice_available(self):
        if self.neural_available():
            return True
        if self.platform.startswith("win"):
            return shutil.which("powershell") is not None
        if self.platform == "darwin":
            return shutil.which("say") is not None
        return bool(shutil.which("espeak") or shutil.which("espeak-ng")
                    or shutil.which("spd-say"))

    def install_neural(self):
        """Installs edge-tts with pip (only when the player presses V).
        Tries a normal install first and then a --user install."""
        if self.installing or self.neural_available():
            return
        self.voice_status = "installing natural voice (needs internet)..."
        self.install_tries = [[], ["--user"]]
        self._next_install()

    def _next_install(self):
        extra = self.install_tries.pop(0)
        log = open(VOICE_DIR / "install_log.txt", "w")
        try:
            self.installing = subprocess.Popen(
                [self.python_exe(), "-m", "pip", "install", "--upgrade", *extra, "edge-tts"],
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=0x08000000 if self.platform.startswith("win") else 0)
        except Exception as err:
            self.voice_status = f"install failed: {err}"
            self.installing = None

    @staticmethod
    def python_exe():
        """pythonw.exe (no console) can't run pip well: use python.exe next to it."""
        exe = Path(sys.executable)
        if exe.name.lower() == "pythonw.exe" and (exe.parent / "python.exe").exists():
            return str(exe.parent / "python.exe")
        return sys.executable

    def poll_install(self):
        if not self.installing or self.installing.poll() is None:
            return False
        ok = self.installing.returncode == 0
        self.installing = None
        import importlib
        import site
        try:                                   # a fresh --user folder isn't on sys.path yet
            user_site = site.getusersitepackages()
            if user_site not in sys.path:
                sys.path.append(user_site)
        except Exception:
            pass
        importlib.invalidate_caches()
        if ok and self.neural_available():
            self.voice_status = "natural voice installed!"
            return True
        if self.install_tries:                 # try the next way of installing
            self._next_install()
            return False
        try:
            lines = [l.strip() for l in (VOICE_DIR / "install_log.txt").read_text(
                errors="ignore").splitlines() if l.strip()]
            reason = next((l for l in reversed(lines) if "error" in l.lower()), lines[-1])
        except Exception:
            reason = "unknown error"
        self.voice_status = f"install failed ({reason[:60]}) - see dino_voice_cache/install_log.txt"
        return False

    def speak(self, text):
        self.stop_voice()
        self.speak_id += 1
        if self.neural_available():
            my_id = self.speak_id
            threading.Thread(target=self._speak_neural, args=(text, my_id),
                             daemon=True).start()
        else:
            self._speak_local(text)

    def _speak_neural(self, text, my_id):
        import hashlib
        path = VOICE_DIR / (hashlib.md5(text.encode()).hexdigest() + ".mp3")
        if not path.exists():
            self.voice_status = "preparing voice..."
            try:
                import asyncio
                import edge_tts
                comm = edge_tts.Communicate(text, self.NEURAL_VOICE, rate="-12%",
                                            pitch="-6Hz")
                asyncio.run(comm.save(str(path)))
            except Exception as err:
                if path.exists():
                    path.unlink()
                self.voice_status = f"natural voice failed ({str(err)[:50]}) - computer voice"
                if my_id == self.speak_id:
                    self._speak_local(text)
                return
        self.voice_status = "natural voice"
        if my_id == self.speak_id:                       # still the current quote?
            self._play_mp3(path)

    def pre_render(self, texts):
        """Make all quote voices in the background, so they play instantly later."""
        if not self.neural_available():
            return
        def work():
            import asyncio
            import hashlib
            import edge_tts
            for text in texts:
                path = VOICE_DIR / (hashlib.md5(text.encode()).hexdigest() + ".mp3")
                if path.exists():
                    continue
                try:
                    asyncio.run(edge_tts.Communicate(text, self.NEURAL_VOICE, rate="-12%",
                                                     pitch="-6Hz").save(str(path)))
                except Exception:
                    return
        threading.Thread(target=work, daemon=True).start()

    def _play_mp3(self, path):
        try:
            if self.platform.startswith("win"):
                p = str(path).replace("'", "''")
                cmd = ["powershell", "-NoProfile", "-Command",
                       "Add-Type -AssemblyName PresentationCore; "
                       "$m = New-Object System.Windows.Media.MediaPlayer; "
                       f"$m.Open([uri]'{p}'); $m.Volume = 1.0; $m.Play(); "
                       "Start-Sleep -Milliseconds 400; "
                       "while (-not $m.NaturalDuration.HasTimeSpan) { Start-Sleep -Milliseconds 100 }; "
                       "Start-Sleep -Milliseconds ([int]$m.NaturalDuration.TimeSpan.TotalMilliseconds)"]
                self.voice_proc = subprocess.Popen(cmd, creationflags=0x08000000)
            elif self.platform == "darwin":
                self.voice_proc = subprocess.Popen(["afplay", str(path)])
            else:
                for player in (["mpg123", "-q"], ["ffplay", "-nodisp", "-autoexit",
                                                   "-loglevel", "quiet"], ["cvlc", "--play-and-exit"]):
                    if shutil.which(player[0]):
                        self.voice_proc = subprocess.Popen(player + [str(path)],
                                                           stderr=subprocess.DEVNULL)
                        return
                self.voice_status = "install mpg123 to hear the natural voice"
        except Exception:
            self.voice_proc = None

    def mac_voice(self):
        """Best English voice on this Mac: Premium/Enhanced voices sound far better."""
        if not hasattr(self, "_mac_voice"):
            self._mac_voice = None
            try:
                listing = subprocess.run(["say", "-v", "?"], capture_output=True,
                                         text=True, timeout=5).stdout
                best = []
                for line in listing.splitlines():
                    if "en_" not in line:
                        continue
                    name = line.split("  ")[0].strip()
                    score = (3 if "Premium" in name else 2 if "Enhanced" in name else 0)
                    score += 1 if name.split()[0] in ("Evan", "Tom", "Alex", "Reed",
                                                      "Daniel", "Nathan", "Aaron") else 0
                    best.append((score, name))
                if best:
                    self._mac_voice = max(best)[1]
            except Exception:
                pass
        return self._mac_voice

    def _speak_local(self, text):
        """Computer's own voice: slightly slower, natural pitch, small pauses."""
        try:
            if self.platform.startswith("win"):
                xml = (text.replace("&", "&amp;").replace("<", "&lt;")
                       .replace(">", "&gt;"))
                xml = xml.replace(", ", ", <break time='250ms'/>").replace(
                    ". ", ". <break time='500ms'/>")
                ssml = ("<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
                        f"xml:lang='en-US'><prosody rate='-10%' volume='x-loud'>{xml}</prosody></speak>")
                ps_ssml = ssml.replace("'", "''")
                cmd = ["powershell", "-NoProfile", "-Command",
                       "Add-Type -AssemblyName System.Speech; "
                       "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Volume = 100; "
                       "$v = $s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo } | "
                       "Where-Object { $_.Culture.Name -like 'en*' -and $_.Gender -eq 'Male' } | "
                       "Select-Object -First 1; if ($v) { $s.SelectVoice($v.Name) }; "
                       f"$s.SpeakSsml('{ps_ssml}')"]
                self.voice_proc = subprocess.Popen(cmd, creationflags=0x08000000)
            elif self.platform == "darwin":
                cmd = ["say", "-r", "160"]
                text = "[[volm 1.0]] " + text
                if self.mac_voice():
                    cmd += ["-v", self.mac_voice()]
                self.voice_proc = subprocess.Popen(cmd + [text])
            else:
                exe = shutil.which("espeak-ng") or shutil.which("espeak")
                if exe:
                    self.voice_proc = subprocess.Popen(
                        [exe, "-v", "en-us+m3", "-s", "140", "-p", "40", "-g", "4", "-a", "200",
                         text],
                        stderr=subprocess.DEVNULL)
                elif shutil.which("spd-say"):
                    self.voice_proc = subprocess.Popen(["spd-say", "-r", "-20", text])
        except Exception:
            self.voice_proc = None

    @staticmethod
    def _kill(proc):
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    def stop_voice(self):
        self.speak_id += 1
        self._kill(self.voice_proc)
        self.voice_proc = None

    def stop_all(self):
        self.stop_voice()
        self.stop_music()


# ============================================================== music engine ===
class Synth:
    """Tiny pure-Python synthesizer: renders a seamless looping track to a .wav."""

    def __init__(self, seconds, rate=22050, seed=1):
        self.rate = rate
        self.n = int(seconds * rate)
        self.rnd = random.Random(seed)
        self.tables = {}
        self.cache = {}

    def buffer(self):
        return [0.0] * self.n

    def table(self, harm, size=2048):
        key = tuple(harm)
        if key not in self.tables:
            self.tables[key] = [sum(a * math.sin(2 * math.pi * k * i / size)
                                    for k, a in harm) for i in range(size)]
        return self.tables[key]

    def tone(self, freq, dur, harm, attack=0.005, release=0.05, decay=0.0,
             vib=0.0, vib_rate=5.0, trem=0.0):
        key = (freq, dur, tuple(harm), attack, release, decay, vib, vib_rate, trem)
        if key in self.cache:
            return self.cache[key]
        tab = self.table(harm)
        size = len(tab)
        n = max(1, int(dur * self.rate))
        na, nr = max(1, int(attack * self.rate)), max(1, int(release * self.rate))
        inc = freq * size / self.rate
        phase, sig = 0.0, [0.0] * n
        dk = math.exp(-decay / self.rate) if decay else 1.0
        amp = 1.0
        for i in range(n):
            step = inc
            if vib:
                step = inc * (1 + vib * math.sin(2 * math.pi * vib_rate * i / self.rate))
            phase = (phase + step) % size
            env = amp
            if i < na:
                env *= i / na
            if n - i < nr:
                env *= (n - i) / nr
            if trem:
                env *= 1 - trem * (0.5 + 0.5 * math.sin(2 * math.pi * 4.0 * i / self.rate))
            sig[i] = tab[int(phase)] * env
            amp *= dk
        self.cache[key] = sig
        return sig

    def add(self, buf, sig, start, gain):
        """Mix sig into buf at time start; wraps around so the loop is seamless."""
        i0 = int(start * self.rate)
        n = self.n
        for k, v in enumerate(sig):
            buf[(i0 + k) % n] += gain * v

    def kick(self, punch=1.0, length=0.35):
        key = ("kick", punch, length)
        if key not in self.cache:
            n = int(length * self.rate)
            sig, ph = [0.0] * n, 0.0
            for i in range(n):
                t = i / self.rate
                ph += 2 * math.pi * (45 + 110 * punch * math.exp(-t * 35)) / self.rate
                sig[i] = math.sin(ph) * math.exp(-t * 9)
            self.cache[key] = sig
        return self.cache[key]

    def noise(self, length, decay, bright=1.0, body_hz=0.0, seed=0):
        key = ("noise", length, decay, bright, body_hz, seed)
        if key not in self.cache:
            rnd = random.Random(seed)
            n = int(length * self.rate)
            sig, prev, lp = [0.0] * n, 0.0, 0.0
            for i in range(n):
                t = i / self.rate
                x = rnd.gauss(0, 1)
                hp = x - prev                      # brighter
                prev = x
                lp += 0.35 * (x - lp)              # darker
                v = (bright * hp + (1 - bright) * lp) * math.exp(-t * decay)
                if body_hz:
                    v += 0.6 * math.sin(2 * math.pi * body_hz * t) * math.exp(-t * 30)
                sig[i] = v
            self.cache[key] = sig
        return self.cache[key]

    def duck(self, buf, beat, depth=0.6, speed=9.0, offset=0.0):
        """Sidechain pumping: the sound dips on every beat (classic dance feel)."""
        bn = int(beat * self.rate)
        env = [1 - depth * math.exp(-speed * i / bn * beat * 4) for i in range(bn)]
        off = int(offset * self.rate)
        for i in range(self.n):
            buf[i] *= env[(i - off) % bn]

    def lowpass(self, buf, a):
        y = buf[-1]
        for i in range(self.n):
            y += a * (buf[i] - y)
            buf[i] = y

    def save(self, path, layers, peak=0.85):
        mix = [sum(vals) for vals in zip(*layers)]
        m = max(abs(v) for v in mix) or 1.0
        k = math.tanh(1.2)
        data = array.array("h", (int(32767 * peak * math.tanh(1.2 * v / m) / k) for v in mix))
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.rate)
            w.writeframes(data.tobytes())


def set_volume(path, gain):
    """Scales a 16-bit .wav file in place (used to keep music under the voice)."""
    with wave.open(str(path), "rb") as w:
        params = w.getparams()
        data = array.array("h", w.readframes(w.getnframes()))
    for i in range(len(data)):
        data[i] = int(data[i] * gain)
    with wave.open(str(path), "wb") as w:
        w.setparams(params)
        w.writeframes(data.tobytes())


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def make_game_music(path):
    """Catchy, driving electro loop (140 bpm, A minor), about 55 s long.
    The beat and bass never stop, so the loop point is just another bar:
    A groove + arpeggio -> B lead hook -> C short breakdown and riser ->
    D hook variation -> E hook again, ending with a snare roll into bar 1."""
    bpm = 140
    beat = 60 / bpm
    bar = 4 * beat
    bars = 32
    S = Synth(bars * bar, seed=11)
    drums, pump, lead = S.buffer(), S.buffer(), S.buffer()
    square = [(1, 1.0), (3, 1 / 3), (5, 1 / 5), (7, 1 / 7), (9, 1 / 9)]
    saw = [(k, 1 / k) for k in range(1, 8)]
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
    arp_a = [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 2, 3, 2]
    arp_b = [3, 2, 0, 2, 3, 1, 0, 1, 3, 2, 0, 2, 1, 2, 3, 1]
    hook = [[(81, 1), (79, .5), (76, .5), (79, 1), (76, .5), (74, .5)],
            [(77, 1), (76, .5), (72, .5), (74, 1), (72, 1)],
            [(76, 1), (79, .5), (84, .5), (83, 1), (79, 1)],
            [(79, 1.5), (81, .5), (83, 1), (86, 1)]]
    hook2 = [[(76, .5), (79, .5), (81, 1), (84, 1), (83, .5), (81, .5)],
             [(81, .5), (77, .5), (76, 1), (72, 1), (74, 1)],
             [(79, .5), (76, .5), (79, 1), (84, 1.5), (83, .5)],
             [(86, 1), (83, 1), (81, 1), (79, 1)]]
    for b in range(bars):
        t0 = b * bar
        ch = chords[b % 4]
        breakdown = 16 <= b < 20
        tones = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[0] + 24]
        order = arp_b if 20 <= b < 28 else arp_a
        for k in range(16):                                  # arpeggio hook
            note = tones[order[k]] + (12 if 20 <= b < 24 else 0)
            S.add(lead, S.tone(midi(note), beat / 4, square, 0.003, 0.04, decay=9),
                  t0 + k * beat / 4, 0.10 if b < 8 or breakdown else 0.065)
        for k in range(4):
            if not breakdown:
                S.add(drums, S.kick(), t0 + k * beat, 0.9)      # four on the floor
            S.add(drums, S.noise(0.12, 30, 1.0, seed=k), t0 + k * beat + beat / 2,
                  0.16)                                       # offbeat hat
            for q in (1, 3):
                S.add(drums, S.noise(0.04, 80, 1.0, seed=9), t0 + k * beat + q * beat / 4,
                      0.06)                                   # 16th ticks
        for k in (1, 3):                                      # clap
            S.add(drums, S.noise(0.22, 18, 0.7, body_hz=180, seed=3), t0 + k * beat, 0.32)
        if breakdown:                                         # long bass notes
            S.add(pump, S.tone(midi(ch[0] - 12), bar * 0.95, saw[:5], 0.01, 0.2,
                               decay=1.2), t0, 0.26)
        else:
            for k in range(4):                                # pumping offbeat bass
                S.add(pump, S.tone(midi(ch[0] - 12), beat / 2 * 0.9, saw[:5], 0.005, 0.05,
                                   decay=4), t0 + k * beat + beat / 2, 0.30)
        for note in ch:                                       # pad chord
            S.add(pump, S.tone(midi(note), bar, saw, 0.05, 0.1), t0,
                  0.06 if breakdown else 0.045)
        if b == 19:                                           # riser into the drop
            for q in range(16):
                S.add(drums, S.noise(0.06, 40, 0.8, body_hz=200, seed=4),
                      t0 + q * beat / 4, 0.04 + 0.012 * q)
        elif b % 8 == 7:                                      # snare fill (also b = 31,
            for q in range(8):                                # rolling into the loop)
                S.add(drums, S.noise(0.08, 35, 0.8, body_hz=200, seed=4),
                      t0 + 2 * beat + q * beat / 4, 0.10 + 0.02 * q)
        melody = (hook if 8 <= b < 16 or 24 <= b < 32 else
                  hook2 if 20 <= b < 24 else None)
        if melody:                                            # lead melody
            tm = t0
            for note, length in melody[b % 4]:
                d = length * beat
                S.add(lead, S.tone(midi(note), d * 0.95, saw, 0.01, 0.06, vib=0.004),
                      tm, 0.13)
                tm += d
        if b in (0, 8, 20, 24):
            S.add(drums, S.noise(1.5, 2.5, 1.0, seed=7), t0, 0.12)     # crash
    S.duck(pump, beat, depth=0.65)
    S.save(path, [drums, pump, lead])


def make_menu_music(path):
    """Chill, cosy lo-fi loop (78 bpm): warm electric-piano chords, round bass,
    soft swung drums, vinyl crackle and a little music-box melody."""
    bpm = 78
    beat = 60 / bpm
    bar = 4 * beat
    bars = 8
    S = Synth(bars * bar, seed=5)
    keys, low, drums, extra = S.buffer(), S.buffer(), S.buffer(), S.buffer()
    epiano = [(1, 1.0), (2, 0.25), (3, 0.08), (4, 0.04)]
    sine = [(1, 1.0)]
    chords = [[53, 57, 60, 64], [57, 60, 64, 67], [50, 53, 57, 60], [46, 50, 53, 57]]
    bass = [41, 45, 38, 46]                                   # Fmaj7 Am7 Dm7 Bbmaj7
    swing = beat / 2 * 0.18
    melody = [[(72, 1.5), (69, 0.5), (67, 2)], [(69, 1), (72, 1), (76, 2)],
              [(74, 1.5), (72, 0.5), (69, 2)], [(70, 1), (69, 1), (65, 2)]]
    for b in range(bars):
        t0 = b * bar
        ch = chords[b % 4]
        for hit, gain in ((0, 0.11), (1.5, 0.07), (3, 0.06)):   # strummed chords
            for j, note in enumerate(ch):
                S.add(keys, S.tone(midi(note), 2.2, epiano, 0.01, 0.4, decay=1.6,
                                   vib=0.002, vib_rate=0.6, trem=0.15),
                      t0 + hit * beat + j * 0.025, gain)
        S.add(low, S.tone(midi(bass[b % 4]), beat * 1.8, sine + [(2, 0.2)], 0.02, 0.3,
                          decay=1.0), t0, 0.32)
        S.add(low, S.tone(midi(bass[b % 4]), beat * 0.9, sine + [(2, 0.2)], 0.02, 0.2,
                          decay=2.0), t0 + 2.5 * beat, 0.22)
        for k in (0, 2):                                      # soft kick
            S.add(drums, S.kick(punch=0.5, length=0.4), t0 + k * beat, 0.45)
        S.add(drums, S.kick(punch=0.4, length=0.3), t0 + 2.75 * beat, 0.22)
        for k in (1, 3):                                      # brushed snare
            S.add(drums, S.noise(0.3, 14, 0.25, seed=2), t0 + k * beat, 0.22)
        for k in range(8):                                    # swung shaker
            S.add(drums, S.noise(0.06, 45, 0.9, seed=6),
                  t0 + k * beat / 2 + (swing if k % 2 else 0), 0.04 if k % 2 else 0.06)
        if b >= 4:                                            # music-box melody
            tm = t0
            for note, length in melody[b % 4]:
                S.add(extra, S.tone(midi(note + 12), 1.2, [(1, 1.0), (3, 0.15), (4, 0.1)],
                                    0.003, 0.3, decay=3.0), tm, 0.07)
                tm += length * beat
    rnd = random.Random(1)                                    # vinyl crackle + hiss
    for i in range(S.n):
        if rnd.random() < 0.0006:
            extra[i] += rnd.uniform(-0.25, 0.25)
        extra[i] += rnd.gauss(0, 0.006)
    S.lowpass(keys, 0.35)                                     # warm, dusty sound
    S.lowpass(drums, 0.5)
    S.duck(keys, beat * 2, depth=0.15, speed=5)               # gentle breathing
    S.save(path, [keys, low, drums, extra], peak=0.8)


def make_epic_music_pure(path, rate=22050):
    """Same epic track as make_epic_music, in plain Python (no numpy needed).
    Takes a few seconds; it runs in the background when the game starts."""
    rnd = random.Random(7)
    beat = 60 / 80
    bar = 4 * beat
    bars = 16
    loop_n = int(rate * bars * bar)
    out = [0.0] * loop_n
    table_n = 2048
    tables = {}

    def table(harm):
        key = tuple(harm)
        if key not in tables:
            tables[key] = [sum(a * math.sin(2 * math.pi * k * i / table_n) for k, a in harm)
                           for i in range(table_n)]
        return tables[key]

    def tone(freq, dur, harm, attack, release, vib=0.0):
        tab = table(harm)
        n = int(dur * rate)
        sig = [0.0] * n
        phase = rnd.uniform(0, table_n)
        inc = freq * table_n / rate
        na, nr = max(1, int(attack * rate)), max(1, int(release * rate))
        for i in range(n):
            step = inc
            if vib and i > rate * 0.25:
                step = inc * (1 + vib * math.sin(2 * math.pi * 5.0 * i / rate))
            phase = (phase + step) % table_n
            env = 1.0
            if i < na:
                env = i / na
            if n - i < nr:
                env = min(env, (n - i) / nr)
            sig[i] = tab[int(phase)] * env
        return sig

    def add(sig, start, gain):                      # wraps around: seamless loop
        i0 = int(start * rate)
        for k, v in enumerate(sig):
            out[(i0 + k) % loop_n] += gain * v

    saw = [(k, 1 / k) for k in range(1, 9)]
    horn = [(1, 1.0), (2, 0.6), (3, 0.35), (4, 0.2), (5, 0.1)]
    chords = [(146.83, 174.61, 220.00), (116.54, 146.83, 174.61),
              (174.61, 220.00, 261.63), (130.81, 164.81, 196.00)]
    roots = [73.42, 58.27, 87.31, 65.41]
    N = {"D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00, "A4": 440.00,
         "Bb4": 466.16, "C5": 523.25, "D5": 587.33}
    melody = [[("A4", 2), ("D5", 2)], [("D5", 1), ("C5", 1), ("Bb4", 2)],
              [("A4", 2), ("C5", 2)], [("G4", 3), ("E4", 1)],
              [("F4", 1), ("A4", 1), ("D5", 2)], [("D5", 2), ("Bb4", 2)],
              [("C5", 2), ("A4", 1), ("C5", 1)], [("G4", 2), ("E4", 2)]]

    # pre-render the repeating parts once
    pads, ostis, basses = [], [], []
    for ci in range(4):
        pad = [0.0] * int((bar + 0.8) * rate)
        for f in chords[ci]:
            for mult, g in ((1, 1.0), (2, 0.45), (1.003, 0.8)):
                for k, v in enumerate(tone(f * mult, bar + 0.8, saw, 0.5, 0.9)):
                    pad[k] += g * v
        pads.append(pad)
        notes = {}
        for m in (1, 1.5, 2):
            sig = tone(chords[ci][0] * m, beat / 2, saw[:5], 0.005, 0.12)
            notes[m] = [v * math.exp(-k / rate * 9) for k, v in enumerate(sig)]
        ostis.append(notes)
        basses.append(tone(roots[ci], bar + 0.4, saw[:6], 0.08, 0.5))
        time.sleep(0)                               # let the game keep running

    def make_boom():
        n = int(1.2 * rate)
        sig, ph = [0.0] * n, 0.0
        for i in range(n):
            t = i / rate
            ph += 2 * math.pi * (48 + 40 * math.exp(-t * 30)) / rate
            sig[i] = math.sin(ph) * math.exp(-t * 4.5)
            if i < 0.01 * rate:
                sig[i] += rnd.gauss(0, 0.5)
        return sig

    def make_noise(dur, decay, tone_hz=0.0):
        n, prev, sig = int(dur * rate), 0.0, []
        for i in range(n):
            x = rnd.gauss(0, 1)
            t = i / rate
            v = (x - prev) * math.exp(-t * decay)
            if tone_hz:
                v += 0.4 * math.sin(2 * math.pi * tone_hz * t) * math.exp(-t * 25)
            sig.append(v)
            prev = x
        return sig

    boom, snare, cymbal = make_boom(), make_noise(0.35, 16, 190), make_noise(2.5, 1.8)
    pattern = [1, 1, 1.5, 1, 1, 1.5, 1, 2]
    for b in range(bars):
        ci, t0 = b % 4, b * bar
        loud = 0.7 if b < 4 else (0.85 if b < 8 else 1.0)
        add(pads[ci], t0, 0.05 * loud)
        for k, m in enumerate(pattern):
            add(ostis[ci][m], t0 + k * beat / 2, 0.11 * loud)
        if b >= 4:
            add(basses[ci], t0, 0.12)
            add(boom, t0, 0.6)
            add(boom, t0 + 2 * beat, 0.5)
            if b % 4 == 3:
                add(boom, t0 + 3 * beat, 0.4)
                add(boom, t0 + 3.5 * beat, 0.55)
        if b >= 8:
            add(snare, t0 + beat, 0.22)
            add(snare, t0 + 3 * beat, 0.22)
            tm = t0
            for name, length in melody[b - 8]:
                d = length * beat
                add(tone(N[name], d + 0.15, horn, 0.07, 0.25, vib=0.006), tm, 0.22)
                add(tone(N[name] / 2, d + 0.15, horn, 0.07, 0.25), tm, 0.06)
                tm += d
        if b in (8, 12):
            add(cymbal, t0, 0.12)
        time.sleep(0)

    wet = list(out)                                  # small hall reverb
    for delay, g in ((0.031, 0.35), (0.071, 0.25), (0.167, 0.15)):
        d = int(delay * rate)
        for i in range(loop_n):
            wet[i] += g * out[i - d]
    peak = max(abs(0.75 * a + 0.25 * w) for a, w in zip(out, wet)) or 1.0
    data = array.array("h", (int(32767 * 0.9 * math.tanh(1.3 * (0.75 * a + 0.25 * w) / peak)
                                 / math.tanh(1.3)) for a, w in zip(out, wet)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def make_epic_music(path, rate=32000):
    """48-second epic loop in D minor (Dm - Bb - F - C), 80 bpm:
    soft strings intro, then bass and drums, then a heroic horn melody."""
    import numpy as np
    rng = np.random.default_rng(7)
    beat = 60 / 80
    bar = 4 * beat
    bars = 16
    total = int(rate * (bars * bar + 3))          # 3 s extra for the tails
    out = np.zeros(total)

    def tone(freq, dur, harm, attack, release, vib=0.0, detune=1.0):
        n = int(dur * rate)
        t = np.arange(n) / rate
        f = freq * detune * np.ones(n)
        if vib:                                   # vibrato fades in after 0.25 s
            f = f * (1 + vib * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.25) / 0.4, 0, 1))
        phase = 2 * np.pi * np.cumsum(f) / rate
        sig = sum(a * np.sin(k * phase + rng.uniform(0, 6.28)) for k, a in harm)
        env = np.clip(t / attack, 0, 1) * np.clip((dur - t) / release, 0, 1)
        return sig * env

    def add(sig, start, gain):
        i = int(start * rate)
        j = min(total, i + len(sig))
        out[i:j] += gain * sig[:j - i]

    saw = [(k, 1 / k) for k in range(1, 9)]          # warm string sound
    horn = [(1, 1.0), (2, 0.6), (3, 0.35), (4, 0.2), (5, 0.1)]
    chords = [(146.83, 174.61, 220.00), (116.54, 146.83, 174.61),
              (174.61, 220.00, 261.63), (130.81, 164.81, 196.00)]
    roots = [73.42, 58.27, 87.31, 65.41]
    N = {"D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00, "A4": 440.00,
         "Bb4": 466.16, "C5": 523.25, "D5": 587.33}
    melody = [[("A4", 2), ("D5", 2)], [("D5", 1), ("C5", 1), ("Bb4", 2)],
              [("A4", 2), ("C5", 2)], [("G4", 3), ("E4", 1)],
              [("F4", 1), ("A4", 1), ("D5", 2)], [("D5", 2), ("Bb4", 2)],
              [("C5", 2), ("A4", 1), ("C5", 1)], [("G4", 2), ("E4", 2)]]

    def boom(start, gain):                        # big low drum
        n = int(1.2 * rate)
        t = np.arange(n) / rate
        f = 48 + 40 * np.exp(-t * 30)
        sig = np.sin(2 * np.pi * np.cumsum(f) / rate) * np.exp(-t * 4.5)
        sig[:int(0.01 * rate)] += rng.normal(0, 0.5, int(0.01 * rate))
        add(sig, start, gain)

    def snare(start, gain):
        n = int(0.35 * rate)
        t = np.arange(n) / rate
        noise = rng.normal(0, 1, n)
        noise = np.diff(noise, prepend=0)          # brighter
        add(noise * np.exp(-t * 16) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25),
            start, gain)

    def cymbal(start, gain):
        n = int(2.5 * rate)
        t = np.arange(n) / rate
        noise = np.diff(rng.normal(0, 1, n), prepend=0)
        add(noise * np.exp(-t * 1.8), start, gain)

    for b in range(bars):
        ci = b % 4
        t0 = b * bar
        loud = 0.7 if b < 4 else (0.85 if b < 8 else 1.0)    # build-up
        # strings: chord + octave above, two slightly detuned voices, overlapping
        for f in chords[ci]:
            for mult, g in ((1, 1.0), (2, 0.45)):
                for det in (0.997, 1.003):
                    add(tone(f * mult, bar + 0.8, saw, 0.5, 0.9, detune=det), t0, 0.05 * g * loud)
        # driving eighth notes (root, root, fifth, root ...)
        pattern = [1, 1, 1.5, 1, 1, 1.5, 1, 2]
        for k, m in enumerate(pattern):
            note = tone(chords[ci][0] * m, beat / 2, saw[:5], 0.005, 0.12)
            note *= np.exp(-np.arange(len(note)) / rate * 9)
            add(note, t0 + k * beat / 2, 0.11 * loud)
        if b >= 4:                                 # bass and drums
            add(tone(roots[ci], bar + 0.4, saw[:6], 0.08, 0.5), t0, 0.12)
            boom(t0, 0.6)
            boom(t0 + 2 * beat, 0.5)
            if b % 4 == 3:                         # fill at the end of each phrase
                boom(t0 + 3 * beat, 0.4)
                boom(t0 + 3.5 * beat, 0.55)
        if b >= 8:
            snare(t0 + beat, 0.22)
            snare(t0 + 3 * beat, 0.22)
            tm = t0
            for name, length in melody[b - 8]:     # heroic horn line
                d = length * beat
                add(tone(N[name], d + 0.15, horn, 0.07, 0.25, vib=0.006), tm, 0.22)
                add(tone(N[name] / 2, d + 0.15, horn, 0.07, 0.25), tm, 0.06)
                tm += d
        if b in (8, 12):
            cymbal(t0, 0.12)
    boom(bars * bar, 0.0)                          # (keeps the tail length)

    # fold the tail back onto the start so the loop is seamless
    loop_n = int(rate * bars * bar)
    tail = out[loop_n:]
    out = out[:loop_n]
    out[:len(tail)] += tail

    # simple hall reverb: a few echoes with feedback
    wet = out.copy()
    for delay, g in ((0.031, 0.35), (0.047, 0.3), (0.071, 0.25), (0.113, 0.2), (0.167, 0.15)):
        d = int(delay * rate)
        wet[d:] += g * out[:-d]
        wet[:d] += g * out[-d:]                    # wrap around (loop)
    mix_ = 0.75 * out + 0.25 * wet
    mix_ = np.tanh(1.3 * mix_ / (np.max(np.abs(mix_)) + 1e-9))   # gentle limiter
    mix_ = 0.9 * mix_ / np.max(np.abs(mix_))
    data = (mix_ * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def is_light(c):
    try:
        r, g_, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    except (ValueError, TypeError):
        return False
    return 0.299 * r + 0.587 * g_ + 0.114 * b > 200


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
            "lands": ["land_desert"], "land": "land_desert",
            "accs": ["acc_none"], "acc": "acc_none",
            "hairs": ["hair_none"], "hair": "hair_none",
            "eyes_owned": ["eyes_classic"], "eyes": "eyes_classic",
            "outfits": ["outfit_none"], "outfit": "outfit_none",
            "couple": 0, "couple_on": 0,
            "stat_runs": 0, "stat_jumps": 0, "stat_bosses": 0, "stat_coins": 0,
            "stat_diamonds": 0, "stat_level": 1, "stat_time": 0.0,
            "diamonds": 0, "trophy": 0, "miners": 1, "pickaxe": 0, "cart": 0,
            "mine_store": 0.0, "mine_time": time.time()}
    try:
        data.update(json.loads(SAVE_FILE.read_text()))
    except Exception:
        pass
    return data


class ScaledCanvas:
    """Wraps the tk Canvas: the game always draws at 900x300 and this scales
    everything (coordinates, line widths, fonts) to the real window size."""

    def __init__(self, canvas):
        self.cv = canvas
        self.f, self.ox, self.oy = 1.0, 0.0, 0.0

    def resize(self, w, h):
        self.f = max(0.2, min(w / WIDTH, h / HEIGHT))
        self.ox = (w - WIDTH * self.f) / 2            # black bars if the shape differs
        self.oy = (h - HEIGHT * self.f) / 2

    def _coords(self, args):
        flat = []
        for a in args:
            if isinstance(a, (list, tuple)):
                flat.extend(v for p in a for v in (p if isinstance(p, (list, tuple)) else (p,)))
            else:
                flat.append(a)
        f, ox, oy = self.f, self.ox, self.oy
        return [v * f + (ox if i % 2 == 0 else oy) for i, v in enumerate(flat)]

    def _kw(self, kw):
        f = self.f
        if f != 1.0:
            if "width" in kw and kw["width"]:
                kw["width"] = kw["width"] * f
            if "font" in kw and isinstance(kw["font"], tuple) and len(kw["font"]) > 1:
                fn = list(kw["font"])
                fn[1] = max(1, int(round(fn[1] * f)))
                kw["font"] = tuple(fn)
        return kw

    def create_text(self, *a, **kw):
        return self.cv.create_text(*self._coords(a), **self._kw(kw))

    def create_rectangle(self, *a, **kw):
        return self.cv.create_rectangle(*self._coords(a), **self._kw(kw))

    def create_oval(self, *a, **kw):
        return self.cv.create_oval(*self._coords(a), **self._kw(kw))

    def create_polygon(self, *a, **kw):
        return self.cv.create_polygon(*self._coords(a), **self._kw(kw))

    def create_line(self, *a, **kw):
        return self.cv.create_line(*self._coords(a), **self._kw(kw))

    def create_arc(self, *a, **kw):
        return self.cv.create_arc(*self._coords(a), **self._kw(kw))

    def __getattr__(self, name):
        return getattr(self.cv, name)


class DinoGame:
    def __init__(self, root):
        self.root = root
        root.title("Dino Runner")
        root.minsize(WIDTH // 2, HEIGHT // 2)
        raw = tk.Canvas(root, width=WIDTH, height=HEIGHT, highlightthickness=0,
                        bg="#000000")
        raw.pack(fill="both", expand=True)
        self.canvas = ScaledCanvas(raw)
        raw.bind("<Configure>", lambda e: self.canvas.resize(e.width, e.height))
        self.fullscreen = False
        root.bind("<F11>", lambda e: self.toggle_fullscreen())
        root.bind("<FocusOut>", lambda e: self.set_pause(True))   # auto-pause
        raw.bind("<Button-1>", self.click)
        self.paused = False
        root.bind("<KeyPress>", self.key_press)
        root.bind("<KeyRelease>", self.key_release)
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self.audio = Audio()
        self.audio.prepare_music()            # composes the music in the background
        self.menu_index = 0
        self.quote_i, self.quote_t, self.affirmation = 0, 0, AFFIRMATIONS[0]
        self.embers = []
        self.sound_on = True
        self.mine_index = 0

        self.save = load_save()
        self.stars = [(random.randint(0, WIDTH), random.randint(10, 160),
                       random.choice([1, 1, 2])) for _ in range(40)]
        self.shop_index = 0
        self.shop_scroll = 0
        self.message = ""
        self.tick = 0              # animation clock that also runs in menus
        self.reset()
        self.state = "menu"        # menu -> running -> over ; shop ; mine ; motivation
        before = self.save["mine_store"]
        self.update_mine(offline=True)
        dug = int(self.save["mine_store"] - before)
        if dug > 0:
            full = " (cart full!)" if self.save["mine_store"] >= self.mine_cap() else ""
            self.show_banner(f"While you were away your miners dug {dug} coins{full}", 240,
                             "#ffb84d")
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
        self.dj_cool = 0
        self.speed = START_SPEED
        self.distance = 0.0
        self.bonus = 0
        self.combo = 0
        self.run_coins = 0
        self.run_gems = 0
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
        self.paused = False
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
        # boss fights
        self.boss = None
        self.bosses_beaten = 0
        self.next_boss = BOSS_EVERY
        self.sparks = []           # pick-ups that let you shoot the boss
        self.shots = []            # your shots flying at the boss

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
    MENU = ["PLAY", "POWER-UP SHOP", "DINO STYLE", "DINO MINE", "MOTIVATION ROOM",
            "MUSIC", "FULLSCREEN", "QUIT"]

    PAUSE_BTN = (WIDTH / 2 - 15, 8, WIDTH / 2 + 15, 36)

    def set_pause(self, on):
        if self.state != "running":
            return
        self.paused = on
        self.ducking = False

    def click(self, e):
        sc = self.canvas
        gx, gy = (e.x - sc.ox) / sc.f, (e.y - sc.oy) / sc.f
        x1, y1, x2, y2 = self.PAUSE_BTN
        if self.state == "running" and x1 <= gx <= x2 and y1 <= gy <= y2:
            self.set_pause(not self.paused)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def key_press(self, e):
        k = e.keysym.lower()
        st = self.state
        if k == "f11":
            return
        if k == "escape" and getattr(self, "fullscreen", False) and st in ("menu",
                                                                           "running", "over"):
            self.toggle_fullscreen()                  # Esc leaves fullscreen first
            return
        if st == "shop":
            self.shop_key(k)
        elif st == "mine":
            self.mine_key(k)
        elif st == "menu":
            self.menu_key(k)
        elif st == "motivation":
            self.motivation_key(k)
        elif k == "q":
            self.quit()
        elif st == "running" and getattr(self, "paused", False):
            if k in ("p", "space", "return"):
                self.set_pause(False)
            elif k in ("m", "escape"):                 # quit to the menu
                self.paused = False
                self.die()
                self.shake = 0
                self.state = "menu"
        elif st == "running" and k == "p":
            self.set_pause(True)
        elif st == "running":
            if k in ("space", "up", "w"):
                self.on_jump()
            elif k in ("down", "s"):
                self.duck_press()
            elif k == "x":
                self.use_slowmo()
            elif k == "escape":                      # give up this run
                self.die()
                self.shake = 0
                self.state = "menu"
        elif st == "over" and not self.shake:
            if k in ("space", "up", "w"):
                self.on_jump()
            elif k == "b":
                self.state, self.message = "shop", ""
            elif k in ("m", "escape"):
                self.state = "menu"

    def menu_key(self, k):
        if k in ("up", "w"):
            self.menu_index = (self.menu_index - 1) % len(self.MENU)
        elif k in ("down", "s"):
            self.menu_index = (self.menu_index + 1) % len(self.MENU)
        elif k in ("q", "escape"):
            self.quit()
        elif k in ("space", "return"):
            choice = self.MENU[self.menu_index]
            if choice == "PLAY":
                self.reset()
                self.state = "running"
                self.audio.play_track(None)
            elif choice in ("POWER-UP SHOP", "DINO STYLE"):
                self.open_shop("power" if choice == "POWER-UP SHOP" else "style")
            elif choice == "MOTIVATION ROOM":
                self.enter_motivation()
            elif choice == "FULLSCREEN":
                self.toggle_fullscreen()
            elif choice == "MUSIC":
                self.save["music"] = 0 if self.save.get("music", 1) else 1
                self.write_save()
                self.sync_music()
            elif choice == "DINO MINE":
                self.update_mine()
                self.state, self.message = "mine", ""
            else:
                self.quit()

    def quit(self):
        self.update_mine()
        self.write_save()
        self.audio.stop_all()
        self.root.destroy()

    # ------------------------------------------------------------- the mine ---
    MINE_MENU = ["COLLECT COINS", "HIRE MINER", "BETTER PICKAXE", "BIGGER CART", "BACK"]

    def mine_rate(self):
        """Coins per minute for all miners together."""
        return self.save["miners"] * 3.0 * (1 + 0.8 * self.save["pickaxe"])

    def mine_cap(self):
        """What the cart can hold while the game is closed (60 .. 300 coins).
        While the game is open the miners keep digging without a limit."""
        return 60 * (1 + self.save["cart"])

    def update_mine(self, offline=False):
        now = time.time()
        dt = min(max(0.0, now - self.save["mine_time"]), MINE_MAX_OFFLINE)
        if not offline:
            dt = min(dt, 120)            # online: a hiccup or sleep never counts as away
        gain = self.mine_rate() / 60 * dt
        store = self.save["mine_store"]
        if offline:                      # away: only as much as the cart holds
            store = max(store, min(self.mine_cap(), store + gain))
        else:                            # online: no limit, it pays to keep playing
            store += gain
        self.save["mine_store"] = store
        self.save["mine_time"] = now

    def mine_cost(self, item):
        sv = self.save
        if item == "HIRE MINER":
            i = sv["miners"] - 1
            return MINER_COSTS[i] if i < len(MINER_COSTS) else None
        if item == "BETTER PICKAXE":
            return PICK_COSTS[sv["pickaxe"]] if sv["pickaxe"] < len(PICK_COSTS) else None
        if item == "BIGGER CART":
            return CART_COSTS[sv["cart"]] if sv["cart"] < len(CART_COSTS) else None
        return None

    def mine_key(self, k):
        if k in ("up", "w"):
            self.mine_index = (self.mine_index - 1) % len(self.MINE_MENU)
        elif k in ("down", "s"):
            self.mine_index = (self.mine_index + 1) % len(self.MINE_MENU)
        elif k in ("escape", "b"):
            self.state = "menu"
        elif k == "c":
            self.mine_collect()
        elif k in ("space", "return"):
            item = self.MINE_MENU[self.mine_index]
            if item == "BACK":
                self.state = "menu"
            elif item == "COLLECT COINS":
                self.mine_collect()
            else:
                cost = self.mine_cost(item)
                if cost is None:
                    self.message = "Already maxed out"
                elif self.save["diamonds"] < cost:
                    self.message = f"Not enough diamonds (need {cost})"
                else:
                    self.update_mine()
                    self.save["diamonds"] -= cost
                    key = {"HIRE MINER": "miners", "BETTER PICKAXE": "pickaxe",
                           "BIGGER CART": "cart"}[item]
                    self.save[key] += 1
                    self.message = {"miners": "A new miner joins the crew!",
                                    "pickaxe": "Sharper pickaxes: faster digging!",
                                    "cart": "Bigger cart: keeps more coins while you're away!"}[key]
                    self.burst(700, 120, 30, ["#5ce1ff", "#ffffff"], speed=5, life=35)
                    self.write_save()

    def mine_collect(self):
        self.update_mine()
        got = int(self.save["mine_store"])
        if got <= 0:
            self.message = "The cart is empty - come back later"
            return
        self.save["mine_store"] -= got
        self.save["coins"] += got
        self.message = f"Collected {got} coins!"
        self.burst(760, 200, 35, [self.coin_col(), "#fff2a8"], speed=6, life=40)
        self.write_save()

    # ---------------------------------------------------- motivation room ---
    def enter_motivation(self):
        self.state = "motivation"
        self.embers = []
        self.audio.pre_render([self.spoken_text(i) for i in range(len(QUOTES))])
        self.show_quote(random.randrange(len(QUOTES)))

    @staticmethod
    def spoken_text(i):
        text, who = QUOTES[i]
        name = who.split(",")[0].replace("(attributed)", "").strip()
        return f"{text} ... {name}."

    def show_quote(self, i):
        self.quote_i = i % len(QUOTES)
        self.quote_t = 0
        self.affirmation = random.choice(AFFIRMATIONS)
        if self.sound_on:
            self.audio.speak(self.spoken_text(self.quote_i))

    def motivation_key(self, k):
        if k in ("space", "right", "return", "d"):
            self.show_quote(self.quote_i + 1)
        elif k in ("left", "a"):
            self.show_quote(self.quote_i - 1)
        elif k == "m":
            self.sound_on = not self.sound_on
            if self.sound_on:
                self.show_quote(self.quote_i)
            else:
                self.audio.stop_voice()
            self.sync_music()
        elif k == "v":
            self.audio.install_neural()
        elif k in ("escape", "b", "q"):
            self.audio.stop_voice()
            self.state = "menu"

    def update_motivation(self):
        self.tick += 1
        if self.tick % 30 == 0 and self.audio.poll_install():   # voice just installed
            self.audio.pre_render([self.spoken_text(i) for i in range(len(QUOTES))])
            if self.sound_on:
                self.show_quote(self.quote_i)
        self.quote_t += 1
        if self.quote_t > 900:                        # new quote every 15 s
            self.show_quote(self.quote_i + 1)
        if self.tick % 4 == 0:
            self.embers.append([random.uniform(0, WIDTH), HEIGHT + 5,
                                random.uniform(0.4, 1.3), random.uniform(0, 6)])
        for e in self.embers:
            e[1] -= e[2]
            e[3] += 0.05
        self.embers = [e for e in self.embers if e[1] > -10]

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
        if self.state == "over":
            if self.shake:
                return
            self.reset()
            self.state = "running"
            self.audio.play_track(None)            # restart the song from the top
        elif self.state == "running":
            jump = JUMP_SPEED * (1.2 if self.boost_is("MOON JUMP") else 1.0)
            if self.on_ground():
                self.vel_y = jump
                self.save["stat_jumps"] += 1
                self.air_jumps = self.save["doublejump"]
                self.dust(self.dino_x + 15, GROUND_Y, 6)
            elif self.air_jumps > 0 and getattr(self, "dj_cool", 0) <= 0:
                self.air_jumps -= 1
                self.dj_cool = 180                    # 3 s before it works again
                self.vel_y = min(self.vel_y, jump * 0.62)   # a smaller hop than before
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
        return self.save[SLOT_LIST[kind]]

    def item_status(self, item):
        iid, _, _, _, kind, mx = item
        if kind == "toggle":
            if not self.save[iid]:
                return ""
            return "ON" if self.save[iid + "_on"] else "off"
        if kind in COSMETIC:
            if self.save[kind] == iid:
                return "EQUIPPED"
            return "owned" if iid in self.owned_list(kind) else ""
        if kind == "perm":
            return "owned" if self.save[iid] else ""
        return f"{self.save[iid]}/{mx}"

    def shop_items(self):
        return SHOPS[getattr(self, "shop_tab", "power")][1]

    def open_shop(self, tab):
        self.shop_tab = tab
        self.state, self.message = "shop", ""
        self.shop_index = self.shop_scroll = 0

    def shop_key(self, k):
        items = self.shop_items()
        self.shop_index %= len(items)
        if k in ("up", "w"):
            self.shop_index = (self.shop_index - 1) % len(items)
        elif k in ("down", "s"):
            self.shop_index = (self.shop_index + 1) % len(items)
        elif k in ("tab", "left", "right", "a", "d"):          # switch shop
            self.open_shop("style" if getattr(self, "shop_tab", "power") == "power"
                           else "power")
            return
        elif k in ("b", "escape"):
            self.state = "menu"
        elif k in ("space", "return"):
            self.buy(items[self.shop_index])
        visible = 9
        if self.shop_index < self.shop_scroll:
            self.shop_scroll = self.shop_index
        elif self.shop_index >= self.shop_scroll + visible:
            self.shop_scroll = self.shop_index - visible + 1

    def buy(self, item):
        iid, name, _, _, kind, mx = item
        if kind == "toggle" and self.save[iid]:
            self.save[iid + "_on"] = 0 if self.save[iid + "_on"] else 1
            self.message = f"{name}: " + ("ON" if self.save[iid + "_on"] else "off")
            self.write_save()
            return
        if kind in COSMETIC and iid in self.owned_list(kind):
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
        if kind in COSMETIC:
            self.owned_list(kind).append(iid)
            self.save[kind] = iid
        elif kind == "toggle":
            self.save[iid] = 1
            self.save[iid + "_on"] = 1
        else:
            self.save[iid] += 1
        self.message = f"Bought {name}!"
        self.burst(WIDTH / 2, 60, 30, CONFETTI, speed=5, life=40)
        if iid == "trophy":
            self.message = "YOU ARE A LEGEND!"
            for x in (150, 450, 750):
                self.burst(x, 80, 50, CONFETTI + ["#ffcc00"], speed=8, life=80)
            self.beep()
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

    def add_coin(self, x, y, value=1, vy=0.0, big=False, gem=False):
        self.coins.append(dict(x=x, y=y, phase=random.uniform(0, 6), value=value,
                               vy=vy, big=big, gem=gem))

    def spawn_coins(self):
        # the further you get, the more and the bigger the coin trails
        n = random.choice([2, 3, 3, 4]) + min(self.level // 3, 2)
        base = GROUND_Y - random.choice([30, 70, 100])
        for i in range(n):
            arc = -22 * math.sin(math.pi * i / (n - 1))
            self.add_coin(WIDTH + i * 26, base + arc)
        if self.level >= 2 and random.random() < 0.05:   # rare diamond above a trail
            self.add_coin(WIDTH + n * 13, base - 40, value=1, big=True, gem=True)
        f = max(0.55, 1.0 - 0.05 * (self.level - 1))
        self.next_coin = random.randint(int(220 * f), int(420 * f))
        if self.boost_is("COIN FRENZY"):
            self.next_coin = 40

    # ------------------------------------------------- random encounters ---
    # name: (frames it lasts, banner text, first level it can happen)
    EVENTS = {
        "COIN RAIN": (300, "grab them!", 1),
        "TREASURE": (1, "big coin ahead (+10)", 1),
        "DIAMOND": (1, "a rare diamond - jump high!", 1),
        "BONUS ZONE": (420, "score x2", 1),
        "ECLIPSE": (500, "lights out...", 1),
        "LOW GRAVITY": (420, "floaty jumps", 1),
        "BIRD FLOCK": (1, "here they come", 2),
        "SPEED RUSH": (360, "faster, but score x2", 2),
        "CACTUS PARADE": (1, "jump, jump, jump!", 2),
        "METEOR SHOWER": (260, "watch the red shadows!", 3),
        "LIGHTNING STORM": (380, "jump when it strikes!", 3),
    }

    def event_is(self, name):
        return self.event is not None and self.event[0] == name

    def start_event(self):
        options = [n for n, (_, _, lvl) in self.EVENTS.items() if self.level >= lvl]
        name = random.choice(options)
        frames, subtitle, _ = self.EVENTS[name]
        self.event = (name, frames)
        self.show_banner(f"{name}: {subtitle}", 110, "#b366ff")
        self.beep()
        if name == "TREASURE":
            self.add_coin(WIDTH + 40, GROUND_Y - 105, value=10, big=True)
        elif name == "DIAMOND":
            self.add_coin(WIDTH + 40, GROUND_Y - 118, value=1, big=True, gem=True)
        elif name == "BIRD FLOCK":
            for i in range(random.randint(3, 5)):
                self.add_bird(WIDTH + 20 + i * self.speed * 45,
                              random.choice(["low", "mid"]))
            self.next_spawn = 45 * 5 + 40
        elif name == "CACTUS PARADE":
            n = random.randint(4, 6)
            for i in range(n):
                self.add_obstacle("cactus", WIDTH + 20 + i * self.speed * 38, GROUND_Y,
                                  14, 32, n=1, cw=14)
            self.next_spawn = 38 * n + 50
        elif name in ("METEOR SHOWER", "LIGHTNING STORM"):
            self.next_spawn = frames + 20           # no other obstacles meanwhile
        self.next_event = random.randint(1000, 1700)

    def update_event(self, ws):
        if self.event is None:
            if self.boss is None:
                self.next_event -= ws
            if self.next_event <= 0 and self.state == "running" and self.boss is None:
                self.start_event()
            return
        name, left = self.event
        if name == "COIN RAIN" and self.frame % 16 == 0:
            self.add_coin(random.uniform(250, WIDTH), -10,
                          vy=random.uniform(2.5, 4.0))
        elif name == "METEOR SHOWER" and self.frame % 55 == 0 and left > 40:
            self.add_meteor(random.uniform(WIDTH * 0.4, WIDTH * 0.85))
        elif name == "LIGHTNING STORM" and self.frame % 70 == 0 and left > 60:
            self.add_bolt()
        left -= ws
        self.event = (name, left) if left > 0 else None

    def add_bolt(self, x=None):
        """Lightning: a warning line first, then a strike that shocks the ground."""
        if x is None:
            x = self.dino_x + self.speed * 55 + random.uniform(-40, 300)
        self.add_obstacle("bolt", x, GROUND_Y, 18, 34, warn=55, active=12)

    # ------------------------------------------------------------------ UFO ---
    def update_ufo(self, v, ws):
        if self.ufo is None:
            if self.boss is not None:
                return
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

    # ----------------------------------------------------------------- boss ---
    def start_boss(self):
        n = self.bosses_beaten + 1
        name, color = BOSSES[(n - 1) % len(BOSSES)]
        worm = random.random() < 1 / 3              # 1 in 3: the sandworm instead
        if worm:
            name, color = "SANDWORM", "#c49a6c"
        hp = 3 + n
        self.boss = dict(name=name, color=color, n=n, hp=hp, maxhp=hp,
                         x=WIDTH + 120, y=95, t=0, phase="warning", warn=300,
                         attack=120, dying=0, hit=0, queue=[], since_star=0,
                         special_done=False, rage=0, worm=worm, rise=0.0)
        if worm:
            self.boss.update(x=770, y=GROUND_Y + 40)
        self.event = None
        self.banner = None
        self.beep()

    LANES = {"low": GROUND_Y - 4,     # jump over it
             "mid": GROUND_Y - 38,    # duck under it
             "high": GROUND_Y - 72}   # stay on the ground

    def add_fireball(self, b, lane):
        self.add_obstacle("fireball", b["x"] - 95, b["y"] + 14, 30, 18,
                          target_y=self.LANES[lane], lane=lane)
        self.burst(b["x"] - 85, b["y"] + 5, 10, ["#ff9f1a", "#ff5c5c"], speed=3, life=15)

    SPECIALS = {"SANDWORM": "EARTHQUAKE",
                "MECHA-PTERO": "ROCKET BARRAGE", "CACTUS KING": "CACTUS STAMPEDE",
                "STORM DRAGON": "THUNDERSTORM", "LAVA BAT": "LAVA RAIN"}

    # ---------------------------------------------------------- sandworm ---
    WORM_LANES = {"mid": GROUND_Y - 50,   # body at head height: DUCK
                  "high": GROUND_Y - 82}  # body up high: STAY ON THE GROUND

    def add_hump(self, b):
        """The worm's body breaks out of the sand as a low arch: jump over it."""
        x = b["x"] - 70
        self.add_obstacle("wormhump", x, GROUND_Y, 96, 34)
        self.burst(x + 10, GROUND_Y, 14, ["#c49a6c", "#e3c497", "#8a5a36"], speed=4,
                   life=25)

    def add_lunge(self, b, lane):
        """The worm shoots its body straight across the track at one height."""
        end = b["x"] - 25
        self.add_obstacle("wormneck", end, self.WORM_LANES[lane] + 13, 0, 26,
                          lane=lane, ly=self.WORM_LANES[lane], head=end, end=end,
                          stage="wind", t=0)
        b["neck_y"] = self.WORM_LANES[lane]

    def worm_attack(self, b):
        n = b["n"]
        if any(o["kind"] == "wormneck" for o in self.obstacles):
            b["attack"] = 15                          # never two things at once
            return
        if b["since_star"] >= 3 or random.random() < 0.3:
            self.add_star(b)
            return
        b["since_star"] += 1
        options = ["hump", "hump", "mid", "high", "mid"]
        if n >= 2:
            options += ["double", "mid"]
        if n >= 3:
            options += ["high", "double"]
        pick = random.choice(options)
        if pick == "hump":
            self.add_hump(b)
        elif pick == "double":                        # two humps in a row
            b["queue"] = [[0, "hump", None], [max(42, 55 - 3 * n), "hump", None]]
        elif any(o["kind"] == "wormhump" for o in self.obstacles):
            self.add_hump(b)                          # no lunge while humps are coming
        else:
            self.add_lunge(b, pick)
            b["attack"] = 175                         # wait until the body is back

    def add_star(self, b):
        """The boss spits out a star: grab it to shoot back."""
        if b.get("worm"):
            self.sparks.append(dict(x=b["x"] - 40, y=b["y"] + 10, vy=0.0, t=0, shot=True))
            b["since_star"] = 0
            return
        self.sparks.append(dict(x=b["x"] - 95, y=b["y"] + 10, vy=0.0, t=0, shot=True))
        b["since_star"] = 0

    def boss_attack(self, b):
        n = b["n"]
        # sometimes the boss shoots a star instead (always after 3 real attacks)
        if b.get("worm"):
            self.worm_attack(b)
            return
        if b["since_star"] >= 3 or random.random() < 0.3:
            self.add_star(b)
            return
        b["since_star"] += 1
        options = ["low", "mid", "high", "low", "mid", "high", "bomb"]
        if n >= 2:
            options += ["barrage", "minions"]
        if n >= 3:
            options += ["bolt", "barrage"]
        pick = random.choice(options)
        if pick in self.LANES:
            self.add_fireball(b, pick)
        elif pick == "barrage":                       # 3 fireballs, one per height
            lanes = ["low", "mid", "high"]
            random.shuffle(lanes)
            gap = max(55, 70 - 4 * n)                 # frames between shots
            b["queue"] = [[i * gap, "fire", lane] for i, lane in enumerate(lanes)]
        elif pick == "bomb":
            self.add_meteor(random.uniform(220, 560))
        elif pick == "minions":
            self.add_bird(WIDTH + 10, "low")
            self.add_bird(WIDTH + 10 + self.speed * 45, "mid")
        elif pick == "bolt":
            self.add_bolt()

    def start_special(self, b):
        """At half health the boss unleashes its special attack."""
        b["special_done"] = True
        name = self.SPECIALS[b["name"]]
        self.show_banner(f"SPECIAL ATTACK: {name}!", 110, "#ff3b3b")
        self.shake = max(self.shake, 15)
        self.beep()
        d = 100                                       # wind-up before it starts
        q = []
        if name == "ROCKET BARRAGE":
            for i, lane in enumerate(["low", "mid", "high", "low", "mid", "high"]):
                q.append([d + i * 58, "fire", lane])
            d += 6 * 58
        elif name == "CACTUS STAMPEDE":
            for i in range(5):
                q.append([d + i * 42, "cactus", None])
            q.append([d + 5 * 42 + 20, "fire", "mid"])
            d += 6 * 42 + 20
        elif name == "THUNDERSTORM":
            for i in range(4):
                q.append([d + i * 70, "bolt", None])
            d += 4 * 70
        elif name == "EARTHQUAKE":
            self.shake = max(self.shake, 40)
            for i in range(3):
                q.append([d + i * 48, "hump", None])
            q.append([d + 3 * 48 + 50, "lunge", "mid"])
            d += 3 * 48 + 50 + 175
            q.append([d, "hump", None])
            q.append([d + 50, "hump", None])
            q.append([d + 150, "lunge", "high"])
            d += 150 + 175
        else:                                         # LAVA RAIN
            for i in range(5):
                q.append([d + i * 48, "meteor", None])
            d += 5 * 48
        q += [[d + 40, "star", None], [d + 90, "star", None]]   # reward for surviving
        b["queue"] = q
        b["attack"] = d + 160
        b["rage"] = d + 90

    def run_queue_item(self, b, kind, arg):
        if kind == "fire":
            self.add_fireball(b, arg)
        elif kind == "cactus":
            self.add_obstacle("cactus", WIDTH + 10, GROUND_Y, 14, 32, n=1, cw=14)
        elif kind == "bolt":
            self.add_bolt()
        elif kind == "meteor":
            self.add_meteor(random.uniform(250, 560))
        elif kind == "star":
            self.add_star(b)
        elif kind == "hump":
            self.add_hump(b)
        elif kind == "lunge":
            self.add_lunge(b, arg)

    def update_boss(self, v, ws, box):
        b = self.boss
        # sparks: grab one to fire a shot at the boss
        kept = []
        for sp in self.sparks:
            sp["t"] += 1
            if sp.get("shot"):                        # fired by the boss
                sp["x"] -= v + 3
                sp["y"] += (GROUND_Y - 50 - sp["y"]) * 0.12
            else:
                sp["x"] -= v * 0.8
                if sp["y"] < GROUND_Y - 50:
                    sp["y"] += sp["vy"]
                    sp["vy"] += 0.15
                else:
                    sp["y"] = GROUND_Y - 50 + 6 * math.sin(sp["t"] * 0.15)
            if self.overlap(box, (sp["x"] - 13, sp["y"] - 13, sp["x"] + 13, sp["y"] + 13)):
                self.shots.append(dict(x=self.dino_x + 45, y=self.dino_y - 30))
                self.popup("FIRE!", self.dino_x + 50, self.dino_y - 60, "#ffd23f")
                self.burst(sp["x"], sp["y"], 12, ["#ffd23f", "#ffffff"], speed=3, life=15)
            elif sp["x"] > -20:
                kept.append(sp)
        self.sparks = kept

        shots = []
        for sh in self.shots:
            sh["x"] += 16
            if b and b["phase"] == "fight":
                sh["y"] += (b["y"] - sh["y"]) * 0.15
                if sh["x"] >= b["x"] - 40:
                    b["hp"] -= 1
                    b["hit"] = 12
                    self.shake = max(self.shake, 8)
                    self.burst(b["x"] - 30, b["y"], 25, ["#ffd23f", "#ff5c5c", "#ffffff"],
                               speed=6, life=30)
                    if b["hp"] <= 0:
                        b["phase"], b["dying"] = "dying", 100
                        b["queue"] = []
                        self.show_banner("BOSS DEFEATED!", 120, "#5cd65c")
                    elif not b["special_done"] and b["hp"] <= b["maxhp"] // 2:
                        self.start_special(b)
                    continue
            if sh["x"] < WIDTH + 20:
                shots.append(sh)
        self.shots = shots

        if b is None:
            return
        b["t"] += 1
        b["hit"] = max(0, b["hit"] - 1)
        if b["phase"] == "warning":                   # time to get ready
            b["warn"] -= 1
            if b["warn"] in (180, 120, 60):
                self.beep()
            if b["warn"] <= 0:
                if b.get("worm"):                     # the world stops, the ground shakes
                    b["phase"], b["timer"] = "rumble", 80
                    self.obstacles = []
                else:
                    b["phase"] = "enter"
        elif b["phase"] == "enter":
            b["x"] -= 3
            b["y"] = 95
            if b["x"] <= 720:
                b["phase"] = "fight"
        elif b["phase"] == "fight":
            if b.get("worm"):
                if not any(o["kind"] == "wormneck" for o in self.obstacles):
                    b["neck_y"] = None
                target = b.get("neck_y") or (118 + 22 * math.sin(b["t"] * 0.035))
                b["y"] += (target - b["y"]) * 0.12
            else:
                b["y"] = 95 + 35 * math.sin(b["t"] * 0.03)
            b["rage"] = max(0, b["rage"] - 1)
            for q in b["queue"]:                      # queued shots
                q[0] -= ws
                if q[0] <= 0:
                    self.run_queue_item(b, q[1], q[2])
            b["queue"] = [q for q in b["queue"] if q[0] > 0]
            b["attack"] -= ws
            if b["attack"] <= 0 and not b["queue"]:
                self.boss_attack(b)
                b["attack"] = max(85, 145 - 10 * b["n"]) + random.randint(0, 40)
                if b["queue"]:
                    b["attack"] += len(b["queue"]) * 60
        else:                                          # dying: explosions, then reward
            b["dying"] -= 1
            b["y"] += 2.2 if b.get("worm") else 1.5     # the worm sinks into the sand
            if b["dying"] % 6 == 0:
                self.burst(b["x"] + random.uniform(-50, 30), b["y"] + random.uniform(-20, 20),
                           12, ["#ff9f1a", "#ffd23f", "#ff5c5c", "#8a8a8a"], speed=5,
                           life=25)
                self.shake = max(self.shake, 5)
            if b["dying"] <= 0:
                n = b["n"]
                coins = (20 + 10 * n) * (2 if self.save["coinx2"] else 1)
                self.save["coins"] += coins
                self.run_coins += coins
                self.bonus += 300 * n
                gems = 1 + n // 2
                self.save["diamonds"] += gems
                self.bosses_beaten += 1
                self.save["stat_bosses"] += 1
                self.show_banner(f"VICTORY!  +{coins} coins  +{gems} diamond"
                                 f"{'s' if gems > 1 else ''}", 150, "#5cd65c")
                self.burst(WIDTH / 2, 90, 80, CONFETTI, speed=8, life=80)
                self.beep()
                self.write_save()
                self.boss = None
                self.sparks = []
                self.next_boss = max((self.score // BOSS_EVERY + 1) * BOSS_EVERY,
                                     self.score + BOSS_EVERY // 2)
                self.next_spawn = 90
                self.next_event = max(self.next_event, 500)

    # --------------------------------------------------------------- update ---
    def update_worm_entry(self, b):
        """The game stands still while the sandworm breaks out of the ground."""
        if self.dino_y < GROUND_Y or self.vel_y < 0:  # let the dino land
            self.vel_y += GRAVITY
            self.dino_y = min(GROUND_Y, self.dino_y + self.vel_y)
            if self.dino_y >= GROUND_Y:
                self.vel_y = 0.0
        b["t"] += 1
        b["timer"] -= 1
        self.shake = max(self.shake, 4 if b["phase"] == "rumble" else 7)
        if self.frame % 4 == 0:                       # sand trickles up everywhere
            self.add_particle(random.uniform(0, WIDTH), GROUND_Y, random.uniform(-1, 1),
                              random.uniform(-3, -1), 20, "#c49a6c", 3)
        if b["phase"] == "rumble":
            if b["timer"] <= 0:
                b["phase"], b["timer"] = "emerge", 130
                self.beep()
        else:
            b["rise"] = min(1.0, b["rise"] + 1 / 100)
            b["y"] = GROUND_Y + 40 - b["rise"] * (GROUND_Y + 40 - 118)
            if self.frame % 2 == 0:
                self.burst(b["x"] + random.uniform(-20, 60), GROUND_Y, 3,
                           ["#c49a6c", "#e3c497", "#8a5a36"], speed=6, life=30)
            if b["timer"] == 40:
                self.show_banner("THE SANDWORM AWAKENS!", 90, "#c49a6c")
            if b["timer"] <= 0:
                b["phase"] = "fight"
                b["attack"] = 70
        self.update_world(0.0)

    def update(self):
        self.frame += 1
        if self.boss and self.boss["phase"] in ("rumble", "emerge"):
            self.update_worm_entry(self.boss)
            return
        self.speed = min(self.speed + SPEED_GAIN, MAX_SPEED)
        ws = 0.5 if self.slowmo else 1.0             # world speed factor
        rush = 1.35 if self.event_is("SPEED RUSH") else 1.0
        v = self.speed * ws * rush
        mult = 2 if (self.boost_is("DOUBLE SCORE") or self.event_is("BONUS ZONE")
                     or self.event_is("SPEED RUSH")) else 1
        self.distance += v * 0.02 * mult
        self.slowmo = max(0, self.slowmo - 1)
        self.dj_cool = max(0, getattr(self, "dj_cool", 0) - 1)
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
        if self.boss is None and self.score >= self.next_boss:
            self.start_boss()

        # dino physics
        was_in_air = not self.on_ground()
        g = GRAVITY * (2.5 if self.ducking and was_in_air else 1.0)
        if self.boost_is("MOON JUMP") and not self.ducking:
            g *= 0.75
        if self.event_is("LOW GRAVITY") and not self.ducking:
            g *= 0.62
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
        if self.next_spawn <= 0 and self.boss is None:
            self.spawn_obstacle()
        box = self.dino_box()
        for ob in self.obstacles:
            self.move_obstacle(ob, v, ws)
            ob_box = self.obstacle_box(ob)
            if ob["kind"] == "bolt" and (ob["warn"] > 0 or ob["active"] <= 0):
                continue                                # only dangerous while striking
            if ob["kind"] == "wormneck" and ob["stage"] == "wind":
                continue                                # still winding up
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
        magnet = self.magnet_range()
        cx0, cy0 = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        kept = []
        for c in self.coins:
            c["phase"] += 0.15
            dx, dy = cx0 - c["x"], cy0 - c["y"]
            dist = math.hypot(dx, dy) or 1.0
            if magnet and dist < magnet:
                c["homing"] = True                   # once caught, never lost
            if c.get("homing"):
                c["pull"] = c.get("pull", 6.0) + 0.8   # flies to you, faster and faster
                step = min(c["pull"], dist)
                c["x"] += dx / dist * step
                c["y"] += dy / dist * step
                if self.frame % 3 == 0:
                    self.add_particle(c["x"], c["y"], 0, 0, 8, self.coin_col(), 2)
            else:
                c["x"] -= v
                if c["vy"]:                           # falling coin (coin rain)
                    c["y"] += c["vy"]
                    if c["y"] >= GROUND_Y - 15:
                        c["y"], c["vy"] = GROUND_Y - 15, 0.0
            r = 14 if c["big"] else 9
            if self.overlap(box, (c["x"] - r, c["y"] - r, c["x"] + r, c["y"] + r)):
                if c["gem"]:                          # diamond: the mine currency
                    self.save["diamonds"] += c["value"]
                    self.run_gems += c["value"]
                    self.popup(f"+{c['value']} DIAMOND", c["x"], c["y"] - 20, "#5ce1ff", 15)
                    self.burst(c["x"], c["y"], 30, ["#5ce1ff", "#ffffff", "#b3f3ff"],
                               speed=5, life=35)
                    self.write_save()
                    continue
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
        self.update_boss(v, ws, box)

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
        elif kind == "bolt":
            ob["x"] -= v
            if ob["warn"] > 0:
                ob["warn"] -= ws
                if ob["warn"] <= 0:                     # strike!
                    self.shake = max(self.shake, 10)
                    self.burst(ob["x"] + 9, GROUND_Y - 5, 20,
                               ["#fff7a8", "#ffe14d", "#ffffff"], speed=6, life=20)
            elif ob["active"] > 0:
                ob["active"] -= ws
            else:
                ob["x"] = -999
        elif kind == "fireball":
            ob["x"] -= v + 3
            ob["y"] += (ob["target_y"] - ob["y"]) * 0.14      # dive into its lane
        elif kind == "wormhump":
            ob["x"] -= v + 2
            if self.frame % 5 == 0:
                self.add_particle(ob["x"] + ob["w"], GROUND_Y, random.uniform(0, 2),
                                  random.uniform(-3, -1), 18, "#c49a6c", 3)
        elif kind == "wormneck":                        # body shoots out and back
            ob["t"] += 1
            st = ob["stage"]
            if st == "wind" and ob["t"] >= 45:
                ob["stage"], ob["t"] = "out", 0
                self.shake = max(self.shake, 6)
            elif st == "out":
                ob["head"] -= 17
                if ob["head"] <= -70:
                    ob["stage"], ob["t"] = "hold", 0
            elif st == "hold" and ob["t"] >= 14:
                ob["stage"] = "back"
            elif st == "back":
                ob["head"] += 17
                if ob["head"] >= ob["end"]:
                    ob["x"], ob["w"] = -999, 0
                    return
            ob["x"] = ob["head"]
            ob["w"] = max(0, ob["end"] - ob["head"])
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
        self.save["stat_runs"] += 1
        self.save["stat_level"] = max(self.save["stat_level"], self.level)
        self.shake = 20
        self.ducking = False
        self.boost = None
        self.burst(self.dino_x + 25, self.dino_y - 25, 40,
                   [self.col("fg"), "#ff5c5c", "#ffb84d"], speed=6, life=45)
        if self.score > self.save["high"]:
            self.save["high"] = self.score
        self.write_save()

    def magnet_range(self):
        if self.boost_is("SUPER MAGNET"):
            return 300
        return [0, 75, 110, 150][self.save["magnet"]]

    def update_world(self, v=0.0):
        """Things that keep moving, also on the menu screens."""
        self.tick += 1
        eclipse = self.event_is("ECLIPSE") or self.event_is("LIGHTNING STORM")
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

    def sync_music(self):
        if self.state == "motivation":
            want = "epic" if self.sound_on else None
        elif not self.save.get("music", 1):
            want = None
        elif self.state == "running":
            want = "game"
        else:
            want = "menu"
        if hasattr(self, "audio"):
            self.audio.play_track(want)

    def track_stats(self):
        """Counts every coin and diamond ever earned (spending doesn't count)."""
        sv = self.save
        for key, stat in (("coins", "stat_coins"), ("diamonds", "stat_diamonds")):
            last = getattr(self, "_last_" + key, sv[key])
            if sv[key] > last:
                sv[stat] += sv[key] - last
            setattr(self, "_last_" + key, sv[key])
        if self.state == "running" and not getattr(self, "paused", False):
            sv["stat_time"] += DT

    def step(self):
        self.track_stats()
        self.update_deco()
        if self.tick % 10 == 0:
            self.sync_music()
        if self.tick % 60 == 0:
            self.update_mine()
            if self.tick % 1800 == 0 and self.state != "running":
                self.write_save()
        if self.state == "running" and getattr(self, "paused", False):
            self.tick += 1                             # frozen, only the glow moves
        elif self.state == "running":
            self.update()
        elif self.state == "motivation":
            self.update_motivation()
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

    def draw_trophy(self, cx, by, s=1.0):
        """Golden cup with its base at (cx, by)."""
        cv = self.canvas
        gold, dark, shine = "#ffcc00", "#c79100", "#fff3b0"
        cv.create_rectangle(cx - 30 * s, by - 12 * s, cx + 30 * s, by, fill="#5a3a1a",
                            outline=dark)                                   # plinth
        cv.create_rectangle(cx - 20 * s, by - 20 * s, cx + 20 * s, by - 12 * s, fill=gold,
                            outline=dark)
        cv.create_rectangle(cx - 5 * s, by - 42 * s, cx + 5 * s, by - 20 * s, fill=gold,
                            outline=dark)                                   # stem
        for side in (-1, 1):                                                # handles
            cv.create_oval(cx + side * 26 * s - 12 * s, by - 88 * s, cx + side * 26 * s + 12 * s,
                           by - 60 * s, outline=gold, width=max(2, int(5 * s)))
        cv.create_polygon(cx - 30 * s, by - 95 * s, cx + 30 * s, by - 95 * s,
                          cx + 22 * s, by - 55 * s, cx, by - 42 * s, cx - 22 * s, by - 55 * s,
                          fill=gold, outline=dark, width=2)                 # cup
        cv.create_polygon(cx - 18 * s, by - 90 * s, cx - 10 * s, by - 90 * s,
                          cx - 12 * s, by - 60 * s, fill=shine, outline="")  # shine
        cv.create_text(cx, by - 72 * s, text="1", fill=dark,
                       font=("Courier", max(8, int(18 * s)), "bold"))
        for i in range(5):                                                   # sparkles
            a = self.tick * 0.05 + i * 1.26
            sx, sy = cx + 48 * s * math.cos(a), by - 70 * s + 40 * s * math.sin(a)
            if (self.tick // 6 + i) % 3:
                cv.create_line(sx - 4, sy, sx + 4, sy, fill=shine, width=2)
                cv.create_line(sx, sy - 4, sx, sy + 4, fill=shine, width=2)

    def look(self, couple=None):
        """The player's chosen hair, eyes, outfit and accessory as keyword args."""
        sv = self.save
        lk = dict(acc=sv["acc"], hair=HAIR.get(sv["hair"]), eyes=EYES.get(sv["eyes"]),
                  outfit=sv["outfit"])
        if couple if couple is not None else (sv["couple"] and sv["couple_on"]):
            lk.update(HIM)
        return lk

    def couple_on(self):
        return bool(self.save["couple"] and self.save["couple_on"])

    def draw_couple(self, x, y, s, body, bg, ducking=False, legs_up=False, dead=False,
                    look=None, partner=True):
        """Draws the player dino and, in couple mode, his girlfriend holding his hand."""
        look = look or self.look()
        if partner:
            gap = (74 if ducking else 58) * s
            her = dict(HER, outfit="outfit_none", acc="acc_none")
            her_body = mix(body, "#ff8fb8", 0.22)
            self.draw_dino_shape(x - gap, y, s, her_body, bg, ducking,
                                 not legs_up, dead, **her)
            cv = self.canvas
            if ducking:                                       # holding hands
                hx1, hy1, hx2, hy2 = x - gap + 58 * s, y - 15 * s, x + 2 * s, y - 15 * s
            else:
                hx1, hy1, hx2, hy2 = x - gap + 35 * s, y - 25 * s, x + 6 * s, y - 17 * s
            cv.create_line(hx1, hy1, hx2, hy2, fill=body, width=max(2, 4 * s))
            cv.create_oval((hx1 + hx2) / 2 - 3 * s, (hy1 + hy2) / 2 - 3 * s,
                           (hx1 + hx2) / 2 + 3 * s, (hy1 + hy2) / 2 + 3 * s,
                           fill=body, width=0)
            if not dead and (self.tick // 40) % 3 == 0:        # a little heart
                rise = (self.tick % 40) * 0.5 * s
                self.draw_heart(x - gap / 2 + 14 * s, y - 66 * s - rise, 5 * s)
        self.draw_dino_shape(x, y, s, body, bg, ducking, legs_up, dead, **look)

    def draw_heart(self, cx, cy, r, color="#ff4f7b"):
        cv = self.canvas
        cv.create_oval(cx - r, cy - r, cx, cy, fill=color, width=0)
        cv.create_oval(cx, cy - r, cx + r, cy, fill=color, width=0)
        cv.create_polygon(cx - r, cy - r / 2, cx + r, cy - r / 2, cx, cy + r,
                          fill=color, outline="")

    def draw_dino_shape(self, x, y, s, body, bg, ducking=False, legs_up=False,
                        dead=False, acc="acc_none", hair=None, eyes=None,
                        outfit="outfit_none", lashes=False, bow=False):
        """Draws the dino with its feet at (x, y), scale s, plus hair, eyes,
        outfit and an accessory."""
        cv = self.canvas

        def R(x1, y1, x2, y2, c):
            cv.create_rectangle(x + x1 * s, y + y1 * s, x + x2 * s, y + y2 * s,
                                fill=c, width=0)

        def P(points, c):
            cv.create_polygon(*[v for px, py in points for v in (x + px * s, y + py * s)],
                              fill=c, outline="")

        # where the head and the back are in this pose
        hx, hy = (20, 20) if ducking else (0, 0)       # head shift when ducking
        back_x, back_y = (2, -26) if ducking else (6, -34)

        # flag goes behind the body
        if acc in FLAGS:
            top = back_y - 34
            R(back_x - 1, top, back_x + 1, back_y, "#6b4a2b")       # pole
            waves = [2 * math.sin(self.tick * 0.25 - i * 0.9) for i in range(5)]
            for i in range(5):                                      # waving cloth
                x1, x2 = back_x + 1 + i * 5, back_x + 6 + i * 5
                for j, colr in enumerate(FLAGS[acc]):
                    R(x1, top + 1 + j * 4 + waves[i], x2, top + 5 + j * 4 + waves[i], colr)
            if acc == "acc_flag_tr":                                # crescent and star
                fx, fy = back_x + 10, top + 7 + (waves[1] + waves[2]) / 2

                def O(cx, cy, r, c):
                    cv.create_oval(x + (cx - r) * s, y + (cy - r) * s, x + (cx + r) * s,
                                   y + (cy + r) * s, fill=c, width=0)
                O(fx, fy, 3.6, "#ffffff")
                O(fx + 1.2, fy, 2.9, "#e30a17")
                pts = []
                for k in range(10):
                    a = -math.pi / 2 + k * math.pi / 5
                    rr = 1.9 if k % 2 == 0 else 0.8
                    pts.append((fx + 5.2 + rr * math.cos(a), fy + rr * math.sin(a)))
                P(pts, "#ffffff")

        wave = math.sin(self.tick * 0.3)
        if outfit == "outfit_cape":
            if ducking:
                P([(36, -26), (44, -26), (14, -16 + 2 * wave), (-8, -22 + 3 * wave)],
                  "#d62828")
            else:
                P([(18, -36), (26, -34), (4, -6 + 2 * wave), (-12, -12 + 3 * wave)],
                  "#d62828")
        if hair:
            self.draw_hair(R, P, hair, hx, hy, ducking, back=True)

        l1 = 0 if legs_up else 6
        l2 = 6 if legs_up else 0
        light = is_light(body)
        eyec = "#2b2b2b" if light else bg
        if light:                                    # dark outline around a white dino
            o = 1.4 / max(s, 0.5)
            parts = ([(0, -26, 46, -8), (40, -30, 60, -14)] if ducking else
                     [(4, -34, 30, -12), (20, -50, 44, -32), (30, -28, 36, -24),
                      (-6, -30, 6, -22)]) + [(8, -12, 13, -l1), (20, -12, 25, -l2)]
            for x1, y1, x2, y2 in parts:
                R(x1 - o, y1 - o, x2 + o, y2 + o, "#3a3a3a")
        if ducking:
            R(0, -26, 46, -8, body)
            R(40, -30, 60, -14, body)
            if dead or not eyes:
                R(50, -26, 53, -23, eyec)
            else:
                R(49, -27, 54, -22, "#ffffff")
                R(50, -26, 53, -23, eyes)
                R(51, -26, 52, -25, "#ffffff")
            if lashes:
                R(49, -29, 50, -27, "#111111")
                R(52, -29, 53, -27, "#111111")
        else:
            R(4, -34, 30, -12, body)
            R(20, -50, 44, -32, body)
            if dead:
                cv.create_line(x + 25 * s, y - 47 * s, x + 31 * s, y - 41 * s,
                               fill=eyec, width=2)
                cv.create_line(x + 31 * s, y - 47 * s, x + 25 * s, y - 41 * s,
                               fill=eyec, width=2)
            elif eyes:
                R(25, -47, 31, -41, "#ffffff")                    # eye white
                R(26, -46, 30, -42, eyes)                         # iris
                R(28, -46, 29, -45, "#ffffff")                    # sparkle
            else:
                R(26, -46, 30, -42, eyec)
            if lashes and not dead:
                R(24, -49, 25, -47, "#111111")
                R(27, -50, 28, -47, "#111111")
                R(30, -49, 31, -47, "#111111")
            R(30, -28, 36, -24, body)
            R(-6, -30, 6, -22, body)
        R(8, -12, 13, -l1, body)
        R(20, -12, 25, -l2, body)

        self.draw_outfit(R, P, outfit, ducking, wave)
        if hair:
            self.draw_hair(R, P, hair, hx, hy, ducking, back=False)
        if bow:                                               # her little bow
            P([(24 + hx, -56 + hy), (30 + hx, -53 + hy), (24 + hx, -50 + hy)], "#ff4f7b")
            P([(36 + hx, -56 + hy), (30 + hx, -53 + hy), (36 + hx, -50 + hy)], "#ff4f7b")
            R(29 + hx, -54 + hy, 31 + hx, -52 + hy, "#c9184a")
        if hair:                                              # hats sit on the hair
            hy -= 4
        # accessories on the head (head top-left is at (20, -50) + shift)
        if acc == "acc_crown":
            P([(22 + hx, -50 + hy), (42 + hx, -50 + hy), (42 + hx, -60 + hy),
               (37 + hx, -55 + hy), (32 + hx, -62 + hy), (27 + hx, -55 + hy),
               (22 + hx, -60 + hy)], "#ffcc00")
            R(30 + hx, -56 + hy, 34 + hx, -53 + hy, "#ff3b3b")
        elif acc == "acc_partyhat":
            P([(26 + hx, -50 + hy), (40 + hx, -50 + hy), (33 + hx, -68 + hy)],
              "#b366ff")
            R(29 + hx, -56 + hy, 37 + hx, -54 + hy, "#ffe14d")
            cv.create_oval(x + (31 + hx) * s, y + (-72 + hy) * s, x + (35 + hx) * s,
                           y + (-67 + hy) * s, fill="#ff5c5c", width=0)
        elif acc == "acc_shades" and not dead:
            if ducking:
                R(46, -27, 60, -22, "#111111")
            else:
                R(23, -47, 44, -42, "#111111")
                R(20, -46, 23, -45, "#111111")

    def draw_hair(self, R, P, hair, hx, hy, ducking, back):
        """Hair on a head whose top-left corner is at (20 + hx, -50 + hy)."""
        style, c = hair
        X = lambda v: v + hx
        Y = lambda v: v + hy
        bounce = 2 * math.sin(self.tick * 0.35)
        if back:                                              # parts behind the head
            if style == "long":
                if ducking:
                    P([(X(20), Y(-52)), (X(26), Y(-52)), (X(12), Y(-42)), (X(4), Y(-44))], c)
                else:
                    R(X(15), Y(-52), X(24), Y(-26), c)
                    P([(X(15), Y(-26)), (X(24), Y(-26)), (X(19), Y(-22))], c)
            elif style == "ponytail":
                R(X(16), Y(-53), X(22), Y(-47), c)
                P([(X(16), Y(-52)), (X(17), Y(-46)), (X(6), Y(-36 + bounce)),
                   (X(4), Y(-42 + bounce))], c)
            return
        if style == "quiff":
            R(X(20), Y(-53), X(40), Y(-50), c)
            P([(X(26), Y(-53)), (X(44), Y(-53)), (X(46), Y(-58)), (X(32), Y(-57))], c)
            R(X(20), Y(-50), X(23), Y(-44), c)                 # sideburn
        elif style == "long":
            R(X(18), Y(-54), X(42), Y(-50), c)
            P([(X(36), Y(-54)), (X(44), Y(-52)), (X(44), Y(-47)), (X(38), Y(-50))], c)
            R(X(18), Y(-50), X(23), Y(-36), c)
        elif style == "ponytail":
            R(X(19), Y(-54), X(42), Y(-50), c)
            R(X(15), Y(-55), X(20), Y(-50), "#ffe14d")          # hair tie
        elif style == "curly":
            for i, (cx, cy) in enumerate([(22, -52), (28, -55), (34, -55), (40, -52),
                                          (19, -47), (25, -51), (31, -52), (37, -50)]):
                P([(X(cx - 4), Y(cy)), (X(cx), Y(cy - 4)), (X(cx + 4), Y(cy)),
                   (X(cx), Y(cy + 4))], c)
        elif style == "mohawk":
            for i in range(4):
                bx = 22 + i * 5
                P([(X(bx), Y(-50)), (X(bx + 5), Y(-50)), (X(bx + 1), Y(-60 - (i % 2) * 3))], c)

    def draw_outfit(self, R, P, outfit, ducking, wave):
        if outfit == "outfit_scarf":
            if ducking:
                R(38, -18, 46, -12, "#2f6fd6")
                R(30, -18 + wave, 38, -15 + wave, "#2f6fd6")
            else:
                R(20, -35, 34, -30, "#2f6fd6")
                R(12, -35 + wave, 20, -31 + wave, "#2f6fd6")
                R(9, -33 + 2 * wave, 13, -29 + 2 * wave, "#ffffff")
        elif outfit == "outfit_bowtie":
            bx, by = (46, -14) if ducking else (32, -31)
            P([(bx - 5, by - 3), (bx, by), (bx - 5, by + 3)], "#d62828")
            P([(bx + 5, by - 3), (bx, by), (bx + 5, by + 3)], "#d62828")
            R(bx - 1, by - 1, bx + 1, by + 1, "#7a0c0c")
        elif outfit == "outfit_suit":
            if ducking:
                R(30, -20, 46, -12, "#ffffff")
                R(30, -17, 44, -15, "#1d3557")
            else:
                P([(20, -32), (30, -32), (30, -16), (25, -14)], "#ffffff")
                P([(26, -31), (29, -31), (28, -18), (27, -17), (25, -18)], "#1d3557")
        elif outfit == "outfit_tutu":
            ty = -10 if ducking else -14
            x1, x2 = (0, 46) if ducking else (2, 32)
            pts = [(x1, ty - 4)]
            for k in range(int((x2 - x1) / 4) + 1):
                pts.append((x1 + 4 * k, ty + (4 if k % 2 else 1)))
            pts.append((x2, ty - 4))
            P(pts, "#ff8fc8")

    def draw_dino(self, ox, oy, fg, bg):
        x, y = self.dino_x + ox, self.dino_y + oy
        body = SKIN_COLOR.get(self.save["skin"]) or fg
        if self.boost_is("STAR POWER"):
            body = CONFETTI[(self.frame // 4) % len(CONFETTI)]
        if self.invuln and (self.invuln // 4) % 2:
            return                                    # blink after a shield hit
        s = 0.55 if self.boost_is("TINY DINO") else 1.0
        running = self.state == "running"
        legs_up = (self.frame // 5) % 2 == 0 and self.on_ground() and running
        self.draw_couple(x, y, s, body, bg, self.ducking, legs_up,
                         self.state == "over", partner=self.couple_on())
        if self.save["shield"] > 0 and running:
            self.canvas.create_oval(x - 10 * s, y - 62 * s, x + 62 * s, y + 6 * s,
                                    outline="#4db8ff", width=2)
        rng = self.magnet_range()
        if rng and running and (self.frame // 30) % 2 == 0:      # magnet field pulse
            cx, cy = x + 25 * s, y - 22 * s
            r = 30 + (self.frame % 30)
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    outline=mix(self.col("bg"), "#ff5c5c", 0.35))

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
        elif kind == "wormhump":
            for i in range(8):                          # arched body out of the sand
                a = math.pi * (i + 0.5) / 8
                sx = x + w / 2 - (w / 2 - 10) * math.cos(a)
                sy = GROUND_Y + oy + 4 - (h - 8) * math.sin(a)
                self.worm_segment(sx, sy, 12, i)
            cv.create_oval(x - 6, y - 5, x + 20, y + 4, fill="#e3c497", width=0)
            cv.create_oval(x + w - 20, y - 5, x + w + 6, y + 4, fill="#e3c497", width=0)
        elif kind == "wormneck":
            ly = ob["ly"] + oy
            if ob["stage"] == "wind":                   # telegraph the height
                on = (ob["t"] // 6) % 2 == 0
                hint = "DUCK!" if ob["lane"] == "mid" else "STAY DOWN!"
                cv.create_text(WIDTH / 2, ly, text=f"<<<  {hint}  <<<",
                               fill="#ff3b3b" if on else "#ff9f9f",
                               font=("Courier", 14, "bold"))
            else:
                head = ob["head"] + ox
                k = 0
                xx = ob["end"] + ox
                while xx > head + 14:                   # the long body
                    self.worm_segment(xx, ly + 2 * math.sin(xx * 0.05), 13, k)
                    xx -= 20
                    k += 1
                self.worm_head(head, ly, 17, -1)
        elif kind == "fireball":
            cv.create_oval(x + 14, y - h + 3, x + w + 14, y - 3, fill="#ff9f1a", width=0)
            cv.create_oval(x + 26, y - h + 6, x + w + 22, y - 6, fill="#ff5c5c", width=0)
            cv.create_oval(x, y - h, x + 20, y, fill="#ffd23f", outline="#ff5c5c", width=2)
        elif kind == "bolt":
            if ob["warn"] > 0:                         # blinking warning line
                if (int(ob["warn"]) // 5) % 2:
                    cv.create_line(x + 9, 0, x + 9, GROUND_Y, fill="#ffe14d", dash=(6, 6),
                                   width=2)
                cv.create_text(x + 9, GROUND_Y - 50, text="!", fill="#ffe14d",
                               font=("Courier", 18, "bold"))
            elif ob["active"] > 0:                     # the strike itself
                pts = []
                yy, xx = 0, x + 9
                while yy < GROUND_Y:
                    pts += [xx, yy]
                    yy += 25
                    xx = x + 9 + random.uniform(-10, 10)
                pts += [x + 9, GROUND_Y]
                cv.create_line(*pts, fill="#fff7a8", width=5)
                cv.create_line(*pts, fill="#ffffff", width=2)
                cv.create_oval(x - 14, GROUND_Y - 34, x + 32, GROUND_Y + 4,
                               outline="#ffe14d", width=3)
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

    def worm_colors(self, flash=False):
        if flash:
            return "#ffffff", "#c9c9c9"
        b = self.boss
        if b and b.get("rage") and (b["rage"] // 6) % 2:
            return "#ff6b4a", "#a83218"
        return "#c49a6c", "#8a5a36"

    def worm_segment(self, x, y, r, i):
        b = self.boss
        body, ring = self.worm_colors(bool(b and b["hit"] % 4 >= 2))
        cv = self.canvas
        cv.create_oval(x - r, y - r, x + r, y + r, fill=body, outline=ring, width=2)
        if i % 2 == 0:
            cv.create_line(x - r * 0.5, y - r * 0.8, x - r * 0.5, y + r * 0.8, fill=ring,
                           width=2)

    def worm_head(self, x, y, r, face):
        """Round head with a ring of teeth; face = -1 looks left."""
        cv = self.canvas
        b = self.boss
        body, ring = self.worm_colors(bool(b and b["hit"] % 4 >= 2))
        cv.create_oval(x - r, y - r, x + r, y + r, fill=body, outline=ring, width=2)
        mx = x + face * r * 0.5
        cv.create_oval(mx - r * 0.5, y - r * 0.65, mx + r * 0.5, y + r * 0.65,
                       fill="#3a1f12", width=0)
        t = self.frame * 0.1
        for k in range(6):
            a = k * math.pi / 3 + t
            tx, ty = mx + r * 0.45 * math.cos(a), y + r * 0.6 * math.sin(a)
            cv.create_polygon(tx, ty, tx + (mx - tx) * 0.5 - 2, ty + (y - ty) * 0.5,
                              tx + (mx - tx) * 0.5 + 2, ty + (y - ty) * 0.5,
                              fill="#f4ecd8", outline="")
        cv.create_oval(x - face * r * 0.1 - 3, y - r * 0.9, x - face * r * 0.1 + 3,
                       y - r * 0.9 + 6, fill="#ff2a2a", width=0)          # little eye

    def draw_worm_boss(self, b, fg):
        """The big worm: a curved column of body rising out of the sand."""
        cv = self.canvas
        hx, hy = b["x"], b["y"]
        bx, by = b["x"] + 55, GROUND_Y + 30              # where it comes out
        neck = any(o["kind"] == "wormneck" and o["stage"] != "wind"
                   for o in self.obstacles)
        pts = []
        for i in range(14):                               # quadratic curve base -> head
            t = i / 13
            cx, cy = b["x"] + 95, (hy + GROUND_Y) / 2
            x = (1 - t) ** 2 * bx + 2 * (1 - t) * t * cx + t * t * hx
            y = (1 - t) ** 2 * by + 2 * (1 - t) * t * cy + t * t * hy
            x += 4 * math.sin(self.frame * 0.08 + i * 0.6) * t
            pts.append((x, y, 22 - 6 * t))
        for i, (x, y, r) in enumerate(pts):
            if y - r * 0.3 < GROUND_Y:
                self.worm_segment(x, y, r, i)
        if not neck and hy < GROUND_Y + 5:
            self.worm_head(hx, hy, 20, -1)
        # hide what is still under the ground, then a sand mound around the base
        cv.create_rectangle(bx - 70, GROUND_Y + 1, bx + 60, HEIGHT, fill=self.col("bg"),
                            width=0)
        cv.create_line(bx - 70, GROUND_Y, bx + 60, GROUND_Y, fill=fg, width=2)
        cv.create_oval(bx - 55, GROUND_Y - 12, bx + 45, GROUND_Y + 10, fill="#e3c497",
                       width=0)
        cv.create_oval(bx - 30, GROUND_Y - 18, bx + 20, GROUND_Y + 2, fill="#d9b483",
                       width=0)

    def draw_boss(self, fg):
        cv = self.canvas
        for sp in self.sparks:                          # grab these to shoot
            x, y = sp["x"], sp["y"]
            pulse = math.sin(self.frame * 0.25)
            for rr, c in ((34 + 4 * pulse, "#fff3b0"), (26 + 3 * pulse, "#ffe066")):
                cv.create_oval(x - rr, y - rr, x + rr, y + rr, outline=c, width=3)
            r = 20 + 3 * pulse
            rot = self.frame * 0.06
            pts = []
            for i in range(10):
                a = -math.pi / 2 + i * math.pi / 5 + rot
                rr = r if i % 2 == 0 else r * 0.45
                pts += [x + rr * math.cos(a), y + rr * math.sin(a)]
            cv.create_polygon(*pts, fill="#ffd23f", outline="#ffffff", width=3)
            cv.create_text(x, y - 46, text="GRAB!", fill="#ffe14d",
                           font=("Courier", 12, "bold"))
            cv.create_polygon(x - 6, y - 37, x + 6, y - 37, x, y - 30, fill="#ffe14d")
            if self.frame % 3 == 0:
                self.add_particle(x + random.uniform(-20, 20), y + random.uniform(-20, 20),
                                  0, -0.5, 12, "#fff3b0", 3)
        for sh in self.shots:
            cv.create_oval(sh["x"] - 8, sh["y"] - 5, sh["x"] + 8, sh["y"] + 5,
                           fill="#ffe14d", outline="#ff9f1a", width=2)
            cv.create_line(sh["x"] - 30, sh["y"], sh["x"] - 8, sh["y"],
                           fill="#ffe14d", width=3)
        b = self.boss
        if not b:
            return
        if b["phase"] == "warning":                   # get-ready screen
            on = (b["warn"] // 15) % 2 == 0
            if on:
                cv.create_rectangle(3, 3, WIDTH - 3, HEIGHT - 3, outline="#ff3b3b", width=6)
            cv.create_text(WIDTH / 2, 75, text="!! WARNING !!",
                           fill="#ff3b3b" if on else "#ff9f9f", font=("Courier", 26, "bold"))
            cv.create_text(WIDTH / 2, 108, text=f"BOSS APPROACHING: {b['name']}",
                           fill="#ff3b3b", font=("Courier", 15, "bold"))
            secs = math.ceil(b["warn"] / 60)
            cv.create_text(WIDTH / 2, 140, text=str(secs), fill=fg,
                           font=("Courier", 28, "bold"))
            cv.create_text(WIDTH / 2, 172, fill=fg, font=("Courier", 11),
                           text=("humps: JUMP   body in the middle: DUCK   body up high: "
                                 "STAY DOWN   grab the stars" if b.get("worm") else
                                 "low fireball: JUMP   middle: DUCK   high: STAY DOWN   "
                                 "grab the stars to shoot back"))
            return
        if b["phase"] in ("rumble", "emerge"):        # the worm breaks out
            if b["phase"] == "emerge":
                self.draw_worm_boss(b, fg)
            on = (b["t"] // 10) % 2 == 0
            cv.create_text(WIDTH / 2, 80, text="THE GROUND IS SHAKING..." if
                           b["phase"] == "rumble" else "S A N D W O R M",
                           fill="#c49a6c" if on else "#8a5a36",
                           font=("Courier", 22, "bold"))
            return
        if b.get("worm"):
            if b["hp"] > 0 or b["phase"] == "dying":
                self.draw_worm_boss(b, fg)
            self.draw_boss_bar(b, fg)
            return
        x, y = b["x"], b["y"]
        body = "#ffffff" if b["hit"] % 4 >= 2 else b["color"]
        if b.get("rage") and (b["rage"] // 6) % 2:
            body = "#ff3b3b"
        flap = 22 * math.sin(self.frame * 0.18)
        dark = mix(b["color"], "#000000", 0.35)
        cv.create_polygon(x - 10, y - 5, x + 40, y - 5, x + 70, y - 40 - flap,
                          x + 15, y - 20 - flap / 2, fill=dark, outline=fg)   # back wing
        cv.create_oval(x - 45, y - 22, x + 55, y + 22, fill=body, outline=fg, width=2)
        cv.create_polygon(x + 50, y - 8, x + 85, y - 18, x + 80, y + 12,
                          fill=body, outline=fg)                              # tail
        cv.create_oval(x - 70, y - 26, x - 30, y + 6, fill=body, outline=fg, width=2)
        cv.create_polygon(x - 68, y - 12, x - 105, y - 2, x - 66, y + 2,
                          fill="#ffb84d", outline=fg)                         # beak
        cv.create_oval(x - 58, y - 18, x - 48, y - 8, fill="#ff2a2a", width=0)  # eye
        cv.create_polygon(x - 10, y, x + 40, y, x + 60, y + 35 + flap,
                          x + 5, y + 18 + flap / 2, fill=dark, outline=fg)    # front wing
        if b["phase"] == "dying" and (b["dying"] // 4) % 2:
            cv.create_oval(x - 60, y - 40, x + 60, y + 40, outline="#ff9f1a", width=3)
        self.draw_boss_bar(b, fg)

    def draw_boss_bar(self, b, fg):
        cv = self.canvas
        bw = 300
        bx = WIDTH / 2 - bw / 2
        cv.create_text(WIDTH / 2, 108, text=f"BOSS: {b['name']}  (grab the stars to shoot!)",
                       fill="#ff3b3b", font=("Courier", 11, "bold"))
        cv.create_rectangle(bx, 118, bx + bw, 128, outline=fg, width=1)
        cv.create_rectangle(bx, 118, bx + bw * max(b["hp"], 0) / b["maxhp"], 128,
                            fill="#ff3b3b", width=0)

    def draw(self):
        self.draw_scene()
        self.draw_frame()

    # ------------------------------------------- fullscreen decoration ---
    # Pure decoration in the empty bars above and below the game (fullscreen):
    # drifting clouds with seagulls flying through them on top, and now and
    # then a sandworm swimming past at the bottom. None of it touches the game.
    def update_deco(self):
        d = getattr(self, "deco", None)
        if d is None:
            rnd = random.Random(3)
            d = self.deco = {
                "clouds": [[rnd.random(), rnd.uniform(0.2, 0.75), rnd.uniform(0.7, 1.4),
                            rnd.uniform(0.00008, 0.0002)] for _ in range(9)],
                "gulls": [], "next_gull": 240, "worm": None,
                "next_worm": random.randint(1500, 3000), "sand": []}
        for c in d["clouds"]:
            c[0] -= c[3]
            if c[0] < -0.12:
                c[0] = 1.12
        d["next_gull"] -= 1
        if d["next_gull"] <= 0:
            d["next_gull"] = random.randint(420, 1100)        # every 7-18 s
            go_left = random.random() < 0.5
            y = random.uniform(0.25, 0.7)
            speed = random.uniform(0.0011, 0.0019)
            for i in range(random.choice([1, 1, 2, 3, 4])):  # alone or a little flock
                d["gulls"].append(dict(
                    x=(1.08 + 0.035 * i) if go_left else (-0.08 - 0.035 * i),
                    y=y + random.uniform(-0.12, 0.12) + (0.06 * i if i % 2 else -0.04 * i),
                    v=(-speed if go_left else speed) * random.uniform(0.93, 1.07),
                    phase=random.uniform(0, 6), size=random.uniform(0.8, 1.15)))
        for gl in d["gulls"]:
            gl["x"] += gl["v"]
            gl["phase"] += 0.16
            gl["y"] += 0.0015 * math.sin(gl["phase"] * 0.15)
        d["gulls"] = [gl for gl in d["gulls"] if -0.2 < gl["x"] < 1.2]
        w = d["worm"]
        if w is None:
            d["next_worm"] -= 1
            if d["next_worm"] <= 0:                          # rare: every 40-100 s
                d["next_worm"] = random.randint(2400, 6000)
                right = random.random() < 0.5
                d["worm"] = dict(p=-0.05 if right else 1.05, dir=1 if right else -1,
                                 t=0.0, speed=random.uniform(0.0028, 0.0036), tail=0.4)
        else:
            w["p"] += w["dir"] * w["speed"]
            w["t"] += 0.07
            # gone once the tail has left the screen as well
            if (w["dir"] > 0 and w["p"] > 1.05 + w["tail"]) or \
                    (w["dir"] < 0 and w["p"] < -0.05 - w["tail"]):
                d["worm"] = None
        for g_ in d["sand"]:
            g_[0] += g_[2]
            g_[1] += g_[3]
            g_[3] += 0.00022
            g_[4] -= 1
        d["sand"] = [g_ for g_ in d["sand"] if g_[4] > 0]

    def bars_visible(self):
        sc = self.canvas
        return isinstance(sc, ScaledCanvas) and sc.oy >= 50

    def draw_frame(self):
        sc = self.canvas
        if not self.bars_visible():
            return
        self.draw_frame_deco()
        if self.state == "running":                  # boost / slow-mo border, whole screen
            cv, f = sc.cv, sc.f
            W, H = WIDTH * f + 2 * sc.ox, HEIGHT * f + 2 * sc.oy
            if self.slowmo:
                cv.create_rectangle(3 * f, 3 * f, W - 3 * f, H - 3 * f,
                                    outline="#4db8ff", width=6 * f)
            if self.boost:
                cv.create_rectangle(2 * f, 2 * f, W - 2 * f, H - 2 * f,
                                    outline=self.boost[2], width=4 * f)

    def draw_frame_deco(self):
        sc = self.canvas
        d = getattr(self, "deco", None)
        if d is None:
            return
        cv, f, bar = sc.cv, sc.f, sc.oy
        W = WIDTH * f + 2 * sc.ox
        bg = self.col("bg")
        bot = bar + HEIGHT * f
        cv.create_rectangle(0, 0, W, bar, fill=bg, width=0)           # hide anything
        cv.create_rectangle(0, bot, W, bot + bar, fill=bg, width=0)   # poking out
        cloud = self.col("cloud")

        def draw_cloud(c):
            cx, cy, k = c[0] * W, c[1] * bar, c[2] * f
            for dx, dy, r in ((-22, 4, 14), (0, -4, 20), (22, 4, 15), (8, 8, 14)):
                cv.create_oval(cx + (dx - r) * k, cy + (dy - r) * k, cx + (dx + r) * k,
                               cy + (dy + r) * k, fill=cloud, width=0)

        for c in d["clouds"][::2]:                                    # clouds behind
            draw_cloud(c)
        gull = mix(bg, self.col("fg"), 0.85)
        for gl in d["gulls"]:                                         # seagulls
            x, y, k = gl["x"] * W, gl["y"] * bar, 7 * f * gl["size"]
            flap = math.sin(gl["phase"])
            cv.create_line(x - 2 * k, y - 0.3 * k + flap * 0.4 * k,
                           x - 1 * k, y - 0.9 * k - flap * 0.5 * k, x, y,
                           x + 1 * k, y - 0.9 * k - flap * 0.5 * k,
                           x + 2 * k, y - 0.3 * k + flap * 0.4 * k,
                           fill=gull, width=max(2, 0.35 * k), smooth=True,
                           capstyle="round")
        for c in d["clouds"][1::2]:                                   # clouds in front
            draw_cloud(c)

        w = d["worm"]
        if w:                                                         # the sandworm
            # big, almost straight, and always fully visible: it slides along
            # the sand from one edge of the screen to the other
            surface = bot + bar * 0.86
            r0 = bar * 0.24
            seg = r0 * 1.05
            n = 20
            body, ring = "#c49a6c", "#8a5a36"
            if self.night_t > 0.5:
                body, ring = "#8f6f4f", "#5e3d22"
            dots = mix(bg, self.col("fg"), 0.35)
            for k in range(int(W // (14 * f)) + 1):                   # sand surface
                x = k * 14 * f + (k % 3) * 3 * f
                jy = surface + (k % 2) * 2 * f + random.uniform(-1.5, 1.5) * f   # rumble
                cv.create_line(x, jy, x + 4 * f, jy, fill=dots, width=max(1, f * 0.8))
            pts = []
            w["tail"] = n * seg / W + 0.03
            for i in range(n):
                x = w["p"] * W - w["dir"] * i * seg
                r = r0 * (1.0 - 0.025 * i)
                y = surface - r - bar * 0.025 * (1 + math.sin(w["t"] * 1.5 - i * 0.5))
                pts.append((x, y, r))
            for i in range(n - 1, -1, -1):
                x, y, r = pts[i]
                cv.create_oval(x - r, y - r, x + r, y + r, fill=body, outline=ring,
                               width=max(1, r * 0.14))
                if i and i % 2 == 0:
                    cv.create_line(x - r * 0.6, y - r * 0.75, x - r * 0.6, y + r * 0.75,
                                   fill=ring, width=max(1, r * 0.12))
            hx, hy, hr = pts[0]                                       # head and teeth
            mx = hx + w["dir"] * hr * 0.55
            cv.create_oval(mx - hr * 0.45, hy - hr * 0.6, mx + hr * 0.45, hy + hr * 0.6,
                           fill="#3a1f12", width=0)
            for k in range(5):
                a = k * 2 * math.pi / 5 + w["t"]
                tx, ty = mx + hr * 0.42 * math.cos(a), hy + hr * 0.55 * math.sin(a)
                cv.create_polygon(tx, ty, tx + (mx - tx) * 0.45 - hr * 0.08,
                                  ty + (hy - ty) * 0.45, tx + (mx - tx) * 0.45 + hr * 0.08,
                                  ty + (hy - ty) * 0.45, fill="#f4ecd8", outline="")
            for i in (0, n // 2, n - 1):                              # sand kicked up
                if random.random() < 0.35:
                    d["sand"].append([pts[i][0] / W, surface / max(bot + bar, 1),
                                      random.uniform(-0.0009, 0.0009),
                                      random.uniform(-0.004, -0.0018), 32])
        H = bot + bar
        for g_ in d["sand"]:
            x, y = g_[0] * W, g_[1] * H
            r = max(1.5, f * 1.6)
            cv.create_rectangle(x - r, y - r, x + r, y + r, fill="#c49a6c", width=0)

    def draw_scene(self):
        cv = self.canvas
        cv.delete("all")
        bg, fg = self.col("bg"), self.col("fg")
        cv.configure(bg=bg)
        cv.create_rectangle(0, 0, WIDTH, HEIGHT, fill=bg, width=0)
        ox = random.randint(-5, 5) if self.shake else 0
        oy = random.randint(-4, 4) if self.shake else 0
        deco = getattr(self, "deco", None)
        if deco and deco["worm"] and self.bars_visible():   # the sandworm rumbles
            ox += random.choice((-1, 0, 1))                 # the ground a little
            oy += random.choice((-1, 0, 0, 1))

        if self.state == "shop":
            self.draw_shop(bg, fg)
            return
        if self.state == "motivation":
            self.draw_motivation()
            return
        if self.state == "mine":
            self.draw_mine(bg, fg)
            return

        self.draw_background(bg, fg)
        if not self.bars_visible():
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
            if c["gem"]:
                gx, gy = c["x"] + ox, c["y"] + oy
                cv.create_polygon(gx - 14, gy - 4, gx - 7, gy - 13, gx + 7, gy - 13,
                                  gx + 14, gy - 4, gx, gy + 14, fill="#5ce1ff",
                                  outline="#ffffff", width=2)
                continue
            R = 14 if c["big"] else 8
            r = R * abs(math.cos(c["phase"])) + 2
            cv.create_oval(c["x"] - r + ox, c["y"] - R + oy, c["x"] + r + ox,
                           c["y"] + R + oy, fill=coin_col, outline=fg,
                           width=2 if c["big"] else 1)
        for ob in self.obstacles:
            self.draw_obstacle(ob, ox, oy, fg)
        self.draw_ufo(fg)
        self.draw_boss(fg)
        self.draw_dino(ox, oy, fg, bg)

        for p in self.particles:
            s = p["size"]
            cv.create_rectangle(p["x"], p["y"], p["x"] + s, p["y"] + s,
                                fill=p["color"] or fg, width=0)
        for t in self.popups:
            cv.create_text(t["x"], t["y"], text=t["text"], fill=t["color"] or fg,
                           font=("Courier", t["size"], "bold"))
        self.draw_hud(fg)
        if self.state == "running" and getattr(self, "paused", False):
            self.draw_pause(fg)

    def draw_pause(self, fg):
        cv = self.canvas
        bg = self.col("bg")
        cv.create_rectangle(WIDTH / 2 - 230, 70, WIDTH / 2 + 230, 225,
                            fill=mix(bg, fg, 0.12), outline=fg, width=2)
        cv.create_text(WIDTH / 2, 100, text="P A U S E D", fill=fg,
                       font=("Courier", 26, "bold"))
        cv.create_text(WIDTH / 2, 140, fill=fg, font=("Courier", 12, "bold"),
                       text=f"score {int(self.score)}    level {self.level}    "
                            f"+{self.run_coins} coins")
        cv.create_text(WIDTH / 2, 175, fill=fg, font=("Courier", 12),
                       text="P / Space / click the button: resume")
        cv.create_text(WIDTH / 2, 198, fill=fg, font=("Courier", 12),
                       text="M / Esc: quit to menu")

    def draw_hud(self, fg):
        cv = self.canvas
        cv.create_text(WIDTH - 20, 18, anchor="ne", fill=fg,
                       font=("Courier", 16, "bold"),
                       text=f"HI {self.save['high']:05d}  {self.score:05d}")
        cv.create_text(WIDTH - 20, 42, anchor="ne", fill=self.coin_col(),
                       font=("Courier", 13, "bold"),
                       text=f"coins {self.save['coins']}   diamonds {self.save['diamonds']}")
        if self.state == "running":
            x1, y1, x2, y2 = self.PAUSE_BTN                      # pause button
            cv.create_rectangle(x1, y1, x2, y2, outline=fg, width=2,
                                fill=mix(self.col("bg"), fg, 0.08))
            if getattr(self, "paused", False):
                cv.create_polygon(x1 + 10, y1 + 7, x1 + 10, y2 - 7, x2 - 8, (y1 + y2) / 2,
                                  fill=fg, outline="")
            else:
                cv.create_rectangle(x1 + 9, y1 + 7, x1 + 13, y2 - 7, fill=fg, width=0)
                cv.create_rectangle(x2 - 13, y1 + 7, x2 - 9, y2 - 7, fill=fg, width=0)
            cv.create_text(x2 + 6, (y1 + y2) / 2, anchor="w", fill=mix(self.col("bg"), fg, 0.5),
                           font=("Courier", 9), text="P")
            info = f"LVL {self.level}"
            if self.combo >= 5:
                info += f"   combo {self.combo}"
            if self.save["shield"]:
                info += f"   shield x{self.save['shield']}"
            if self.save["slowmo"]:
                info += f"   slow-mo x{self.save['slowmo']} [X]"
            if self.save["doublejump"]:
                cool = getattr(self, "dj_cool", 0)
                info += "   2x jump " + ("ready" if cool <= 0 else f"{cool / 60:.1f}s")
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
            cv.create_text(WIDTH / 2, 272 if self.state == "menu" else 90, text=text,
                           fill=color, font=("Courier", 16 if self.state == "menu" else 20,
                                             "bold"))

        mid = HEIGHT / 2
        land = LANDS[self.save["land"]]["name"]
        if self.state == "menu":
            cv.create_text(WIDTH / 2 + 3, 58, text="D I N O   R U N N E R",
                           fill=mix(self.col("bg"), fg, 0.3), font=("Courier", 30, "bold"))
            cv.create_text(WIDTH / 2, 55, text="D I N O   R U N N E R", fill=fg,
                           font=("Courier", 30, "bold"))
            for i, item in enumerate(self.MENU):
                y = 84 + i * 19
                sel = i == self.menu_index
                if sel:
                    cv.create_rectangle(WIDTH / 2 - 170, y - 9, WIDTH / 2 + 170, y + 9,
                                        fill=mix(self.col("bg"), "#4db8ff", 0.3), width=0)
                color = "#ff9f1a" if item == "MOTIVATION ROOM" else fg
                if item == "FULLSCREEN":
                    item = "FULLSCREEN: " + ("ON" if getattr(self, "fullscreen", False)
                                             else "OFF") + "  (F11)"
                if item == "MUSIC":
                    item = "MUSIC: " + ("ON" if self.save.get("music", 1) else "OFF")
                cv.create_text(WIDTH / 2, y, text=(f">  {item}  <" if sel else item),
                               fill=color, font=("Courier", 13, "bold"))
            cv.create_text(WIDTH - 10, HEIGHT - 8, anchor="e", fill=fg,
                           font=("Courier", 9), text=VERSION)
            if self.save["trophy"]:
                self.draw_trophy(WIDTH - 130, 215, 1.0)
                cv.create_text(WIDTH - 130, 232, text="LEGEND", fill="#c79100",
                               font=("Courier", 12, "bold"))
            cv.create_text(WIDTH / 2, 240, fill=fg, font=("Courier", 10),
                           text="Up/Down + Enter   in game: Space jump, Down duck/dive, "
                                f"X slow-mo   F11 fullscreen   world: {land}")
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
                               text="SPACE: play again     B: shop     M: menu")

    def draw_mine(self, bg, fg):
        cv = self.canvas
        sv = self.save
        # left: the menu
        cv.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#2b1d14", width=0)
        cv.create_text(230, 22, text="T H E   D I N O   M I N E", fill="#ffd27a",
                       font=("Courier", 17, "bold"))
        cv.create_text(230, 46, fill="#ffd27a", font=("Courier", 12, "bold"),
                       text=f"coins {sv['coins']}     diamonds {sv['diamonds']}")
        store, cap = sv["mine_store"], self.mine_cap()
        info = {
            "COLLECT COINS": f"{int(store)} coins dug",
            "HIRE MINER": f"{sv['miners']}/8 miners",
            "BETTER PICKAXE": f"level {sv['pickaxe']}/5",
            "BIGGER CART": f"holds {cap} offline",
            "BACK": "",
        }
        for i, item in enumerate(self.MINE_MENU):
            y = 82 + i * 30
            if i == self.mine_index:
                cv.create_rectangle(20, y - 12, 445, y + 12, fill="#4a3424", width=0)
            cv.create_text(32, y, anchor="w", fill="#ffffff", font=("Courier", 12, "bold"),
                           text=item)
            cv.create_text(300, y, anchor="e", fill="#d9c3a5", font=("Courier", 10),
                           text=info[item])
            cost = self.mine_cost(item)
            if item in ("HIRE MINER", "BETTER PICKAXE", "BIGGER CART"):
                cv.create_text(435, y, anchor="e", fill="#5ce1ff", font=("Courier", 11, "bold"),
                               text="MAX" if cost is None else f"{cost} diamond"
                                                                 f"{'s' if cost > 1 else ''}")
        rate = self.mine_rate()
        cv.create_text(230, 240, fill="#ffd27a", font=("Courier", 11),
                       text=f"{rate:.0f} coins/min while you play  -  "
                            f"only {cap} while you're away")
        cv.create_text(230, 262, fill="#ff9f9f", font=("Courier", 11, "bold"),
                       text=self.message)
        cv.create_text(WIDTH / 2, HEIGHT - 9, fill="#d9c3a5", font=("Courier", 9),
                       text="Up/Down + Enter   C: collect   Esc: back      "
                            "Diamonds: catch them in runs, beat bosses")

        # right: the tunnel with the miners at work
        x0, y0, x1, y1 = 465, 60, 890, 255
        cv.create_rectangle(x0, y0, x1, y1, fill="#1a110b", outline="#6b4a2b", width=3)
        for wx in range(x0 + 20, x1, 140):                     # wooden supports
            cv.create_rectangle(wx, y0, wx + 10, y1, fill="#6b4a2b", width=0)
        cv.create_rectangle(x0, y0, x1, y0 + 10, fill="#6b4a2b", width=0)
        rnd = random.Random(3)                                 # rock wall with ore
        for _ in range(28):
            rx, ry = rnd.uniform(x0 + 10, x1 - 20), rnd.uniform(y0 + 15, y1 - 60)
            on = (self.tick // 10 + int(rx)) % 9 == 0
            cv.create_oval(rx, ry, rx + 6, ry + 6,
                           fill="#ffffff" if on else rnd.choice(["#e6a700", "#5ce1ff",
                                                                 "#8a7560"]), width=0)
        ground = y1 - 18
        cv.create_line(x0, ground, x1, ground, fill="#8a7560", width=3)
        for i in range(sv["miners"]):                          # the miners
            mx = x0 + 25 + (i % 4) * 75
            my = ground if i < 4 else ground - 70
            if i >= 4:
                cv.create_line(mx - 15, my, mx + 60, my, fill="#6b4a2b", width=4)
            self.draw_dino_shape(mx, my, 0.75, "#3fae49" if i % 2 else "#535353",
                                 "#1a110b", legs_up=False)
            cv.create_arc(mx + 12, my - 46, mx + 36, my - 30, start=0, extent=180,
                          fill="#ffcc00", outline="")          # helmet
            cv.create_oval(mx + 33, my - 42, mx + 37, my - 38, fill="#fff7a8", width=0)
            a = math.sin(self.tick * 0.2 + i * 1.3)            # swinging pickaxe
            hx, hy = mx + 28, my - 18
            tx, ty = hx + 22 * math.cos(-0.6 + a), hy + 22 * math.sin(-0.6 + a)
            cv.create_line(hx, hy, tx, ty, fill="#a07a50", width=3)
            cv.create_line(tx - 6, ty - 4, tx + 6, ty + 4, fill="#c0c0c0", width=3)
            if a > 0.95 and self.tick % 4 == 0:
                self.add_particle(tx, ty, random.uniform(-1, 1), -1, 10, "#ffcc00", 2)
        # the cart, filling up
        cx = x1 - 95
        fill = min(1.0, store / cap)
        cv.create_polygon(cx, ground - 40, cx + 75, ground - 40, cx + 68, ground - 8,
                          cx + 7, ground - 8, fill="#7a7a7a", outline="#cccccc")
        pile = 32 * fill
        if pile > 1:
            cv.create_oval(cx + 6, ground - 40 - pile * 0.6, cx + 69, ground - 40 + pile * 0.4,
                           fill="#e6a700", outline="#7a5600")
        for wx in (cx + 15, cx + 55):
            cv.create_oval(wx - 7, ground - 12, wx + 7, ground + 2, fill="#333333",
                           outline="#cccccc")
        cv.create_text(cx + 37, ground - 52 - pile * 0.6, text=f"{int(store)}",
                       fill="#ffd27a", font=("Courier", 10, "bold"))
        for p in self.particles:
            s = p["size"]
            cv.create_rectangle(p["x"], p["y"], p["x"] + s, p["y"] + s,
                                fill=p["color"] or "#ffffff", width=0)

    def draw_motivation(self):
        cv = self.canvas
        top, midc, low = "#0b1020", "#3a1f4d", "#c4572b"
        bands = 24
        for i in range(bands):                       # sunset gradient
            t = i / (bands - 1)
            c = mix(top, midc, t * 2) if t < 0.5 else mix(midc, low, (t - 0.5) * 2)
            y0 = i * HEIGHT / bands
            cv.create_rectangle(0, y0, WIDTH, y0 + HEIGHT / bands + 1, fill=c, width=0)
        sx, sy = WIDTH / 2, 255                        # rising sun with rays
        for i in range(16):
            a = i * math.pi / 8 + self.tick * 0.004
            cv.create_line(sx, sy, sx + 600 * math.cos(a), sy + 600 * math.sin(a),
                           fill="#e0743a", width=3)
        glow = 70 + 4 * math.sin(self.tick * 0.05)
        cv.create_oval(sx - glow - 25, sy - glow - 25, sx + glow + 25, sy + glow + 25,
                       fill="#e8843f", width=0)
        cv.create_oval(sx - glow, sy - glow, sx + glow, sy + glow, fill="#ffb347", width=0)
        for e in self.embers:                          # rising golden embers
            x = e[0] + 6 * math.sin(e[3])
            cv.create_oval(x, e[1], x + 3, e[1] + 3, fill="#ffd27a", width=0)
        cv.create_polygon(0, HEIGHT, 0, 240, 90, 205, 170, 235, 260, 190, 360, 250,
                          480, 225, 600, 255, 720, 215, 820, 240, WIDTH, 220, WIDTH, HEIGHT,
                          fill="#1a0f1f", outline="")         # mountains
        # the dino, standing proud on the mountain top
        self.draw_couple(232, 192, 1.1, "#1a0f1f", "#ffb347",
                         partner=self.couple_on())

        text, who = QUOTES[self.quote_i]
        fade = min(1.0, self.quote_t / 40)
        cv.create_text(WIDTH / 2, 28, text="THE MOTIVATION ROOM",
                       fill=mix("#0b1020", "#ffd27a", 0.9), font=("Courier", 13, "bold"))
        cv.create_text(WIDTH / 2, 92, text=f"\u201c{text}\u201d", width=760,
                       justify="center", fill=mix("#0b1020", "#ffffff", fade),
                       font=("Georgia", 18, "italic"))
        cv.create_text(WIDTH / 2, 150, text=f"- {who}", fill=mix("#0b1020", "#ffd27a", fade),
                       font=("Georgia", 13, "bold"))
        cv.create_text(WIDTH / 2, 185, text=self.affirmation, fill="#ffffff",
                       font=("Courier", 13, "bold"))
        if self.sound_on:
            if self.audio.neural_available():
                voice = self.audio.voice_status or "natural voice"
            elif self.audio.installing:
                voice = self.audio.voice_status
            else:
                voice = ((self.audio.voice_status + "  ") if self.audio.voice_status else "") \
                    + "press V for a natural, human-sounding voice"
            voice += "   |   " + (self.audio.status or "starting music...")
        else:
            voice = "sound OFF"
        cv.create_text(WIDTH / 2, HEIGHT - 26, fill="#ffd27a", font=("Courier", 10),
                       text=voice)
        cv.create_text(WIDTH / 2, HEIGHT - 10, fill="#ffffff", font=("Courier", 10),
                       text="SPACE/Right: next quote   Left: previous   M: sound   "
                            "Esc: back to the menu")

    def draw_shop(self, bg, fg):
        cv = self.canvas
        title, items = SHOPS[getattr(self, "shop_tab", "power")]
        self.shop_index %= len(items)
        cv.create_text(290, 20, text=title, fill=fg, font=("Courier", 20, "bold"))
        cv.create_text(290, 44, text=f"coins: {self.save['coins']}   "
                                     f"diamonds: {self.save['diamonds']}",
                       fill=self.coin_col(), font=("Courier", 14, "bold"))
        top, row, visible = 70, 20, 9
        for vi in range(visible):
            i = self.shop_scroll + vi
            if i >= len(items):
                break
            item = items[i]
            iid, name, desc, _, kind, mx = item
            y = top + vi * row
            if i == self.shop_index:
                cv.create_rectangle(25, y - 9, 560, y + 10,
                                    fill=mix(bg, "#4db8ff", 0.25), width=0)
            cv.create_text(40, y, anchor="w", fill=fg, font=("Courier", 12, "bold"),
                           text=name)
            cv.create_text(410, y, anchor="e", fill=self.coin_col(),
                           font=("Courier", 12, "bold"), text=self.price_text(item))
            cv.create_text(548, y, anchor="e", fill=fg, font=("Courier", 11),
                           text=self.item_status(item))
        if self.shop_scroll > 0:
            cv.create_text(15, top, text="^", fill=fg, font=("Courier", 12, "bold"))
        if self.shop_scroll + visible < len(items):
            cv.create_text(15, top + (visible - 1) * row, text="v", fill=fg,
                           font=("Courier", 12, "bold"))
        self.draw_preview(items[self.shop_index], bg, fg)
        cv.create_text(290, HEIGHT - 28, fill="#ff5c5c",
                       font=("Courier", 12, "bold"), text=self.message)
        cv.create_text(WIDTH / 2, HEIGHT - 9, fill=fg, font=("Courier", 10),
                       text="Up/Down: choose   Enter: buy/equip   Tab/Left/Right: other shop   Esc: back")
        for p in self.particles:
            s = p["size"]
            cv.create_rectangle(p["x"], p["y"], p["x"] + s, p["y"] + s,
                                fill=p["color"] or fg, width=0)

    def price_text(self, item):
        iid, _, _, _, kind, mx = item
        price = self.item_price(item)
        owned = kind in COSMETIC and iid in self.owned_list(kind)
        maxed = kind not in COSMETIC and self.save[iid] >= mx
        if owned or maxed or price is None:
            return "-"
        return "free" if price == 0 else f"{price} c"

    def draw_preview(self, item, bg, fg):
        """Right-hand panel: shows what the selected item looks like."""
        cv = self.canvas
        iid, name, desc, _, kind, mx = item
        x0, y0, x1, y1 = 580, 58, 885, 270
        cv.create_rectangle(x0, y0, x1, y1, fill=mix(bg, fg, 0.06), outline=fg)
        cx, ground = (x0 + x1) / 2, 190
        skin = SKIN_COLOR.get(self.save["skin"]) or fg
        acc = self.save["acc"]
        lk = self.look()
        legs = (self.tick // 8) % 2 == 0

        if kind == "land":
            self.draw_land_preview(iid, x0 + 8, y0 + 8, x1 - 8, ground + 8)
        else:
            cv.create_line(x0 + 15, ground, x1 - 15, ground, fill=fg, width=2)

        if kind == "skin":
            body = SKIN_COLOR.get(iid) or fg
            self.draw_dino_shape(cx - 40, ground, 1.8, body, bg, legs_up=legs, **lk)
        elif kind in ("acc", "hair", "eyes", "outfit"):
            lk = self.look(couple=False)
            lk[kind] = {"acc": iid, "outfit": iid, "hair": HAIR.get(iid),
                        "eyes": EYES.get(iid)}[kind]
            self.draw_dino_shape(cx - 40, ground, 1.8, skin, bg, legs_up=legs, **lk)
        elif kind == "toggle":
            self.draw_couple(cx + 20, ground, 1.2, skin, bg, legs_up=legs,
                             look=self.look(couple=True))
        elif iid == "shield":
            self.draw_dino_shape(cx - 30, ground, 1.4, skin, bg, legs_up=legs, **lk)
            r = 55 + 3 * math.sin(self.tick * 0.15)
            cv.create_oval(cx - r + 8, ground - 45 - r, cx + r + 8, ground - 45 + r,
                           outline="#4db8ff", width=3)
        elif iid == "slowmo":
            cv.create_oval(cx - 45, ground - 120, cx + 45, ground - 30, fill="#ffffff",
                           outline="#4db8ff", width=4)
            a = self.tick * 0.02
            cv.create_line(cx, ground - 75, cx + 30 * math.sin(a), ground - 75
                           - 30 * math.cos(a), fill="#333333", width=3)
            cv.create_line(cx, ground - 75, cx + 18, ground - 75, fill="#333333", width=4)
            cv.create_text(cx, ground - 15, text="press X in a run", fill=fg,
                           font=("Courier", 10))
        elif iid == "doublejump":
            hop = 25 * abs(math.sin(self.tick * 0.05))
            self.draw_dino_shape(cx - 30, ground - 45 - hop, 1.3, skin, bg, **lk)
            for dx in (-18, 0, 18):
                cv.create_oval(cx + dx - 6, ground - 40 - hop, cx + dx + 6,
                               ground - 30 - hop, fill="#dddddd", width=0)
        elif iid == "magnet":
            cv.create_arc(cx - 40, ground - 130, cx + 40, ground - 50, start=180,
                          extent=180, style="arc", outline="#d63031", width=14)
            for sx in (cx - 40, cx + 40):
                cv.create_rectangle(sx - 7, ground - 115, sx + 7, ground - 90,
                                    fill="#d63031", width=0)
                cv.create_rectangle(sx - 7, ground - 125, sx + 7, ground - 115,
                                    fill="#dfe6e9", width=0)
            for i in range(3):
                t = (self.tick * 0.03 + i / 3) % 1
                yy = ground - 150 + 50 * t
                cv.create_oval(cx - 8 + (i - 1) * 30 * (1 - t), yy - 8,
                               cx + 8 + (i - 1) * 30 * (1 - t), yy + 8,
                               fill=self.coin_col(), outline=fg)
            lvl = self.save["magnet"]
            cv.create_text(cx, ground - 15, text=f"level {lvl}/3", fill=fg,
                           font=("Courier", 10))
        elif iid == "coinx2":
            r = 40 * abs(math.cos(self.tick * 0.04)) + 5
            cv.create_oval(cx - r, ground - 120, cx + r, ground - 40,
                           fill=self.coin_col(), outline=fg, width=2)
            cv.create_text(cx, ground - 80, text="x2", fill="#7a5600",
                           font=("Courier", 22, "bold"))
        elif iid == "trophy":
            self.draw_trophy(cx, ground, 1.15)
        elif iid == "ufo_luck":
            ux, uy = cx + 30 * math.sin(self.tick * 0.05), ground - 100
            cv.create_polygon(ux - 10, uy + 8, ux + 10, uy + 8, ux + 40, ground,
                              ux - 40, ground, fill=mix(bg, "#5cd65c", 0.3), width=0)
            cv.create_oval(ux - 16, uy - 18, ux + 16, uy + 4, fill="#9fe8ff", outline=fg)
            cv.create_oval(ux - 40, uy - 6, ux + 40, uy + 12, fill="#8a8f99", outline=fg)

        cv.create_text(cx, ground + 22, text=name, fill=fg, font=("Courier", 13, "bold"))
        cv.create_text(cx, ground + 44, text=desc, fill=fg, font=("Courier", 10),
                       width=x1 - x0 - 20, justify="center")
        cv.create_text(cx, ground + 66, fill=self.coin_col(),
                       font=("Courier", 11, "bold"),
                       text=f"{self.price_text(item)}   {self.item_status(item)}")

    def draw_land_preview(self, iid, x0, y0, x1, y1):
        cv = self.canvas
        land = LANDS[iid]
        c = land["day"]
        ground = y1 - 8
        cv.create_rectangle(x0, y0, x1, y1, fill=c["bg"], width=0)
        sun = "#ff9f6b" if land["decor"] == "craters" else "#ffe9a3"
        cv.create_oval(x1 - 50, y0 + 12, x1 - 22, y0 + 40, fill=sun, width=0)
        cv.create_oval(x0 + 30, y0 + 22, x0 + 80, y0 + 36, fill=c["cloud"], width=0)
        dark = mix(c["hill"], c["fg"], 0.35)
        for hx, w, h in ((x0 - 10, 150, 50), (x0 + 110, 130, 38), (x0 + 200, 110, 55)):
            cv.create_oval(hx, ground - h, hx + w, ground + h, fill=c["hill"], width=0)
            if land["decor"] == "trees":
                for t in (0.35, 0.6):
                    tx = hx + w * t
                    top = ground - h * math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2))
                    cv.create_polygon(tx - 8, top + 5, tx + 8, top + 5, tx, top - 18,
                                      fill=dark)
            elif land["decor"] == "craters":
                cv.create_oval(hx + w * 0.4, ground - h * 0.5, hx + w * 0.6,
                               ground - h * 0.5 + 7, fill=dark, width=0)
            elif land["decor"] == "snow":
                cv.create_oval(hx + w * 0.35, ground - h, hx + w * 0.65,
                               ground - h * 0.75, fill="#ffffff", width=0)
        cv.create_rectangle(x0, ground, x1, y1, fill=c["bg"], width=0)
        cv.create_line(x0, ground, x1, ground, fill=c["fg"], width=2)
        if land["decor"] == "snow":
            for i in range(14):
                fx = x0 + (i * 37 + self.tick * 0.6) % (x1 - x0)
                fy = y0 + (i * 23 + self.tick * 1.2) % (ground - y0)
                cv.create_oval(fx, fy, fx + 3, fy + 3, fill="#9fb3c8", width=0)
        body = SKIN_COLOR.get(self.save["skin"]) or c["fg"]
        self.draw_couple(x0 + 25 + (50 if self.couple_on() else 0), ground, 0.8, body,
                         c["bg"], legs_up=(self.tick // 8) % 2 == 0,
                         partner=self.couple_on())
        cv.create_rectangle(x0, y0, x1, y1, outline=c["fg"])

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
