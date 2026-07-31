"""cogs/shop.py — магазин, инвентарь, использование предметов, рынок игроков, пассивный доход."""

import discord
import time
import random
from discord import app_commands
from discord.ext import commands
import core


def item_autocomplete_all(inter, current):
    opts = []
    for iid, it in core.ALL_ITEMS.items():
        label = f"{it['name']} — {core.fmt(it['price'])} {core.CURRENCY}"
        if current.lower() in it["name"].lower() or current.lower() in iid:
            opts.append(app_commands.Choice(name=label[:100], value=iid))
    return opts[:25]


def item_autocomplete_owned(inter, current, kinds):
    uid = str(inter.user.id)
    ud = core.get_user(uid)
    opts = []
    for iid in ud["items"]:
        it = core.ALL_ITEMS.get(iid)
        if it and (not kinds or it["type"] in kinds):
            if current.lower() in it["name"].lower() or current.lower() in iid:
                opts.append(app_commands.Choice(name=it["name"][:100], value=iid))
    if "consumable" in (kinds or []):
        for iid, cnt in ud.get("consumables", {}).items():
            it = core.ALL_ITEMS.get(iid)
            if it and cnt > 0 and (current.lower() in it["name"].lower() or current.lower() in iid):
                opts.append(app_commands.Choice(name=f"{it['name']} (x{cnt})"[:100], value=iid))
    return opts[:25]


