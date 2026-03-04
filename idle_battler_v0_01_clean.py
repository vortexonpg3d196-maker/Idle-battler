import tkinter as tk
from dataclasses import dataclass, asdict, field
import random
import math
import time
import datetime
import json
from pathlib import Path
import os
from typing import Dict, List, Optional, Tuple

APP_TITLE = "Idle Battler_v0_01"
APP_VERSION = "1.0-alpha"


# --- Build / version (for debugging releases) ---
APP_VERSION = 'v12.11-release-candidate'
BUILD_ID = '2026-03-03_0543'


# ---------------------------------
# Idle Battler v12.0 (Dungeons + Post-35 Ascension)
# Adds:
# - Hidden endgame (unlocks ONLY at Forge Level 35):
#   - Dungeons window
#   - Tickets currency (dungeon rewards + dungeon entry)
#   - Forge level cap extends to 100
#   - New rarities post-35 (hidden until unlock)
# - Player HP scaling with forge level (fixes 120 HP vs huge enemies)
# - SELL ALL (UNEQUIPPED) button
#
# Notes:
# - New players (Forge 1-34) won't see:
#   - Tickets
#   - Dungeons
#   - Level cap 100 UI
#   - Post-35 rarities
# ---------------------------------

# Save file handling (public release-safe)
APP_NAME = "ForgeBattler"
SAVE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME)
SAVE_PATH = os.path.join(SAVE_DIR, "save.json")
LEGACY_SAVE_PATH = os.path.join(os.path.dirname(__file__), "forge_battler_save.json")

# Limited-time redeem code
BETA_CODE = "BETA"
# Expires April 2, 2026 (local system date)
BETA_CODE_EXPIRES = datetime.date(2026, 4, 2)
# Build/version (used for maintenance rewards + safe one-time migrations)
GAME_VERSION = "v12.12-pass2.1"

# When GAME_VERSION changes, grant a small maintenance reward once per user
MAINTENANCE_REWARD = {"hammers": 500, "coins": 2500, "gems": 75, "tickets": 10}

# During active development, allow specific codes to be reset on update so you can test them again
RESETTABLE_CODES_ON_UPDATE = {"beta", "ayysoul"}



# Base rarities (visible pre-35)
BASE_RARITIES = [
    "Common", "Tempered", "Runed", "Arcane", "Eternal",
    "Ascendant", "Mythic", "Divine", "Celestial", "Primordial", "Transcendent"
]
POST35_RARITIES = [
    "Omniscient",
    "Voidbound",
    "Sovereign",
    "Apex",
    "Paradox",
]

RARITIES_ALL = BASE_RARITIES + POST35_RARITIES
RARITY_COLORS = {
    "Common": "#9AA0A6",
    "Tempered": "#22C55E",
    "Runed": "#60A5FA",
    "Arcane": "#A855F7",
    "Eternal": "#F59E0B",
    "Ascendant": "#EF4444",
    "Mythic": "#FACC15",
    "Divine": "#7DD3FC",
    "Celestial": "#A7F3D0",
    "Primordial": "#C4B5FD",
    "Transcendent": "#F472B6",

    # Post-35
    "Omniscient": "#34D399",  # mint
    "Voidbound": "#111827",   # near-black
    "Sovereign": "#F97316",   # orange
    "Apex": "#38BDF8",        # bright cyan
    "Paradox": "#FB7185",     # pink/red
    "Beta": "#FFFFFF",      # limited
}

RARITY_MULT = {
    "Common": 1.00,
    "Tempered": 1.25,
    "Runed": 1.60,
    "Arcane": 2.05,
    "Eternal": 2.65,
    "Ascendant": 3.40,
    "Mythic": 4.50,
    "Divine": 6.00,
    "Celestial": 7.50,
    "Primordial": 9.50,
    "Transcendent": 12.00,

    # Post-35
    "Omniscient": 15.00,
    "Voidbound": 19.00,
    "Sovereign": 24.00,
    "Apex": 30.00,
    "Paradox": 38.00,
}



# -------------------------------
# Quests (easy, friendly)
# -------------------------------
QUEST_TEMPLATES = [
    {"kind": "win_battles", "target": 10, "desc": "Win 10 battles", "xp": 25, "gems": 10, "coins": 250},
    {"kind": "forge_items", "target": 15, "desc": "Forge 15 weapons", "xp": 25, "gems": 10, "coins": 250},
    {"kind": "sell_items", "target": 10, "desc": "Sell 10 weapons", "xp": 25, "gems": 10, "coins": 250},
    {"kind": "beat_boss", "target": 1,  "desc": "Defeat 1 boss", "xp": 40, "gems": 25, "coins": 600},
]

def make_daily_quests(n: int = 3) -> List[dict]:
    # simple offline rotation; stored in save so players keep progress
    picks = random.sample(QUEST_TEMPLATES, k=min(n, len(QUEST_TEMPLATES)))
    quests = []
    for q in picks:
        quests.append({
            "kind": q["kind"],
            "desc": q["desc"],
            "target": int(q["target"]),
            "progress": 0,
            "claimed": False,
            "xp": int(q["xp"]),
            "gems": int(q["gems"]),
            "coins": int(q["coins"]),
        })
    return quests

# -------------------------------
# Battle Pass (offline alpha)
# Exclusive weapons here are NOT in normal forge pools.
# -------------------------------
BP_XP_PER_TIER = 100

# Battle Pass scrolling (fake scroll)
BP_ROWS_VISIBLE = 11  # how many tiers fit on screen

BP_REWARDS = {
    # tier: reward dict
    1: {"type": "currency", "hammers": 50},
    2: {"type": "currency", "coins": 1000},
    3: {"type": "weapon", "name": "Nebula Reaver", "rarity": "Mythic", "weapon_type": "Sword", "base_dmg": 42000},
    4: {"type": "currency", "gems": 60},
    5: {"type": "currency", "hammers": 120},
    7: {"type": "weapon", "name": "Starfall Carbine", "rarity": "Divine", "weapon_type": "Gun", "base_dmg": 52000},
    10: {"type": "currency", "coins": 5000, "gems": 120},
    12: {"type": "weapon", "name": "Void Crown Pike", "rarity": "Celestial", "weapon_type": "Spear", "base_dmg": 68000},
    15: {"type": "weapon", "name": "Paradox Monarch", "rarity": "Paradox", "weapon_type": "Hammer", "base_dmg": 82000},
}
WEAPON_TYPES = ["Sword", "Axe", "Hammer", "Spear", "Bow", "Staff", "Gun", "Gauntlets"]

AFFIX_POOL = [
    "Health %", "Skill Damage %", "Critical Chance %", "Critical Damage %",
    "Attack Speed %", "Lifesteal %", "Melee Damage %", "Ranged Damage %",
    "Skill Cooldown %", "Block Chance %"
]

ENEMIES = ["Slime", "Goblin", "Ghoul", "Wisp", "Crawler", "Knight", "Golem", "Shade", "Revenant", "Warden"]

# Base name pools (for pre-35 rarities)
NAME_POOLS_BASE: Dict[str, Dict[str, List[str]]] = {
    "Common": {
        "Sword": ["Iron Blade", "Steel Saber", "Militia Sword"],
        "Axe": ["Steel Hatchet", "Woodcutter Axe", "Rough Axe"],
        "Hammer": ["Stone Hammer", "Iron Maul", "Forge Mallet"],
        "Spear": ["Soldier Spear", "Short Pike", "Rusty Lance"],
        "Bow": ["Shortbow", "Hunting Bow", "Wooden Bow"],
        "Staff": ["Ash Staff", "Worn Staff", "Apprentice Staff"],
        "Gun": ["Rusty Revolver", "Old Rifle", "Scrap SMG"],
        "Gauntlets": ["Leather Wraps", "Iron Knuckles", "Training Gauntlets"],
    },
    "Tempered": {
        "Sword": ["Tempered Edge", "Ashblade", "Forged Sabre"],
        "Axe": ["Ash Axe", "Tempered Hatchet", "Ember Axe"],
        "Hammer": ["Forge Maul", "Tempered Maul", "Cinder Hammer"],
        "Spear": ["Piercing Lance", "Forged Pike", "Steelthorn Spear"],
        "Bow": ["Tempered Longbow", "Emberstring Bow", "Forged Recurve"],
        "Staff": ["Cinder Staff", "Tempered Rod", "Ember Staff"],
        "Gun": ["Tempered Carbine", "Ember Pistol", "Forged SMG"],
        "Gauntlets": ["Tempered Fists", "Emberwrap Gauntlets", "Forged Knuckles"],
    },
    "Runed": {
        "Sword": ["Rune Fang", "Glyph Blade", "Sigil Saber"],
        "Axe": ["Glyph Cleaver", "Rune Axe", "Hex Hatchet"],
        "Hammer": ["Hexhammer", "Runic Maul", "Sigil Hammer"],
        "Spear": ["Sigil Pike", "Rune Spear", "Glyph Lance"],
        "Bow": ["Glyphstring Bow", "Runebound Longbow", "Sigil Recurve"],
        "Staff": ["Glyphstaff", "Runic Rod", "Sigil Staff"],
        "Gun": ["Runepeater", "Glyph Carbine", "Sigil SMG"],
        "Gauntlets": ["Runed Grips", "Glyphfist Gauntlets", "Sigil Knuckles"],
    },
    "Arcane": {
        "Sword": ["Arcveil", "Spellrender", "Aether Blade"],
        "Axe": ["Mooncarver", "Arcane Cleaver", "Void Axe"],
        "Hammer": ["Aether Maul", "Spellmaul", "Arc Hammer"],
        "Spear": ["Moonspike", "Aether Pike", "Arcane Lance"],
        "Bow": ["Aetherbow", "Moonstring Longbow", "Arc Recurve"],
        "Staff": ["Spellstaff", "Aether Rod", "Void Staff"],
        "Gun": ["Aether Blaster", "Arc Carbine", "Void SMG"],
        "Gauntlets": ["Aetherfists", "Spellbound Gauntlets", "Void Grips"],
    },
    "Eternal": {
        "Sword": ["Sunwake", "Last Oath", "Dawn Splitter"],
        "Axe": ["Evercleaver", "Eternal Hatchet", "Dusk Axe"],
        "Hammer": ["Oath Maul", "Eternal Maul", "Sunhammer"],
        "Spear": ["Everpiercer", "Dawn Pike", "Eternal Lance"],
        "Bow": ["Dawnstring Bow", "Eternal Longbow", "Sunwake Recurve"],
        "Staff": ["Dawnstaff", "Eternal Rod", "Sunwake Staff"],
        "Gun": ["Eternal Carbine", "Dawnreaper Rifle", "Sunwake SMG"],
        "Gauntlets": ["Eternal Grips", "Oathbound Gauntlets", "Sunfist Wraps"],
    },
    "Ascendant": {
        "Sword": ["Crownbreaker", "Skyrend", "Ember Reign"],
        "Axe": ["Storm Cleaver", "Highflare Axe", "Crown Axe"],
        "Hammer": ["Storm Throne", "Crown Maul", "Skyhammer"],
        "Spear": ["Skylance", "Crown Pike", "Stormpiercer"],
        "Bow": ["Stormstring Bow", "Skyforged Longbow", "Crown Recurve"],
        "Staff": ["Skyrod", "Stormstaff", "Crown Staff"],
        "Gun": ["Stormcarbine", "Crown Rifle", "Skyforged SMG"],
        "Gauntlets": ["Crownfists", "Stormgrip Gauntlets", "Skyknuckles"],
    },
    "Mythic": {
        "Sword": ["Kingsbane", "Nightfall Edge", "Starforged Blade"],
        "Axe": ["Wyrmfang Cleaver", "Starforged Axe", "Nightfall Axe"],
        "Hammer": ["Kingsmaul", "Wyrmfang Maul", "Starforged Hammer"],
        "Spear": ["Wyrmfang Pike", "Nightfall Lance", "Starforged Spear"],
        "Bow": ["Nightfall Longbow", "Starforged Bow", "Wyrmstring Recurve"],
        "Staff": ["Starforged Staff", "Nightfall Rod", "Wyrmstaff"],
        "Gun": ["Starforged Rifle", "Nightfall Blaster", "Wyrmfang SMG"],
        "Gauntlets": ["Kingsgrip", "Nightfall Gauntlets", "Starforged Fists"],
    },
    "Divine": {
        "Sword": ["Blade of First Light", "Judgment of Solara", "Radiant Oathblade"],
        "Axe": ["Sanctum Reaver", "Dawnreaper Axe", "Solar Cleaver"],
        "Hammer": ["Radiant Cataclysm", "Solara's Hammer", "Sanctum Maul"],
        "Spear": ["Lightpiercer", "Judgment Lance", "Sanctum Pike"],
        "Bow": ["Halo Longbow", "Solarstring Bow", "Judgment Recurve"],
        "Staff": ["Sanctum Staff", "Halo Rod", "First Light Staff"],
        "Gun": ["Radiant Carbine", "Halo Blaster", "Judgment Rifle"],
        "Gauntlets": ["Halo Grips", "Sanctum Gauntlets", "Radiant Fists"],
    },
    "Celestial": {
        "Sword": ["Astral Edge", "Starweaver Blade", "Heavenfall Saber"],
        "Axe": ["Comet Cleaver", "Skyshard Axe", "Nebula Reaver"],
        "Hammer": ["Starlight Maul", "Astral Hammer", "Meteorcrush"],
        "Spear": ["Constellation Pike", "Skyneedle Lance", "Aurora Spear"],
        "Bow": ["Aurorasting Bow", "Astral Longbow", "Nebula Recurve"],
        "Staff": ["Starseer Staff", "Aurora Rod", "Astral Staff"],
        "Gun": ["Nebula Carbine", "Starlight Blaster", "Aurora Rifle"],
        "Gauntlets": ["Astral Grips", "Nebula Gauntlets", "Aurora Fists"],
    },
    "Primordial": {
        "Sword": ["Worldcore Blade", "Elder Riftedge", "Originbrand"],
        "Axe": ["Firstborn Cleaver", "Stone-Age Reaver", "Elderwood Axe"],
        "Hammer": ["Titanforged Maul", "Worldbreaker Hammer", "Elder Crushmaul"],
        "Spear": ["Genesis Pike", "Earthspine Lance", "Ancestor Spear"],
        "Bow": ["Genesis Longbow", "Worldcore Bow", "Ancestor Recurve"],
        "Staff": ["Worldcore Staff", "Elder Rod", "Genesis Staff"],
        "Gun": ["Worldbreaker Rifle", "Origin Carbine", "Elder Blaster"],
        "Gauntlets": ["Titan Grips", "Worldcore Gauntlets", "Ancestor Knuckles"],
    },
    "Transcendent": {
        "Sword": ["Infinity Edgeblade", "Realitysplit Saber", "Apex Oathblade"],
        "Axe": ["Godrift Cleaver", "Paradox Axe", "Apex Reaver"],
        "Hammer": ["Singularity Maul", "Infinity Hammer", "Apex Cataclysm"],
        "Spear": ["Continuum Pike", "Paradox Lance", "Apex Skyspike"],
        "Bow": ["Infinity Longbow", "Paradox Bow", "Apex Recurve"],
        "Staff": ["Singularity Staff", "Infinity Rod", "Apex Staff"],
        "Gun": ["Paradox Rifle", "Infinity Blaster", "Apex Carbine"],
        "Gauntlets": ["Singularity Fists", "Paradox Gauntlets", "Apex Knuckles"],
    },
}

def clamp(n, lo, hi):
    return max(lo, min(hi, n))

def fmt_pct(p):
    if p >= 1:
        return f"{p:.0f}%"
    if p >= 0.1:
        return f"{p:.1f}%"
    if p >= 0.01:
        return f"{p:.2f}%"
    return f"{p:.3f}%"

def procedural_post35_names(rarity: str, weapon_type: str) -> List[str]:
    # Keeps it compact but still cool.
    themes = {
        "Omniscient": ["All-Seeing", "Oracle", "Mindforge", "Truthbound", "Seer"],
        "Voidbound": ["Void", "Null", "Abyss", "Blackstar", "Grave"],
        "Sovereign": ["Crown", "Regal", "Imperial", "Throne", "Sovereign"],
        "Apex": ["Apex", "Peak", "Summit", "Zenith", "Prime"],
        "Paradox": ["Paradox", "Loop", "Inverse", "Rift", "Fracture"],
    }
    forms = {
        "Sword": ["Blade", "Saber", "Edge", "Oathblade", "Longsword"],
        "Axe": ["Cleaver", "Reaver", "Axe", "Chopper", "Hatchet"],
        "Hammer": ["Maul", "Hammer", "Crusher", "Cataclysm", "Breaker"],
        "Spear": ["Pike", "Lance", "Spear", "Needle", "Skyspike"],
        "Bow": ["Longbow", "Recurve", "Bow", "Stringbow", "Arc Bow"],
        "Staff": ["Staff", "Rod", "Scepter", "Spire", "Wand"],
        "Gun": ["Rifle", "Carbine", "Blaster", "SMG", "Repeater"],
        "Gauntlets": ["Gauntlets", "Fists", "Grips", "Knuckles", "Wraps"],
    }
    t = themes.get(rarity, ["Apex"])
    f = forms.get(weapon_type, ["Weapon"])
    out = []
    for a in t[:3]:
        for b in f[:2]:
            out.append(f"{a} {b}")
    out.append(f"{rarity} {weapon_type}")
    return out

def name_pool_for(rarity: str, weapon_type: str) -> List[str]:
    if rarity in NAME_POOLS_BASE and weapon_type in NAME_POOLS_BASE[rarity]:
        return NAME_POOLS_BASE[rarity][weapon_type]
    return procedural_post35_names(rarity, weapon_type)

def rarity_weights_for_level_pre35(level: int) -> Dict[str, float]:
    level = clamp(level, 1, 35)
    w = {r: 0.0 for r in BASE_RARITIES}

    bands = [
        (1, 3,  "Common",     "Tempered",  None),
        (4, 7,  "Common",     "Tempered",  "Runed"),
        (8, 11, "Tempered",   "Runed",     "Arcane"),
        (12, 15, "Runed",     "Arcane",    "Eternal"),
        (16, 19, "Arcane",    "Eternal",   "Ascendant"),
        (20, 23, "Eternal",   "Ascendant", "Mythic"),
        (24, 27, "Ascendant", "Mythic",    "Divine"),
        (28, 30, "Mythic",    "Divine",    "Celestial"),
        (31, 33, "Divine",    "Celestial", "Primordial"),
        (34, 35, "Celestial", "Primordial","Transcendent"),
    ]

    for (a, b, main, second, third) in bands:
        if a <= level <= b:
            t = 1.0 if a == b else (level - a) / (b - a)

            main_start, main_end = 90.0, 78.0
            second_start, second_end = 9.0, 20.0
            third_start, third_end = 1.0, 2.5

            main_p = main_start + (main_end - main_start) * t
            second_p = second_start + (second_end - second_start) * t

            if third is None:
                third_p = 0.0
                second_p = 100.0 - main_p
            else:
                third_p = third_start + (third_end - third_start) * t
                total = main_p + second_p + third_p
                if total != 100.0:
                    scale = 100.0 / total
                    main_p *= scale
                    second_p *= scale
                    third_p *= scale

            w[main] = round(main_p, 3)
            w[second] = round(second_p, 3)
            if third:
                w[third] = round(third_p, 3)

            # Level 35 special split
            if level == 35:
                w = {r: 0.0 for r in BASE_RARITIES}
                w["Celestial"] = 64.0
                w["Primordial"] = 32.0
                w["Transcendent"] = 4.0
            return w

    w["Common"] = 100.0
    return w

def rarity_weights_for_level_post35(level: int) -> Dict[str, float]:
    """
    Post-35: still 3-tier "active band" style, but now using:
    Transcendent -> Omniscient -> Voidbound -> Sovereign -> Apex -> Paradox
    """
    level = clamp(level, 36, 100)
    w = {r: 0.0 for r in RARITIES_ALL}

    # Bands: (start, end, main, second, third)
    # Keep it smooth and not insane.
    bands = [
        (36, 45, "Transcendent", "Omniscient", "Voidbound"),
        (46, 60, "Omniscient", "Voidbound", "Sovereign"),
        (61, 75, "Voidbound", "Sovereign", "Apex"),
        (76, 90, "Sovereign", "Apex", "Paradox"),
        (91, 100, "Apex", "Paradox", "Paradox"),
    ]

    for (a, b, main, second, third) in bands:
        if a <= level <= b:
            t = 1.0 if a == b else (level - a) / (b - a)

            # main decreases, second increases, third rises slightly
            main_start, main_end = 88.0, 72.0
            second_start, second_end = 11.0, 24.0
            third_start, third_end = 1.0, 4.0

            main_p = main_start + (main_end - main_start) * t
            second_p = second_start + (second_end - second_start) * t
            third_p = third_start + (third_end - third_start) * t

            # Special: last band uses Paradox as both second+third; just fold into second
            if third == second:
                third_p = 0.0

            total = main_p + second_p + third_p
            scale = 100.0 / total
            main_p *= scale
            second_p *= scale
            third_p *= scale

            w[main] = round(main_p, 3)
            w[second] = round(second_p, 3)
            if third_p > 0.0 and third:
                w[third] = round(third_p, 3)
            return w

    # fallback
    w["Transcendent"] = 100.0
    return w

def rarity_weights_for_level(level: int, ascended: bool) -> Dict[str, float]:
    if not ascended:
        return rarity_weights_for_level_pre35(level)
    if level <= 35:
        # still use pre-35 for 35 itself
        base = rarity_weights_for_level_pre35(35)
        out = {r: 0.0 for r in RARITIES_ALL}
        for k, v in base.items():
            out[k] = v
        return out
    return rarity_weights_for_level_post35(level)

def pick_rarity(level: int, ascended: bool) -> str:
    weights = rarity_weights_for_level(level, ascended)
    names = [r for r in weights.keys() if weights[r] > 0]
    vals = [weights[r] for r in names]
    return random.choices(names, weights=vals, k=1)[0]

def roll_affixes(rarity: str) -> List[str]:
    idx = (RARITIES_ALL.index(rarity) + 1) if rarity in RARITIES_ALL else 1
    a, b = random.sample(AFFIX_POOL, 2)
    v1 = round(random.uniform(1.1, 2.4) * idx, 2)
    v2 = round(random.uniform(1.1, 2.4) * idx, 2)
    return [f"+{v1}% {a}", f"+{v2}% {b}"]

