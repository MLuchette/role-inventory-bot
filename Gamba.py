import os
import random
import json
import datetime
import discord
from discord import app_commands
from discord.ext import commands
import db
from dotdict import dotdict

# load the loot table according to the environment
env = os.getenv('BOT_ENV')
file = 'loot_table.json' if env == 'prod' else 'loot_table.test.json'
with open(file, encoding='utf8') as stream:
    loot_table = json.load(stream)
loot_table = dotdict(loot_table)

# cooldown in seconds
gamba_cooldown = 600

# make a losing roll
def lose_roll():
    emotes = ['🍒', '🌈', '🍎', '🍋', '💎', '💰', '🍀']
    result_str = '🍒🍒🍒'
    while result_str[0] == result_str[1] and result_str[1] == result_str[2]:
        result_str = ' | '.join(random.choice(emotes) for i in range(3))

    return result_str

# quick and dirty epoch timestamp
def timestamp():
    now = datetime.datetime.now()
    return int(round(now.timestamp()))

class Gamba(commands.Cog):
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.server = discord.Object(id=config.server)
        self.bot.tree.add_command(self.gamba, guild=self.server)

    @app_commands.command(name='gamba', description='Open for a chance at a rare role!')
    async def gamba(self, interaction):
        # check last slot for user from database
        last_pull = db.get_last_slot_pull(interaction.user.id)
        # fake it if there's no entry
        if not last_pull: last_pull = {"datestamp": timestamp()-700}

        # cooldown, now - then < cooldown
        if (timestamp() - int(last_pull['datestamp']) < gamba_cooldown):
            await interaction.response.send_message('Still cooling down from your last spin!', ephemeral=True)
            return

        # roll a random number,
        # loop through the loot table and find the rarest reward hit
        award = None
        roll = random.randrange(1,1000001)
        for loot in loot_table.keys():
            if roll <= loot_table[loot]['chance']:
                award = loot

        # save the timestamp for the cooldown
        db.save_slot_pull(interaction.user.id, timestamp())

        # Create a pretty embed
        embed = discord.Embed(
            color=discord.Color.blue(),
            title='Rock Slots!'
        )
        # embed.set_footer(text=roll) # for debug to show the roll
        # fancy thumbnail to look nice
        embed.set_thumbnail(url='https://media.discordapp.net/attachments/772018609610031104/1193726070474678343/image.png')

        if not award:
            # no win, show only to user who spun
            embed.description = f'{lose_roll()}\n\nBetter luck next time!'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # won, show publicly
            embed.description = f'{loot_table[award]["spin"]}\n\nYou won the {award} role!'
            if roll == 1:
                # rarest spin gets a different message
                embed.description += f' I didn\'t even know that was possible!!'
            await interaction.response.send_message(embed=embed)

        # oh yeah give the user the role
        await interaction.user.add_roles(discord.Object(id=loot_table[award]['role']))

    async def cog_unload(self):
        """this gets called if the cog gets unloaded, remove commands from tree"""
        self.bot.tree.remove_command('gamba', guild=self.server)