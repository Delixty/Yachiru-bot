"""cogs/moderation.py — модерация: бан, кик, мут, роли, автороль, приветствие."""

import discord
from datetime import timedelta
from discord import app_commands
from discord.ext import commands
import core


def role_autocomplete(inter: discord.Interaction, current: str):
    if not inter.guild:
        return []
    roles = [r for r in inter.guild.roles if r.name != "@everyone"]
    opts = []
    for r in roles:
        if current.lower() in r.name.lower():
            opts.append(app_commands.Choice(name=r.name, value=str(r.id)))
    return opts[:25]


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- СОБЫТИЕ: новый участник ----------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = core.load_data()

        # Автороль
        role_id = data.get("autorole")
        if role_id:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.add_roles(role, reason="Автороль")
                except Exception:
                    pass

        # Приветствие
        welcome = data.get("welcome")
        if not welcome or not welcome.get("text"):
            return
        ch = member.guild.get_channel(int(welcome.get("channel", 0)))
        if not ch:
            return

        text = welcome["text"].replace("{user}", member.mention).replace("{server}", member.guild.name)
        text = f"{text}\n\n*by delixty*"

        e = discord.Embed(
            title=f"👋 Добро пожаловать, {member.display_name}!",
            description=text,
            color=discord.Color.pink(),
        )
        e.set_thumbnail(url=member.display_avatar.url)

        # Баннер сервера, если есть; иначе баннер пользователя; иначе иконка сервера
        banner_url = None
        if member.guild.banner:
            banner_url = member.guild.banner.url
        else:
            try:
                fetched = await self.bot.fetch_user(member.id)
                if fetched.banner:
                    banner_url = fetched.banner.url
            except Exception:
                pass
        if not banner_url and member.guild.icon:
            banner_url = member.guild.icon.url
        if banner_url:
            e.set_image(url=banner_url)

        e.add_field(name="👥 Участник №", value=str(member.guild.member_count), inline=True)
        e.add_field(name="📅 Аккаунт создан", value=discord.utils.format_dt(member.created_at, "R"), inline=True)
        e.set_footer(text=f"{member.guild.name} • by delixty",
                     icon_url=member.guild.icon.url if member.guild.icon else None)

        try:
            await ch.send(content=member.mention, embed=e)
        except Exception:
            pass

    # ---------- СОБЫТИЕ: бот зашёл на сервер ----------
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Когда бот заходит на новый сервер — здоровается баннером во всех участниках."""
        # Ищем подходящий канал: system_channel → первый доступный текстовый
        target = guild.system_channel
        if not target or not target.permissions_for(guild.me).send_messages:
            for c in guild.text_channels:
                if c.permissions_for(guild.me).send_messages:
                    target = c
                    break
        if not target:
            return

        e = discord.Embed(
            title="🌸 Yachiru прибыла!",
            description=(
                f"Всем привет, **{guild.name}**! 👋\n\n"
                "Я — **Yachiru**, ваш универсальный бот с экономикой (**чирукойны** 🪙),\n"
                "мини-играми, магазином, модерацией и RP-командами.\n\n"
                "📖 Начните с `/help` — там весь список команд.\n"
                "🎉 Не забудьте `/seteventchannel` для дождя денег и `/welcome set` для приветствий.\n\n"
                "*by delixty*"
            ),
            color=discord.Color.pink(),
        )
        # Баннер: сервера → иконка сервера → аватар бота
        if guild.banner:
            e.set_image(url=guild.banner.url)
        elif guild.icon:
            e.set_image(url=guild.icon.url)
        else:
            e.set_image(url=self.bot.user.display_avatar.url)
        e.set_thumbnail(url=self.bot.user.display_avatar.url)
        e.set_footer(text=f"Yachiru • Валюта: чирукойны 🪙 • by delixty")

        try:
            await target.send(embed=e)
        except Exception:
            pass

    # ---------- /ban ----------
    @app_commands.command(name="ban", description="🔨 [МОД] Забанить пользователя")
    @app_commands.describe(user="Кого забанить", reason="Причина")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, inter: discord.Interaction, user: discord.Member, reason: str = "Не указана"):
        if not inter.user.guild_permissions.ban_members:
            return await inter.response.send_message("❌ Нет прав `Забанить участников`!", ephemeral=True)
        if user.top_role >= inter.user.top_role and inter.user != inter.guild.owner:
            return await inter.response.send_message("❌ Ты не можешь забанить этого участника (роль выше или равна твоей)!", ephemeral=True)
        try:
            await user.ban(reason=f"{inter.user} — {reason}")
        except discord.Forbidden:
            return await inter.response.send_message("❌ У бота недостаточно прав для бана!", ephemeral=True)
        e = discord.Embed(title="🔨 Бан", color=discord.Color.red())
        e.add_field(name="Участник", value=user.mention)
        e.add_field(name="Причина", value=reason)
        e.add_field(name="Модератор", value=inter.user.mention)
        await inter.response.send_message(embed=e)

    # ---------- /kick ----------
    @app_commands.command(name="kick", description="👢 [МОД] Выгнать пользователя")
    @app_commands.describe(user="Кого выгнать", reason="Причина")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, inter: discord.Interaction, user: discord.Member, reason: str = "Не указана"):
        if not inter.user.guild_permissions.kick_members:
            return await inter.response.send_message("❌ Нет прав `Выгнать участников`!", ephemeral=True)
        if user.top_role >= inter.user.top_role and inter.user != inter.guild.owner:
            return await inter.response.send_message("❌ Ты не можешь выгнать этого участника (роль выше или равна твоей)!", ephemeral=True)
        try:
            await user.kick(reason=f"{inter.user} — {reason}")
        except discord.Forbidden:
            return await inter.response.send_message("❌ У бота недостаточно прав для кика!", ephemeral=True)
        e = discord.Embed(title="👢 Кик", color=discord.Color.orange())
        e.add_field(name="Участник", value=user.mention)
        e.add_field(name="Причина", value=reason)
        e.add_field(name="Модератор", value=inter.user.mention)
        await inter.response.send_message(embed=e)

    # ---------- /mute ----------
    @app_commands.command(name="mute", description="🔇 [МОД] Замутить пользователя (таймаут)")
    @app_commands.describe(user="Кого замутить", minutes="Длительность в минутах (макс. 40320 = 28 дней)", reason="Причина")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, inter: discord.Interaction, user: discord.Member, minutes: int, reason: str = "Не указана"):
        if not inter.user.guild_permissions.moderate_members:
            return await inter.response.send_message("❌ Нет прав `Управлять таймаутами`!", ephemeral=True)
        if minutes <= 0:
            return await inter.response.send_message("❌ Время должно быть больше 0!", ephemeral=True)
        if minutes > 40320:
            return await inter.response.send_message("❌ Максимум 40320 минут (28 дней)!", ephemeral=True)
        if user.top_role >= inter.user.top_role and inter.user != inter.guild.owner:
            return await inter.response.send_message("❌ Ты не можешь замутить этого участника (роль выше или равна твоей)!", ephemeral=True)
        try:
            await user.timeout(timedelta(minutes=minutes), reason=f"{inter.user} — {reason}")
        except discord.Forbidden:
            return await inter.response.send_message("❌ У бота недостаточно прав для таймаута!", ephemeral=True)
        e = discord.Embed(title="🔇 Мут", color=discord.Color.dark_blue())
        e.add_field(name="Участник", value=user.mention)
        e.add_field(name="Длительность", value=f"**{core.cd(minutes * 60)}**")
        e.add_field(name="Причина", value=reason)
        await inter.response.send_message(embed=e)

    # ---------- /unmute ----------
    @app_commands.command(name="unmute", description="🔊 [МОД] Снять мут с пользователя")
    @app_commands.describe(user="С кого снять мут")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, inter: discord.Interaction, user: discord.Member):
        if not inter.user.guild_permissions.moderate_members:
            return await inter.response.send_message("❌ Нет прав `Управлять таймаутами`!", ephemeral=True)
        try:
            await user.timeout(None)
        except discord.Forbidden:
            return await inter.response.send_message("❌ Не удалось снять мут!", ephemeral=True)
        await inter.response.send_message(embed=discord.Embed(title="🔊 Мут снят", description=f"С **{user.mention}** снят таймаут.", color=discord.Color.green()))

    # ---------- /role ----------
    @app_commands.command(name="role", description="🎭 [МОД] Выдать роль пользователю")
    @app_commands.describe(user="Кому выдать", role="Какую роль")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.autocomplete(role=role_autocomplete)
    async def role(self, inter: discord.Interaction, user: discord.Member, role: str):
        if not inter.user.guild_permissions.manage_roles:
            return await inter.response.send_message("❌ Нет прав `Управлять ролями`!", ephemeral=True)
        r = inter.guild.get_role(int(role))
        if not r:
            return await inter.response.send_message("❌ Роль не найдена!", ephemeral=True)
        if r >= inter.guild.me.top_role:
            return await inter.response.send_message("❌ Я не могу выдать эту роль (она выше моей)!", ephemeral=True)
        try:
            await user.add_roles(r, reason=f"{inter.user}")
        except discord.Forbidden:
            return await inter.response.send_message("❌ Не удалось выдать роль!", ephemeral=True)
        await inter.response.send_message(embed=discord.Embed(title="🎭 Роль выдана", description=f"**{user.mention}** получил роль **{r.mention}**", color=discord.Color.purple()))

    # ---------- /autorole ----------
    autorole = app_commands.Group(name="autorole", description="🎖️ Автоматическая роль для новых участников")

    @autorole.command(name="set", description="🎖️ [АДМИН] Установить автороль")
    @app_commands.describe(role="Какую роль выдавать новичкам")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(role=role_autocomplete)
    async def autorole_set(self, inter: discord.Interaction, role: str):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        r = inter.guild.get_role(int(role))
        if not r:
            return await inter.response.send_message("❌ Роль не найдена!", ephemeral=True)
        if r >= inter.guild.me.top_role:
            return await inter.response.send_message("❌ Эта роль выше моей, я не смогу её выдавать!", ephemeral=True)
        data = core.load_data()
        data["autorole"] = str(r.id)
        core.save_data(data)
        await inter.response.send_message(embed=discord.Embed(title="🎖️ Автороль установлена", description=f"Новые участники будут получать **{r.mention}**", color=discord.Color.green()))

    @autorole.command(name="remove", description="🎖️ [АДМИН] Убрать автороль")
    @app_commands.default_permissions(administrator=True)
    async def autorole_remove(self, inter: discord.Interaction):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        data = core.load_data()
        data.pop("autorole", None)
        core.save_data(data)
        await inter.response.send_message(embed=discord.Embed(title="🎖️ Автороль убрана", color=discord.Color.orange()))

    # ---------- /welcome ----------
    welcome = app_commands.Group(name="welcome", description="👋 Приветствие для новых участников")

    @welcome.command(name="set", description="👋 [АДМИН] Установить приветствие для новых участников")
    @app_commands.describe(channel="Канал для приветствий", text="Текст. Используй {user} и {server}")
    @app_commands.default_permissions(administrator=True)
    async def welcome_set(self, inter: discord.Interaction, channel: discord.TextChannel, text: str):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        if len(text) > 900:
            return await inter.response.send_message("❌ Текст слишком длинный (макс. 900 символов)!", ephemeral=True)
        data = core.load_data()
        data["welcome"] = {"channel": channel.id, "text": text}
        core.save_data(data)
        preview = text.replace("{user}", "Новичок").replace("{server}", inter.guild.name)
        e = discord.Embed(title="👋 Приветствие установлено", color=discord.Color.green())
        e.add_field(name="Канал", value=channel.mention, inline=True)
        e.add_field(name="Текст (превью)", value=preview, inline=False)
        e.set_footer(text="Плейсхолдеры: {user} — упоминание, {server} — имя сервера")
        await inter.response.send_message(embed=e)

    @welcome.command(name="delete", description="👋 [АДМИН] Удалить приветствие")
    @app_commands.default_permissions(administrator=True)
    async def welcome_delete(self, inter: discord.Interaction):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        data = core.load_data()
        data.pop("welcome", None)
        core.save_data(data)
        await inter.response.send_message(embed=discord.Embed(title="👋 Приветствие удалено", color=discord.Color.orange()))

    @welcome.command(name="preview", description="👋 [АДМИН] Посмотреть текущее приветствие")
    @app_commands.default_permissions(administrator=True)
    async def welcome_preview(self, inter: discord.Interaction):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        data = core.load_data()
        w = data.get("welcome")
        if not w or not w.get("text"):
            return await inter.response.send_message("📭 Приветствие не установлено. Напиши `/welcome set`!", ephemeral=True)
        await inter.response.send_message(embed=discord.Embed(title="👋 Текущее приветствие", description=w["text"], color=discord.Color.blurple()))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
