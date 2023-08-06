import asyncio
from datetime import date
from glob import glob
import sys
import os

import discord
from discord.ext import tasks, commands


class dump(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @tasks.loop(hours=24, reconnect=True)
    async def dump(self):
        print('Removing old files...')
        today = date.today().strftime('%m.%d.%Y')
        for file in glob('data.*.db'):
            if today not in file:
                os.remove(file)
        for file in glob('regions.*.xml.gz'):
            if today not in file:
                os.remove(file)
        print('Generating daily V20XX database...')
        executable = './V20XX.exe' if os.name == 'nt' else './V20XX'
        process = await asyncio.create_subprocess_exec(executable, '-n', 'scarabbot')
        stdout, stderr = await process.communicate()
        if stdout:
            print(stdout.decode())
        if stderr:
            print(stderr.decode(), file=sys.stderr)
        print('Database generated!')

    @commands.command(aliases=["dump"])
    @discord.app_commands.checks.has_any_role(
        "command"
    )  # Needs Update Command Role!
    async def start_dump(self, ctx):
        self.dump.start()  # This simply starts the above "dump" loop - which runs once a day to maintain
        # a XML file of the newest daily dump! (Could also set it to be done at a certain time each day if needed,
        # unsure if required atm though)

'''
    @commands.command()
    @discord.app_commands.checks.has_role("command")
    async def check_update(self, ctx):
'''

async def setup(bot):
    await bot.add_cog(dump(bot))
