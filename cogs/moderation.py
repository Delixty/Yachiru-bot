"""cogs/moderation.py — модерация: бан, кик, мут, роли, автороль, приветствие."""

import discord
from datetime import timedelta
from discord import app_commands
from discord.ext import commands
import core


def role_autocomplete(interaction: discord.Interaction, current: str):
    if interaction.guild is None:
        return []
    opts = []
    for r in interaction.guild.roles:
        if r.name == "@everyone":
            continue
        if current.lower() in r.name.lower():
            opts.append(app_commands.Choice(name=r.name, value=str(r.id)))
        if len(opts) >= 25:
            break
    return opts


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = core.load_data()

        # Автороль
        role_id = data.get("autorole")
        if role_id:
            role = member.guild.get_role(int(role_id))
            if role is not None:
                try:
                    await member.add_roles(role, reason="Автороль")
                except discord.HTTPException:
                    pass

        # Приветствие
        welcome = data.get("welcome")
        if not welcome or not welcome.get("text"):
            return
        channel = member.guild.get_channel(int(welcome.get("channel", 0)))
        if channel is None:
            return

        text = welcome["text"].replace("{user}", member.mention).replace("{server}", member.guild.name)

        embed = discord.Embed(
            title=f"👋 Добро пожаловать, {member.display_name}!",
            description=f"{text}\n\n*by delixty*",
            color=discord.Color.pink(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        banner = None
        if member.guild.banner:
            banner = member.guild.banner.url
        else:
            try:
                fetched = await self.bot.fetch_user(member.id)
                if fetched.banner:
                    banner = fetched.banner.url
            except discord.HTTPException:
                pass
        if not banner and member.guild.icon:
            banner = member.guild.icon.url
        if banner:
            embed.set_image(url=banner)

        embed.add_field(name="👥 Участник №", value=str(member.guild.member_count), inline=True)
        embed.add_field(name="📅 Аккаунт создан", value=discord.utils.format_dt(member.created_at, "R"), inline=True)
        embed.set_footer(text=f"{member.guild.name} • by delixty",
                         icon_url=member.guild.icon.url if member.guild.icon else discord.Embed.Empty)

        try:
            await channel.send(content=member.mention, embed=embed)
        except discord.HTTPException:
            pass

    # ---------- /ban ----------
    @app_commands.command(name="ban", description="🔨 Забанить пользователя")
    @app_commands.describe(user="Кого забанить", reason="Причина")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Не указана"):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ У тебя нет прав `Забанить участников`!", ephemeral=True)
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            return await interaction.response.send_message("❌ Этот участник на уровне тебя или выше — нельзя!", ephemeral=True)
        try:
            await user.ban(reason=f"{interaction.user} — {reason}")
        except discord.Forbidden:
            return await interaction.response.send_message("❌ У меня нет прав на бан!", ephemeral=True)
        embed = discord.Embed(title="🔨 Бан", color=discord.Color.red())
        embed.add_field(name="Участник", value=user.mention)
        embed.add_field(name="Причина", value=reason)
        embed.add_field(name="Модератор", value=interaction.user.mention)
        await interaction.response.send_message(embed=embed)

    # ---------- /kick ----------
    @app_commands.command(name="kick", description="👢 Выгнать пользователя")
    @app_commands.describe(user="Кого выгнать", reason="Причина")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Не указана"):
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ У тебя нет прав `Выгнать участников`!", ephemeral=True)
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            return await interaction.response.send_message("❌ Этот участник на уровне тебя или выше — нельзя!", ephemeral=True)
        try:
            await user.kick(reason=f"{interaction.user} — {reason}")
        except discord.Forbidden:
            return await interaction.response.send_message("❌ У меня нет прав на кик!", ephemeral=True)
        embed = discord.Embed(title="👢 Кик", color=discord.Color.orange())
        embed.add_field(name="Участник", value=user.mention)
        embed.add_field(name="Причина", value=reason)
        embed.add_field(name="Модератор", value=interaction.user.mention)
        await interaction.response.send_message(embed=embed)

    # ---------- /mute ----------
    @app_commands.command(name="mute", description="🔇 Замутить пользователя (таймаут)")
    @app_commands.describe(user="Кого замутить", minutes="Сколько минут (макс. 40320)", reason="Причина")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, user: discord.Member, minutes: int, reason: str = "Не указана"):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ У тебя нет прав `Управлять таймаутами`!", ephemeral=True)
        if minutes <= 0:
            return await interaction.response.send_message("❌ Время должно быть больше 0!", ephemeral=True)
        if minutes > 40320:
            return await interaction.response.send_message("❌ Максимум 40320 минут (28 дней)!", ephemeral=True)
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            return await interaction.response.send_message("❌ Этот участник на уровне тебя или выше — нельзя!", ephemeral=True)
        try:
            await user.timeout(timedelta(minutes=minutes), reason=f"{interaction.user} — {reason}")
        except discord.Forbidden:
            return await interaction.response.send_message("❌ У меня нет прав на таймаут!", ephemeral=True)
        embed = discord.Embed(title="🔇 Мут", color=discord.Color.dark_blue())
        embed.add_field(name="Участник", value=user.mention)
        embed.add_field(name="Длительность", value=core.cd(minutes * 60))
        embed.add_field(name="Причина", value=reason)
        await interaction.response.send_message(embed=embed)

    # ---------- /unmute ----------
    @app_commands.command(name="unmute", description="🔊 Снять мут с пользователя")
    @app_commands.describe(user="С кого снять мут")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ У тебя нет прав `Управлять таймаутами`!", ephemeral=True)
        try:
            await user.timeout(None)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Не удалось снять мут!", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(
            title="🔊 Мут снят", description=f"С **{user.mention}** снят таймаут.", color=discord.Color.green()))

    # ---------- /role ----------
    @app_commands.command(name="role", description="🎭 Выдать роль пользователю")
    @app_commands.describe(user="Кому выдать", role="Какую роль")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.autocomplete(role=role_autocomplete)
    async def role(self, interaction: discord.Interaction, user: discord.Member, role: str):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("❌ У тебя нет прав `Управлять ролями`!", ephemeral=True)
        r = interaction.guild.get_role(int(role))
        if r is None:
            return await interaction.response.send_message("❌ Роль не найдена!", ephemeral=True)
        if r >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ Эта роль выше моей — не могу выдать!", ephemeral=True)
        try:
            await user.add_roles(r, reason=str(interaction.user))
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Не удалось выдать роль!", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(
            title="🎭 Роль выдана",
            description=f"**{user.mention}** получил роль **{r.mention}**", color=discord.Color.purple()))

    # ---------- /autorole ----------
    autorole = app_commands.Group(name="autorole", description="🎖️ Автоматическая роль для новичков")

    @autorole.command(name="set", description="Установить автороль")
    @app_commands.describe(role="Какую роль выдавать новичкам")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(role=role_autocomplete)
    async def autorole_set(self, interaction: discord.Interaction, role: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Только для администраторов!", ephemeral=True)
        r = interaction.guild.get_role(int(role))
        if r is None:
            return await interaction.response.send_message("❌ Роль не найдена!", ephemeral=True)
        if r >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ Эта роль выше моей — не смогу выдавать!", ephemeral=True)
        data = core.load_data()
        data["autorole"] = str(r.id)
        core.save_data(data)
        await interaction.response.send_message(embed=discord.Embed(
            title="🎖️ Автороль установлена",
            description=f"Новые участники будут получать **{r.mention}**", color=discord.Color.green()))

    @autorole.command(name="remove", description="Убрать автороль")
    @app_commands.default_permissions(administrator=True)
    async def autorole_remove(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Только для администраторов!", ephemeral=True)
        data = core.load_data()
        data.pop("autorole", None)
        core.save_data(data)
        await interaction.response.send_message(embed=discord.Embed(
            title="🎖️ Автороль убрана", color=discord.Color.orange()))

    # ---------- /welcome ----------
    welcome = app_commands.Group(name="welcome", description="👋 Приветствие для новичков")

    @welcome.command(name="set", description="Установить приветствие для новых участников")
    @app_commands.describe(channel="Канал для приветствий", text="Текст ({user}, {server})")
    @app_commands.default_permissions(administrator=True)
    async def welcome_set(self, interaction: discord.Interaction, channel: discord.TextChannel, text: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Только для администраторов!", ephemeral=True)
        if len(text) > 900:
            return await interaction.response.send_message("❌ Текст слишком длинный (макс. 900 символов)!", ephemeral=True)
        data = core.load_data()
        data["welcome"] = {"channel": channel.id, "text": text}
        core.save_data(data)
        preview = text.replace("{user}", "Новичок").replace("{server}", interaction.guild.name)
        embed = discord.Embed(title="👋 Приветствие установлено", color=discord.Color.green())
        embed.add_field(name="Канал", value=channel.mention, inline=True)
        embed.add_field(name="Текст (превью)", value=preview, inline=False)
        embed.set_footer(text="Плейсхолдеры: {user} — упоминание, {server} — имя сервера")
        await interaction.response.send_message(embed=embed)

    @welcome.command(name="delete", description="Удалить приветствие")
    @app_commands.default_permissions(administrator=True)
    async def welcome_delete(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Только для администраторов!", ephemeral=True)
        data = core.load_data()
        data.pop("welcome", None)
        core.save_data(data)
        await interaction.response.send_message(embed=discord.Embed(
            title="👋 Приветствие удалено", color=discord.Color.orange()))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
