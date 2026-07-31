"""cogs/games.py — мини-игры: блэкджек, слоты, рулетка, кубики, угадай число, КНБ."""

import discord
import random
import time
from discord import app_commands
from discord.ext import commands
import core


async def reply(inter, embed, new=None):
    if new:
        embed.add_field(name="🎯 Достижение разблокировано!", value=core.ach_text(new), inline=False)
    await inter.followup.send(embed=embed) if inter.response.is_done() else await inter.response.send_message(embed=embed)


def settle(uid, bet, won, mult):
    """Обработка результата ставки: статистика, выигрыш, серия побед, достижения."""
    ud = core.get_user(uid)
    s = ud["stats"]
    s["games_played"] = s.get("games_played", 0) + 1
    s["gambled"] = s.get("gambled", 0) + bet
    payout = 0
    if won:
        payout = int(bet * mult)
        ud["wallet"] += payout
        ud["total_earned"] += max(0, payout - bet)
        s["games_won"] = s.get("games_won", 0) + 1
        s["streak"] = s.get("streak", 0) + 1
        s["max_streak"] = max(s.get("max_streak", 0), s["streak"])
        s["biggest_win"] = max(s.get("biggest_win", 0), payout - bet)
    else:
        s["streak"] = 0
    new = core.check_achievements(uid, ud)
    core.save_user(uid, ud)
    return ud, new, payout


# ======================== БЛЭКДЖЕК ========================
CARD_VALUES = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
               "10": 10, "В": 10, "Д": 10, "К": 10, "Т": 11}
SUITS = ["♠️", "♥️", "♦️", "♣️"]
NAMES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "В", "Д", "К", "Т"]


def make_deck():
    d = [{"n": n, "s": s, "v": CARD_VALUES[n]} for s in SUITS for n in NAMES]
    random.shuffle(d)
    return d


def cstr(c):
    return f"`{c['n']}{c['s']}`"


def hstr(h):
    return " ".join(cstr(c) for c in h)


def hval(h):
    v = sum(c["v"] for c in h)
    a = sum(1 for c in h if c["n"] == "Т")
    while v > 21 and a > 0:
        v -= 10
        a -= 1
    return v


