import discord
import io
from datetime import datetime
from discord import Embed
from asyncio import sleep
from discord.ui import DynamicItem, TextInput, Modal
import wavelink
from math import ceil

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
        '''
        Initializes a single button under a RR Embed.
        
        Arguments:
            role_id (int): ID of role connected to the button.
        '''
        super().__init__(discord.ui.Button(style=discord.ButtonStyle.primary, label="Role", custom_id=f"role:{role_id}"))

        self.role_id = role_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls(int(match['id']))
    
    async def callback(self, interaction : discord.Interaction):
        '''
        Gives/Removes role from user.

        Arguments:
            interaction (discord.Interaction): Interaction context.
        '''

        try:
            role = interaction.guild.get_role(self.role_id)

            if not role:
                await interaction.response.send_message("This role doesnt exist")
                return
            
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
            else:
                await interaction.user.add_roles(role)

            await interaction.response.defer()
        
        except discord.Forbidden as e:
            await interaction.followup.send(f"I cant assign role {role.mention}, missing permissions!", ephemeral=True)



class FinalSetupModal(Modal, title="RR Configuration"):
    def __init__(self, channel, selected_roles):
        '''
        Initializes the Modal elements.

        Arguments:
            channel (discord.TextChannel): Channel for RR Embed.
            selected_roles (list): List of selected roles for RR.
        '''
        super().__init__()
        self.channel = channel
        self.selected_roles = selected_roles

        self.title_input = TextInput(label="Title of RR Embed", default="Role Center", required=True)

        default_desc = "Choose your rang:\n\n"
        for role in selected_roles:
            default_desc += f"👉 {role.mention} <- {role.name}\n"

        self.desc_input = TextInput(label="Description of RR Embed", default=default_desc, style=discord.TextStyle.paragraph, required=True)
        self.emoji_input = TextInput(label=f"Emotes for {len(self.selected_roles)} roles", placeholder="📄 📝 🔒 (remember to put space between)", required=False)
        self.colors_input = TextInput(label="Colors for each role (blue, gray, green, red)", placeholder="green blue blue (remember to put space between)", required=False)
        self.embed_color = TextInput(label="Color of your embed!", placeholder="#FF00FF", required=True)

        self.add_item(self.title_input)
        self.add_item(self.desc_input)
        self.add_item(self.emoji_input)
        self.add_item(self.colors_input)
        self.add_item(self.embed_color)


    def parse_style(self, text):
        '''
        Translate provided style for button to discord.ButtonStyle.

        Arguments:
            text (string): style to translate.

        Returns:
            discord.ButtonStyle.*.
        '''
        text = text.lower().strip()
        if text in ["green", "success"]:
            return discord.ButtonStyle.green
        elif text in ["red", "danger"]:
            return discord.ButtonStyle.red
        elif text in ["grey", "gray", "secondary"]:
            return discord.ButtonStyle.secondary
        elif text in ["blue", "blurple", "primary"]:
            return discord.ButtonStyle.primary
        else:
            return None

    async def on_submit(self, interaction : discord.Interaction):
        try:
            embed = Embed(title=self.title_input.value, description=self.desc_input.value, color=discord.Color.from_str(self.embed_color.value))

            emojis = list(self.emoji_input.value.split(' '))

            colors = list(self.colors_input.value.split(' '))

            embed.set_author(name="BrazilBot", icon_url=interaction.client.user.display_avatar.url)

            view = discord.ui.View(timeout=None)

            for i, role in enumerate(self.selected_roles):
                button = DynamicRoleButton(role.id)
                button.item.label = role.name

                if i < len(emojis):
                    button.item.emoji = emojis[i]

                if i < len(colors):
                    try:
                        button.item.style = self.parse_style(colors[i])
                    except Exception:
                        pass

                view.add_item(button)

            await self.channel.send(embed=embed, view=view)
            await interaction.response.defer()
        except discord.Forbidden as e:
            print(f"Bot permission error in FinalSetupModal: {e}")


class RoleSetupView(discord.ui.View):
    def __init__(self, channel : discord.TextChannel):
        '''
        Initializes the select and the button attached to setup_rr Embed.

        Arguments:
            channel (discord.TextChannel): Channel for RR Embed.
        '''
        super().__init__(timeout=180)
        self.channel = channel
        self.selected_roles = []


    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="select roles...", min_values=1, max_values=25)
    async def select_roles(self, interaction : discord.Interaction, select : discord.ui.RoleSelect):
        '''
        Updates the selected roles list.

        Arguments:
            interaction (discord.Interaction): Interaction context.
            select (discord.ui.RoleSelect): Select containing every role.
        '''
        self.selected_roles = select.values
        await interaction.response.defer()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, intreaction : discord.Interaction, button : discord.ui.Button):
        '''
        Submits chosen roles to go into Reaction Roles.

        Arguments:
            interaction (discord.Interaction): Interaction context.
            button (discord.ui.Button): Confirmation button.
        '''

        if not self.selected_roles:
            await intreaction.response.send_message("Choose roles!", ephemeral=True)
            return
        
        modal = FinalSetupModal(self.channel, self.selected_roles)
        await intreaction.response.send_modal(modal)

class MusicButton(discord.ui.Button):
    def __init__(self, id : int, track : wavelink.Playable, mode : bool):
        super().__init__(
            label=str(id + 1),
            style=discord.ButtonStyle.primary,
            row=id // 5
        )
        self.track = track
        self.mode = mode

    async def callback(self, interaction : discord.Interaction):

        await interaction.response.defer()

        if not interaction.user.voice:
            return
        try:
            player : wavelink = interaction.guild.voice_client

            if not player:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
            else:
                if player.channel.id != interaction.user.voice.channel.id:
                    return
                
            if self.mode:
                player.queue.put(self.track)
            else:
                if player.playing:
                    player.queue.put(self.track)
                else:
                    await player.play(self.track)

        except (discord.Forbidden, discord.ClientException, Exception) as e:
            print(f"Error on music button callback! {e}")


class MenuForMusic(discord.ui.View):
    def __init__(self, tracks : list, mode : bool):
        super().__init__(timeout=60)
        self.tracks = tracks

        for id, track in enumerate(self.tracks):
            self.add_item(MusicButton(id, track, mode))

class Queue_View(discord.ui.View):
    def __init__(self, queue_list : list):
        super().__init__(timeout=180)
        self.queue = queue_list
        self.current_page = 0
        self.items_per_page = 10
        self.pages = ceil(len(queue_list) / self.items_per_page)

        self.update_buttons()

    def update_buttons(self):

        if(self.current_page == 0):
            self.children[0].disabled = True
        else:
            self.children[0].disabled = False

        if(self.current_page == self.pages-1):
            self.children[1].disabled = True
        else:
            self.children[1].disabled = False

    def create_embed(self):

        start = self.current_page * self.items_per_page
        end = start + self.items_per_page

        current_items = self.queue[start:end]

        embed = Embed(title="Songs in queue!")
        embed.set_footer(text=f"Page {self.current_page+1} of {self.pages}")

        for id, item in enumerate(current_items):
            embed.add_field(name=f"{id+1+start}. {item.title}", value=item.author, inline=False)

        return embed
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction : discord.Interaction, button : discord.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)


    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction : discord.Interaction, button : discord.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

        