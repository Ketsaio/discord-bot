import discord
from discord import Embed
from discord.ext import commands
from discord import app_commands
from .views import TicketView


class Tickets(commands.Cog):
    '''
    Cog responsible for ticket system.
    '''
    def __init__(self, bot):
        '''
        Initializes the Tickets cog.

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
    
    @app_commands.command(name = "setup_tickets", description="Use on channel dedicated to tickets!")
    async def setup(self, interaction : discord.Interaction):
        '''
        Sends an embed with a button to create tickets.

        Arguments:
            interaction (discord.Interaction): Context interaction.

        Returns:
            Embed with button.
        '''

        if not (interaction.user.guild_permissions.manage_channels or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!")
            return
        
        if not (interaction.guild.me.guild_permissions.manage_channels or interaction.guild.me.guild_permissions.administrator):
            await interaction.response.send_message("I dont have permissions to do that!")
            return

        try:
            embed = Embed(
                title="Siemano",
                description="Aby stworzyć ticket kliknij przycisk niżej!",
                color=discord.Color.dark_green()
            )
            await interaction.response.send_message(embed=embed, view=TicketView())
        except discord.Forbidden as e:
            print(f"discord Forbidden in tickets: {e}")

async def setup(bot):
    await bot.add_cog(Tickets(bot))