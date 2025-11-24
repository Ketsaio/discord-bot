import discord
from discord.ext import commands
from discord import app_commands
from random import randint, choice
from asyncio import sleep


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
            await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$inc" : {"coins" : amount*7}})
            await interaction.followup.send(f"U just won {amount*7} coins!")
        else:
            await interaction.followup.send(f"U lost all your coins...")
                    
async def setup(bot):
    await bot.add_cog(Gambling(bot))