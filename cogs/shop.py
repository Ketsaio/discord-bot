import discord
from discord.ext import commands
from discord import app_commands
from pymongo.errors import PyMongoError
import json
from functools import partial
from asyncio import sleep
from random import choice, randint

class ItemShop(discord.ui.Select):
    def __init__(self, shop_items: dict, bot):

        self.bot = bot

        self.items = shop_items

        options = [discord.SelectOption(label=name, description=item['desc'], emoji=item['emote']) for name, item in shop_items.items()]

        super().__init__(placeholder="Choose your item!", min_values=1, max_values=1, options=options)

    async def get_database_cog(self):
        return self.bot.get_cog("Database")
    
    async def get_member(self, discord_Obj):
        database_cog = await self.get_database_cog()
        member_data = await database_cog.find_or_create__member(discord_Obj)
        if member_data is None:
            return None
        return member_data
    
    async def lootbox(self, interaction : discord.Interaction, member_inv : discord.Member):

        embed = discord.Embed(
            title="🎰🎰🎰",
            description="*Jackpot this time!*",
            color=discord.Color.red()
        )

        tier = ["common", "rare", "epic", "legendary"]

        x = randint(1, 1000)

        if x <= 650:
            tier = "common"
        elif x > 650 and x <= 800:
            tier = "rare"
        elif x > 800 and x <= 999:
            tier = "epic"
        else:
            tier = "legendary"

        items_in_tier = [{name : rest} for name, rest in self.items.items() if rest['rarity'] == tier]
        picked = choice(items_in_tier)
        key = next(iter(picked))

        if key not in member_inv:
            await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$set": {f"inventory.{key}" : picked[key]}})
            message = f"{interaction.user.name} just dropped {picked[key]['emote']}**{key.capitalize()}**"
        else:
            how_much = randint(45, 125)
            await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$inc" : {"coins" : how_much}})
            message = f"{interaction.user.name} dropped {how_much} coins because he/she has ***{key}*** {[picked[key]['emote']]}"

        new_embed = discord.Embed(
            title=message,
            description=f"*Congratulations!*",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=new_embed)
        await interaction.channel.send(interaction.user.mention)

    async def callback(self, interaction : discord.Interaction):
        chosen_label = self.values[0]
        
        chosen_item = self.items[chosen_label]

        if chosen_item['rarity'] == "common":
            color = discord.Color.green()
        elif chosen_item['rarity'] == "rare":
            color = discord.Color.blue()
        elif chosen_item['rarity'] == "epic":
            color = discord.Color.purple()
        elif chosen_item['rarity'] == "legendary":
            color = discord.Color.gold()
        else:
            color = discord.Color.red()

        new_embed = discord.Embed(
            title = f"{chosen_item['emote']} **{chosen_label.capitalize()}**",
            description = f"*{chosen_item['desc']}*",
            color=color
        )

        button = discord.ui.Button(label="BUY", style=discord.ButtonStyle.primary)

        async def button_callback(interaction : discord.Interaction, chosen_item, chosen_label):
            member_data = await self.get_member(interaction)

            member_coins = member_data.get("coins", {})
            member_inv = member_data.get("inventory", {})

            if member_coins < chosen_item['cost']:
                await interaction.response.send_message("**U don't have enought coins!**")
                return
            
            if chosen_label == "pet_lootbox":
                await self.lootbox(interaction, member_inv)
                await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$inc" : {"coins" : chosen_item['cost'] * -1}})
                return

            if chosen_label == "unjail":

                guild_data = await self.bot.database["guilds"].find_one({"_id" : str(interaction.guild_id)})

                role_id = guild_data.get("automod", {}).get("jail", {}).get("jail_role", {})

                jail_role = interaction.guild.get_role(role_id)

                if jail_role in interaction.user.roles:
                    await interaction.user.remove_roles(jail_role)
                    await interaction.response.send_message("U are free!")
                    await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$inc" : {"coins" : chosen_item['cost'] * -1}})
                else:
                    await interaction.response.send_message("U are not in jail!")
                return

            if chosen_label not in member_inv:
                await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$set": {f"inventory.{chosen_label}": chosen_item}, "$inc" : {"coins" : chosen_item['cost'] * -1}})
                await interaction.response.send_message(f"U bought **{chosen_label}**")
            else:
                await interaction.response.send_message(f"*U already have this pet!*", ephemeral=True)


        button.callback = partial(button_callback, chosen_item=chosen_item, chosen_label=chosen_label)

        new_view = discord.ui.View()
        new_view.add_item(button)

        new_embed.set_footer(text=f"Remeber {chosen_label.capitalize()} costs {chosen_item['cost']} coins!!")

        await interaction.response.send_message(embed=new_embed, view=new_view)

        

class ShopView(discord.ui.View):
    def __init__(self, shop_items : dict, bot):
        super().__init__(timeout=60)
        self.bot = bot
        self.add_item(ItemShop(shop_items, bot))

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open ("data/shop.json", "r", encoding="utf-8") as shop_file:
            self.shop_items = json.load(shop_file)

    
    @app_commands.command(name="shop", description="Check shop for items")
    async def shop(self, interaction : discord.Interaction):
        embed = discord.Embed(
            title="🏪 Item shop",
            description="*Choose your item!* 🎁",
            color=discord.Color.gold()
        )

        for name, item in self.shop_items.items():
            embed.add_field(
                name=f"{item['emote']} **{name.capitalize()}** {item['rare_emote']}",
                value=f"💰 {item['cost']} coins",
                inline=True
            )


        view = ShopView(self.shop_items, self.bot)

        embed.set_footer(text=f"Common - 🟢, rare - 🔵, epic - 🟣, legendary - 🟡")

        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Shop(bot))