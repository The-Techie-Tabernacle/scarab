import discord
from discord.ext import commands
from dbh import dbh
import os
import logging
import aiohttp

from cogs.chooser import chooser


class main_class(commands.Bot):
    def __init__(self):
        # Basic bot stuff, sets the bot to send me logs as well as creates the Activity, sets Intents as well as
        # loads the token via text file
        with open(
            "token.txt", "r"
        ) as fp:  
            self.token = (
                fp.read().strip()
            ) 
        logging.basicConfig(level=logging.INFO)
        intents = discord.Intents.all()
        super().__init__(command_prefix=".", intents=intents)
        self.database = dbh()

        # HTTP interactions are performed by the brainstem
        #self.session = aiohttp.ClientSession(
        #    headers={
        #        "User-Agent": "AUTO Bot accessing for common nation API, devved by nation=scottiesland"
        #    }
        #)
        #self.api_url = "https://www.nationstates.net/cgi-bin/api.cgi"

    # Load all cogs in the cogs folder and starts the "timely" loop(yoinked from Aav <3)
    async def setup_hook(self):
        # NOT COGS - DO NOT TRY TO LOAD
        blacklist = ["backbrain.py", "nationstates.py", "RegionBlock.py", "RegionClass.py", "dbh.py", "chooser.py"]

        for filename in os.listdir("cogs"):
            if os.path.isfile(os.path.join("cogs", filename)):
                try:
                    if filename.endswith(".py") and filename not in blacklist:
                        await self.load_extension(f"cogs.{filename[:-3]}")
                        print(f"Loaded: {filename}")
                except Exception as e:
                    print(f"Failed to load cog {filename}")
                    print(e)

        await self.add_cog(chooser(self))  # for some reason loading this one as an extension causes the imports to lag
        print("Loaded: chooser.py")

        await self.database.initialize()

        # Migrated to setup_hook from on_ready because on_ready is best left not used after d.py 2.0
        print("Ready to Rock and Roll!")
        
        # TODO: Dynamically choose channel
        channel = await bot.fetch_channel(
            1039736266893299843
        )  # Converted to fetch because get_channel requires a
        # loaded cache which we may not have at this point.
        on_ready_embed = discord.Embed(
            title="Powering On",
            description="I am ready to rock and roll!",
            color=0x8EE6DD,
        )
        await channel.send(embed=on_ready_embed)


if __name__ == "__main__":
    bot = main_class()
    bot.run(token=bot.token)