class BlackjackView(discord.ui.View):
    def __init__(self, uid, bet, deck, ph, dh):
        super().__init__(timeout=120)
        self.uid, self.bet, self.deck = uid, bet, deck
        self.player, self.dealer = ph, dh
        self.over = False

    def embed(self, result=None):
        pv, dv = hval(self.player), hval(self.dealer)
        color = discord.Color.gold()
        if result:
            color = discord.Color.green() if "выиграл" in result or "побед" in result or "БЛЭКДЖЕК" in result else (
                discord.Color.red() if "проиграл" in result else discord.Color.greyple())
        e = discord.Embed(title=f"🃏 Блэкджек — ставка {core.fmt(self.bet)} {core.CURRENCY}", color=color)
        if self.over:
            e.add_field(name=f"🤖 Дилер ({dv})", value=hstr(self.dealer), inline=False)
        else:
            e.add_field(name="🤖 Дилер (?)", value=f"{cstr(self.dealer[0])} `??`", inline=False)
        e.add_field(name=f"🧑 Ты ({pv})", value=hstr(self.player), inline=False)
        if result:
            e.add_field(name="📊 Результат", value=result, inline=False)
        return e

    async def finish(self, inter, text, state):
        # state: "win" / "lose" / "push" / "bj" / "surrender"
        self.over = True
        uid = self.uid
        if state in ("win", "bj"):
            core.progress_quest(uid, "bj_win")
        
        if state == "bj":
            ud, new, _ = settle(uid, self.bet, True, 2.5)
            text += f"\n💰 Выплата x2.5 → +{core.fmt(int(self.bet * 2.5) - self.bet)} {core.CURRENCY}"
        elif state == "win":
            ud, new, _ = settle(uid, self.bet, True, 2)
            text += f"\n💰 +{core.fmt(self.bet)} {core.CURRENCY}"
        elif state == "push":
            ud = core.get_user(uid)
            ud["wallet"] += self.bet
            ud["stats"]["games_played"] = ud["stats"].get("games_played", 0) + 1
            ud["stats"]["gambled"] = ud["stats"].get("gambled", 0) + self.bet
            new = core.check_achievements(uid, ud)
            core.save_user(uid, ud)
            text += "\n🤝 Возврат ставки"
        elif state == "surrender":
            ud = core.get_user(uid)
            refund = self.bet // 2
            ud["wallet"] += refund
            ud["stats"]["games_played"] = ud["stats"].get("games_played", 0) + 1
            ud["stats"]["gambled"] = ud["stats"].get("gambled", 0) + self.bet
            ud["stats"]["streak"] = 0
            new = core.check_achievements(uid, ud)
            core.save_user(uid, ud)
            text += f"\n🏳️ Возврат половины: {core.fmt(refund)} {core.CURRENCY}"
        else:  # lose
            ud, new, _ = settle(uid, self.bet, False, 0)
            text += f"\n💔 -{core.fmt(self.bet)} {core.CURRENCY}"
        for c in self.children:
            c.disabled = True
        emb = self.embed(text)
        emb.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await inter.response.edit_message(embed=emb, view=self)
        if new:
            await inter.followup.send(embed=discord.Embed(title="🎯 Достижение!", description=core.ach_text(new), color=discord.Color.gold()))
        self.stop()

    @discord.ui.button(label="🂠 Ещё", style=discord.ButtonStyle.primary)
    async def hit(self, inter, btn):
        if str(inter.user.id) != self.uid:
            return await inter.response.send_message("Не твоя игра!", ephemeral=True)
        self.player.append(self.deck.pop())
        if hval(self.player) > 21:
            await self.finish(inter, "💥 Перебор! Ты проиграл!", "lose")
        elif hval(self.player) == 21:
            await self.stand(inter, btn)
        else:
            await inter.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="✋ Хватит", style=discord.ButtonStyle.secondary)
    async def stand(self, inter, btn):
        if str(inter.user.id) != self.uid:
            return await inter.response.send_message("Не твоя игра!", ephemeral=True)
        while hval(self.dealer) < 17:
            self.dealer.append(self.deck.pop())
        pv, dv = hval(self.player), hval(self.dealer)
        if dv > 21:
            await self.finish(inter, "🎉 Дилер перебрал! Ты выиграл!", "win")
        elif pv > dv:
            await self.finish(inter, "🎉 Ты выиграл!", "win")
        elif pv < dv:
            await self.finish(inter, "😞 Ты проиграл!", "lose")
        else:
            await self.finish(inter, "🤝 Ничья!", "push")

    @discord.ui.button(label="🏳️ Сдаться", style=discord.ButtonStyle.danger)
    async def surrender(self, inter, btn):
        if str(inter.user.id) != self.uid:
            return await inter.response.send_message("Не твоя игра!", ephemeral=True)
        await self.finish(inter, "🏳️ Ты сдался!", "surrender")


# ======================== КАМЕНЬ-НОЖНИЦЫ-БУМАГА ========================
class RpsView(discord.ui.View):
    def __init__(self, uid, bet):
        super().__init__(timeout=60)
        self.uid, self.bet = uid, bet

    async def resolve(self, inter, player):
        bot = random.choice(["🗿", "✂️", "📄"])
        beats = {"🗿": "✂️", "✂️": "📄", "📄": "🗿"}
        if bot == player:
            ud = core.get_user(self.uid)
            ud["wallet"] += self.bet
            ud["stats"]["games_played"] = ud["stats"].get("games_played", 0) + 1
            ud["stats"]["gambled"] = ud["stats"].get("gambled", 0) + self.bet
            new = core.check_achievements(self.uid, ud)
            core.save_user(self.uid, ud)
            txt, color = f"Ничья! Бот: {bot}. Возврат ставки.", discord.Color.greyple()
            emb = discord.Embed(title="✊ Камень-Ножницы-Бумага", description=txt, color=color)
        elif beats[player] == bot:
            ud, new, _ = settle(self.uid, self.bet, True, 2)
            txt, color = f"Ты: {player} | Бот: {bot}\n🎉 Победа! +{core.fmt(self.bet)} {core.CURRENCY}", discord.Color.green()
            emb = discord.Embed(title="✊ Камень-Ножницы-Бумага", description=txt, color=color)
        else:
            ud, new, _ = settle(self.uid, self.bet, False, 0)
            txt, color = f"Ты: {player} | Бот: {bot}\n😞 Поражение! -{core.fmt(self.bet)} {core.CURRENCY}", discord.Color.red()
            emb = discord.Embed(title="✊ Камень-Ножницы-Бумага", description=txt, color=color)
        for c in self.children:
            c.disabled = True
        emb.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await inter.response.edit_message(embed=emb, view=self)
        if new:
            await inter.followup.send(embed=discord.Embed(title="🎯 Достижение!", description=core.ach_text(new), color=discord.Color.gold()))
        self.stop()

    @discord.ui.button(label="🗿 Камень", style=discord.ButtonStyle.primary)
    async def rock(self, inter, btn):
        if str(inter.user.id) != self.uid:
            return await inter.response.send_message("Не твоя игра!", ephemeral=True)
        await self.resolve(inter, "🗿")

    @discord.ui.button(label="✂️ Ножницы", style=discord.ButtonStyle.secondary)
    async def scissors(self, inter, btn):
        if str(inter.user.id) != self.uid:
            return await inter.response.send_message("Не твоя игра!", ephemeral=True)
        await self.resolve(inter, "✂️")

    @discord.ui.button(label="📄 Бумага", style=discord.ButtonStyle.success)
    async def paper(self, inter, btn):
        if str(inter.user.id) != self.uid:
            return await inter.response.send_message("Не твоя игра!", ephemeral=True)
        await self.resolve(inter, "📄")


