"""cogs/economy.py — экономика: работа, награды, банк, переводы."""

import discord
import time
import random
from discord import app_commands
from discord.ext import commands
import core


async def reply(inter, embed, new=None):
    if new:
        embed.add_field(name="🎯 Достижение разблокировано!", value=core.ach_text(new), inline=False)
    if inter.response.is_done():
        await inter.followup.send(embed=embed)
    else:
        await inter.response.send_message(embed=embed)


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- /work ----------
    @app_commands.command(name="work", description="💼 Поработать и заработать (раз в час)")
    async def work(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        if now - ud.get("last_work", 0) < core.COOLDOWNS["work"]:
            return await inter.response.send_message(
                f"⏰ Ты уже работал! Возвращайся через **{core.cd(core.COOLDOWNS['work'] - (now - ud['last_work']))}**",
                ephemeral=True)
        base = random.randint(30, 250)
        bonus_pct = core.get_bonus_percent(ud)
        bonus = int(base * bonus_pct / 100)
        mult = 1.0
        if ud.get("boost_until", 0) > now:
            mult = ud.get("boost_mult", 1.0)
        total = int((base + bonus) * mult)
        jobs = [
            ("👨‍💻 Программист", "писал код для клиента"), ("🍕 Курьер", "развозил пиццу"),
            ("🎨 Дизайнер", "рисовал логотип"), ("📦 Грузчик", "разгружал фуру"),
            ("🚗 Таксист", "возил пассажиров"), ("🎵 Музыкант", "играл на улице"),
            ("📸 Фотограф", "снимал свадьбу"), ("🧹 Уборщик", "убирал огромный офис"),
            ("🍳 Повар", "готовил блюда"), ("📚 Репетитор", "учил детей математике"),
            ("🔧 Механик", "чинил машины"), ("🎮 Стример", "стримил и собирал донаты"),
        ]
        jn, jd = random.choice(jobs)
        ud["wallet"] += total
        ud["total_earned"] += total
        ud["last_work"] = now
        ud["stats"]["work"] = ud["stats"].get("work", 0) + 1
        if mult > 1:
            ud["boost_until"] = 0
            ud["boost_mult"] = 1.0
        new = core.check_achievements(uid, ud)
        core.save_user(uid, ud)
        
        # Квесты и опыт
        core.progress_quest(uid, "work")
        core.add_xp(uid, random.randint(10, 20))
        
        lvl_bonus = int((ud.get("level", 1) - 1) * 1.5)
        level_extra = int(base * lvl_bonus / 100)
        
        if level_extra > 0:
            ud = core.get_user(uid)
            ud["wallet"] += level_extra
            ud["total_earned"] += level_extra
            core.save_user(uid, ud)
            total += level_extra
            
        e = discord.Embed(title=f"💼 {jn}", description=f"*Ты {jd}!*", color=discord.Color.green())
        e.add_field(name="💰 База", value=f"{core.fmt(base)} {core.CURRENCY}", inline=True)
        
        if bonus > 0 or level_extra > 0:
            e.add_field(name="📈 Бонус", value=f"+{core.fmt(bonus+level_extra)} ({bonus_pct+lvl_bonus}%)", inline=True)
        if mult > 1:
            e.add_field(name="🍀 Буст", value=f"x{mult}", inline=True)
        e.add_field(name="💵 Итого", value=f"**+{core.fmt(total)}** {core.CURRENCY}", inline=True)
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await reply(inter, e, new)

    # ---------- /daily ----------
    @app_commands.command(name="daily", description="📅 Забрать ежедневную награду")
    async def daily(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        cd_ = core.COOLDOWNS["daily"]
        if now - ud.get("last_daily", 0) < cd_:
            return await inter.response.send_message(
                f"⏳ Возвращайся через **{core.cd(cd_ - (now - ud['last_daily']))}**", ephemeral=True)
        if now - ud.get("last_daily", 0) < cd_ * 2:
            ud["stats"]["daily_streak"] = ud["stats"].get("daily_streak", 0) + 1
        else:
            ud["stats"]["daily_streak"] = 1
        streak = ud["stats"]["daily_streak"]
        reward = 200 + min((streak - 1) * 25, 500)
        ud["last_daily"] = now
        core.save_user(uid, ud)
        ud, new = core.earn(uid, reward)
        e = discord.Embed(title="📅 Ежедневная награда", color=discord.Color.gold())
        e.add_field(name="🔥 Серия дней", value=f"**{streak}**", inline=True)
        e.add_field(name="🪙 Получено", value=f"**+{core.fmt(reward)}** {core.CURRENCY}", inline=True)
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await reply(inter, e, new)

    # ---------- /weekly ----------
    @app_commands.command(name="weekly", description="🗓️ Забрать еженедельный бонус")
    async def weekly(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        cd_ = core.COOLDOWNS["weekly"]
        if now - ud.get("last_weekly", 0) < cd_:
            return await inter.response.send_message(
                f"⏳ Возвращайся через **{core.cd(cd_ - (now - ud['last_weekly']))}**", ephemeral=True)
        reward = 1500
        ud["last_weekly"] = now
        core.save_user(uid, ud)
        ud, new = core.earn(uid, reward)
        e = discord.Embed(title="🗓️ Еженедельный бонус", description=f"**+{core.fmt(reward)}** {core.CURRENCY} за верность!",
                          color=discord.Color.gold())
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await reply(inter, e, new)

    # ---------- /crime ----------
    @app_commands.command(name="crime", description="🦹 Совершить ограбление с риском (раз в час)")
    async def crime(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        cd_ = core.COOLDOWNS["crime"]
        if now - ud.get("last_crime", 0) < cd_:
            return await inter.response.send_message(
                f"⏳ Лежи тихо! Следующее дело через **{core.cd(cd_ - (now - ud['last_crime']))}**", ephemeral=True)
        r = random.random()
        ud["last_crime"] = now
        if r < 0.5:
            gain = random.randint(150, 1200)
            ud["wallet"] += gain
            ud["total_earned"] += gain
            ud["stats"]["crimes"] = ud["stats"].get("crimes", 0) + 1
            txt = f"🤑 Ограбление удалось! Добыча: **+{core.fmt(gain)}** {core.CURRENCY}"
            color = discord.Color.green()
        elif r < 0.75:
            loss = min(ud["wallet"], random.randint(50, 400))
            ud["wallet"] -= loss
            txt = f"😬 Тебя заметили! Ты потерял **{core.fmt(loss)}** {core.CURRENCY} на бегстве"
            color = discord.Color.red()
        else:
            loss = min(ud["wallet"], random.randint(100, 600))
            ud["wallet"] -= loss
            txt = f"🚔 ПОЛИЦИЯ! Тебя поймали и оштрафовали на **{core.fmt(loss)}** {core.CURRENCY}"
            color = discord.Color.dark_red()
        new = core.check_achievements(uid, ud)
        core.save_user(uid, ud)
        e = discord.Embed(title="🦹 Ограбление", description=txt, color=color)
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await reply(inter, e, new)

    # ---------- /beg ----------
    @app_commands.command(name="beg", description="🥺 Попросить милостыню (5–50 🪙)")
    async def beg(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        cd_ = core.COOLDOWNS["beg"]
        if now - ud.get("last_beg", 0) < cd_:
            return await inter.response.send_message(
                f"⏳ Не навязывайся! Подожди **{core.cd(cd_ - (now - ud['last_beg']))}**", ephemeral=True)
        ud["last_beg"] = now
        if random.random() < 0.7:
            gain = random.randint(5, 50)
            ud["wallet"] += gain
            ud["total_earned"] += gain
            txt = f"🥺 Добрый прохожий дал тебе **{core.fmt(gain)}** {core.CURRENCY}"
            color = discord.Color.green()
        else:
            txt = "😤 Тебе ничего не дали. Может, помыться стоит?"
            color = discord.Color.greyple()
        new = core.check_achievements(uid, ud)
        core.save_user(uid, ud)
        e = discord.Embed(title="🥺 Милостыня", description=txt, color=color)
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await reply(inter, e, new)

    # ---------- /deposit ----------
    @app_commands.command(name="deposit", description="🏦 Положить деньги в банк")
    @app_commands.describe(amount="Сколько положить (0 = всё)")
    async def deposit(self, inter: discord.Interaction, amount: int):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        if amount == 0:
            amount = ud["wallet"]
        if amount <= 0:
            return await inter.response.send_message("❌ В кошельке нет денег!", ephemeral=True)
        if ud["wallet"] < amount:
            return await inter.response.send_message(f"❌ Недостаточно! В кошельке {core.fmt(ud['wallet'])} {core.CURRENCY}", ephemeral=True)
        ud["wallet"] -= amount
        ud["bank"] += amount
        core.save_user(uid, ud)
        e = discord.Embed(title="🏦 Депозит", description=f"Положено **{core.fmt(amount)}** {core.CURRENCY}", color=discord.Color.blurple())
        e.add_field(name="👛 Кошелёк", value=f"{core.fmt(ud['wallet'])} {core.CURRENCY}")
        e.add_field(name="🏦 Банк", value=f"{core.fmt(ud['bank'])} {core.CURRENCY}")
        await inter.response.send_message(embed=e)

    # ---------- /withdraw ----------
    @app_commands.command(name="withdraw", description="💸 Снять деньги из банка")
    @app_commands.describe(amount="Сколько снять (0 = всё)")
    async def withdraw(self, inter: discord.Interaction, amount: int):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        if amount == 0:
            amount = ud["bank"]
        if amount <= 0:
            return await inter.response.send_message("❌ В банке нет денег!", ephemeral=True)
        if ud["bank"] < amount:
            return await inter.response.send_message(f"❌ Недостаточно! В банке {core.fmt(ud['bank'])} {core.CURRENCY}", ephemeral=True)
        ud["bank"] -= amount
        ud["wallet"] += amount
        core.save_user(uid, ud)
        e = discord.Embed(title="💸 Снятие", description=f"Снято **{core.fmt(amount)}** {core.CURRENCY}", color=discord.Color.blurple())
        e.add_field(name="👛 Кошелёк", value=f"{core.fmt(ud['wallet'])} {core.CURRENCY}")
        e.add_field(name="🏦 Банк", value=f"{core.fmt(ud['bank'])} {core.CURRENCY}")
        await inter.response.send_message(embed=e)

    # ---------- /bank ----------
    @app_commands.command(name="bank", description="🏦 Посмотреть баланс банка")
    async def bank(self, inter: discord.Interaction):
        ud = core.get_user(str(inter.user.id))
        now = time.time()
        next_int = max(0, core.COOLDOWNS["interest"] - (now - ud.get("last_interest", 0)))
        e = discord.Embed(title="🏦 Банк", color=discord.Color.blurple())
        e.add_field(name="🏦 В банке", value=f"**{core.fmt(ud['bank'])}** {core.CURRENCY}", inline=True)
        e.add_field(name="👛 В кошельке", value=f"**{core.fmt(ud['wallet'])}** {core.CURRENCY}", inline=True)
        e.add_field(name="💵 Всего", value=f"**{core.fmt(core.net_worth(ud))}** {core.CURRENCY}", inline=True)
        e.add_field(name="📈 Процент", value="**2%** каждые 12 часов", inline=False)
        e.add_field(name="⏳ До процентов", value=core.cd(next_int) if ud["bank"] > 0 else "Пополни банк!", inline=False)
        await inter.response.send_message(embed=e)

    # ---------- /interest ----------
    @app_commands.command(name="interest", description="📈 Забрать проценты по вкладу (раз в 12 ч)")
    async def interest(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        cd_ = core.COOLDOWNS["interest"]
        if now - ud.get("last_interest", 0) < cd_:
            return await inter.response.send_message(
                f"⏳ Проценты начисл через **{core.cd(cd_ - (now - ud['last_interest']))}**", ephemeral=True)
        if ud["bank"] <= 0:
            return await inter.response.send_message("❌ Сначала положи деньги в банк через `/deposit`!", ephemeral=True)
        gain = max(10, int(ud["bank"] * 0.02))
        ud["bank"] += gain
        ud["total_earned"] += gain
        ud["last_interest"] = now
        new = core.check_achievements(uid, ud)
        core.save_user(uid, ud)
        e = discord.Embed(title="📈 Проценты", description=f"Начислено **+{core.fmt(gain)}** {core.CURRENCY} (2%)", color=discord.Color.green())
        e.add_field(name="🏦 В банке", value=f"**{core.fmt(ud['bank'])}** {core.CURRENCY}")
        await reply(inter, e, new)

    # ---------- /give ----------
    @app_commands.command(name="give", description="🎁 Передать чирукойны игроку")
    @app_commands.describe(user="Кому передать", amount="Сколько")
    async def give(self, inter: discord.Interaction, user: discord.Member, amount: int):
        sid, rid = str(inter.user.id), str(user.id)
        if sid == rid:
            return await inter.response.send_message("❌ Нельзя передать себе!", ephemeral=True)
        if user.bot:
            return await inter.response.send_message("❌ Нельзя передать боту!", ephemeral=True)
        if amount <= 0:
            return await inter.response.send_message("❌ Сумма должна быть больше 0!", ephemeral=True)
        sd = core.get_user(sid)
        if sd["wallet"] < amount:
            return await inter.response.send_message(f"❌ Недостаточно! У тебя {core.fmt(sd['wallet'])} {core.CURRENCY}", ephemeral=True)
        rd = core.get_user(rid)
        sd["wallet"] -= amount
        rd["wallet"] += amount
        rd["total_earned"] += amount
        core.save_user(sid, sd)
        core.save_user(rid, rd)
        e = discord.Embed(title="🎁 Перевод", description=f"**{inter.user.display_name}** → **{user.display_name}**", color=discord.Color.blue())
        e.add_field(name="💰 Сумма", value=f"**{core.fmt(amount)}** {core.CURRENCY}", inline=False)
        e.add_field(name=inter.user.display_name, value=f"{core.fmt(sd['wallet'])} {core.CURRENCY}", inline=True)
        e.add_field(name=user.display_name, value=f"{core.fmt(rd['wallet'])} {core.CURRENCY}", inline=True)
        await inter.response.send_message(embed=e)

    # ---------- /admin-give ----------
    @app_commands.command(name="admin-give", description="⚡ [АДМИН] Выдать чирукойны игроку")
    @app_commands.describe(user="Кому выдать", amount="Сколько")
    @app_commands.default_permissions(administrator=True)
    async def admin_give(self, inter: discord.Interaction, user: discord.Member, amount: int):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        core.earn(str(user.id), amount)
        ud = core.get_user(str(user.id))
        e = discord.Embed(title="⚡ Админ-выдача", color=discord.Color.orange())
        e.add_field(name="Игрок", value=user.mention, inline=True)
        e.add_field(name="Выдано", value=f"**{core.fmt(amount)}** {core.CURRENCY}", inline=True)
        e.add_field(name="Баланс", value=f"**{core.fmt(ud['wallet'])}** {core.CURRENCY}", inline=False)
        await inter.response.send_message(embed=e)

    # ---------- /take ----------
    @app_commands.command(name="take", description="⚡ [АДМИН] Забрать чирукойны у игрока")
    @app_commands.describe(user="У кого забрать", amount="Сколько")
    @app_commands.default_permissions(administrator=True)
    async def take(self, inter: discord.Interaction, user: discord.Member, amount: int):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        ud = core.get_user(str(user.id))
        actual = min(ud["wallet"], amount)
        ud["wallet"] -= actual
        core.save_user(str(user.id), ud)
        e = discord.Embed(title="⚡ Изъятие", color=discord.Color.red())
        e.add_field(name="Игрок", value=user.mention, inline=True)
        e.add_field(name="Забрано", value=f"**{core.fmt(actual)}** {core.CURRENCY}", inline=True)
        e.add_field(name="Баланс", value=f"**{core.fmt(ud['wallet'])}** {core.CURRENCY}", inline=False)
        await inter.response.send_message(embed=e)

    # ---------- /setbalance ----------
    @app_commands.command(name="setbalance", description="⚡ [АДМИН] Установить точный баланс игроку")
    @app_commands.describe(user="Кому", amount="Сумма")
    @app_commands.default_permissions(administrator=True)
    async def setbalance(self, inter: discord.Interaction, user: discord.Member, amount: int):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        ud = core.get_user(str(user.id))
        ud["wallet"] = max(0, amount)
        core.save_user(str(user.id), ud)
        e = discord.Embed(title="⚡ Новый баланс", color=discord.Color.orange())
        e.add_field(name="Игрок", value=user.mention, inline=True)
        e.add_field(name="Баланс", value=f"**{core.fmt(ud['wallet'])}** {core.CURRENCY}", inline=True)
        await inter.response.send_message(embed=e)

    # ---------- /heist ----------
    @app_commands.command(name="heist", description="🏦 Крупное ограбление банка (Мин. 10 000 🪙)")
    async def heist(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        if now - ud.get("last_heist", 0) < core.COOLDOWNS["heist"]:
            return await inter.response.send_message(f"⏳ Полиция начеку! Следующее дело через **{core.cd(core.COOLDOWNS['heist'] - (now - ud['last_heist']))}**", ephemeral=True)
        if ud["wallet"] < 10000:
            return await inter.response.send_message("❌ Для такого дела нужно хотя бы **10 000** 🪙 в кошельке (на снаряжение)!", ephemeral=True)
        
        ud["last_heist"] = now
        ud["wallet"] -= 10000
        core.save_user(uid, ud)
        
        r = random.random()
        if r < 0.20:
            gain = random.randint(20000, 100000)
            ud, new = core.earn(uid, gain)
            e = discord.Embed(title="🏦 Ограбление века УДАЛОСЬ!", description=f"Вы вскрыли хранилище и вынесли **{core.fmt(gain)}** {core.CURRENCY}!\n*(-10 000 🪙 на снаряжение)*", color=discord.Color.green())
        else:
            loss = random.randint(5000, 15000)
            ud = core.get_user(uid)
            actual_loss = min(ud["wallet"], loss)
            ud["wallet"] -= actual_loss
            new = core.check_achievements(uid, ud)
            core.save_user(uid, ud)
            e = discord.Embed(title="🚔 ПРОВАЛ ОГРАБЛЕНИЯ", description=f"Спецназ оказался быстрее! Вы потеряли **10 000** 🪙 за подготовку и ещё штраф **{core.fmt(actual_loss)}** {core.CURRENCY}!", color=discord.Color.red())
        
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await reply(inter, e, new)

async def setup(bot):
    await bot.add_cog(Economy(bot))
