"""cogs/profile.py — профиль, статистика, ранг, достижения, лидерборд, помощь."""

import discord
from discord import app_commands
from discord.ext import commands
import core


async def display_name(bot, uid):
    try:
        u = await bot.fetch_user(int(uid))
        return u.display_name
    except Exception:
        return f"Игрок {uid}"


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- /balance ----------
    @app_commands.command(name="balance", description="💰 Проверить баланс чирукойнов")
    @app_commands.describe(user="Чей баланс (пусто = свой)")
    async def balance(self, inter: discord.Interaction, user: discord.Member = None):
        t = user or inter.user
        ud = core.get_user(str(t.id))
        avail, _ = core.passive_income(ud)
        e = discord.Embed(title=f"💰 Баланс — {t.display_name}", color=discord.Color.gold())
        e.set_thumbnail(url=t.display_avatar.url)
        e.add_field(name="👛 Кошелёк", value=f"**{core.fmt(ud['wallet'])}** {core.CURRENCY}", inline=True)
        e.add_field(name="🏦 Банк", value=f"**{core.fmt(ud['bank'])}** {core.CURRENCY}", inline=True)
        e.add_field(name="💵 Всего", value=f"**{core.fmt(core.net_worth(ud))}** {core.CURRENCY}", inline=True)
        e.add_field(name="📈 Бонус к работе", value=f"+{core.get_bonus_percent(ud)}%", inline=True)
        e.add_field(name="🏦 Накопилось дохода", value=f"{core.fmt(avail)} {core.CURRENCY}", inline=True)
        e.add_field(name="🎁 Предметов", value=f"{len(ud['items']) + sum(ud.get('consumables', {}).values())}", inline=True)
        await inter.response.send_message(embed=e)

    # ---------- /profile ----------
    @app_commands.command(name="profile", description="👤 Профиль игрока")
    @app_commands.describe(user="Чей профиль (пусто = свой)")
    async def profile(self, inter: discord.Interaction, user: discord.Member = None):
        t = user or inter.user
        ud = core.get_user(str(t.id))
        rank, total = core.get_rank(str(t.id))
        s = ud["stats"]
        e = discord.Embed(title=f"👤 {t.display_name}", color=discord.Color.blurple())
        e.set_thumbnail(url=t.display_avatar.url)
        e.add_field(name="💵 Капитал", value=f"**{core.fmt(core.net_worth(ud))}** {core.CURRENCY}", inline=True)
        e.add_field(name="🏆 Место", value=f"**#{rank}** / {total}", inline=True)
        e.add_field(name="🎯 Достижений", value=f"**{len(ud['achievements'])}** / {len(core.ACHIEVEMENTS)}", inline=True)
        e.add_field(name="⭐ Уровень", value=str(ud.get("level", 1)), inline=True)
        e.add_field(name="💼 Работ", value=str(s.get("work", 0)), inline=True)
        e.add_field(name="🎮 Побед", value=f"{s.get('games_won', 0)} / {s.get('games_played', 0)}", inline=True)
        e.add_field(name="🔥 Серия", value=f"{s.get('streak', 0)} (рекорд {s.get('max_streak', 0)})", inline=True)
        icons = "".join(core.ALL_ITEMS[i].get("name", "")[:2] for i in ud["items"] if i in core.ALL_ITEMS)
        e.add_field(name="🎒 Имущество", value=icons or "Ничего", inline=False)
        await inter.response.send_message(embed=e)

    # ---------- /stats ----------
    @app_commands.command(name="stats", description="📊 Подробная статистика")
    @app_commands.describe(user="Чья статистика (пусто = своя)")
    async def stats(self, inter: discord.Interaction, user: discord.Member = None):
        t = user or inter.user
        s = core.get_user(str(t.id))["stats"]
        e = discord.Embed(title=f"📊 Статистика — {t.display_name}", color=discord.Color.blurple())
        e.add_field(name="💼 Отработано", value=str(s.get("work", 0)))
        e.add_field(name="🃏 Блэкджек", value=f"{s.get('blackjack_won', 0)}/{s.get('blackjack_played', 0)}")
        e.add_field(name="🎮 Игр всего", value=f"{s.get('games_won', 0)}/{s.get('games_played', 0)}")
        e.add_field(name="🔥 Макс. серия", value=str(s.get("max_streak", 0)))
        e.add_field(name="💰 Поставлено", value=f"{core.fmt(s.get('gambled', 0))} {core.CURRENCY}")
        e.add_field(name="💵 Крупнейший выигрыш", value=f"{core.fmt(s.get('biggest_win', 0))} {core.CURRENCY}")
        e.add_field(name="🦹 Ограблений", value=str(s.get("crimes", 0)))
        e.add_field(name="⏰ Серия daily", value=str(s.get("daily_streak", 0)))
        await inter.response.send_message(embed=e)

    # ---------- /rank ----------
    @app_commands.command(name="rank", description="🏅 Твоё место в рейтинге")
    @app_commands.describe(user="Чей ранг (пусто = свой)")
    async def rank(self, inter: discord.Interaction, user: discord.Member = None):
        t = user or inter.user
        uid = str(t.id)
        rank, total = core.get_rank(uid)
        top, _ = core.leaderboard(limit=10, offset=0)
        # соседи
        all_users, _ = core.leaderboard(limit=10000)
        idx = next((i for i, (u, _) in enumerate(all_users) if u == uid), None)
        neigh = all_users[max(0, idx - 2):idx + 3] if idx is not None else []
        e = discord.Embed(title=f"🏅 Ранг — {t.display_name}", description=f"Ты на **#{rank}** месте из {total}", color=discord.Color.gold())
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (u, d) in enumerate(neigh):
            name = await display_name(self.bot, u)
            real_rank = all_users.index((u, d)) + 1 if (u, d) in all_users else "?"
            mark = "👈 **ТЫ**" if u == uid else ""
            medal = medals[real_rank - 1] if isinstance(real_rank, int) and real_rank <= 3 else f"#{real_rank}"
            lines.append(f"{medal} **{name}** — {core.fmt(core.net_worth(d))} {core.CURRENCY} {mark}")
        e.add_field(name="Соседи по рейтингу", value="\n".join(lines) or "—", inline=False)
        await inter.response.send_message(embed=e)

    # ---------- /level ----------
    @app_commands.command(name="level", description="⭐ Твой уровень и опыт")
    async def level(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        lvl = ud.get("level", 1)
        xp = ud.get("xp", 0)
        needed = lvl * 100
        
        pct = min(100, int((xp / needed) * 100))
        filled = int(pct / 10)
        bar = "█" * filled + "░" * (10 - filled)
        
        e = discord.Embed(title="⭐ Уровень", color=discord.Color.blue())
        e.set_thumbnail(url=inter.user.display_avatar.url)
        e.add_field(name="Уровень", value=f"**{lvl}**", inline=True)
        e.add_field(name="Опыт", value=f"**{xp} / {needed} XP**", inline=True)
        e.add_field(name="Прогресс", value=f"`{bar}` {pct}%", inline=False)
        e.add_field(name="Бонус", value=f"+{int((lvl-1)*1.5)}% к заработку в /work", inline=False)
        await inter.response.send_message(embed=e)
        
    # ---------- /quest ----------
    @app_commands.command(name="quest", description="📜 Ежедневные задания")
    async def quest(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        q = core.get_quests(uid)
        
        work = min(3, q["progress"].get("work", 0))
        bj = min(2, q["progress"].get("bj_win", 0))
        buy = min(1, q["progress"].get("buy", 0))
        
        e = discord.Embed(title="📜 Ежедневные задания", color=discord.Color.gold())
        e.add_field(name="💼 Отработать 3 раза", value=f"**{work}/3**", inline=False)
        e.add_field(name="🃏 Выиграть 2 раза в Blackjack", value=f"**{bj}/2**", inline=False)
        e.add_field(name="🛍️ Купить 1 предмет", value=f"**{buy}/1**", inline=False)
        
        if work == 3 and bj == 2 and buy == 1:
            if not q.get("completed", False):
                ud = core.get_user(uid)
                ud["wallet"] += 1000
                ud["total_earned"] += 1000
                q["completed"] = True
                ud["quests"] = q
                core.save_user(uid, ud)
                e.add_field(name="🎁 Статус", value="✅ **ЗАДАНИЯ ВЫПОЛНЕНЫ!** Получено **1000** 🪙", inline=False)
            else:
                e.add_field(name="🎁 Статус", value="✅ Уже получена награда за сегодня.", inline=False)
        else:
            e.add_field(name="🎁 Награда", value="**1000** 🪙", inline=False)
            
        await inter.response.send_message(embed=e)

    # ---------- /achievements ----------
    @app_commands.command(name="achievements", description="🎯 Список достижений")
    async def achievements(self, inter: discord.Interaction):
        ud = core.get_user(str(inter.user.id))
        e = discord.Embed(title="🎯 Достижения", description=f"Открыто: **{len(ud['achievements'])}** / **{len(core.ACHIEVEMENTS)}**",
                          color=discord.Color.gold())
        for aid, a in core.ACHIEVEMENTS.items():
            done = aid in ud["achievements"]
            mark = "✅" if done else "🔒"
            status = "Открыто" if done else "Не открыто"
            e.add_field(
                name=f"{mark} {a['icon']} {a['name']}",
                value=f"{a['desc']}\n🎁 +{core.fmt(a['reward'])} {core.CURRENCY} • {status}",
                inline=False
            )
        await inter.response.send_message(embed=e)

    # ---------- /leaderboard ----------
    @app_commands.command(name="leaderboard", description="🏆 Топ игроков по капиталу")
    async def leaderboard(self, inter: discord.Interaction):
        top, total = core.leaderboard(10)
        if not top:
            return await inter.response.send_message("📭 Пока нет данных!", ephemeral=True)
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (uid, ud) in enumerate(top):
            name = await display_name(self.bot, uid)
            medal = medals[i] if i < 3 else f"**{i + 1}.**"
            icons = "".join(core.ALL_ITEMS[x].get("name", "")[:2] for x in ud.get("items", []) if x in core.ALL_ITEMS)
            lines.append(f"{medal} **{name}** — **{core.fmt(core.net_worth(ud))}** {core.CURRENCY} {icons}")
        e = discord.Embed(title="🏆 Таблица лидеров", description="\n\n".join(lines), color=discord.Color.gold())
        e.set_footer(text=f"Всего игроков: {total}")
        await inter.response.send_message(embed=e)

    # ---------- /help ----------
    @app_commands.command(name="help", description="❓ Все команды бота")
    async def help(self, inter: discord.Interaction):
        e = discord.Embed(title="📖 Команды Yachiru", color=discord.Color.blue())
        e.add_field(name="💰 Экономика", value="`/balance` `/work` `/daily` `/weekly` `/crime` `/beg`\n`/deposit` `/withdraw` `/bank` `/interest` `/give`", inline=False)
        e.add_field(name="🎰 Игры", value="`/blackjack` `/slots` `/coinflip` `/roulette` `/dice` `/guess` `/rps`", inline=False)
        e.add_field(name="🛒 Магазин", value="`/shop` `/buy` `/sell` `/inventory` `/use` `/collect`\n`/market sell` `/market browse`", inline=False)
        e.add_field(name="👤 Профиль", value="`/profile` `/stats` `/rank` `/achievements` `/leaderboard`", inline=False)
        e.add_field(name="👥 Взаимодействие", value="`/rob` `/gift` `/trade` `/duel`", inline=False)
        e.add_field(name="🎉 Ивенты", value="`/treasure` `/lottery buy` `/lottery info`\n`/auction start` `/bid` `/seteventchannel`", inline=False)
        e.add_field(name="🛡️ Модерация", value="`/ban` `/kick` `/mute` `/unmute` `/role`\n`/autorole set` `/welcome set <канал> <текст>` `/welcome delete <канал>`", inline=False)
        e.add_field(name="💕 RP-команды", value="`/kiss` `/hug` `/punch` `/sex` `/hand`\n`/slap` `/laugh` `/point` — с аниме-картинками", inline=False)
        e.set_footer(text="Yachiru • Валюта: чирукойны 🪙")
        await inter.response.send_message(embed=e)


async def setup(bot):
    await bot.add_cog(Profile(bot))
