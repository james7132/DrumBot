import copy
import hourai.utils as utils
import inspect
import re
import traceback
from hourai import bot, extensions
from hourai.db import models
from discord.ext import commands


def regex_multi_attr_match(context, regex, attrs):
    return any(regex.search(func(context)) for func in attrs)


class Owner(bot.BaseCog):

    GUILD_CRITERIA = (
        lambda g: g.name,
        lambda g: str(g.id)
    )

    USER_CRITERIA = (
        lambda u: u.name,
        lambda u: str(u.id),
        lambda u: (f'{u.discriminator:0>4d}' if u.discriminator is not None
                   else 'None'),
    )

    async def cog_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)

    @commands.group()
    async def search(self, ctx, regex):
        pass

    @search.command(name="server")
    async def search_guild(self, ctx, regex):
        regex = re.compile(regex)
        guilds = (f'{g.id}: {g.name}' for g in ctx.bot.guilds
                  if regex_multi_attr_match(regex, g, self.GUILD_CRITERIA))
        await ctx.send(format.multiline_code(format.vertical_list(guilds)))

    @search.command(name="user")
    async def search_user(self, ctx, regex):
        regex = re.compile(regex)
        usernames = ctx.session.query(models.Usernames).all()
        # Deduplicate entries
        users = {u.id: u for u in usernames
                 if regex_multi_attr_match(regex, u, self.USER_CRITERIA)}
        users = (f'{u.id}: {u.name}#{u.discriminator}' for _,
                 u in users.items())
        await ctx.send(format.multiline_code(format.vertical_list(users)))

    @commands.command()
    async def reload(self, ctx,  *, extension: str):
        """Reloads the specified bot module."""
        extension = f'{extensions.__name__}.{extension}'
        try:
            ctx.bot.unload_extension(extension)
        except Exception:
            pass
        try:
            ctx.bot.load_extension(extension)
        except Exception as e:
            trace = utils.format.ellipsize(traceback.format_exc())
            err_type = type(e).__name__
            await ctx.send(f'**ERROR**: {err_type} - {e}\n```{trace}```')
        else:
            await utils.success(ctx)

    @commands.command()
    async def repeat(self, ctx, times: int, *, command):
        """Repeats a command a specified number of times."""
        msg = copy.copy(ctx.message)
        msg.content = command

        new_ctx = await ctx.bot.get_context(msg)
        new_ctx.db = ctx.db

        for i in range(times):
            await new_ctx.reinvoke()

    @commands.command()
    async def eval(self, ctx, *, expr: str):
        global_vars = {**globals(), **{
            'bot': ctx.bot,
            'msg': ctx.message,
            'channel': ctx.channel,
            'guild': ctx.guild,
            'guilds': ctx.bot.guilds,
            'users': ctx.bot.users,
            'dms': ctx.bot.private_channels,
            'members': ctx.bot.get_all_members(),
            'channels': ctx.bot.get_all_channels(),
        }}
        try:
            result = eval(expr, {}, global_vars)
            if inspect.isawaitable(result):
                result = await result
            await ctx.send(f"Eval results for `{expr}`:\n```{str(result)}```")
        except Exception:
            await ctx.send(f"Error when running eval of `{expr}`:\n"
                           f"```{str(traceback.format_exc())}```")


def setup(bot):

    bot.add_cog(Owner())
