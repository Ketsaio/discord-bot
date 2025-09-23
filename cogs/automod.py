from pymongo import MongoClient
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
import asyncio

class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name = "clear", description = "Clear given amount of messages")
    @app_commands.describe(amount = "How much messages to clear")
    async def delete_messages(self, interaction: discord.Interaction, amount : int = 1):

        await interaction.response.defer(ephemeral=True, thinking=True)

        if not (interaction.user.guild_permissions.manage_messages or 
                interaction.user.guild_permissions.administrator or
                interaction.user.id == interaction.guild.owner_id):
            await interaction.response.send_message("Nie masz permisji do tego!", ephemeral=True)
            return

        older = []
        newer = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        async for message in interaction.channel.history(limit=amount):
            if message.created_at < cutoff:
                older.append(message)
            else:
                newer.append(message)
            
        deleted = await interaction.channel.purge(limit=len(newer))
        
        for message in older:
            await message.delete()
            await asyncio.sleep(0.6)

        await interaction.followup.send(f"Cleared {len(deleted)} messages!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Automod(bot))