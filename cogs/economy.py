import discord
from discord.ext import commands
from discord import app_commands, Embed
from random import randint
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Economy(commands.Cog):
    """
    Cog responsible for Economy structure, features: checking balance and inventory and handling daily rewards.
    """
    def __init__(self, bot):
        """
        Initializes the Economy cog.

        Arguments:
            bot: Discord bot instance.
        """
        self.bot = bot

    async def get_database_cog(self):
        """
        Returns the Database cog instance.

        Returns:
            Database cog or None if cog is not loaded.
        """
        return self.bot.get_cog("Database")
    
    async def get_member(self, discord_Obj):
        """
        Retrieves guild data from database.

        Arguments:
            discord_Obj: Discord Object (Interaction, Member, Role or Channel).

        Returns:
            dict: Guild member_data dict or None is something went wrong.
        """
        database_cog = await self.get_database_cog()
        member_data = await database_cog.find_or_create__member(discord_Obj)
        if member_data is None:
            return None
        return member_data

    @commands.Cog.listener()
    async def on_message(self, message : discord.Message):
        """
        Listens for any message send, then gives author 1-5 xp.
        If user active pet is doggo then user recives bounus xp.

        Arguments:
            message (discord.Message): Message that was send in channel.
        """

        if message.author.bot:
            return
        
        member_data = await self.get_member(message.author)
        if member_data.get("active_pet", 0) == "doggo":
            added_xp = randint(3,8)
        else:
            added_xp = randint(1,5)
        await self.bot.database["users"].update_one({"_id" : str(message.author.id)}, {"$inc" : {"xp" : added_xp}})
        member_data = await self.get_member(message.author)
        xp = member_data.get("xp")
        level = member_data.get("level")
        if xp >= 8 * level:
            await self.bot.database["users"].update_one({"_id" : str(message.author.id)}, {"$inc" : {"level" : 1}, "$set" : {"xp" : 0}})
            
            embed = Embed(title="**🔊 LEVEL UP **", description=f"**{message.author.mention} JUST LEVELED UP TO LEVEL{level+1}\nCONGRATULATIONS!**", color=discord.Color.random())
            await message.channel.send(embed=embed)
    

    @app_commands.command(name="balance", description="Check your balance!")
    async def check_bal(self, interaction : discord.Interaction):
        """
        Retrieves user balance from database.

        Arguments:
            interaction (discord.Interaction): Context interaction.
        """
        member_data = await self.get_member(interaction)
        if member_data is None:
            return

        balance = member_data.get("coins", 0)

        embed = Embed(title="**🪙 NATIONAL BANK**", description=f"**Your balance: ${balance}**", color=discord.Color.gold())

        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="daily_reward", description="Claim your global daily reward")
    async def daily_reward(self, interaction : discord.Interaction):
        """
        Gives user a reward (can be used once in 24h).

        Arguments:
            interaction (discord.Interaction): Context interaction.
        """
        member_data = await self.get_member(interaction)
        last_daily = member_data.get("cooldowns", {}).get("last_daily_reward")

        if last_daily is None or datetime.now() - last_daily >= timedelta(hours=24):
            await self.bot.database["users"].update_one({"_id": str(interaction.user.id)}, {"$set" : {"cooldowns.last_daily_reward" : datetime.now()}, "$inc": {"coins": 100}})

            embed = Embed(title="**📅 DAILY REWARD**", description="**U claimed your daily! Come back in 24h**", color=discord.Color.green())
        
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif datetime.now() - last_daily < timedelta(hours=24):

            hours, minutes = await self.time_left(last_daily)

            embed = Embed(title="**📅 DAILY REWARD**", description=f"**U can claim next daily reward in {hours} hours and {minutes} minutes**", color=discord.Color.green())

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="inventory", description="Take a look into your inventory")
    async def inventory(self, interaction : discord.Interaction):
        """
        Retrieves user inventory from database.

        Arguments:
            interaction (discord.Interaction): Context interaction.
        """
        member_data = await self.get_member(interaction)

        inventory = member_data.get("inventory", {})

        embed = discord.Embed(
            title=f"{interaction.user.name} inventory!",
            description="",
            color=discord.Color.brand_green()
        )

        for name, item in inventory.items():
            embed.add_field(
                name=f"{item['emote']} **{name.capitalize()}**",
                value=f"*{item['desc']}*\nRarity: {item['rare_emote']}\nLevel: {item['level']}\nxp: {item['xp']}",
                inline=True
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


    async def time_left(self, last_smth : datetime):
        remaining = timedelta(hours=24) - (datetime.now() - last_smth)
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes = remainder // 60
        return hours, minutes 


async def setup(bot):
    await bot.add_cog(Economy(bot))