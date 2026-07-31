"""
core.py — ядро бота: база данных, предметы, достижения, вспомогательные функции.
"""

import json
import os
import time
import copy
import threading

# ======================== НАСТРОЙКИ ========================
TOKEN = "123"
DATA_FILE = "data.json"
CURRENCY = "🪙"
CURRENCY_NAME = "чирукойны"

COOLDOWNS = {
    "work": 3600,
    "daily": 86400,
    "weekly": 604800,
    "crime": 3600,
    "heist": 43200,
    "beg": 1800,
    "rob": 3600,
    "interest": 43200,
    "treasure": 3600,
    "fish": 300,
    "mine": 300,
}
# ==========================================================

_lock = threading.Lock()

# ---------- ПРЕДМЕТЫ ----------
BONUS_ITEMS = {
    "fishing_rod": {"name": "🎣 Удочка",       "desc": "+10% к /work, бонус к рыбалке","price": 500,   "bonus": 10},
    "pickaxe":     {"name": "⛏️ Кирка",        "desc": "+20% к /work, бонус в шахте",  "price": 1500,  "bonus": 20},
    "laptop":      {"name": "💻 Ноутбук",      "desc": "+35% к /work",  "price": 3000,  "bonus": 35},
    "corporation": {"name": "🏢 Корпорация",   "desc": "+100% к /work", "price": 15000, "bonus": 100},
}
INCOME_ITEMS = {
    "house":   {"name": "🏠 Дом",      "desc": "+30 🪙 каждые 6 ч",  "price": 5000,  "income": 30,  "interval": 21600},
    "store":   {"name": "🏪 Магазин",  "desc": "+100 🪙 каждые 12 ч","price": 20000, "income": 100, "interval": 43200},
    "factory": {"name": "🏭 Завод",    "desc": "+500 🪙 каждые 24 ч","price": 80000, "income": 500, "interval": 86400},
}
CONSUMABLES = {
    "lucky_charm": {"name": "🍀 Талисман удачи", "desc": "x2 к следующему /work",       "price": 1000},
    "energy_drink":{"name": "⚡ Энергетик",       "desc": "+50% к следующему /work",     "price": 800},
    "shield":      {"name": "🛡️ Щит",            "desc": "Защита от ограбления 24 ч",   "price": 1500},
    "mystery_box": {"name": "🎁 Мистический ящик","desc": "Случайная награда",           "price": 2000},
}
CASES = {
    "case_normal": {"name": "📦 Обычный кейс", "desc": "Случайные вещи", "price": 2000},
    "case_rare":   {"name": "🔮 Редкий кейс",  "desc": "Шанс на редкость!", "price": 10000},
}
RESOURCES = {
    "ore":  {"name": "🪨 Руда", "desc": "Добыто в шахте", "price": 50},
    "fish": {"name": "🐟 Рыба", "desc": "Поймано на рыбалке", "price": 40},
    "boot": {"name": "🥾 Ботинок", "desc": "Мусор", "price": 1},
    "crop": {"name": "🌾 Урожай", "desc": "С фермы", "price": 150},
}
COLLECTIONS = {
    "demon_sword": {"name": "🟥 Демонический меч", "desc": "Часть коллекции", "price": 15000},
    "mask":        {"name": "🟪 Маска", "desc": "Часть коллекции", "price": 15000},
    "gold_coin":   {"name": "🟨 Золотая монета", "desc": "Часть коллекции", "price": 15000},
}

ALL_ITEMS = {}
for _i, _v in BONUS_ITEMS.items():   ALL_ITEMS[_i] = {**_v, "type": "bonus",      "id": _i}
for _i, _v in INCOME_ITEMS.items():  ALL_ITEMS[_i] = {**_v, "type": "income",     "id": _i}
for _i, _v in CONSUMABLES.items():   ALL_ITEMS[_i] = {**_v, "type": "consumable", "id": _i}
for _i, _v in CASES.items():         ALL_ITEMS[_i] = {**_v, "type": "consumable", "id": _i}
for _i, _v in RESOURCES.items():     ALL_ITEMS[_i] = {**_v, "type": "resource",   "id": _i}
for _i, _v in COLLECTIONS.items():   ALL_ITEMS[_i] = {**_v, "type": "collection", "id": _i}