# ======================== УГАДАЙ ЧИСЛО ========================
class GuessModal(discord.ui.Modal, title="🔢 Угадай число (1–100)"):
    answer = discord.ui.TextInput(label="Твой ответ", placeholder="Число от 1 до 100", min_length=1, max_length=3)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, inter):
        await self.view.guess(inter, self.answer.value)


class GuessView(discord.ui.View):
    def __init__(self, uid, bet):
        super().__init__(timeout=120)
        self.uid, self.bet = uid, bet
        self.target = random.randint(1, 100)
        self.tries = 5

    def emb(self, hint=""):
        left = self.tries
        e = discord.Embed(title="🔢 Угадай число", description=f"Я загадал число **1–100**.\nПопыток осталось: **{left}**\n{hint}", color=discord.Color.blurple())
        e.set_footer(text=f"Ставка: {core.fmt(self.bet)} {core.CURRENCY} • Выигрыш до x6")
        return e

    async def guess(self, inter, raw):
        try:
            num = int(raw)
        except ValueError:
            return await inter.response.send_message("Введи число!", ephemeral=True)
        if str(inter.user.id) != self.uid:
            return await inter.response.send_message("Не твоя игра!", ephemeral=True)
        if num < 1 or num > 100:
            return await inter.response.send_message("Число от 1 до 100!", ephemeral=True)
        self.tries -= 1
        if num == self.target:
            mult = 1 + self.tries  # осталось попыток → больше множитель
            ud, new, payout = settle(self.uid, self.bet, True, mult)
            for c in self.children:
                c.disabled = True
            e = discord.Embed(title="🎉 Верно!", description=f"Число было **{self.target}**!\nВыигрыш x{mult} → +{core.fmt(payout - self.bet)} {core.CURRENCY}", color=discord.Color.green())
            e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
            await inter.response.edit_message(embed=e, view=self)
            if new:
                await inter.followup.send(embed=discord.Embed(title="🎯 Достижение!", description=core.ach_text(new), color=discord.Color.gold()))
            self.stop()
            return
        if self.tries <= 0:
            ud, new, _ = settle(self.uid, self.bet, False, 0)
            for c in self.children:
                c.disabled = True
            e = discord.Embed(title="😞 Не угадал!", description=f"Число было **{self.target}**.\n-{core.fmt(self.bet)} {core.CURRENCY}", color=discord.Color.red())
            e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
            await inter.response.edit_message(embed=e, view=self)
            self.stop()
            return
        hint = "📈 **Моё число больше!**" if num < self.target else "📉 **Моё число меньше!**"
        await inter.response.edit_message(embed=self.emb(hint), view=self)

    @discord.ui.button(label="🔢 Ввести число", style=discord.ButtonStyle.primary)
    async def ask(self, inter, btn):
        if str(inter.user.id) != self.uid:
            return await inter.response.send_message("Не твоя игра!", ephemeral=True)
        await inter.response.send_modal(GuessModal(self))


