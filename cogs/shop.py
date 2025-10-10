import discord
from discord.ext import commands
from discord import app_commands
from pymongo.errors import PyMongoError
import json
from functools import partial
from asyncio import sleep
from random import choice, randint

async def create_embed(title : str, desc : str, color: discord.Color, footer : str = ""):

    embed = discord.Embed(
        title=title,
        description=desc,
        color=color
    )

    embed.set_footer(text=footer)

    return embed


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
    
    async def get_jail_role(self, interaction : discord.Interaction):
        try:
            guild_data = await self.bot.database["guilds"].find_one({"_id" : str(interaction.guild_id)})

            if guild_data is None:
                return

            role_id = guild_data.get("automod", {}).get("jail", {}).get("jail_role", 0)

            jail_role = interaction.guild.get_role(role_id)

            return jail_role
        except discord.Forbidden:
            print(f"Cant open shop! (get_jail_role, ItemShop)")
        except discord.HTTPException:
            print("Something happend on line discord API - discord Bot, (get_jail_role, ItemShop)")
        except PyMongoError as e:
            print(f"PyMongoError: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    
    async def deduct_money(self, interaction : discord.Interaction, item):
        try:
            await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$inc" : {"coins" : item['cost'] * -1}})
        except PyMongoError as e:
            print(f"PyMongoError {e}")

    async def add_item_to_user_inv(self, interaction : discord.Interaction, item_key, item_data):
        try:
            await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$set": {f"inventory.{item_key}" : item_data}})
        except PyMongoError as e:
            print(f"PyMongoError {e}")

    async def tier_picker(self):
        x = randint(1, 1000)

        if x <= 650:
            return "common"
        elif x > 650 and x <= 800:
            return "rare"
        elif x > 800 and x <= 999:
            return "epic"
        else:
            return "legendary"
        
    async def color_picker(self, rarity : str):
        if rarity == "common":
            return discord.Color.green()
        elif rarity == "rare":
            return discord.Color.blue()
        elif rarity == "epic":
            return discord.Color.purple()
        elif rarity == "legendary":
            return discord.Color.gold()
        else:
            return discord.Color.red()
    
    async def lootbox(self, interaction : discord.Interaction, member_inv : dict):
        try:
            tier = await self.tier_picker()

            if not self.items:
                return

            items_in_tier = [{name : rest} for name, rest in self.items.items() if rest['rarity'] == tier]

            if not items_in_tier:
                return

            picked = choice(items_in_tier)
            key = next(iter(picked))

            if key not in member_inv:
                await self.add_item_to_user_inv(interaction, key, picked[key])
                message = f"{interaction.user.name} just dropped {picked[key]['emote']} **{key.capitalize()}**"
            else:
                how_much = randint(45, 125)
                await self.bot.database["users"].update_one({"_id" : str(interaction.user.id)}, {"$inc" : {"coins" : how_much}})
                message = f"{interaction.user.name} dropped {how_much} coins because he/she has {picked[key]['emote']} **{key.capitalize()}**"

            new_embed = await create_embed(message, f"*Congratulations!*", discord.Color.red())

            await interaction.response.send_message(embed=new_embed)
            await interaction.channel.send(interaction.user.mention)
        except discord.Forbidden:
            print(f"Cant open shop! (callback, ItemShop)")
        except discord.HTTPException:
            print("Something happend on line discord API - discord Bot, (callback, ItemShop)")
        except PyMongoError as e:
            print(f"PyMongoError: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    async def button_callback(self, interaction : discord.Interaction, chosen_item, chosen_label):
        try:
            member_data = await self.get_member(interaction)

            if member_data is None:
                return

            member_coins = member_data.get("coins", 0)
            member_inv = member_data.get("inventory", {})

            if member_coins < chosen_item['cost']:
                await interaction.response.send_message("**U don't have enough coins!**")
                return
            
            if chosen_label == "pet_lootbox":
                await self.deduct_money(interaction, chosen_item)
                await self.lootbox(interaction, member_inv)
                return

            if chosen_label == "unjail":

                jail_role = await self.get_jail_role(interaction)

                if jail_role in interaction.user.roles:
                    await interaction.user.remove_roles(jail_role)
                    await interaction.response.send_message("U are free!")
                    await self.deduct_money(interaction, chosen_item)
                else:
                    await interaction.response.send_message("U are not in jail!")
                return

            if chosen_label not in member_inv:
                await self.add_item_to_user_inv(interaction, chosen_label, chosen_item)
                await self.deduct_money(interaction, chosen_item)
                await interaction.response.send_message(f"U bought **{chosen_label}**")
            else:
                await interaction.response.send_message(f"*U already have this pet!*", ephemeral=True)
        except discord.Forbidden:
            print(f"Cant open shop! (callback, Shop)")
        except discord.HTTPException:
            print("Something happend on line discord API - discord Bot, (callback, Shop)")
        except Exception as e:
            print(f"Unexpected error: {e}")

    async def callback(self, interaction : discord.Interaction):
        chosen_label = self.values[0]

        if chosen_label not in self.items:
            return
        try:
            chosen_item = self.items[chosen_label]

            color = await self.color_picker(chosen_item['rarity'])

            new_embed = await create_embed(f"{chosen_item['emote']} **{chosen_label.capitalize()}**", f"*{chosen_item['desc']}*", color, f"Remember {chosen_label.capitalize()} costs {chosen_item['cost']} coins!!")

            button = discord.ui.Button(label="BUY", style=discord.ButtonStyle.primary)

            button.callback = partial(self.button_callback, chosen_item=chosen_item, chosen_label=chosen_label)

            new_view = discord.ui.View()
            new_view.add_item(button)

            await interaction.response.send_message(embed=new_embed, view=new_view)
        except discord.Forbidden:
            print(f"Cant open shop! (callback, Shop)")
        except discord.HTTPException:
            print("Something happend on line discord API - discord Bot, (callback, Shop)")
        except Exception as e:
            print(f"Unexpected error: {e}")

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
        try:
            embed = await create_embed("🏪 Item shop", "*Choose your item!* 🎁", discord.Color.gold(), f"Common - 🟢, rare - 🔵, epic - 🟣, legendary - 🟡")

            for name, item in self.shop_items.items():
                embed.add_field(
                    name=f"{item['emote']} **{name.capitalize()}** {item['rare_emote']}",
                    value=f"💰 {item['cost']} coins",
                    inline=True
                )
    
            view = ShopView(self.shop_items, self.bot)

            await interaction.response.send_message(embed=embed, view=view)
        except discord.Forbidden:
            print(f"Cant open shop! (shop command, Shop)")
        except discord.HTTPException:
            print("Something happend on line discord API - discord Bot, (shop command, Shop)")
        except Exception as e:
            print(f"Unexpected error: {e}")

async def setup(bot):
    await bot.add_cog(Shop(bot))