import discord
import io
from datetime import datetime
from discord import Embed
from asyncio import sleep
from discord.ui import DynamicItem, TextInput, Modal
import wavelink
from math import ceil
from random import randint

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
        '''
        Creates a button linked to song.

        Arguments:
            id (int): Number of song.
            track (wavelink.Playable): Track that will be played after interaction.
            mode (bool): Decides if play right now or add to queue.
        '''
        super().__init__(
            label=str(id + 1),
            style=discord.ButtonStyle.primary,
            row=id // 5
        )
        self.track = track
        self.mode = mode

    async def callback(self, interaction : discord.Interaction):
        '''
        On button click plays chosen song or adds it to the queue.

        Arguments:
            interaction (discord.Interaction): The interaction context.
        '''

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
        '''
        Initializes buttons for song choosing menu.

        Arguments:
            tracks (list): List of track that will be linked to each button.
            mode (bool): Decides if play right now or add to queue.
        '''
        super().__init__(timeout=60)
        self.tracks = tracks

        for id, track in enumerate(self.tracks):
            self.add_item(MusicButton(id, track, mode))

class Queue_View(discord.ui.View):
    def __init__(self, queue_list : list):
        '''
        Initializes the view for queue.

        Arguments:
            queue_list (list): List of songs in queue.
        '''
        super().__init__(timeout=180)
        self.queue = queue_list
        self.current_page = 0
        self.items_per_page = 10
        self.pages = ceil(len(queue_list) / self.items_per_page)

        self.update_buttons()

    def update_buttons(self):
        '''
        Updates button on changing page. If page is first/last corresponding button is disabled.
        '''
        if(self.current_page == 0):
            self.children[0].disabled = True
        else:
            self.children[0].disabled = False

        if(self.current_page == self.pages-1):
            self.children[1].disabled = True
        else:
            self.children[1].disabled = False

    def create_embed(self):
        '''
        Creates embed with 10 songs from queue, divided into pages that you can move between.

        Returns:
            "Interactive" embed.
        '''
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page

        current_items = self.queue[start:end]

        embed = Embed(title="Songs in queue!")
        embed.set_footer(text=f"Page {self.current_page+1} of {self.pages}")

        for id, item in enumerate(current_items):
            embed.add_field(name=f"{id+1+start}. {item.title}", value=item.author, inline=False)

        return embed
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction : discord.Interaction, button : discord.ui.Button):
        '''
        Button responsible for changing pages (backward).

        Arguments:
            interaction (discord.Interaction): The interaction context.
            button (discord.ui.Button): Button that was clicked.
        '''
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)


    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction : discord.Interaction, button : discord.ui.Button):
        '''
        Button responsible for changing pages (forward).

        Arguments:
            interaction (discord.Interaction): The interaction context.
            button (discord.ui.Button): Button that was clicked.
        '''
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

class AcceptView(discord.ui.View):

    def __init__(self, members : list):
        '''
        Initializes the view for accepting challenge.

        Arguments:
            members (list): List containing two fighters.
        '''
        super().__init__(timeout=None)
        self.members = members

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

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept_button(self, interaction : discord.Interaction, button : discord.ui.Button):
        '''
        Creates an accept button used to accept challenge.
        If interacted with, it prepares everything needed to battle and edits the original embed.

        Arguments:
            interaction (discord.Interaction): The interaction context.
            button (discord.ui.Button): Button that was clicked.
        '''
        if interaction.user.id != self.members[1].id:
            await interaction.response.send_message("It's not your battle!", ephemeral=True)
            return

        try:
            self.bot = interaction.client

            data1 = await self.get_member(self.members[0])
            data2 = await self.get_member(self.members[1])

            player1 = BattlePlayer(self.members[0], data1)
            player2 = BattlePlayer(self.members[1], data2)

            embed = Embed(title="Challenge was accepted!", description=f"{self.members[1].mention}, pick your move!", color=discord.Colour.red())

            await interaction.response.edit_message(embed=embed, view=BattleView([player1, player2]))

        except discord.Forbidden as e:
            print(f"I cant do that!\n{e}")

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny_button(self, interaction : discord.Interaction, button : discord.ui.Button):
        '''
        Creates a deny button used to deny chellenge.
        If interacted with it removes the buttons and stops the view.
        Arguments:
            interaction (discord.Interaction): The interaction context.
            button (discord.ui.Button): Button that was clicked.

        '''
        if interaction.user.id != self.members[1].id:
            await interaction.response.send_message("It's not your battle!", ephemeral=True)
            return
            
        try:
            embed = Embed(title="What a coward...", description=f"{self.members[1].mention} has denied {self.members[0].mention} challenge!", color=discord.Colour.dark_gray())

            await interaction.response.edit_message(embed=embed, view=None)

            self.stop()

        except discord.Forbidden as e:
            print(f"I cant do that!\n{e}")


