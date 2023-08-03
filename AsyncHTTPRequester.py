import aiohttp
import asyncio


class AsyncHttpRequester:
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def make_request(self, *args, **kwargs):
        async with self.session.request(*args, **kwargs) as response:
            return response

    async def close(self):
        await self.session.close()
