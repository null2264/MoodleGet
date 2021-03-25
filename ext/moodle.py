import discord
import io


from .utils.formatting import pformat
from .utils.paginator import ZiReplyMenu
from discord.ext import commands, menus


LOGO = "https://raw.githubusercontent.com/null2264/null2264/master/assets/748911e4b9b498730712abf392826131.webp"
SCHOOL_NAME = "Universitas Bina Darma"


class ActivitiesPageSource(menus.ListPageSource):
    def __init__(self, ctx, course, activities):
        super().__init__(entries=activities, per_page=1)
        self.ctx = ctx
        self.course = course

    async def format_page(self, menu, activity):
        images = "\n".join(activity.images)
        e = discord.Embed(
            title=activity.name or "No title.",
            description=activity.content or "No content." + (
                "\n\n🖼️ Images:\n{}".format(images) if images else ""),
            url=activity.weblink,
            colour=discord.Colour.dark_gray(),
        )
        maximum = self.get_max_pages()
        e.set_author(
            name="{} - {}".format(SCHOOL_NAME, self.course.name),
            url=self.course.weblink,
            icon_url=LOGO,
        )
        e.set_thumbnail(url=LOGO)
        e.set_footer(
            text=f"Requested by {self.ctx.author} - Page {menu.current_page + 1}/{maximum}",
            icon_url=self.ctx.author.avatar_url,
        )
        return e

class CoursesPageSource(menus.ListPageSource):
    def __init__(self, ctx, courses):
        super().__init__(entries=[["firstPage"]] + courses, per_page=1)
        self.ctx = ctx
        self.courses = courses

    def format_firstPage(self, menu):
        e = discord.Embed(
            title="{}'s Courses".format(self.ctx.author.name),
            description="\n".join(["- {}".format(course.name) for course in self.courses]),
            colour=discord.Colour.dark_gray(),
        )
        e.set_author(
            name="{} - {}".format(SCHOOL_NAME, self.ctx.author.name),
            icon_url=LOGO,
        )
        e.set_thumbnail(url=LOGO)
        maximum = self.get_max_pages()
        e.set_footer(
            text=f"Requested by {self.ctx.author} - Page {menu.current_page + 1}/{maximum}",
            icon_url=self.ctx.author.avatar_url,
        )
        return e

    async def format_page(self, menu, course):
        if isinstance(course, list):
            return self.format_firstPage(menu)
        e = discord.Embed(
            title=course.name,
            description="**Progress**: {}/100".format(course.progress),
            url=course.weblink,
            colour=discord.Colour.dark_gray(),
        )
        e.add_field(name="Start Date", value=course.startdate)
        e.add_field(name="End Date", value=course.enddate)
        e.set_author(
            name="{} - {}'s Courses".format(SCHOOL_NAME, self.ctx.author.name),
            icon_url=LOGO,
        )
        e.set_thumbnail(url=LOGO)
        maximum = self.get_max_pages()
        e.set_footer(
            text=f"Requested by {self.ctx.author} - Page {menu.current_page + 1}/{maximum}",
            icon_url=self.ctx.author.avatar_url,
        )
        return e


class Moodle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def courses(self, ctx):
        courses = await self.bot.getCourses()
        menu = ZiReplyMenu(
            source=CoursesPageSource(
                ctx,
                courses,
            )
        )
        await menu.start(ctx)

    @commands.command()
    async def activities(self, ctx, *, course):
        courses = await self.bot.getCourses()
        sel_course = None
        for _course in courses:
            if pformat(course) == _course.id or pformat(course) in pformat(_course.name):
                sel_course = _course
        if not sel_course:
            raise commands.BadArgument("Course `{}` not found".format(course))
        activities = await self.bot.getActivities(sel_course)
        menu = ZiReplyMenu(
            source=ActivitiesPageSource(
                ctx,
                sel_course,
                activities
            )
        )
        await menu.start(ctx)


def setup(bot):
    bot.add_cog(Moodle(bot))