class MarketBuySelect(discord.ui.Select):
    def __init__(self, buyer_id, listings):
        self.buyer_id = buyer_id
        opts = []
        for lst in listings:
            it = core.ALL_ITEMS.get(lst["item_id"])
            if not it:
                continue
            opts.append(app_commands.SelectOption(
                label=f"{it['name']} — {core.fmt(lst['price'])} {core.CURRENCY}",
                description=f"Продавец: {lst['seller_name']}",
                value=lst["id"], emoji=it["name"][:2]))
        super().__init__(placeholder="Выбери предмет для покупки...", options=opts or [app_commands.SelectOption(label="Пусто", value="none")])

    async def callback(self, inter):
        if str(inter.user.id) != self.buyer_id:
            return await inter.response.send_message("Это не твой рынок!", ephemeral=True)
        if self.values[0] == "none":
            return
        data = core.load_data()
        market = data.get("market", [])
        lst = next((l for l in market if l["id"] == self.values[0]), None)
        if not lst:
            return await inter.response.send_message("Лот уже продан!", ephemeral=True)
        if lst["seller_id"] == self.buyer_id:
            return await inter.response.send_message("Нельзя купить свой лот!", ephemeral=True)
        buyer = core.get_user(self.buyer_id)
        if buyer["wallet"] < lst["price"]:
            return await inter.response.send_message(f"❌ Недостаточно! Нужно {core.fmt(lst['price'])} {core.CURRENCY}", ephemeral=True)
        seller = core.get_user(lst["seller_id"])
        # передаём предмет
        if lst["kind"] == "consumable":
            buyer["consumables"][lst["item_id"]] = buyer["consumables"].get(lst["item_id"], 0) + 1
        else:
            buyer["items"].append(lst["item_id"])
        buyer["wallet"] -= lst["price"]
        seller["wallet"] += lst["price"]
        seller["total_earned"] += lst["price"]
        market = [l for l in market if l["id"] != lst["id"]]
        data["market"] = market
        data[self.buyer_id] = buyer
        data[lst["seller_id"]] = seller
        core.save_data(data)
        it = core.ALL_ITEMS.get(lst["item_id"])
        await inter.response.send_message(f"✅ Ты купил **{it['name']}** за **{core.fmt(lst['price'])}** {core.CURRENCY}!", embed=None)
        for c in self.view.children:
            c.disabled = True
        await inter.message.edit(view=self.view)


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- /shop ----------
    @app_commands.command(name="shop", description="🛒 Магазин предметов")
    async def shop(self, inter: discord.Interaction):
        ud = core.get_user(str(inter.user.id))
        e = discord.Embed(title="🛒 Магазин чирукойнов", description="Покупай предметы через `/buy`", color=discord.Color.purple())
        e.add_field(name="📈 Бонусы к работе", value="\n".join(f"{it['name']} — {core.fmt(it['price'])} {core.CURRENCY} ({it['desc']})" for it in core.BONUS_ITEMS.values()) or "—", inline=False)
        e.add_field(name="🏦 Пассивный доход", value="\n".join(f"{it['name']} — {core.fmt(it['price'])} {core.CURRENCY} ({it['desc']})" for it in core.INCOME_ITEMS.values()) or "—", inline=False)
        e.add_field(name="🎁 Расходники", value="\n".join(f"{it['name']} — {core.fmt(it['price'])} {core.CURRENCY} ({it['desc']})" for it in core.CONSUMABLES.values()) or "—", inline=False)
        e.set_footer(text=f"Бонус к работе: +{core.get_bonus_percent(ud)}% | Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await inter.response.send_message(embed=e)

    # ---------- /buy ----------
    @app_commands.command(name="buy", description="🛍️ Купить конкретный предмет")
    @app_commands.describe(item="Название предмета")
    @app_commands.autocomplete(item=item_autocomplete_all)
    async def buy(self, inter: discord.Interaction, item: str):
        uid = str(inter.user.id)
        it = core.ALL_ITEMS.get(item)
        if not it:
            return await inter.response.send_message("❌ Такого предмета нет в магазине!", ephemeral=True)
        ud = core.get_user(uid)
        if it["type"] != "consumable" and item in ud["items"]:
            return await inter.response.send_message(f"❌ У тебя уже есть **{it['name']}**!", ephemeral=True)
        if ud["wallet"] < it["price"]:
            return await inter.response.send_message(f"❌ Не хватает! Нужно {core.fmt(it['price'])} {core.CURRENCY}", ephemeral=True)
        ud["wallet"] -= it["price"]
        if it["type"] == "consumable":
            ud["consumables"][item] = ud["consumables"].get(item, 0) + 1
        else:
            ud["items"].append(item)
        new = core.check_achievements(uid, ud)
        core.save_user(uid, ud)
        core.progress_quest(uid, "buy")
        core.add_xp(uid, 5)
        e = discord.Embed(title="✅ Куплено!", description=f"**{it['name']}** за **{core.fmt(it['price'])}** {core.CURRENCY}", color=discord.Color.green())
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        if new:
            e.add_field(name="🎯 Достижение!", value=core.ach_text(new), inline=False)
        await inter.response.send_message(embed=e)

    # ---------- /sell ----------
    @app_commands.command(name="sell", description="💸 Продать предмет боту (50% цены)")
    @app_commands.describe(item="Название предмета")
    @app_commands.autocomplete(item=lambda inter, c: item_autocomplete_owned(inter, c, ["bonus", "income", "consumable"]))
    async def sell(self, inter: discord.Interaction, item: str):
        uid = str(inter.user.id)
        it = core.ALL_ITEMS.get(item)
        if not it:
            return await inter.response.send_message("❌ Неверный предмет!", ephemeral=True)
        ud = core.get_user(uid)
        if it["type"] == "consumable":
            if ud["consumables"].get(item, 0) <= 0:
                return await inter.response.send_message("❌ У тебя нет такого предмета!", ephemeral=True)
            ud["consumables"][item] -= 1
        else:
            if item not in ud["items"]:
                return await inter.response.send_message("❌ У тебя нет такого предмета!", ephemeral=True)
            ud["items"].remove(item)
        refund = it["price"] // 2
        ud["wallet"] += refund
        core.save_user(uid, ud)
        e = discord.Embed(title="💸 Продажа", description=f"Ты продал **{it['name']}** за **{core.fmt(refund)}** {core.CURRENCY} (50%)", color=discord.Color.orange())
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await inter.response.send_message(embed=e)

    # ---------- /inventory ----------
    @app_commands.command(name="inventory", description="🎒 Твой инвентарь")
    async def inventory(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        e = discord.Embed(title=f"🎒 Инвентарь — {inter.user.display_name}", color=discord.Color.purple())
        perm = [core.ALL_ITEMS[i]["name"] for i in ud["items"] if i in core.ALL_ITEMS]
        cons = [f"{core.ALL_ITEMS[i]['name']} x{c}" for i, c in ud.get("consumables", {}).items() if c > 0 and i in core.ALL_ITEMS]
        e.add_field(name="📦 Предметы", value="\n".join(perm) or "Пусто", inline=False)
        e.add_field(name="🎁 Расходники", value="\n".join(cons) or "Пусто", inline=False)
        avail, _ = core.passive_income(ud)
        e.add_field(name="📊 Бонус к работе", value=f"+{core.get_bonus_percent(ud)}%", inline=True)
        e.add_field(name="🏦 Накопилось дохода", value=f"{core.fmt(avail)} {core.CURRENCY}", inline=True)
        e.set_footer(text="Забери доход: /collect")
        await inter.response.send_message(embed=e)

    # ---------- /use ----------
    @app_commands.command(name="use", description="✨ Использовать расходник")
    @app_commands.describe(item="Название расходника")
    @app_commands.autocomplete(item=lambda inter, c: item_autocomplete_owned(inter, c, ["consumable"]))
    async def use(self, inter: discord.Interaction, item: str):
        uid = str(inter.user.id)
        it = core.ALL_ITEMS.get(item)
        if not it or it["type"] != "consumable":
            return await inter.response.send_message("❌ Это нельзя использовать!", ephemeral=True)
        ud = core.get_user(uid)
        if ud["consumables"].get(item, 0) <= 0:
            return await inter.response.send_message("❌ У тебя нет такого предмета!", ephemeral=True)
        ud["consumables"][item] -= 1
        now = time.time()
        if item == "lucky_charm":
            ud["boost_mult"] = 2.0
            ud["boost_until"] = now + 3600
            txt = "🍀 Талисман удачи! Следующий `/work` принесёт **x2**!"
        elif item == "energy_drink":
            ud["boost_mult"] = 1.5
            ud["boost_until"] = now + 3600
            txt = "⚡ Энергетик! Следующий `/work` принесёт **+50%**!"
        elif item == "shield":
            ud["shield_until"] = now + 86400
            txt = "🛡️ Щит активирован на 24 часа — тебя нельзя ограбить!"
        elif item == "mystery_box":
            r = random.random()
            if r < 0.7:
                gain = random.randint(100, 2000)
                ud["wallet"] += gain
                ud["total_earned"] += gain
                txt = f"🎁 В ящике **{core.fmt(gain)}** {core.CURRENCY}!"
            else:
                reward_id = random.choice(list(core.CONSUMABLES.keys()))
                ud["consumables"][reward_id] = ud["consumables"].get(reward_id, 0) + 1
                txt = f"🎁 В ящике предмет: **{core.ALL_ITEMS[reward_id]['name']}**!"
        else:
            txt = "Ничего не произошло."
        new = core.check_achievements(uid, ud)
        core.save_user(uid, ud)
        e = discord.Embed(title="✨ Предмет использован", description=txt, color=discord.Color.gold())
        if new:
            e.add_field(name="🎯 Достижение!", value=core.ach_text(new), inline=False)
        await inter.response.send_message(embed=e)

    # ---------- /collect ----------
    @app_commands.command(name="collect", description="🏦 Забрать накопившийся пассивный доход")
    async def collect(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        amount, lines = core.passive_income(ud, now)
        if amount <= 0:
            return await inter.response.send_message("❌ Нечего забирать! Купи дома/заводы в `/shop`.", ephemeral=True)
        ud["wallet"] += amount
        ud["total_earned"] += amount
        ud["last_collect"] = now
        new = core.check_achievements(uid, ud)
        core.save_user(uid, ud)
        e = discord.Embed(title="🏦 Доход собран", description=f"Получено **+{core.fmt(amount)}** {core.CURRENCY}", color=discord.Color.green())
        if lines:
            e.add_field(name="📋 Детали", value="\n".join(lines), inline=False)
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        if new:
            e.add_field(name="🎯 Достижение!", value=core.ach_text(new), inline=False)
        await inter.response.send_message(embed=e)

    # ---------- /market группа ----------
    market = app_commands.Group(name="market", description="🏪 Рынок между игроками")

    @market.command(name="sell", description="Выставить свой предмет на продажу")
    @app_commands.describe(item="Предмет", price="Цена в чирукойнах")
    @app_commands.autocomplete(item=lambda inter, c: item_autocomplete_owned(inter, c, ["bonus", "income", "consumable"]))
    async def market_sell(self, inter: discord.Interaction, item: str, price: int):
        uid = str(inter.user.id)
        it = core.ALL_ITEMS.get(item)
        if not it:
            return await inter.response.send_message("❌ Неверный предмет!", ephemeral=True)
        if price <= 0:
            return await inter.response.send_message("❌ Цена больше 0!", ephemeral=True)
        ud = core.get_user(uid)
        data = core.load_data()
        # забираем предмет у продавца
        if it["type"] == "consumable":
            if ud["consumables"].get(item, 0) <= 0:
                return await inter.response.send_message("❌ У тебя нет такого предмета!", ephemeral=True)
            ud["consumables"][item] -= 1
        else:
            if item not in ud["items"]:
                return await inter.response.send_message("❌ У тебя нет такого предмета!", ephemeral=True)
            ud["items"].remove(item)
        market = data.get("market", [])
        listing = {"id": f"{uid}_{int(time.time()*1000)}", "seller_id": uid, "seller_name": inter.user.display_name,
                   "item_id": item, "price": price, "kind": it["type"]}
        market.append(listing)
        data["market"] = market
        data[uid] = ud
        core.save_data(data)
        await inter.response.send_message(f"✅ **{it['name']}** выставлен на рынок за **{core.fmt(price)}** {core.CURRENCY}!\nКупят — смотри `/market browse`.")

    @market.command(name="browse", description="Посмотреть товары на рынке")
    async def market_browse(self, inter: discord.Interaction):
        data = core.load_data()
        market = data.get("market", [])[:25]
        if not market:
            return await inter.response.send_message("📭 Рынок пуст! Выставляй товары через `/market sell`.", ephemeral=True)
        e = discord.Embed(title="🏪 Рынок игроков", color=discord.Color.purple())
        for lst in market:
            it = core.ALL_ITEMS.get(lst["item_id"])
            if it:
                e.add_field(name=f"{it['name']} — {core.fmt(lst['price'])} {core.CURRENCY}", value=f"Продавец: {lst['seller_name']}", inline=True)
        view = discord.ui.View(timeout=120)
        view.add_item(MarketBuySelect(str(inter.user.id), market))
        await inter.response.send_message(embed=e, view=view)


async def setup(bot):
    await bot.add_cog(Shop(bot))
