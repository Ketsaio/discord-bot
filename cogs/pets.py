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
        return self.bot.get_cog("Database")
    
    async def get_member(self, discord_Obj):
        database_cog = await self.get_database_cog()
        member_data = await database_cog.find_or_create__member(discord_Obj)
        return member_data or {}

    async def unicorn(self, message : discord.Message):
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
                    embed = discord.Embed(
                        title="🦄 Unicorn activated!",
                        description=f"Here's your gif:",
                        color=discord.Colour.purple()
                    )
                    embed.set_image(url=gif_url)
                    await message.channel.send(embed=embed)
        
        await self.add_pet_xp(randint(1,5), message)

    async def parrot(self, message : discord.Message):
        to_repeat = message.content
        embed = discord.Embed(
            title="🦜 Parrot says:",
            description=f"***{to_repeat}***",
            color=discord.Colour.blue()
        )
        await message.channel.send(embed=embed)
        await self.add_pet_xp(randint(1,5), message)

    async def pet_selector(self, pet, message):
        if pet == "kitty":
            await self.add_pet_xp(randint(1,10), message)
        elif pet == "unicorn":
            await self.unicorn(message)
        elif pet == "parrot":
            await self.parrot(message)
        elif pet is None:
            return
        else:
            await self.add_pet_xp(randint(1,5), message)

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

        await self.bot.database["users"].update_one(
            {"_id" : str(message.author.id)}, 
            {"$inc" : {f"inventory.{current_pet}.xp" : int(xp)}}
        )

        member_data = await self.get_member(message.author)
        current_xp = member_data.get("inventory", {}).get(current_pet, {}).get("xp", 0)
        level = member_data.get("inventory", {}).get(current_pet, {}).get("level", 0)

        if current_xp >= (20 * level):
            await self.bot.database["users"].update_one(
                {"_id" : str(message.author.id)},
                {"$set" : {f"inventory.{current_pet}.xp" : 0},
                 "$inc" : {f"inventory.{current_pet}.level" : 1,
                           f"inventory.{current_pet}.def" : defence,
                           f"inventory.{current_pet}.atk" : attack}}
            )
            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"Your **{current_pet}** leveled up to **{level+1}**!",
                color=discord.Colour.green()
            )
            await message.channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message : discord.Message):
        if message.author.bot or not message.guild:
            return
        member_data = await self.get_member(message.author)
        active_pet = member_data.get("active_pet", 0)
        await self.pet_selector(active_pet, message)

    @app_commands.command(name="change_pet", description="Choose pet to level and fight for you!")
    @app_commands.describe(pet_name="Name of the pet you chose!")
    async def choose_active_pet(self, interaction : discord.Interaction, pet_name : str):
        member_data = await self.get_member(interaction)
        pets = member_data.get("inventory", {})

        if pet_name not in pets:
            embed = discord.Embed(
                title="❌ Pet not found",
                description="You don't have that pet!",
                color=discord.Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.bot.database["users"].update_one(
            {"_id" : str(interaction.user.id)},
            {"$set" : {"active_pet" : pet_name}}
        )
        embed = discord.Embed(
            title="✅ Active Pet Changed",
            description=f"Your active pet is now **{pet_name}**",
            color=discord.Colour.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Pets(bot))