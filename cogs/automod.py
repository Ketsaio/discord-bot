import discord
from discord.ext import commands
from discord import app_commands, Embed
from datetime import datetime, timedelta, timezone
import asyncio
import re
import logging

logger = logging.getLogger(__name__)


class Automod(commands.Cog):
    """
    Cog responsible for automoderation features, including banned words detection,
    jail setup and management, message clearing, bans, and timeouts.
    """
    def __init__(self, bot):
        """
        Initializes the Automod cog.

        Arguments:
            bot: Discord bot instance.
        """
        self.bot = bot
        self.guild_banned_words = {}

    async def safe_add_role(self, member: discord.Member, role: discord.Role):
        """
        Adds a role to a member safely, without raising permission errors.

        Arguments:
            member (discord.Member): The member to add roles to.
            role (discord.Role): Role to add to member.
        """
        if not role:
            return
        
        if member.top_role >= role.guild.me.top_role:
            return
        await member.add_roles(role)

    async def safe_remove_role(self, member: discord.Member, role: discord.Role):
        """
        Removes a role from a member safely, without raising permission errors.

         Arguments:
            member (discord.Member): The member to removes role from.
            role (discord.Role): Role to remove from member.
        """
        if not role:
            return
        
        await member.remove_roles(role)

    async def get_banned_words(self, discord_Obj):
        """
        Retrieves a set of banned words for a guild.

        Arguments:
            discord_Obj: Discord Object (Interaction, Member, Role or Channel).

        Returns:
            set: A set of banned words in the guild.
        """

        if discord_Obj in self.guild_banned_words:
            return self.guild_banned_words[discord_Obj]

        guild_data = await self.get_guild(discord_Obj)

        if guild_data is None:
            return set()

        words_set = set(guild_data.get("automod", {}).get("banned_words", []))

        self.guild_banned_words[discord_Obj] = words_set
        return words_set

    async def categorize_messages(self, interaction : discord.Interaction, amount : int) -> tuple:
        """
        Categorizes messages into older than 14 days and newer.

        Arguments:
            interaction (discord.Interaction): The interaction context.
            amount (int): Amount of messages to categorize.

        Returns:
            tuple: Two lists of messages (older, newer).
        """
        older = []
        newer = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        async for message in interaction.channel.history(limit=amount):
            if message.created_at < cutoff:
                older.append(message)
            else:
                newer.append(message)
        
        return older, newer      

    async def create_jail_utilities(self, interaction : discord.Interaction) -> tuple:
        """
        Creates utilities for jail: jail role, jail category, and jail text and voice channels.

        Arguments:
            interaction (discord.Intreaction): The interaction context.

        Returns:
            tuple: Every jail utility needed, (jail_role, jail_category, jail_text, jail_vc) or None if something goes wrong.
        """
        jail_role = await interaction.guild.create_role(name = "Jail", permissions=discord.Permissions.none(), color=discord.Colour.dark_gray(), hoist=True, mentionable=True)

        overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                jail_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, use_application_commands=True)
            }  
        
        for chan in interaction.guild.channels:
                await chan.set_permissions(jail_role, overwrite=discord.PermissionOverwrite(view_channel=False))
                await asyncio.sleep(0.1)

        jail_category = await interaction.guild.create_category(name="Jail", overwrites=overwrites, reason="Category for jailed people")
        jail_text = await interaction.guild.create_text_channel(name="jail-chat", category=jail_category, reason="Here jailed people can text")
        jail_vc = await interaction.guild.create_voice_channel(name="Jail Voice", category=jail_category, reason="Here jailed people can talk")

        return jail_role, jail_category, jail_text, jail_vc

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

    async def is_jail_enabled(self, guild_data : dict) -> bool:
        """
        Checks if jail is enabled in database.

        Arguments:
            guild_data (dict): Guild data from database.

        Returns:
            bool: If jail is enabled return True, otherwise returns False.
        """
        return guild_data.get("automod", {}).get("jail", {}).get("enabled", False)

    async def jail_disable(self, discord_Obj):
        """
        Disables jail in guild.

        Arguments:
            discord_Obj: Discord Object (Interaction, Member, Role or Channel).
        """
        database_cog = await self.get_database_cog()
        if not database_cog:
            return None

        guild_data = await self.get_guild(discord_Obj)
        if guild_data is None:
            return None
        await database_cog.disable_jail(discord_Obj)

    async def get_jail_role(self, guild_data : dict, discord_Obj) -> discord.Role:
        """
        Retrives jail role for a guild.

        Arguments:
            guild_data (dict): Guild data from database.
            discord_Obj: Discord Object (Interaction, Member, Role or Channel).

        Returns:
            discord.Role: Jail role or None if role id is missing.
        """
        role_id = guild_data.get("automod", {}).get("jail", {}).get("jail_role")
        if not role_id:
            return 
        return discord_Obj.guild.get_role(role_id) 

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listen for any message send, then checks if its a guild banned word.

        Arguments:
            message (discord.Message): Message sent in guild channel.
        """

        if message.author.bot:
            return

        if not message.guild:
            return
        
        guild_data = await self.get_guild(message)

        is_enabled = guild_data.get("automod", {}).get("anti_bad_words")

        if not is_enabled:
            return

        banned_words = await self.get_banned_words(message)
        if not banned_words:
            return

        words = re.findall(r'\b\w+\b', message.content.lower())

        if any(word in banned_words for word in words):
            await message.delete()
            await message.author.send(f"Please don't swear {message.author.mention}, a word from your sentence is prohibited on ***{message.guild.name}***")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role : discord.Role):
        """
        Listen for jail role deletion.

        Arguments:
            role (discord.Role): Role deleted from guild.
        """
        guild_data = await self.get_guild(role)

        if guild_data is None:
            return

        if guild_data and guild_data["automod"]["jail"]["jail_role"] == role.id:
            await self.jail_disable(role)

    @commands.Cog.listener() 
    async def on_guild_channel_delete(self, channel : discord.abc.GuildChannel):
        """
        Listen for jail voice/text channel delete.

        Arguments:
            channel (discord.abc.GuildChannel): Channel deleted from guild.
        """
        guild_data = await self.get_guild(channel)

        if guild_data is None:
            return

        if guild_data and (guild_data["automod"]["jail"]["jail_text"] == channel.id or guild_data["automod"]["jail"]["jail_vc"] == channel.id):
            await self.jail_disable(channel)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel : discord.abc.GuildChannel):
        """
        Listen for channel create. If jail is enabled sets permissions accordingly.

        Arguments:
            channel (discord.abc.GuildChannel): Channel that was created.
        """
        if not (channel.guild.me.guild_permissions.manage_roles or channel.guild.me.guild_permissions.administrator):
            return

        guild_data = await self.get_guild(channel)

        if guild_data is None:
            return

        if await self.is_jail_enabled(guild_data):
            jail_role = await self.get_jail_role(guild_data, channel)
            await channel.set_permissions(jail_role, overwrite=discord.PermissionOverwrite(view_channel=False))

    @app_commands.command(name = "clear", description = "Clear given amount of messages")
    @app_commands.describe(amount = "How much messages to clear")
    async def delete_messages(self, interaction: discord.Interaction, amount : int = 1):
        """
        Delete a set amount of messages.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            amount (int): Amount of messages to delete (if none given, defaults to 1).
        """

        if not (interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        older, newer = await self.categorize_messages(interaction, amount)

        deleted_newer = await interaction.channel.purge(limit=len(newer))
        
        for message in older:
            deleted_count = 0
            try:
                await message.delete()
                await asyncio.sleep(0.6)
                deleted_count += 1
                if deleted_count % 5 == 0:
                    await asyncio.sleep(2)
                else:
                    await asyncio.sleep(0.4)
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = e.retry_after
                    logger.warning(f"Rate limited! Sleeping for {retry_after}")
                    await asyncio.sleep(retry_after)
                else:
                    break

        deleted_messages = len(deleted_newer) + len(older)

        await interaction.followup.send(f"Cleared {deleted_messages} messages!", ephemeral=True)

    @app_commands.command(name = "jail_setup", description = "Prepares jail channel and role for jail command (can take a while if u have many channels)")
    async def setup_jail(self, interaction : discord.Interaction):
        """
        Creates category, text and voice channel, and role for jail.
        
        Arguments:
            interaction (discord.Interaction): Context interaction.
        """

        if not (interaction.user.guild_permissions.manage_channels or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!", ephemeral=True)
            return
        

        await interaction.response.defer(ephemeral=True, thinking=True)

        guild_data = await self.get_guild(interaction)

        if guild_data and not await self.is_jail_enabled(guild_data):
                result = await self.create_jail_utilities(interaction)

                if not result:
                    await interaction.followup.send("Can't create jail role/category/text/vc", ephemeral=True)
                    return

                jail_role, jail_category, jail_text, jail_vc = result

                database_cog = await self.get_database_cog()
                if database_cog:
                    await self.bot.database["guilds"].update_one({"_id" : str(interaction.guild_id)}, {"$set" : {"automod.jail.enabled" : True, "automod.jail.jail_role" : jail_role.id, "automod.jail.jail_category" : jail_category.id, "automod.jail.jail_text" : jail_text.id, "automod.jail.jail_vc" : jail_vc.id}})

                    await interaction.followup.send("Jail has been created", ephemeral=True)
        else:
            await interaction.response.send_message("Jail is set!")
            return

    @app_commands.command(name = "jail", description = "Send to jail or let them out")
    @app_commands.describe(member = "Person that will be send to jail")
    async def jail(self, interaction : discord.Interaction, member : discord.Member):
        """
        Send chosen member to jail. If member is in jail already, its will unjail them.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            member (discord.Member): Member who will be send to jail.
        """

        if not (interaction.user.guild_permissions.manage_roles or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!", ephemeral=True)
            return

        guild_data = await self.get_guild(interaction)

        if guild_data is None:
            return

        if not await self.is_jail_enabled(guild_data):
            await interaction.response.send_message("U didnt setup jail or u deleted jail role/channel/category, please use /jail_setup to setup jail again", ephemeral=True)
            return

        jail_role = await self.get_jail_role(guild_data, interaction)

        if jail_role in member.roles:
            await self.safe_remove_role(member, jail_role)

            embed = Embed(title="**⛓️ JAIL TIME**", description=f"**{member.mention} HAS BEEN REALESED!**", color=discord.Color.dark_blue())

            await interaction.response.send_message(embed=embed)
        else:
            await self.safe_add_role(member, jail_role)

            embed = Embed(title="**⛓️ JAIL TIME**", description=f"**{member.mention} HAS BEEN SENT TO JAIL!**", color=discord.Color.dark_blue())
            
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description = "Bans user")
    async def ban(self, interaction : discord.Interaction, member : discord.Member):    # to add: deleted days and reason
        """
        Ban chosen member.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            member (discord.Member): Member who will be banned.
        """

        if not (interaction.user.guild_permissions.ban_members or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!", ephemeral=True)
            return

        await member.ban()
        
        embed = Embed(title="**🔨 BAN HAMMER **", description=f"**{member.mention} HAS BEEN BANNED!**", color=discord.Color.red())

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="timeout", description = "Timeout user")
    @app_commands.describe(member = "Person to timeout", time = "How much time? (in minutes)")
    async def timeout(self, interaction : discord.Interaction, member : discord.Member, time : int = 10):
        """
        Times out a chosen member.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            member (discord.Member): Member who will be timed out.
            time (int): Timeout duration in minutes (default is 10).
        """
        if not (interaction.user.guild_permissions.moderate_members or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!", ephemeral=True)
            return
        
        if member.is_timed_out():
            await member.timeout(None)

            embed = Embed(title="**🔇 MUTE INCOMING**", description=f"**{member.mention} HAS BEEN UNMUTED!**", color=discord.Color.dark_grey())

            await interaction.response.send_message(embed=embed)
        else:
            await member.timeout(datetime.now(timezone.utc) + timedelta(minutes=time))

            embed = Embed(title="**🔇 MUTE INCOMING**", description=f"**{member.mention} HAS BEEN MUTED FOR {time} MINUTES!**", color=discord.Color.dark_grey())

            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="add_to_bad_words", description="Adds word to banned words in guild")
    @app_commands.describe(bad_word="Bad word that will be banned from this guild")
    async def add_bad_word(self, interaction : discord.Interaction, bad_word : str):
        """
         Add or remove a bad word from the guild's banned list.

        Arguments:
            interaction (discord.Interaction): Context interaction.
            bad_word (str): Word that will be prohibited in the guild.
        """

        if not (interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        guild_data = await self.get_guild(interaction)
        if guild_data is None:
            return

        banned_words = set(guild_data.get("automod", {}).get("banned_words", []))

        if bad_word.lower() in banned_words:
            await self.bot.database["guilds"].update_one(
                {"_id": str(interaction.guild_id)},
                {"$pull": {"automod.banned_words": bad_word.lower()}}
            )
            action = "removed"
        else:
            await self.bot.database["guilds"].update_one(
                {"_id": str(interaction.guild_id)},
                {"$addToSet": {"automod.banned_words": bad_word.lower()}}
            )
            action = "added"
        if interaction.guild_id in self.guild_banned_words:
            self.guild_banned_words.pop(interaction.guild_id)
        await interaction.followup.send(f"{bad_word} has been {action}")
        
    @app_commands.command(name="check_messages_for_bad_words", description="Enable/disable checking every message for potential bad words")
    async def check_bool_bad_words(self, interaction : discord.Interaction):
        """
        Check if deleting bad words is enabled

        Arguments:
            interaction (discord.Interaction): Context interaction.
        """
        if not (interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!", ephemeral=True)
            return
        
        guild_data = await self.get_guild(interaction)

        is_enabled = guild_data.get("automod", {}).get("anti_bad_words")

        if not is_enabled:
            await self.bot.database["guilds"].update_one({"_id" : str(interaction.guild_id)}, {"$set" : {"automod.anti_bad_words" : True}})
            await interaction.response.send_message("Scanning for bad words in this guild!")
        else:
            await self.bot.database["guilds"].update_one({"_id" : str(interaction.guild_id)}, {"$set" : {"automod.anti_bad_words" : False}})
            await interaction.response.send_message("Scanning turned off.")

async def setup(bot):
    await bot.add_cog(Automod(bot))