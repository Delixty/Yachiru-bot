"""cogs/rp.py — RP-команды с аниме-картинками (nekos.best API)."""

import discord
import aiohttp
from discord import app_commands
from discord.ext import commands

# Категория nekos.best для каждой команды
RP_ACTIONS = {
    "kiss":  {"cat": "kiss",    "emoji": "💋", "title": "Поцелуй",   "text": "целует"},
    "punch": {"cat": "punch",   "emoji": "👊", "title": "Удар",      "text": "ударяет"},
    "hug":   {"cat": "hug",     "emoji": "🤗", "title": "Объятие",   "text": "обнимает"},
    "sex":   {"cat": "blush",   "emoji": "😳", "title": "Шалость",   "text": "делает непристойность с"},
    "hand":  {"cat": "highfive","emoji": "🖐️", "title": "Дай пять",  "text": "даёт пять"},
    "slap":  {"cat": "slap",    "emoji": "✋", "title": "Шлепок",    "text": "шлёпает"},
    "laugh": {"cat": "laugh",   "emoji": "😂", "title": "Смех",      "text": "смеётся над"},
    "point": {"cat": "poke",    "emoji": "☝️", "title": "Указывает", "text": "указывает пальцем на"},
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

    async def get_gif(self, category: str):
        """Получить случайную аниме-гифку с nekos.best."""
        try:
            async with self.session.get(f"https://nekos.best/api/v2/{category}") as r:
                if r.status == 200:
                    j = await r.json()
                    results = j.get("results") or []
                    if results and results[0].get("url"):
                        return results[0]["url"]
        except Exception:
            pass
        return None

    async def run_action(self, inter: discord.Interaction, action: str, target: discord.Member):
        a = RP_ACTIONS[action]
        gif = await self.get_gif(a["cat"])

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
