from discord.ext import commands
from discord import app_commands, Embed
import discord

class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.title = "**NEW MEMBER APPEARED**"
        self.description = "{mention} **just joined the server!\nWelcome them warmly!**"

    async def get_database_cog(self):
        """
        Returns the Database cog instance.

        Returns:
            Database cog or None if cog is not loaded.
        """
        return self.bot.get_cog("Database")

    async def get_guild(self, discord_Obj) -> dict:
        """
        Retrives guild data from database.

        Arguments:
            discord_Obj: Discord Object (Interaction, Member, Role or Channel).

        Returns:
            dict: Guild data dict or None is something went wrong.
        """
        database_cog = await self.get_database_cog()
        if not database_cog:
            return None
    
        guild_data = await database_cog.find_or_create_guild(discord_Obj)
        if guild_data is None:
            return None
        return guild_data

    @commands.Cog.listener()
    async def on_member_join(self, member : discord.Member):
        
        guild_data = await self.get_guild(member)
        welcome_settings = guild_data.get("welcome", {})


        if(not welcome_settings.get("enabled", False)):
            return
        
        if(member.id == self.bot.user.id):
            return
        
        if(not welcome_settings.get("message")):
            title = self.title
        else:
            title = welcome_settings.get("message")

        if(not welcome_settings.get("description")):
            embed_desc = self.description
        else:
            embed_desc = welcome_settings.get("description")

        embed_desc = embed_desc.replace("{mention}", member.mention)

        embed = Embed(title=title, description=embed_desc, color=discord.Colour.random())

        embed.set_image(url=member.display_avatar.url)

        channel_id = welcome_settings.get("channel_id")

        if(not channel_id):
            return

        channel = member.guild.get_channel(channel_id)

        await channel.send(embed=embed)

    @app_commands.command(name="turn_welcome_messages", description="Turn on/off welcome messages for this discord server!")
    async def turn_welcome(self, interaction : discord.Interaction):

        guild_data = await self.get_guild(interaction)
        welcome_state = guild_data.get("welcome", {}).get("enabled")

        await self.bot.database["guilds"].update_one({"_id" : str(interaction.guild_id)}, {"$set" : {"welcome.enabled" : not welcome_state}})

        await interaction.response.send_message(f"Welcome messages are now {'enabled' if not welcome_state else 'disabled'}!")

    @app_commands.command(name="welcome_messages_setup", description="Setup everything needed for welcome messages!")
    @app_commands.describe(channel_name="Channel name", title="Your custom title of welcome message embed!", desc="Your desc, {mention} will mention member!")
    async def setup_wm(self, interaction : discord.Interaction, channel_name : discord.TextChannel, title : str = "", desc : str = ""):


        if(not channel_name):
            await interaction.response.send_message("Wrong channel name!", ephemeral=True)
            return

        update = {"welcome.channel_id" : channel_name.id, "welcome.enabled" : True}

        if(title):
            update["welcome.message"] = title
        if(desc):
            update["welcome.description"] = desc

        await self.bot.database["guilds"].update_one({"_id" : str(interaction.guild_id)}, {"$set" : update})

        await interaction.response.send_message("Welcome messages are ready to welcome!", ephemeral=True)
    

async def setup(bot):
    await bot.add_cog(Welcome(bot))