"""cogs/social.py — взаимодействие: ограбление, подарок, обмен, дуэль."""

import discord
import time
import random
from discord import app_commands
from discord.ext import commands
import core


def owned_choices(ud, current):
    opts = []
    for iid in ud["items"]:
        it = core.ALL_ITEMS.get(iid)
        if it and (current.lower() in it["name"].lower() or current.lower() in iid):
            opts.append(app_commands.Choice(name=it["name"][:100], value=iid))
    for iid, cnt in ud.get("consumables", {}).items():
        it = core.ALL_ITEMS.get(iid)
        if it and cnt > 0 and (current.lower() in it["name"].lower() or current.lower() in iid):
            opts.append(app_commands.Choice(name=f"{it['name']} (x{cnt})"[:100], value=iid))
    return opts[:25]


class TradeView(discord.ui.View):
    def __init__(self, proposer, target, offer, want):
        super().__init__(timeout=120)
        self.proposer, self.target = proposer, target
        self.offer, self.want = offer, want

    async def accept(self, inter):
        if str(inter.user.id) != self.target:
            return await inter.response.send_message("Это предложение не тебе!", ephemeral=True)
        pd = core.get_user(self.proposer)
        td = core.get_user(self.target)
        of = core.ALL_ITEMS.get(self.offer)
        wf = core.ALL_ITEMS.get(self.want)
        # проверка владения
        def owns(ud, iid, typ):
            return (iid in ud["items"]) if typ != "consumable" else (ud["consumables"].get(iid, 0) > 0)
        if not owns(pd, self.offer, of["type"]) or not owns(td, self.want, wf["type"]):
            for c in self.children:
                c.disabled = True
            return await inter.response.edit_message(content="❌ Обмен невозможен — кто-то уже лишился предмета.", view=self)
        # обмен
        def take(ud, iid, typ):
            if typ == "consumable":
                ud["consumables"][iid] -= 1
            else:
                ud["items"].remove(iid)
        def give(ud, iid, typ):
            if typ == "consumable":
                ud["consumables"][iid] = ud["consumables"].get(iid, 0) + 1
            else:
                ud["items"].append(iid)
        take(pd, self.offer, of["type"])
        give(td, self.offer, of["type"])
        take(td, self.want, wf["type"])
        give(pd, self.want, wf["type"])
        core.save_user(self.proposer, pd)
        core.save_user(self.target, td)
        for c in self.children:
            c.disabled = True
        await inter.response.edit_message(content=f"🤝 Обмен совершён! **{of['name']}** ⇄ **{wf['name']}**", view=self)
        self.stop()

    @discord.ui.button(label="✅ Принять обмен", style=discord.ButtonStyle.success)
    async def yes(self, inter, btn):
        await self.accept(inter)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def no(self, inter, btn):
        if str(inter.user.id) != self.target:
            return await inter.response.send_message("Это не тебе!", ephemeral=True)
        for c in self.children:
            c.disabled = True
        await inter.response.edit_message(content="❌ Обмен отклонён.", view=self)
        self.stop()


class DuelView(discord.ui.View):
    def __init__(self, proposer, target, amount):
        super().__init__(timeout=120)
        self.proposer, self.target, self.amount = proposer, target, amount

    async def accept(self, inter):
        if str(inter.user.id) != self.target:
            return await inter.response.send_message("Этот вызов не тебе!", ephemeral=True)
        pd = core.get_user(self.proposer)
        td = core.get_user(self.target)
        if pd["wallet"] < self.amount or td["wallet"] < self.amount:
            for c in self.children:
                c.disabled = True
            return await inter.response.edit_message(content="❌ У кого-то недостаточно денег!", view=self)
        pd["wallet"] -= self.amount
        td["wallet"] -= self.amount
        winner_id = random.choice([self.proposer, self.target])
        pot = self.amount * 2
        wd = core.get_user(winner_id)
        wd["wallet"] += pot
        wd["stats"]["duels"] = wd["stats"].get("duels", 0) + 1
        core.save_user(self.proposer, pd)
        core.save_user(self.target, td)
        core.save_user(winner_id, wd)
        for c in self.children:
            c.disabled = True
        await inter.response.edit_message(content=f"⚔️ Дуэль окончена! Победитель забирает **{core.fmt(pot)}** {core.CURRENCY}!", view=self, embed=None)
        self.stop()

    @discord.ui.button(label="⚔️ Принять дуэль", style=discord.ButtonStyle.danger)
    async def yes(self, inter, btn):
        await self.accept(inter)

    @discord.ui.button(label="❌ Отказаться", style=discord.ButtonStyle.secondary)
    async def no(self, inter, btn):
        if str(inter.user.id) != self.target:
            return await inter.response.send_message("Это не тебе!", ephemeral=True)
        for c in self.children:
            c.disabled = True
        await inter.response.edit_message(content="❌ Дуэль отклонена.", view=self)
        self.stop()


