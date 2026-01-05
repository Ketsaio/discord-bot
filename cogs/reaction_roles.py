import discord
from discord import Embed
from discord.ext import commands
from discord import app_commands
from .views import PanelSetupView

class Reaction_roles(commands.Cog):
    def __init__(self, bot):
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
    
    @app_commands.command(name="setup_reaction_roles", description="Sets up reaction roles embed")
    @app_commands.describe(title="Title of your embed", desc="Description of your embed")
    async def setup_rr(self, interaction : discord.Interaction, title : str, desc : str):

        if not (interaction.user.guild_permissions.manage_channels or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!")
            return
        
        if not (interaction.guild.me.guild_permissions.manage_channels or interaction.guild.me.guild_permissions.administrator):
            await interaction.response.send_message("I dont have permissions to do that!")
            return
        
        embed = Embed(title="Reaction roles embed creator!", description="Select roles from the dropdown menu")

        view = PanelSetupView(title, desc)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Reaction_roles(bot))