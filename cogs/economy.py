import discord
from discord.ext import commands
from discord import app_commands
from random import randint
from pymongo.errors import PyMongoError
from datetime import datetime, timedelta

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
        try:
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
                await self.bot.database["users"].update_one({"_id" : str(message.author.id)}, {"$inc" : {"xp" : -10,"level" : 1}})
        except PyMongoError as e:
            print(f"PyMongoError: {e}")
    

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

        await interaction.response.send_message(f"Your balance: {balance}")
        
    @app_commands.command(name="daily_reward", description="Claim your global daily reward")
    async def daily_reward(self, interaction : discord.Interaction):
        """
        Gives user a reward (can be used once in 24h).

        Arguments:
            interaction (discord.Interaction): Context interaction.
        """
        member_data = await self.get_member(interaction)
        last_daily = member_data.get("cooldowns", {}).get("last_daily_reward")

        try:
            if last_daily is None or datetime.now() - last_daily >= timedelta(hours=24):
                await self.bot.database["users"].update_one({"_id": str(interaction.user.id)}, {"$set" : {"cooldowns.last_daily_reward" : datetime.now()}, "$inc": {"coins": 100}})
                await interaction.response.send_message("U claimed your daily! Come back in 24h")
            elif datetime.now() - last_daily < timedelta(hours=24):
                await interaction.response.send_message(f"Nagrode możesz odebrać dopiero za {abs(datetime.now().hour - last_daily.hour)} godzin i {abs(datetime.now().minute - last_daily.minute)} minut")
        except PyMongoError as e:
            print(f"PyMongoError: {e}")

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

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Economy(bot))

# code to change, written by me
"""
async def lootbox(self, interaction : discord.Interaction, member_inv : discord.Member):

        colors = ["🟩","🟦", "🟪", "🟨", "🟥", "⬜"]

        embed = discord.Embed(
            title="🎰🎰🎰",
            description="*Jackpot this time!*",
            color=discord.Color.red()
        )

        slot1, slot2, slot3 = choice(colors), choice(colors), choice(colors)

        embed.add_field(
                name="",
                value=f"{slot1}|{slot2}|{slot3}"
        )

        await interaction.response.send_message(embed=embed)

        await sleep(0.3)

        for _ in range(8):
            slot1, slot2, slot3 = choice(colors), choice(colors), choice(colors)
            embed.set_field_at(
                index=0,
                name="",
                value=f"{slot1}|{slot2}|{slot3}"
            )
            await interaction.edit_original_response(embed=embed)
            await sleep(0.3)

        if slot1 == slot2 == slot3:
            if slot1 == colors[0]:
                if randint(1,2) == 1:
                    green = [{name : rest} for name, rest in self.items.items() if rest['rarity'] == "common"]
                    picked = choice(green)
                    key = next(iter(picked))
                    if key not in member_inv:
                        await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$set": {f"inventory.{key}" : picked[key]}})
                        await interaction.channel.send(f"{interaction.user.mention} just dropped {key}")
                    else:
                        await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$inc" : {"coins" : 50}})
                        await interaction.channel.send(f"{interaction.user.mention} gained 50 coin because he/she has an item!")
                else:
                    money = randint(50,100)
                    await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$inc" : {"coins" : money}})
                    await interaction.channel.send(f"{interaction.user.mention} just got {money} coins!")
            
"""