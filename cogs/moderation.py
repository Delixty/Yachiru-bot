"""cogs/moderation.py — модерация: бан, кик, мут, роли, автороль, приветствие."""

import discord
from datetime import timedelta
from discord import app_commands
from discord.ext import commands
import core

YACHIRU_BANNER_URL = "https://images.unsplash.com/photo-1519608487953-e999c86e7450?auto=format&fit=crop&w=1600&q=85"


def guild_settings(data: dict, guild_id: int, create: bool = True):
    """Возвращает настройки конкретного сервера, чтобы они не смешивались между guild."""
    settings = data.setdefault("guild_settings", {}) if create else data.get("guild_settings", {})
    key = str(guild_id)
    if create:
        return settings.setdefault(key, {})
    return settings.get(key, {})


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
    async def on_member_join(self, member):
        data = core.load_data()
        settings = guild_settings(data, member.guild.id, create=False)

        # Автороль
        role_id = settings.get("autorole")
        if role_id:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.add_roles(role, reason="Автороль")
                except Exception:
                    pass

        # Приветствие
        welcome = settings.get("welcome")
        if welcome and welcome.get("text"):
            ch = member.guild.get_channel(int(welcome.get("channel", 0)))
            if ch:
                try:
                    text = welcome["text"]
                    text = text.replace("{user}", member.mention).replace("{server}", member.guild.name)
                    await ch.send(text)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Показывает приветственный баннер, когда Yachiru добавляют на сервер."""
        me = guild.me or guild.get_member(self.bot.user.id)
        channel = guild.system_channel
        if channel is None or not me or not channel.permissions_for(me).send_messages:
            channel = next(
                (ch for ch in guild.text_channels if me and ch.permissions_for(me).send_messages),
                None,
            )
        if channel is None:
            return

        embed = discord.Embed(
            title="👋 Привет, я Yachiru!",
            description=(
                "Спасибо за приглашение! Я помогу с экономикой, играми, "
                "модерацией и RP-командами.\n\n"
                "Начни с `/help`, а для приветствий используй `/welcome set`.\n\n"
                "(by delixty)"
            ),
            color=discord.Color.pink(),
        )
        embed.set_image(url=YACHIRU_BANNER_URL)
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
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
        guild_settings(data, inter.guild_id)["autorole"] = str(r.id)
        core.save_data(data)
        await inter.response.send_message(embed=discord.Embed(title="🎖️ Автороль установлена", description=f"Новые участники будут получать **{r.mention}**", color=discord.Color.green()))

    @autorole.command(name="remove", description="🎖️ [АДМИН] Убрать автороль")
    @app_commands.default_permissions(administrator=True)
    async def autorole_remove(self, inter: discord.Interaction):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        data = core.load_data()
        guild_settings(data, inter.guild_id).pop("autorole", None)
        core.save_data(data)
        await inter.response.send_message(embed=discord.Embed(title="🎖️ Автороль убрана", color=discord.Color.orange()))

    # ---------- /welcome ----------
    welcome = app_commands.Group(name="welcome", description="👋 Приветствие для новых участников")

    @welcome.command(name="set", description="👋 [АДМИН] Установить приветствие в выбранном канале")
    @app_commands.describe(channel="Канал для приветствий", text="Текст. Можно использовать {user} и {server}")
    @app_commands.default_permissions(administrator=True)
    async def welcome_set(self, inter: discord.Interaction, channel: discord.TextChannel, text: str):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        if len(text) > 900:
            return await inter.response.send_message("❌ Текст слишком длинный (макс. 900 символов)!", ephemeral=True)
        me = inter.guild.me or inter.guild.get_member(self.bot.user.id)
        if not me or not channel.permissions_for(me).send_messages:
            return await inter.response.send_message("❌ Я не могу отправлять сообщения в этом канале!", ephemeral=True)
        data = core.load_data()
        guild_settings(data, inter.guild_id)["welcome"] = {"channel": channel.id, "text": text}
        core.save_data(data)
        preview = text.replace("{user}", "Новичок").replace("{server}", inter.guild.name)
        e = discord.Embed(title="👋 Приветствие установлено", color=discord.Color.green())
        e.add_field(name="Канал", value=channel.mention)
        e.add_field(name="Текст", value=preview)
        await inter.response.send_message(embed=e)

    @welcome.command(name="delete", description="👋 [АДМИН] Удалить приветствие из канала")
    @app_commands.describe(channel="Канал, в котором настроено приветствие")
    @app_commands.default_permissions(administrator=True)
    async def welcome_delete(self, inter: discord.Interaction, channel: discord.TextChannel):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        data = core.load_data()
        settings = guild_settings(data, inter.guild_id)
        welcome = settings.get("welcome")
        if not welcome or int(welcome.get("channel", 0)) != channel.id:
            return await inter.response.send_message("❌ В этом канале нет настроенного приветствия!", ephemeral=True)
        settings.pop("welcome", None)
        core.save_data(data)
        await inter.response.send_message(embed=discord.Embed(title="👋 Приветствие удалено", description=f"Канал: {channel.mention}", color=discord.Color.orange()))

    @welcome.command(name="preview", description="👋 [АДМИН] Посмотреть текущее приветствие")
    @app_commands.default_permissions(administrator=True)
    async def welcome_preview(self, inter: discord.Interaction):
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message("❌ Только для администраторов!", ephemeral=True)
        data = core.load_data()
        w = guild_settings(data, inter.guild_id, create=False).get("welcome")
        if not w or not w.get("text"):
            return await inter.response.send_message("📭 Приветствие не установлено. Напиши `/welcome set`!", ephemeral=True)
        await inter.response.send_message(embed=discord.Embed(title="👋 Текущее приветствие", description=w["text"], color=discord.Color.blurple()))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
