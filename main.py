import asyncio


from core.bot import MoodleGet


try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


bot = MoodleGet()


loop = asyncio.get_event_loop()
bot.run()
