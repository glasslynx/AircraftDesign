import json
import math
from pathlib import Path
import random
import tkinter as tk
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

# ============================================================================
# CONFIGURATION & THEME
# ============================================================================

TILE_SIZE = 44
GRID_COLS = 22
GRID_ROWS = 14
CANVAS_W = GRID_COLS * TILE_SIZE
CANVAS_H = GRID_ROWS * TILE_SIZE
FRAME_MS = 16
SCORE_FILE = Path("bastion_scores.json")

TARGET_MODES = ["First", "Strongest", "Closest", "Last"]

COLORS = {
    "bg": "#0b0e14",
    "panel": "#131822",
    "panel_alt": "#1a2130",
    "border": "#2a3447",
    "grid_line": "#141a24",
    "road": "#232b3a",
    "road_edge": "#323d52",
    "spawn": "#06d6a0",
    "core": "#ef476f",
    "text": "#edf2f4",
    "muted": "#8d99ae",
    "accent": "#4cc9f0",
    "gold": "#ffd166",
    "danger": "#ff4d6d",
    "valid": "#06d6a0",
    "invalid": "#ef476f",
}


# ============================================================================
# MAP DEFINITIONS & PATH GEOMETRY
# ============================================================================

MAPS: Dict[str, List[Tuple[int, int]]] = {
    "Serpentine Valley": [
        (0, 2),
        (5, 2),
        (5, 11),
        (10, 11),
        (10, 3),
        (16, 3),
        (16, 10),
        (21, 10),
    ],
    "Twin Switchback": [
        (0, 1),
        (19, 1),
        (19, 5),
        (3, 5),
        (3, 9),
        (18, 9),
        (18, 12),
        (0, 12),
    ],
    "Citadel Spiral": [
        (0, 1),
        (20, 1),
        (20, 12),
        (2, 12),
        (2, 4),
        (17, 4),
        (17, 9),
        (6, 9),
        (6, 6),
        (12, 6),
    ],
}


def grid_to_pixel(gx: int, gy: int) -> Tuple[float, float]:
    return (gx + 0.5) * TILE_SIZE, (gy + 0.5) * TILE_SIZE


