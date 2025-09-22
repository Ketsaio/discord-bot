from pymongo import MongoClient
from dotenv import load_dotenv
from discord.ext import commands

class Database(commands.Cog):
    def __init__(self, bot):        #initializing Cog
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):

        collection = self.bot.database["users"]

        if not collection.find_one({"_id" : member.id}):   # Create user document if doesn't exist
            collection.insert_one({
                "_id" : member.id,
                "name" : member.name,
                "coins" : 0,
                "xp" :  0,
                "level" : 1,
                "last_daily_reward" : None,
                "level_up_notification" : True
            })



    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        collection = self.bot.database["guilds"]

        if not collection.find_one({"_id" : guild.id}):     # Create guild document if doesn't exist
            collection.insert_one({
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
                    "banned_words" : [],
                    "anti_link" : False,
                    "anti_spam" : False,
                    "muted_role" : None,
                    "jail_role" : None
                },
                "economy": {
                    "daily_coins" : 100,
                    "coins_name" : "$"
                },
                "levelSystem": {
                    "xp_per_message" : 5,
                }
            })
        
async def setup(bot):
    await bot.add_cog(Database(bot))     # Register the cog with the bot