import discord
#from time import time
#import os
#import sys
import requests
#from keep_alive import keep_alive
from discord.ext import commands
from discord import Activity, ActivityType
#from discord.ext.commands import clean_content
from discord.ext.commands import MissingPermissions, CommandNotFound
import pandas as pd
import io
import inspect
import textwrap
import traceback
from contextlib import redirect_stdout
import aiohttp
from datetime import datetime

year = datetime.now().year

bot = commands.Bot(command_prefix='zpy!')
bot.remove_command('help')
bot.config = pd.read_json('config.json')
bot.launch_time = datetime.utcnow()


def codeblock(ctx):
    return f'```yaml\n{ctx}\n```'


def codeblocklang(ctx, lang):
    return f'```{lang}\n{ctx}\n```'


async def startup():
    await bot.wait_until_ready()
    bot.session = aiohttp.ClientSession(loop=bot.loop)
    await bot.change_presence(
        activity=Activity(name=f"Over {len(bot.guilds)} Servers | zpy!help",
                          type=ActivityType.listening))


bot.loop.create_task(startup())


#uptime
def botuptime(b):
    delta_uptime = datetime.utcnow() - b.launch_time
    hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    return codeblock(
        f"Days: {days}\nHours: {hours}\nMinutes: {minutes}\nSeconds: {seconds}"
    )


#on error
#@bot.event
#async def on_error_command(ctx, error):
#	pass


# on command error
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        pass
    if isinstance(error, MissingPermissions):
        return await ctx.reply(codeblock('Missing Permissions!'),
                                 delete_after=20.0,
                               mention_author=False)
    return await ctx.reply(codeblock(error),
                           delete_after=20.0,
                           mention_author=False)


#guild join
@bot.event
async def on_guild_join(guild):
    await bot.change_presence(
        activity=Activity(name=f"Over {len(bot.guilds)} Servers | zpy!help",
                          type=ActivityType.listening))


#guild leave
@bot.event
async def on_guild_remove(guild):
    await bot.change_presence(
        activity=Activity(name=f"Over {len(bot.guilds)} Servers | zpy!help",
                          type=ActivityType.listening))


#on
@bot.event
async def on_ready():
    print(f'[{bot.launch_time}] Logged in as : {bot.user}')


#ping
@bot.command()
async def ping(ctx):
    await ctx.reply(codeblock(f'pong! {round(bot.latency * 1000)}ms'),
                    mention_author=False)


def resolve_variable(self, variable):
    if hasattr(variable, "__iter__"):
        var_length = len(list(variable))
        if (var_length > 100) and (not isinstance(variable, str)):
            return f"<a {type(variable).__name__} iterable with more than 100 values ({var_length})>"
        elif (not var_length):
            return f"<an empty {type(variable).__name__} iterable>"

    if (not variable) and (not isinstance(variable, bool)):
        return f"<an empty {type(variable).__name__} object>"
    return (
        variable if (len(f"{variable}") <= 1000) else
        f"<a long {type(variable).__name__} object with the length of {len(f'{variable}'):,}>"
    )


def prepare(self, string):
    arr = string.strip("```").replace("py\n", "").replace("python\n",
                                                          "").split("\n")
    if not arr[::-1][0].replace(" ", "").startswith("return"):
        arr[len(arr) - 1] = "return " + arr[::-1][0]
    return "".join(f"\n\t{i}" for i in arr)


def is_owner(ctx):
    return ctx.message.author.id == bot.config.bot.ownerid


#eval
@bot.command(name='eval')
@commands.is_owner()
async def _eval(ctx, *, body):
    """Evaluates python code"""
    blocked_words = [
        '.delete()', 'os', 'subprocess', 'history()', '("token")', "('token')",
        'aW1wb3J0IG9zCnJldHVybiBvcy5lbnZpcm9uLmdldCgndG9rZW4nKQ==',
        'aW1wb3J0IG9zCnByaW50KG9zLmVudmlyb24uZ2V0KCd0b2tlbicpKQ=='
    ]
    if ctx.message.author.id == bot.owner_id:
        for x in blocked_words:
            if x in body:
                return await ctx.reply(
                    'Your code contains certain blocked words.',
                    mention_author=False)
    env = {
        'ctx': ctx,
        'channel': ctx.channel,
        'author': ctx.author,
        'guild': ctx.guild,
        'message': ctx.message,
        'source': inspect.getsource,
        'session': bot.session
    }

    env.update(globals())

    body = cleanup_code(body)
    stdout = io.StringIO()
    err = out = None

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    def paginate(text: str):
        '''Simple generator that paginates text.'''
        last = 0
        pages = []
        for curr in range(0, len(text)):
            if curr % 1980 == 0:
                pages.append(text[last:curr])
                last = curr
                appd_index = curr
        if appd_index != len(text) - 1:
            pages.append(text[last:curr])
        return list(filter(lambda a: a != '', pages))

    try:
        exec(to_compile, env)
    except Exception as e:
        err = await ctx.reply(f'```py\n{e.__class__.__name__}: {e}\n```',
                              mention_author=False)
        pass


