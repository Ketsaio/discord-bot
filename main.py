from dotenv import load_dotenv
import os
import discord
from discord import app_commands
from discord.ext import commands
from pymongo import AsyncMongoClient

load_dotenv() # loads .env

TOKEN = os.getenv("DISCORD_TOKEN")
MONGO = os.getenv("MONGO_URL")

GUILD_ID = 1415448304157987008


intents = discord.Intents.default()
intents.message_content = True          # allows bot to read messages
intents.members = True                  # allows bot to access member info
intents.presences = True                # allows bot to see member presence/status (requires privileged intent in Discord dev portal)

client = AsyncMongoClient(MONGO)
database = client["discordbot"]         # connection to database "discordbot" holding users and guilds (in future tickets and reaction roles)
print(f"Connected to {database.name} database")

class MyBot(commands.Bot):
    def __init__(self, command_prefix, database, tree_cls = app_commands.CommandTree, description = "My discord bot", intents=intents):
        super().__init__(command_prefix=command_prefix, tree_cls=tree_cls, description=description, intents=intents)    
        self.database = database    # Make database accessible across all cogs
        self.synced = False

    async def setup_hook(self):
        for file in os.listdir("cogs"):         # loads all .py files from cogs folder as extentions
            if file.endswith(".py"):
                await self.load_extension(f"cogs.{file[:-3]}")
        print(f"Loaded {len(os.listdir('cogs'))} cogs")


bot = MyBot(command_prefix="?", database = database)

@bot.event
async def on_ready():
    print(f"{bot.user} READY FOR FLIGHT")
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    print(f"Synced {len(synced)} commands to guild")
    
    bot.synced = True

bot.run(TOKEN)