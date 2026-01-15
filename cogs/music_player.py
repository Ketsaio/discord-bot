import discord
from discord import Embed
from discord.ext import commands
from discord import app_commands
import wavelink
from dotenv import load_dotenv
from os import getenv
from .views import MenuForMusic
from typing import Literal


class Music_player(commands.Cog):
    def __init__(self, bot):

        self.bot = bot
        load_dotenv()
        self.passw = getenv("LAVALINK_CLIENT")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload : wavelink.TrackStartEventPayload):

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

        if member.id == self.bot.user.id:

            if before.channel is not None and after.channel is None:

                player : wavelink = member.guild.voice_client

                if player:
                    await player.stop()


    @app_commands.command(name="join", description="Joins your voice channel!")
    async def join(self, interaction : discord.Interaction):
        
        if await self.no_stealing(interaction):
            return

        await interaction.user.voice.channel.connect(cls=wavelink.Player)

        await interaction.response.send_message(f"I joined {interaction.user.voice.channel.mention}", delete_after=5)

    @app_commands.command(name="leave", description="Leaves your voice channel!")
    async def leave(self, interaction : discord.Interaction):

        if await self.no_stealing(interaction):
            return

        await interaction.guild.voice_client.disconnect()

        await interaction.response.send_message(f"I left {interaction.user.voice.channel.mention}", delete_after=5)

    @app_commands.command(name="skip", description="Skip current track!")
    async def skip(self, interaction : discord.Interaction):

        if await self.no_stealing(interaction):
            return

        player : wavelink = interaction.guild.voice_client

        await player.skip()

        await interaction.response.send_message(f"Skipped song!", delete_after=5)

    @app_commands.command(name="volume", description="Change volume of your music!")
    @app_commands.describe(volume="Needs to be in [1-100] range!")
    async def change_volume(self, interaction : discord.Interaction, volume : int):
        
        if await self.no_stealing(interaction):
            return

        if volume < 1 or volume > 100:
            await interaction.response.send_message("Volume must be in [1-100] radius!")
            return

        player : wavelink = interaction.guild.voice_client

        await player.set_volume(volume)

        await interaction.response.send_message(f"Volume is at {volume}%", delete_after=5)


    @app_commands.command(name="loop", description="Loop your song!")
    @app_commands.describe(mode="Mode of your loop! [OFF, SINGLE, PLAYLIST]")
    async def loop(self, interaction : discord.Interaction, mode: Literal["OFF", "SINGLE", "QUEUE"]):

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

        if(await self.no_stealing(interaction)):
            return
        
        await interaction.response.defer()

        player : wavelink = interaction.guild.voice_client

        if not player:
            return
        
        embed = Embed(title="Songs in queue!")

        for id, item in enumerate(player.queue):
            embed.add_field(name=f"{id+1}. {item.title}", value=item.author, inline=False)


        await interaction.followup.send(embed=embed)

    @app_commands.command(name="play", description="Play your favourite music!")
    @app_commands.describe(argument="Title/Author/Link to your song!")
    async def play(self, interaction : discord.Interaction, argument : str):

        await interaction.response.defer()

        if await self.no_stealing(interaction):
            return

        tracks = await wavelink.Playable.search(argument)  # poczytać dokumentacje o Playable i Playerze, bo to będę głównie obsługiwał!
        
        player : wavelink = interaction.guild.voice_client

        if(len(tracks) == 1):

            if not player:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)

            if not player.playing:
                await player.play(tracks[0])
            else:
                player.queue.put(tracks[0])

        else:

            mode = False

            if player and player.playing:       #Play - False, Queue - True
                mode = True

            await self.embed_for_songs(interaction, tracks, mode)

    async def cog_load(self):
        if not wavelink.Pool.nodes:
            node = wavelink.Node(
                uri="http://localhost:2333", 
                password=self.passw   # załadować passy z .env   
            )
            await wavelink.Pool.connect(nodes=[node], client=self.bot)
            print("Wavelink: Connected succefully!")

    async def embed_for_songs(self, interaction : discord.Interaction, tracks : list, mode : bool):

            embed = Embed(title="Choose your song!")
            emotes = [":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:", ":keycap_ten:"]

            tracks = tracks[:10]

            for i in range(10):
                embed.add_field(name=f"{emotes[i]} {tracks[i].title}", value=f"By: {tracks[i].author}", inline=False)
                
            await interaction.followup.send(embed=embed, view=MenuForMusic(tracks, mode)) # mode: False = Play | True = Queue

    async def no_stealing(self, interaction : discord.Interaction):
        player : wavelink = interaction.guild.voice_client

        if player and player.playing:
            if interaction.user.voice.channel.id != player.channel.id:
                await interaction.followup.send (f"Bot is playing music on {player.channel} voice channel!", ephemeral=True)
                return True
            
        return False


async def setup(bot):
    await bot.add_cog(Music_player(bot))