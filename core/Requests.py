import asyncio, requests

class Requests:
    def __init__(self, url=""):
        self.url = url

    async def request(self, **kwargs):
        return requests.request(**kwargs)
    
    async def get(self, **kwargs) -> requests.Response:
        task = asyncio.ensure_future(self.request(method="GET", url=self.url, **kwargs))

        return (await asyncio.gather(task))[0]

    async def post(self, **kwargs) -> requests.Response:
        task = asyncio.ensure_future(self.request(method="POST", url=self.url, **kwargs))

        return (await asyncio.gather(task))[0]