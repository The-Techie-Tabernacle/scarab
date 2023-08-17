from datetime import date, datetime, time, timedelta, timezone
import os
from typing import List, NamedTuple, Tuple, Union

import aiosqlite


class Region(NamedTuple):
    name: str
    last_update_time: time


class TrigAndTargs(NamedTuple):
    trigger: Region
    trigger_time: int
    targets: List[Tuple[Region, int]]


def to_region_url(region: str):
    return 'https://nationstates.net/region=' + region.replace(' ', '_').lower()


class chooser:
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

    async def first_region(self, is_minor: bool = False) -> Region:
        """Gets the first updating region on the site.

        Args:
            is_minor: A bool representing whether or not to get the minor update time. Defaults to False.

        Returns:
            A Region NamedTuple corresponding to the first updating region.

        Raises:
            FileNotFoundError: If a current dump is not found.
        """
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

    async def last_region(self, is_minor: bool = False) -> Region:
        """Gets the last updating region on the site.

        Args:
            is_minor: A bool representing whether or not to get the minor update time. Defaults to False.

        Returns:
            A Region NamedTuple corresponding to the last updating region.

        Raises:
            FileNotFoundError: If a current dump is not found.
        """
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
        """Selects a trigger for the region.

        select_trigger's trigger is the best available one equal to or longer than the provided trigger_time.

        Args:
            region: The region to select a trigger for. Can be either the name of the region or the ID in update order.
            trigger_time: The lowest time desired for the trigger. Defaults to 4.
            is_minor: Whether or not to select triggers for minor. Defaults to False.

        Returns:
            A Region NamedTuple corresponding to the best available trigger.
        """
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
        """Selects a target or multiple raidable targets along with a trigger.

        Args:
            is_minor: Whether or not to select targets and a trigger for minor. Defaults to False.
            after_region: The region to scan for targets after. Defaults to the first updating region.
            count: How many targets to pull. Defaults to 1.
            trigger_time: The lowest time desired for the trigger. Defaults to 4.
            switch_time: The minimum time desired between the region provided and the first target. Defaults to 30.

        Returns:
            A TrigAndTargs NamedTuple representing the trigger and a list of targets. The trigger is a Region NamedTuple, and
            The targets are given in a tuple consisting of a Region and an int representing the update time in seconds after
            the first region.
        """
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
