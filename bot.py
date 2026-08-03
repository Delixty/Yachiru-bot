"""
bot.py — главный файл. Запуск: python bot.py
Загружает все модули (cogs) и синхронизирует slash-команды.
"""

import discord
from discord import app_commands
from discord.ext import commands
import core


class KokuBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        import traceback
        exts = ["cogs.economy", "cogs.games", "cogs.shop", "cogs.profile",
                "cogs.social", "cogs.events", "cogs.activities",
                "cogs.moderation", "cogs.rp"]
        loaded = 0
        for ext in exts:
            try:
                await self.load_extension(ext)
                loaded += 1
                print(f"  ✅ Загружен модуль: {ext}")
            except Exception:
                # Полный traceback, чтобы видеть реальную причину сбоя модуля
                print(f"  ❌ Ошибка загрузки {ext}:")
                traceback.print_exc()
        print(f"  📦 Загружено модулей: {loaded}/{len(exts)}")


bot = KokuBot()


async def sync_commands():
    """Синхронизирует slash-команды: глобально + мгновенно в каждой гильдии."""
    import traceback
    # 1) Глобальная синхронизация (для всех серверов)
    try:
        synced = await bot.tree.sync()
        print(f"  ✅ Глобально синхронизировано команд: {len(synced)}")
    except Exception:
        print("  ❌ Ошибка глобальной синхронизации:")
        traceback.print_exc()

    # 2) Копируем глобальные команды в каждую гильдию и синхронизируем — МГНОВЕННО
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=discord.Object(id=guild.id))
            await bot.tree.sync(guild=discord.Object(id=guild.id))
        except Exception:
            pass
    if bot.guilds:
        print(f"  ⚡ Команды синхронизированы для {len(bot.guilds)} гильдий (мгновенно)")


@bot.event
async def on_ready():
    print("=" * 52)
    print(f"  🌸 Yachiru запущена: {bot.user}")
    print(f"  🆔 ID: {bot.user.id}")
    print(f"  🪙 Валюта: чирукойны")
    print(f"  ✨ by delixty")
    print("=" * 52)
    await sync_commands()


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    uid = str(message.author.id)
    ud = core.get_user(uid)
    now = __import__("time").time()
    
    # Кулдаун на опыт за сообщения (раз в 15 секунд)
    if now - ud.get("last_msg", 0) > 15:
        ud["last_msg"] = now
        core.save_user(uid, ud)
        core.add_xp(uid, __import__("random").randint(3, 8))
                
    await bot.process_commands(message)

@bot.tree.error
async def on_app_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    msg = "⚠️ Произошла ошибка при выполнении команды. Попробуй позже."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass


if __name__ == "__main__":
    if not core.TOKEN:
        print("❌ Токен не найден!")
        print("   Установи переменную окружения TOKEN (или DISCORD_TOKEN / BOT_TOKEN).")
        print("   Локально: скопируй .env.example в .env и вставь токен.")
        print("   На BotHost: Settings → Environment Variables → TOKEN = твой токен.")
    else:
        print("🚀 Запуск Yachiru...")
        bot.run(core.TOKEN)
