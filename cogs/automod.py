import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
import asyncio
from pymongo.errors import PyMongoError

class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_banned_words = {}

    async def safe_add_role(self, member: discord.Member, role: discord.Role):
        if not role:
            return
        try:
            if member.top_role >= role.guild.me.top_role:
                return
            await member.add_roles(role)
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def safe_remove_role(self, member: discord.Member, role: discord.Role):
        if not role:
            return
        try:
            await member.remove_roles(role)
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def get_banned_words(self, guild_id):
        if guild_id in self.guild_banned_words:
            return self.guild_banned_words[guild_id]

        guild_data = await self.get_guild(guild_id)

        if guild_data is None:
            return set()

        words_set = set(guild_data.get("automod", {}).get("banned_words", []))

        self.guild_banned_words[guild_id] = words_set
        return words_set

    async def categorize_messages(self, interaction : discord.Interaction, amount : int) -> tuple:
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
        try:
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
        except discord.Forbidden:
            print("Can't create jail utilities (create_jail_utilities, Automod)")
            return None
        except discord.HTTPException:
            print("Something happend on line discord API - discord Bot, (create_jail_utilities, Automod)")
            return None

    async def get_database_cog(self):
        return self.bot.get_cog("Database")

    async def get_guild(self, discord_Obj) -> dict:
        database_cog = await self.get_database_cog()
        if not database_cog:
            return None
    
        guild_data = await database_cog.find_or_create_guild(discord_Obj)
        if guild_data is None:
            return None
        return guild_data

    async def is_jail_enabled(self, guild_data : dict) -> bool:
        return guild_data.get("automod", {}).get("jail", {}).get("enabled", False)

    async def jail_disable(self, discord_Obj):
        database_cog = await self.get_database_cog()
        if not database_cog:
            return None

        guild_data = await self.get_guild(discord_Obj)
        if guild_data is None:
            return None
        await database_cog.disable_jail(discord_Obj)

    async def get_jail_role(self, guild_data : dict, discord_Obj) -> discord.Role:
        role_id = guild_data.get("automod", {}).get("jail", {}).get("jail_role")
        if not role_id:
            return 
        return discord_Obj.guild.get_role(role_id) 

    @commands.Cog.listener()
    async def on_message(self, message : discord.Message):

        if not message.guild:
            return

        banned_words = await self.get_banned_words(message.guild.id)
        words = [w.strip(".,!?") for w in message.content.lower().split()]
        try:
            if any(word in banned_words for word in words):
                await message.delete()
                await message.author.send(f"Please dont swear {message.author.mention}, word from your sentence is prohibited on ***{message.guild.name}***")
        except discord.Forbidden:
            print("Bot dont have permission to delete messagess/cant send message to user, (on_message, Automod)")
        except discord.HTTPException:
            print("Something happend on line discord API - discord Bot, (on_message, Automod)")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role : discord.Role):
        guild_data = await self.get_guild(role)

        if guild_data is None:
            return

        if guild_data and guild_data["automod"]["jail"]["jail_role"] == role.id:
            await self.jail_disable(role)

    @commands.Cog.listener() 
    async def on_guild_channel_delete(self, channel : discord.abc.GuildChannel):
        guild_data = await self.get_guild(channel)

        if guild_data is None:
            return

        if guild_data and (guild_data["automod"]["jail"]["jail_text"] == channel.id or guild_data["automod"]["jail"]["jail_vc"] == channel.id):
            await self.jail_disable(channel)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel : discord.abc.GuildChannel):

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

        if not (interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!", ephemeral=True)
            return
        
        if not (interaction.guild.me.guild_permissions.manage_messages or interaction.guild.me.guild_permissions.administrator):
            await interaction.response.send_message("I dont have permissions to do that!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            older, newer = await self.categorize_messages(interaction, amount)

            deleted_newer = await interaction.channel.purge(limit=len(newer))
            
            for message in older:
                await message.delete()
                await asyncio.sleep(0.6)

            deleted_messages = len(deleted_newer) + len(older)

            await interaction.followup.send(f"Cleared {deleted_messages} messages!", ephemeral=True)
        except discord.Forbidden:
            print("Can't delete messages, (delete_messages, Automod)")
        except discord.HTTPException:
            print("Something happend on line discord API - discord Bot, (delete_messages, Automod)")

    @app_commands.command(name = "jail_setup", description = "Prepares jail channel and role for jail command (can take a while if u have many channels)")
    async def setup_jail(self, interaction : discord.Interaction):

        if not (interaction.user.guild_permissions.manage_channels or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!")
            return
        
        if not (interaction.guild.me.guild_permissions.manage_channels or interaction.guild.me.guild_permissions.administrator):
            await interaction.response.send_message("I dont have permissions to do that!")
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
                    try:
                        await self.bot.database["guilds"].update_one({"_id" : str(interaction.guild_id)}, {"$set" : {"automod.jail.enabled" : True, "automod.jail.jail_role" : jail_role.id, "automod.jail.jail_category" : jail_category.id, "automod.jail.jail_text" : jail_text.id, "automod.jail.jail_vc" : jail_vc.id}})
                    except PyMongoError as e:
                        print(f"PymongoError (setup_jail, Automod): {e}")

                    await interaction.followup.send("Jail has been created", ephemeral=True)
        else:
            return

    @app_commands.command(name = "jail", description = "Send to jail or let them out")
    @app_commands.describe(member = "Person that will be send to jail")
    async def jail(self, interaction : discord.Interaction, member : discord.Member):

        if not (interaction.user.guild_permissions.manage_roles or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!")
            return
        
        if not (interaction.guild.me.guild_permissions.manage_roles or interaction.guild.me.guild_permissions.administrator):
            await interaction.response.send_message("I dont have permissions to do that!")
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
            await interaction.response.send_message(f"{member.name} has been unjailed", ephemeral=True)
        else:
            await self.safe_add_role(member, jail_role)
            await interaction.response.send_message(f"{member.name} has been jailed", ephemeral=True)

    @app_commands.command(name="ban", description = "Bans user")
    async def ban(self, interaction : discord.Interaction, member : discord.Member):    # to add: deleted days and reason

        if not (interaction.user.guild_permissions.ban_members or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!")
            return
        
        if not (interaction.guild.me.guild_permissions.ban_members or interaction.guild.me.guild_permissions.administrator):
            await interaction.response.send_message("I dont have permissions to do that!")
            return

        try:
            await member.ban()
            await interaction.response.send_message(f"{member.name} has been banned!", ephemeral=True)
        except discord.Forbidden:
            print("Can't ban member, (ban, Automod)")
        except discord.HTTPException:
            print("Something happend on line discord API - discord Bot, (ban, Automod)")

    @app_commands.command(name="timeout", description = "Timeout user")
    @app_commands.describe(member = "Person to timeout", time = "How much time? (in minutes)")
    async def timeout(self, interaction : discord.Interaction, member : discord.Member, time : int = 10):

        if not (interaction.user.guild_permissions.moderate_members or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("U dont have permissions to do that!")
            return
        
        if not (interaction.guild.me.guild_permissions.moderate_members or interaction.guild.me.guild_permissions.administrator):
            await interaction.response.send_message("I dont have permissions to do that!")
            return
        
        try:
            if member.communication_disabled_until is not None:
                await member.edit(communication_disabled_until = None)
                await interaction.response.send_message(f"{member.name} can speak again")
            else:
                await member.edit(communication_disabled_until = datetime.now(timezone.utc) + timedelta(minutes=time))
                await interaction.response.send_message(f"{member.name} has been timeouted")
        except discord.Forbidden:
            print("Can't timeout member, (timeout, Automod)")
        except discord.HTTPException:
            print("Something happend on line discord API - discord Bot, (timeout, Automod)")

    

async def setup(bot):
    await bot.add_cog(Automod(bot))