class BattleView(discord.ui.View):
    def __init__(self, players : list):
        '''
        Initializes BattleView used for battle sequence.
        
        Arguments:
            players (list): List with two BattlePlayer objects.
        '''
        super().__init__(timeout=None)
        self.members = players

        self.turn = 1;
        self.curr_playing = self.members[self.turn].member_id

    async def update_buttons(self, interaction : discord.Interaction):
        '''
        Function responsible for changing turns and end the game.

        Arguments:
            interaction (discord.Interaction): The interaction context.
        '''
        try:
            self.turn = not self.turn
            self.curr_playing = self.members[self.turn].member_id

            victory_message = "The challenge was won by "
            end = False

            if(self.members[0].pet_hp <= 0):
                victory_message += self.members[1].member_name
                end = True
            elif(self.members[1].pet_hp <= 0):
                victory_message += self.members[0].member_name
                end = True

            if(end):
                victory_message += ", congratulations!"
                embed = Embed(title="BATTLE HAS COME TO AN END!", description=victory_message, color=discord.Colour.green())

                await interaction.response.edit_message(embed=embed, view=None)

                self.stop()
                return False
            return True
        
        except discord.Forbidden as e:
            print(f"I cant do that!\n{e}")
    
    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger)
    async def normal_attack(self, interaction : discord.Interaction, button : discord.ui.Button):
        '''
        Creates a button responsible for attack move, deducting hp from opponent and editing original embed.

        Arguments:
            interaction (discord.Interaction): The interaction context.
            button (discord.ui.Button): Button that was clicked.
        '''
        if interaction.user.id != self.curr_playing:
            await interaction.response.send_message("Its not your turn yet!")
            return
        try:
            damage_to_deal = self.members[self.turn].pet_atk

            self.members[not self.turn].receive_damage(damage_to_deal)


            embed = Embed(title="BATTLE!", description=f"{self.members[self.turn].member_name}s {self.members[self.turn].pet_name} dealt {damage_to_deal} to {self.members[not self.turn].member_name}s {self.members[not self.turn].pet_name}", color=discord.Colour.red())

            embed.add_field(name=f"Current hp of {self.members[0].member_name} pet:", value=self.members[0].pet_hp, inline=False)
            embed.add_field(name=f"Current hp of {self.members[1].member_name} pet:", value=self.members[1].pet_hp, inline=False)
            
            state = await self.update_buttons(interaction)

            if(state):
                await interaction.response.edit_message(embed=embed, view=self)

        except discord.Forbidden as e:
            print(f"I cant do that!\n{e}")

    @discord.ui.button(label="Healing", style=discord.ButtonStyle.danger)
    async def healing(self, interaction : discord.Interaction, button : discord.ui.Button):
        '''
        Button responible for healing action, adding hp to player pet and editing the original embed.

        Arguments:
            interaction (discord.Interaction): The interaction context.
            button (discord.ui.Button): Button that was clicked.
        '''
        if interaction.user.id != self.curr_playing:
            await interaction.response.send_message("Its not your turn yet!")
            return

        try:
            embed = Embed(title="BATTLE", description=f"{self.members[self.turn].member_name}s {self.members[self.turn].pet_name} healed for {self.members[self.turn].regen()}", color=discord.Colour.green())

            embed.add_field(name=f"Current hp of {self.members[0].member_name} pet:", value=self.members[0].pet_hp, inline=False)
            embed.add_field(name=f"Current hp of {self.members[1].member_name} pet:", value=self.members[1].pet_hp, inline=False)
            
            state = await self.update_buttons(interaction)

            if(state):
                await interaction.response.edit_message(embed=embed, view=self)

        except discord.Forbidden as e:
            print(f"I cant do that!\n{e}")

class BattlePlayer:
    def __init__(self, member : discord.Member, data_from_db : dict):
        '''
        Initializes the BattlePlayer instance.

        Arguments:
            member (discord.Member): Member data from discord.
            data_from_db (dict): Member data from database.
        '''
        self.member_id = member.id
        self.member_name = member.name
        self.pet_name = data_from_db.get("active_pet", 0)
        self.pet_hp = 100
        self.pet_atk = data_from_db.get("inventory", {}).get(self.pet_name, {}).get("atk", 0)
        self.pet_def = data_from_db.get("inventory", {}).get(self.pet_name, {}).get("def", 0)

    def id(self):
        '''
        Method responsible for returning member id.

        Returns:
            member_id (int): Member id.
        '''
        return self.member_id

    def receive_damage(self, damage : int):
        '''
        Method responsible for receiving damage, deducts calculated hp from pet.
        '''
        multipli = randint(0,5)
        multipli /= 10
        multipli += 1

        self.pet_hp -= int(damage * multipli // (self.pet_def * 0.05))

    def regen(self):
        '''
        Method responsible for regenerating your pet health.
        '''
        healed_for = randint(10,20)

        self.pet_hp += healed_for

        if self.pet_hp > 100:
            self.pet_hp = 100

        return healed_for