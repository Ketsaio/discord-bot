from discord.ext import commands
import discord
from pymongo.errors import PyMongoError

class Database(commands.Cog):
    def __init__(self, bot):        #initializing Cog
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):

        collection = await self.bot.database["users"]

        if not await collection.find_one({"_id" : member.id}):   # Create user document if doesn't exist
            await collection.insert_one({
                "_id" : str(member.id),
                "name" : member.name,
                "coins" : 0,
                "xp" :  0,
                "level" : 1,
                "last_daily_reward" : None,
                "level_up_notification" : True
            })

    async def find_or_create_guild(self, discord_Obj) -> dict:
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
                        "anti_link" : False,
                        "anti_spam" : False,
                        "muted_role" : None,
                        "jail" : {
                            "enabled" : False,
                            "jail_role" : None,
                            "jail_category" : None,
                            "jail_text" : None,
                            "jail_vc" : None
                        }
                    },
                    "levelSystem": {
                        "xp_per_message" : 5,
                    }
                })
        except PyMongoError as e:
            print(f"PyMongoError : {e}")

    async def disable_jail(self, discord_Obj):
        try:
            await self.bot.database["guilds"].update_one({"_id" : str(discord_Obj.guild.id)}, {"$set" : {"automod.jail.enabled" : False}})
        except PyMongoError as e:
            print(f"PyMongo error {e}")


    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        collection = await self.bot.database["guilds"]

        if not await collection.find_one({"_id" : str(guild.id)}):     # Create guild document if doesn't exist
            await self.add_guild_to_database(guild)
        
async def setup(bot):
    await bot.add_cog(Database(bot))     # Register the cog with the bot