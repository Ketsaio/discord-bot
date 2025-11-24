import discord
from discord.ext import commands
from discord import app_commands
from random import randint, choice
import aiohttp
from os import getenv
from dotenv import load_dotenv

class Pets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        self.tenor = getenv("TENOR")

    async def get_database_cog(self):
        """
        Returns the Database cog instance.

        Returns:
            Database cog or None if cog is not loaded.
        """
        return self.bot.get_cog("Database")
    
    async def get_member(self, discord_Obj):
        """
        Retrieves guild data from database.

        Arguments:
            discord_Obj: Discord Object (Interaction, Member, Role or Channel).

        Returns:
            dict: Guild member_data dict or None is something went wrong.
        """
        database_cog = await self.get_database_cog()
        member_data = await database_cog.find_or_create__member(discord_Obj)
        if member_data is None:
            return None
        return member_data

    async def unicorn(self, message : discord.Message):
        #unicorn - gifs
        chance = randint(1,10)
        if chance >= 9:
            query = "spongebob"
            url = f"https://tenor.googleapis.com/v2/search?q={query}&key={self.tenor}&limit=30"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                if "results" in data and len(data["results"]) > 0:
                    result = choice(data["results"])
                    gif_url = result["media_formats"]["gif"]["url"]
                    await message.channel.send(gif_url)
        
        await self.add_pet_xp(randint(1,5), message)

    async def squid(self):
        #squid - illegal income
        pass

    async def parrot(self, message : discord.Message):
        #parrot - repeats sentences
        to_repeat = message.content
        await message.channel.send(content=f"🦜 ***{to_repeat}***")
        await self.add_pet_xp(randint(1,5), message)

    async def rat(self):
        #rat - legal income
        pass

    async def pet_selector(self, pet, message):
        if pet == "kitty":
            await self.add_pet_xp(randint(1,10), message)
        elif pet == "doggo":
            await self.doggo()
        elif pet == "unicorn":
            await self.unicorn(message)
        elif pet == "parrot":
            await self.parrot(message)
        elif pet is None:
            return
        else:
            await self.add_pet_xp(randint(1,5),message)

    async def get_current_pet(self, message : discord.Message):
        member_data = await self.get_member(message.author)
        return member_data.get("active_pet", None)

    async def add_pet_xp(self, xp : int, message : discord.Message):
        current_pet = await self.get_current_pet(message)

        if not current_pet:
            return

        defence, attack = 3, 5

        if current_pet == "dragon":
            defence, attack = 8, 12

        await self.bot.database["users"].update_one({"_id" : str(message.author.id)}, {"$inc" : {f"inventory.{current_pet}.xp" : int(xp)}})
        member_data = await self.get_member(message.author)
        current_xp = member_data.get("inventory", {}).get(current_pet, {}).get("xp", 0)
        level = member_data.get("inventory", {}).get(current_pet, {}).get("level", 0)
        if current_xp >= (20 * level):
            await self.bot.database["users"].update_one({"_id" : str(message.author.id)}, {"$set" : {f"inventory.{current_pet}.xp" : 0}, "$inc" : {f"inventory.{current_pet}.level" : 1, f"inventory.{current_pet}.def" : defence, f"inventory.{current_pet}.atk" : attack}})
            await message.channel.send(f"Your {current_pet} leveled up to {level+1} level!")




    @commands.Cog.listener()
    async def on_message(self, message : discord.Message):

        if message.author.bot:
            return

        if not message.guild:
            return

        message

        member_data = await self.get_member(message.author)
        active_pet = member_data.get("active_pet", 0)

        checker = await self.pet_selector(active_pet, message)

        if checker == 1:
            return
        



        #get_pet = member_data.get(f"inventory.{active_pet}", {})



        '''
        await self.bot.database["users"].update_one({"_id" : str(message.author.id)}, {"$inc" : {f"inventory.{active_pet}.xp" : given_xp}})
        member_data = await self.get_member(message.author)
        xp = member_data.get(f"inventory.{active_pet}.xp", 0)
        '''



    @app_commands.command(name = "change_pet", description="Choose pet to level and fight for u!")
    @app_commands.describe(pet_name = "Name of the pet u chose!")
    async def choose_active_pet(self, interaction : discord.Interaction, pet_name : str):
        member_data = await self.get_member(interaction)
        pets = member_data.get("inventory", {})

        if pet_name not in pets:
            await interaction.response.send_message("U dont have that pet!", ephemeral=True)
            return
        #await self.bot.database["users"].update_one({"_id" : str(message.author.id)}, {"$inc" : {"xp" : -10,"level" : 1}})
        await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$set" : {"active_pet" : pet_name}})
        await interaction.response.send_message(f"Your active pet is now **{pet_name}**", ephemeral=True)
        
async def setup(bot):
    await bot.add_cog(Pets(bot))