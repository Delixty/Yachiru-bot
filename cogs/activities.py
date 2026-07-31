"""cogs/activities.py — рыбалка, шахта, ферма, кейсы, биржа."""

import discord
import random
import time
from discord import app_commands
from discord.ext import commands
import core

class Activities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- /fish ----------
    @app_commands.command(name="fish", description="🐟 Отправиться на рыбалку (раз в 5 минут)")
    async def fish(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        cd = core.COOLDOWNS["fish"]
        if now - ud.get("last_fish", 0) < cd:
            return await inter.response.send_message(f"⏳ Рыба не клюёт... Жди **{core.cd(cd - (now - ud['last_fish']))}**", ephemeral=True)
            
        ud["last_fish"] = now
        core.add_xp(uid, 5)
        
        has_rod = "fishing_rod" in ud["items"]
        
        r = random.random()
        if r < 0.15:
            item = "boot"
            msg = "Ты поймал **дырявый ботинок**! 🥾 Ну, хоть что-то..."
        elif r < (0.8 if has_rod else 0.65):
            item = "fish"
            msg = "Удачный улов! Ты поймал **рыбу**! 🐟"
        elif r < (0.95 if has_rod else 0.9):
            item = "crop"
            msg = "Ты выловил чей-то потерянный **мешок с урожаем**! 🌾 Странно, но ладно."
        else:
            item = "gold_coin"
            msg = "✨ ВАУ! Ты выловил из воды **Золотую монету**! 🟨"
            
        if core.ALL_ITEMS[item]["type"] == "consumable":
            ud["consumables"][item] = ud.get("consumables", {}).get(item, 0) + 1
        elif core.ALL_ITEMS[item]["type"] == "collection":
            if item not in ud["items"]:
                ud["items"].append(item)
            else:
                ud["wallet"] += 5000
                msg += "\n*У тебя уже была такая монета, ты продал её скупщику за 5000 🪙.*"
        else: # resource
            ud["consumables"][item] = ud.get("consumables", {}).get(item, 0) + 1
            
        core.save_user(uid, ud)
        await inter.response.send_message(embed=discord.Embed(title="🎣 Рыбалка", description=msg, color=discord.Color.blue()))

    # ---------- /mine ----------
    @app_commands.command(name="mine", description="⛏️ Спуститься в шахту (раз в 5 минут)")
    async def mine(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        now = time.time()
        cd = core.COOLDOWNS["mine"]
        if now - ud.get("last_mine", 0) < cd:
            return await inter.response.send_message(f"⏳ Ты устал махать киркой. Жди **{core.cd(cd - (now - ud['last_mine']))}**", ephemeral=True)
            
        ud["last_mine"] = now
        core.add_xp(uid, 5)
        
        has_pick = "pickaxe" in ud["items"]
        
        amt = random.randint(1, 3)
        if has_pick:
            amt += random.randint(1, 2)
            
        ud["consumables"]["ore"] = ud.get("consumables", {}).get("ore", 0) + amt
        
        msg = f"Ты добыл **{amt} шт. Руды**! 🪨"
        
        # Шанс найти редкую коллекционку
        if random.random() < (0.05 if has_pick else 0.01):
            if "mask" not in ud["items"]:
                ud["items"].append("mask")
                msg += "\n\n✨ **НЕВЕРОЯТНАЯ НАХОДКА!** В глубине шахты ты нашёл **Маску**! 🟪"
            else:
                ud["wallet"] += 5000
                msg += "\n\nТы нашел древнюю реликвию и продал её за 5000 🪙."
                
        core.save_user(uid, ud)
        await inter.response.send_message(embed=discord.Embed(title="⛏️ Шахта", description=msg, color=discord.Color.dark_grey()))

    # ---------- /farm ----------
    farm = app_commands.Group(name="farm", description="🌾 Ферма")
    
    @farm.command(name="plant", description="Посадить семена на ферме")
    async def farm_plant(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        
        if ud["farm"].get("planted", 0) > 0:
            return await inter.response.send_message("❌ У тебя уже что-то посажено! Собери урожай через `/farm harvest`.", ephemeral=True)
            
        ud["farm"]["planted"] = time.time()
        core.save_user(uid, ud)
        core.add_xp(uid, 2)
        await inter.response.send_message(embed=discord.Embed(title="🌾 Ферма", description="Ты посадил семена! 🌱\nУрожай созреет через 4 часа.", color=discord.Color.green()))

    @farm.command(name="harvest", description="Собрать созревший урожай")
    async def farm_harvest(self, inter: discord.Interaction):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        
        planted = ud["farm"].get("planted", 0)
        if planted == 0:
            return await inter.response.send_message("❌ У тебя ничего не посажено! Напиши `/farm plant`.", ephemeral=True)
            
        now = time.time()
        elapsed = now - planted
        
        if elapsed < 14400: # 4 часа
            return await inter.response.send_message(f"⏳ Урожай еще зреет... Осталось **{core.cd(14400 - elapsed)}**.", ephemeral=True)
            
        ud["farm"]["planted"] = 0
        amt = random.randint(3, 8)
        ud["consumables"]["crop"] = ud.get("consumables", {}).get("crop", 0) + amt
        
        core.save_user(uid, ud)
        core.add_xp(uid, 10)
        await inter.response.send_message(embed=discord.Embed(title="🌾 Ферма", description=f"Ты собрал **{amt} шт. Урожая**! 🌾\nМожешь продать его через `/sell item:crop`.", color=discord.Color.green()))

    # ---------- /case ----------
    case = app_commands.Group(name="case", description="📦 Кейсы")
    
    @case.command(name="open", description="Открыть кейс из инвентаря")
    @app_commands.describe(case_type="Какой кейс открыть")
    @app_commands.choices(case_type=[
        app_commands.Choice(name="📦 Обычный кейс", value="case_normal"),
        app_commands.Choice(name="🔮 Редкий кейс", value="case_rare"),
    ])
    async def case_open(self, inter: discord.Interaction, case_type: app_commands.Choice[str]):
        uid = str(inter.user.id)
        ud = core.get_user(uid)
        ctype = case_type.value
        
        if ud.get("consumables", {}).get(ctype, 0) <= 0:
            return await inter.response.send_message(f"❌ У тебя нет **{core.ALL_ITEMS[ctype]['name']}**! Купи его в магазине.", ephemeral=True)
            
        ud["consumables"][ctype] -= 1
        
        msg = ""
        r = random.random()
        
        if ctype == "case_normal":
            if r < 0.6:
                gain = random.randint(500, 3000)
                ud["wallet"] += gain
                msg = f"Ты открыл кейс и нашёл **{core.fmt(gain)}** 🪙!"
            elif r < 0.9:
                ud["consumables"]["ore"] = ud.get("consumables", {}).get("ore", 0) + 10
                msg = f"В кейсе оказалось **10 шт. Руды**! 🪨"
            else:
                ud["items"].append("fishing_rod") if "fishing_rod" not in ud["items"] else None
                msg = f"В кейсе лежала **Удочка**! 🎣"
        else: # case_rare
            if r < 0.4:
                gain = random.randint(5000, 20000)
                ud["wallet"] += gain
                msg = f"Ты открыл редкий кейс и нашёл **{core.fmt(gain)}** 🪙!"
            elif r < 0.8:
                ud["items"].append("factory") if "factory" not in ud["items"] else None
                msg = f"ВАУ! Документы на **Завод**! 🏭"
            else:
                col_item = "demon_sword"
                if col_item not in ud["items"]:
                    ud["items"].append(col_item)
                    msg = f"✨ **ЭПИЧЕСКАЯ НАХОДКА!** Внутри лежал **Демонический меч**! 🟥"
                else:
                    ud["wallet"] += 15000
                    msg = f"Там лежал Демонический меч, но у тебя он уже есть. Скупщик дал за него 15000 🪙."
                    
        core.save_user(uid, ud)
        await inter.response.send_message(embed=discord.Embed(title="📦 Открытие кейса", description=msg, color=discord.Color.purple()))

    # ---------- /stocks ----------
    stocks = app_commands.Group(name="stocks", description="📈 Биржа")

    @stocks.command(name="market", description="Посмотреть цены на бирже")
    async def stocks_market(self, inter: discord.Interaction):
        st = core.get_stocks()
        e = discord.Embed(title="📈 Биржа чирукойнов", description="Покупай дёшево, продавай дорого! Цены меняются каждый час.", color=discord.Color.blue())
        for sn, price in st.items():
            e.add_field(name=f"📊 {sn}", value=f"Цена: **{core.fmt(price)}** 🪙", inline=True)
        await inter.response.send_message(embed=e)

    @stocks.command(name="buy", description="Купить акции")
    @app_commands.describe(stock="Название (например, IT_CORP)", amount="Количество")
    @app_commands.choices(stock=[
        app_commands.Choice(name="IT_CORP", value="IT_CORP"),
        app_commands.Choice(name="GOLD_INC", value="GOLD_INC"),
        app_commands.Choice(name="FISH_CO", value="FISH_CO"),
    ])
    async def stocks_buy(self, inter: discord.Interaction, stock: app_commands.Choice[str], amount: int):
        uid = str(inter.user.id)
        if amount <= 0: return await inter.response.send_message("❌ Больше нуля!", ephemeral=True)
        st = core.get_stocks()
        price = st[stock.value]
        cost = price * amount
        ud = core.get_user(uid)
        if ud["wallet"] < cost:
            return await inter.response.send_message(f"❌ Не хватает денег! Нужно {core.fmt(cost)} 🪙", ephemeral=True)
            
        ud["wallet"] -= cost
        ud["stocks"][stock.value] = ud.get("stocks", {}).get(stock.value, 0) + amount
        core.save_user(uid, ud)
        
        await inter.response.send_message(embed=discord.Embed(title="📈 Покупка акций", description=f"Ты купил **{amount}** акций {stock.value} за **{core.fmt(cost)}** 🪙!", color=discord.Color.green()))

    @stocks.command(name="sell", description="Продать акции")
    @app_commands.describe(stock="Название (например, IT_CORP)", amount="Количество")
    @app_commands.choices(stock=[
        app_commands.Choice(name="IT_CORP", value="IT_CORP"),
        app_commands.Choice(name="GOLD_INC", value="GOLD_INC"),
        app_commands.Choice(name="FISH_CO", value="FISH_CO"),
    ])
    async def stocks_sell(self, inter: discord.Interaction, stock: app_commands.Choice[str], amount: int):
        uid = str(inter.user.id)
        if amount <= 0: return await inter.response.send_message("❌ Больше нуля!", ephemeral=True)
        ud = core.get_user(uid)
        owned = ud.get("stocks", {}).get(stock.value, 0)
        
        if owned < amount:
            return await inter.response.send_message(f"❌ У тебя нет столько акций! (У тебя: {owned})", ephemeral=True)
            
        st = core.get_stocks()
        price = st[stock.value]
        revenue = price * amount
        
        ud["stocks"][stock.value] -= amount
        ud["wallet"] += revenue
        core.save_user(uid, ud)
        
        await inter.response.send_message(embed=discord.Embed(title="📉 Продажа акций", description=f"Ты продал **{amount}** акций {stock.value} за **{core.fmt(revenue)}** 🪙!", color=discord.Color.orange()))


async def setup(bot):
    await bot.add_cog(Activities(bot))