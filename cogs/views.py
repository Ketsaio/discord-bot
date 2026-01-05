import discord
import io
from datetime import datetime
from discord import Embed
from asyncio import sleep
from discord.ui import DynamicItem

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Click to create a ticket!", style=discord.ButtonStyle.grey, custom_id="view_create_ticket")
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

        try:
            existing_channel = discord.utils.get(interaction.guild.text_channels, topic=str(interaction.user.id))

            if existing_channel:
                await interaction.response.send_message("U already have a ticket open!", ephemeral=True)
                return

            channel = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites, topic=str(interaction.user.id))

            embed = Embed(title="Support will contact shortly, please wait.", description="To close this ticket, click ❌\nTo get log of this conversation, click 📝", color=discord.Color.dark_green())

            await interaction.response.defer(ephemeral=True)

            await channel.send(embed=embed, view=InTicketView())
        
        except (discord.Forbidden, PermissionError) as e:
            print(f"Error in TicketView: {e}")

class InTicketView(discord.ui.View):
    def __init__(self):
        '''
        Initializes the ticket control view.

        Arguments:
            channel (discord.TextChannel): Channel that was created.
            member (discord.Member): Member that created a ticket.
        '''
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close", style = discord.ButtonStyle.gray, custom_id="view_close_ticket")
    async def close(self, interaction : discord.Interaction, button: discord.ui.Button):
        '''
        Closes the ticket for the user and displays the admin control panel.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            button (discord.ui.Button): Not used but required by syntax.
        '''
        try:
            embed1 = Embed(title = f"Closed by {interaction.user.name}")

            await interaction.response.send_message(embed=embed1)

            await interaction.channel.set_permissions(interaction.user, view_channel=False)

            embed2 = Embed(title = "======= CONTROL PANEL =======", description="To delete ticket click button with ❌\nTo get ticket log click button with 📝", color=discord.Color.dark_green())

            await interaction.followup.send(embed=embed2, view=AfterTicketView())

        except (discord.Forbidden, PermissionError) as e:
            print(f"Error in TicketView: {e}")

class AfterTicketView(discord.ui.View):
    def __init__(self):
        '''
        Initializes the control panel view shown after the ticket is closed.

        Arguments:
            channel (discord.TextChannel): Channel that was created.
            member (discord.Member): Member that created a ticket.
        '''
        super().__init__(timeout=None)

    @discord.ui.button(label = "❌ Delete", style = discord.ButtonStyle.gray, custom_id="view_delete_ticket")
    async def delete(self, interaction : discord.Interaction, button: discord.ui.Button):
        '''
        Deletes a ticket.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            button (discord.ui.Button): Not used but required by syntax.
        '''
        try:
            await interaction.response.send_message("**Channel will be deleted in 5 seconds!**", )

            await sleep(5)

            await interaction.channel.delete()

        except (discord.Forbidden, PermissionError) as e:
            print(f"Error in TicketView: {e}")

    @discord.ui.button(label = "📝 Log", style = discord.ButtonStyle.gray, custom_id="view_logs_in_ticket")
    async def log(self, interaction : discord.Interaction, button: discord.ui.Button):
        '''
        Generates and sends a .txt file containing the ticket's message log.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            button (discord.ui.Button): Not used but required by syntax.

        Returns:
            A .txt file containing the message history.
        '''
        try:
            await interaction.response.send_message("Please wait, generating logs...")

            date = datetime.now().strftime("%Y-%m-%d")

            buffer = io.BytesIO()

            async for message in interaction.channel.history(oldest_first=True):
                if message.author == interaction.guild.me:
                    continue
                else:
                    content = f"[{message.created_at.strftime('%Y-%m-%d %H:%M')}] {message.author}: {message.content}\n"
                    buffer.write(content.encode('UTF-8'))
                
            buffer.seek(0)

            file_name = f"{interaction.user.name}_{date}.txt"

            await interaction.followup.send(file=discord.File(fp=buffer, filename=file_name))
            buffer.close()

        except (discord.Forbidden, PermissionError) as e:
            print(f"Error in TicketView: {e}")


class DynamicRoleButton(DynamicItem[discord.ui.Button], template = r'role:(?P<id>[0-9]+)'):
    def __init__(self, role_id : int):
        super().__init__(discord.ui.Button(style=discord.ButtonStyle.primary, label="Role", custom_id=f"role:{role_id}", emoji="🎭"))

        self.role_id = role_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls(int(match['id']))
    
    async def callback(self, interaction : discord.Interaction):

        role = interaction.guild.get_role(self.role_id)

        if not role:
            await interaction.response.send_message("This role doesnt exit")
            return
        
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
        else:
            await interaction.user.add_roles(role)

        await interaction.response.defer()


class PanelSetupView(discord.ui.View):
    def __init__(self, title : str, desc : str):
        super().__init__(timeout=180)
        self.title = title
        self.desc = desc
        self.selected_roles = []

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="select roles...", min_values=1, max_values=25)
    async def select_roles(self, interaction : discord.Interaction, select : discord.ui.RoleSelect):
        self.selected_roles = select.values
        await interaction.response.defer()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, intreaction : discord.Interaction, button : discord.ui.Button):

        embed = Embed(title=self.title, description=self.desc, color=discord.Color.blue())

        view = discord.ui.View(timeout=None)

        for role in self.selected_roles:
            button = DynamicRoleButton(role.id)
            button.item.label = role.name

            view.add_item(button)

        await intreaction.response.send_message(embed=embed, view=view)