# ======================== COG ========================
SLOTS = ["🍒", "🍋", "🍊", "🍇", "🔔", "⭐", "💎"]
SLOT_W = [30, 25, 20, 15, 10, 7, 3]


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- /blackjack ----------
    @app_commands.command(name="blackjack", description="🃏 Блэкджек против дилера (до 21)")
    @app_commands.describe(bet="Ставка")
    async def blackjack(self, inter, bet: int):
        uid = str(inter.user.id)
        if bet <= 0:
            return await inter.response.send_message("❌ Ставка больше 0!", ephemeral=True)
        ok, _ = core.spend(uid, bet)
        if not ok:
            return await inter.response.send_message(f"❌ Недостаточно денег! Кошелёк: {core.fmt(core.get_user(uid)['wallet'])} {core.CURRENCY}", ephemeral=True)
        deck = make_deck()
        ph = [deck.pop(), deck.pop()]
        dh = [deck.pop(), deck.pop()]
        ud = core.get_user(uid)
        ud["stats"]["blackjack_played"] = ud["stats"].get("blackjack_played", 0) + 1
        core.save_user(uid, ud)
        view = BlackjackView(uid, bet, deck, ph, dh)
        core.add_xp(uid, 5)
        if hval(ph) == 21:
            await view.finish(inter, "🎰 БЛЭКДЖЕК!", "bj")
            core.progress_quest(uid, "bj_win")
            return
        e = view.embed()
        e.set_footer(text=f"Кошелёк: {core.fmt(core.get_user(uid)['wallet'])} {core.CURRENCY}")
        await inter.response.send_message(embed=e, view=view)

    # ---------- /slots ----------
    @app_commands.command(name="slots", description="🎰 Слот-машина")
    @app_commands.describe(bet="Ставка")
    async def slots(self, inter, bet: int):
        uid = str(inter.user.id)
        if bet <= 0:
            return await inter.response.send_message("❌ Ставка больше 0!", ephemeral=True)
        ok, _ = core.spend(uid, bet)
        if not ok:
            return await inter.response.send_message("❌ Недостаточно денег в кошельке!", ephemeral=True)
        reels = [random.choices(SLOTS, weights=SLOT_W)[0] for _ in range(3)]
        a, b, c = reels
        if a == b == c:
            mult, res = (12, "💎 ДЖЕКПОТ x12!") if a == "💎" else (5, "🎉 Три в ряд x5!")
        elif a == b or b == c or a == c:
            mult, res = 2, "✅ Пара x2!"
        else:
            mult, res = 0, "😞 Мимо!"
        ud, new, payout = settle(uid, bet, mult > 0, mult)
        e = discord.Embed(title="🎰 Слоты", description=f"# {a} | {b} | {c}\n**{res}**",
                          color=discord.Color.green() if mult else discord.Color.red())
        e.add_field(name="💰 Ставка", value=f"{core.fmt(bet)} {core.CURRENCY}")
        e.add_field(name="💵 Выигрыш", value=f"{core.fmt(payout)} {core.CURRENCY}" if mult else "0")
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await reply(inter, e, new)

    # ---------- /coinflip ----------
    @app_commands.command(name="coinflip", description="🪙 Орёл или решка (x2)")
    @app_commands.describe(bet="Ставка", side="Орёл или Решка")
    @app_commands.choices(side=[app_commands.Choice(name="Орёл", value="Орёл"), app_commands.Choice(name="Решка", value="Решка")])
    async def coinflip(self, inter, bet: int, side: app_commands.Choice[str]):
        uid = str(inter.user.id)
        if bet <= 0:
            return await inter.response.send_message("❌ Ставка больше 0!", ephemeral=True)
        ok, _ = core.spend(uid, bet)
        if not ok:
            return await inter.response.send_message("❌ Недостаточно денег!", ephemeral=True)
        result = random.choice(["Орёл", "Решка"])
        won = result == side.value
        ud, new, payout = settle(uid, bet, won, 2)
        e = discord.Embed(title="🪙 Орёл и Решка", color=discord.Color.green() if won else discord.Color.red())
        e.add_field(name="Ты выбрал", value=side.value)
        e.add_field(name="Выпало", value=result)
        e.add_field(name="Итог", value=("🎉 +"+core.fmt(bet)) if won else ("💔 -"+core.fmt(bet)))
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await reply(inter, e, new)

    # ---------- /roulette ----------
    @app_commands.command(name="roulette", description="🎡 Рулетка (красное/чёрное x2, зелёное x14)")
    @app_commands.describe(bet="Ставка", color="Цвет")
    @app_commands.choices(color=[
        app_commands.Choice(name="🔴 Красное", value="red"),
        app_commands.Choice(name="⚫ Чёрное", value="black"),
        app_commands.Choice(name="🟢 Зелёное", value="green"),
    ])
    async def roulette(self, inter, bet: int, color: app_commands.Choice[str]):
        uid = str(inter.user.id)
        if bet <= 0:
            return await inter.response.send_message("❌ Ставка больше 0!", ephemeral=True)
        ok, _ = core.spend(uid, bet)
        if not ok:
            return await inter.response.send_message("❌ Недостаточно денег!", ephemeral=True)
        r = random.random()
        if r < 0.05:
            res = "green"
        elif r < 0.525:
            res = "red"
        else:
            res = "black"
        won = res == color.value
        mult = 14 if color.value == "green" else 2
        ud, new, payout = settle(uid, bet, won, mult)
        names = {"red": "🔴 Красное", "black": "⚫ Чёрное", "green": "🟢 Зелёное"}
        e = discord.Embed(title="🎡 Рулетка", color=discord.Color.green() if won else discord.Color.red())
        e.add_field(name="Твоя ставка", value=names[color.value])
        e.add_field(name="Выпало", value=names[res])
        e.add_field(name="Итог", value=("🎉 +"+core.fmt(payout - bet)) if won else ("💔 -"+core.fmt(bet)))
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await reply(inter, e, new)

    # ---------- /dice ----------
    @app_commands.command(name="dice", description="🎲 Бросок кубика — угадай число 1–6 (x6)")
    @app_commands.describe(bet="Ставка", guess="Число от 1 до 6")
    async def dice(self, inter, bet: int, guess: int):
        uid = str(inter.user.id)
        if bet <= 0:
            return await inter.response.send_message("❌ Ставка больше 0!", ephemeral=True)
        if guess < 1 or guess > 6:
            return await inter.response.send_message("❌ Число от 1 до 6!", ephemeral=True)
        ok, _ = core.spend(uid, bet)
        if not ok:
            return await inter.response.send_message("❌ Недостаточно денег!", ephemeral=True)
        roll = random.randint(1, 6)
        won = roll == guess
        ud, new, payout = settle(uid, bet, won, 6)
        e = discord.Embed(title="🎲 Кубик", description=f"🎲 Выпало: **{roll}**", color=discord.Color.green() if won else discord.Color.red())
        e.add_field(name="Твоя ставка", value=str(guess))
        e.add_field(name="Итог", value=("🎉 +"+core.fmt(payout - bet)) if won else ("💔 -"+core.fmt(bet)))
        e.set_footer(text=f"Кошелёк: {core.fmt(ud['wallet'])} {core.CURRENCY}")
        await reply(inter, e, new)

    # ---------- /guess ----------
    @app_commands.command(name="guess", description="🔢 Угадай число 1–100 за 5 попыток")
    @app_commands.describe(bet="Ставка")
    async def guess(self, inter, bet: int):
        uid = str(inter.user.id)
        if bet <= 0:
            return await inter.response.send_message("❌ Ставка больше 0!", ephemeral=True)
        ok, _ = core.spend(uid, bet)
        if not ok:
            return await inter.response.send_message("❌ Недостаточно денег!", ephemeral=True)
        view = GuessView(uid, bet)
        await inter.response.send_message(embed=view.emb("Нажми кнопку и введи число!"), view=view)

    # ---------- /rps ----------
    @app_commands.command(name="rps", description="✊ Камень-Ножницы-Бумага (x2)")
    @app_commands.describe(bet="Ставка")
    async def rps(self, inter, bet: int):
        uid = str(inter.user.id)
        if bet <= 0:
            return await inter.response.send_message("❌ Ставка больше 0!", ephemeral=True)
        ok, _ = core.spend(uid, bet)
        if not ok:
            return await inter.response.send_message("❌ Недостаточно денег!", ephemeral=True)
        view = RpsView(uid, bet)
        e = discord.Embed(title="✊ Камень-Ножницы-Бумага", description="Выбери свой ход!", color=discord.Color.blurple())
        e.set_footer(text=f"Ставка: {core.fmt(bet)} {core.CURRENCY}")
        await inter.response.send_message(embed=e, view=view)


async def setup(bot):
    await bot.add_cog(Games(bot))