def pixel_to_grid(px: float, py: float) -> Tuple[int, int]:
    return int(px // TILE_SIZE), int(py // TILE_SIZE)


def compute_road_cells(waypoints: List[Tuple[int, int]]) -> Set[Tuple[int, int]]:
    road: Set[Tuple[int, int]] = set()
    for i in range(len(waypoints) - 1):
        x1, y1 = waypoints[i]
        x2, y2 = waypoints[i + 1]
        if x1 == x2:
            step = 1 if y2 >= y1 else -1
            for y in range(y1, y2 + step, step):
                road.add((x1, y))
        elif y1 == y2:
            step = 1 if x2 >= x1 else -1
            for x in range(x1, x2 + step, step):
                road.add((x, y1))
    return road


# ============================================================================
# DATA BLUEPRINTS: TOWERS & ENEMIES
# ============================================================================

@dataclass(frozen=True)
class TowerBlueprint:
    key: str
    name: str
    hotkey: str
    cost: int
    damage: float
    fire_rate: float
    range_tiles: float
    color: str
    accent: str
    proj_speed: float
    splash_radius: float = 0.0
    slow_factor: float = 0.0
    slow_duration: float = 0.0
    chain_count: int = 0
    stun_duration: float = 0.0
    armor_pierce: bool = False
    is_beacon: bool = False
    description: str = ""


TOWER_SPECS: Dict[str, TowerBlueprint] = {
    "kinetic": TowerBlueprint(
        key="kinetic",
        name="Autocannon",
        hotkey="1",
        cost=50,
        damage=14.0,
        fire_rate=2.2,
        range_tiles=3.3,
        color="#4cc9f0",
        accent="#90e0ef",
        proj_speed=540.0,
        description="Rapid-fire kinetic rounds. Reliable early defense.",
    ),
    "frost": TowerBlueprint(
        key="frost",
        name="Cryo Spire",
        hotkey="2",
        cost=75,
        damage=9.0,
        fire_rate=1.35,
        range_tiles=3.1,
        color="#48bfe3",
        accent="#caf0f8",
        proj_speed=420.0,
        splash_radius=54.0,
        slow_factor=0.45,
        slow_duration=2.4,
        description="Chills targets in a small radius, slowing movement by 45%.",
    ),
    "cannon": TowerBlueprint(
        key="cannon",
        name="Mortar Pod",
        hotkey="3",
        cost=100,
        damage=34.0,
        fire_rate=0.75,
        range_tiles=3.8,
        color="#f77f00",
        accent="#fcbf49",
        proj_speed=340.0,
        splash_radius=78.0,
        description="Heavy explosive shells dealing wide area splash damage.",
    ),
    "tesla": TowerBlueprint(
        key="tesla",
        name="Arc Coil",
        hotkey="4",
        cost=125,
        damage=22.0,
        fire_rate=1.05,
        range_tiles=3.0,
        color="#b5179e",
        accent="#f72585",
        proj_speed=0.0,
        chain_count=3,
        stun_duration=0.35,
        description="Discharges chain lightning across 3 enemies with micro-stun.",
    ),
    "sniper": TowerBlueprint(
        key="sniper",
        name="Railgun",
        hotkey="5",
        cost=145,
        damage=88.0,
        fire_rate=0.52,
        range_tiles=5.8,
        color="#06d6a0",
        accent="#b7efc5",
        proj_speed=0.0,
        armor_pierce=True,
        description="Extreme range hyper-velocity slug that ignores armor.",
    ),
    "beacon": TowerBlueprint(
        key="beacon",
        name="Command Relay",
        hotkey="6",
        cost=115,
        damage=0.0,
        fire_rate=0.0,
        range_tiles=2.6,
        color="#ffd166",
        accent="#fff3b0",
        proj_speed=0.0,
        is_beacon=True,
        description="Boosts nearby towers (+22% fire rate & +12% range per level).",
    ),
}


@dataclass(frozen=True)
class EnemyBlueprint:
    key: str
    name: str
    max_hp: float
    speed: float
    armor: float
    reward: int
    lives_cost: int
    radius: int
    color: str
    regen_per_sec: float = 0.0


ENEMY_SPECS: Dict[str, EnemyBlueprint] = {
    "scout": EnemyBlueprint(
        key="scout",
        name="Skirmisher",
        max_hp=42.0,
        speed=88.0,
        armor=0.0,
        reward=8,
        lives_cost=1,
        radius=10,
        color="#8ac926",
    ),
    "trooper": EnemyBlueprint(
        key="trooper",
        name="Vanguard",
        max_hp=88.0,
        speed=64.0,
        armor=2.0,
        reward=12,
        lives_cost=1,
        radius=12,
        color="#ffca3a",
    ),
    "sprinter": EnemyBlueprint(
        key="sprinter",
        name="Phase Runner",
        max_hp=65.0,
        speed=126.0,
        armor=0.0,
        reward=14,
        lives_cost=1,
        radius=9,
        color="#4cc9f0",
    ),
    "armored": EnemyBlueprint(
        key="armored",
        name="Aegis Mech",
        max_hp=210.0,
        speed=44.0,
        armor=10.0,
        reward=22,
        lives_cost=2,
        radius=14,
        color="#adb5bd",
    ),
    "regen": EnemyBlueprint(
        key="regen",
        name="Bio-Strider",
        max_hp=155.0,
        speed=58.0,
        armor=3.0,
        reward=20,
        lives_cost=2,
        radius=13,
        color="#06d6a0",
        regen_per_sec=11.0,
    ),
    "boss": EnemyBlueprint(
        key="boss",
        name="Dreadnought",
        max_hp=1150.0,
        speed=34.0,
        armor=16.0,
        reward=95,
        lives_cost=5,
        radius=18,
        color="#ef476f",
        regen_per_sec=8.0,
    ),
}


# ============================================================================
# SCORE PERSISTENCE
# ============================================================================

class ScoreManager:
    def __init__(self, path: Path = SCORE_FILE) -> None:
        self.path = path
        self.records: List[Dict[str, object]] = self._load()

    def _load(self) -> List[Dict[str, object]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data[:5]
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def best_score(self) -> int:
        if not self.records:
            return 0
        return max(int(r.get("score", 0)) for r in self.records)

    def record_run(self, map_name: str, wave: int, score: int) -> None:
        if score <= 0:
            return
        self.records.append({"map": map_name, "wave": wave, "score": score})
        self.records.sort(key=lambda item: int(item["score"]), reverse=True)
        self.records = self.records[:5]
        try:
            self.path.write_text(json.dumps(self.records, indent=2), encoding="utf-8")
        except OSError:
            pass


# ============================================================================
# VISUAL EFFECTS & PROJECTILES
# ============================================================================

class Particle:
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: str,
        size: float,
        lifetime: float,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        if self.lifetime <= 0:
            return False
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.92
        self.vy *= 0.92
        return True

    def draw(self, canvas: tk.Canvas) -> None:
        ratio = max(0.1, self.lifetime / self.max_lifetime)
        r = self.size * ratio
        canvas.create_oval(
            self.x - r, self.y - r, self.x + r, self.y + r, fill=self.color, outline=""
        )


class FloatingText:
    def __init__(self, x: float, y: float, text: str, color: str) -> None:
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.lifetime = 0.75

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        self.y -= 28.0 * dt
        return self.lifetime > 0

    def draw(self, canvas: tk.Canvas) -> None:
        canvas.create_text(
            self.x,
            self.y,
            text=self.text,
            fill=self.color,
            font=("Consolas", 9, "bold"),
        )


class LightningArc:
    def __init__(
        self, points: List[Tuple[float, float]], color: str, width: int = 2
    ) -> None:
        self.points = points
        self.color = color
        self.width = width
        self.lifetime = 0.14

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        return self.lifetime > 0

    def draw(self, canvas: tk.Canvas) -> None:
        for i in range(len(self.points) - 1):
            x1, y1 = self.points[i]
            x2, y2 = self.points[i + 1]
            mx = (x1 + x2) * 0.5 + random.uniform(-7, 7)
            my = (y1 + y2) * 0.5 + random.uniform(-7, 7)
            canvas.create_line(
                x1, y1, mx, my, x2, y2, fill=self.color, width=self.width
            )


class ShockwaveRing:
    def __init__(
        self, x: float, y: float, max_radius: float, color: str, duration: float = 0.28
    ) -> None:
        self.x = x
        self.y = y
        self.max_radius = max_radius
        self.color = color
        self.duration = duration
        self.elapsed = 0.0

    def update(self, dt: float) -> bool:
        self.elapsed += dt
        return self.elapsed < self.duration

    def draw(self, canvas: tk.Canvas) -> None:
        progress = min(1.0, self.elapsed / self.duration)
        r = max(4.0, self.max_radius * progress)
        canvas.create_oval(
            self.x - r, self.y - r, self.x + r, self.y + r, outline=self.color, width=2
        )


class Projectile:
    def __init__(
        self,
        x: float,
        y: float,
        target: "Enemy",
        source_tower: "Tower",
        damage: float,
        speed: float,
        color: str,
        splash_radius: float = 0.0,
        slow_factor: float = 0.0,
        slow_duration: float = 0.0,
    ) -> None:
        self.x = x
        self.y = y
        self.target = target
        self.source_tower = source_tower
        self.damage = damage
        self.speed = speed
        self.color = color
        self.splash_radius = splash_radius
        self.slow_factor = slow_factor
        self.slow_duration = slow_duration
        self.last_tx = target.x
        self.last_ty = target.y
        self.alive = True

    def update(
        self,
        dt: float,
        enemies: List["Enemy"],
        rings: List[ShockwaveRing],
        particles: List[Particle],
        texts: List[FloatingText],
    ) -> None:
        if not self.alive:
            return

        if self.target.alive and not self.target.reached_end:
            self.last_tx = self.target.x
            self.last_ty = self.target.y

        dx = self.last_tx - self.x
        dy = self.last_ty - self.y
        dist = math.hypot(dx, dy)
        step = self.speed * dt

        if dist <= step or dist < 4.0:
            self.x = self.last_tx
            self.y = self.last_ty
            self._detonate(enemies, rings, particles, texts)
            self.alive = False
            return

        self.x += (dx / dist) * step
        self.y += (dy / dist) * step

    def _detonate(
        self,
        enemies: List["Enemy"],
        rings: List[ShockwaveRing],
        particles: List[Particle],
        texts: List[FloatingText],
    ) -> None:
        if self.splash_radius > 0:
            rings.append(ShockwaveRing(self.x, self.y, self.splash_radius, self.color))
            for enemy in enemies:
                if not enemy.alive or enemy.reached_end:
                    continue
                d = math.hypot(enemy.x - self.x, enemy.y - self.y)
                if d <= self.splash_radius:
                    falloff = max(0.45, 1.0 - (d / (self.splash_radius * 1.35)))
                    dealt = enemy.take_damage(self.damage * falloff)
                    self.source_tower.register_hit(enemy, dealt)
                    if self.slow_factor > 0:
                        enemy.apply_slow(self.slow_factor, self.slow_duration)
        else:
            if self.target.alive and not self.target.reached_end:
                dealt = self.target.take_damage(self.damage)
                self.source_tower.register_hit(self.target, dealt)
                texts.append(
                    FloatingText(
                        self.target.x,
                        self.target.y - 14,
                        f"-{int(round(dealt))}",
                        self.color,
                    )
                )
                if self.slow_factor > 0:
                    self.target.apply_slow(self.slow_factor, self.slow_duration)

        for _ in range(5):
            angle = random.uniform(0, math.tau)
            spd = random.uniform(35, 110)
            particles.append(
                Particle(
                    self.x,
                    self.y,
                    math.cos(angle) * spd,
                    math.sin(angle) * spd,
                    self.color,
                    3.2,
                    0.26,
                )
            )

    def draw(self, canvas: tk.Canvas) -> None:
        r = 4.5 if self.splash_radius > 0 else 3.2
        canvas.create_oval(
            self.x - r, self.y - r, self.x + r, self.y + r, fill=self.color, outline=""
        )


# ============================================================================
# ENEMY ENTITY
# ============================================================================

class Enemy:
    def __init__(
        self,
        spec: EnemyBlueprint,
        waypoints: List[Tuple[int, int]],
        hp_scale: float,
        reward_scale: float,
    ) -> None:
        self.spec = spec
        self.pixel_points = [grid_to_pixel(gx, gy) for gx, gy in waypoints]
        self.x, self.y = self.pixel_points[0]
        self.waypoint_idx = 1
        self.distance_traveled = 0.0

        self.max_hp = round(spec.max_hp * hp_scale, 1)
        self.hp = self.max_hp
        self.base_speed = spec.speed
        self.armor = spec.armor
        self.reward = max(1, int(round(spec.reward * reward_scale)))
        self.lives_cost = spec.lives_cost

        self.alive = True
        self.reached_end = False
        self.reward_claimed = False

        self.slow_factor = 0.0
        self.slow_timer = 0.0
        self.stun_timer = 0.0
        self.hit_flash = 0.0

    def apply_slow(self, factor: float, duration: float) -> None:
        if factor >= self.slow_factor:
            self.slow_factor = factor
            self.slow_timer = max(self.slow_timer, duration)

    def apply_stun(self, duration: float) -> None:
        self.stun_timer = max(self.stun_timer, duration)

    def take_damage(self, raw_damage: float, armor_pierce: bool = False) -> float:
        if not self.alive:
            return 0.0
        effective_armor = 0.0 if armor_pierce else self.armor
        actual = max(1.0, raw_damage - effective_armor)
        self.hp -= actual
        self.hit_flash = 0.08
        if self.hp <= 0:
            self.hp = 0.0
            self.alive = False
        return actual

    def update(self, dt: float) -> None:
        if not self.alive or self.reached_end:
            return

        if self.hit_flash > 0:
            self.hit_flash = max(0.0, self.hit_flash - dt)

        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_factor = 0.0

        if self.spec.regen_per_sec > 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + self.spec.regen_per_sec * dt)

        if self.stun_timer > 0:
            self.stun_timer -= dt
            return

        speed = self.base_speed * (1.0 - self.slow_factor)
        remaining_move = speed * dt

        while remaining_move > 0 and self.waypoint_idx < len(self.pixel_points):
            tx, ty = self.pixel_points[self.waypoint_idx]
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)

            if dist <= remaining_move:
                self.x = tx
                self.y = ty
                self.distance_traveled += dist
                remaining_move -= dist
                self.waypoint_idx += 1
            else:
                self.x += (dx / dist) * remaining_move
                self.y += (dy / dist) * remaining_move
                self.distance_traveled += remaining_move
                remaining_move = 0.0

        if self.waypoint_idx >= len(self.pixel_points):
            self.reached_end = True

    def draw(self, canvas: tk.Canvas) -> None:
        if not self.alive or self.reached_end:
            return

        r = self.spec.radius
        fill_color = "#ffffff" if self.hit_flash > 0 else self.spec.color
        outline_color = "#90e0ef" if self.slow_timer > 0 else "#10141d"
        outline_w = 2 if self.slow_timer > 0 else 1

        if self.spec.key == "armored" or self.spec.key == "boss":
            canvas.create_rectangle(
                self.x - r,
                self.y - r,
                self.x + r,
                self.y + r,
                fill=fill_color,
                outline=outline_color,
                width=outline_w,
            )
        elif self.spec.key == "sprinter":
            pts = [
                self.x,
                self.y - r - 2,
                self.x + r + 2,
                self.y,
                self.x,
                self.y + r + 2,
                self.x - r - 2,
                self.y,
            ]
            canvas.create_polygon(
                pts, fill=fill_color, outline=outline_color, width=outline_w
            )
        else:
            canvas.create_oval(
                self.x - r,
                self.y - r,
                self.x + r,
                self.y + r,
                fill=fill_color,
                outline=outline_color,
                width=outline_w,
            )

        if self.stun_timer > 0:
            canvas.create_oval(
                self.x - r - 3,
                self.y - r - 3,
                self.x + r + 3,
                self.y + r + 3,
                outline="#f72585",
                width=2,
            )

        # Health bar
        bar_w = max(22, r * 2 + 4)
        bar_h = 4
        bx1 = self.x - bar_w * 0.5
        by1 = self.y - r - 9
        hp_ratio = max(0.0, self.hp / self.max_hp)
        canvas.create_rectangle(
            bx1, by1, bx1 + bar_w, by1 + bar_h, fill="#1a1f2b", outline=""
        )
        hp_color = "#06d6a0" if hp_ratio > 0.5 else ("#ffd166" if hp_ratio > 0.25 else "#ef476f")
        canvas.create_rectangle(
            bx1, by1, bx1 + bar_w * hp_ratio, by1 + bar_h, fill=hp_color, outline=""
        )


