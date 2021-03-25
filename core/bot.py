import aiohttp
import discord
import re


from datetime import datetime
from discord.ext import commands
from lxml import html
from markdownify import markdownify as md


import config


def _callable_prefix(bot, message):
    """A callable prefix for bot."""
    user_id = bot.user.id
    prefixes = (f"<@{user_id}> ", f"<@!{user_id}> ")
    return prefixes


extensions = (
    "ext.moodle",
)


BASEURL = "https://elearning.binadarma.ac.id"
MYURL = BASEURL + "/my/"
LOGINURL = BASEURL + "/login/index.php"


class Activity(object):
    __slots__ = ("id", "type", "weblink", "name", "content", "images")
    
    def __init__(self, baseData):
        self.id = baseData.xpath("@id")[0]
        baseData = baseData.xpath("./div/div/div/div")

        # Activity Instance
        try:
            activityInstance = [data for data in baseData if "activityinstance" in data.xpath("@class")][0]
            instanceName = activityInstance.xpath("./a/span[@class='instancename']")[0]
            self.name = instanceName.text
            try:
                self.type = instanceName.xpath("./span")[0].text
            except IndexError:
                self.type = " Post"
        except IndexError:
            self.name = ""
            self.type = " Post"
        
        try:
            self.weblink = baseData[0].xpath("./a/@href")[0]
        except IndexError:
            self.weblink = None

        # Content
        try:
            try:
                contents = [data.xpath("./div/div/*") for data in baseData if "content" in data.xpath("@class")[0]][0]
            except IndexError:
                contents = []

            self.content = []
            self.images = []
            for content in contents:
                self.images += content.xpath("./img/@src")
                self.content += [str(html.tostring(content, pretty_print=True, encoding="unicode").strip().replace("\r\n", ""))]

            self.content = md("".join(self.content), strip=["h3", "img"])

            # Get zoom from content
            if "zoom.us" in self.content:
                zoomRegex = re.compile(r"(http(?:s)?:\/\/[\S]*zoom.us\/j\/.*)")
                match = zoomRegex.findall(self.content)
                if match:
                    self.weblink = match[0]
                self.name = "Zoom Meeting"
                self.type = " Zoom"

        except Exception as exc:
            self.content = ""
            self.images = []
            print("Error:", exc)

    def __str__(self):
        return self.name + " - " + self.content


class Course(object):
    __slots__=("id", "name", "weblink", "shortname", "progress", "startdate", "enddate")
    def __init__(self, baseData):
        self.id = baseData["id"]
        self.weblink = baseData["viewurl"]
        self.name = str(baseData["fullname"]).replace("&amp;", "&")
        self.shortname = baseData["shortname"]
        self.progress = baseData.get("progress", "0")
        self.startdate = datetime.fromtimestamp(baseData["startdate"]) 
        self.enddate = datetime.fromtimestamp(baseData["enddate"]) 

    def __str__(self):
        return self.name


class MoodleGet(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=_callable_prefix,
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=True, roles=False
            ),
            intents=discord.Intents.all(),
        )
        # aiohttp session with cookie jar, for MoodleSession
        self.session = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar()
        )
        self.loop.create_task(self.asyncInit())
    
    async def asyncInit(self):
        """__init__ but async."""
        # Getting necessary data to login
        init = await self.session.post(LOGINURL)
        tree = html.fromstring(await init.text())
        loginToken = list(set(tree.xpath("//input[@name='logintoken']/@value")))[0]
        payload = {
            "username": config.username,
            "password": config.password,
            "logintoken": loginToken,
        }

        # Logging into moodle
        login = await self.session.post(LOGINURL, data=payload, headers={"referer": LOGINURL})
        tree = html.fromstring(await login.text())
        try:
            self.sesskey = tree.xpath("//input[@name='sesskey']/@value")[0]
        except IndexError:
            # Invalid login (probably wrong password)
            raise RuntimeError("Invalid login, please try again.")
        # Getting moodleSession from cookie, required for certain function
        self.moodleSession = self.session.cookie_jar.filter_cookies(BASEURL).get("MoodleSession")

    async def getCourses(self) -> [Course]:
        """Get course from moodle's backend core api."""
        sessionKey = self.sesskey
        result = await self.session.post(
            BASEURL + "/lib/ajax/service.php?sesskey={}&info=core_course_get_enrolled_courses_by_timeline_classification".format(sessionKey),
            headers={
                "referer": MYURL,
                "content-type": "application/json",
                "cookie": "MoodleSession={}".format(self.moodleSession)
            },
            data='''[
                {
                    "index": 0,
                    "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
                    "args": {
                        "offset": 0,
                        "limit":96,
                        "classification": "all",
                        "sort": "fullname"
                    }
                }
            ]''',
        )
        result = await result.json()
        if result and "error" not in result:
            return [Course(course) for course in result[0]["data"]["courses"]]
        raise RuntimeError

    async def getActivities(self, course: Course) -> [Activity]:
        """Get activities by scraping it."""
        getRes = await self.session.get(course.weblink, headers={"referer": MYURL})
        tree = html.fromstring(await getRes.text())

        activities = tree.xpath("//div[@class='course-content']/ul/li/div[@class='content']/ul/li")
        activities = [Activity(activity) for activity in activities]
        return activities

    async def on_ready(self):
        await self.change_presence(
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=('@MoodleGet help')
            )
        )

        for extension in extensions:
            self.load_extension(extension)

        print("Bot is online!")

    def run(self):
        super().run(config.token, reconnect=True)

    async def close(self):
        await super().close()
        await self.session.close()

    @property
    def config(self):
        return __import__("config")