class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- /rob ----------
    @app_commands.command(name="rob", description="🦹 Ограбить игрока (с шансом провала)")
    @app_commands.describe(user="Кого ограбить")
    async def rob(self, inter: discord.Interaction, user: discord.Member):
        sid, rid = str(inter.user.id), str(user.id)
        if sid == rid:
            return await inter.response.send_message("❌ Нельзя грабить себя!", ephemeral=True)
        if user.bot:
            return await inter.response.send_message("❌ Ботов грабить нельзя!", ephemeral=True)
        sd = core.get_user(sid)
        now = time.time()
        if now - sd.get("last_rob", 0) < core.COOLDOWNS["rob"]:
            return await inter.response.send_message(f"⏳ Ты в бегах! Подожди **{core.cd(core.COOLDOWNS['rob'] - (now - sd['last_rob']))}**", ephemeral=True)
        rd = core.get_user(rid)
        if rd["wallet"] <= 0:
            return await inter.response.send_message("💸 У жертвы пустой кошелёк!", ephemeral=True)
        sd["last_rob"] = now
        if rd.get("shield_until", 0) > now:
            fine = min(sd["wallet"], random.randint(50, 300))
            sd["wallet"] -= fine
            core.save_user(sid, sd)
            return await inter.response.send_message(embed=discord.Embed(title="🛡️ Провал!", description=f"У **{user.display_name}** щит! Ты попался и заплатил штраф **{core.fmt(fine)}** {core.CURRENCY}", color=discord.Color.red()))
        if random.random() < 0.45:
            stolen = min(rd["wallet"], int(rd["wallet"] * random.uniform(0.10, 0.40)))
            sd["wallet"] += stolen
            sd["total_earned"] += stolen
            rd["wallet"] -= stolen
            sd["stats"]["robs"] = sd["stats"].get("robs", 0) + 1
            core.save_user(sid, sd)
            core.save_user(rid, rd)
            e = discord.Embed(title="🦹 Ограбление удалось!", description=f"Ты украл **{core.fmt(stolen)}** {core.CURRENCY} у {user.mention}!", color=discord.Color.green())
        else:
            fine = min(sd["wallet"], random.randint(50, 250))
            sd["wallet"] -= fine
            core.save_user(sid, sd)
            e = discord.Embed(title="🚔 Провал!", description=f"Тебя поймали и оштрафовали на **{core.fmt(fine)}** {core.CURRENCY}", color=discord.Color.red())
        e.set_footer(text=f"Кошелёк: {core.fmt(sd['wallet'])} {core.CURRENCY}")
        await inter.response.send_message(embed=e)

    # ---------- /gift ----------
    @app_commands.command(name="gift", description="🎁 Подарить предмет игроку")
    @app_commands.describe(user="Кому подарить", item="Какой предмет")
    @app_commands.autocomplete(item=lambda inter, c: owned_choices(core.get_user(str(inter.user.id)), c))
    async def gift(self, inter: discord.Interaction, user: discord.Member, item: str):
        sid, rid = str(inter.user.id), str(user.id)
        if sid == rid:
            return await inter.response.send_message("❌ Нельзя дарить себе!", ephemeral=True)
        if user.bot:
            return await inter.response.send_message("❌ Нельзя дарить боту!", ephemeral=True)
        it = core.ALL_ITEMS.get(item)
        if not it:
            return await inter.response.send_message("❌ Неверный предмет!", ephemeral=True)
        sd = core.get_user(sid)
        rd = core.get_user(rid)
        if it["type"] == "consumable":
            if sd["consumables"].get(item, 0) <= 0:
                return await inter.response.send_message("❌ У тебя нет такого предмета!", ephemeral=True)
            sd["consumables"][item] -= 1
            rd["consumables"][item] = rd["consumables"].get(item, 0) + 1
        else:
            if item not in sd["items"]:
                return await inter.response.send_message("❌ У тебя нет такого предмета!", ephemeral=True)
            sd["items"].remove(item)
            rd["items"].append(item)
        core.save_user(sid, sd)
        core.save_user(rid, rd)
        await inter.response.send_message(embed=discord.Embed(title="🎁 Подарок!", description=f"**{inter.user.display_name}** подарил **{it['name']}** игроку {user.mention}!", color=discord.Color.pink()))

    # ---------- /trade ----------
    @app_commands.command(name="trade", description="🤝 Предложить обмен предметами")
    @app_commands.describe(user="С кем обмен", offer="Что ты даёшь", want="Что хочешь получить")
    @app_commands.autocomplete(offer=lambda inter, c: owned_choices(core.get_user(str(inter.user.id)), c))
    @app_commands.autocomplete(want=lambda inter, c: owned_choices(core.get_user(str(getattr(inter.namespace, "user", None).id)) if getattr(inter.namespace, "user", None) else {}, c))
    async def trade(self, inter: discord.Interaction, user: discord.Member, offer: str, want: str):
        sid, rid = str(inter.user.id), str(user.id)
        of = core.ALL_ITEMS.get(offer)
        wf = core.ALL_ITEMS.get(want)
        if not of or not wf:
            return await inter.response.send_message("❌ Неверный предмет!", ephemeral=True)
        sd = core.get_user(sid)
        owns_of = (offer in sd["items"]) if of["type"] != "consumable" else (sd["consumables"].get(offer, 0) > 0)
        if not owns_of:
            return await inter.response.send_message("❌ У тебя нет этого предмета!", ephemeral=True)
        view = TradeView(sid, rid, offer, want)
        e = discord.Embed(title="🤝 Предложение обмена", color=discord.Color.blurple())
        e.add_field(name=inter.user.display_name + " отдаёт", value=of["name"])
        e.add_field(name="Хочет получить", value=wf["name"])
        e.set_footer(text=f"{user.display_name}, нажми «Принять» для обмена")
        await inter.response.send_message(content=user.mention, embed=e, view=view)

    # ---------- /duel ----------
    @app_commands.command(name="duel", description="⚔️ Дуэль на деньги")
    @app_commands.describe(user="Кого вызвать", amount="Ставка с каждой стороны")
    async def duel(self, inter: discord.Interaction, user: discord.Member, amount: int):
        sid, rid = str(inter.user.id), str(user.id)
        if sid == rid:
            return await inter.response.send_message("❌ Нельзя вызвать себя!", ephemeral=True)
        if user.bot:
            return await inter.response.send_message("❌ Нельзя вызвать бота!", ephemeral=True)
        if amount <= 0:
            return await inter.response.send_message("❌ Ставка больше 0!", ephemeral=True)
        if core.get_user(sid)["wallet"] < amount:
            return await inter.response.send_message("❌ У тебя недостаточно денег!", ephemeral=True)
        view = DuelView(sid, rid, amount)
        e = discord.Embed(title="⚔️ Вызов на дуэль!", description=f"**{inter.user.display_name}** вызывает **{user.display_name}** на дуэль!\nСтавка: **{core.fmt(amount)}** {core.CURRENCY} с каждого. Победитель забирает всё!", color=discord.Color.red())
        e.set_footer(text="Прими вызов кнопкой ниже")
        await inter.response.send_message(content=user.mention, embed=e, view=view)


async def setup(bot):
    await bot.add_cog(Social(bot))
