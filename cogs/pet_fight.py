import discord
from discord import Embed
from discord.ext import commands
from discord import app_commands
from .views import AcceptView

class Pet_fight(commands.Cog):
    '''
    Cog responsible for pet fights between members.
    '''
    def __init__(self, bot):
        '''
        Initializes the pet fight cog.

        Arguments:
            bot: Discord bot instance.
        '''
        self.bot = bot

    async def get_database_cog(self):
        '''
        Returns the Database cog instance.

        Returns:
            Database cog or None if cog is not loaded.
        '''
        return self.bot.get_cog("Database")
    
    async def get_member(self, discord_Obj):
        '''
        Retrieves guild data from database.

        Arguments:
            discord_Obj: Discord Object (Interaction, Member, Role or Channel).

        Returns:
            dict: Guild member_data dict or None is something went wrong.
        '''
        database_cog = await self.get_database_cog()
        member_data = await database_cog.find_or_create__member(discord_Obj)
        if member_data is None:
            return None
        return member_data
    

    @app_commands.command(name="battle", description="Test your pet in battle!")
    @app_commands.describe(member="Your opponent!")
    async def battle(self, interaction : discord.Interaction, member : discord.Member):
        '''
        Creates embed and links it with view.

        Arguments:
            interaction (discord.Interaction): The interaction context.
            member (discord.Member): Member challenged to the fight.
        '''
        
        if member.id == interaction.user.id:
            await interaction.response.send_message("U cant fight with yourself!", ephemeral=True)
            return

        if member.id == interaction.guild.me.id:
            await interaction.response.send_message("U cant challange me to a battle!", ephemeral=True)
            return

        embed = Embed(title="Fight is about to begin!", description=f"{interaction.user.mention} challenges {member.mention} to fight!\n\n{member.mention} do u accept?", color=discord.Color.red())

        members = [interaction.user, member]

        await interaction.response.send_message(embed=embed, view=AcceptView(members))
        

async def setup(bot):
    await bot.add_cog(Pet_fight(bot))