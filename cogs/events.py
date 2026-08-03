"""cogs/events.py — ивенты: дождь денег, лотерея, аукцион, сундуки."""

import discord
import time
import random
from discord import app_commands
from discord.ext import commands, tasks
import core

TICKET_PRICE = 100


class RainView(discord.ui.View):
    def __init__(self, amount):
        super().__init__(timeout=120)
        self.amount = amount
        self.claimed = False

    @discord.ui.button(label="🌧️ Схватить деньги!", style=discord.ButtonStyle.primary)
    async def grab(self, inter, btn):
        if self.claimed:
            return await inter.response.send_message("Опоздал! Деньги уже схватили 😢", ephemeral=True)
        self.claimed = True
        for c in self.children:
            c.disabled = True
        ud, new = core.earn(str(inter.user.id), self.amount)
        await inter.response.edit_message(content=f"🎉 **{inter.user.display_name}** поймал(а) дождь из **{core.fmt(self.amount)}** {core.CURRENCY}!", view=self)
        self.stop()


def all_item_choices(current):
    opts = []
    for iid, it in core.ALL_ITEMS.items():
        if current.lower() in it["name"].lower() or current.lower() in iid:
            opts.append(app_commands.Choice(name=it["name"][:100], value=iid))
    return opts[:25]


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rain_loop.start()
        self.auction_loop.start()
        self.lottery_loop.start()
        self.rare_events_loop.start()

    def cog_unload(self):
        self.rain_loop.cancel()
        self.auction_loop.cancel()
        self.lottery_loop.cancel()
        self.rare_events_loop.cancel()

    # ---------- ДОЖДЬ ДЕНЕГ ----------
    @tasks.loop(hours=2)
    async def rain_loop(self):
        ch_id = core.get_event_channel()
        if not ch_id:
            return
        ch = self.bot.get_channel(ch_id)
        if not ch:
            return
        amount = random.randint(200, 1500)
        e = discord.Embed(title="🌧️ ДОЖДЬ ДЕНЕГ!", description=f"Чирукойны льются с неба!\nПервый, кто нажмёт кнопку, забирает **{core.fmt(amount)}** {core.CURRENCY}!", color=discord.Color.gold())
        try:
            await ch.send(embed=e, view=RainView(amount))
        except Exception:
            pass

    @rain_loop.before_loop
    async def before_rain(self):
        await self.bot.wait_until_ready()

    # ---------- ЛОТЕРЕЯ (ежедневная) ----------
    @tasks.loop(hours=24)
    async def lottery_loop(self):
        data = core.load_data()
        lot = data.get("lottery", {"tickets": {}})
        tickets = lot.get("tickets", {})
        if not tickets:
            return
            
        pool = list(tickets.keys())
        weights = [tickets[u] for u in pool]
        winner = random.choices(pool, weights=weights)[0]
        pot = sum(weights) * 100
        
        core.earn(winner, pot)
        data["lottery"] = {"tickets": {}}
        core.save_data(data)
        
        ch_id = core.get_event_channel()
        if ch_id:
            ch = self.bot.get_channel(ch_id)
            if ch:
                try:
                    u = await self.bot.fetch_user(int(winner))
                    await ch.send(embed=discord.Embed(title="🎟️ РОЗЫГРЫШ ЛОТЕРЕИ!", description=f"🏆 Победитель: {u.mention}\n💰 Выигрыш: **{core.fmt(pot)}** {core.CURRENCY}!", color=discord.Color.gold()))
                except Exception:
                    pass

    @lottery_loop.before_loop
    async def before_lottery(self):
        await self.bot.wait_until_ready()

    # ---------- РЕДКИЕ СОБЫТИЯ ----------
    @tasks.loop(hours=1)
    async def rare_events_loop(self):
        ch_id = core.get_event_channel()
        if not ch_id:
            return
        ch = self.bot.get_channel(ch_id)
        if not ch:
            return
        if random.random() < 0.3: # 30% шанс раз в час
            amount = random.randint(1000, 5000)
            e = discord.Embed(title="💰 Кошелек найден!", description=f"Кто-то обронил кошелек с **{core.fmt(amount)}** {core.CURRENCY}!\nНажми первым, чтобы забрать!", color=discord.Color.gold())
            try:
                await ch.send(embed=e, view=RainView(amount))
            except Exception:
                pass
        elif random.random() < 0.2: # 20% шанс
            amount = random.randint(3000, 10000)
            e = discord.Embed(title="🎁 Yachiru оставила сундук!", description=f"Легендарный сундук появился!\nПервый, кто нажмёт, заберёт **{core.fmt(amount)}** {core.CURRENCY}!", color=discord.Color.purple())
            try:
                await ch.send(embed=e, view=RainView(amount))
            except Exception:
                pass

    @rare_events_loop.before_loop
    async def before_rare(self):
        await self.bot.wait_until_ready()

    # ---------- АУКЦИОН (закрытие) ----------
    @tasks.loop(seconds=30)
    async def auction_loop(self):
        data = core.load_data()
        au = data.get("auction")
        if not au or not au.get("active") or time.time() < au.get("end", 0):
            return
        au["active"] = False
        it = core.ALL_ITEMS.get(au.get("item_id"))
        ch = self.bot.get_channel(core.get_event_channel())
        if au.get("leader_id") and it:
            wd = data.get(au["leader_id"]) or core.get_user(au["leader_id"])
            if isinstance(wd, dict) and wd.get("wallet", 0) >= au["price"]:
                wd["wallet"] -= au["price"]
                if it["type"] == "consumable":
                    wd["consumables"][it["id"]] = wd.get("consumables", {}).get(it["id"], 0) + 1
                else:
                    wd.setdefault("items", []).append(it["id"])
                core.check_achievements(au["leader_id"], wd)
                data[au["leader_id"]] = wd
                msg = f"🔨 Аукцион окончен! **{au['leader_name']}** забирает **{it['name']}** за **{core.fmt(au['price'])}** {core.CURRENCY}!"
            else:
                msg = "🔨 Аукцион окончен, но победитель не смог оплатить — лот сгорел."
        else:
            msg = "🔨 Аукцион окончен — ставок не было."
        data["auction"] = au
        core.save_data(data)
        if ch:
            try:
                await ch.send(msg)
            except Exception:
                pass

    @auction_loop.before_loop
    async def before_auction(self):
        await self.bot.wait_until_ready()

    # ---------- /treasure ----------
    @app_commands.command(name="treasure", description="🎁 Открыть сундук с сокровищами (раз в час)")
    async def treasure(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        if now - ud.get("last_treasure", 0) < core.COOLDOWNS["treasure"]:
            return await inter.response.send_message(f"⏳ Следующий сундук через **{core.cd(core.COOLDOWNS['treasure'] - (now - ud['last_treasure']))}**", ephemeral=True)
        ud["last_treasure"] = now
        core.save_user(uid, ud)
        r = random.random()
        if r < 0.55:
            gain = random.randint(50, 500)
            ud, new = core.earn(uid, gain)
            e = discord.Embed(title="🎁 Сундук", description=f"В сундуке **{core.fmt(gain)}** {core.CURRENCY}!", color=discord.Color.gold())
        elif r < 0.82:
            cid = random.choice(list(core.CONSUMABLES.keys()))
            ud = core.get_user(uid)
            ud["consumables"][cid] = ud["consumables"].get(cid, 0) + 1
            new = core.check_achievements(uid, ud)
            core.save_user(uid, ud)
            e = discord.Embed(title="🎁 Сундук", description=f"Ты нашёл **{core.ALL_ITEMS[cid]['name']}**!", color=discord.Color.purple())
        elif r < 0.96:
            iid = random.choice(list(core.BONUS_ITEMS.keys()) + list(core.INCOME_ITEMS.keys()))
            ud = core.get_user(uid)
            if iid in ud["items"]:
                gain = random.randint(500, 1000)
                ud["wallet"] += gain
                ud["total_earned"] += gain
                e = discord.Embed(title="🎁 Сундук", description=f"Дубликат! Получено **{core.fmt(gain)}** {core.CURRENCY}!", color=discord.Color.gold())
            else:
                ud["items"].append(iid)
                e = discord.Embed(title="🎁 РЕДКИЙ СУНДУК!", description=f"Ты нашёл **{core.ALL_ITEMS[iid]['name']}**! 🎉", color=discord.Color.gold())
            new = core.check_achievements(uid, ud)
            core.save_user(uid, ud)
        else:
            gain = random.randint(1000, 5000)
            ud, new = core.earn(uid, gain)
            e = discord.Embed(title="💎 ОГРОМНЫЙ СУНДУК!", description=f"ДЖЕКПОТ! **{core.fmt(gain)}** {core.CURRENCY}!", color=discord.Color.gold())
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        if new:
            e.add_field(name="🎯 Достижение!", value=core.ach_text(new), inline=False)
        await inter.response.send_message(embed=e)

    # ---------- /lottery ----------
    lottery = app_commands.Group(name="lottery", description="🎟️ Лотерея")

    @lottery.command(name="buy", description="Купить билеты лотереи (100 🪙 за билет)")
    @app_commands.describe(amount="Сколько билетов")
    async def lottery_buy(self, inter: discord.Interaction, amount: int):
        uid = str(inter.user.id)
        if amount <= 0:
            return await inter.response.send_message("❌ Хочешь 0 билетов?", ephemeral=True)
        cost = amount * TICKET_PRICE
        ok, _ = core.spend(uid, cost)
        if not ok:
            return await inter.response.send_message(f"❌ Недостаточно! Нужно {core.fmt(cost)} {core.CURRENCY}", ephemeral=True)
        data = core.load_data()
        lot = data.get("lottery", {"tickets": {}})
        lot.setdefault("tickets", {})
        lot["tickets"][uid] = lot["tickets"].get(uid, 0) + amount
        data["lottery"] = lot
        core.save_data(data)
        await inter.response.send_message(embed=discord.Embed(title="🎟️ Билеты куплены!", description=f"Ты купил **{amount}** билетов за **{core.fmt(cost)}** {core.CURRENCY}", color=discord.Color.green()))

    @lottery.command(name="info", description="Информация о лотерее")
    async def lottery_info(self, inter: discord.Interaction):
        data = core.load_data()
        lot = data.get("lottery", {"tickets": {}})
        tickets = lot.get("tickets", {})
        total_t = sum(tickets.values())
        pot = total_t * TICKET_PRICE
        mine = tickets.get(str(inter.user.id), 0)
        chance = (mine / total_t * 100) if total_t else 0
        e = discord.Embed(title="🎟️ Лотерея", color=discord.Color.gold())
        e.add_field(name="💰 Призовой фонд", value=f"**{core.fmt(pot)}** {core.CURRENCY}")
        e.add_field(name="🎫 Всего билетов", value=f"**{total_t}**")
        e.add_field(name="🎫 Твоих билетов", value=f"**{mine}** ({chance:.1f}% шанс)")
        e.set_footer(text="Розыгрыш: /lottery draw (для админов)")
        await inter.response.send_message(embed=e)

    @lottery.command(name="draw", description="[АДМИН] Провести розыгрыш лотереи")
    @app_commands.default_permissions(administrator=True)
    async def lottery_draw(self, inter: discord.Interaction):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для админов!", ephemeral=True)
        data = core.load_data()
        lot = data.get("lottery", {"tickets": {}})
        tickets = lot.get("tickets", {})
        if not tickets:
            return await inter.response.send_message("📭 Никто не купил билеты!", ephemeral=True)
        pool = list(tickets.keys())
        weights = [tickets[u] for u in pool]
        winner = random.choices(pool, weights=weights)[0]
        pot = sum(weights) * TICKET_PRICE
        core.earn(winner, pot)
        data["lottery"] = {"tickets": {}}
        core.save_data(data)
        wname = winner
        try:
            u = await self.bot.fetch_user(int(winner))
            wname = u.mention
        except Exception:
            pass
        await inter.response.send_message(embed=discord.Embed(title="🎟️ РОЗЫГРЫШ ЛОТЕРЕИ!", description=f"🏆 Победитель: {wname}\n💰 Выигрыш: **{core.fmt(pot)}** {core.CURRENCY}!", color=discord.Color.gold()))

    # ---------- /auction ----------
    auction = app_commands.Group(name="auction", description="🔨 Аукцион редких предметов")

    @auction.command(name="start", description="[АДМИН] Начать аукцион (10 минут)")
    @app_commands.describe(item="Предмет", start_price="Стартовая цена")
    @app_commands.autocomplete(item=lambda inter, c: all_item_choices(c))
    @app_commands.default_permissions(administrator=True)
    async def auction_start(self, inter: discord.Interaction, item: str, start_price: int):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для админов!", ephemeral=True)
        it = core.ALL_ITEMS.get(item)
        if not it:
            return await inter.response.send_message("❌ Неверный предмет!", ephemeral=True)
        if start_price <= 0:
            return await inter.response.send_message("❌ Цена больше 0!", ephemeral=True)
        data = core.load_data()
        data["auction"] = {"active": True, "item_id": item, "price": start_price, "leader_id": None, "leader_name": None, "end": time.time() + 600}
        core.save_data(data)
        e = discord.Embed(title="🔨 АУКЦИОН НАЧАЛСЯ!", description=f"Предмет: **{it['name']}**\nСтартовая цена: **{core.fmt(start_price)}** {core.CURRENCY}\n⏱️ Заканчивается через 10 минут!", color=discord.Color.orange())
        e.set_footer(text="Делай ставки командой /bid (мин. +5% к текущей)")
        await inter.response.send_message(embed=e)

    # ---------- /bid ----------
    @app_commands.command(name="bid", description="🔨 Сделать ставку на аукционе")
    @app_commands.describe(amount="Твоя ставка")
    async def bid(self, inter: discord.Interaction, amount: int):
        uid = str(inter.user.id)
        data = core.load_data()
        au = data.get("auction")
        if not au or not au.get("active"):
            return await inter.response.send_message("❌ Сейчас нет активного аукциона!", ephemeral=True)
        if amount < au["price"] * 1.05:
            return await inter.response.send_message(f"❌ Ставка слишком мала! Минимум **{core.fmt(int(au['price'] * 1.05))}** {core.CURRENCY}", ephemeral=True)
        if core.get_user(uid)["wallet"] < amount:
            return await inter.response.send_message("❌ Недостаточно денег в кошельке!", ephemeral=True)
        au["price"] = amount
        au["leader_id"] = uid
        au["leader_name"] = inter.user.display_name
        data["auction"] = au
        core.save_data(data)
        await inter.response.send_message(embed=discord.Embed(title="🔨 Ставка принята!", description=f"**{inter.user.display_name}** лидирует со ставкой **{core.fmt(amount)}** {core.CURRENCY}", color=discord.Color.orange()))

    # ---------- /seteventchannel ----------
    @app_commands.command(name="seteventchannel", description="📢 [АДМИН] Установить канал для ивентов (дождь, аукционы)")
    @app_commands.default_permissions(administrator=True)
    async def seteventchannel(self, inter: discord.Interaction):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для админов!", ephemeral=True)
        core.set_event_channel(inter.channel_id)
        await inter.response.send_message(embed=discord.Embed(title="📢 Канал ивентов установлен!", description=f"Теперь сюда будут падать дожди денег и результаты аукционов: {inter.channel.mention}", color=discord.Color.green()))


async def setup(bot):
    await bot.add_cog(Events(bot))