@dataclass
class Weapon:
    name: str
    rarity: str
    weapon_type: str
    damage: int
    affixes: List[str]

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_any_dict(d: dict) -> Optional["Weapon"]:
        # Old item format (armor) gets ignored; weapons-only
        if "slot" in d:
            if d.get("slot") != "Weapon":
                return None
            return Weapon(
                name=str(d.get("name", "Weapon")),
                rarity=str(d.get("rarity", "Common")),
                weapon_type=str(d.get("item_type", d.get("weapon_type", "Sword"))),
                damage=int(d.get("damage", 6)),
                affixes=list(d.get("affixes", [])),
            )
        if "weapon_type" in d:
            return Weapon(
                name=str(d.get("name", "Weapon")),
                rarity=str(d.get("rarity", "Common")),
                weapon_type=str(d.get("weapon_type", "Sword")),
                damage=int(d.get("damage", 6)),
                affixes=list(d.get("affixes", [])),
            )
        return None

def create_weapon(forge_level: int, ascended: bool, forced_rarity: Optional[str] = None) -> Weapon:
    rarity = forced_rarity if forced_rarity else pick_rarity(forge_level, ascended)
    wtype = random.choice(WEAPON_TYPES)

    if rarity == 'Beta':
        wtype = 'Beta'

    # Base damage scales with forge level; post-35 gives a stronger slope so "Battle 11 wall" disappears.
    if ascended and forge_level > 35:
        base = 12 + (35 * 9) + (forge_level - 35) * 18   # stronger slope after 35
    else:
        base = 12 + (forge_level * 9)

    dmg = int(base * RARITY_MULT.get(rarity, 1.0) * random.uniform(0.95, 1.08))
    name = random.choice(name_pool_for(rarity, wtype))
    affixes = roll_affixes(rarity)
    return Weapon(name=name, rarity=rarity, weapon_type=wtype, damage=dmg, affixes=affixes)

@dataclass
class RewardTimer:
    label: str
    reward_kind: str
    reward_amount: int
    current_seconds: int
    ready_at: float = 0.0

    def is_ready(self) -> bool:
        return time.time() >= self.ready_at

    def seconds_left(self) -> int:
        return max(0, int(self.ready_at - time.time()))

    def start(self):
        self.ready_at = time.time() + self.current_seconds
        self.current_seconds = min(self.current_seconds * 2, 600)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "reward_kind": self.reward_kind,
            "reward_amount": self.reward_amount,
            "current_seconds": self.current_seconds,
            "ready_at": self.ready_at,
        }

    @staticmethod
    def from_dict(d: dict) -> "RewardTimer":
        return RewardTimer(
            label=d["label"],
            reward_kind=d["reward_kind"],
            reward_amount=int(d["reward_amount"]),
            current_seconds=int(d["current_seconds"]),
            ready_at=float(d.get("ready_at", 0.0)),
        )

@dataclass
class BundleOffer:
    title: str
    wait_seconds: int
    reward_coins: int
    reward_gems: int
    reward_hammers: int
    weapon_rolls: int = 0
    guaranteed_rarity: Optional[str] = None

@dataclass
class PendingBundle:
    offer: BundleOffer
    ready_at: float

@dataclass
class PendingForgeLevelUp:
    target_level: int
    ready_at: float

@dataclass
class PlayerState:
    forge_level: int = 1
    hammers: int = 80
    coins: int = 400
    gems: int = 35

    # Hidden endgame currency
    tickets: int = 0

    # Rebirth + Storage
    rebirths: int = 0
    storage: List[Weapon] = field(default_factory=list)

    inventory: List[Weapon] = field(default_factory=list)
    equipped_idx: Optional[int] = None

    world: int = 1
    stage: int = 1

    player_max_hp: int = 120
    player_hp: int = 120

    auto_forge: bool = False
    auto_ms: int = 250
    auto_equip: bool = False

    rewards: Dict[str, RewardTimer] = field(default_factory=dict)
    used_codes: List[str] = field(default_factory=list)

    pending_levelup: Optional[PendingForgeLevelUp] = None

    # Hidden unlock at 35
    ascended_unlocked: bool = False
    # Once unlocked, Ascension stays available even after rebirth resets forge level
    ascension_unlocked: bool = False

    # Quests (easy, friendly)
    quests: List[dict] = field(default_factory=list)

    # Battle pass (offline alpha)
    bp_tier: int = 1
    bp_xp: int = 0
    bp_claimed_tiers: List[int] = field(default_factory=list)


    
    # Terms of Service / License agreement
    tos_accepted: bool = False
    tos_accepted_version: str = ""

    # Settings
    fullscreen: bool = False

    def equipped_weapon(self) -> Optional[Weapon]:
        if self.equipped_idx is None:
            return None
        if 0 <= self.equipped_idx < len(self.inventory):
            return self.inventory[self.equipped_idx]
        return None

    # --- Tournaments (offline bots) ---
    tournaments_unlocked: bool = False
    tourn_points: int = 0
    tourn_season_end: float = 0.0
    tourn_last_reset: float = 0.0
    tourn_bots: list = field(default_factory=list)

