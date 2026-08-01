"""cogs/rp.py — RP-команды с аниме-картинками.

Источники картинок (по порядку, со сменой при сбое):
1) waifu.pics  — https://api.waifu.pics/sfw/<категория>
2) nekos.best  — https://nekos.best/api/v2/<категория> (обязателен User-Agent)
3) waifu.pics «waifu» — любая аниме-картинка, чтобы ответ не остался без картинки
"""

import discord
import aiohttp
from discord import app_commands
from discord.ext import commands

USER_AGENT = "YachiruBot/1.0 (Discord bot; by delixty)"

# Категории для каждого источника (None = в этом источнике нет такой категории)
RP_ACTIONS = {
    "kiss":  {"emoji": "💋", "title": "Поцелуй",   "text": "целует",                  "waifu": "kiss",     "nekos": "kiss"},
    "punch": {"emoji": "👊", "title": "Удар",      "text": "ударяет",                 "waifu": "kick",     "nekos": "punch"},
    "hug":   {"emoji": "🤗", "title": "Объятие",   "text": "обнимает",                "waifu": "hug",      "nekos": "hug"},
    "sex":   {"emoji": "😳", "title": "Шалость",   "text": "делает непристойность с", "waifu": "blush",    "nekos": "blush"},
    "hand":  {"emoji": "🖐️", "title": "Дай пять",  "text": "даёт пять",               "waifu": "highfive", "nekos": "highfive"},
    "slap":  {"emoji": "✋", "title": "Шлепок",     "text": "шлёпает",                 "waifu": "slap",     "nekos": "slap"},
    "laugh": {"emoji": "😂", "title": "Смех",      "text": "смеётся над",             "waifu": "smile",    "nekos": "laugh"},
    "point": {"emoji": "☝️", "title": "Указывает", "text": "указывает пальцем на",    "waifu": "poke",     "nekos": "poke"},
}


class RP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        if self.session and not self.session.closed:
            self.bot.loop.create_task(self.session.close())

    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def _fetch(self, url: str, mode: str):
        """Скачать JSON и достать ссылку на картинку.
        mode: "waifu" -> json["url"]; "nekos" -> json["results"][0]["url"]"""
        await self._ensure_session()
        try:
            headers = {"User-Agent": USER_AGENT}
            async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    j = await r.json(content_type=None)
                    if mode == "waifu":
                        u = j.get("url")
                        if u:
                            return u
                    elif mode == "nekos":
                        results = j.get("results") or []
                        if results and results[0].get("url"):
                            return results[0]["url"]
        except Exception:
            pass
        return None

    async def get_gif(self, action: str):
        """Получить аниме-картинку: waifu.pics → nekos.best → любая waifu."""
        cfg = RP_ACTIONS[action]

        if cfg.get("waifu"):
            u = await self._fetch(f"https://api.waifu.pics/sfw/{cfg['waifu']}", "waifu")
            if u:
                return u

        if cfg.get("nekos"):
            u = await self._fetch(f"https://nekos.best/api/v2/{cfg['nekos']}", "nekos")
            if u:
                return u

        # Гарантированная аниме-картинка, если оба источника недоступны
        return await self._fetch("https://api.waifu.pics/sfw/waifu", "waifu")

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
        else:
            e.set_footer(text="Не удалось загрузить картинку 😔")
        await inter.response.send_message(embed=e)

    # ---------- /kiss ----------
    @app_commands.command(name="kiss", description="💋 Поцеловать участника")
    @app_commands.describe(user="Кого поцеловать")
    async def kiss(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "kiss", user)

    # ---------- /punch ----------
    @app_commands.command(name="punch", description="👊 Ударить участника")
    @app_commands.describe(user="Кого ударить")
    async def punch(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "punch", user)

    # ---------- /hug ----------
    @app_commands.command(name="hug", description="🤗 Обнять участника")
    @app_commands.describe(user="Кого обнять")
    async def hug(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "hug", user)

    # ---------- /sex ----------
    @app_commands.command(name="sex", description="😳 Сделать непристойность")
    @app_commands.describe(user="С кем")
    async def sex(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "sex", user)

    # ---------- /hand ----------
    @app_commands.command(name="hand", description="🖐️ Дать пять участнику")
    @app_commands.describe(user="Кому дать пять")
    async def hand(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "hand", user)

    # ---------- /slap ----------
    @app_commands.command(name="slap", description="✋ Шлёпнуть участника")
    @app_commands.describe(user="Кого шлёпнуть")
    async def slap(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "slap", user)

    # ---------- /laugh ----------
    @app_commands.command(name="laugh", description="😂 Посмеяться")
    @app_commands.describe(user="Над кем посмеяться (пусто = над всеми)")
    async def laugh(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "laugh", user)

    # ---------- /point ----------
    @app_commands.command(name="point", description="☝️ Указать пальцем")
    @app_commands.describe(user="На кого указать (пусто = на всех)")
    async def point(self, inter: discord.Interaction, user: discord.Member = None):
        await self.run_action(inter, "point", user)


async def setup(bot):
    await bot.add_cog(RP(bot))
