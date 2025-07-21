import aiohttp


class SingletonAiohttp:
    aiohttp_client: aiohttp.ClientSession | None = None

    @classmethod
    def get_aiohttp_client(cls) -> aiohttp.ClientSession:
        if cls.aiohttp_client is None:
            connector = aiohttp.TCPConnector(limit_per_host=100)
            cls.aiohttp_client = aiohttp.ClientSession(connector=connector, trust_env=True)

        return cls.aiohttp_client

    @classmethod
    async def close_aiohttp_client(cls) -> None:
        if cls.aiohttp_client:
            await cls.aiohttp_client.close()
            cls.aiohttp_client = None
