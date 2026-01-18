import discord
from discord import Embed
from discord.ext import commands
from discord import app_commands
import wavelink
from dotenv import load_dotenv
from os import getenv
from .views import MenuForMusic, Queue_View
from typing import Literal


class Music_player(commands.Cog):
    '''
    Cog responsible for playing music on voice channel, with commands like /play, /skip, /loop and queue.
    '''
    def __init__(self, bot):
        '''
        Initializes the Music_player cog.

        Arguments:
            bot: Discord bot instance.
        '''
        self.bot = bot
        load_dotenv()
        self.passw = getenv("LAVALINK_CLIENT")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload : wavelink.TrackEndEventPayload):
        '''
        Listen for song to end, if queue is not empty plays next track, else waits for new song to play.

        Arguments:
            payload (wavelink.TrackEndEventPayload): Event that appears on track end.
        '''

        player : wavelink = payload.player

        if not player:
            return

        try:
            next_track = player.queue.get()
            await player.play(next_track)
        except wavelink.QueueEmpty:
            pass
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member : discord.Member, before : discord.VoiceState, after : discord.VoiceState):
        '''
        Listens for members joining/leaving voice channel, if bot leaves the channel it disconnects from lavalink.

        Arguments:
            member (discord.Member): Needed for member id to verify if member is bot.
            before (discord.VoiceState): Voice channel state before someone joins/leaves.
            after (discord.VoiceState): Voice channel state after someone joins/leaves.
        '''
        if member.id == self.bot.user.id:

            if before.channel is not None and after.channel is None:

                player : wavelink = member.guild.voice_client

                if player:
                    await player.stop()


    @app_commands.command(name="join", description="Joins your voice channel!")
    async def join(self, interaction : discord.Interaction):
        '''
        Connects bot to your voice channel.

        Arguments:
            interaction (discord.Interaction): The interaction context.
        '''
        if await self.no_stealing(interaction):
            return

        await interaction.user.voice.channel.connect(cls=wavelink.Player)

        await interaction.response.send_message(f"I joined {interaction.user.voice.channel.mention}", delete_after=5)

    @app_commands.command(name="leave", description="Leaves your voice channel!")
    async def leave(self, interaction : discord.Interaction):
        '''
        Disconnects bot from your voice channel.

        Arguments:
            interaction (discord.Interaction): The interaction context.
        '''
        if await self.no_stealing(interaction):
            return

        await interaction.guild.voice_client.disconnect()

        await interaction.response.send_message(f"I left {interaction.user.voice.channel.mention}", delete_after=5)

    @app_commands.command(name="skip", description="Skip current track!")
    async def skip(self, interaction : discord.Interaction):
        '''
        Skips currently playing song.

        Arguments:
            interaction (discord.Interaction): The interaction context.
        '''
        if await self.no_stealing(interaction):
            return

        player : wavelink = interaction.guild.voice_client

        await player.skip()

        await interaction.response.send_message(f"Skipped song!", delete_after=5)

    @app_commands.command(name="volume", description="Change volume of your music!")
    @app_commands.describe(volume="Needs to be in [1-100] range!")
    async def change_volume(self, interaction : discord.Interaction, volume : int):
        '''
        Changes music volume.

        Arguments:
            interaction (discord.Interaction): The interaction context.
            volume (int): Volume in %.
        '''
        if await self.no_stealing(interaction):
            return

        if volume < 1 or volume > 100:
            await interaction.response.send_message("Volume must be in [1-100] range!")
            return

        player : wavelink = interaction.guild.voice_client

        await player.set_volume(volume)

        await interaction.response.send_message(f"Volume is at {volume}%", delete_after=5)


    @app_commands.command(name="loop", description="Loop your song!")
    @app_commands.describe(mode="Mode of your loop! [OFF, SINGLE, PLAYLIST]")
    async def loop(self, interaction : discord.Interaction, mode: Literal["OFF", "SINGLE", "QUEUE"]):
        '''
        Loops song you are listening to.

        Arguments:
            interaction (discord.Interaction): The interaction context.
            mode (Literal): Mode of your loop (OFF, single song, whole queue).
        '''
        if await self.no_stealing(interaction):
            return

        player : wavelink = interaction.guild.voice_client

        if not player:
            return
        
        if mode == "OFF":
            player.queue.mode = wavelink.QueueMode.normal
        elif mode == "SINGLE":
            player.queue.mode = wavelink.QueueMode.loop
        elif mode == "QUEUE":
            player.queue.mode = wavelink.QueueMode.loop_all

        await interaction.response.send_message(f"Queue is now in {mode} mode!", delete_after=5)

    @app_commands.command(name="show_queue", description="Look into your queue!")
    async def show_queue(self, interaction : discord.Interaction):
        '''
        Generates embed with songs in queue, divided into pages.

        Arguments:
            interaction (discord.Interaction): The interaction context.

        Sends:
            Embed with queue.
        '''

        if await self.no_stealing(interaction):
            return

        await interaction.response.defer()

        player : wavelink = interaction.guild.voice_client

        if not player:
            return
        
        view = Queue_View(list(player.queue))

        embed = view.create_embed()
        
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="play", description="Play your favourite music!")
    @app_commands.describe(argument="Title/Author/Link to your song!")
    async def play(self, interaction : discord.Interaction, argument : str):
        '''
        Music player core mechanism. If song is already playing, adds to queue.

        Arguments:
            interaction (discord.Interaction): The interaction context.
            argument (str): Link/Title/Author of the song.
        '''
        await interaction.response.defer()

        if await self.no_stealing(interaction):
            return

        try:
            tracks = await wavelink.Playable.search(argument)
        except wavelink.LavalinkLoadException as e:
            print(f"Lavalink error: {e}")


        player : wavelink = interaction.guild.voice_client

        if(len(tracks) == 1):
            try:
                if not player:
                    player = await interaction.user.voice.channel.connect(cls=wavelink.Player)

                if not player.playing:
                    await player.play(tracks[0])
                else:
                    player.queue.put(tracks[0])
            except (discord.Forbidden, discord.ClientException, Exception) as e:
                print(f"Error on music button callback! {e}")

        else:

            mode = False

            if player and player.playing:       #Play - False, Queue - True
                mode = True

            await self.embed_for_songs(interaction, tracks, mode)

    async def cog_load(self):
        '''
        Loads wavelink node.
        '''
        try:
            node = wavelink.Node(
                uri="http://localhost:2333", 
                password=self.passw   # załadować passy z .env   
            )
            await wavelink.Pool.connect(nodes=[node], client=self.bot)
            print("Wavelink: Connected succefully!")
        except wavelink.InvalidNodeException as e:
            print(f"Node error on connect, exiting! | {e}")
            exit()

    async def embed_for_songs(self, interaction : discord.Interaction, tracks : list, mode : bool):
            '''
            Generates embed menu for choosing songs.

            Arguments:
                interaction (discord.Interaction): The interaction context.
                tracks (list): List of found tracks.
                mode (bool): Queue mode (play song or add song to queue).

            Sends:
                Menu in embed, with songs assigned to buttons.
            '''
            embed = Embed(title="Choose your song!")
            emotes = [":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:", ":keycap_ten:"]

            tracks = tracks[:10]

            for i, track in enumerate(tracks):
                embed.add_field(name=f"{emotes[i]} {track.title}", value=f"By: {track.author}", inline=False)

            await interaction.followup.send(embed=embed, view=MenuForMusic(tracks, mode)) # mode: False = Play | True = Queue

    async def no_stealing(self, interaction : discord.Interaction):
        '''
        Checks if user is in the same channel as bot.

        Arguments:
            interaction (discord.Interaction): The interaction context.

        Returns:
            bool: True, if user is not in the same channel, else False.
        '''
        player : wavelink = interaction.guild.voice_client
        try:   
            if not interaction.user.voice:
                msg = "Join channel to use me!"
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
                return True

            if player and player.playing:
                if interaction.user.voice.channel.id != player.channel.id:

                    msg = f"Bot is playing music on {player.channel} voice channel!"

                    if interaction.response.is_done():
                        await interaction.followup.send(msg, ephemeral=True)
                    else:
                        await interaction.response.send_message(msg, ephemeral=True)
                    return True
                
            return False
        except discord.Forbidden as e:
                print(f"Cant send message! {e}")


async def setup(bot):
    await bot.add_cog(Music_player(bot))