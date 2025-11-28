import discord
from discord import Embed, Colour
from discord.ext import commands
from discord import app_commands
from random import randint, choice
from asyncio import sleep
from datetime import datetime, timedelta


class Gambling(commands.Cog):
    def __init__(self, bot):
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
    
    @app_commands.command(name = "automat", description="Gamble your money on automats")
    @app_commands.describe(amount = "Amount of money u want to gamble")
    async def automats(self, interaction : discord.Interaction, amount : int):
        member_data = await self.get_member(interaction)
        money = member_data.get("coins", 0)

        if money < amount:
            await interaction.response.send_message("U dont have enought money!")
            return

        await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$inc" : {"coins" : -amount}})

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

        await interaction.response.send_message(embed=embed, ephemeral=True)

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
            win_amount = amount * 7
            await self.bot.database["users"].update_one({"_id": str(interaction.user.id)}, {"$inc": {"coins": win_amount}})
            embed_result = discord.Embed(
                title="🎉 JACKPOT! 🎉",
                description=f"All slots match! You won **{win_amount} coins**!",
                color=discord.Colour.green()
            )
        else:
            embed_result = discord.Embed(
                title="💸 You lost",
                description=f"Slots didn't match. You lost **{amount} coins**.",
                color=discord.Colour.red()
            )

        await interaction.followup.send(embed=embed_result, ephemeral=True)
                    

    @app_commands.command(name="scratches", description="Scratch your way to glory! 12$")
    async def scratches(self, interaction: discord.Interaction):
        member_data = await self.get_member(interaction)
        money = member_data.get("coins", 0)

        if money < 12:
            embed = Embed(title="Insufficient funds", description="You don't have enough money to play!", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.bot.database["users"].update_one({"_id": str(interaction.user.id)}, {"$inc": {"coins": -12}})

        roll = randint(1, 100)
        win = 0
        if 1 <= roll <= 5:
            win = randint(150, 250)
        elif 6 <= roll <= 15:
            win = randint(60, 120)
        elif 16 <= roll <= 40:
            win = randint(20, 50)

        if win != 0:
            await self.bot.database["users"].update_one({"_id": str(interaction.user.id)}, {"$inc": {"coins": win}})
            embed = Embed(
                title="🎉 You won!",
                description=f"You just won **{win} coins**!",
                color=Colour.green()
            )
        else:
            embed = Embed(
                title="💸 You lost",
                description="Better luck next time! You lost your 12 coins.",
                color=Colour.red()
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="roulette", description="Win some money!")
    @app_commands.describe(amount="Amount of money to gamble", color="Pick color", number="Pick number")
    async def roulette(self, interaction: discord.Interaction, amount: int, color: str = choice(["red", "black", "green"]), number: int = randint(0, 36)):
        member_data = await self.get_member(interaction)

        if member_data.get("coins", 0) < amount:
            embed = Embed(title="Insufficient funds", description="You don't have enough money to gamble!", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.bot.database["users"].update_one({"_id": str(interaction.user.id)}, {"$inc": {"coins": -amount}})

        result = randint(0, 36)

        if result == 0:
            result_color = "green"
        elif result % 2 == 0:
            result_color = "black"
        else:
            result_color = "red"

        win = 0
        if result_color == color and result == number:
            win = amount * 70
        elif result == number:
            win = amount * 35
        elif result_color == color:
            win = amount * 2

        if win > 0:
            await self.bot.database["users"].update_one({"_id": str(interaction.user.id)}, {"$inc": {"coins": win}})
            embed = Embed(
                title="🎉 You won!",
                description=f"The roulette landed on **{result} ({result_color})**\nYou won **{win} coins**!",
                color=Colour.green()
            )
        else:
            embed = Embed(
                title="💸 You lost",
                description=f"The roulette landed on **{result} ({result_color})**\nBetter luck next time!",
                color=Colour.red()
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name = "crime", description = "go do a crime")
    async def crime(self, interaction : discord.Interaction):
        member_data = await self.get_member(interaction)

        if not member_data:
            return
        
        last_crime = member_data.get("cooldowns", {}).get("last_crime")

        if last_crime is None or datetime.now() - last_crime >= timedelta(hours=3):
            chance = randint(1,10)
            if chance <= 6:
                money_from_crime = randint(50, 150)
                await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$set" : {"cooldowns.last_crime" : datetime.now()}, "$inc" : {
                    "coins" : money_from_crime}})
                
                embed = Embed(
                    title="💸 You commited a crime!",
                    description=f"U have a {money_from_crime} more illegal coins!",
                    color=Colour.green()
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                bail = randint(75, 125)
                await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$set" : {"cooldowns.last_crime" : datetime.now()}, "$inc" : {
                    "coins" : -bail}})
                
                embed = Embed(
                    title="⛓️ You got caught...",
                    description=f"U have to pay {bail} for bail",
                    color=Colour.red()
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        elif datetime.now() - last_crime < timedelta(hours=3):
            embed = Embed(
                title="⏰ MORE TIME",
                description=f"U need to wait {abs(datetime.now().hour - last_crime.hour)} hours and {abs(datetime.now().minute - last_crime.minute)} to steal from someone again!",
                color=Colour.red()
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name = "steal", description = "rob someone")
    @app_commands.describe(member = "discord member")
    async def steal(self, interaction : discord.Interaction, member : discord.Member):
        
        # tutaj zabezpieczenie

        robber = await self.get_member(interaction)
        getting_robbed = await self.get_member(member)

        if not robber and not getting_robbed:
            return

        getting_robbed_money = getting_robbed.get("coins", 0)
        last_steal = robber.get("cooldowns", {}).get("last_steal")

        if last_steal is None or datetime.now() - last_steal >= timedelta(hours=6):
            chance = randint(1,10)
            if chance >= 8:
                how_much = randint(1,5)
                how_much /= 10
                stolen = getting_robbed_money * how_much
                await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$set" : {"cooldowns.last_steal" : datetime.now()}, "$inc" : {"coins" : getting_robbed_money * stolen}})
                await self.bot.database["users"].update_one({"_id" : str(member.id)}, {"$inc" : {"coins" : -stolen}})

                embed = Embed(
                    title="🥷 Succesful robbery!",
                    description=f"{interaction.user.mention} just robbed {int(stolen)} from {member.mention}!",
                    color=Colour.green()
                )

                await interaction.response.send_message(embed=embed)
            else:
                bail = randint(75, 125)
                await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$set" : {"cooldowns.last_crime" : datetime.now()}, "$inc" : {
                    "coins" : -bail}})
                
                embed = Embed(
                    title="⛓️ You got caught...",
                    description=f"U have to pay {bail} for bail",
                    color=Colour.red()
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif datetime.now() - last_steal < timedelta(hours=6):

            embed = Embed(
                title="⏰ MORE TIME",
                description=f"U need to wait {abs(datetime.now().hour - last_steal.hour)} hours and {abs(datetime.now().minute - last_steal.minute)} to steal from someone again!",
                color=Colour.red()
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Gambling(bot))