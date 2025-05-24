import discord
from discord.ext import commands
import json

# Load token from data.json
with open("data.json", "r") as f:
    config = json.load(f)

DISCORD_TOKEN = config.get("DISCORD_TOKEN")

# Custom bot class
class Seemu(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Load the music cog
        await self.load_extension("cogs.musicnexx")
        # Sync slash commands
        await self.tree.sync()

    async def on_ready(self):
        print(f"✅ Bot is online as {self.user}")

# Run the bot
bot = Seemu()
bot.run(DISCORD_TOKEN)