#       return await ctx.message.add_reaction('\u2049')

    func = env['func']
    try:
        with redirect_stdout(stdout):
            ret = await func()
    except Exception:
        value = stdout.getvalue()
        err = await ctx.reply(f'```py\n{value}{traceback.format_exc()}\n```',
                              mention_author=False)
    else:
        value = stdout.getvalue()
        if ret is None:
            if value:
                try:

                    out = await ctx.reply(f'```py\n{value}\n```',
                                          mention_author=False)
                except:
                    paginated_text = paginate(value)
                    for page in paginated_text:
                        if page == paginated_text[-1]:
                            out = await ctx.reply(f'```py\n{page}\n```',
                                                  mention_author=False)
                            break
                        await ctx.reply(f'```py\n{page}\n```',
                                        mention_author=False)
        else:
            bot._last_result = ret
            try:
                out = await ctx.reply(f'```py\n{value}{ret}\n```',
                                      mention_author=False)
            except:
                paginated_text = paginate(f"{value}{ret}")
                for page in paginated_text:
                    if page == paginated_text[-1]:
                        out = await ctx.reply(f'```py\n{page}\n```',
                                              mention_author=False)
                        break
                    await ctx.reply(f'```py\n{page}\n```',
                                    mention_author=False)

    if out:
        pass
        #await ctx.message.add_reaction('\u2705')  # tick
    elif err:
        pass
        #await ctx.message.add_reaction('\u2049')  # x
    else:
        pass
        #await ctx.message.add_reaction('\u2705')


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')


def get_syntax_error(e):
    if e.text is None:
        return f'```py\n{e.__class__.__name__}: {e}\n```'
    return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'


#help
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Help Menu", color=0x0011ff)
    embed.add_field(
        name="INFO [Total Commands: 3]",
        value=
        "`zpy!ping`, `zpy!help`, `zpy!botinfo`, `zpy!uptime`, `zpy!support`, `zpy!invite`",
        inline=False)
    embed.add_field(
        name="UTILITY [Total Commands: 4]",
        value="`zpy!avatar`, `zpy!userinfo`, `zpy!reverse`, `zpy!tinyurl`",
        inline=False)
    embed.add_field(name="CRYPTO [Total Commands: 3]",
                    value="`zpy!bitcoin`, `zpy!ethereum`, `zpy!monero`",
                    inline=False)
    embed.set_thumbnail(url=bot.user.avatar_url)
    embed.set_footer(text=f"Ziro-Bot Python {year} ©")
    await ctx.reply(embed=embed, mention_author=False)


#support
@bot.command()
async def support(ctx):
    await ctx.reply(f'discord.gg/yXjx596', mention_author=False)


#invite
@bot.command()
async def invite(ctx):
    await ctx.reply(
        f'**<https://discord.com/oauth2/authorize?client_id={bot.user.id}&scope=bot&permissions=8>**',
        mention_author=False)


#botinfo
@bot.command()
async def botinfo(ctx):
    embed = discord.Embed(color=0x0011ff)
    embed.set_thumbnail(url=bot.user.avatar_url)
    embed.add_field(name="Library",
                    value=codeblock("discord.py"),
                    inline=False)
    embed.add_field(name="Ping",
                    value=codeblock(f'{round(bot.latency * 1000)}ms'),
                    inline=False)
    embed.add_field(name="Owner", value=codeblock("Ziroトト#9200"), inline=False)
    embed.add_field(name="Bot Created",
                    value=codeblock(f"{bot.user.created_at}"),
                    inline=False)
    embed.add_field(name="Bot Uptime", value=botuptime(bot), inline=False)
    embed.set_footer(text=f"Ziro-Bot Python {year} ©")
    await ctx.reply(embed=embed, mention_author=False)


#uptime
@bot.command()
async def uptime(ctx):
    await ctx.reply(botuptime(bot), mention_author=False)


#avatar
@bot.command()
async def avatar(ctx, *, member: discord.Member = None):
    if not member:
        member = ctx.message.author

    embed = discord.Embed(color=0x0011ff)
    embed.set_image(url=member.avatar_url)
    embed.set_footer(text=f"Ziro-Bot Python {year} ©")
    await ctx.reply(embed=embed, mention_author=False)


