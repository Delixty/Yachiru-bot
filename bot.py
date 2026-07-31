"""
bot.py — главный файл. Запуск: python bot.py
Загружает все модули (cogs) и синхронизирует slash-команды.
"""

import discord
from discord import app_commands
from discord.ext import commands
import core


class YachiruBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for ext in ["cogs.economy", "cogs.games", "cogs.shop", "cogs.profile", "cogs.social", "cogs.events", "cogs.activities", "cogs.moderation", "cogs.rp"]:
            try:
                await self.load_extension(ext)
                print(f"  ✅ Загружен модуль: {ext}")
            except Exception as e:
                print(f"  ❌ Ошибка загрузки {ext}: {e}")
        try:
            synced = await self.tree.sync()
            print(f"  ✅ Синхронизировано команд: {len(synced)}")
        except Exception as e:
            print(f"  ❌ Ошибка синхронизации: {e}")


bot = YachiruBot()


@bot.event
async def on_ready():
    print("=" * 52)
    print(f"  🤖 Yachiru запущен: {bot.user}")
    print(f"  🆔 ID: {bot.user.id}")
    print(f"  🪙 Валюта: чирукойны")
    print("=" * 52)


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
        lvl_up = core.add_xp(uid, __import__("random").randint(3, 8))
        if lvl_up:
            new_ud = core.get_user(uid)
            try:
                await message.channel.send(f"🎉 {message.author.mention}, ты достиг **{new_ud['level']}** уровня!")
            except Exception:
                pass
                
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
    print("🚀 Запуск Yachiru...")
    bot.run("СЮДА_ВСТАВЬ_НОВЫЙ_ТОКЕН")
