import aiohttp


class AsyncHttpRequester:
    def __init__(self):
        self.session = None

    async def create_session(self):
        self.session = aiohttp.ClientSession()

    async def close_session(self):
        await self.session.close()

    async def make_request(self, *args, **kwargs):
        async with self.session.request(*args, **kwargs) as response:
            text = await response.text()
            status_code = response.status
            if status_code == 200 or status_code == 201 or status_code == 204 or status_code == 207:
                return text, status_code
            elif status_code == 400:
                await self.session.close()
                raise ValueError("Bad request")
            elif status_code == 404:
                await self.session.close()
                raise FileNotFoundError("Not found")
            elif status_code == 409:
                await self.session.close()
                raise FileNotFoundError("Conflict")
            elif status_code == 500:
                await self.session.close()
                raise Exception("Internal server error")
            else:
                await self.session.close()
                raise Exception(f"Unexpected status code: {status_code}")