class ForgeBattlerApp:
    BG = "#0E1117"
    PANEL = "#1A1F2B"
    PANEL2 = "#222938"
    TEXT = "#E5E7EB"
    SUB = "#AAB2C0"
    BORDER = "#364152"

    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1360x880")
        self.root.minsize(1180, 720)
        self.root.configure(bg=self.BG)

        self.state = PlayerState()

        # Track recent forged items for UI (most recent first)
        self.last_forged: List[str] = []
        self.state.rewards = {
            "coin": RewardTimer("Coin Crate", "coins", 400, 30),
            "gem": RewardTimer("Gem Drip", "gems", 40, 60),
            "hammer": RewardTimer("Hammer Box", "hammers", 25, 90),
        }

        self.last_seen = time.time()
        self.enemy_name = random.choice(ENEMIES)
        self.enemy_max_hp = 100
        self.enemy_hp = 100
        self.enemy_damage = 6

        self.enemy_phase = 0
        self.damage_popup = None

        self.toast_text = ""
        self.toast_until = 0.0

        self.selected_idx: Optional[int] = None
        self.inventory_scroll = 0
        self.rarity_scroll = 0
        self.shop_window = None
        self.rarity_window = None
        self.dungeon_window = None

        self.auto_job = None

        self.bundle_offers: List[BundleOffer] = []
        self.pending_bundless: List[PendingBundle] = []

        self._load_converted_armor_coins = 0
        self.load_game()

        # Initialize quests / battle pass if missing
        if not getattr(self.state, "quests", None):
            self.state.quests = make_daily_quests()
        if not hasattr(self.state, "bp_tier"):
            self.state.bp_tier = 1
        if not hasattr(self.state, "bp_xp"):
            self.state.bp_xp = 0
        # Battle Pass config (ensure windows render)
        if not hasattr(self.state, "bp_xp_needed"):
            self.state.bp_xp_needed = BP_XP_PER_TIER
        if not hasattr(self.state, "bp_premium"):
            self.state.bp_premium = False
        if not hasattr(self.state, "bp_tiers"):
            tiers = []
            max_tier = max(BP_REWARDS.keys()) if BP_REWARDS else 20
            for t in range(1, max(20, max_tier) + 1):
                rw = BP_REWARDS.get(t, {"type": "currency", "coins": 250 * t})
                tiers.append({"tier": t, "reward": rw, "claimed_free": False, "claimed_premium": False})
            self.state.bp_tiers = tiers
        if not hasattr(self.state, "bp_claimed_tiers"):
            self.state.bp_claimed_tiers = []

        # If player is already 35+, unlock endgame
        if self.state.forge_level >= 35:
            self.state.ascended_unlocked = True
            self.state.ascension_unlocked = True

        self.recalc_player_stats(force_full=True)

        self.refresh_offers()

        self.canvas = tk.Canvas(root, bg=self.BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.handle_click)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel_main)
        self.click_regions: List[Tuple[int, int, int, int, callable]] = []
        self.battle_rect = (0, 0, 0, 0)

        self.root.bind("<Configure>", lambda e: self.render())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.setup_enemy_for_stage()

        # Boss rush (every 100 worlds at X10: 110, 210, 310, ...)
        self.boss_active = False
        self.boss_deadline = 0.0

        self.root.after(200, self.maybe_show_offline_rewards)

        if self._load_converted_armor_coins > 0:
            self.root.after(350, lambda: self.toast(f"Converted old armor into +{self._load_converted_armor_coins} coins (weapons-only now).", 3.0))

        # Start rendering immediately
        self.render()

        # Gate gameplay behind Terms of Service acceptance
        self._game_loop_started = False
        if bool(getattr(self.state, "tos_accepted", False)):
            self._start_game_loop()
        else:
            self.root.after(120, self.show_tos_dialog)

    # ---------- Toast ----------
    def toast(self, msg: str, seconds: float = 1.8):
        self.toast_text = str(msg)
        self.toast_until = time.time() + float(seconds)
        self.render()

    # ---------- Stat Scaling ----------
    # ---------- Quests + Battle Pass ----------
    def add_bp_xp(self, amount: int):
        if amount <= 0:
            return
        self.state.bp_xp = int(getattr(self.state, "bp_xp", 0)) + int(amount)
        while self.state.bp_xp >= BP_XP_PER_TIER:
            self.state.bp_xp -= BP_XP_PER_TIER
            self.state.bp_tier = int(getattr(self.state, "bp_tier", 1)) + 1
            self.toast(f"Battle Pass Tier Up! Tier {self.state.bp_tier}")

    def quest_add_progress(self, kind: str, amount: int = 1):
        if not getattr(self.state, "quests", None):
            return
        for q in self.state.quests:
            if q.get("claimed"):
                continue
            if q.get("kind") == kind:
                q["progress"] = int(q.get("progress", 0)) + int(amount)
        # no auto-claim; player claims manually

    def claim_quest(self, index: int):
        if not (0 <= index < len(self.state.quests)):
            return
        q = self.state.quests[index]
        if q.get("claimed"):
            return
        if int(q.get("progress", 0)) < int(q.get("target", 1)):
            self.toast("Quest not complete yet.")
            return

        q["claimed"] = True
        self.add_coins(int(q.get("coins", 0)))
        self.add_gems(int(q.get("gems", 0)))
        self.add_bp_xp(int(q.get("xp", 0)))
        self.toast("Quest claimed!")

        # Replace claimed quest with a new easy quest (keeps panel fresh)
        new_q = make_daily_quests(1)[0]
        self.state.quests[index] = new_q
        self.save_game()
        self.render()

    def bp_reward_for_tier(self, tier: int) -> dict:
        return BP_REWARDS.get(int(tier), {"type": "currency", "hammers": 50})

    def bp_claim_tier(self, tier: int):
        tier = int(tier)
        if tier in getattr(self.state, "bp_claimed_tiers", []):
            return
        if tier > int(getattr(self.state, "bp_tier", 1)):
            self.toast("Tier not reached yet.")
            return

        r = self.bp_reward_for_tier(tier)
        if r.get("type") == "weapon":
            # Create a special weapon (not in normal forge pools)
            dmg = int(r.get("base_dmg", 1000))
            # light scaling with forge level so it stays relevant
            dmg = int(dmg * (1.0 + (self.state.forge_level - 1) * 0.02))
            w = Weapon(
                name=r.get("name", "Battle Pass Weapon"),
                rarity=r.get("rarity", "Mythic"),
                weapon_type=r.get("weapon_type", "Sword"),
                damage=dmg,
                affixes=["Battle Pass Exclusive"]
            )
            self.state.inventory.insert(0, w)
            self.toast("Battle Pass weapon claimed!")
        else:
            self.add_hammers(int(r.get("hammers", 0)))
            self.add_coins(int(r.get("coins", 0)))
            self.add_gems(int(r.get("gems", 0)))
            self.toast("Battle Pass reward claimed!")

        self.state.bp_claimed_tiers.append(tier)
        self.save_game()
        self.render()

    def recalc_player_stats(self, force_full: bool = False):
        """
        Fixes the "120 HP forever" problem.
        Also keeps HP from snapping down weirdly unless forced.
        """
        lvl = self.state.forge_level
        # Strong but not crazy: gives thousands of HP at high forge.
        new_max = 120 + int((lvl ** 1.15) * 85)

        # Post-35 a little extra tankiness for dungeons
        if self.state.ascended_unlocked and lvl >= 35:
            new_max += int((lvl - 34) * 120)

        new_max = max(120, new_max)

        # Rebirth HP scaling
        new_max = int(new_max * self.rebirth_player_hp_mult())

        old_max = self.state.player_max_hp
        self.state.player_max_hp = new_max

        # Maintain % HP unless forced
        if force_full:
            self.state.player_hp = self.state.player_max_hp
        else:
            if old_max <= 0:
                self.state.player_hp = self.state.player_max_hp
            else:
                frac = self.state.player_hp / old_max
                self.state.player_hp = int(max(1, frac * self.state.player_max_hp))

    # ---------- Save / Load ----------
    def get_save_path(self) -> str:
        """Per-user save location (keeps saves out of the GitHub folder)."""
        # Windows: %APPDATA%\ForgeBattler\save.json
        # macOS/Linux: ~/.forgebattler/save.json
        try:
            base = os.environ.get("APPDATA")
            if base:
                root = Path(base) / "ForgeBattler"
            else:
                root = Path.home() / ".forgebattler"
        except Exception:
            root = Path(".")  # last resort

        try:
            root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        return str(root / "save.json")


    def save_game(self):
        try:
            data = {
                "forge_level": self.state.forge_level,
                "hammers": self.state.hammers,
                "coins": self.state.coins,
                "gems": self.state.gems,
                "tickets": self.state.tickets,
                "rebirths": int(getattr(self.state, "rebirths", 0)),
                "storage": [w.to_dict() for w in getattr(self.state, "storage", [])],
                "world": self.state.world,
                "stage": self.state.stage,
                "player_max_hp": self.state.player_max_hp,
                "player_hp": self.state.player_hp,
                "inventory": [w.to_dict() for w in self.state.inventory],
                "equipped_idx": self.state.equipped_idx,
                "auto_ms": self.state.auto_ms,
                "auto_equip": self.state.auto_equip,
                "rewards": {k: v.to_dict() for k, v in self.state.rewards.items()},
                "used_codes": list(self.state.used_codes),
                "last_seen": time.time(),
                "save_version": GAME_VERSION,
                "fullscreen": bool(getattr(self.state, "fullscreen", False)),
                "tos_accepted_version": str(getattr(self.state, "tos_accepted_version", "")),
                "tos_accepted": bool(getattr(self.state, "tos_accepted", False)),
                "pending_bundles": [
                    {
                        "offer": {
                            "title": pb.offer.title,
                            "wait_seconds": pb.offer.wait_seconds,
                            "reward_coins": pb.offer.reward_coins,
                            "reward_gems": pb.offer.reward_gems,
                            "reward_hammers": pb.offer.reward_hammers,
                            "weapon_rolls": pb.offer.weapon_rolls,
                            "guaranteed_rarity": pb.offer.guaranteed_rarity,
                        },
                        "ready_at": pb.ready_at,
                    }
                    for pb in self.pending_bundless
                ],
                "pending_levelup": None if self.state.pending_levelup is None else {
                    "target_level": self.state.pending_levelup.target_level,
                    "ready_at": self.state.pending_levelup.ready_at,
                },
                "ascended_unlocked": bool(self.state.ascended_unlocked),
                "ascension_unlocked": bool(getattr(self.state, "ascension_unlocked", False)),


                "tournaments_unlocked": bool(getattr(self.state, "tournaments_unlocked", False)),
                "quests": list(self.state.quests),
                "bp_tier": int(getattr(self.state, "bp_tier", 1)),
                "bp_xp": int(getattr(self.state, "bp_xp", 0)),
                "bp_claimed_tiers": list(getattr(self.state, "bp_claimed_tiers", [])),
            }
            os.makedirs(SAVE_DIR, exist_ok=True)
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def cleanup_beta_items(self):
        """Remove any legacy Beta items from older saves (Beta is disabled)."""
        def is_beta(w):
            return bool(w) and (getattr(w, "rarity", "") == "Beta" or getattr(w, "weapon_type", "") == "Beta")

        try:
            if is_beta(getattr(self.state, "equipped", None)):
                self.state.equipped = None
        except Exception:
            pass

        try:
            inv = getattr(self.state, "inventory", None)
            if inv:
                self.state.inventory = [w for w in inv if not is_beta(w)]
        except Exception:
            pass

        try:
            stor = getattr(self.state, "storage", None)
            if stor:
                self.state.storage = [w for w in stor if not is_beta(w)]
        except Exception:
            pass


    def load_game(self):
        # Ensure per-user save directory exists
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            # If we loaded from legacy path, migrate it into AppData
            try:
                if path == LEGACY_SAVE_PATH:
                    self.save_game()
            except Exception:
                pass

        except Exception:
            pass

        path = SAVE_PATH
        if not os.path.exists(path):
            # Legacy migration for the developer (public GitHub should NOT include legacy file)
            if os.path.exists(LEGACY_SAVE_PATH):
                path = LEGACY_SAVE_PATH
            else:
                return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.last_seen = float(data.get("last_seen", time.time()))

            self.state.forge_level = int(data.get("forge_level", self.state.forge_level))
            self.state.hammers = int(data.get("hammers", self.state.hammers))
            self.state.coins = int(data.get("coins", self.state.coins))
            self.state.gems = int(data.get("gems", self.state.gems))
            self.state.tickets = int(data.get("tickets", self.state.tickets))

            self.state.rebirths = int(data.get("rebirths", getattr(self.state, "rebirths", 0)))
            # Storage
            st = data.get("storage", [])
            stored: List[Weapon] = []
            if isinstance(st, list):
                for it in st:
                    if isinstance(it, dict):
                        w = Weapon.from_any_dict(it)
                        if w is None:
                            continue
                        if w.weapon_type not in WEAPON_TYPES:
                            w.weapon_type = "Sword"
                        if w.rarity not in RARITIES_ALL:
                            w.rarity = "Common"
                        stored.append(w)
            self.state.storage = stored

            self.state.world = int(data.get("world", self.state.world))
            self.state.stage = int(data.get("stage", self.state.stage))
            self.state.player_max_hp = int(data.get("player_max_hp", self.state.player_max_hp))
            self.state.player_hp = int(data.get("player_hp", self.state.player_hp))

            self.state.ascended_unlocked = bool(data.get("ascended_unlocked", False))
            self.state.ascension_unlocked = bool(data.get("ascension_unlocked", self.state.ascended_unlocked or self.state.forge_level >= 35))



            self.state.tournaments_unlocked = bool(data.get("tournaments_unlocked", self.state.forge_level >= 35))
            # Quests + Battle Pass (offline)
            self.state.quests = data.get("quests", []) or []
            self.state.bp_tier = int(data.get("bp_tier", getattr(self.state, "bp_tier", 1)))
            self.state.bp_xp = int(data.get("bp_xp", getattr(self.state, "bp_xp", 0)))
            self.state.bp_claimed_tiers = list(data.get("bp_claimed_tiers", getattr(self.state, "bp_claimed_tiers", []))) or []

            inv = data.get("inventory", [])
            weapons: List[Weapon] = []
            armor_coin_value = 0

            if isinstance(inv, list):
                for it in inv:
                    if not isinstance(it, dict):
                        continue
                    if "slot" in it and it.get("slot") != "Weapon":
                        try:
                            armor_coin_value += max(1, int(it.get("hp_bonus", 0)) // 3)
                        except Exception:
                            armor_coin_value += 1
                        continue

                    w = Weapon.from_any_dict(it)
                    if w is None:
                        continue
                    if w.weapon_type not in WEAPON_TYPES:
                        w.weapon_type = "Sword"
                    if w.rarity not in RARITIES_ALL:
                        w.rarity = "Common"
                    weapons.append(w)

            self.state.inventory = weapons
            if armor_coin_value > 0:
                self.state.coins += armor_coin_value
                self._load_converted_armor_coins = armor_coin_value

            eqi = data.get("equipped_idx", None)
            self.state.equipped_idx = None if eqi is None else int(eqi)
            if self.state.equipped_idx is not None and not (0 <= self.state.equipped_idx < len(self.state.inventory)):
                self.state.equipped_idx = None

            self.state.auto_ms = int(data.get("auto_ms", self.state.auto_ms))
            self.state.auto_equip = bool(data.get("auto_equip", self.state.auto_equip))

            rd = data.get("rewards", {})
            if isinstance(rd, dict) and rd:
                self.state.rewards = {k: RewardTimer.from_dict(v) for k, v in rd.items()}

            # --- Maintenance handling (version bump) ---
            prev_ver = str(data.get("save_version", "") or "")
            if prev_ver != GAME_VERSION:
                # Small "thanks for waiting" reward on update
                try:
                    self.state.hammers += int(MAINTENANCE_REWARD.get("hammers", 0))
                    self.state.coins += int(MAINTENANCE_REWARD.get("coins", 0))
                    self.state.gems += int(MAINTENANCE_REWARD.get("gems", 0))
                    self.state.tickets += int(MAINTENANCE_REWARD.get("tickets", 0))
                    self.toast("Maintenance reward claimed!")
                except Exception:
                    pass

                # Reset select codes on update (dev/testing convenience)
                try:
                    existing = [str(x).lower() for x in list(data.get("used_codes", []))]
                    existing = [x for x in existing if x not in RESETTABLE_CODES_ON_UPDATE]
                    data["used_codes"] = existing
                except Exception:
                    pass


            self.state.used_codes = list(data.get("used_codes", []))

            self.pending_bundless = []
            pbs = data.get("pending_bundles", [])
            if isinstance(pbs, list):
                for item in pbs[:3]:
                    try:
                        off = item.get("offer", {})
                        offer = BundleOffer(
                            title=off.get("title", "Bundle"),
                            wait_seconds=int(off.get("wait_seconds", 180)),
                            reward_coins=int(off.get("reward_coins", 0)),
                            reward_gems=int(off.get("reward_gems", 0)),
                            reward_hammers=int(off.get("reward_hammers", 0)),
                            weapon_rolls=int(off.get("weapon_rolls", 0)),
                            guaranteed_rarity=off.get("guaranteed_rarity", None),
                        )
                        self.pending_bundless.append(PendingBundle(offer=offer, ready_at=float(item.get("ready_at", time.time()))))
                    except Exception:
                        pass

            pl = data.get("pending_levelup", None)
            if pl and "target_level" in pl and "ready_at" in pl:
                self.state.pending_levelup = PendingForgeLevelUp(int(pl["target_level"]), float(pl["ready_at"]))
            else:
                self.state.pending_levelup = None

            if self.state.auto_equip and self.state.equipped_idx is None:
                bi = self.best_weapon_index()
                self.state.equipped_idx = bi if bi >= 0 else None

            # Normalize ascension unlock: once unlocked, it stays available after rebirth resets forge level
            if self.state.forge_level >= 35 or self.state.ascended_unlocked:
                self.state.ascension_unlocked = True

        except Exception:
            return
        self.cleanup_beta_items()

    def on_close(self):
        self.save_game()
        self.root.destroy()

    # ---------- Offline rewards ----------
    def maybe_show_offline_rewards(self):
        now = time.time()
        away = max(0, int(now - getattr(self, "last_seen", now)))
        if away < 30:
            return
        cap = 6 * 60 * 60
        away = min(away, cap)

        coins = int(away * 0.8)
        hammers = int(away * 0.05)
        gems = int(away / 600)

        if coins <= 0 and hammers <= 0 and gems <= 0:
            return
        self.offline_reward = (coins, hammers, gems, away)
        self.open_offline_popup()

    def open_offline_popup(self):
        coins, hammers, gems, away = getattr(self, "offline_reward", (0, 0, 0, 0))
        w = tk.Toplevel(self.root)
        w.title("Offline Rewards")
        w.geometry("520x320")
        w.configure(bg=self.BG)
        w.transient(self.root)
        w.resizable(False, False)

        c = tk.Canvas(w, bg=self.BG, highlightthickness=0)
        c.pack(fill="both", expand=True)

        c.create_rectangle(20, 20, 500, 300, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(260, 58, text="OFFLINE REWARDS", fill=self.TEXT, font=("Arial", 16, "bold"))
        c.create_text(260, 92, text=f"You were away for {away//60}m {away%60}s", fill=self.SUB, font=("Arial", 11, "bold"))

        c.create_text(260, 140, text=f"+{coins} coins", fill=self.TEXT, font=("Arial", 13, "bold"))
        c.create_text(260, 170, text=f"+{hammers} hammers", fill=self.TEXT, font=("Arial", 13, "bold"))
        c.create_text(260, 200, text=f"+{gems} gems", fill=self.TEXT, font=("Arial", 13, "bold"))

        def collect():
            self.add_coins(coins)
            self.add_hammers(hammers)
            self.add_gems(gems)
            try:
                w.destroy()
            except Exception:
                pass
            self.render()

        btn = tk.Button(w, text="Collect", command=collect, bg="#16A34A", fg="white", font=("Arial", 12, "bold"))
        c.create_window(260, 255, window=btn, width=180, height=38)

    # ---------- Battle / Stage ----------
    def difficulty(self) -> int:
        return (self.state.world - 1) * 10 + self.state.stage

    def setup_enemy_for_stage(self):
        d = self.difficulty()

        # Boss stage: every stage 10 (ex: 483-10). 5 seconds to kill or you drop back.
        is_boss_stage = (self.state.stage == 10)

        if is_boss_stage:
            self.boss_active = True
            self.boss_deadline = time.time() + 5.0  # 5 seconds to kill
            self.enemy_type = random.choice(ENEMIES)
            self.enemy_name = f"BOSS • {self.enemy_type}"
            # Boss stats: chunky HP, higher damage
            self.enemy_max_hp = int((120 + d * 60) * 2.4)
            self.enemy_hp = self.enemy_max_hp
            self.enemy_damage = int((8 + d * 3) * 1.6)
        else:
            self.boss_active = False
            self.boss_deadline = 0.0
            self.enemy_type = random.choice(ENEMIES)
            self.enemy_name = self.enemy_type
            self.enemy_max_hp = 80 + d * 42
            self.enemy_hp = self.enemy_max_hp
            self.enemy_damage = 5 + d * 2


        # Rebirth scaling (enemies get stronger)
        self.enemy_max_hp = int(self.enemy_max_hp * self.rebirth_enemy_hp_mult())
        self.enemy_hp = self.enemy_max_hp
        self.enemy_damage = int(self.enemy_damage * self.rebirth_enemy_dmg_mult())

    def advance_stage(self):
        if self.state.stage < 10:
            self.state.stage += 1
        else:
            self.state.world += 1
            self.state.stage = 1
        self.setup_enemy_for_stage()
        self.refresh_offers()

    def rollback_stage(self):
        if self.state.world == 1 and self.state.stage == 1:
            return
        if self.state.stage > 1:
            self.state.stage -= 1
        else:
            self.state.world = max(1, self.state.world - 1)
            self.state.stage = 10
        self.setup_enemy_for_stage()
        self.refresh_offers()

    # ---------- Combat ----------
    def current_damage(self):
        eq = self.state.equipped_weapon()
        base = (eq.damage if eq else 6)
        return int(base * self.rebirth_player_dmg_mult())

    def player_attack(self, multiplier: float = 1.0):
        dmg = int(self.current_damage() * multiplier)
        self.enemy_hp -= dmg
        self.damage_popup = [str(dmg), 935, 240, 12]
        self.enemy_phase = 6

        if self.enemy_hp <= 0:
            d = self.difficulty()

            if getattr(self, "boss_active", False):
                # Boss clear rewards
                self.boss_active = False
                self.boss_deadline = 0.0
                self.add_gems(150)
                self.add_coins(5000)
                self.add_hammers(250 + (d * 2))
                # Tickets are dungeon-focused, but small boss bonus feels good
                if hasattr(self.state, "tickets"):
                    self.add_tickets(40)
                self.toast("BOSS CLEARED! +150💎 +5000🪙 +hammers")
                self.quest_add_progress("beat_boss", 1)
            else:
                self.add_coins(18 + d * 3)
                self.add_gems(1 + (d // 20))
                self.add_hammers(3 + (d // 3))

            self.quest_add_progress("win_battles", 1)
            self.advance_stage()

    def enemy_attack(self):
        self.state.player_hp -= self.enemy_damage
        if self.state.player_hp <= 0:
            self.recalc_player_stats(force_full=True)
            self.rollback_stage()

    # ---------- Forging ----------
    def best_weapon_index(self) -> int:
        if not self.state.inventory:
            return -1
        best_i = 0
        best_d = self.state.inventory[0].damage
        for i, w in enumerate(self.state.inventory):
            if w.damage > best_d:
                best_d = w.damage
                best_i = i
        return best_i

    def forge_once(self):
        global inv_scroll_index
        if self.state.hammers < 1:
            self.toast("No hammers. Go SHOP → Exchanges.")
            return None

        self.state.hammers -= 1

        if self.state.equipped_idx is not None:
            self.state.equipped_idx += 1

        weapon = create_weapon(self.state.forge_level, self.state.ascended_unlocked)
        self.state.inventory.insert(0, weapon)
        # Tournament points from forging (rarity-weighted)
        try:
            r = getattr(weapon, 'rarity', 'Common')
            pts_map = {'Common': 1, 'Uncommon': 2, 'Rare': 4, 'Epic': 8, 'Legendary': 16, 'Mythic': 32, 'Beta': 40}
            self.award_tourn_points(pts_map.get(str(r), 1), 'forge')
        except Exception:
            pass
        self.quest_add_progress("forge_items", 1)

        # Keep "newest forged" visible + selected
        inv_scroll_index = 0
        self.selected_idx = 0

        # Track recent forged for UI (optional)
        try:
            self.last_forged.insert(0, weapon.name)
            self.last_forged = self.last_forged[:5]
        except Exception:
            pass

        if self.state.auto_equip:
            bi = self.best_weapon_index()
            self.state.equipped_idx = bi if bi >= 0 else None

        self.render()
        return weapon

    def toggle_auto_equip(self):
        self.state.auto_equip = not self.state.auto_equip
        if self.state.auto_equip:
            bi = self.best_weapon_index()
            self.state.equipped_idx = bi if bi >= 0 else None
            self.toast("AUTO EQUIP: ON")
        else:
            self.toast("AUTO EQUIP: OFF")
        self.render()

    def auto_forge_toggle(self):
        self.state.auto_forge = not self.state.auto_forge
        if self.state.auto_forge:
            self.toast("AUTO FORGE: ON")
            self.run_auto_forge()
        else:
            if self.auto_job:
                try:
                    self.root.after_cancel(self.auto_job)
                except Exception:
                    pass
                self.auto_job = None
            self.toast("AUTO FORGE: OFF")
        self.render()

    def run_auto_forge(self):
        if not self.state.auto_forge:
            return
        if self.state.hammers <= 0:
            self.state.auto_forge = False
            self.auto_job = None
            self.toast("Out of hammers. Auto-forge stopped.")
            self.render()
            return
        self.forge_once()
        self.auto_job = self.root.after(self.state.auto_ms, self.run_auto_forge)

    # ---------- SELL ALL ----------
    def sell_all_unequipped(self):
        if not self.state.inventory:
            self.toast("Inventory empty.")
            return

        eqi = self.state.equipped_idx
        kept = None
        if eqi is not None and 0 <= eqi < len(self.state.inventory):
            kept = self.state.inventory[eqi]

        total = 0
        sold = 0
        new_inv = []
        for i, w in enumerate(self.state.inventory):
            if kept is not None and w is kept:
                new_inv.append(w)
                continue
            total += max(1, w.damage // 4)
            sold += 1

        self.state.inventory = new_inv
        self.state.coins += total

        # re-find equipped index
        if kept is None:
            self.state.equipped_idx = None
        else:
            self.state.equipped_idx = 0

        self.selected_idx = 0 if self.state.inventory else None
        if sold:
            self.quest_add_progress("sell_items", sold)
        self.toast(f"Sold {sold} weapons for +{total} coins.")
        self.render()

    # ---------- Forge Level Up + Gem Skip ----------

        # Tournament points from selling
        try:
            sold = int(locals().get('sold_count', 0)) if 'sold_count' in locals() else 0
            if sold <= 0:
                sold = 1
            self.award_tourn_points(max(1, sold // 2), 'sell')
        except Exception:
            pass
    def forge_level_cap_visible(self) -> int:
        # Players below 35 only ever see 35. Post-35: they see 100.
        return 100 if self.state.ascended_unlocked else 35

    def storage_limit(self) -> int:
        # Base 1 slot, +1 per rebirth
        return 1 + int(getattr(self.state, "rebirths", 0))

    def rebirth_count(self) -> int:
        return int(getattr(self.state, "rebirths", 0))

    def rebirth_player_dmg_mult(self) -> float:
        R = self.rebirth_count()
        return 1.0 + (R * 0.10)

    def rebirth_player_hp_mult(self) -> float:
        R = self.rebirth_count()
        return 1.0 + (R * 0.14)

    def rebirth_enemy_hp_mult(self) -> float:
        R = self.rebirth_count()
        return 1.0 + (R * 0.17)

    def rebirth_enemy_dmg_mult(self) -> float:
        R = self.rebirth_count()
        return 1.0 + (R * 0.11)

    def rebirth_hammer_mult(self) -> float:
        R = self.rebirth_count()
        return max(0.40, 1.0 - (R * 0.05))

    def rebirth_coin_mult(self) -> float:
        R = self.rebirth_count()
        return max(0.50, 1.0 - (R * 0.04))

    def rebirth_gem_mult(self) -> float:
        R = self.rebirth_count()
        return max(0.60, 1.0 - (R * 0.03))

    def rebirth_ticket_mult(self) -> float:
        R = self.rebirth_count()
        return 1.0 + (R * 0.16)

    def add_coins(self, amount: int):
        self.state.coins += int(max(0, amount) * self.rebirth_coin_mult())

    def add_hammers(self, amount: int):
        self.state.hammers += int(max(0, amount) * self.rebirth_hammer_mult())

    def add_gems(self, amount: int):
        self.state.gems += int(max(0, amount) * self.rebirth_gem_mult())

    def add_tickets(self, amount: int):
        if not hasattr(self.state, "tickets"):
            return
        self.state.tickets += int(max(0, amount) * self.rebirth_ticket_mult())
    def forge_levelup_cost(self, level: int) -> int:
        """
        Keep costs reasonable for new players.
        Post-35 grows smoothly, not insane.

        Rebirth makes leveling progressively more expensive (prestige loop),
        without deleting your items/currencies.
        """
        if level < 35:
            cost = 650 + (level ** 2) * 38
        else:
            # Post-35: smooth linear-ish growth
            base = 650 + (35 ** 2) * 38
            extra = int((level - 35) * 1800 + (level - 35) ** 1.15 * 700)
            cost = base + max(0, extra)

        R = int(getattr(self.state, "rebirths", 0))
        # +12% per rebirth makes late-game prestiges feel meaningfully harder
        cost = int(cost * (1.0 + (R * 0.12)))
        return max(1, cost)

    def forge_levelup_wait(self, level: int) -> int:
        """
        Keep the same pre-35 timing.
        Post-35: still wait-based, but slightly heavier.
        """
        if level <= 35:
            level = clamp(level, 1, 35)
            if level <= 5:
                return int(8 + level * 6)
            if level <= 10:
                return int(60 + (level - 5) * 90)
            if level <= 15:
                return int(10 * 60 + (level - 10) * 20 * 60)
            if level <= 20:
                return int(2 * 60 * 60 + (level - 15) * 4 * 60 * 60)
            return int(1 * 24 * 60 * 60 + (level - 20) * 1.2 * 24 * 60 * 60)

        # Post-35: 10m -> 2h range
        over = level - 35
        return clamp(int(10 * 60 + over * 90), 10 * 60, 2 * 60 * 60)

    def forge_levelup_skip_cost(self, current_level: int, secs_left: int) -> int:
        current_level = max(1, int(current_level))
        secs_left = max(0, int(secs_left))

        # Pre-35 tuning (cheap-ish)
        if current_level <= 10:
            return clamp(int(math.ceil(secs_left / 15)), 5, 120)
        if current_level <= 15:
            return clamp(40 + int(math.ceil(secs_left / 120)), 60, 260)
        if current_level <= 20:
            return clamp(120 + int(math.ceil(secs_left / 900)), 180, 800)
        if current_level <= 35:
            return clamp(300 + int(math.ceil(secs_left / 7200)), 400, 2500)

        # Post-35: still spendy, but you're rich
        return clamp(600 + int(math.ceil(secs_left / 900)), 800, 6000)

    def start_level_up(self):
        cap = self.forge_level_cap_visible()
        if self.state.forge_level >= cap:
            self.toast("Max visible level reached.")
            return
        if self.state.pending_levelup is not None:
            self.toast("Already leveling.")
            return

        cost = self.forge_levelup_cost(self.state.forge_level)
        if self.state.coins < cost:
            self.toast("Not enough coins to level up.")
            return

        self.state.coins -= cost
        wait_s = self.forge_levelup_wait(self.state.forge_level)
        self.state.pending_levelup = PendingForgeLevelUp(
            target_level=self.state.forge_level + 1,
            ready_at=time.time() + wait_s
        )
        self.render()

    def finish_level_up_now(self):
        pl = self.state.pending_levelup
        if pl is None:
            return
        secs_left = max(0, int(pl.ready_at - time.time()))
        cost = self.forge_levelup_skip_cost(self.state.forge_level, secs_left)
        if self.state.gems < cost:
            self.toast("Not enough gems to skip.")
            return
        self.state.gems -= cost

        cap = 100 if self.state.ascended_unlocked else 35
        self.state.forge_level = min(cap, pl.target_level)
        self.state.pending_levelup = None

        # unlock ascension if reached 35
        if self.state.forge_level >= 35:
            if not self.state.ascended_unlocked:
                self.state.ascended_unlocked = True
                self.state.ascension_unlocked = True
                self.toast("ENDGAME UNLOCKED: Dungeons + Forge 36-100!", 3.0)

        self.recalc_player_stats(force_full=True)
        self.refresh_offers()
        self.render()
    def open_rebirth(self):
        if not (self.state.ascended_unlocked and self.forge_level_cap_visible() == 100 and self.state.forge_level >= 100):
            self.toast("Rebirth unlocks at Forge Level 100.")
            return
        if int(getattr(self.state, "rebirths", 0)) >= 45:
            self.toast("Max rebirths reached (45).")
            return

        win = tk.Toplevel(self.root)
        win.title("Rebirth")
        win.geometry("760x520")
        win.configure(bg=self.BG)
        win.transient(self.root)

        next_r = int(getattr(self.state, "rebirths", 0)) + 1
        next_limit = 1 + next_r

        tk.Label(win, text=f"REBIRTH ⭐ {next_r} (max 45)", bg=self.BG, fg=self.TEXT,
                 font=("Arial", 16, "bold")).pack(pady=10)

        msg = f"""Rebirth resets your Forge Level and battle progress,
but permanently boosts your account and increases Storage slots.

After rebirth, Storage limit becomes: {next_limit} slots.

You may choose ONE item to store before your inventory is wiped."""

        tk.Label(win, text=msg, bg=self.BG, fg=self.SUB, justify="left",
                 font=("Arial", 11)).pack(pady=6)

        box = tk.Frame(win, bg=self.BG)
        box.pack(fill="both", expand=True, padx=12, pady=10)

        lb = tk.Listbox(box, font=("Arial", 11), bg="#0B0F15", fg=self.TEXT, selectbackground="#2563EB",
                        activestyle="none")
        sb = tk.Scrollbar(box, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for it in self.state.inventory:
            try:
                lb.insert("end", f"{it.name}  •  {it.rarity} {it.weapon_type}  •  DMG {('???' if getattr(it,'rarity','')=='Beta' else it.damage)}")
            except Exception:
                lb.insert("end", str(it))

        btn_row = tk.Frame(win, bg=self.BG)
        btn_row.pack(pady=10)

        def do_rebirth_now():
            keep_idx = None
            try:
                sel = lb.curselection()
                if sel:
                    keep_idx = int(sel[0])
            except Exception:
                keep_idx = None

            self.perform_rebirth(keep_idx)
            try:
                win.destroy()
            except Exception:
                pass

        tk.Button(btn_row, text="CONFIRM REBIRTH", command=do_rebirth_now,
                  bg="#F59E0B", fg="black", font=("Arial", 12, "bold"), relief="flat",
                  padx=18, pady=10).pack(side="left", padx=8)

        tk.Button(btn_row, text="CANCEL", command=lambda: win.destroy(),
                  bg="#374151", fg="white", font=("Arial", 12, "bold"), relief="flat",
                  padx=18, pady=10).pack(side="left", padx=8)

    def perform_rebirth(self, keep_inventory_index: Optional[int] = None):
        # Prestige without deleting your account progress:
        # - Keep currencies, inventory, equipped, used codes, storage
        # - Reset forge level progression + battle progression
        self.state.rebirths = int(getattr(self.state, "rebirths", 0)) + 1
        if self.state.rebirths > 45:
            self.state.rebirths = 45

        if not hasattr(self.state, "storage") or self.state.storage is None:
            self.state.storage = []

        # Optional: move exactly one item into permanent storage each rebirth
        if keep_inventory_index is not None and (0 <= keep_inventory_index < len(self.state.inventory)):
            item = self.state.inventory.pop(keep_inventory_index)

            # Fix indices after pop
            if self.state.equipped_idx is not None:
                if self.state.equipped_idx == keep_inventory_index:
                    self.state.equipped_idx = None
                elif self.state.equipped_idx > keep_inventory_index:
                    self.state.equipped_idx -= 1
            if self.selected_idx is not None:
                if self.selected_idx == keep_inventory_index:
                    self.selected_idx = None
                elif self.selected_idx > keep_inventory_index:
                    self.selected_idx -= 1

            self.state.storage.append(item)

        # Reset progression loop (but keep your stuff)
        self.state.forge_level = 1
        self.state.world = 1
        self.state.stage = 1

        # Clear timers/automation that could glitch after prestige
        self.state.pending_levelup = None
        self.state.auto_forge = False

        self.recalc_player_stats(force_full=True)
        self.setup_enemy_for_stage()

        self.save_game()
        self.toast(f"REBIRTH COMPLETE ⭐ {self.state.rebirths}")
        self.render()


    def apply_pending_levelup_if_ready(self):
        pl = self.state.pending_levelup
        if pl is None:
            return
        if time.time() >= pl.ready_at:
            cap = 100 if self.state.ascended_unlocked else 35
            old_level = int(getattr(self.state, 'forge_level', 1))
            self.state.forge_level = min(cap, pl.target_level)
            # Tournament points from leveling up (only when the level actually increases)
            try:
                new_level = int(getattr(self.state, 'forge_level', old_level))
                if new_level > old_level:
                    self.award_tourn_points((new_level - old_level) * 8, 'level up')
            except Exception:
                pass
            self.state.pending_levelup = None

            if self.state.forge_level >= 35 and not self.state.ascended_unlocked:
                self.state.ascended_unlocked = True
                self.state.ascension_unlocked = True
                self.toast("ENDGAME UNLOCKED: Dungeons + Forge 36-100!", 3.0)

            self.recalc_player_stats(force_full=True)
            self.refresh_offers()
            self.render()

    # ---------- Inventory actions ----------
    def equip_selected(self):
        old = getattr(self.state, 'equipped_idx', None)
        if self.selected_idx is None:
            return
        if 0 <= self.selected_idx < len(self.state.inventory):
            if self.state.equipped_idx == self.selected_idx:
                self.state.equipped_idx = None
            else:
                self.state.equipped_idx = self.selected_idx
            self.render()

        try:
            new = getattr(self.state, 'equipped_idx', None)
            if new != old:
                self.award_tourn_points(3, 'equip')
        except Exception:
            pass
    def sell_selected(self):
        if self.selected_idx is None:
            return
        if 0 <= self.selected_idx < len(self.state.inventory):
            if self.state.equipped_idx == self.selected_idx:
                self.toast("Can't sell equipped weapon.")
                return
            weapon = self.state.inventory.pop(self.selected_idx)
            self.quest_add_progress("sell_items", 1)
            self.state.coins += max(1, weapon.damage // 4)

            if self.state.equipped_idx is not None:
                if self.selected_idx < self.state.equipped_idx:
                    self.state.equipped_idx -= 1

            if not self.state.inventory:
                self.selected_idx = None
            else:
                self.selected_idx = min(self.selected_idx, len(self.state.inventory) - 1)
            self.render()

    # ---------- Shop / Bundles ----------
    def refresh_offers(self):
        fl = self.state.forge_level
        d = self.difficulty()

        def scale(n):
            # Keep it friendly; scales with forge but not exploding.
            return int(n * (1.0 + min(fl, 35) * 0.08 + d * 0.02))

        offers = []
        offers.append(BundleOffer("Forge Cache", 180, scale(1500), scale(40), scale(120), weapon_rolls=5))
        offers.append(BundleOffer("Hunter Cache", 360, scale(4500), scale(120), scale(320), weapon_rolls=10))

        # If ascended, let this guarantee a post-35 rarity sometimes
        if self.state.ascended_unlocked and fl >= 60:
            offers.append(BundleOffer("Apex Trial Cache", 600, scale(12000), scale(420), scale(1400), weapon_rolls=1, guaranteed_rarity="Apex"))
        elif fl >= 16:
            offers.append(BundleOffer("Divine Trial Cache", 600, scale(9000), scale(300), scale(900), weapon_rolls=1, guaranteed_rarity="Divine"))
        else:
            offers.append(BundleOffer("Ascendant Trial Cache", 600, scale(9000), scale(280), scale(900), weapon_rolls=1, guaranteed_rarity="Ascendant"))

        self.bundle_offers = offers
    def store_selected(self):
        if self.selected_idx is None:
            return
        if not (0 <= self.selected_idx < len(self.state.inventory)):
            return

        if not hasattr(self.state, "storage") or self.state.storage is None:
            self.state.storage = []

        limit = self.storage_limit()
        if len(self.state.storage) >= limit:
            self.toast(f"Storage full ({len(self.state.storage)}/{limit}). Rebirth to unlock more slots.")
            return

        w = self.state.inventory.pop(self.selected_idx)

        if self.state.equipped_idx == self.selected_idx:
            self.state.equipped_idx = None
        elif self.state.equipped_idx is not None and self.state.equipped_idx > self.selected_idx:
            self.state.equipped_idx -= 1

        self.state.storage.append(w)

        if self.state.inventory:
            self.selected_idx = min(self.selected_idx, len(self.state.inventory) - 1)
        else:
            self.selected_idx = None

        self.save_game()
        self.toast(f"Stored: {w.name}  ({len(self.state.storage)}/{limit})")
        self.render()

    def open_storage(self):
        if not hasattr(self.state, "storage") or self.state.storage is None:
            self.state.storage = []

        if getattr(self, "storage_window", None) and self.storage_window.winfo_exists():
            self.storage_window.lift()
            self.render_storage_window()
            return

        self.storage_window = tk.Toplevel(self.root)
        self.storage_window.title("Storage Vault")
        self.storage_window.geometry("760x520")
        self.storage_window.configure(bg=self.BG)
        self.storage_window.transient(self.root)

        self.render_storage_window()

    def render_storage_window(self):
        if not getattr(self, "storage_window", None) or not self.storage_window.winfo_exists():
            return
        w = self.storage_window
        for child in list(w.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

        limit = self.storage_limit()

        title = tk.Label(w, text=f"STORAGE  ({len(self.state.storage)}/{limit})", bg=self.BG, fg=self.TEXT,
                         font=("Arial", 14, "bold"))
        title.pack(pady=10)

        frame = tk.Frame(w, bg=self.BG)
        frame.pack(fill="both", expand=True, padx=12, pady=8)

        lb = tk.Listbox(frame, font=("Arial", 11), bg="#0B0F15", fg=self.TEXT, selectbackground="#2563EB",
                        activestyle="none")
        sb = tk.Scrollbar(frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for it in self.state.storage:
            try:
                lb.insert("end", f"{it.name}  •  {it.rarity} {it.weapon_type}  •  DMG {('???' if getattr(it,'rarity','')=='Beta' else it.damage)}")
            except Exception:
                lb.insert("end", str(it))

        btn_row = tk.Frame(w, bg=self.BG)
        btn_row.pack(pady=10)

        def restore_selected():
            try:
                sel = lb.curselection()
                if not sel:
                    return
                idx = int(sel[0])
            except Exception:
                return
            if not (0 <= idx < len(self.state.storage)):
                return

            item = self.state.storage.pop(idx)
            self.state.inventory.insert(0, item)
            self.selected_idx = 0
            self.save_game()
            self.toast("Restored item to inventory.")
            self.render()
            self.render_storage_window()

        tk.Button(btn_row, text="RESTORE TO INVENTORY", command=restore_selected,
                  bg="#16A34A", fg="white", font=("Arial", 11, "bold"), relief="flat",
                  padx=16, pady=8).pack(side="left", padx=8)

        tk.Button(btn_row, text="CLOSE", command=lambda: w.destroy(),
                  bg="#374151", fg="white", font=("Arial", 11, "bold"), relief="flat",
                  padx=16, pady=8).pack(side="left", padx=8)


    def start_bundle(self, idx: int):
        if len(self.pending_bundless) >= 3:
            return
        offer = self.bundle_offers[idx]
        self.pending_bundless.append(PendingBundle(offer=offer, ready_at=time.time() + offer.wait_seconds))
        self.render_shop()

    def claim_bundle(self, idx: int = 0):
        if not self.pending_bundless:
            return
        idx = clamp(idx, 0, len(self.pending_bundless) - 1)
        pb = self.pending_bundless[idx]
        if time.time() < pb.ready_at:
            return
        offer = pb.offer

        self.add_coins(offer.reward_coins)
        self.add_gems(offer.reward_gems)
        self.add_hammers(offer.reward_hammers)

        if offer.weapon_rolls > 0:
            for i in range(offer.weapon_rolls):
                forced = offer.guaranteed_rarity if (offer.guaranteed_rarity and i == 0) else None
                w = create_weapon(self.state.forge_level, self.state.ascended_unlocked, forced_rarity=forced)
                if self.state.equipped_idx is not None:
                    self.state.equipped_idx += 1
                self.state.inventory.insert(0, w)

            if self.selected_idx is None:
                self.selected_idx = 0
            if self.state.auto_equip:
                bi = self.best_weapon_index()
                self.state.equipped_idx = bi if bi >= 0 else None

        try:
            self.pending_bundless.pop(idx)
        except Exception:
            self.pending_bundless = []

        self.refresh_offers()
        self.render_shop()
        self.render()

    def claim_reward(self, key: str):
        rt = self.state.rewards[key]
        if not rt.is_ready():
            return
        if rt.reward_kind == "coins":
            self.state.coins += rt.reward_amount
        elif rt.reward_kind == "gems":
            self.state.gems += rt.reward_amount
        elif rt.reward_kind == "hammers":
            self.state.hammers += rt.reward_amount
        rt.start()
        self.render_shop()
        self.render()

    def exchange_buy_hammer_with_coins(self):
        cost = 350
        if self.state.coins >= cost:
            self.state.coins -= cost
            self.state.hammers += 1
            self.render_shop()
            self.render()

    def exchange_buy_hammers_with_gems(self):
        cost = 100
        if self.state.gems >= cost:
            self.state.gems -= cost
            self.state.hammers += 5
            self.render_shop()
            self.render()

    def exchange_buy_coins_with_gems(self):
        cost = 250
        if self.state.gems >= cost:
            self.state.gems -= cost
            self.state.coins += 3500
            self.render_shop()
            self.render()

    def redeem_code(self, code: str) -> str:
            raw = (code or "").strip()
            if not raw:
                return "Enter a code."
            key = raw.lower()

            used = set(getattr(self.state, "used_codes", []))
            if key in used:
                return "Code already used."

            # Codes (keep hidden in UI so you can promote them yourself)
            codes = {
                "ayysoul": {"type": "curr", "coins": 10000, "gems": 500, "hammers": 3000},
                "beta": {"type": "weapon"},
            }

            if key not in codes:
                return "Invalid code."

            # Limited-time BETA code
            if key == "beta":
                return "Beta is currently disabled."

            # mark used + save
            try:
                self.state.used_codes.append(key)
            except Exception:
                pass
            self.save_state()

            return "Code redeemed."

    def dungeon_refresh_loop(self):
        if self.dungeon_window and self.dungeon_window.winfo_exists():
            self.render_dungeons()
            self.dungeon_window.after(250, self.dungeon_refresh_loop)

    def dungeon_btn(self, c, x, y, w, h, text, fill, action):
        rect = c.create_rectangle(x, y, x + w, y + h, fill=fill, outline="#0A0D13", width=2)
        txt = c.create_text(x + w / 2, y + h / 2, text=text, fill="white", font=("Arial", 11, "bold"))
        for item in (rect, txt):
            c.tag_bind(item, "<Button-1>", lambda e, fn=action: fn())

    def start_dungeon(self, kind: str):
        if self.dungeon_running:
            return

        # Entry costs (tickets-only)
        if kind == "crypt":
            cost = 0
            name = "Crypt of Ash"
            waves = 5
            difficulty_mult = 1.0
        elif kind == "graveyard":
            cost = 2
            name = "Graveyard of Kings"
            waves = 7
            difficulty_mult = 1.35
        else:
            cost = 5
            name = "Endless Abyss (10 waves)"
            waves = 10
            difficulty_mult = 1.75

        if self.state.tickets < cost:
            self.toast("Not enough 🎟 tickets.")
            return

        self.state.tickets -= cost

        self.dungeon_running = True
        self.dungeon_log = []
        self.dungeon_status = "RUNNING..."
        self.dungeon_wave = 1
        self.dungeon_total_waves = waves
        self.dungeon_name = name
        self.dungeon_rewards_pending = None

        # Setup first wave
        self._setup_dungeon_wave(difficulty_mult)
        self._dungeon_step(difficulty_mult)

    def _setup_dungeon_wave(self, mult: float):
        # Scale dungeon enemies with forge level and wave
        fl = self.state.forge_level
        w = self.dungeon_wave

        base_hp = int(1800 + (fl ** 1.25) * 220 + w * 950)
        base_dmg = int(25 + (fl ** 0.9) * 3 + w * 8)

        self.dungeon_enemy_max_hp = int(base_hp * mult)
        self.dungeon_enemy_hp = self.dungeon_enemy_max_hp
        self.dungeon_enemy_dmg = int(base_dmg * mult)

        self.dungeon_log.append(f"Wave {w}/{self.dungeon_total_waves}: Enemy HP {self.dungeon_enemy_max_hp}")

    def _dungeon_step(self, mult: float):
        if not self.dungeon_running:
            return

        # Each step = both sides attack once (fast, simple)
        player_dmg = int(self.current_damage() * (1.0 + self.state.forge_level / 100.0))
        self.dungeon_enemy_hp -= player_dmg

        # enemy hits back
        self.state.player_hp -= self.dungeon_enemy_dmg

        # Clamp
        if self.state.player_hp < 0:
            self.state.player_hp = 0

        # Win wave
        if self.dungeon_enemy_hp <= 0:
            self.dungeon_log.append(f"✅ Cleared wave {self.dungeon_wave} (+loot later)")
            self.dungeon_wave += 1

            if self.dungeon_wave > self.dungeon_total_waves:
                self._finish_dungeon_success(mult)
                return

            self._setup_dungeon_wave(mult)
            self.root.after(80, lambda: self._dungeon_step(mult))
            return

        # Lose dungeon
        if self.state.player_hp <= 0:
            self._finish_dungeon_fail()
            return

        # Continue
        self.root.after(80, lambda: self._dungeon_step(mult))

    def _finish_dungeon_success(self, mult: float):
        self.dungeon_running = False
        self.dungeon_status = "CLEARED!"
        fl = self.state.forge_level
        waves = self.dungeon_total_waves

        # Rewards: BIG gold/hammers, some gems, and tickets.
        coins = int((6500 + fl * 420) * mult + waves * 900)
        hammers = int((450 + fl * 18) * mult + waves * 40)
        gems = int((12 + fl // 3) * mult)
        tickets = int(2 + waves // 2)

        # Graveyard/Abyss give extra tickets
        if mult >= 1.35:
            tickets += 3
        if mult >= 1.75:
            tickets += 6

        self.state.coins += coins
        self.state.hammers += hammers
        self.state.gems += gems
        self.state.tickets += tickets

        # Restore HP after dungeon clear
        self.recalc_player_stats(force_full=True)

        self.dungeon_log.append(f"🎁 Rewards: +{coins} coins, +{hammers} hammers, +{gems} gems, +{tickets} tickets")
        self.toast("Dungeon cleared! Loot claimed.", 2.5)
        self.render()

    def _finish_dungeon_fail(self):
        self.dungeon_running = False
        self.dungeon_status = "FAILED"
        # restore HP so you don't get softlocked
        self.recalc_player_stats(force_full=True)
        self.dungeon_log.append("❌ You failed. Try stronger gear / higher forge.")
        self.toast("Dungeon failed.", 2.0)
        self.render()

    def open_dungeons(self):
            if not self.state.ascended_unlocked:
                self.toast("Dungeons unlock at Forge Level 35.")
                return

            if self.dungeon_window and self.dungeon_window.winfo_exists():
                self.dungeon_window.lift()
                self.render_dungeons()
                return

            self.dungeon_window = tk.Toplevel(self.root)
            self.dungeon_window.title("Dungeons")
            self.dungeon_window.geometry("820x720")
            self.dungeon_window.configure(bg=self.BG)
            self.dungeon_window.transient(self.root)
            self.dungeon_window.resizable(False, False)

            self.dungeon_canvas = tk.Canvas(self.dungeon_window, bg=self.BG, highlightthickness=0)
            self.dungeon_canvas.pack(fill="both", expand=True)

            # Dungeon run state
            self.dungeon_running = False
            self.dungeon_log = []
            self.dungeon_status = ""
            self.dungeon_enemy_hp = 0
            self.dungeon_enemy_max_hp = 0
            self.dungeon_enemy_dmg = 0
            self.dungeon_wave = 0
            self.dungeon_total_waves = 0
            self.dungeon_name = ""
            self.dungeon_rewards_pending = None

            self.render_dungeons()
            self.dungeon_window.after(250, self.dungeon_refresh_loop)

    def render_dungeons(self):
        if not (self.dungeon_window and self.dungeon_window.winfo_exists()):
            return
        c = self.dungeon_canvas
        c.delete("all")

        c.create_text(20, 18, text="DUNGEONS", anchor="w", fill=self.TEXT, font=("Arial", 16, "bold"))
        c.create_text(20, 44,
                      text=f"Forge {self.state.forge_level}/{self.forge_level_cap_visible()}   🎟 {self.state.tickets}   (Tickets are endgame-only)",
                      anchor="w", fill=self.SUB, font=("Arial", 11, "bold"))

        # Dungeon cards
        c.create_rectangle(20, 70, 800, 250, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(34, 92, text="Crypt of Ash (FREE)", anchor="w", fill=self.TEXT, font=("Arial", 12, "bold"))
        c.create_text(34, 118, text="5 waves • Best for farming tickets safely", anchor="w", fill=self.SUB, font=("Arial", 10))
        self.dungeon_btn(c, 640, 98, 140, 32, "Start", "#16A34A" if not self.dungeon_running else "#374151",
                         lambda: self.start_dungeon("crypt"))

        c.create_rectangle(20, 260, 800, 440, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(34, 282, text="Graveyard of Kings (2 🎟)", anchor="w", fill=self.TEXT, font=("Arial", 12, "bold"))
        c.create_text(34, 308, text="7 waves • More tickets • Hits harder", anchor="w", fill=self.SUB, font=("Arial", 10))
        self.dungeon_btn(c, 640, 288, 140, 32, "Start", "#F59E0B" if not self.dungeon_running else "#374151",
                         lambda: self.start_dungeon("graveyard"))

        c.create_rectangle(20, 450, 800, 630, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(34, 472, text="Endless Abyss (5 🎟)", anchor="w", fill=self.TEXT, font=("Arial", 12, "bold"))
        c.create_text(34, 498, text="10 waves (prototype) • Big rewards • High danger", anchor="w", fill=self.SUB, font=("Arial", 10))
        self.dungeon_btn(c, 640, 478, 140, 32, "Start", "#EF4444" if not self.dungeon_running else "#374151",
                         lambda: self.start_dungeon("abyss"))

        # Live status panel
        c.create_rectangle(20, 640, 800, 705, fill=self.PANEL2, outline=self.BORDER, width=2)
        status = self.dungeon_status or "Idle"
        c.create_text(34, 662, text=f"Status: {status}", anchor="w", fill=self.TEXT, font=("Arial", 10, "bold"))

        if self.dungeon_running:
            c.create_text(34, 684, text=f"{self.dungeon_name} • Wave {self.dungeon_wave}/{self.dungeon_total_waves}",
                          anchor="w", fill=self.SUB, font=("Arial", 9, "bold"))
            # Enemy HP bar
            frac = self.dungeon_enemy_hp / max(1, self.dungeon_enemy_max_hp)
            c.create_rectangle(420, 668, 790, 684, fill="#374151", outline="")
            c.create_rectangle(420, 668, 420 + int(370 * frac), 684, fill="#F97316", outline="")
            c.create_text(790, 676, text=f"{max(0, self.dungeon_enemy_hp)}/{self.dungeon_enemy_max_hp}",
                          anchor="e", fill=self.TEXT, font=("Arial", 9, "bold"))
        else:
            # show last few log lines
            last = self.dungeon_log[-2:] if self.dungeon_log else []
            y = 684
            for line in last:
                c.create_text(34, y, text=line, anchor="w", fill=self.SUB, font=("Arial", 9))
                y += 16

    # ---------- Tick ----------
    def tick(self):
        self.apply_pending_levelup_if_ready()

        # Auto combat loop (main lane)
        self.player_attack(1.0)
        self.enemy_attack()

        if self.enemy_phase > 0:
            self.enemy_phase -= 1
        if self.damage_popup:
            self.damage_popup[2] -= 8
            self.damage_popup[3] -= 1
            if self.damage_popup[3] <= 0:
                self.damage_popup = None

        self.save_game()
        self.render()

        if self.shop_window and self.shop_window.winfo_exists():
            self.render_shop()
        if self.dungeon_window and self.dungeon_window.winfo_exists():
            self.render_dungeons()

        self.root.after(800, self.tick)

    # ---------- Drawing ----------
    def rect_btn(self, x, y, w, h, text, fill, action):
        self.canvas.create_rectangle(x, y, x + w, y + h, fill=fill, outline="#0A0D13", width=2)
        self.canvas.create_text(x + w / 2, y + h / 2, text=text, fill="white", font=("Arial", 12, "bold"))
        self.click_regions.append((x, y, x + w, y + h, action))

    def panel(self, x, y, w, h, title=None):
        self.canvas.create_rectangle(x, y, x + w, y + h, fill=self.PANEL, outline=self.BORDER, width=2)
        if title:
            self.canvas.create_text(x + 14, y + 16, text=title, anchor="w", fill=self.TEXT, font=("Arial", 14, "bold"))

    def migrate_beta_weapons(self):
        return

    def hsv_to_hex(self, h: float, s: float, v: float) -> str:
        # Small helper for animated rainbow UI (no external deps required)
        h = float(h) % 1.0
        s = max(0.0, min(1.0, float(s)))
        v = max(0.0, min(1.0, float(v)))

        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - f * s)
        t = v * (1.0 - (1.0 - f) * s)
        i = i % 6

        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q

        return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


    def draw_weapon_icon(self, x, y, weapon_type, color, scale=1.0):
        """Draw a small weapon icon at (x,y)."""
        c = self.canvas
        s = float(scale)

        # Beta icon: square + question mark, with a rainbow ring that shifts color
        if str(weapon_type) == "Beta":
            size = 20 * s
            x0, y0 = x - size/2, y - size/2
            x1, y1 = x + size/2, y + size/2

            # Square base
            c.create_rectangle(x0, y0, x1, y1, fill="#111827", outline="#FFFFFF", width=max(2, int(2*s)))

            # Rainbow ring around the question mark
            phase = (time.time() * 0.60) % 1.0
            rainbow = self.hsv_to_hex(phase, 1.0, 1.0)
            ring = size * 0.70
            c.create_oval(x - ring/2, y - ring/2, x + ring/2, y + ring/2,
                          outline=rainbow, width=max(3, int(3*s)))

            # Question mark
            c.create_text(x, y, text="?", fill="#FFFFFF", font=("Arial", max(12, int(14*s)), "bold"))
            return

        col = color if color else self.TEXT
        w2 = max(2, int(2*s))
        w3 = max(2, int(3*s))

        if weapon_type == "Sword":
            c.create_line(x, y + 10*s, x, y - 10*s, fill=col, width=w3)
            c.create_line(x - 6*s, y - 6*s, x + 6*s, y - 6*s, fill=col, width=w2)
        elif weapon_type == "Axe":
            c.create_line(x, y + 12*s, x, y - 10*s, fill=col, width=w3)
            c.create_polygon(x, y - 10*s, x + 12*s, y - 2*s, x, y + 4*s, fill=col, outline=col)
        elif weapon_type == "Hammer":
            c.create_line(x, y + 12*s, x, y - 6*s, fill=col, width=w3)
            c.create_rectangle(x - 10*s, y - 12*s, x + 10*s, y - 6*s, fill=col, outline=col)
        elif weapon_type == "Spear":
            c.create_line(x, y + 12*s, x, y - 12*s, fill=col, width=w2)
            c.create_polygon(x, y - 14*s, x - 6*s, y - 6*s, x + 6*s, y - 6*s, fill=col, outline=col)
        elif weapon_type == "Bow":
            c.create_arc(x - 10*s, y - 12*s, x + 10*s, y + 12*s, start=90, extent=180, style='arc', outline=col, width=w2)
            c.create_line(x + 6*s, y - 10*s, x + 6*s, y + 10*s, fill=col, width=w2)
        elif weapon_type == "Staff":
            c.create_line(x, y + 12*s, x, y - 10*s, fill=col, width=w2)
            c.create_oval(x - 6*s, y - 16*s, x + 6*s, y - 4*s, fill=col, outline=col)
        elif weapon_type == "Gun":
            c.create_rectangle(x - 10*s, y - 6*s, x + 10*s, y + 2*s, fill=col, outline=col)
            c.create_rectangle(x + 6*s, y - 2*s, x + 14*s, y + 1*s, fill=col, outline=col)
        elif weapon_type == "Gauntlets":
            c.create_oval(x - 10*s, y - 4*s, x - 2*s, y + 4*s, fill=col, outline=col)
            c.create_oval(x + 2*s, y - 4*s, x + 10*s, y + 4*s, fill=col, outline=col)
        else:
            c.create_oval(x - 8*s, y - 8*s, x + 8*s, y + 8*s, fill=col, outline=col)
    def draw_hp_bar(self, x, y, w, h, frac, fill_color):
        self.canvas.create_rectangle(x, y, x + w, y + h, fill="#374151", outline="")
        self.canvas.create_rectangle(x, y, x + max(0, int(w * frac)), y + h, fill=fill_color, outline="")

    def draw_top_bar(self, W):
        self.panel(20, 20, W - 40, 92)
        self.canvas.create_text(40, 62, text="Idle Battler", anchor="w", fill=self.TEXT, font=("Arial", 18, "bold"))

        # Top-bar quick buttons (keep nav clean)
        # Tournament button beside title
        if getattr(self.state, "tournaments_unlocked", False):
            self.rect_btn(260, 44, 150, 34, "TOURNAMENT", "#EAB308", self.open_tournaments)
        else:
            self.rect_btn(260, 44, 150, 34, "TOURNAMENT", "#334155",
                          lambda: self.toast("Unlock tournaments at Forge 35."))
        self.canvas.create_text(W / 2, 50, text=f"Battle {self.state.world}-{self.state.stage}", fill="#FDE68A", font=("Arial", 20, "bold"))

        cap = self.forge_level_cap_visible()
        if self.state.pending_levelup is not None:
            secs = max(0, int(self.state.pending_levelup.ready_at - time.time()))
            forge_txt = f"FORGE LEVEL {self.state.forge_level}/{cap}  •  leveling in {secs}s"
            color = "#FB7185"
        else:
            forge_txt = f"FORGE LEVEL {self.state.forge_level}/{cap}"
            color = "#60A5FA"
        self.canvas.create_text(W / 2, 78, text=forge_txt, fill=color, font=("Arial", 14, "bold"))

        reb = int(getattr(self.state, "rebirths", 0))
        if self.state.ascended_unlocked:
            currencies = f"⭐ {reb}    🔨 {self.state.hammers}    💰 {self.state.coins}    💎 {self.state.gems}    🎟 {self.state.tickets}"
        else:
            currencies = f"⭐ {reb}    🔨 {self.state.hammers}    💰 {self.state.coins}    💎 {self.state.gems}"

        # Currency strip (top-right)
        cur_id = self.canvas.create_text(W - 40, 62, text=currencies, anchor="e", fill=self.TEXT, font=("Arial", 14, "bold"))
        # Place ABOUT just to the LEFT of the ⭐ strip (so it doesn't cover coins/gems)
        try:
            bx0, by0, bx1, by1 = self.canvas.bbox(cur_id)
            about_x = max(220, bx0 - 12 - 90)
        except Exception:
            about_x = W - 520
        self.rect_btn(about_x, 44, 90, 34, "ABOUT", "#334155", self.open_about)

    def draw_enemy_sprite(self, ex: int, ey: int, enemy_type: str, boss: bool = False):
        """Draw varied enemy sprites using simple Tkinter shapes."""
        n = (enemy_type or "").lower()
        scale = 1.25 if boss else 1.0

        # Shadow
        self.canvas.create_oval(ex - 34*scale, ey + 36*scale, ex + 34*scale, ey + 54*scale, fill="#0B1220", outline="")

        # base colors by type
        palette = {
            "slime": ("#34D399", "#059669"),
            "goblin": ("#86EFAC", "#16A34A"),
            "ghoul": ("#A78BFA", "#6D28D9"),
            "wisp": ("#93C5FD", "#2563EB"),
            "crawler": ("#FCA5A5", "#DC2626"),
            "knight": ("#D1D5DB", "#6B7280"),
            "golem": ("#FCD34D", "#B45309"),
            "shade": ("#9CA3AF", "#111827"),
            "revenant": ("#F472B6", "#BE185D"),
            "warden": ("#60A5FA", "#1D4ED8"),
        }
        head, body = palette.get(n, ("#93C5FD", "#7C3AED"))

        # size
        hw = int(22 * scale)
        hh = int(42 * scale)
        bw = int(22 * scale)
        bh = int(56 * scale)

        # different silhouettes
        if n in ("slime", "wisp"):
            # blobby enemy
            self.canvas.create_oval(ex - hw, ey - hh, ex + hw, ey - int(8 * scale), fill=head, outline="")
            self.canvas.create_oval(ex - int(26 * scale), ey - int(10 * scale), ex + int(26 * scale), ey + int(34 * scale), fill=body, outline="")
        elif n in ("golem",):
            self.canvas.create_rectangle(ex - hw, ey - hh, ex + hw, ey - int(10 * scale), fill=head, outline="")
            self.canvas.create_rectangle(ex - int(28 * scale), ey - int(10 * scale), ex + int(28 * scale), ey + int(40 * scale), fill=body, outline="")
        elif n in ("crawler",):
            self.canvas.create_oval(ex - hw, ey - hh, ex + hw, ey - int(12 * scale), fill=head, outline="")
            self.canvas.create_rectangle(ex - bw, ey - int(12 * scale), ex + bw, ey + int(30 * scale), fill=body, outline="")
            # little legs
            for dx in (-18, -6, 6, 18):
                self.canvas.create_line(ex + int(dx * scale), ey + int(30 * scale),
                                        ex + int(dx * scale), ey + int(46 * scale),
                                        fill="#D1D5DB", width=max(2, int(3 * scale)))
        else:
            # default humanoid
            self.canvas.create_oval(ex - hw, ey - hh, ex + hw, ey - int(12 * scale), fill=head, outline="")
            self.canvas.create_rectangle(ex - bw, ey - int(12 * scale), ex + bw, ey + int(28 * scale), fill=body, outline="")

        # Boss crown marker
        if boss:
            cy = ey - int(62 * scale)
            self.canvas.create_polygon(
                ex - int(16 * scale), cy + int(12 * scale),
                ex - int(8 * scale), cy,
                ex, cy + int(10 * scale),
                ex + int(8 * scale), cy,
                ex + int(16 * scale), cy + int(12 * scale),
                fill="#FDE68A", outline="#111827"
            )

    def draw_battle(self, x, y, w, h):
        self.panel(x, y, w, h, "Battle Lane (tap to attack)")
        self.battle_rect = (x, y, x + w, y + h)

        self.canvas.create_rectangle(x + 20, y + h - 60, x + w - 20, y + h - 36, fill="#2D3748", outline="")

        px = x + 140
        py = y + 190
        # Player (cleaner sprite)
        self.canvas.create_oval(px - 28, py + 34, px + 28, py + 50, fill="#0B1220", outline="")  # shadow
        self.canvas.create_oval(px - 20, py - 74, px + 20, py - 34, fill="#F2C094", outline="#111827", width=2)  # head
        self.canvas.create_arc(px - 20, py - 78, px + 20, py - 34, start=0, extent=180, fill="#111827", outline="")  # hair
        self.canvas.create_oval(px - 10, py - 58, px - 4, py - 52, fill="#111827", outline="")
        self.canvas.create_oval(px + 4, py - 58, px + 10, py - 52, fill="#111827", outline="")
        self.canvas.create_rectangle(px - 22, py - 34, px + 22, py + 24, fill="#5B6B88", outline="#111827", width=2)
        self.canvas.create_rectangle(px - 18, py - 10, px + 18, py + 12, fill="#3B4A66", outline="")
        self.canvas.create_rectangle(px - 22, py + 8, px + 22, py + 14, fill="#111827", outline="")
        self.canvas.create_rectangle(px - 18, py + 24, px - 2, py + 48, fill="#2D3748", outline="#111827", width=2)
        self.canvas.create_rectangle(px + 2, py + 24, px + 18, py + 48, fill="#2D3748", outline="#111827", width=2)
        self.canvas.create_line(px + 26, py - 8, px + 44, py - 26, fill="#E5E7EB", width=3)
        self.canvas.create_rectangle(px + 20, py - 6, px + 28, py + 2, fill="#B45309", outline="#111827", width=1)
        self.canvas.create_line(px - 10, py + 24, px - 18, py + 58, fill="#D1D5DB", width=3)
        self.canvas.create_line(px + 10, py + 24, px + 18, py + 58, fill="#D1D5DB", width=3)

        eq = self.state.equipped_weapon()
        icon_color = (RARITY_COLORS.get(eq.rarity, "#9AA0A6")) if eq else "#9AA0A6"
        icon_type = eq.weapon_type if eq else "Sword"
        self.draw_weapon_icon(px + 18, py - 4, icon_type, icon_color, scale=0.9)

        self.canvas.create_line(px - 18, py - 18, px - 40, py + 10, fill="#D1D5DB", width=3)

        # Player HP
        hp_frac = self.state.player_hp / max(1, self.state.player_max_hp)
        self.canvas.create_text(x + 30, y + 52, text="HP", anchor="w", fill=self.TEXT, font=("Arial", 10, "bold"))
        self.draw_hp_bar(x + 60, y + 44, 220, 14, hp_frac, "#22C55E")
        self.canvas.create_text(x + 290, y + 52, text=f"{self.state.player_hp}/{self.state.player_max_hp}", anchor="w", fill=self.SUB, font=("Arial", 9))

        # Enemy
        ex = x + w - 180
        ey = y + 190 + (6 if self.enemy_phase else 0)
        enemy_type = getattr(self, "enemy_type", self.enemy_name)
        self.draw_enemy_sprite(ex, ey, enemy_type, boss=getattr(self, "boss_active", False))
        self.canvas.create_text(ex, y + 42, text=self.enemy_name, fill=self.TEXT, font=("Arial", 12, "bold"))
        if getattr(self, "boss_active", False):
            secs = max(0, int(self.boss_deadline - time.time()))
            self.canvas.create_text(ex, y + 60, text=f"{secs}s LEFT", fill="#FB7185", font=("Arial", 11, "bold"))

        bx, by = ex - 70, y + 70
        self.draw_hp_bar(bx, by, 180, 14, self.enemy_hp / max(1, self.enemy_max_hp), "#F97316")
        self.canvas.create_text(ex + 110, by - 2, text=f"{self.enemy_hp}/{self.enemy_max_hp}", anchor="e", fill=self.SUB, font=("Arial", 9))

        if self.damage_popup:
            txt, dx, dy, _ = self.damage_popup
            self.canvas.create_text(dx, dy, text=txt, fill="#FDE68A", font=("Arial", 13, "bold"))

        dmg = self.current_damage()
        self.canvas.create_text(x + 30, y + h - 24, text=f"Weapon Damage: {dmg}", anchor="w", fill=self.TEXT, font=("Arial", 11, "bold"))
        self.canvas.create_text(x + w - 20, y + h - 24, text="Kills add rewards (no drops)", anchor="e", fill=self.SUB, font=("Arial", 10))

    
    def draw_quests(self, x, y, w, h):
        self.panel(x, y, w, h, "Quests (Easy)")
        # simple list
        quests = getattr(self.state, "quests", []) or []
        row_h = 70
        top = y + 40
        for i in range(min(3, len(quests))):
            q = quests[i]
            yy = top + i * row_h
            self.canvas.create_rectangle(x + 12, yy, x + w - 12, yy + 56, fill=self.PANEL2, outline="#4B5563", width=2)
            desc = q.get("desc", "Quest")
            prog = int(q.get("progress", 0))
            tgt = int(q.get("target", 1))
            self.canvas.create_text(x + 26, yy + 18, text=desc, anchor="w", fill=self.TEXT, font=("Arial", 11, "bold"))
            self.canvas.create_text(x + 26, yy + 40, text=f"{prog}/{tgt}  •  +{q.get('xp',0)} BP XP  •  +{q.get('gems',0)}💎  +{q.get('coins',0)}🪙",
                                    anchor="w", fill=self.SUB, font=("Arial", 10, "bold"))

            done = prog >= tgt
            btn_txt = "CLAIM" if done else "IN PROGRESS"
            btn_col = "#16A34A" if done else "#374151"
            # click region button
            bx = x + w - 130
            by = yy + 12
            self.rect_btn(bx, by, 110, 32, btn_txt, btn_col, (lambda ix=i: self.claim_quest(ix)) if done else None)

        # Battle pass quick preview
        tier = int(getattr(self.state, "bp_tier", 1))
        xp = int(getattr(self.state, "bp_xp", 0))
        self.canvas.create_text(x + 18, y + h - 26, text=f"Battle Pass: Tier {tier} • XP {xp}/{BP_XP_PER_TIER}",
                                anchor="w", fill=self.SUB, font=("Arial", 10, "bold"))

    def draw_inventory(self, x, y, w, h):
        self.panel(x, y, w, h, "Inventory")

        # Remember area for mouse-wheel scrolling (main window only)
        self._inventory_box = (x, y, x + w, y + h)

        inv = self.state.inventory
        if not hasattr(self, "inventory_scroll"):
            self.inventory_scroll = 0

        row_h = 54
        list_top = y + 38
        list_bottom = y + h - 60  # leave room for the sell-all button
        rows_fit = max(1, int((list_bottom - list_top) // row_h))
        self._inventory_rows_fit = rows_fit

        max_scroll = max(0, len(inv) - rows_fit)
        self.inventory_scroll = clamp(getattr(self, "inventory_scroll", 0), 0, max_scroll)

        start = self.inventory_scroll
        visible = inv[start:start + rows_fit]

        for i, weapon in enumerate(visible):
            gi = start + i
            yy = list_top + i * row_h

            outline = "#FFFFFF" if self.selected_idx == gi else "#4B5563"
            self.canvas.create_rectangle(x + 12, yy, x + w - 24, yy + 44, fill=self.PANEL2, outline=outline, width=2)

            self.draw_weapon_icon(x + 22, yy + 12, weapon.weapon_type,
                                  RARITY_COLORS.get(weapon.rarity, "#9AA0A6"), scale=0.7)

            eq_tag = "  [EQUIPPED]" if (self.state.equipped_idx == gi) else ""
            self.canvas.create_text(x + 60, yy + 14, text=weapon.name + eq_tag, anchor="w",
                                    fill=RARITY_COLORS.get(weapon.rarity, self.TEXT), font=("Arial", 10, "bold"))
            self.canvas.create_text(x + 60, yy + 30,
                                    text=f"{weapon.weapon_type} • {weapon.rarity} • DMG {weapon.damage}",
                                    anchor="w", fill=self.TEXT, font=("Arial", 9))
            self.click_regions.append((x + 12, yy, x + w - 24, yy + 44, lambda idx=gi: self.select_item(idx)))

        # Fake scrollbar (visual only, wheel controls it)
        track_x1 = x + w - 20
        track_x2 = x + w - 12
        c_y1 = list_top
        c_y2 = list_bottom
        self.canvas.create_rectangle(track_x1, c_y1, track_x2, c_y2, fill="#111827", outline="#374151")
        if len(inv) > rows_fit:
            frac = rows_fit / max(1, len(inv))
            thumb_h = max(24, int((c_y2 - c_y1) * frac))
            thumb_y = c_y1 + int((c_y2 - c_y1 - thumb_h) * (self.inventory_scroll / max(1, max_scroll)))
            self.canvas.create_rectangle(track_x1 + 1, thumb_y, track_x2 - 1, thumb_y + thumb_h,
                                         fill="#6B7280", outline="")

        # Sell all button
        self.rect_btn(x + 12, y + h - 54, 260, 40, "SELL ALL (UNEQUIPPED)", "#DC2626", self.sell_all_unequipped)

    def draw_details(self, x, y, w, h):
        self.panel(x, y, w, h, "Gear Details")

        eq = self.state.equipped_weapon()
        sel = None
        if self.selected_idx is not None and self.selected_idx < len(self.state.inventory):
            sel = self.state.inventory[self.selected_idx]

        mid = x + (w // 2)

        # Left: Equipped summary
        if eq:
            eq_col = RARITY_COLORS.get(eq.rarity, "#9AA0A6")
            self.canvas.create_text(x + 18, y + 44, text="EQUIPPED:", anchor="w",
                                    fill=self.SUB, font=("Arial", 10, "bold"))
            self.canvas.create_text(x + 18, y + 64,
                                    text=f"{eq.name}  •  {eq.rarity} {eq.weapon_type}  •  DMG {('???' if getattr(eq,'rarity','')=='Beta' else eq.damage)}",
                                    anchor="w", fill=eq_col, font=("Arial", 10, "bold"))
        else:
            self.canvas.create_text(x + 18, y + 54, text="EQUIPPED: None (DMG 6)", anchor="w",
                                    fill=self.SUB, font=("Arial", 10, "bold"))

        # Right: Selected / last forged summary
        right_x = x + w - 18
        right_col_left = mid + 18  # left edge of the right half

        self.canvas.create_text(right_x, y + 44, text="IN INVENTORY:", anchor="e",
                                fill=self.SUB, font=("Arial", 10, "bold"))

        if sel:
            sel_col = RARITY_COLORS.get(sel.rarity, "#9AA0A6")
            # Small icon + left-aligned text inside the right column (looks cleaner than a single right-anchored line)
            self.draw_weapon_icon(right_col_left + 10, y + 56, sel.weapon_type, sel_col, scale=0.95)
            self.canvas.create_text(right_col_left + 42, y + 64,
                                    text=f"{sel.name}  •  {sel.rarity} {sel.weapon_type}  •  DMG {('???' if getattr(sel,'rarity','')=='Beta' else sel.damage)}",
                                    anchor="w", fill=sel_col, font=("Arial", 10, "bold"))
        else:
            # If nothing is selected, show newest forged if available
            lf = getattr(self, "last_forged_weapon", None) or getattr(self, "last_forged", None)
            if lf:
                # lf may be a Weapon object or a (name, rarity, type, dmg) tuple
                try:
                    lf_name = lf.name
                    lf_rarity = lf.rarity
                    lf_type = lf.weapon_type
                    lf_dmg = lf.damage
                except Exception:
                    lf_name = lf[0] if isinstance(lf, (list, tuple)) and len(lf) > 0 else str(lf)
                    lf_rarity = lf[1] if isinstance(lf, (list, tuple)) and len(lf) > 1 else "Common"
                    lf_type = lf[2] if isinstance(lf, (list, tuple)) and len(lf) > 2 else "Weapon"
                    lf_dmg = lf[3] if isinstance(lf, (list, tuple)) and len(lf) > 3 else ""
                lf_col = RARITY_COLORS.get(lf_rarity, "#9AA0A6")
                self.draw_weapon_icon(right_col_left + 10, y + 56, lf_type, lf_col, scale=0.95)
                dmg_txt = f"  •  DMG {('???' if str(lf_rarity)=='Beta' else lf_dmg)}" if lf_dmg != "" else ""
                self.canvas.create_text(right_col_left + 42, y + 64,
                                        text=f"{lf_name}  •  {lf_rarity} {lf_type}{dmg_txt}",
                                        anchor="w", fill=lf_col, font=("Arial", 10, "bold"))
            else:
                self.canvas.create_text(right_x, y + 64,
                                        text="Select a weapon from inventory.",
                                        anchor="e", fill=self.SUB, font=("Arial", 10, "bold"))

        self.canvas.create_line(x + 18, y + 82, x + w - 18, y + 82, fill=self.BORDER, width=2)

        # --- Side-by-side stats (left = equipped, right = selected inventory) ---
        content_top = y + 100
        left_x = x + 18
        right_x2 = mid + 18

        # Left column: Equipped weapon stats
        if eq:
            eq_col = RARITY_COLORS.get(eq.rarity, "#9AA0A6")
            self.draw_weapon_icon(left_x + 10, content_top + 10, eq.weapon_type, eq_col, scale=1.20)
            self.canvas.create_text(left_x + 62, content_top, text="EQUIPPED STATS", anchor="w",
                                    fill=self.SUB, font=("Arial", 10, "bold"))
            self.canvas.create_text(left_x + 62, content_top + 22, text=eq.name, anchor="w",
                                    fill=eq_col, font=("Arial", 13, "bold"))
            self.canvas.create_text(left_x + 62, content_top + 42, text=f"{eq.rarity} • {eq.weapon_type}", anchor="w",
                                    fill=self.TEXT, font=("Arial", 10, "bold"))
            self.canvas.create_text(left_x, content_top + 72, text=f"Damage: {('???' if getattr(eq,'rarity','')=='Beta' else eq.damage)}", anchor="w",
                                    fill="#93C5FD", font=("Arial", 12, "bold"))

            # show up to 2 affixes
            ay = content_top + 98
            if eq.affixes:
                self.canvas.create_text(left_x, ay, text=("???" if getattr(eq,'rarity','')=='Beta' else eq.affixes[0]), anchor="w",
                                        fill=self.TEXT, font=("Arial", 10))
                if len(eq.affixes) > 1:
                    self.canvas.create_text(left_x, ay + 20, text=("???" if getattr(eq,'rarity','')=='Beta' else eq.affixes[1]), anchor="w",
                                            fill=self.TEXT, font=("Arial", 10))
        else:
            self.canvas.create_text(left_x, content_top + 12, text="EQUIPPED STATS", anchor="w",
                                    fill=self.SUB, font=("Arial", 10, "bold"))
            self.canvas.create_text(left_x, content_top + 40, text="No equipped weapon.", anchor="w",
                                    fill=self.TEXT, font=("Arial", 11))

        # Right column: Selected inventory weapon stats
        if self.selected_idx is None or self.selected_idx >= len(self.state.inventory):
            self.canvas.create_text(right_x2, content_top + 12, text="INVENTORY STATS", anchor="w",
                                    fill=self.SUB, font=("Arial", 10, "bold"))
            self.canvas.create_text(right_x2, content_top + 40, text="Click an item on the left.", anchor="w",
                                    fill=self.TEXT, font=("Arial", 11))
            return

        weapon = self.state.inventory[self.selected_idx]
        color = RARITY_COLORS.get(weapon.rarity, "#9AA0A6")
        is_beta = (getattr(weapon, 'rarity', '') == 'Beta')

        self.draw_weapon_icon(right_x2 + 10, content_top + 10, weapon.weapon_type, color, scale=1.20)
        self.canvas.create_text(right_x2 + 62, content_top, text="INVENTORY STATS", anchor="w",
                                fill=self.SUB, font=("Arial", 10, "bold"))
        self.canvas.create_text(right_x2 + 62, content_top + 22, text=weapon.name, anchor="w",
                                fill=color, font=("Arial", 13, "bold"))
        self.canvas.create_text(right_x2 + 62, content_top + 42, text=f"{weapon.rarity} • {weapon.weapon_type}", anchor="w",
                                fill=self.TEXT, font=("Arial", 10, "bold"))
        self.canvas.create_text(right_x2, content_top + 72, text=f"Damage: {('???' if is_beta else weapon.damage)}", anchor="w",
                                fill="#93C5FD", font=("Arial", 12, "bold"))

        if not is_beta and not (eq and getattr(eq, 'rarity', '') == 'Beta'):
            eq_dmg = eq.damage if eq else 6
            diff = weapon.damage - eq_dmg
            sign = "+" if diff >= 0 else ""
            comp_col = "#22C55E" if diff >= 0 else "#EF4444"
            self.canvas.create_text(right_x2, content_top + 96, text=f"Compared to equipped: {sign}{diff} DMG",
                                    anchor="w", fill=comp_col, font=("Arial", 10, "bold"))
        else:
            self.canvas.create_text(right_x2, content_top + 96, text="Compared to equipped: ???",
                                    anchor="w", fill=self.SUB, font=("Arial", 10, "bold"))

        ay2 = content_top + 122
        if weapon.affixes:
            self.canvas.create_text(right_x2, ay2, text=("???" if is_beta else weapon.affixes[0]), anchor="w",
                                    fill=self.TEXT, font=("Arial", 10))
            if len(weapon.affixes) > 1:
                self.canvas.create_text(right_x2, ay2 + 20, text=("???" if is_beta else weapon.affixes[1]), anchor="w",
                                        fill=self.TEXT, font=("Arial", 10))

        btn_txt = "UNEQUIP" if (self.state.equipped_idx == self.selected_idx) else "EQUIP"
        # Equip / Store / Sell
        self.rect_btn(x + 18, y + h - 60, 95, 38, btn_txt, "#2563EB", self.equip_selected)
        self.rect_btn(x + 118, y + h - 60, 95, 38, "STORE", "#F59E0B", self.store_selected)
        self.rect_btn(x + 218, y + h - 60, 95, 38, "SELL", "#DC2626", self.sell_selected)

        ae_txt = "AUTO EQUIP ON" if self.state.auto_equip else "AUTO EQUIP OFF"
        ae_col = "#16A34A" if self.state.auto_equip else "#DC2626"
        self.rect_btn(x + 318, y + h - 60, 170, 38, ae_txt, ae_col, self.toggle_auto_equip)

    def draw_bottom_bar(self, W, H):
        y = H - 92
        self.panel(20, y, W - 40, 60)

        x = 38
        gap = 10

        # --- Core controls (left) ---
        self.rect_btn(x, y + 10, 210, 40, "FORGE (1 🔨)", "#2563EB", self.forge_once)
        x += 210 + gap

        auto_color = "#16A34A" if self.state.auto_forge else "#DC2626"
        self.rect_btn(x, y + 10, 160, 40, "AUTO FORGE", auto_color, self.auto_forge_toggle)
        x += 160 + gap

        ae_color = "#16A34A" if self.state.auto_equip else "#DC2626"
        self.rect_btn(x, y + 10, 150, 40, "AUTO EQUIP", ae_color, self.toggle_auto_equip)
        x += 150 + gap

        # Storage button (right of auto-equip)
        self.rect_btn(x, y + 10, 130, 40, "STORAGE", "#0EA5E9", self.open_storage)
        x += 130 + gap

        # --- Level / Rebirth button ---
        cap = self.forge_level_cap_visible()

        if self.state.forge_level >= cap:
            if cap == 100 and self.state.ascended_unlocked and int(getattr(self.state, "rebirths", 0)) < 45:
                lvl_text = "REBIRTH ⭐"
                lvl_color = "#F59E0B"
                action = self.open_rebirth
            else:
                lvl_text = "MAX LEVEL"
                lvl_color = "#374151"
                action = lambda: None
        elif self.state.pending_levelup is not None:
            secs = max(0, int(self.state.pending_levelup.ready_at - time.time()))
            skip_cost = self.forge_levelup_skip_cost(self.state.forge_level, secs)
            can_skip = self.state.gems >= skip_cost
            lvl_text = f"LEVELING {secs}s / SKIP {skip_cost}💎"
            lvl_color = "#FB7185" if can_skip else "#6B7280"
            action = self.finish_level_up_now if can_skip else (lambda: self.toast("Not enough gems to skip."))
        else:
            cost = self.forge_levelup_cost(self.state.forge_level)
            wait = self.forge_levelup_wait(self.state.forge_level)
            lvl_text = f"LEVEL UP ({cost}, {wait}s)"
            lvl_color = "#16A34A"
            action = self.start_level_up

        # Leave enough room on small windows by shrinking this button if needed
        lvl_w = 260
        if x + lvl_w + 10 > W - 40:
            lvl_w = max(200, (W - 40) - x - 10)
        self.rect_btn(x, y + 10, lvl_w, 40, lvl_text, lvl_color, action)

        
        # --- Tabs to the right of the level button ---
        gap2 = 10
        tx = x + lvl_w + gap2

        tabs = [
            ("RARITY", "#0EA5E9", self.open_rarity),
            ("SHOP", "#7C3AED", self.open_shop),
            ("BP & QUESTS", "#22C55E", self.open_bp_and_quests),
            ("SETTINGS", "#475569", self.open_settings),
        ]
        # Endgame hub when ascension/dungeons exist
        if getattr(self.state, "ascension_unlocked", False) or getattr(self.state, "ascended_unlocked", False):
            tabs.append(("ENDGAME", "#F59E0B", self.open_endgame_hub))
        if getattr(self.state, "ascended_unlocked", False):
            tabs.append(("DUNGEONS", "#F97316", self.open_dungeons))

        remaining = (W - 40) - tx
        n = len(tabs)
        btn_w = max(80, int((remaining - gap2 * (n - 1)) / max(1, n)))
        btn_w = min(btn_w, 118)

        for label, col, fn in tabs:
            if label == "TOURNAMENTS" and not getattr(self.state, "tournaments_unlocked", False):
                self.rect_btn(tx, y + 10, btn_w, 40, label, "#334155",
                              lambda: self.toast("Unlock tournaments at Forge 35."))
            else:
                self.rect_btn(tx, y + 10, btn_w, 40, label, col, fn)
            tx += btn_w + gap2


    def render(self):
        self.canvas.delete("all")
        self.click_regions.clear()
        W = self.root.winfo_width()
        H = self.root.winfo_height()
        # Unlock tournaments at Forge 35 on Rebirth 0
        # Unlock tournaments permanently once Forge 35+ is reached (any rebirth)
        if self.state.forge_level >= 35:
            self.state.tournaments_unlocked = True

        self.ensure_tournament_state() if getattr(self.state, 'tournaments_unlocked', False) else None

        # Boss timer check (fails back if time runs out)
        if getattr(self, "boss_active", False) and time.time() > getattr(self, "boss_deadline", 0.0):
            # Fail: drop back to start of this 10-world chunk (457->450-1, 110->110-1 etc.)
            self.boss_active = False
            self.boss_deadline = 0.0
            self.state.world = max(1, (self.state.world // 10) * 10)
            self.state.stage = 1
            self.toast("Boss escaped! Dropped back to start of this 10-world chunk.")
            self.setup_enemy_for_stage()

        self.draw_top_bar(W)
        self.draw_battle(20, 128, int(W * 0.50), 320)

        self.draw_quests(int(W * 0.50) + 40, 128, W - (int(W * 0.50) + 60), 320)

        self.draw_inventory(20, 475, int(W * 0.54), H - 590)
        self.draw_details(int(W * 0.54) + 40, 475, W - (int(W * 0.54) + 60), H - 590)

        if self.toast_text and time.time() < self.toast_until:
            self.canvas.create_rectangle(20, H - 140, 640, H - 102, fill="#111827", outline=self.BORDER, width=2)
            self.canvas.create_text(36, H - 121, text=self.toast_text, anchor="w", fill=self.TEXT, font=("Arial", 10, "bold"))

        self.draw_bottom_bar(W, H)

    
    # ---------- Settings ----------
    def open_settings(self):
        if getattr(self, "settings_window", None) and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.render_settings_window()
            return
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        self.settings_window.geometry("520x320")
        self.settings_window.configure(bg=self.BG)
        self.settings_window.transient(self.root)
        self.settings_window.resizable(False, False)

        self.sw_canvas = tk.Canvas(self.settings_window, bg=self.BG, highlightthickness=0)
        self.sw_canvas.pack(fill="both", expand=True)
        self.settings_window.bind("<Button-1>", self.handle_settings_click)
        self.render_settings_window()

    def handle_settings_click(self, event):
        x, y = event.x, event.y
        # Fullscreen toggle button
        if 40 <= x <= 480 and 120 <= y <= 170:
            self.toggle_fullscreen()
            self.render_settings_window()

    def exit_fullscreen(self):
        if getattr(self, "fullscreen", False):
            self.fullscreen = False
            self.root.attributes("-fullscreen", False)
            self.toast("Fullscreen OFF")

    def toggle_fullscreen(self):
        self.fullscreen = not getattr(self, "fullscreen", False)
        self.root.attributes("-fullscreen", self.fullscreen)
        self.toast("Fullscreen ON" if self.fullscreen else "Fullscreen OFF")

    def render_settings_window(self):
        c = self.sw_canvas
        c.delete("all")
        c.create_text(28, 28, text="SETTINGS", anchor="w", fill=self.TEXT, font=("Arial", 18, "bold"))
        c.create_text(28, 56, text="Basic display options.", anchor="w", fill=self.SUB, font=("Arial", 10, "bold"))

        label = "Fullscreen: ON" if getattr(self, "fullscreen", False) else "Fullscreen: OFF"
        fill = "#16A34A" if getattr(self, "fullscreen", False) else "#334155"
        c.create_rectangle(40, 120, 480, 170, fill=fill, outline=self.BORDER, width=2)
        c.create_text(260, 145, text=label, fill=self.TEXT, font=("Arial", 12, "bold"))

        c.create_text(28, 260, text="Tip: Press ESC to exit fullscreen.", anchor="w", fill=self.SUB, font=("Arial", 10, "bold"))

    # ---------- Quests Window ----------
    def open_quests(self):
        if getattr(self, "quests_window", None) and self.quests_window.winfo_exists():
            self.quests_window.lift()
            self.render_quests_window()
            return
        self.quests_window = tk.Toplevel(self.root)
        self.quests_window.title("Quests")
        self.quests_window.geometry("860x740")
        self.quests_window.configure(bg=self.BG)
        self.quests_window.transient(self.root)
        self.quests_window.resizable(False, False)

        self.qw_canvas = tk.Canvas(self.quests_window, bg=self.BG, highlightthickness=0)
        self.qw_canvas.pack(fill="both", expand=True)

        self.qw_tab = "QUESTS"
        self.quests_window.bind("<Button-1>", self.handle_quests_click)
        self.render_quests_window()


    def open_bp_and_quests(self):
        """Small hub popup: Battle Pass + Quests."""
        win = tk.Toplevel(self.root)
        win.title("Battle Pass & Quests")
        win.geometry("380x220")
        win.configure(bg=self.BG)
        frm = tk.Frame(win, bg=self.BG)
        frm.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(frm, text="Choose a screen:", bg=self.BG, fg=self.TEXT, font=("Arial", 12, "bold")).pack(pady=(0, 12))

        def go_bp():
            try:
                win.destroy()
            except Exception:
                pass
            self.open_battle_pass()

        def go_q():
            try:
                win.destroy()
            except Exception:
                pass
            self.open_quests()

        tk.Button(frm, text="Battle Pass", command=go_bp, width=26).pack(pady=6)
        tk.Button(frm, text="Quests", command=go_q, width=26).pack(pady=6)

        tk.Button(frm, text="Close", command=win.destroy, width=26).pack(pady=(14, 0))



    def open_endgame_hub(self):
        """Small hub popup: Endgame (Ascension)."""
        win = tk.Toplevel(self.root)
        win.title("Endgame")
        win.geometry("380x220")
        win.configure(bg=self.BG)
        frm = tk.Frame(win, bg=self.BG)
        frm.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(frm, text="Endgame options:", bg=self.BG, fg=self.TEXT, font=("Arial", 12, "bold")).pack(pady=(0, 12))

        def go_asc():
            try:
                win.destroy()
            except Exception:
                pass
            self.open_ascension()

        asc_enabled = bool(getattr(self.state, "ascension_unlocked", False))
        tk.Button(frm, text="Ascension", command=go_asc, width=26,
                  state=("normal" if asc_enabled else "disabled")).pack(pady=6)

        if not asc_enabled:
            tk.Label(frm, text="(Unlock Ascension at Forge 35+)", bg=self.BG, fg="#93C5FD",
                     font=("Arial", 10)).pack(pady=(8, 0))

        tk.Button(frm, text="Close", command=win.destroy, width=26).pack(pady=(14, 0))

    # ---------- Tournaments Window ----------
    def open_tournaments(self):

        if not getattr(self.state, "tournaments_unlocked", False):
            self.toast("Unlock tournaments at Forge 35.")
            return

        self.ensure_tournament_state()
        if getattr(self, "tourn_window", None) and self.tourn_window.winfo_exists():
            self.tourn_window.lift()
            self.render_tourn_window()
            return

        self.active_tab = "tournaments"
        self.tourn_window = tk.Toplevel(self.root)
        self.tourn_window.title("Tournaments")
        self.tourn_window.geometry("860x760")
        self.tourn_window.configure(bg=self.BG)
        self.tourn_window.transient(self.root)
        self.tourn_window.resizable(False, False)

        self.tw_canvas = tk.Canvas(self.tourn_window, bg=self.BG, highlightthickness=0)
        self.tw_canvas.pack(fill="both", expand=True)

        self.tourn_window.bind("<Button-1>", self.handle_tourn_click)
        self.tourn_window.bind("<MouseWheel>", self.handle_tourn_wheel)
        self.render_tourn_window()
        self.tourn_window.after(250, self.tourn_refresh_loop)

    def tourn_refresh_loop(self):
        # Keep tournament timer + rainbow icon animating while the window is open
        if not (getattr(self, "tourn_window", None) and self.tourn_window.winfo_exists()):
            return

        # Let bots advance over time so you have to keep up
        self.ensure_tournament_state()
        now = time.time()
        last = getattr(self.state, "tourn_last_bot_tick", None)
        if last is None:
            self.state.tourn_last_bot_tick = now
        else:
            dt = now - float(last)
            if dt >= 0.75:
                steps = int(dt // 0.75)
                self.state.tourn_last_bot_tick = now
                # bots gain more as your points rise (pressure)
                p = int(getattr(self.state, "tourn_points", 0))
                base_lo = 2 + min(8, p // 100)
                base_hi = 10 + min(30, p // 30)
                for _ in range(steps):
                    for b in self.state.tourn_bots:
                        b["points"] += random.randint(base_lo, base_hi)
                self.state.tourn_bots.sort(key=lambda x: x["points"], reverse=True)

        try:
            self.render_tourn_window()
        finally:
            try:
                self.tourn_window.after(250, self.tourn_refresh_loop)
            except Exception:
                pass

    def handle_tourn_wheel(self, event):
        # Windows: event.delta is multiples of 120
        delta = -1 if event.delta > 0 else 1
        if not hasattr(self, 'tourn_scroll'):
            self.tourn_scroll = 0
        self.tourn_scroll = max(0, self.tourn_scroll + delta)
        self.render_tourn_window()

    def open_tourn_rewards(self):
        # Simple preview of tournament prizes (visual only for now)
        if getattr(self, "tourn_rewards_window", None) and self.tourn_rewards_window.winfo_exists():
            try:
                self.tourn_rewards_window.lift()
                return
            except Exception:
                pass

        w = tk.Toplevel(self.root)
        w.title("Tournament Rewards")
        w.geometry("520x720")
        w.configure(bg=self.BG)
        self.tourn_rewards_window = w

        c = tk.Canvas(w, width=520, height=720, bg=self.BG, highlightthickness=0)
        c.pack(fill="both", expand=True)

        c.create_text(20, 22, text="Tournament Rewards", anchor="w", fill=self.TEXT, font=("Arial", 18, "bold"))
        c.create_text(20, 48, text="(Preview) Rewards are local for now — online prizes later.", anchor="w",
                      fill=self.SUB, font=("Arial", 10, "bold"))

        # Helper icon drawers
        def draw_coin(x, y):
            c.create_oval(x-12, y-12, x+12, y+12, fill="#F59E0B", outline=self.BORDER, width=2)
            c.create_text(x, y, text="$", fill="#111827", font=("Arial", 12, "bold"))

        def draw_gem(x, y):
            pts = [x, y-14, x+12, y, x, y+14, x-12, y]
            c.create_polygon(pts, fill="#60A5FA", outline=self.BORDER, width=2)
            c.create_line(x, y-14, x, y+14, fill=self.BORDER, width=1)

        def draw_ticket(x, y):
            c.create_rectangle(x-14, y-10, x+14, y+10, fill="#A78BFA", outline=self.BORDER, width=2)
            c.create_text(x, y, text="T", fill="#111827", font=("Arial", 12, "bold"))

        # Reward rows
        rows = [
            ("1st Place", 100000, 1000, 100),
            ("2nd Place", 50000, 500, 50),
            ("3rd Place", 25000, 250, 25),
            ("4th Place", 10000, 100, 10),
            ("5th Place", 7500, 75, 8),
            ("6th Place", 5000, 50, 6),
            ("7th Place", 3000, 30, 4),
            ("8th Place", 2000, 20, 3),
            ("9th Place", 1500, 15, 2),
            ("10th Place", 1000, 10, 1),
        ]

        y0 = 110
        for i, (title, coins, gems, tickets) in enumerate(rows):
            y = y0 + i * 58
            c.create_rectangle(20, y-24, 500, y+24, fill=self.PANEL, outline=self.BORDER, width=2)
            c.create_text(40, y-8, text=title, anchor="w", fill=self.TEXT, font=("Arial", 13, "bold"))

            draw_coin(90, y+12)
            c.create_text(112, y+12, text=f"{coins:,} Gold", anchor="w", fill=self.TEXT, font=("Arial", 12, "bold"))

            draw_gem(260, y+12)
            c.create_text(282, y+12, text=f"{gems:,} Gems", anchor="w", fill=self.TEXT, font=("Arial", 12, "bold"))

            draw_ticket(410, y+12)
            c.create_text(432, y+12, text=f"{tickets:,} Tickets", anchor="w", fill=self.TEXT, font=("Arial", 12, "bold"))

        c.create_text(20, 690, text="Tip: Earn points by forging, selling, equipping better gear, leveling up, and rebirthing.",
                      anchor="w", fill=self.SUB, font=("Arial", 10, "bold"))


    def handle_tourn_click(self, event):
        x, y = event.x, event.y
        if 640 <= x <= 830 and 92 <= y <= 142:
            self.open_tourn_rewards()
            return

    def award_tourn_points(self, amount: int, reason: str = ""):
        """Add tournament points from normal gameplay actions."""
        self.ensure_tournament_state()
        amt = int(amount)
        if amt <= 0:
            return
        self.state.tourn_points += amt
        # small toast only in tournaments window to avoid spam
        if getattr(self, "active_tab", "") == "tournaments":
            if reason:
                self.toast(f"+{amt} pts ({reason})")
            else:
                self.toast(f"+{amt} pts")


    def ensure_tournament_state(self):
        now = time.time()
        if not getattr(self.state, "tourn_season_end", 0.0):
            self.state.tourn_points = 0
            self.state.tourn_season_end = now + 24*3600
            self.state.tourn_last_reset = now
            self.state.tourn_bots = self.generate_tournament_bots()

        if now >= self.state.tourn_season_end:
            self.state.tourn_points = 0
            self.state.tourn_season_end = now + 24*3600
            self.state.tourn_last_reset = now
            self.state.tourn_bots = self.generate_tournament_bots()
            self.toast("New tournament season started!")

    def generate_tournament_bots(self):
        names = ["PiQy3r","Player_5198","Player_4704","Player_4698","Player_3816","colJohnny","el lucha","K1ng","Nova","Byte","Rogue","Nexus","Shade","Warden","Slime","Revenant","Crawler","Astra","Echo","Zen"]
        random.shuffle(names)
        bots = []
        base = int(getattr(self.state, "tourn_points", 0))
        for i, n in enumerate(names[:15]):
            top_bias = 90 if i < 5 else 30
            p = max(0, base + random.randint(-20, top_bias + 80) + i*6)
            bots.append({"name": n, "points": p})
        bots.sort(key=lambda x: x["points"], reverse=True)
        return bots

    def tournament_rank(self, pts):
        tiers = [
            ("Bronze", 0, "#B45309"),
            ("Silver", 250, "#94A3B8"),
            ("Gold", 600, "#EAB308"),
            ("Platinum", 1100, "#22C55E"),
            ("Diamond", 1700, "#0EA5E9"),
            ("Champion", 2400, "#A855F7"),
        ]
        cur = tiers[0]
        for t in tiers:
            if pts >= t[1]:
                cur = t
        return cur

    def play_tournament_match(self):
        self.ensure_tournament_state()
        eq = self.state.equipped_weapon()
        pts = int(getattr(self.state, "tourn_points", 0))

        # Make tournament matches feel "worth it":
        # - harder wins (especially as your points climb)
        # - bigger win payout
        # - small participation payout on losses
        power = (eq.damage if eq else 10) + self.state.forge_level * 20 + int(getattr(self.state, "rebirths", 0)) * 200
        difficulty = 1.0 + (pts / 250.0)

        win_chance = 0.12 + (power / (500000.0 * difficulty))
        win_chance = max(0.08, min(0.60, win_chance))

        if random.random() < win_chance:
            gain = random.randint(40, 80)
            self.toast(f"Tournament win! +{gain} points")
        else:
            gain = random.randint(5, 12)
            self.toast(f"Tournament match complete. +{gain} points")
        self.state.tourn_points += gain

        # Bots progress (can pass you) — never removes your points
        for b in self.state.tourn_bots:
            b["points"] += random.randint(4, 28)
        self.state.tourn_bots.sort(key=lambda x: x["points"], reverse=True)

    def render_tourn_window(self):
        self.ensure_tournament_state()
        c = self.tw_canvas
        c.delete("all")
        W, H = 860, 760

        # Scroll offset for leaderboard
        if not hasattr(self, 'tourn_scroll'):
            self.tourn_scroll = 0

        pts = int(getattr(self.state, "tourn_points", 0))
        rank_name, _, rank_col = self.tournament_rank(pts)
        ends_in = max(0, int(self.state.tourn_season_end - time.time()))
        hh = ends_in // 3600
        mm = (ends_in % 3600) // 60
        ss = ends_in % 60
        timer = f"{hh:02d}:{mm:02d}:{ss:02d}"

        c.create_rectangle(20, 20, W - 20, 160, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(40, 50, text=f"{rank_name} League", anchor="w", fill=self.TEXT, font=("Arial", 22, "bold"))
        c.create_text(40, 84, text=f"Points: {pts}", anchor="w", fill=self.SUB, font=("Arial", 12, "bold"))
        c.create_text(40, 114, text=f"Season ends in: {timer}", anchor="w", fill="#22C55E", font=("Arial", 12, "bold"))

        # Rank badge (centered)
        cx, cy = W/2, 80
        c.create_oval(cx - 40, cy - 40, cx + 40, cy + 40, fill=rank_col, outline=self.BORDER, width=2)
        c.create_text(cx, cy, text=rank_name[0], fill="#111827", font=("Arial", 28, "bold"))

        c.create_rectangle(640, 92, 830, 142, fill="#10B981", outline=self.BORDER, width=2)
        c.create_text(735, 117, text="REWARDS", fill=self.TEXT, font=("Arial", 12, "bold"))

        c.create_rectangle(20, 180, W - 20, H - 20, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(40, 206, text="Leaderboard", anchor="w", fill=self.TEXT, font=("Arial", 14, "bold"))
        c.create_text(40, 232, text="Others can pass you — your points never drop.", anchor="w", fill=self.SUB, font=("Arial", 10, "bold"))

        entries = [{"name": "YOU", "points": pts, "is_you": True}] + list(getattr(self.state, "tourn_bots", []))
        entries.sort(key=lambda x: x["points"], reverse=True)
        entries = entries[:60]

        row_h = 54
        visible_rows = int((H - 280) / row_h)
        max_scroll = max(0, len(entries) - visible_rows)
        self.tourn_scroll = max(0, min(self.tourn_scroll, max_scroll))
        start_idx = self.tourn_scroll
        end_idx = min(len(entries), start_idx + visible_rows)

        y = 260
        for i, e in enumerate(entries[start_idx:end_idx], start=start_idx+1):
            fill = "#0B3B65" if e.get("is_you") else "#1F2937"
            c.create_rectangle(40, y, W - 40, y + 44, fill=fill, outline=self.BORDER, width=2)
            c.create_text(58, y + 22, text=str(i), anchor="w", fill=self.TEXT, font=("Arial", 12, "bold"))
            c.create_text(110, y + 22, text=e["name"], anchor="w", fill=self.TEXT, font=("Arial", 12, "bold"))
            c.create_text(W - 60, y + 22, text=str(e["points"]), anchor="e", fill=self.TEXT, font=("Arial", 12, "bold"))
            y += 54

# ---------- Shop UI ----------
    def open_shop(self):
        if self.shop_window and self.shop_window.winfo_exists():
            self.shop_window.lift()
            self.render_shop()
            return
        self.shop_window = tk.Toplevel(self.root)
        self.shop_window.title("Shop")
        self.shop_window.geometry("820x820")
        self.shop_window.configure(bg=self.BG)
        self.shop_window.transient(self.root)
        self.shop_window.resizable(False, False)

        self.shop_canvas = tk.Canvas(self.shop_window, bg=self.BG, highlightthickness=0)
        self.shop_canvas.pack(fill="both", expand=True)

        self.shop_scroll = tk.Scrollbar(self.shop_window, orient="vertical", command=self.shop_canvas.yview)
        self.shop_canvas.configure(yscrollcommand=self.shop_scroll.set)
        self.shop_scroll.pack(side="right", fill="y")

        def _on_mousewheel(event):
            try:
                self.shop_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        self.shop_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.code_msg = tk.StringVar(value="")
        self.code_entry = tk.Entry(self.shop_window, font=("Arial", 12))
        self.redeem_btn = tk.Button(self.shop_window, text="Redeem", font=("Arial", 10, "bold"),
                                    command=self.on_redeem_click, bg="#2563EB", fg="white")
        self.msg_label = tk.Label(self.shop_window, textvariable=self.code_msg, bg=self.BG, fg=self.TEXT,
                                  font=("Arial", 10, "bold"))

        self.shop_window.after(250, self.shop_refresh_loop)
        self.render_shop()

    
    def open_battle_pass(self):
        # Offline battle pass (quests feed XP; tiers give rewards including exclusive weapons)
        if hasattr(self, "battlepass_window") and self.battlepass_window and self.battlepass_window.winfo_exists():
            self.battlepass_window.lift()
            self.render_battle_pass()
            return
        self.battlepass_window = tk.Toplevel(self.root)
        self.battlepass_window.title("Battle Pass (Alpha)")
        self.battlepass_window.geometry("880x840")
        self.battlepass_window.configure(bg=self.BG)
        self.battlepass_window.transient(self.root)
        self.battlepass_window.resizable(False, False)

        self.bp_canvas = tk.Canvas(self.battlepass_window, bg=self.BG, highlightthickness=0)
        self.bp_canvas.pack(fill="both", expand=True)

        # battle pass fake scroll state
        self.bp_scroll_idx = int(getattr(self.state, "bp_scroll_idx", 0))
        self.bp_canvas.bind("<MouseWheel>", self._on_bp_wheel)
        self.battlepass_window.bind("<MouseWheel>", self._on_bp_wheel)

        self.render_battle_pass()

    def render_battle_pass(self):
        if not (hasattr(self, "bp_canvas") and self.bp_canvas.winfo_exists()):
            return
        c = self.bp_canvas
        c.delete("all")

        tier = int(getattr(self.state, "bp_tier", 1))
        xp = int(getattr(self.state, "bp_xp", 0))
        pct = min(1.0, xp / max(1, BP_XP_PER_TIER))

        c.create_text(24, 22, text="BATTLE PASS", anchor="w", fill=self.TEXT, font=("Arial", 18, "bold"))
        c.create_text(24, 50, text="Earn XP from Quests. Claim tiers for rewards (includes exclusive weapons).",
                      anchor="w", fill=self.SUB, font=("Arial", 11, "bold"))

        c.create_text(24, 86, text=f"Tier {tier} • XP {xp}/{BP_XP_PER_TIER}", anchor="w",
                      fill=self.TEXT, font=("Arial", 14, "bold"))
        bar_x1, bar_y1 = 24, 110
        bar_x2, bar_y2 = 24 + 820, 130
        c.create_rectangle(bar_x1, bar_y1, bar_x2, bar_y2, fill="#2D3748", outline="")
        c.create_rectangle(bar_x1, bar_y1, bar_x1 + int((bar_x2 - bar_x1) * pct), bar_y2, fill="#22C55E", outline="")

        claimed = set(getattr(self.state, "bp_claimed_tiers", []))
        # tiers list (scrollable)
        # destroy old tier buttons (avoid stacking)
        for _b in getattr(self, "bp_btns", []):
            try:
                _b.destroy()
            except Exception:
                pass
        self.bp_btns = []

        start_y = 160
        row_h = 54
        total_tiers = max(BP_REWARDS.keys()) if isinstance(BP_REWARDS, dict) and BP_REWARDS else 20
        rows_vis = BP_ROWS_VISIBLE
        max_scroll = max(0, total_tiers - rows_vis)

        self.bp_scroll_idx = int(getattr(self, "bp_scroll_idx", 0))
        if self.bp_scroll_idx < 0:
            self.bp_scroll_idx = 0
        if self.bp_scroll_idx > max_scroll:
            self.bp_scroll_idx = max_scroll
        try:
            self.state.bp_scroll_idx = self.bp_scroll_idx
        except Exception:
            pass

        y = start_y
        for i in range(rows_vis):
            t = 1 + self.bp_scroll_idx + i
            if t > total_tiers:
                break
            r = self.bp_reward_for_tier(t)
            c.create_rectangle(24, y, 24 + 820, y + 44, fill="#1F2937", outline="#334155")
            c.create_text(40, y + 22, text=f"Tier {t}", anchor="w", fill=self.TEXT, font=("Arial", 12, "bold"))

            if r.get("type") == "weapon":
                label = f"WEAPON: {r.get('name')} ({r.get('rarity')})"
            else:
                parts = []
                if r.get("hammers", 0): parts.append(f"{r.get('hammers')} Hammers")
                if r.get("coins", 0): parts.append(f"{r.get('coins')} Coins")
                if r.get("gems", 0): parts.append(f"{r.get('gems')} Gems")
                label = " • ".join(parts) if parts else "Reward"
            c.create_text(220, y + 22, text=label, anchor="w", fill=self.SUB, font=("Arial", 12, "bold"))

            claimed = set(getattr(self.state, "bp_claimed_tiers", []))
            can_claim = (t <= tier) and (t not in claimed)
            btn_txt = "CLAIM" if can_claim else ("CLAIMED" if t in claimed else "LOCKED")
            btn_col = "#16A34A" if can_claim else "#374151"
            b = tk.Button(self.battlepass_window, text=btn_txt,
                          command=(lambda tt=t: self.bp_claim_tier(tt)) if can_claim else None,
                          bg=btn_col, fg="white", relief="flat", activebackground=btn_col)
            self.bp_btns.append(b)
            c.create_window(24 + 820 - 90, y + 22, window=b, width=80, height=28)

            y += row_h

        # fake scrollbar (visual)
        list_top = start_y
        list_bottom = start_y + rows_vis * row_h - 10
        track_x1 = 24 + 820 + 10
        track_x2 = track_x1 + 10
        c.create_rectangle(track_x1, list_top, track_x2, list_bottom, fill="#111827", outline="#334155")
        if max_scroll > 0:
            track_h = (list_bottom - list_top)
            thumb_h = max(24, int(track_h * (rows_vis / max(1, total_tiers))))
            thumb_y = list_top + int((self.bp_scroll_idx / max_scroll) * max(1, (track_h - thumb_h)))
            c.create_rectangle(track_x1 + 1, thumb_y, track_x2 - 1, thumb_y + thumb_h, fill="#64748B", outline="")

        tip_y = list_bottom + 28
        c.create_text(24, tip_y, text="Tip: Scroll to view more tiers. Quests are intentionally easy so players can relax and still progress.",
                      anchor="w", fill=self.SUB, font=("Arial", 10, "bold"))


    def _on_bp_wheel(self, event):
        # Mousewheel scroll for Battle Pass tiers
        delta = -1 if getattr(event, "delta", 0) > 0 else 1
        self.bp_scroll_idx = int(getattr(self, "bp_scroll_idx", 0)) + delta

        total_tiers = max(BP_REWARDS.keys()) if isinstance(BP_REWARDS, dict) and BP_REWARDS else 20
        rows_vis = BP_ROWS_VISIBLE
        max_scroll = max(0, total_tiers - rows_vis)
        if self.bp_scroll_idx < 0:
            self.bp_scroll_idx = 0
        if self.bp_scroll_idx > max_scroll:
            self.bp_scroll_idx = max_scroll
        try:
            self.state.bp_scroll_idx = self.bp_scroll_idx
        except Exception:
            pass
        self.render_battle_pass()

    def open_about(self):
        if hasattr(self, "about_window") and self.about_window and self.about_window.winfo_exists():
            self.about_window.lift()
            return

        self.about_window = tk.Toplevel(self.root)
        self.about_window.title("About")
        self.about_window.geometry("860x740")
        self.about_window.configure(bg=self.BG)
        self.about_window.transient(self.root)
        self.about_window.resizable(False, False)

        # Header
        title = tk.Label(self.about_window, text="ABOUT FORGE BATTLER",
                         bg=self.BG, fg=self.TEXT, font=("Arial", 18, "bold"))
        title.pack(anchor="w", padx=24, pady=(18, 0))

        subtitle = tk.Label(
            self.about_window,
            text=f"Created by the developer (you). Alpha build — expect changes.\nBuild: {APP_VERSION} [{BUILD_ID}] (file: {os.path.basename(__file__)})",
            bg=self.BG, fg=self.SUB, font=("Arial", 12, "bold")
        )
        subtitle.pack(anchor="w", padx=24, pady=(6, 14))

        # Scrollable text area (fixes overflow / clipping)
        outer = tk.Frame(self.about_window, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=24, pady=(0, 14))

        box = tk.Frame(outer, bg="#111827", highlightbackground="#334155", highlightthickness=1)
        box.pack(fill="both", expand=True)

        sb = tk.Scrollbar(box)
        sb.pack(side="right", fill="y")

        txt = tk.Text(
            box,
            bg="#111827",
            fg=self.TEXT,
            insertbackground=self.TEXT,
            wrap="word",
            font=("Arial", 12, "bold"),
            yscrollcommand=sb.set,
            relief="flat",
            bd=0,
            padx=14,
            pady=12
        )
        txt.pack(side="left", fill="both", expand=True)
        sb.config(command=txt.yview)

        about_text = """Creator / Contact:
• Creator: AySoulXYZ (Idle Battler dev)
• Twitch: twitch.tv/ayysoulxyz
• This is an indie alpha project — updates will be frequent.

PC Requirements (Recommended):
• Windows 10/11 (64-bit)
• Python 3.12+ installed (if running the .py source)
• 2 GB RAM (4 GB recommended)
• Any modern CPU (2015+ is fine)
• ~200 MB free disk space

Safety / Virus Notes:
• This project is a Python game. It does NOT steal data.
• If Windows SmartScreen warns you, you can scan the file on VirusTotal.
• The creator will post a video showing a VirusTotal scan (0 detections).

How to Run / Updates:
• If you downloaded source: open the folder, run the .py with Python.
• If you downloaded a packaged build: just run the .exe.
• Check the project page for the newest version (patch notes + downloads).

Saving / Data:
• The game auto-saves. Closing the window also saves.

Alpha Disclaimer:
• Balance, UI, and features will keep changing.
• If something looks weird, it’s probably a bug — report it!

Thanks for playing. More updates coming soon.
"""

        txt.insert("1.0", about_text)
        txt.config(state="disabled")


    # ---------- Settings ----------
    def open_settings(self):
        if hasattr(self, "settings_window") and self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        self.settings_window.geometry("520x260")
        self.settings_window.configure(bg=self.BG)

        tk.Label(self.settings_window, text="Settings", bg=self.BG, fg=self.TEXT, font=("Arial", 18, "bold")).pack(pady=(14, 10))

        frm = tk.Frame(self.settings_window, bg=self.BG)
        frm.pack(fill="x", padx=18, pady=8)

        # Fullscreen toggle
        self.fullscreen_var = tk.BooleanVar(value=bool(getattr(self.state, "fullscreen", False)))
        chk = tk.Checkbutton(
            frm,
            text="Fullscreen",
            variable=self.fullscreen_var,
            command=self.toggle_fullscreen,
            bg=self.BG,
            fg=self.TEXT,
            activebackground=self.BG,
            activeforeground=self.TEXT,
            selectcolor=self.BG
        )
        chk.pack(anchor="w")

        # Save path display (helps users + supports public release trust)
        tk.Label(self.settings_window, text=f"Save file location:\n{SAVE_PATH}", bg=self.BG, fg=self.SUB, justify="left", wraplength=480).pack(padx=18, pady=(10, 6), anchor="w")

        tk.Button(self.settings_window, text="Close", command=self.settings_window.destroy).pack(pady=10)

    def exit_fullscreen(self):
        if getattr(self, "fullscreen", False):
            self.fullscreen = False
            self.root.attributes("-fullscreen", False)
            self.toast("Fullscreen OFF")

    def toggle_fullscreen(self):
        new_val = bool(self.fullscreen_var.get()) if hasattr(self, "fullscreen_var") else (not bool(getattr(self.state, "fullscreen", False)))
        self.state.fullscreen = new_val
        self.apply_fullscreen()
        self.save_game()

    def apply_fullscreen(self):
        try:
            self.root.attributes("-fullscreen", bool(getattr(self.state, "fullscreen", False)))
            if bool(getattr(self.state, "fullscreen", False)):
                # Allow ESC to exit fullscreen
                self.root.bind("<Escape>", lambda e: self._exit_fullscreen())
            else:
                self.root.unbind("<Escape>")
        except Exception:
            pass

    def _exit_fullscreen(self):
        self.state.fullscreen = False
        if hasattr(self, "fullscreen_var"):
            try:
                self.fullscreen_var.set(False)
            except Exception:
                pass
        self.apply_fullscreen()
        self.save_game()

    # ---------- Terms of Service Agreement ----------
    def _start_game_loop(self):
        if getattr(self, "_game_loop_started", False):
            return
        self._game_loop_started = True
        # Apply fullscreen preference on startup
        self.apply_fullscreen()
        self.tick()

    def show_tos_dialog(self):
        # If already accepted (race), start loop
        if bool(getattr(self.state, "tos_accepted", False)):
            self._start_game_loop()
            return

        if hasattr(self, "tos_window") and self.tos_window and self.tos_window.winfo_exists():
            self.tos_window.lift()
            return

        self.tos_window = tk.Toplevel(self.root)
        self.tos_window.title("Terms of Service & License Agreement")
        self.tos_window.geometry("760x640")
        self.tos_window.configure(bg=self.BG)
        self.tos_window.grab_set()  # modal

        tk.Label(self.tos_window, text="Please read and agree to continue", bg=self.BG, fg=self.TEXT, font=("Arial", 16, "bold")).pack(pady=(14, 8))

        container = tk.Frame(self.tos_window, bg=self.BG)
        container.pack(fill="both", expand=True, padx=14, pady=10)

        yscroll = tk.Scrollbar(container)
        yscroll.pack(side="right", fill="y")

        txt = tk.Text(container, wrap="word", yscrollcommand=yscroll.set, bg=self.PANEL, fg=self.TEXT, insertbackground=self.TEXT, relief="flat")
        txt.pack(side="left", fill="both", expand=True)
        yscroll.config(command=txt.yview)

        tos_body = """FORGE BATTLER — TERMS OF SERVICE (TOS)

By downloading or using Idle Battler, you agree:

1) Ownership
Idle Battler and its source code are owned by AySoulXYZ. You may not claim ownership.

2) Allowed Use
You may download and play the game for PERSONAL, NON-COMMERCIAL use only.

3) Prohibited Actions
You may NOT:
- Re-upload or redistribute the game or its source code
- Sell or monetize the game or any modified versions
- Remove or modify copyright / license notices
- Attempt to bypass progression systems for competitive advantage
- Distribute cheats, modified builds, or "god mode" versions

4) Save Integrity / Cheating
This is an offline game. If you modify local files, your progress may break. Any redistribution of modified builds is prohibited.

5) No Warranty
This game is provided AS IS, without warranty of any kind.

Scroll to the bottom to enable the Agree button.
"""

        # If About already contains the license, we keep this short but clear.
        txt.insert("1.0", tos_body)
        txt.config(state="disabled")

        btn_frame = tk.Frame(self.tos_window, bg=self.BG)
        btn_frame.pack(fill="x", padx=14, pady=(0, 14))

        self._agree_btn = tk.Button(btn_frame, text="Agree", state="disabled", command=self._accept_tos)
        self._agree_btn.pack(side="right")

        tk.Button(btn_frame, text="Exit", command=self.root.destroy).pack(side="right", padx=10)

        # Enable Agree only when scrolled to bottom
        def check_bottom(*_):
            try:
                # yview returns (first, last) in 0..1
                first, last = txt.yview()
                if last >= 0.999:
                    self._agree_btn.config(state="normal")
            except Exception:
                pass

        # bind scroll updates
        txt.bind("<ButtonRelease-1>", lambda e: check_bottom())
        txt.bind("<KeyRelease>", lambda e: check_bottom())
        self.tos_window.after(200, check_bottom)
        self.tos_window.after(600, check_bottom)

    def _accept_tos(self):
        self.state.tos_accepted = True
        self.state.tos_accepted_version = str(GAME_VERSION)
        try:
            if hasattr(self, "tos_window") and self.tos_window and self.tos_window.winfo_exists():
                self.tos_window.grab_release()
                self.tos_window.destroy()
        except Exception:
            pass
        self.save_game()
        self.toast("Thanks! You can play now.", 2.0)
        self._start_game_loop()

    def on_redeem_click(self):
        msg = self.redeem_code(self.code_entry.get())
        self.code_msg.set(msg)
        self.render_shop()

    def shop_refresh_loop(self):
        if self.shop_window and self.shop_window.winfo_exists():
            self.render_shop()
            self.shop_window.after(250, self.shop_refresh_loop)

    def shop_btn(self, c, x, y, w, h, text, fill, action):
        rect = c.create_rectangle(x, y, x + w, y + h, fill=fill, outline="#0A0D13", width=2)
        txt = c.create_text(x + w / 2, y + h / 2, text=text, fill="white", font=("Arial", 10, "bold"))
        for item in (rect, txt):
            c.tag_bind(item, "<Button-1>", lambda e, fn=action: fn())

    def render_shop(self):
        if not (self.shop_window and self.shop_window.winfo_exists()):
            return
        c = self.shop_canvas
        c.delete("all")

        header = f"SHOP    🔨 {self.state.hammers}   💰 {self.state.coins}   💎 {self.state.gems}"
        if self.state.ascended_unlocked:
            header += f"   🎟 {self.state.tickets}"
        c.create_text(20, 18, text=header, anchor="w", fill=self.TEXT, font=("Arial", 16, "bold"))

        c.create_rectangle(20, 40, 800, 190, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(34, 60, text="Quick Claims (timer replaces ads)", anchor="w", fill=self.TEXT, font=("Arial", 13, "bold"))
        keys = ["coin", "gem", "hammer"]
        x = 34
        for key in keys:
            rt = self.state.rewards[key]
            c.create_rectangle(x, 80, x + 245, 170, fill=self.PANEL2, outline="#4B5563", width=2)
            c.create_text(x + 12, 98, text=rt.label, anchor="w", fill=self.TEXT, font=("Arial", 11, "bold"))
            c.create_text(x + 12, 120, text=f"+{rt.reward_amount} {rt.reward_kind}", anchor="w", fill=self.SUB, font=("Arial", 10))
            state_text = "Ready" if rt.is_ready() else f"{rt.seconds_left()}s"
            color = "#16A34A" if rt.is_ready() else "#2563EB"
            self.shop_btn(c, x + 12, 136, 120, 26, state_text, color, lambda k=key: self.claim_reward(k))
            c.create_text(x + 145, 149, text=f"Next cd: {rt.current_seconds}s", anchor="w", fill=self.SUB, font=("Arial", 8))
            x += 258

        c.create_rectangle(20, 210, 800, 330, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(34, 230, text="Exchanges", anchor="w", fill=self.TEXT, font=("Arial", 13, "bold"))
        c.create_text(34, 260, text="350 coins → 1 hammer", anchor="w", fill=self.TEXT, font=("Arial", 10))
        self.shop_btn(c, 240, 246, 120, 28, "Buy", "#2563EB", self.exchange_buy_hammer_with_coins)

        c.create_text(34, 292, text="100 gems → 5 hammers", anchor="w", fill=self.TEXT, font=("Arial", 10))
        self.shop_btn(c, 240, 278, 120, 28, "Buy", "#2563EB", self.exchange_buy_hammers_with_gems)

        c.create_text(430, 260, text="250 gems → 3,500 coins", anchor="w", fill=self.TEXT, font=("Arial", 10))
        self.shop_btn(c, 640, 246, 120, 28, "Buy", "#2563EB", self.exchange_buy_coins_with_gems)

        c.create_rectangle(20, 350, 800, 600, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(34, 370, text="Bundles (endless offers)", anchor="w", fill=self.TEXT, font=("Arial", 13, "bold"))

        y = 395
        for i, offer in enumerate(self.bundle_offers[:3]):
            c.create_rectangle(34, y, 764, y + 58, fill=self.PANEL2, outline="#4B5563")
            c.create_text(48, y + 18, text=offer.title, anchor="w", fill=self.TEXT, font=("Arial", 11, "bold"))
            line = f"+{offer.reward_coins} coins, +{offer.reward_gems} gems, +{offer.reward_hammers} hammers"
            c.create_text(48, y + 40, text=line, anchor="w", fill=self.SUB, font=("Arial", 9))
            c.create_text(520, y + 29, text=f"Wait: {offer.wait_seconds}s", anchor="e", fill=self.TEXT, font=("Arial", 10, "bold"))
            if len(self.pending_bundless) < 3:
                self.shop_btn(c, 640, y + 16, 120, 28, "Start", "#7C3AED", lambda idx=i: self.start_bundle(idx))
            else:
                self.shop_btn(c, 640, y + 16, 120, 28, "FULL", "#374151", lambda: None)
            y += 70

        c.create_rectangle(20, 610, 800, 690, fill=self.PANEL, outline=self.BORDER, width=2)

        if self.pending_bundless:
            c.create_text(34, 630, text=f"Active bundle timers: {len(self.pending_bundless)}/3",
                          anchor="w", fill=self.TEXT, font=("Arial", 10, "bold"))
            yb = 646
            for i, pb in enumerate(self.pending_bundless[:3]):
                left = max(0, int(pb.ready_at - time.time()))
                ready = left <= 0
                line = f"{i + 1}) {pb.offer.title} — {'READY' if ready else str(left) + 's'}"
                c.create_text(34, yb, text=line, anchor="w", fill=self.TEXT if ready else self.SUB, font=("Arial", 9, "bold"))
                self.shop_btn(c, 660, yb - 10, 120, 22, "Claim", "#16A34A" if ready else "#374151", lambda idx=i: self.claim_bundle(idx))
                yb += 16
        else:
            c.create_text(34, 630, text="No active bundle timers.", anchor="w", fill=self.SUB, font=("Arial", 10))

        c.create_text(34, 720, text="Creator Code:", anchor="w", fill=self.TEXT, font=("Arial", 10, "bold"))
        c.create_window(125, 720, window=self.code_entry, width=180, height=26)
        c.create_window(320, 720, window=self.redeem_btn, width=80, height=26)
        c.create_window(560, 720, window=self.msg_label, width=420, height=26)
        c.configure(scrollregion=(0, 0, 820, 900))

    # ---------- Rarity UI ----------
    def open_rarity(self):
        if self.rarity_window and self.rarity_window.winfo_exists():
            self.rarity_window.lift()
            self.render_rarity()
            return
        self.rarity_window = tk.Toplevel(self.root)
        self.rarity_window.title("Rarity Odds")
        self.rarity_window.geometry("780x740")
        self.rarity_window.configure(bg=self.BG)
        self.rarity_window.transient(self.root)
        self.rarity_window.resizable(False, False)

        self.rarity_canvas = tk.Canvas(self.rarity_window, bg=self.BG, highlightthickness=0)
        self.rarity_canvas.pack(fill="both", expand=True)

        # Mousewheel scroll inside this window (fake scroll)
        def _on_mousewheel(e):
            try:
                if e.delta > 0:
                    self.rarity_scroll = getattr(self, "rarity_scroll", 0) - 1
                else:
                    self.rarity_scroll = getattr(self, "rarity_scroll", 0) + 1
            except Exception:
                pass
            self.render_rarity()

        self.rarity_canvas.bind("<MouseWheel>", _on_mousewheel)


        self.rarity_window.after(250, self.rarity_refresh_loop)
        self.render_rarity()

    def rarity_refresh_loop(self):
        if self.rarity_window and self.rarity_window.winfo_exists():
            self.render_rarity()
            self.rarity_window.after(250, self.rarity_refresh_loop)

    def render_rarity(self):
        if not (self.rarity_window and self.rarity_window.winfo_exists()):
            return
        c = self.rarity_canvas
        c.delete("all")

        if not hasattr(self, "rarity_scroll"):
            self.rarity_scroll = 0

        lvl = self.state.forge_level
        next_lvl = min(self.forge_level_cap_visible(), lvl + 1)

        c.create_text(20, 18, text="RARITY ODDS", anchor="w", fill=self.TEXT, font=("Arial", 16, "bold"))
        c.create_text(20, 42, text=f"Forge Level {lvl}  →  {next_lvl}", anchor="w", fill=self.SUB, font=("Arial", 11, "bold"))

        # Panel box
        box_x1, box_y1, box_x2, box_y2 = 20, 64, 760, 650
        c.create_rectangle(box_x1, box_y1, box_x2, box_y2, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(40, 88, text="Rarity", anchor="w", fill=self.TEXT, font=("Arial", 12, "bold"))
        c.create_text(560, 88, text=f"Level {lvl}", anchor="e", fill=self.TEXT, font=("Arial", 12, "bold"))
        c.create_text(740, 88, text=f"Level {next_lvl}", anchor="e", fill=self.TEXT, font=("Arial", 12, "bold"))

        # Only show post-35 rarities if unlocked
        show_rarities = RARITIES_ALL if self.state.ascended_unlocked else BASE_RARITIES

        w_now = rarity_weights_for_level(lvl, self.state.ascended_unlocked)
        w_next = rarity_weights_for_level(next_lvl, self.state.ascended_unlocked)

        list_top = 110
        row_h = 34
        row_step = row_h + 6
        list_bottom = box_y2 - 12
        rows_fit = max(1, int((list_bottom - list_top) // row_step))
        self._rarity_rows_fit = rows_fit
        max_scroll = max(0, len(show_rarities) - rows_fit)
        self.rarity_scroll = clamp(self.rarity_scroll, 0, max_scroll)

        start = self.rarity_scroll
        visible = show_rarities[start:start + rows_fit]

        y = list_top
        for r in visible:
            color = RARITY_COLORS.get(r, "#9AA0A6")
            both_zero = (w_now.get(r, 0.0) <= 0.0) and (w_next.get(r, 0.0) <= 0.0)
            row_fill = "#1F2937" if both_zero else self.PANEL2

            c.create_rectangle(34, y, 746, y + row_h, fill=row_fill, outline="#4B5563")
            c.create_rectangle(34, y, 44, y + row_h, fill=color, outline="")
            c.create_text(56, y + row_h / 2, text=r, anchor="w", fill=color if not both_zero else "#6B7280",
                          font=("Arial", 11, "bold"))
            c.create_text(560, y + row_h / 2, text=fmt_pct(w_now.get(r, 0.0)), anchor="e",
                          fill=self.TEXT if not both_zero else "#6B7280", font=("Arial", 11, "bold"))
            c.create_text(740, y + row_h / 2, text=fmt_pct(w_next.get(r, 0.0)), anchor="e",
                          fill=self.TEXT if not both_zero else "#6B7280", font=("Arial", 11, "bold"))
            y += row_step

        # Fake scrollbar (visual + wheel)
        track_x1, track_x2 = 748, 756
        c.create_rectangle(track_x1, list_top, track_x2, list_bottom, fill="#111827", outline="#374151")
        if len(show_rarities) > rows_fit:
            frac = rows_fit / max(1, len(show_rarities))
            thumb_h = max(24, int((list_bottom - list_top) * frac))
            thumb_y = list_top + int((list_bottom - list_top - thumb_h) * (self.rarity_scroll / max(1, max_scroll)))
            c.create_rectangle(track_x1 + 1, thumb_y, track_x2 - 1, thumb_y + thumb_h, fill="#6B7280", outline="")

        c.create_rectangle(20, 665, 760, 720, fill=self.PANEL, outline=self.BORDER, width=2)
        tip = "Tip: Endgame rarities + dungeons unlock at Forge 35. (Scroll wheel works here)"
        c.create_text(40, 692, text=tip, anchor="w", fill=self.SUB, font=("Arial", 10, "bold"))

    def select_item(self, idx):
        self.selected_idx = idx
        self.render()

    def on_mousewheel_main(self, event):
        """Mousewheel scrolling for main-canvas lists (inventory)."""
        try:
            x, y = event.x, event.y
            # Normalize ascension unlock: once unlocked, it stays available after rebirth resets forge level
            if self.state.forge_level >= 35 or self.state.ascended_unlocked:
                self.state.ascension_unlocked = True

        except Exception:
            return

        # Inventory scrolling
        box = getattr(self, "_inventory_box", None)
        if box:
            x1, y1, x2, y2 = box
            if x1 <= x <= x2 and y1 <= y <= y2:
                step = -1 if getattr(event, "delta", 0) > 0 else 1
                rows_fit = getattr(self, "_inventory_rows_fit", 10)
                max_scroll = max(0, len(self.state.inventory) - rows_fit)
                self.inventory_scroll = clamp(getattr(self, "inventory_scroll", 0) + step, 0, max_scroll)
                self.render()
                return

    def handle_click(self, event):
        x, y = event.x, event.y

        bx1, by1, bx2, by2 = self.battle_rect
        in_battle = (bx1 <= x <= bx2) and (by1 <= y <= by2)

        for x1, y1, x2, y2, fn in reversed(self.click_regions):
            if x1 <= x <= x2 and y1 <= y <= y2:
                fn()
                return

        if in_battle:
            self.player_attack(1.0)
            self.render()
            return

# =========================================================
# TICKET / ASCENSION INSTALL (PASTE ABOVE if __name__ == "__main__": )
# Adds:
# - tickets + skills saved/loaded
# - ASCENSION button (only shows at forge 35+)
# - Ascension window with ticket skill upgrades
# - Skills apply to damage, lifesteal, and auto-forge speed
# Works by monkey-patching ForgeBattlerApp so you don't edit tons of places.
# =========================================================

def _install_ticket_ascension_system():
    # ---- Safety: if class isn't defined yet, do nothing
    if "ForgeBattlerApp" not in globals():
        return

    App = ForgeBattlerApp

    # ---------------------------
    # Helpers: ensure attributes exist
    # ---------------------------
    def _ensure_ticket_fields(app):
        # Tickets
        if not hasattr(app.state, "tickets"):
            app.state.tickets = 0
        # Skill levels: dict name -> int level
        if not hasattr(app.state, "skills") or not isinstance(getattr(app.state, "skills", None), dict):
            app.state.skills = {}
        # Skill ascension tiers: dict name -> int tier (I, II, III...)
        if not hasattr(app.state, "skill_tiers") or not isinstance(getattr(app.state, "skill_tiers", None), dict):
            app.state.skill_tiers = {}
        # Skill ascension stacks: each ASCEND adds 1; 5 stacks -> +1 tier
        if not hasattr(app.state, "skill_asc_stacks") or not isinstance(getattr(app.state, "skill_asc_stacks", None), dict):
            app.state.skill_asc_stacks = {}

    # ---------------------------
    # Patch load_game: call original, then load tickets/skills from save if present
    # ---------------------------
    _orig_load_game = App.load_game

    def _load_game_patched(self):
        _orig_load_game(self)
        _ensure_ticket_fields(self)

        # Pull tickets/skills from save file if they exist
        try:
            if os.path.exists(SAVE_PATH):
                with open(SAVE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.state.tickets = int(data.get("tickets", getattr(self.state, "tickets", 0)))
                    sd = data.get("skills", {})
                    if isinstance(sd, dict):
                        self.state.skills = {str(k): int(v) for k, v in sd.items()}
                    td = data.get("skill_tiers", {})
                    if isinstance(td, dict):
                        self.state.skill_tiers = {str(k): int(v) for k, v in td.items()}
                    ad = data.get("skill_asc_stacks", {})
                    if isinstance(ad, dict):
                        self.state.skill_asc_stacks = {str(k): int(v) for k, v in ad.items()}
        except Exception:
            pass

    App.load_game = _load_game_patched

    # ---------------------------
    # Patch save_game: call original, then inject tickets/skills into JSON
    # ---------------------------
    _orig_save_game = App.save_game

    def _save_game_patched(self):
        _ensure_ticket_fields(self)
        _orig_save_game(self)

        # Post-write inject (so we don't rewrite your whole save system)
        try:
            if os.path.exists(SAVE_PATH):
                with open(SAVE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data["tickets"] = int(getattr(self.state, "tickets", 0))
                    data["skills"] = dict(getattr(self.state, "skills", {}))
                    data["skill_tiers"] = dict(getattr(self.state, "skill_tiers", {}))
                    data["skill_asc_stacks"] = dict(getattr(self.state, "skill_asc_stacks", {}))
                    with open(SAVE_PATH, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
        except Exception:
            pass

    App.save_game = _save_game_patched

    # ---------------------------
    # Skill getters / costs
    # ---------------------------
    def roman_numeral(self, n: int) -> str:
        n = int(n)
        if n <= 0:
            return ""
        pairs = [
            (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
            (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
            (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
        ]
        out = []
        for val, sym in pairs:
            while n >= val:
                out.append(sym)
                n -= val
        return "".join(out)

    def skill_tier(self, name: str) -> int:
        _ensure_ticket_fields(self)
        return int(getattr(self.state, "skill_tiers", {}).get(name, 0))

    def skill_asc_stack(self, name: str) -> int:
        _ensure_ticket_fields(self)
        return int(getattr(self.state, "skill_asc_stacks", {}).get(name, 0))

    def ascend_cost(self, name: str, next_tier: int) -> int:
        base = {
            "Berserk": 800,
            "Lifesteal": 1000,
            "Crit Boost": 1200,
            "Forge Rush": 1400,
        }.get(name, 1000)
        return int(base * (1.8 ** max(0, next_tier - 1)))

    def ascend_skill(self, name: str):
        _ensure_ticket_fields(self)
        lvl = self.skill_level(name)
        if lvl < 10:
            return

        # Each ascend adds 1 stack. 5 stacks -> +1 Roman tier.
        stacks = self.skill_asc_stack(name)
        cur_tier = self.skill_tier(name)

        nxt_tier_for_cost = cur_tier + 1  # cost roughly tracks the next tier you're working toward
        cost = self.ascend_cost(name, nxt_tier_for_cost)
        if self.state.tickets < cost:
            return

        self.state.tickets -= cost

        stacks += 1
        if stacks >= 5:
            stacks = 0
            self.state.skill_tiers[name] = cur_tier + 1

        self.state.skill_asc_stacks[name] = stacks
        self.state.skills[name] = 0  # reset levels for next climb

        try:
            self.render()
        except Exception:
            pass
        try:
            self.render_ascension()
        except Exception:
            pass

    def skill_level(self, name: str) -> int:
        _ensure_ticket_fields(self)
        return int(self.state.skills.get(name, 0))

    def skill_cost(self, name: str, next_level: int) -> int:
        base = {
            "Berserk": 40,
            "Lifesteal": 60,
            "Crit Boost": 75,
            "Forge Rush": 90,
        }.get(name, 75)
        # Growth curve (tune anytime)
        return int(base * (1.35 ** max(0, next_level - 1)))

    def buy_skill_level(self, name: str):
        _ensure_ticket_fields(self)
        lvl = self.skill_level(name)
        nxt = lvl + 1
        if nxt > 10:
            return
        cost = self.skill_cost(name, nxt)
        if self.state.tickets < cost:
            return
        self.state.tickets -= cost
        self.state.skills[name] = nxt
        try:
            self.render()
        except Exception:
            pass
        try:
            self.render_ascension()
        except Exception:
            pass

    # ---------------------------
    # Ascension Window UI
    # ---------------------------
    def open_ascension(self):
        _ensure_ticket_fields(self)
        if getattr(self, "asc_window", None) and self.asc_window.winfo_exists():
            self.asc_window.lift()
            self.render_ascension()
            return

        self.asc_window = tk.Toplevel(self.root)
        self.asc_window.title("Ascension")
        self.asc_window.geometry("760x560")
        self.asc_window.configure(bg=self.BG)
        self.asc_window.transient(self.root)
        self.asc_window.resizable(False, False)

        self.asc_canvas = tk.Canvas(self.asc_window, bg=self.BG, highlightthickness=0)
        self.asc_canvas.pack(fill="both", expand=True)

        self.asc_window.after(200, self.ascension_refresh_loop)
        self.render_ascension()

    def ascension_refresh_loop(self):
        if getattr(self, "asc_window", None) and self.asc_window.winfo_exists():
            self.render_ascension()
            self.asc_window.after(250, self.ascension_refresh_loop)

    def render_ascension(self):
        if not (getattr(self, "asc_window", None) and self.asc_window.winfo_exists()):
            return
        _ensure_ticket_fields(self)

        c = self.asc_canvas
        c.delete("all")

        c.create_text(20, 18, text="ASCENSION", anchor="w", fill=self.TEXT, font=("Arial", 16, "bold"))
        c.create_text(
            20, 44,
            text=f"Forge {self.state.forge_level}   •   🎟 {self.state.tickets} tickets",
            anchor="w", fill=self.SUB, font=("Arial", 11, "bold")
        )

        c.create_rectangle(20, 70, 740, 520, fill=self.PANEL, outline=self.BORDER, width=2)
        c.create_text(40, 96, text="Ticket Skills (permanent boosts)", anchor="w",
                      fill=self.TEXT, font=("Arial", 12, "bold"))

        skills = [
            ("Berserk", "Always-on damage bonus."),
            ("Lifesteal", "Heal a bit when you hit."),
            ("Crit Boost", "Crit chance boost (we’ll wire this later)."),
            ("Forge Rush", "Auto-forge speed boost."),
        ]

        y = 130
        for name, desc in skills:
            lvl = self.skill_level(name)
            nxt = lvl + 1
            cost = self.skill_cost(name, nxt) if nxt <= 10 else None

            c.create_rectangle(40, y, 720, y + 78, fill=self.PANEL2, outline="#4B5563")
            tier_done = self.skill_tier(name)
            stacks = self.skill_asc_stack(name)
            # Show the Roman numeral as soon as you start working toward the next tier
            tier_show = tier_done + (1 if stacks > 0 else 0)
            tier_txt = self.roman_numeral(tier_show) if tier_show > 0 else ""
            tier_disp = (f" {tier_txt}" if tier_txt else "")
            stack_disp = (f"  • Ascend {stacks}/5" if (stacks > 0) else "")
            c.create_text(56, y + 18, text=f"{name}{tier_disp}{stack_disp}  (Lv {lvl}/10)", anchor="w",
                          fill=self.TEXT, font=("Arial", 11, "bold"))
            c.create_text(56, y + 44, text=desc, anchor="w", fill=self.SUB, font=("Arial", 10))

            if lvl >= 10:
                nxt_tier = self.skill_tier(name) + 1
                costA = self.ascend_cost(name, nxt_tier)
                stacks = self.skill_asc_stack(name)
                btn_text = f"ASCEND {stacks+1}/5 ({costA}🎟)"
                btn_col = "#F59E0B" if self.state.tickets >= costA else "#374151"
                action = (lambda n=name: self.ascend_skill(n))
            else:
                btn_text = f"Upgrade ({cost}🎟)"
                btn_col = "#16A34A" if self.state.tickets >= cost else "#374151"
                action = (lambda n=name: self.buy_skill_level(n))

            rect = c.create_rectangle(560, y + 22, 705, y + 56, fill=btn_col, outline="#0A0D13", width=2)
            txt = c.create_text(632, y + 39, text=btn_text, fill="white", font=("Arial", 10, "bold"))
            for item in (rect, txt):
                c.tag_bind(item, "<Button-1>", lambda e, fn=action: fn())

            y += 92

        c.create_text(40, 500, text="Next: add dungeon boosts + real active skills if you want.",
                      anchor="w", fill=self.SUB, font=("Arial", 9, "bold"))

    # Attach methods to class
    App.open_ascension = open_ascension
    App.ascension_refresh_loop = ascension_refresh_loop
    App.render_ascension = render_ascension
    App.skill_level = skill_level
    App.skill_cost = skill_cost
    App.buy_skill_level = buy_skill_level
    App.skill_tier = skill_tier
    App.skill_asc_stack = skill_asc_stack
    App.ascend_cost = ascend_cost
    App.ascend_skill = ascend_skill
    App.roman_numeral = roman_numeral



    # ---------------------------
    # Make skills actually affect gameplay
    # ---------------------------

    # Damage hook: Berserk (always-on)
    _orig_current_damage = App.current_damage

    def _current_damage_patched(self):
        _ensure_ticket_fields(self)
        base = _orig_current_damage(self)

        berserk_lvl = int(self.state.skills.get("Berserk", 0))
        berserk_tier = int(getattr(self.state, "skill_tiers", {}).get("Berserk", 0))
        if berserk_lvl > 0 or berserk_tier > 0:
            tier_bonus = 0.20 * berserk_tier
            per_level = 0.06 * (1.0 + 0.20 * berserk_tier)
            base = int(base * (1.0 + tier_bonus + per_level * berserk_lvl))

        return base

    App.current_damage = _current_damage_patched

    # Lifesteal hook: heal on hit
    _orig_player_attack = App.player_attack

    def _player_attack_patched(self, multiplier: float = 1.0):
        _ensure_ticket_fields(self)

        # We want dmg amount; easiest is to compute before calling original
        # because original uses current_damage().
        dmg_est = int(self.current_damage() * multiplier)

        _orig_player_attack(self, multiplier)

        ls_lvl = int(self.state.skills.get("Lifesteal", 0))
        ls_tier = int(getattr(self.state, "skill_tiers", {}).get("Lifesteal", 0))
        if ls_lvl > 0 or ls_tier > 0:
            pct = (0.04 * ls_tier) + (0.01 * (1.0 + 0.25 * ls_tier) * ls_lvl)
            heal = max(0, int(dmg_est * pct))
            if heal > 0:
                self.state.player_hp = min(self.state.player_max_hp, self.state.player_hp + heal)

    App.player_attack = _player_attack_patched

    # Auto-forge speed hook: Forge Rush
    _orig_run_auto_forge = App.run_auto_forge

    def _run_auto_forge_patched(self):
        _ensure_ticket_fields(self)
        if not getattr(self.state, "auto_forge", False):
            return

        if self.state.hammers <= 0:
            self.state.auto_forge = False
            self.auto_job = None
            try:
                self.render()
            except Exception:
                pass
            return

        # Forge once
        self.forge_once()

        # Speed scaling
        rush_lvl = int(self.state.skills.get("Forge Rush", 0))
        rush_tier = int(getattr(self.state, "skill_tiers", {}).get("Forge Rush", 0))
        tier_mult = (0.92 ** rush_tier)
        level_mult = (0.95 ** int(rush_lvl * (1.0 + 0.20 * rush_tier)))
        ms = int(self.state.auto_ms * tier_mult * level_mult)
        ms = max(30, ms)
        self.auto_job = self.root.after(ms, self.run_auto_forge)

    App.run_auto_forge = _run_auto_forge_patched


# Install the system as soon as this module loads
_install_ticket_ascension_system()
# =========================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = ForgeBattlerApp(root)
    root.mainloop()

    