#userinfo
@bot.command()
@commands.guild_only()
async def userinfo(ctx, *, member: discord.Member = None):
    if not member:
        member = ctx.message.author

    embed = discord.Embed(color=0x0011ff)
    embed.set_thumbnail(url=member.avatar_url)
    embed.add_field(name="Tag",
                    value=codeblock(f'{member.name}#{member.discriminator}'))
    embed.add_field(name="ID", value=codeblock(member.id), inline=False)
    embed.add_field(name="Created At",
                    value=codeblock(member.created_at),
                    inline=False)
    embed.add_field(name="Joined At",
                    value=codeblock(member.joined_at),
                    inline=False)
    embed.add_field(name="Boosting Since",
                    value=codeblock(member.premium_since))
    embed.add_field(name="Nickname", value=codeblock(member.nick))
    embed.add_field(name="Top Role", value=codeblock(f'@{member.top_role}'))
    embed.add_field(name='On Mobile', value=codeblock(member.is_on_mobile()))
    embed.add_field(name="Status",
                    value=codeblock(f'{member.status} (Not Exact)'))
    embed.set_footer(text=f"Ziro-Bot Python {year} ©")
    print(member.is_on_mobile())
    await ctx.reply(embed=embed, mention_author=False)


#reverse
@bot.command()
async def reverse(ctx, *, var):
    stuff = var[::-1]
    embed = discord.Embed(description=stuff, color=0x0011ff)
    embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
    await ctx.reply(embed=embed, mention_author=False)


#tinyurl
@bot.command()
async def tinyurl(ctx, *, link):
    r = requests.get(f'http://tinyurl.com/api-create.php?url={link}').text
    em = discord.Embed()
    em.add_field(name='Shortened link:', value=r, inline=False)
    await ctx.reply(embed=em, mention_author=False)


#bitcoin
@bot.command(aliases=['bitcoin'])
async def btc(ctx):
    r = requests.get(
        'https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD,EUR,BGN'
    )
    r = r.json()
    usd = r['USD']
    eur = r['EUR']
    bgn = r['BGN']
    em = discord.Embed(
        description=
        f'USD: `{str(usd)}$`\nEUR: `{str(eur)}€`\nBGN: `{str(bgn)}BGN`')
    em.set_author(name='Bitcoin Price')
    await ctx.reply(embed=em, mention_author=False)


#ethereum
@bot.command(aliases=['ethereum'])
async def eth(ctx):
    r = requests.get(
        'https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD,EUR,BGN'
    )
    r = r.json()
    usd = r['USD']
    eur = r['EUR']
    bgn = r['BGN']
    em = discord.Embed(
        description=
        f'USD: `{str(usd)}$`\nEUR: `{str(eur)}€`\nBGN: `{str(bgn)}BGN`')
    em.set_author(name='Ethereum Price')
    await ctx.reply(embed=em, mention_author=False)


#monero
@bot.command(aliases=['monero'])
async def xmr(ctx):
    r = requests.get(
        'https://min-api.cryptocompare.com/data/price?fsym=XMR&tsyms=USD,EUR,BGN'
    )
    r = r.json()
    usd = r['USD']
    eur = r['EUR']
    bgn = r['BGN']
    em = discord.Embed(
        description=
        f'USD: `{str(usd)}$`\nEUR: `{str(eur)}€`\nBGN: `{str(bgn)}BGN`')
    em.set_author(name='Monero Price')
    await ctx.reply(embed=em, mention_author=False)


def clean_code(ctx):
    if ctx.startsWith("```") and ctx.endsWith("```"):
        return "\n".join(ctx.split("\n")[1:][:-3])
        return ctx


#kick
@bot.command()
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
@commands.guild_only()
async def kick(ctx, member: discord.Member, *, reason=None):
    await ctx.reply(codeblock(f'{member.mention} Was Kicked For: {reason}'),
                    mention_author=False)
    await member.kick(reason=reason)


#ban
@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
@commands.guild_only()
async def ban(ctx, member: discord.Member, *, reason=None):
    await ctx.reply(codeblock(f'{member.mention} Was Banned For: {reason}'),
                    mention_author=False)
    await member.ban(reason=reason)


#clear
@bot.command(aliases=['purge'])
@commands.guild_only()
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount)


#nickname
@bot.command(aliases=['nick'])
@commands.has_permissions(change_nickname=True)
@commands.bot_has_permissions(manage_nicknames=True)
@commands.guild_only()
async def nickname(ctx, *, nickname=None):
    await ctx.message.author.edit(nick=nickname)
    await ctx.reply(codeblock(f'{ctx.message.author.name} => {nickname}'),
                    mention_author=False,
                    delete_after=5.0)
    await ctx.message.delete()


#keep_alive()
bot.run(bot.config.bot.token)
