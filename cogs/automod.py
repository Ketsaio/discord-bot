from pymongo import MongoClient
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
import asyncio

class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @app_commands.command(name = "clear", description = "Clear given amount of messages")
    @app_commands.describe(amount = "How much messages to clear")
    async def delete_messages(self, interaction: discord.Interaction, amount : int = 1):

        await interaction.response.defer(ephemeral=True, thinking=True)

        older, newer = await self.categorize_messages(interaction, amount)

        deleted_newer = await interaction.channel.purge(limit=len(newer))
        
        for message in older:
            await message.delete()
            await asyncio.sleep(0.6)

        deleted_messages = len(deleted_newer) + len(older)

        await interaction.followup.send(f"Cleared {deleted_messages} messages!", ephemeral=True)

    async def create_jail_utilities(self, interaction : discord.Interaction) -> tuple:
        jail_role = await interaction.guild.create_role(name = "Jail", permissions=discord.Permissions.none(), color=discord.Colour.dark_gray(), hoist=True, mentionable=True)

        overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                jail_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, use_application_commands=True)
            }  
        
        for chan in interaction.guild.channels:
                await chan.set_permissions(jail_role, overwrite=discord.PermissionOverwrite(view_channel=False))

        jail_category = await interaction.guild.create_category(name="Jail", overwrites=overwrites, reason="Category for jailed people")
        jail_text = await interaction.guild.create_text_channel(name="jail-chat", category=jail_category, reason="Here jailed people can text")
        jail_vc = await interaction.guild.create_voice_channel(name="Jail Voice", category=jail_category, reason="Here jailed people can talk")

        return jail_role, jail_category, jail_text, jail_vc

    async def find_guild(self, discord_Obj) -> dict:
        if isinstance(discord_Obj, discord.Interaction):
            return self.bot.database["guilds"].find_one({"_id"  : str(discord_Obj.guild_id)})
        elif isinstance(discord_Obj, discord.abc.GuildChannel) or isinstance(discord_Obj, discord.Role):
            return self.bot.database["guilds"].find_one({"_id"  : str(discord_Obj.guild.id)})
        else:
            return

    async def is_jail_enabled(self, guild_data : dict) -> bool:
        return guild_data["automod"]["jail"]["enabled"]

    async def jail_disable(self, discord_Obj):
        await self.bot.database["guilds"].update_one({"_id" : str(discord_Obj.guild.id)}, {"$set" : {"automod.jail.enabled" : False}})

    async def get_jail_role(self, guild_data : dict, discord_Obj) -> discord.Role:
        role_id = guild_data["automod"]["jail"]["jail_role"]
        return discord_Obj.guild.get_role(role_id) 

    @app_commands.command(name = "jail_setup", description = "Prepares jail channel and role for jail command (can take a while if u have many channels)")
    async def setup_jail(self, interaction : discord.Interaction):

        await interaction.response.defer(ephemeral=True, thinking=True)

        guild_data = await self.find_guild(interaction)

        if guild_data and not await self.is_jail_enabled(guild_data):

            jail_role, jail_category, jail_text, jail_vc = await self.create_jail_utilities(interaction)

            await self.bot.database["guilds"].update_one({"_id" : str(interaction.guild_id)}, {"$set" : {"automod.jail.enabled" : True, "automod.jail.jail_role" : jail_role.id, "automod.jail.jail_category" : jail_category.id, "automod.jail.jail_text" : jail_text.id, "automod.jail.jail_vc" : jail_vc.id}})

            await interaction.followup.send("Jail has been created", ephemeral=True)
        else:
            return

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role : discord.Role):
        guild_data = await self.find_guild(role)

        if guild_data and guild_data["automod"]["jail"]["jail_role"] == role.id:
            await self.jail_disable(role)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel : discord.abc.GuildChannel):
        guild_data = await self.find_guild(channel)

        if guild_data and (guild_data["automod"]["jail"]["jail_text"] == channel.id or guild_data["automod"]["jail"]["jail_vc"] == channel.id):
            await self.jail_disable(channel)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel : discord.abc.GuildChannel):
        guild_data = await self.find_guild(channel)

        if await self.is_jail_enabled(guild_data):
            jail_role = await self.get_jail_role(guild_data, channel)
            await channel.set_permissions(jail_role, overwrite=discord.PermissionOverwrite(view_channel=False))

    @app_commands.command(name = "jail", description = "Send to jail or let them out")
    @app_commands.describe(member = "Person that will be send to jail")
    async def jail(self, interaction : discord.Interaction, member : discord.Member):

        guild_data = await self.find_guild(interaction)

        if not await self.is_jail_enabled(guild_data):
            await interaction.response.send_message("U didnt setup jail or u deleted jail role/channel/category, please use /jail_setup to setup jail again", ephemeral=True)

        jail_role = await self.get_jail_role(guild_data, interaction)

        if jail_role in member.roles:
            await member.remove_roles(jail_role)
            await interaction.response.send_message(f"{member.name} has been unjailed", ephemeral=True)
        else:
            await member.add_roles(jail_role)
            await interaction.response.send_message(f"{member.name} has been jailed", ephemeral=True)

    @app_commands.command(name="ban", description = "Bans user")
    async def ban(self, interaction : discord.Interaction, member : discord.Member):    # to add: deleted days and reason

        await member.ban()
        await interaction.response.send_message(f"{member.name} has been banned!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Automod(bot))