# ---------- ДОСТИЖЕНИЯ ----------
ACHIEVEMENTS = {
    "first_earn": {"name": "Первые шаги", "desc": "Впервые заработать", "reward": 100, "icon": "🌱", "check": lambda s, u: u["total_earned"] > 0},
    "rich_1k":    {"name": "Богач", "desc": "Накопить 1 000 🪙", "reward": 500, "icon": "💰", "check": lambda s, u: net_worth(u) >= 1000},
    "rich_10k":   {"name": "Миллионер", "desc": "Накопить 10 000 🪙", "reward": 2000, "icon": "💎", "check": lambda s, u: net_worth(u) >= 10000},
    "rich_100k":  {"name": "Магнат", "desc": "Накопить 100 000 🪙", "reward": 10000, "icon": "👑", "check": lambda s, u: net_worth(u) >= 100000},
    "bj_100":     {"name": "Карточный шулер", "desc": "Сыграть 100 раз в блэкджек", "reward": 1000, "icon": "🃏", "check": lambda s, u: s.get("blackjack_played", 0) >= 100},
    "streak_10":  {"name": "На волне", "desc": "10 побед подряд в играх", "reward": 1500, "icon": "🔥", "check": lambda s, u: s.get("max_streak", 0) >= 10},
    "first_item": {"name": "Шопоголик", "desc": "Купить первый предмет", "reward": 300, "icon": "🛍️", "check": lambda s, u: len(u["items"]) > 0 or sum(u.get("consumables", {}).values()) > 0},
    "gambler":    {"name": "Азартный игрок", "desc": "Сыграть 50 игр", "reward": 800, "icon": "🎲", "check": lambda s, u: s.get("games_played", 0) >= 50},
    "criminal":   {"name": "Преступник", "desc": "5 успешных ограблений", "reward": 600, "icon": "🦹", "check": lambda s, u: s.get("crimes", 0) >= 5},
    "hardworker": {"name": "Трудяга", "desc": "Отработать 25 раз", "reward": 700, "icon": "💼", "check": lambda s, u: s.get("work", 0) >= 25},
}


def default_stats():
    return {
        "work": 0, "games_played": 0, "games_won": 0,
        "blackjack_played": 0, "blackjack_won": 0,
        "streak": 0, "max_streak": 0, "crimes": 0, "robs": 0,
        "gambled": 0, "duels": 0, "biggest_win": 0, "daily_streak": 0,
    }


def default_user():
    return {
        "wallet": 0, "bank": 0,
        "xp": 0, "level": 1,
        "quests": {"date": "", "progress": {"work": 0, "bj_win": 0, "buy": 0}, "completed": False},
        "farm": {"planted": 0},
        "stocks": {},
        "last_daily": 0, "last_weekly": 0, "last_crime": 0, "last_heist": 0, "last_beg": 0,
        "last_rob": 0, "last_interest": 0, "last_collect": 0, "last_treasure": 0,
        "last_fish": 0, "last_mine": 0, "last_msg": 0,
        "total_earned": 0, "items": [], "consumables": {}, "achievements": [],
        "stats": default_stats(), "shield_until": 0, "boost_until": 0, "boost_mult": 1.0,
    }


# ---------- БАЗА ДАННЫХ ----------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)


def get_user(uid):
    uid = str(uid)
    data = load_data()
    if uid not in data or not isinstance(data[uid], dict) or "wallet" not in data[uid]:
        data[uid] = default_user()
        save_data(data)
        return data[uid]
    base = data[uid]
    du = default_user()
    changed = False
    for k, v in du.items():
        if k not in base:
            base[k] = copy.deepcopy(v)
            changed = True
    if "stats" not in base or not isinstance(base["stats"], dict):
        base["stats"] = default_stats()
        changed = True
    for sk, sv in default_stats().items():
        if sk not in base["stats"]:
            base["stats"][sk] = sv
            changed = True
    if "consumables" not in base or not isinstance(base["consumables"], dict):
        base["consumables"] = {}
        changed = True
    if changed:
        save_data(data)
    return base


def save_user(uid, ud):
    data = load_data()
    data[str(uid)] = ud
    save_data(data)


# ---------- ВСПОМОГАТЕЛЬНЫЕ ----------
def net_worth(ud):
    return ud["wallet"] + ud["bank"]


def fmt(n):
    return f"{int(n):,}".replace(",", " ")


