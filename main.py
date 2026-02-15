from dotenv import load_dotenv
import os
import discord
from discord import app_commands
from discord.ext import commands
from pymongo import AsyncMongoClient
from cogs.views import TicketView, InTicketView, AfterTicketView, DynamicRoleButton
import logging
import datetime

load_dotenv() # loads .env

logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
MONGO = os.getenv("MONGO_URL")

GUILD_ID = 1415448304157987008


intents = discord.Intents.default()
intents.message_content = True          # allows bot to read messages
intents.members = True                  # allows bot to access member info
intents.presences = True                # allows bot to see member presence/status (requires privileged intent in Discord dev portal)
intents.voice_states = True

client = AsyncMongoClient(MONGO)
database = client["discordbot"]         # connection to database "discordbot" holding users and guilds (in future tickets and reaction roles)
print(f"Connected to {database.name} database")

class MyBot(commands.Bot):
    def __init__(self, command_prefix, database, tree_cls = app_commands.CommandTree, description = "My discord bot", intents=intents):
        super().__init__(command_prefix=command_prefix, tree_cls=tree_cls, description=description, intents=intents)    
        self.database = database    # Make database accessible across all cogs
        self.synced = False

    async def setup_hook(self):

        self.tree.on_error = self.on_tree_error

        for file in os.listdir("cogs"):         # loads all .py files from cogs folder as extentions
            if file.endswith(".py") and file != "views.py":
                await self.load_extension(f"cogs.{file[:-3]}")
        print(f"Loaded {len(os.listdir('cogs'))} cogs")

        self.add_view(TicketView())
        self.add_view(InTicketView())
        self.add_view(AfterTicketView())
        print("Loaded all views!")

        self.add_dynamic_items(DynamicRoleButton)
        print("Loaded all Dynamic Items!")

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
            if isinstance(error, app_commands.CommandInvokeError):
                error = error.original

            if interaction.command:
                cmd_name = interaction.command.callback.__name__
                cog_name = interaction.command.binding.__class__.__name__ if interaction.command.binding else "NoCog"
            else:
                cmd_name = "Unknown"
                cog_name = "Interaction"

            location = f"{cog_name}.{cmd_name}"
            
            if isinstance(error, discord.NotFound):
                return
            
            if isinstance(error, discord.Forbidden):
                logger.warning(f"Forbidden error in '{location}': {error}")
                msg = "I don't have enough permissions to perform this action!"
                return await self._respond_to_error(interaction, msg)

            if isinstance(error, discord.HTTPException):
                logger.error(f"Discord API Error in '{location}': {error}")
                msg = "A connection error occurred with Discord servers."
                return await self._respond_to_error(interaction, msg)

            if isinstance(error, ValueError):
                logger.warning(f"Value error in '{location}': {error}")
                msg = "Invalid value provided for this command."
                return await self._respond_to_error(interaction, msg)

            if isinstance(error, app_commands.CommandOnCooldown):
                msg = f"Command is on cooldown. Try again in {error.retry_after:.2f}s."
                return await self._respond_to_error(interaction, msg)

            logger.error(f"Unhandled error in '{location}':", exc_info=error)
            msg = "An unexpected error occurred. The developers have been notified."
            await self._respond_to_error(interaction, msg)

    async def _respond_to_error(self, interaction: discord.Interaction, message: str):
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except:
            pass

bot = MyBot(command_prefix="?", database = database)

@bot.event
async def on_ready():
    print(f"{bot.user} READY FOR FLIGHT")
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    print(f"Synced {len(synced)} commands to guild")
    
    bot.synced = True

if __name__ == "__main__":
    
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    logging_handler = logging.FileHandler(filename=f"discord_{date_str}.log", encoding="UTF-8", mode="a")

    discord.utils.setup_logging(handler=logging_handler, level=logging.INFO)
    
    bot.run(TOKEN)