import asyncio


def async_test(func):
    def run(*args, **kwargs):
        asyncio.run(func(*args, **kwargs))

    return run