def cd(sec):
    sec = int(sec)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    p = []
    if h: p.append(f"{h}ч")
    if m: p.append(f"{m}м")
    if not h and s: p.append(f"{s}с")
    return " ".join(p) or "0с"


def ach_text(new_ach):
    """Красивое оформление новых достижений — каждая строчка отдельно, без слипания."""
    parts = []
    for a in new_ach:
        parts.append(
            f"{a.get('icon', '🏆')} **{a['name']}**\n"
            f"└ {a['desc']} — награда **+{fmt(a['reward'])} {CURRENCY}**"
        )
    return "\n\n".join(parts)


def get_bonus_percent(ud):
    b = sum(BONUS_ITEMS[i]["bonus"] for i in ud["items"] if i in BONUS_ITEMS)
    if all(k in ud["items"] for k in COLLECTIONS.keys()):
        b += 50  # бонус за полную коллекцию
    return b


def passive_income(ud, now=None):
    now = now or time.time()
    total = 0.0
    lines = []
    for iid in ud["items"]:
        it = INCOME_ITEMS.get(iid)
        if not it: continue
        elapsed = max(0, now - ud.get("last_collect", now))
        elapsed = min(elapsed, it["interval"] * 8)
        amt = (it["income"] / it["interval"]) * elapsed
        total += amt
        lines.append(f"{it['name']}: +{int(amt)} {CURRENCY}")
    return int(total), lines


def earn(uid, amount):
    ud = get_user(uid)
    ud["wallet"] += amount
    if amount > 0: ud["total_earned"] += amount
    new = check_achievements(uid, ud)
    save_user(uid, ud)
    return ud, new


def spend(uid, amount):
    ud = get_user(uid)
    if ud["wallet"] < amount: return False, ud
    ud["wallet"] -= amount
    save_user(uid, ud)
    return True, ud


def check_achievements(uid, ud):
    newly = []
    s = ud["stats"]
    for aid, a in ACHIEVEMENTS.items():
        if aid not in ud["achievements"]:
            try:
                if a["check"](s, ud):
                    ud["achievements"].append(aid)
                    ud["wallet"] += a["reward"]
                    ud["total_earned"] += a["reward"]
                    newly.append(a)
            except Exception: pass
    return newly


def get_rank(uid):
    uid = str(uid)
    data = load_data()
    us = [(u, d) for u, d in data.items() if isinstance(d, dict) and "wallet" in d]
    us.sort(key=lambda x: net_worth(x[1]), reverse=True)
    for i, (u, _) in enumerate(us):
        if u == uid: return i + 1, len(us)
    return len(us) + 1, len(us)


def leaderboard(limit=10, offset=0):
    data = load_data()
    us = [(u, d) for u, d in data.items() if isinstance(d, dict) and "wallet" in d]
    us.sort(key=lambda x: net_worth(x[1]), reverse=True)
    return us[offset:offset + limit], len(us)


def get_event_channel():
    return load_data().get("event_channel")


def set_event_channel(cid):
    data = load_data()
    data["event_channel"] = cid
    save_data(data)

# ---------- LEVEL & QUESTS ----------
def add_xp(uid, amount):
    ud = get_user(uid)
    ud["xp"] += amount
    lvl_up = False
    needed = ud["level"] * 100
    while ud["xp"] >= needed:
        ud["xp"] -= needed
        ud["level"] += 1
        needed = ud["level"] * 100
        lvl_up = True
    save_user(uid, ud)
    return lvl_up

def get_quests(uid):
    ud = get_user(uid)
    today = time.strftime("%Y-%m-%d")
    if ud["quests"].get("date") != today:
        ud["quests"] = {
            "date": today,
            "progress": {"work": 0, "bj_win": 0, "buy": 0},
            "completed": False
        }
        save_user(uid, ud)
    return ud["quests"]

def progress_quest(uid, task, amount=1):
    ud = get_user(uid)
    q = get_quests(uid)
    if not q.get("completed", False):
        q["progress"][task] = q["progress"].get(task, 0) + amount
        ud["quests"] = q
        save_user(uid, ud)

def get_stocks():
    data = load_data()
    if "stocks_market" not in data:
        data["stocks_market"] = {"IT_CORP": 100, "GOLD_INC": 500, "FISH_CO": 50}
        save_data(data)
    return data["stocks_market"]
