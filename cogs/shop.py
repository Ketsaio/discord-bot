import discord
from discord.ext import commands
from discord import app_commands
from random import randint
from pymongo.errors import PyMongoError
from datetime import datetime, timedelta, timezone
import json

class ItemShop(discord.ui.Select):
    def __init__(self, shop_items: dict):

        self.items = shop_items

        options = [discord.SelectOption(label=name, description=item['desc'], emoji=item['emote']) for name, item in shop_items.items()]

        super().__init__(placeholder="Choose your item!", min_values=1, max_values=1, options=options)

    async def callback(self, interaction : discord.Interaction):
        chosen_label = self.values[0]
        
        chosen_item = self.items[chosen_label]

        if chosen_item['rarity'] == "common":
            color = discord.Color.green()
        elif chosen_item['rarity'] == "rare":
            color = discord.Color.blue()
        elif chosen_item['rarity'] == "epic":
            color = discord.Color.pink()
        elif chosen_item['rarity'] == "legendary":
            color = discord.Color.gold()

        new_embed = discord.Embed(
            title = f"{chosen_item['emote']} **{chosen_label.capitalize()}**",
            description = f"*{chosen_item['desc']}*",
            color=color
        )

        button = discord.ui.Button(label="BUY", style=discord.ButtonStyle.primary)

        async def button_callback(interaction : discord.Interaction):
            await interaction.response.send_message(f"U bought {chosen_label} ✅")

        button.callback = button_callback

        new_view = discord.ui.View()
        new_view.add_item(button)

        new_embed.set_footer(text=f"Remeber {chosen_label.capitalize()} costs {chosen_item['cost']} coins!!")

        await interaction.response.send_message(embed=new_embed, view=new_view, ephemeral=True)

        

class ShopView(discord.ui.View):
    def __init__(self, shop_items : dict):
        super().__init__(timeout=60)
        self.add_item(ItemShop(shop_items))

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


        view = ShopView(self.shop_items)

        embed.set_footer(text=f"Common - 🟢, rare - 🔵, epic - 🟣, legendary - 🟡")

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))