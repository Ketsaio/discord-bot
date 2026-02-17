from discord.ext import commands
import discord
import logging

logger = logging.getLogger(__name__)

class Database(commands.Cog):
    """
    Cog responsible for any action in database including retrieving, 
    updating and creating new documents.
    """
    def __init__(self, bot):
        """
        Initializes Database cog.

        Arguments:
            bot: Discord bot instance.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member : discord.Member) -> None:
        """
        Listen for member joining the guild and creates document for them in database if it doesn't already exists.

        Arguments:
            member (discord.Member): Member who just joined the guild.
        """
        member_in_database = await self.bot.database["users"].find_one({"_id" : str(member.id)})
        if member_in_database is None:
            await self.add_member_to_database(member)

    async def find_or_create_guild(self, discord_Obj) -> dict:
        """
        Retrieve guild data from database. If guild document dont exist, creates it.

        Arguments:
            discord_Obj: Discord object (Interaction, Channel, Member, Message)

        Returns:
            dict: Guild data document from database or None if error occured.
        """

        guild_id = None
        if isinstance(discord_Obj, discord.Interaction):
            guild_id = str(discord_Obj.guild_id)
        elif isinstance(discord_Obj, (discord.abc.GuildChannel, discord.Role, discord.Member, discord.Message)):
            guild_id = str(discord_Obj.guild.id)
        else:
            return None
        guild_data = await self.bot.database["guilds"].find_one({"_id": guild_id})
        if guild_data is None:
            await self.add_guild_to_database(discord_Obj.guild)
            guild_data = await self.bot.database["guilds"].find_one({"_id": guild_id})
        return guild_data

    async def add_guild_to_database(self, guild : discord.Guild) -> None:
        """
        Create document for guild in database.

        Arguments:
            guild (discord.guild): The guild to add.
        """
        await self.bot.database["guilds"].insert_one({
                "_id": str(guild.id),
                "name": guild.name,
                "prefix": "?",
                "welcome" : {
                    "enabled" : False,
                    "channel_id" : 0,
                    "message" : None,
                    "description" : None
                },
                "leave" : {
                    "enabled" : False,
                    "channel_id" : 0,
                    "message" : None,
                    "description" : None
                },
                "automod": {
                    "banned_words" : [],
                    "anti_bad_words" : False,
                    "jail" : {
                        "enabled" : False,
                        "jail_role" : None,
                        "jail_category" : None,
                        "jail_text" : None,
                        "jail_vc" : None
                    }
                },
                "item_shop" : {
                    "piece of paper" : 100
                }
            })

    async def disable_jail(self, discord_Obj) -> None:
        """
        Disable jail system for guild.

        Arguments:
            discord_Obj: Discord object (Interaction, Channel, Member, Message)
        """

        await self.bot.database["guilds"].update_one({"_id" : str(discord_Obj.guild.id)}, {"$set" : {"automod.jail.enabled" : False}})


    @commands.Cog.listener()
    async def on_guild_join(self, guild : discord.Guild) -> None:
        """
        Listen for bot joining the guild, then creates documents for guild in database if it doesn't exist.

        Arguments:
            guild (discord.Guild): Guild data.
        """
        guild_in_database = await self.bot.database["guilds"].find_one({"_id" : str(guild.id)})

        if guild_in_database is None:
            await self.add_guild_to_database(guild)

    async def find_or_create__member(self, discord_Obj) -> dict:
        """
        Finds or creates members in database.

        Arguments:
            discord_Obj: Discord object (Interaction, Channel, Member, Message).

        Returns:
            dict: Member data document from database or None if error occured.
        """
        member_id = None
        if isinstance(discord_Obj, discord.Interaction):
            member_id = str(discord_Obj.user.id)
        elif isinstance(discord_Obj, discord.Member):
            member_id = str(discord_Obj.id)
        else:
            return None

        user_data = await self.bot.database["users"].find_one({"_id" : member_id})
        if user_data is None:
            await self.add_member_to_database(member_id)
            user_data = await self.bot.database["users"].find_one({"_id" : member_id})
        return user_data

    async def add_member_to_database(self, member_id : int) -> None:
        """
        Add member to database.

        Arguments:
            member_id (int): Id of the discord member.
        """
        await self.bot.database["users"].update_one({
            "_id" : str(member_id),
            "coins" : 0,
            "xp" :  0,
            "level" : 1,
            "cooldowns" : {
                "last_daily_reward" : None,
                "last_crime" : None,
                "last_steal" : None
            },
            "level_up_notification" : True,
            "inventory" : {},
            "active_pet" : None
        },
        upsert = True
        )

async def setup(bot):
    await bot.add_cog(Database(bot))