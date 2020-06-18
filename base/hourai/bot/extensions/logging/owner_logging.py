import discord
import traceback
from discord.ext import commands
from hourai.bot import cogs
from hourai.utils import consts, hastebin, format


class OwnerLogging(cogs.BaseCog):
    """ Cog for logging bot events """

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

        self.log = None
        if bot.config.webhooks.bot_log:
            self.log = discord.Webhook.from_url(
                    bot.config.webhooks.bot_log,
                    adapter=discord.AsyncWebhookAdapter(bot.http_session))

    async def send_log(self, *args, **kwargs):
        if self.log:
            await self.log.send(*args, **kwargs)

    async def send_error(self, error, msg=''):
        trace_str = self._get_traceback(error)
        if len(trace_str) > consts.DISCORD_MAX_MESSAGE_SIZE:
            trace_str = await hastebin.post(self.bot.http_session, trace_str)
        await self.send_log(msg + '\n' + format.multiline_code(trace_str))

    @commands.Cog.listener()
    async def on_ready(self):
        await self.send_log(f'`[{self.bot.user}]: Bot is ready.`')

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id):
        await self.send_log(f'`[{self.bot.user}]: Shard {shard_id} is ready.`')

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.send_log(
                f'`[{self.bot.user}]: Joined {guild.name} ({guild.id}).`')

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.send_log(
                f'`[{self.bot.user}]: Left {guild.name} ({guild.id}).`')

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        message = f'Exception in event {event} (args={args}, kwargs={kwargs}):'
        self.bot.logger.exception(message)
        _, err, _ = sys.exc_info()
        await self.send_error(err, msg=message)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not isinstance(error, commands.CommandInvokeError):
            return
        trace_str = self._get_traceback(error)
        message = f'Command error. Command: {ctx.command.qualified_name}'
        self.bot.logger.error(f'{message}\n{trace_str}\n')
        await self.send_error(error)

    def _get_traceback(self, error):
        trace = traceback.format_exception(type(error), error,
                                           error.__traceback__)
        return '\n'.join(trace)