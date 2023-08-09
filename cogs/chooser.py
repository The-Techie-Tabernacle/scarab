from datetime import date, datetime, time, timedelta, timezone
import os
from typing import List, NamedTuple, Tuple, Union

import aiosqlite
import discord
from discord.ext import tasks, commands


class Region:
    def __init__(self, name: str, last_update_time: time):
        self.name = name
        self.last_update_time = last_update_time


class TrigAndTargs(NamedTuple):
    trigger: Region
    trigger_time: int
    targets: List[Tuple[Region, int]]


def to_region_url(region: str):
    return 'https://nationstates.net/region=' + region.replace(' ', '_').lower()


class chooser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.headers = {"User-Agent": "SCARAB Accessing NSAPI for regional data, devved by nation=hesskin_empire"}

    def _connect_db(self):
        today, yesterday = date.today().strftime('%m.%d.%Y'), (date.today() - timedelta(days=1)).strftime('%m.%d.%Y')
        # maybe in the future have more complex data dump storage for dealing with GA night? but this will work for now
        db_file = None
        if os.path.exists(f'data.{today}.db'):
            db_file = f'data.{today}.db'
        elif os.path.exists(f'data.{yesterday}.db'):
            db_file = f'data.{yesterday}.db'
        if not db_file:
            raise FileNotFoundError('No current DB dump detected')
        return aiosqlite.connect(db_file)

    async def first_region(self, is_minor: bool = False):
        async with self._connect_db() as db:
            db: aiosqlite.Connection
            db.row_factory = aiosqlite.Row
            async with db.execute(
                    f'''
                    SELECT
                        Name, Last{"Minor" if is_minor else "Major"}Update
                    FROM REGION
                    LIMIT 1
                    ''') as cursor:
                row = await cursor.fetchone()
                return Region(row['Name'], datetime.fromtimestamp(row[f'Last{"Minor" if is_minor else "Major"}Update']).time())

    async def last_region(self, is_minor: bool = False):
        async with self._connect_db() as db:
            db: aiosqlite.Connection
            db.row_factory = aiosqlite.Row
            async with db.execute(
                    f'''
                    SELECT
                        Name, Last{"Minor" if is_minor else "Major"}Update
                    FROM REGION
                    ORDER BY ID DESC
                    LIMIT 1
                    ''') as cursor:
                row = await cursor.fetchone()
                return Region(row['Name'], datetime.fromtimestamp(row[f'Last{"Minor" if is_minor else "Major"}Update']).time())

    async def select_trigger(self, region: Union[str | int], trigger_time: int = 4, is_minor: bool = False) -> Region:
        async with self._connect_db() as db:
            db: aiosqlite.Connection
            db.row_factory = aiosqlite.Row
            if isinstance(region, str):
                async with db.execute(
                        'SELECT ID FROM Region WHERE lower(Name) = ?',
                        (region.lower().replace('_', ' '),)
                ) as cursor:
                    region = int((await cursor.fetchone())['ID'])

            async with db.execute(
                f'''
                    SELECT
                        Name, Last{"Minor" if is_minor else "Major"}Update
                    FROM Region WHERE
                    Last{"Minor" if is_minor else "Major"}Update <= (
                        SELECT Last{"Minor" if is_minor else "Major"}Update FROM Region WHERE ID = ?
                    ) - ? AND LastMinorUpdate != 0
                    ORDER BY ID DESC
                    LIMIT 1
                    ''', (region, trigger_time)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return await self.first_region(is_minor)
                return Region(row['Name'], datetime.fromtimestamp(row[f'Last{"Minor" if is_minor else "Major"}Update']).time())

    async def select_targets(self,
                             is_minor: bool = False,
                             after_region: Union[str | int] = 1,
                             count: int = 1,
                             trigger_time: int = 4,
                             switch_time: int = 30) -> TrigAndTargs:
        if isinstance(after_region, str) and after_region.isdigit():
            after_region = int(after_region)

        async with self._connect_db() as db:
            db: aiosqlite.Connection
            db.row_factory = aiosqlite.Row
            if isinstance(after_region, str):
                async with db.execute(
                        'SELECT ID FROM Region WHERE lower(Name) = ?',
                        (after_region.lower().replace('_', ' '),)
                ) as cursor:
                    after_region = int((await cursor.fetchone())['ID'])

            async with db.execute(
                    f'''
                    SELECT
                        Name, Last{"Minor" if is_minor else "Major"}Update
                    FROM Region WHERE
                    DelegateAuth & 3 = 3 AND NOT hasPassword AND NOT DelegateVotes AND LastMinorUpdate != 0
                    AND Last{"Minor" if is_minor else "Major"}Update > (
                        SELECT Last{"Minor" if is_minor else "Major"}Update FROM Region WHERE ID = ?
                    ) + ?
                    LIMIT ?
                    ''', (after_region, switch_time, count)) as cursor:
                first_row = await cursor.fetchone()
                if not first_row:
                    last_region = await self.last_region(is_minor)
                    trigger = await self.select_trigger(last_region.name, trigger_time, is_minor)
                    trigger_time = (datetime.combine(date.today(), trigger.last_update_time) -
                                    datetime.combine(date.today(), last_region.last_update_time))
                    return TrigAndTargs(trigger, int(trigger_time.total_seconds()), [(last_region, 0)])
                first_target_name, first_target_update = first_row['Name'], first_row[f'Last{"Minor" if is_minor else "Major"}Update']
                targets = [(Region(first_target_name, datetime.fromtimestamp(first_target_update).time()), 0)]
                async for row in cursor:
                    targets.append(
                        (Region(
                            row['Name'],
                            datetime.fromtimestamp(row[f'Last{"Minor" if is_minor else "Major"}Update']).time()
                        ), int(row[f'Last{"Minor" if is_minor else "Major"}Update']) - int(first_target_update))
                    )

        trigger = await self.select_trigger(first_target_name, trigger_time, is_minor)
        trigger_time = (datetime.combine(date.today(), trigger.last_update_time) -
                        datetime.combine(date.today(), datetime.fromtimestamp(first_target_update).time()))

        return TrigAndTargs(trigger, int(trigger_time.total_seconds()), targets)

    @commands.command(aliases=["choose_targets"])
    @discord.app_commands.checks.has_role("command")
    async def get_targets(self,
                          ctx,
                          is_minor: bool = False,
                          after_region: Union[str | int] = 1,
                          count: int = 1,
                          trigger_time: int = 4,
                          switch_time: int = 30):
        try:
            trigger, trigger_time, targets = await self.select_targets(is_minor, after_region, count, trigger_time, switch_time)
        except FileNotFoundError:
            embed = discord.Embed(title='No Current Dump Found',
                                  description='Please dump a more recent dump with `.dump`.',
                                  color=0xd90202)
            return await ctx.reply(embed=embed)

        message = f'Trigger ({trigger_time}s): {trigger.name} ({trigger.last_update_time.strftime("%H:%M:%S")})'
        for target in targets:
            message += f'\n{to_region_url(target[0].name)}'
            if target[1] != 0:
                message += f' (+{target[1]}s)'

        await ctx.reply(message)


async def setup(bot):
    await bot.add_cog(chooser(bot))
