from dotenv import load_dotenv
import os
import discord
from discord import app_commands
from discord.ext import commands

load_dotenv() # loads .env

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True          # allows bot to read messages
intents.members = True                  # allows bot to access member info
intents.presences = True                # allows bot to see member presence/status (requires privileged intent in Discord dev portal)

class MyBot(commands.Bot):
    def __init__(self, command_prefix, tree_cls = app_commands.CommandTree, description = "My discord bot", intents=intents):
        super().__init__(command_prefix=command_prefix, tree_cls=tree_cls, description=description, intents=intents)    

    async def setup_hook(self):
        for file in os.listdir("cogs"):         # loads all .py files from cogs folder as extentions
            if file.endswith(".py"):
                await self.load_extension(f"cogs.{file[:-3]}")
        print("All cogs loaded!")

bot = MyBot(command_prefix="?")

@bot.event
async def on_ready():
    print(f"{bot.user} READY FOR FLIGHT")