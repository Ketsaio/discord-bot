import discord
from discord import Embed
from discord.ext import commands
from discord import app_commands
from asyncio import sleep
import aiofiles
from datetime import datetime


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

        embed = Embed(
            title="Siemano",
            description="Aby stworzyć ticket kliknij przycisk niżej!",
            color=discord.Color.dark_green()
        )
        await interaction.response.send_message(embed=embed, view=TicketView())

    
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="📩 Click to create a ticket!", style=discord.ButtonStyle.grey)
    async def create(self, interaction : discord.Interaction, button: discord.ui.Button):
        '''
        Creates a new ticket channel with restricted access for the user.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            button (discord.ui.Button): Not used but required by syntax.
        '''

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True)
        }  

        channel = await interaction.guild.create_text_channel(name=f"Ticket {interaction.user.name}", overwrites=overwrites)

        embed = Embed(title="Support will contact shortly, please wait.", description="To close this ticket, click ❌\nTo get log of this conversation, click 📝", color=discord.Color.dark_green())

        await interaction.response.defer(ephemeral=True)

        await channel.send(embed=embed, view=InTicketView(channel, interaction.user))

class InTicketView(discord.ui.View):
    def __init__(self, channel : discord.TextChannel, member : discord.Member):
        '''
        Initializes the ticket control view.

        Arguments:
            channel (discord.TextChannel): Channel that was created.
            member (discord.Member): Member that created a ticket.
        '''
        super().__init__()
        self.channel = channel
        self.member = member

    @discord.ui.button(label="🔒 Close", style = discord.ButtonStyle.gray)
    async def close(self, interaction : discord.Interaction, button: discord.ui.Button):
        '''
        Closes the ticket for the user and displays the admin control panel.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            button (discord.ui.Button): Not used but required by syntax.
        '''
        embed1 = Embed(title = f"Closed by {self.member.name}")

        await interaction.response.send_message(embed=embed1)

        await self.channel.set_permissions(self.member, view_channel=False)

        embed2 = Embed(title = "======= CONTROL PANEL =======", description="To delete ticket click button with ❌\nTo get ticket log click button with 📝", color=discord.Color.dark_green())

        await interaction.followup.send(embed=embed2, view=AfterTicketView(self.channel, self.member))

class AfterTicketView(discord.ui.View):
    def __init__(self, channel : discord.TextChannel, member : discord.Member):
        '''
        Initializes the control panel view shown after the ticket is closed.

        Arguments:
            channel (discord.TextChannel): Channel that was created.
            member (discord.Member): Member that created a ticket.
        '''
        super().__init__()
        self.channel = channel
        self.member = member

    @discord.ui.button(label = "❌ Delete", style = discord.ButtonStyle.gray)
    async def delete(self, interaction : discord.Interaction, button: discord.ui.Button):
        '''
        Deletes a ticket.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            button (discord.ui.Button): Not used but required by syntax.
        '''

        await interaction.response.send_message("**Channel will be deleted in 5 seconds!**", )

        await sleep(5)

        await interaction.channel.delete()

    @discord.ui.button(label = "📝 Log", style = discord.ButtonStyle.gray)
    async def log(self, interaction : discord.Interaction, button: discord.ui.Button):
        '''
        Generates and sends a .txt file containing the ticket's message log.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            button (discord.ui.Button): Not used but required by syntax.

        Returns:
            A .txt file containing the message history.
        '''

        await interaction.response.send_message("Please wait, generating logs...")

        date = datetime.now().strftime("%Y-%m-%d")

        async with aiofiles.open(f"logs/{self.member.name}_{date}.txt", "w") as f:
            async for message in self.channel.history():
                if message.author == interaction.guild.me:
                    continue
            
                await f.write(f"{message.author}: {message.content}\n")

        await interaction.followup.send(file=discord.File(f"logs/{self.member.name}_{date}.txt"))

async def setup(bot):
    await bot.add_cog(Tickets(bot))