from discord.ext import commands
import discord
from pymongo.errors import PyMongoError

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
    async def on_member_join(self, member):
        """
        Listen for member joining the guild and creates document for them in database if it doesn't already exists.

        Arguments:
            member (discord.Member): Member who just joined the guild.
        """
        try:
            member_in_database = await self.bot.database["users"].find_one({"_id" : str(member.id)})
            if member_in_database is None:
                await self.add_member_to_database(member)
        except PyMongoError as e:
            print(f"PyMongoError: {e}")

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
        try:
            guild_data = await self.bot.database["guilds"].find_one({"_id": guild_id})
            if guild_data is None:
                await self.add_guild_to_database(discord_Obj.guild)
                guild_data = await self.bot.database["guilds"].find_one({"_id": guild_id})
            return guild_data
        except PyMongoError as e:
            print(f"PyMongo error {e}")
            return None

    async def add_guild_to_database(self, guild):
        """
        Create document for guild in database.

        Arguments:
            guild (discord.guild): The guild to add.
        """
        try:
            await self.bot.database["guilds"].insert_one({
                    "_id": str(guild.id),
                    "name": guild.name,
                    "prefix": "?",
                    "welcome" : {
                        "enabled" : False,
                        "channel_id" : 0,
                        "message" : None
                    },
                    "leave" : {
                        "enabled" : False,
                        "channel_id" : 0,
                        "message" : None
                    },
                    "automod": {
                        "banned_words" : [
                            "ass","asshole","asshat","asswipe","assclown","assmonkey","assmunch","arse","arsehole","balls","ballbag",
                            "bastard","bastards","bitch","b1tch","bloody","bollocks","bollocking","bugger","butthead",
                            "child of a bitch","cock","cockface","cocksucker","cunt","cuntface","cuntmuffin",
                            "crap","damn","dick","d1ck","dickhead","dickwad","dipshit","dipshitface",
                            "dingleberry","dumbass","dumbfuck","fag","faggot","fatherless","fuck","fuckface","fubar","fucktard","freakingass","fck","m0therfucker",
                            "git","hell","idiot","idiotface","jerk","jackass","knob","knobhead","knucklehead",
                            "moron","numpty","numptyface","piss","prat","plonker","shit","sh1t","shithead","shitbag","shitbagger","shitface","shitstain","shitlicker",
                            "slut","son of a bitch","son of a whore","twat","twatwaffle","wanker","whore","daughter of a bitch","motherless","motherfucker","motherlover",
                            "pussy","a$$hole","wazzock","chav","clown","tosser","freakingass","assclown","asshat","jackass","shitbagger",
                            "dickmonger","cockmuncher","assmonkey","assmunch","twit","numskull","knobhead","gitface","bollocksed","idiotface",
                            "shithead","dipshitface","dumbfuck","fuckface","fucktard","twatwaffle","shitstain","prickface","cockface",
                            "cuntface","asswipe","asshat","butthead","dingleberry","dickwad","dipshit","fubar","fucktard","fuckhead",
                            "shithead","motherlover","twatwaffle","shitstain","prickface","cockface","cuntface","arsehole","bollocksed",
                            "gitface","knobhead","numptyface","dumbfuck","retard","idiotface","jackass","assclown","pussy","shitbagger",
                            "dipshitface","freakingass","assmonkey","assmunch","cockmuncher","cuntmuffin","dickmonger","shitlicker",
                            "fuk","fukk","fukking","shitt","sh1tt","bitchy","b!tch","d!ck","c0ck","c0cksucker","mothrfucker","assh0le","pissface",
                            "wh0re","c0ckface","d!ckhead","fag0t","f@g","f@ggot","c*nt","sh*t","b!tches","b!tched","d!ckwad",
                            "fatherless","motherless","son of a bitch","daughter of a bitch","motherfucker","son of a whore","child of a bitch",
                            "momless","dadless","parentless","familyless","orphan","orphaned",
                            "cretin","dunce","dumb","fool","idiotic","moronic","nincompoop","simpleton","twit","dope","loser","dork","nerd","weirdo",
                            "noob","n00b","lame","scrub","trash","rekt","sux","suxx","suck","loserface","pwned","fail","fml","omgwtf","wtf","omfg","stfu","gtfo",
                            "f@ck","sh!t","d!ck","b!tch","c*nt","a$$","@sshole","c0ck","f*ck","s#it","b@$tard","b@stard"
                            ],
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
        except PyMongoError as e:
            print(f"PyMongoError : {e}")

    async def disable_jail(self, discord_Obj):
        """
        Disable jail system for guild.

        Arguments:
            discord_Obj: Discord object (Interaction, Channel, Member, Message)
        """
        try:
            await self.bot.database["guilds"].update_one({"_id" : str(discord_Obj.guild.id)}, {"$set" : {"automod.jail.enabled" : False}})
        except PyMongoError as e:
            print(f"PyMongo error {e}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """
        Listen for bot joiningthe guild, then creates documents for guild in database if it doesn't exist.

        Arguments:
            guild (discord.guild): Guild data.
        """
        try:
            guild_in_database = await self.bot.database["guilds"].find_one({"_id" : str(guild.id)})

            if guild_in_database is None:
                await self.add_guild_to_database(guild)
        except PyMongoError as e:
            print(f"PyMongoError: {e}")

    async def find_or_create__member(self, discord_Obj):
        member_id = None
        if isinstance(discord_Obj, discord.Interaction):
            member_id = str(discord_Obj.user.id)
        elif isinstance(discord_Obj, discord.Member):
            member_id = str(discord_Obj.id)
        else:
            return None

        try:
            user_data = await self.bot.database["users"].find_one({"_id" : member_id})
            if user_data is None:
                await self.add_member_to_database(member_id)
                user_data = await self.bot.database["users"].find_one({"_id" : member_id})
            return user_data
        except PyMongoError as e:
            print(f"PyMongoError: {e}")
            return None

    async def add_member_to_database(self, member_id : int):
        try:
            await self.bot.database["users"].insert_one({
                "_id" : str(member_id),
                "coins" : 0,
                "xp" :  0,
                "level" : 1,
                "last_daily_reward" : None,
                "level_up_notification" : True,
                "pets" : {}
            })
        except PyMongoError as e:
            print(f"PyMongoError: {e}")
        
    async def check_instance(self, discord_Obj):
        pass

async def setup(bot):
    await bot.add_cog(Database(bot))     # Register the cog with the bot