# ============================================================================
# TOWER ENTITY & TARGETING AI
# ============================================================================

class Tower:
    MAX_LEVEL = 3

    def __init__(self, gx: int, gy: int, spec: TowerBlueprint) -> None:
        self.gx = gx
        self.gy = gy
        self.x, self.y = grid_to_pixel(gx, gy)
        self.spec = spec
        self.level = 1
        self.total_invested = spec.cost
        self.kills = 0
        self.total_damage = 0.0
        self.target_mode_idx = 0
        self.cooldown = 0.0
        self.angle = 0.0
        self.rate_buff = 1.0
        self.range_buff = 1.0
        self.pulse_phase = random.uniform(0, math.tau)

    @property
    def target_mode(self) -> str:
        return TARGET_MODES[self.target_mode_idx]

    def cycle_target_mode(self) -> str:
        self.target_mode_idx = (self.target_mode_idx + 1) % len(TARGET_MODES)
        return self.target_mode

    @property
    def damage(self) -> float:
        return self.spec.damage * (1.0 + 0.48 * (self.level - 1))

    @property
    def fire_rate(self) -> float:
        base = self.spec.fire_rate * (1.0 + 0.16 * (self.level - 1))
        return base * self.rate_buff

    @property
    def range_px(self) -> float:
        base_tiles = self.spec.range_tiles * (1.0 + 0.10 * (self.level - 1))
        return base_tiles * TILE_SIZE * self.range_buff

    @property
    def upgrade_cost(self) -> Optional[int]:
        if self.level >= self.MAX_LEVEL:
            return None
        return int(round(self.spec.cost * (0.85 * self.level)))

    @property
    def sell_value(self) -> int:
        return int(round(self.total_invested * 0.72))

    def upgrade(self) -> bool:
        cost = self.upgrade_cost
        if cost is None:
            return False
        self.level += 1
        self.total_invested += cost
        return True

    def register_hit(self, enemy: Enemy, damage_dealt: float) -> None:
        self.total_damage += damage_dealt
        if not enemy.alive:
            self.kills += 1

    def select_target(self, enemies: List[Enemy]) -> Optional[Enemy]:
        in_range: List[Enemy] = []
        max_r = self.range_px
        for enemy in enemies:
            if not enemy.alive or enemy.reached_end:
                continue
            if math.hypot(enemy.x - self.x, enemy.y - self.y) <= max_r:
                in_range.append(enemy)

        if not in_range:
            return None

        mode = self.target_mode
        if mode == "First":
            return max(in_range, key=lambda e: e.distance_traveled)
        if mode == "Last":
            return min(in_range, key=lambda e: e.distance_traveled)
        if mode == "Strongest":
            return max(in_range, key=lambda e: e.hp)
        return min(in_range, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))

    def update(
        self,
        dt: float,
        enemies: List[Enemy],
        projectiles: List[Projectile],
        arcs: List[LightningArc],
        rings: List[ShockwaveRing],
        particles: List[Particle],
        texts: List[FloatingText],
    ) -> None:
        self.pulse_phase += dt * 3.2
        if self.spec.is_beacon:
            return

        if self.cooldown > 0:
            self.cooldown = max(0.0, self.cooldown - dt)

        target = self.select_target(enemies)
        if target is None:
            return

        self.angle = math.atan2(target.y - self.y, target.x - self.x)
        if self.cooldown > 0:
            return

        self.cooldown = 1.0 / max(0.1, self.fire_rate)
        self._fire_at(target, enemies, projectiles, arcs, rings, particles, texts)

    def _fire_at(
        self,
        target: Enemy,
        enemies: List[Enemy],
        projectiles: List[Projectile],
        arcs: List[LightningArc],
        rings: List[ShockwaveRing],
        particles: List[Particle],
        texts: List[FloatingText],
    ) -> None:
        if self.spec.key == "tesla":
            self._fire_chain_lightning(target, enemies, arcs, texts)
            return

        if self.spec.key == "sniper":
            arcs.append(
                LightningArc([(self.x, self.y), (target.x, target.y)], self.spec.accent, width=3)
            )
            dealt = target.take_damage(self.damage, armor_pierce=True)
            self.register_hit(target, dealt)
            texts.append(
                FloatingText(target.x, target.y - 16, f"-{int(round(dealt))}!", self.spec.color)
            )
            rings.append(ShockwaveRing(target.x, target.y, 18.0, self.spec.color, duration=0.18))
            return

        muzzle_x = self.x + math.cos(self.angle) * 14
        muzzle_y = self.y + math.sin(self.angle) * 14
        projectiles.append(
            Projectile(
                x=muzzle_x,
                y=muzzle_y,
                target=target,
                source_tower=self,
                damage=self.damage,
                speed=self.spec.proj_speed,
                color=self.spec.accent,
                splash_radius=self.spec.splash_radius,
                slow_factor=self.spec.slow_factor,
                slow_duration=self.spec.slow_duration,
            )
        )

    def _fire_chain_lightning(
        self,
        primary: Enemy,
        enemies: List[Enemy],
        arcs: List[LightningArc],
        texts: List[FloatingText],
    ) -> None:
        chain_limit = self.spec.chain_count + (self.level - 1)
        jump_radius = 115.0
        visited: Set[int] = set()
        points: List[Tuple[float, float]] = [(self.x, self.y)]
        current: Optional[Enemy] = primary
        dmg = self.damage

        for _ in range(chain_limit):
            if current is None:
                break
            visited.add(id(current))
            points.append((current.x, current.y))
            dealt = current.take_damage(dmg)
            self.register_hit(current, dealt)
            current.apply_stun(self.spec.stun_duration)
            texts.append(
                FloatingText(current.x, current.y - 14, f"-{int(round(dealt))}", self.spec.accent)
            )
            dmg *= 0.80

            next_target: Optional[Enemy] = None
            best_dist = jump_radius
            for candidate in enemies:
                if (
                    not candidate.alive
                    or candidate.reached_end
                    or id(candidate) in visited
                ):
                    continue
                d = math.hypot(candidate.x - current.x, candidate.y - current.y)
                if d <= best_dist:
                    best_dist = d
                    next_target = candidate
            current = next_target

        if len(points) > 1:
            arcs.append(LightningArc(points, self.spec.accent, width=2))

    def draw(self, canvas: tk.Canvas, selected: bool) -> None:
        pad = 6
        x1 = self.gx * TILE_SIZE + pad
        y1 = self.gy * TILE_SIZE + pad
        x2 = (self.gx + 1) * TILE_SIZE - pad
        y2 = (self.gy + 1) * TILE_SIZE - pad

        outline = "#ffffff" if selected else "#1d2432"
        canvas.create_rectangle(
            x1, y1, x2, y2, fill="#19202e", outline=outline, width=2 if selected else 1
        )

        if self.spec.is_beacon:
            pulse = 10 + math.sin(self.pulse_phase) * 2.5
            canvas.create_oval(
                self.x - pulse,
                self.y - pulse,
                self.x + pulse,
                self.y + pulse,
                fill=self.spec.color,
                outline=self.spec.accent,
                width=2,
            )
        else:
            core_r = 10
            canvas.create_oval(
                self.x - core_r,
                self.y - core_r,
                self.x + core_r,
                self.y + core_r,
                fill=self.spec.color,
                outline="#0f131a",
                width=1,
            )
            bx = self.x + math.cos(self.angle) * 15
            by = self.y + math.sin(self.angle) * 15
            canvas.create_line(
                self.x, self.y, bx, by, fill=self.spec.accent, width=4, capstyle=tk.ROUND
            )

        # Level indicator pips
        for idx in range(self.level):
            px = x1 + 5 + idx * 7
            py = y2 - 4
            canvas.create_oval(px - 2, py - 2, px + 2, py + 2, fill="#ffd166", outline="")


