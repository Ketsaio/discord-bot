import discord
from discord.ext import commands
from discord import app_commands
from random import randint
from pymongo.errors import PyMongoError
from datetime import datetime, timedelta, timezone

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_database_cog(self):
        return self.bot.get_cog("Database")
    
    async def get_member(self, discord_Obj):
        database_cog = await self.get_database_cog()
        member_data = await database_cog.find_or_create__member(discord_Obj)
        if member_data is None:
            return None
        return member_data

    @commands.Cog.listener()
    async def on_message(self, message : discord.Message):

        if message.author.bot:
            return

        added_xp = randint(1,5)
        member_data = await self.get_member(message.author)
        await self.bot.database["users"].update_one({"_id" : str(message.author.id)}, {"$inc" : {"xp" : added_xp}})
        member_data = await self.get_member(message.author)
        xp = member_data.get("xp")
        if xp >= 10:
            await self.bot.database["users"].update_one({"_id" : str(message.author.id)}, {"$inc" : {"xp" : -10,"level" : 1}})

    @app_commands.command(name="balance", description="Check your balance!")
    async def check_bal(self, interaction : discord.Interaction):
        member_data = await self.get_member(interaction)
        if member_data is None:
            return

        balance = member_data.get("coins")

        await interaction.response.send_message(f"Your balance: {balance}")
        
    @app_commands.command(name="daily_reward", description="Claim your global daily reward")
    async def daily_reward(self, interaction : discord.Interaction):
        member_data = await self.get_member(interaction)
        last_daily = member_data.get("last_daily_reward")
        if datetime.now() - last_daily < timedelta(hours=24):
            await interaction.response.send_message(f"Nagrode możesz odebrać dopiero za {abs(datetime.now().hour - last_daily.hour)} godzin i {abs(datetime.now().minute - last_daily.minute)} minut")
        elif datetime.now() - last_daily >= timedelta(hours=24) or last_daily is None:
            await self.bot.database["users"].update_one({"_id": str(interaction.user.id)}, {"$set" : {"last_daily_reward" : datetime.now()}, "$inc": {"coins": 100}})
            await interaction.response.send_message("U claimed your daily! Come back in 24h")

async def setup(bot):
    await bot.add_cog(Economy(bot))