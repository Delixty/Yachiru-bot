"""cogs/rp.py — RP-команды с аниме-гифками.

Источник: gifukai.com (бесплатный API аниме-гифок, без ключей и лимитов).
Если API временно недоступен — используются проверенные прямые ссылки (fallback),
поэтому картинка гарантированно появляется.
"""

import discord
import aiohttp
from discord import app_commands
from discord.ext import commands

USER_AGENT = "YachiruBot/1.0 (Discord bot; by delixty)"

# Категория gifukai для каждой команды + запасные прямые ссылки
RP_ACTIONS = {
    "kiss":  {"cat": "kiss",     "emoji": "💋", "title": "Поцелуй",   "text": "целует",
              "fallback": ["https://cdn.gifukai.com/kiss/61c962e0-d1d8-4e5e-a456-1e1c7a76e827.gif"]},
    "punch": {"cat": "punch",    "emoji": "👊", "title": "Удар",      "text": "ударяет",
              "fallback": ["https://cdn.gifukai.com/punch/6a608670-3863-4231-955a-ae95a123e00d.gif"]},
    "hug":   {"cat": "hug",      "emoji": "🤗", "title": "Объятие",   "text": "обнимает",
              "fallback": ["https://cdn.gifukai.com/hug/0a891cbe-fb69-431e-b228-eb8b44909daf.gif"]},
    "sex":   {"cat": "blush",    "emoji": "😳", "title": "Шалость",   "text": "делает непристойность с",
              "fallback": ["https://cdn.gifukai.com/blush/278813e2-9259-4970-9355-d524a3e77f09.gif"]},
    "hand":  {"cat": "highfive", "emoji": "🖐️", "title": "Дай пять",  "text": "даёт пять",
              "fallback": ["https://cdn.gifukai.com/highfive/643281d6-f19e-47dc-b022-e0a35134d2d2.gif"]},
    "slap":  {"cat": "slap",     "emoji": "✋", "title": "Шлепок",     "text": "шлёпает",
              "fallback": ["https://cdn.gifukai.com/slap/3fd72659-51b9-46d0-b3e5-c4afb211e59f.gif"]},
    "laugh": {"cat": "laugh",    "emoji": "😂", "title": "Смех",      "text": "смеётся над",
              "fallback": ["https://cdn.gifukai.com/laugh/47bd14e7-7914-41c7-833e-3c1ac2248f8a.gif"]},
    "point": {"cat": "poke",     "emoji": "☝️", "title": "Указывает", "text": "указывает пальцем на",
              "fallback": ["https://cdn.gifukai.com/poke/bb9d5b09-af83-4185-a851-17ffd24912dd.gif"]},
}

import random


class RP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        if self.session and not self.session.closed:
            self.bot.loop.create_task(self.session.close())

    async def get_gif(self, action: str):
        cfg = RP_ACTIONS[action]

        # 1) Пытаемся получить свежую гифку с gifukai API
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        try:
            headers = {"User-Agent": USER_AGENT}
            async with self.session.get(
                f"https://api.gifukai.com/{cfg['cat']}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status == 200:
                    j = await r.json(content_type=None)
                    if isinstance(j, dict) and j.get("url"):
                        return j["url"]
        except Exception:
            pass

        # 2) Запасной вариант — проверенная прямая ссылка
        if cfg.get("fallback"):
            return random.choice(cfg["fallback"])
        return None

    async def run_action(self, inter: discord.Interaction, action: str, target: discord.Member):
        a = RP_ACTIONS[action]
        gif = await self.get_gif(action)

        if target and target.id != inter.user.id:
            desc = f"**{inter.user.display_name}** {a['text']} **{target.display_name}** {a['emoji']}"
        elif target and target.id == inter.user.id:
            desc = f"**{inter.user.display_name}** {a['text']} себя... странно, но ладно {a['emoji']}"
        else:
            desc = f"**{inter.user.display_name}** {a['text']} всех {a['emoji']}"

        e = discord.Embed(title=f"{a['emoji']} {a['title']}", description=desc, color=discord.Color.pink())
        if gif:
            e.set_image(url=gif)
        await inter.response.send_message(embed=e)

    # ---------- команды ----------
    @app_commands.command(name="kiss", description="💋 Поцеловать участника")
    @app_commands.describe(user="Кого поцеловать")
    async def kiss(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "kiss", user)

    @app_commands.command(name="punch", description="👊 Ударить участника")
    @app_commands.describe(user="Кого ударить")
    async def punch(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "punch", user)

    @app_commands.command(name="hug", description="🤗 Обнять участника")
    @app_commands.describe(user="Кого обнять")
    async def hug(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "hug", user)

    @app_commands.command(name="sex", description="😳 Сделать непристойность")
    @app_commands.describe(user="С кем")
    async def sex(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "sex", user)

    @app_commands.command(name="hand", description="🖐️ Дать пять участнику")
    @app_commands.describe(user="Кому дать пять")
    async def hand(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "hand", user)

    @app_commands.command(name="slap", description="✋ Шлёпнуть участника")
    @app_commands.describe(user="Кого шлёпнуть")
    async def slap(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "slap", user)

    @app_commands.command(name="laugh", description="😂 Посмеяться")
    @app_commands.describe(user="Над кем посмеяться (пусто = над всеми)")
    async def laugh(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "laugh", user)

    @app_commands.command(name="point", description="☝️ Указать пальцем")
    @app_commands.describe(user="На кого указать (пусто = на всех)")
    async def point(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "point", user)


async def setup(bot):
    await bot.add_cog(RP(bot))