# ============================================================================
# WAVE DIRECTOR
# ============================================================================

CURATED_WAVES: List[List[Tuple[str, int, float]]] = [
    [("scout", 8, 0.85)],
    [("scout", 12, 0.70)],
    [("scout", 8, 0.65), ("trooper", 5, 0.90)],
    [("trooper", 10, 0.75), ("sprinter", 5, 0.60)],
    [("armored", 4, 1.35), ("trooper", 8, 0.75)],
    [("sprinter", 14, 0.48)],
    [("regen", 6, 1.00), ("trooper", 8, 0.70)],
    [("armored", 6, 1.15), ("regen", 5, 0.95)],
    [("sprinter", 12, 0.45), ("armored", 6, 1.05)],
    [("trooper", 12, 0.55), ("boss", 1, 2.0)],
    [("regen", 10, 0.75), ("sprinter", 12, 0.42)],
    [("armored", 10, 0.90), ("regen", 8, 0.80)],
    [("sprinter", 18, 0.36), ("armored", 8, 0.85)],
    [("armored", 10, 0.75), ("regen", 10, 0.70), ("boss", 1, 2.5)],
    [("boss", 2, 3.2), ("armored", 10, 0.75), ("sprinter", 15, 0.40)],
]


class WaveDirector:
    def __init__(self) -> None:
        self.wave_num = 0
        self.spawn_queue: List[Tuple[str, float]] = []
        self.spawn_timer = 0.0
        self.active = False

    def start_next_wave(self) -> int:
        self.wave_num += 1
        self.spawn_queue.clear()

        if self.wave_num <= len(CURATED_WAVES):
            groups = CURATED_WAVES[self.wave_num - 1]
        else:
            extra = self.wave_num - len(CURATED_WAVES)
            groups = [
                ("sprinter", 10 + extra * 2, 0.36),
                ("armored", 6 + extra, 0.72),
                ("regen", 6 + extra, 0.68),
                ("boss", 1 + extra // 2, 2.6),
            ]

        for enemy_key, count, interval in groups:
            for _ in range(count):
                self.spawn_queue.append((enemy_key, interval))

        self.spawn_timer = 0.25
        self.active = True
        return self.wave_num

    def update(self, dt: float, waypoints: List[Tuple[int, int]]) -> List[Enemy]:
        spawned: List[Enemy] = []
        if not self.active:
            return spawned

        if not self.spawn_queue:
            self.active = False
            return spawned

        self.spawn_timer -= dt
        while self.spawn_timer <= 0 and self.spawn_queue:
            enemy_key, interval = self.spawn_queue.pop(0)
            hp_scale = 1.0 + (self.wave_num - 1) * 0.14
            reward_scale = 1.0 + (self.wave_num - 1) * 0.04
            spawned.append(
                Enemy(ENEMY_SPECS[enemy_key], waypoints, hp_scale, reward_scale)
            )
            self.spawn_timer += interval

        return spawned


# ============================================================================
# MAIN GAME APPLICATION
# ============================================================================

class BastionApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("BastionGrid — Tactical Tower Defense")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)

        self.scores = ScoreManager()
        self.current_map_name = "Serpentine Valley"
        self.after_id: Optional[str] = None

        self.selected_build_key: Optional[str] = "kinetic"
        self.selected_tower: Optional[Tower] = None
        self.hover_cell: Optional[Tuple[int, int]] = None

        self.game_speed = 1
        self.paused = False
        self.auto_wave = False
        self.game_over = False

        self._build_ui()
        self._bind_events()
        self._reset_game()

    def _build_ui(self) -> None:
        # Top status bar
        top_bar = tk.Frame(self.root, bg=COLORS["panel"], padx=12, pady=8)
        top_bar.pack(fill="x", padx=10, pady=(10, 6))

        tk.Label(
            top_bar,
            text="BASTION GRID",
            font=("Consolas", 13, "bold"),
            bg=COLORS["panel"],
            fg=COLORS["accent"],
        ).pack(side="left", padx=(0, 14))

        self.map_var = tk.StringVar(value=self.current_map_name)
        map_menu = tk.OptionMenu(
            top_bar, self.map_var, *MAPS.keys(), command=self._on_map_change
        )
        map_menu.config(
            font=("Consolas", 10),
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            activebackground=COLORS["border"],
            activeforeground=COLORS["text"],
            highlightthickness=0,
            bd=0,
        )
        map_menu["menu"].config(
            bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Consolas", 10)
        )
        map_menu.pack(side="left", padx=(0, 18))

        self.stats_label = tk.Label(
            top_bar,
            font=("Consolas", 11, "bold"),
            bg=COLORS["panel"],
            fg=COLORS["text"],
        )
        self.stats_label.pack(side="left")

        self.status_banner = tk.Label(
            top_bar,
            font=("Consolas", 10),
            bg=COLORS["panel"],
            fg=COLORS["gold"],
        )
        self.status_banner.pack(side="right")

        # Main workspace
        workspace = tk.Frame(self.root, bg=COLORS["bg"])
        workspace.pack(padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(
            workspace,
            width=CANVAS_W,
            height=CANVAS_H,
            bg=COLORS["bg"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        self.canvas.grid(row=0, column=0)

        # Right sidebar
        sidebar = tk.Frame(workspace, width=275, bg=COLORS["panel"], padx=10, pady=10)
        sidebar.grid(row=0, column=1, sticky="ns", padx=(10, 0))
        sidebar.grid_propagate(False)

        tk.Label(
            sidebar,
            text="DEPLOY TURRETS [1-6]",
            font=("Consolas", 10, "bold"),
            bg=COLORS["panel"],
            fg=COLORS["accent"],
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.build_buttons: Dict[str, tk.Button] = {}
        for key, spec in TOWER_SPECS.items():
            btn = tk.Button(
                sidebar,
                text=f"[{spec.hotkey}] {spec.name:<13} ${spec.cost}",
                font=("Consolas", 10),
                anchor="w",
                padx=8,
                pady=4,
                bg=COLORS["panel_alt"],
                fg=COLORS["text"],
                activebackground=COLORS["border"],
                activeforeground=COLORS["text"],
                relief="flat",
                command=lambda k=key: self._select_build_type(k),
            )
            btn.pack(fill="x", pady=2)
            self.build_buttons[key] = btn

        self.desc_label = tk.Label(
            sidebar,
            text="",
            font=("Consolas", 9),
            bg=COLORS["panel_alt"],
            fg=COLORS["muted"],
            wraplength=245,
            justify="left",
            anchor="nw",
            height=3,
            padx=8,
            pady=6,
        )
        self.desc_label.pack(fill="x", pady=(6, 10))

        # Inspector section
        tk.Label(
            sidebar,
            text="TURRET INSPECTOR",
            font=("Consolas", 10, "bold"),
            bg=COLORS["panel"],
            fg=COLORS["accent"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self.inspector_label = tk.Label(
            sidebar,
            text="Click a placed tower to inspect,\nupgrade, or change targeting.",
            font=("Consolas", 9),
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            justify="left",
            anchor="nw",
            height=7,
            padx=8,
            pady=6,
        )
        self.inspector_label.pack(fill="x", pady=(0, 6))

        insp_btns = tk.Frame(sidebar, bg=COLORS["panel"])
        insp_btns.pack(fill="x", pady=(0, 10))

        self.target_btn = tk.Button(
            insp_btns,
            text="Target [T]",
            font=("Consolas", 9, "bold"),
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            relief="flat",
            command=self._cycle_selected_target,
        )
        self.target_btn.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.upgrade_btn = tk.Button(
            insp_btns,
            text="Upgrade [U]",
            font=("Consolas", 9, "bold"),
            bg=COLORS["panel_alt"],
            fg=COLORS["gold"],
            relief="flat",
            command=self._upgrade_selected_tower,
        )
        self.upgrade_btn.pack(side="left", expand=True, fill="x", padx=2)

        self.sell_btn = tk.Button(
            insp_btns,
            text="Sell [X]",
            font=("Consolas", 9, "bold"),
            bg=COLORS["panel_alt"],
            fg=COLORS["danger"],
            relief="flat",
            command=self._sell_selected_tower,
        )
        self.sell_btn.pack(side="left", expand=True, fill="x", padx=(2, 0))

        # Wave & Simulation controls
        tk.Label(
            sidebar,
            text="COMMAND CONTROLS",
            font=("Consolas", 10, "bold"),
            bg=COLORS["panel"],
            fg=COLORS["accent"],
            anchor="w",
        ).pack(fill="x", pady=(2, 4))

        self.wave_btn = tk.Button(
            sidebar,
            text="Start Wave [Space]",
            font=("Consolas", 10, "bold"),
            bg="#06d6a0",
            fg="#0b0e14",
            relief="flat",
            pady=5,
            command=self._trigger_wave,
        )
        self.wave_btn.pack(fill="x", pady=2)

        ctrl_row = tk.Frame(sidebar, bg=COLORS["panel"])
        ctrl_row.pack(fill="x", pady=2)

        self.speed_btn = tk.Button(
            ctrl_row,
            text="Speed: 1x",
            font=("Consolas", 9, "bold"),
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            relief="flat",
            command=self._toggle_speed,
        )
        self.speed_btn.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.auto_btn = tk.Button(
            ctrl_row,
            text="Auto: OFF",
            font=("Consolas", 9, "bold"),
            bg=COLORS["panel_alt"],
            fg=COLORS["muted"],
            relief="flat",
            command=self._toggle_auto_wave,
        )
        self.auto_btn.pack(side="left", expand=True, fill="x", padx=2)

        self.pause_btn = tk.Button(
            ctrl_row,
            text="Pause [P]",
            font=("Consolas", 9, "bold"),
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            relief="flat",
            command=self._toggle_pause,
        )
        self.pause_btn.pack(side="left", expand=True, fill="x", padx=(2, 0))

        tk.Button(
            sidebar,
            text="Restart Map [R]",
            font=("Consolas", 9),
            bg=COLORS["panel_alt"],
            fg=COLORS["muted"],
            relief="flat",
            pady=4,
            command=self._reset_game,
        ).pack(fill="x", pady=(6, 0))

    def _bind_events(self) -> None:
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Leave>", lambda _: setattr(self, "hover_cell", None))
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.root.bind("<KeyPress>", self._on_key_press)

    def _on_map_change(self, selected: str) -> None:
        self.current_map_name = selected
        self._reset_game()

    def _reset_game(self) -> None:
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        self.waypoints = MAPS[self.current_map_name]
        self.road_cells = compute_road_cells(self.waypoints)
        self.gold = 160
        self.lives = 20
        self.score = 0
        self.game_over = False
        self.paused = False

        self.towers: List[Tower] = []
        self.enemies: List[Enemy] = []
        self.projectiles: List[Projectile] = []
        self.arcs: List[LightningArc] = []
        self.rings: List[ShockwaveRing] = []
        self.particles: List[Particle] = []
        self.texts: List[FloatingText] = []

        self.director = WaveDirector()
        self.selected_tower = None
        self._select_build_type("kinetic")
        self._set_banner("Build defenses and launch Wave 1.")
        self._refresh_sidebar()
        self._loop()

    def _set_banner(self, message: str) -> None:
        self.status_banner.config(text=message)

    def _select_build_type(self, key: Optional[str]) -> None:
        self.selected_build_key = key
        for k, btn in self.build_buttons.items():
            if k == key:
                btn.config(bg="#26334d", fg=COLORS["accent"])
            else:
                btn.config(bg=COLORS["panel_alt"], fg=COLORS["text"])

        if key and key in TOWER_SPECS:
            self.desc_label.config(text=TOWER_SPECS[key].description)
        else:
            self.desc_label.config(text="Right-click to clear build selection.")

    def _tower_at(self, gx: int, gy: int) -> Optional[Tower]:
        for tower in self.towers:
            if tower.gx == gx and tower.gy == gy:
                return tower
        return None

    def _can_build_at(self, gx: int, gy: int) -> bool:
        if not (0 <= gx < GRID_COLS and 0 <= gy < GRID_ROWS):
            return False
        if (gx, gy) in self.road_cells:
            return False
        if self._tower_at(gx, gy) is not None:
            return False
        return True

    def _recalculate_beacon_buffs(self) -> None:
        for tower in self.towers:
            tower.rate_buff = 1.0
            tower.range_buff = 1.0

        beacons = [t for t in self.towers if t.spec.is_beacon]
        for tower in self.towers:
            if tower.spec.is_beacon:
                continue
            for beacon in beacons:
                dist = math.hypot(tower.x - beacon.x, tower.y - beacon.y)
                if dist <= beacon.range_px:
                    tower.rate_buff += 0.22 * beacon.level
                    tower.range_buff += 0.12 * beacon.level

    def _on_mouse_move(self, event: tk.Event) -> None:
        gx, gy = pixel_to_grid(event.x, event.y)
        if 0 <= gx < GRID_COLS and 0 <= gy < GRID_ROWS:
            self.hover_cell = (gx, gy)
        else:
            self.hover_cell = None

    def _on_left_click(self, event: tk.Event) -> None:
        if self.game_over:
            return
        gx, gy = pixel_to_grid(event.x, event.y)
        existing = self._tower_at(gx, gy)
        if existing is not None:
            self.selected_tower = existing
            self._refresh_sidebar()
            return

        if self.selected_build_key is None:
            self.selected_tower = None
            self._refresh_sidebar()
            return

        spec = TOWER_SPECS[self.selected_build_key]
        if not self._can_build_at(gx, gy):
            self._set_banner("Blocked tile — cannot build on road.")
            return
        if self.gold < spec.cost:
            self._set_banner(f"Need ${spec.cost} for {spec.name}.")
            return

        self.gold -= spec.cost
        tower = Tower(gx, gy, spec)
        self.towers.append(tower)
        self.selected_tower = tower
        self._recalculate_beacon_buffs()
        self._set_banner(f"Deployed {spec.name} (-${spec.cost}).")
        self._refresh_sidebar()

    def _on_right_click(self, _event: tk.Event) -> None:
        self._select_build_type(None)
        self.selected_tower = None
        self._refresh_sidebar()

    def _on_key_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        hotkey_map = {spec.hotkey: spec.key for spec in TOWER_SPECS.values()}
        if key in hotkey_map:
            self._select_build_type(hotkey_map[key])
        elif key == "space":
            self._trigger_wave()
        elif key == "t":
            self._cycle_selected_target()
        elif key == "u":
            self._upgrade_selected_tower()
        elif key == "x":
            self._sell_selected_tower()
        elif key == "p":
            self._toggle_pause()
        elif key == "r":
            self._reset_game()

    def _cycle_selected_target(self) -> None:
        if self.selected_tower and not self.selected_tower.spec.is_beacon:
            mode = self.selected_tower.cycle_target_mode()
            self._set_banner(f"{self.selected_tower.spec.name} targeting: {mode}")
            self._refresh_sidebar()

    def _upgrade_selected_tower(self) -> None:
        if self.game_over or self.selected_tower is None:
            return
        cost = self.selected_tower.upgrade_cost
        if cost is None:
            self._set_banner("Turret already at maximum level.")
            return
        if self.gold < cost:
            self._set_banner(f"Need ${cost} to upgrade.")
            return
        self.gold -= cost
        self.selected_tower.upgrade()
        self._recalculate_beacon_buffs()
        self._set_banner(
            f"Upgraded {self.selected_tower.spec.name} to Lv.{self.selected_tower.level}!"
        )
        self._refresh_sidebar()

    def _sell_selected_tower(self) -> None:
        if self.game_over or self.selected_tower is None:
            return
        refund = self.selected_tower.sell_value
        name = self.selected_tower.spec.name
        self.gold += refund
        self.towers.remove(self.selected_tower)
        self.selected_tower = None
        self._recalculate_beacon_buffs()
        self._set_banner(f"Salvaged {name} (+${refund}).")
        self._refresh_sidebar()

    def _trigger_wave(self) -> None:
        if self.game_over:
            return
        if self.director.active or self.enemies:
            self._set_banner("Clear the current wave before launching the next.")
            return
        wave_num = self.director.start_next_wave()
        self._set_banner(f"Wave {wave_num} inbound!")

    def _toggle_speed(self) -> None:
        self.game_speed = 2 if self.game_speed == 1 else 1
        self.speed_btn.config(text=f"Speed: {self.game_speed}x")

    def _toggle_auto_wave(self) -> None:
        self.auto_wave = not self.auto_wave
        self.auto_btn.config(
            text=f"Auto: {'ON' if self.auto_wave else 'OFF'}",
            fg=COLORS["spawn"] if self.auto_wave else COLORS["muted"],
        )

    def _toggle_pause(self) -> None:
        if self.game_over:
            return
        self.paused = not self.paused
        self.pause_btn.config(
            text="Resume [P]" if self.paused else "Pause [P]",
            fg=COLORS["gold"] if self.paused else COLORS["text"],
        )

    def _loop(self) -> None:
        dt = (FRAME_MS / 1000.0) * self.game_speed
        if not self.paused and not self.game_over:
            self._step_simulation(dt)
        self._render()
        self.after_id = self.root.after(FRAME_MS, self._loop)

    def _step_simulation(self, dt: float) -> None:
        newly_spawned = self.director.update(dt, self.waypoints)
        if newly_spawned:
            self.enemies.extend(newly_spawned)

        for enemy in self.enemies:
            enemy.update(dt)
            if not enemy.alive and not enemy.reward_claimed:
                enemy.reward_claimed = True
                self.gold += enemy.reward
                self.score += enemy.reward * 10
                self.texts.append(
                    FloatingText(enemy.x, enemy.y - 6, f"+${enemy.reward}", COLORS["gold"])
                )
            elif enemy.reached_end and not enemy.reward_claimed:
                enemy.reward_claimed = True
                self.lives = max(0, self.lives - enemy.lives_cost)
                self._set_banner(f"Core breached! -{enemy.lives_cost} Lives.")

        self.enemies = [e for e in self.enemies if e.alive and not e.reached_end]

        for tower in self.towers:
            tower.update(
                dt,
                self.enemies,
                self.projectiles,
                self.arcs,
                self.rings,
                self.particles,
                self.texts,
            )

        for proj in self.projectiles:
            proj.update(dt, self.enemies, self.rings, self.particles, self.texts)
        self.projectiles = [p for p in self.projectiles if p.alive]

        self.arcs = [a for a in self.arcs if a.update(dt)]
        self.rings = [r for r in self.rings if r.update(dt)]
        self.particles = [p for p in self.particles if p.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]

        if self.lives <= 0 and not self.game_over:
            self.game_over = True
            self.scores.record_run(self.current_map_name, self.director.wave_num, self.score)
            self._set_banner("CORE DESTROYED — Press R to play again.")

        if (
            not self.game_over
            and not self.director.active
            and not self.enemies
            and self.director.wave_num > 0
            and self.auto_wave
        ):
            self._trigger_wave()

        self._refresh_sidebar()

    def _refresh_sidebar(self) -> None:
        self.stats_label.config(
            text=(
                f"Wave: {self.director.wave_num}   "
                f"Lives: {self.lives}   "
                f"Gold: ${self.gold}   "
                f"Score: {self.score}   "
                f"Best: {max(self.score, self.scores.best_score())}"
            )
        )

        if self.selected_tower is None:
            self.inspector_label.config(
                text="No turret selected.\nClick any placed turret to view\nstats, upgrade, or set priority."
            )
            self.upgrade_btn.config(text="Upgrade [U]")
            return

        t = self.selected_tower
        if t.spec.is_beacon:
            info = (
                f"{t.spec.name} (Lv.{t.level}/{t.MAX_LEVEL})\n"
                f"Fire Rate Aura : +{int(22 * t.level)}%\n"
                f"Range Aura     : +{int(12 * t.level)}%\n"
                f"Salvage Value  : ${t.sell_value}"
            )
        else:
            info = (
                f"{t.spec.name} (Lv.{t.level}/{t.MAX_LEVEL})\n"
                f"Target : {t.target_mode}  |  Kills: {t.kills}\n"
                f"Damage : {t.damage:.1f}  |  Rate: {t.fire_rate:.2f}/s\n"
                f"Range  : {t.range_px / TILE_SIZE:.1f} tiles\n"
                f"Total Dmg: {int(t.total_damage)} | Sell: ${t.sell_value}"
            )
        self.inspector_label.config(text=info)

        up_cost = t.upgrade_cost
        self.upgrade_btn.config(text="Maxed" if up_cost is None else f"Up (${up_cost})")

    def _render(self) -> None:
        self.canvas.delete("all")

        # Subtle tactical grid
        for c in range(1, GRID_COLS):
            x = c * TILE_SIZE
            self.canvas.create_line(x, 0, x, CANVAS_H, fill=COLORS["grid_line"])
        for r in range(1, GRID_ROWS):
            y = r * TILE_SIZE
            self.canvas.create_line(0, y, CANVAS_W, y, fill=COLORS["grid_line"])

        # Road cells
        for gx, gy in self.road_cells:
            x1 = gx * TILE_SIZE + 2
            y1 = gy * TILE_SIZE + 2
            x2 = (gx + 1) * TILE_SIZE - 2
            y2 = (gy + 1) * TILE_SIZE - 2
            self.canvas.create_rectangle(
                x1, y1, x2, y2, fill=COLORS["road"], outline=COLORS["road_edge"]
            )

        # Spawn and Core portals
        sx, sy = grid_to_pixel(*self.waypoints[0])
        cx, cy = grid_to_pixel(*self.waypoints[-1])
        self.canvas.create_oval(
            sx - 15, sy - 15, sx + 15, sy + 15, outline=COLORS["spawn"], width=3
        )
        self.canvas.create_text(
            sx, sy, text="IN", fill=COLORS["spawn"], font=("Consolas", 8, "bold")
        )
        self.canvas.create_oval(
            cx - 16, cy - 16, cx + 16, cy + 16, outline=COLORS["core"], width=3
        )
        self.canvas.create_text(
            cx, cy, text="CORE", fill=COLORS["core"], font=("Consolas", 8, "bold")
        )

        # Selected tower range ring
        if self.selected_tower is not None:
            r = self.selected_tower.range_px
            self.canvas.create_oval(
                self.selected_tower.x - r,
                self.selected_tower.y - r,
                self.selected_tower.x + r,
                self.selected_tower.y + r,
                outline=COLORS["accent"],
                dash=(5, 4),
                width=2,
            )

        # Hover placement preview
        if self.hover_cell is not None and self.selected_build_key is not None:
            hx, hy = self.hover_cell
            spec = TOWER_SPECS[self.selected_build_key]
            valid = self._can_build_at(hx, hy) and self.gold >= spec.cost
            preview_color = COLORS["valid"] if valid else COLORS["invalid"]
            px, py = grid_to_pixel(hx, hy)
            r = spec.range_tiles * TILE_SIZE
            self.canvas.create_oval(
                px - r, py - r, px + r, py + r, outline=preview_color, dash=(3, 3)
            )
            self.canvas.create_rectangle(
                hx * TILE_SIZE + 5,
                hy * TILE_SIZE + 5,
                (hx + 1) * TILE_SIZE - 5,
                (hy + 1) * TILE_SIZE - 5,
                outline=preview_color,
                width=2,
            )

        # Entities & VFX
        for tower in self.towers:
            tower.draw(self.canvas, selected=(tower is self.selected_tower))

        for enemy in self.enemies:
            enemy.draw(self.canvas)

        for proj in self.projectiles:
            proj.draw(self.canvas)

        for arc in self.arcs:
            arc.draw(self.canvas)

        for ring in self.rings:
            ring.draw(self.canvas)

        for particle in self.particles:
            particle.draw(self.canvas)

        for text in self.texts:
            text.draw(self.canvas)

        if self.paused:
            self.canvas.create_text(
                CANVAS_W // 2,
                CANVAS_H // 2,
                text="PAUSED",
                fill=COLORS["gold"],
                font=("Consolas", 28, "bold"),
            )

        if self.game_over:
            self.canvas.create_rectangle(
                CANVAS_W // 2 - 230,
                CANVAS_H // 2 - 55,
                CANVAS_W // 2 + 230,
                CANVAS_H // 2 + 55,
                fill="#0b0e14",
                outline=COLORS["danger"],
                width=2,
            )
            self.canvas.create_text(
                CANVAS_W // 2,
                CANVAS_H // 2 - 14,
                text="CORE BREACHED — GAME OVER",
                fill=COLORS["danger"],
                font=("Consolas", 18, "bold"),
            )
            self.canvas.create_text(
                CANVAS_W // 2,
                CANVAS_H // 2 + 20,
                text=f"Final Score: {self.score} (Wave {self.director.wave_num}) — Press R",
                fill=COLORS["text"],
                font=("Consolas", 11),
            )


if __name__ == "__main__":
    root = tk.Tk()
    BastionApp(root)
    root.mainloop()
