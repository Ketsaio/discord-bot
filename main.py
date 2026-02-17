from dotenv import load_dotenv
import os
import discord
from discord import app_commands
from discord.ext import commands
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from cogs.views import TicketView, InTicketView, AfterTicketView, DynamicRoleButton
from aiohttp import ClientConnectionError
import logging
import datetime

load_dotenv() # loads .env

logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
MONGO = os.getenv("MONGO_URL")
DEV_ID = os.getenv("DEV_ID")
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
                return await self._respond_to_error(interaction, msg, False)

            if isinstance(error, discord.HTTPException):
                logger.error(f"Discord API Error in '{location}': {error}")
                msg = "A connection error occurred with Discord servers."
                return await self._respond_to_error(interaction, msg, True)

            if isinstance(error, ValueError):
                logger.warning(f"Value error in '{location}': {error}")
                msg = "Invalid value provided for this command."
                return await self._respond_to_error(interaction, msg, False)

            if isinstance(error, app_commands.CommandOnCooldown):
                msg = f"Command is on cooldown. Try again in {error.retry_after:.2f}s."
                return await self._respond_to_error(interaction, msg, False)
            
            if isinstance(error, PyMongoError):
                logger.exception(f"PyMongoError in '{location}' : {error}")
                msg = "Database error, your data might not been saved."
                return await self._respond_to_error(interaction, msg, True)
            
            if isinstance(error, discord.ClientException):
                logger.warning(f"Client logic error in '{location}': {error}")
                msg = f"Action failed {error}."
                return await self._respond_to_error(interaction, msg, False)
            
            if isinstance(error, ClientConnectionError):
                logger.exception(f"Aiohttp error in '{location}': {error}")
                msg = f"Cant download gif right now."
                return await self._respond_to_error(interaction, msg, True)

            logger.error(f"Unhandled error in '{location}':", exc_info=error)
            msg = "An unexpected error occurred. The developers have been notified."
            await self._respond_to_error(interaction, msg, True)

    async def _respond_to_error(self, interaction: discord.Interaction, message: str, notify_dev : bool):
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except:
            pass

        if notify_dev:
            try:
                dev = await self.fetch_user(int(DEV_ID))
                await dev.send(message)
            except discord.Forbidden:
                print("UNBLOCK ME, I NEED TO SEND U DM!")
            except Exception as e:
                print(f"Error while sending DM: {e}")

bot = MyBot(command_prefix="?", database = database)

@bot.tree.command(name="sync", description="ADMIN COMMAND ONLY")
@app_commands.describe(option="GLOBAL | LOCAL")
@app_commands.choices(option=[app_commands.Choice(name="Global", value="global"), app_commands.Choice(name="Local", value="guild")])
async def sync(interaction: discord.Interaction, option: app_commands.Choice[str]):
    if interaction.user.id != int(DEV_ID):
        await interaction.response.send_message("U are not a dev!", ephemeral=True)
        return 

    await interaction.response.defer(ephemeral=True)

    try:
        if option.value == "global":
            synced = await bot.tree.sync()
            await interaction.followup.send("Synced commands globally!")
        
        elif option.value == "guild":
            bot.tree.copy_global_to(guild=interaction.guild)
            synced = await bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send("Synced commands locally!")

    except Exception as e:
        await interaction.followup.send(f"Sync error: {e}")

@bot.event
async def on_ready():

    if hasattr(bot, 'synced') and bot.synced:
        print("Bot reconnected (Skipping sync).")
        return

    print(f"{bot.user} READY FOR FLIGHT")
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    print(f"Synced {len(synced)} commands to guild")
    
    bot.synced = True

if __name__ == "__main__":
    
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    logging_handler = logging.FileHandler(filename=f"discord_logs/discord_{date_str}.log", encoding="UTF-8", mode="a")

    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
    logging_handler.setFormatter(formatter)

    bot.run(TOKEN, log_handler=logging_handler, log_level=logging.INFO, root_logger=True)