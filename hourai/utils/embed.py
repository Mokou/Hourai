import asyncio
import logging
import discord
import humanize
import traceback
import collections
from datetime import datetime
from hourai.utils import format, consts
from hourai.db import models


def ellipsize(txt, keep_end=False):
    return format.ellipsize(txt, consts.DISCORD_MAX_EMBED_DESCRIPTION_SIZE,
                            keep_end=keep_end)


def text_to_embed(txt, keep_end=False):
    embed = discord.Embed(description=ellipsize(txt, keep_end=keep_end))
    return embed


def traceback_to_embed(keep_end=False):
    text = format.multiline_code(traceback.format_exc())
    return text_to_embed(text, keep_end=keep_end)


def make_whois_embed(ctx, user):
    now = datetime.utcnow()

    description = []

    guild_count = _get_guild_count(ctx, user)
    if guild_count > 1:
        count = format.bold(str(guild_count))
        description.append(f'Seen on {count} servers.')

    usernames = _get_extra_usernames(ctx, user)
    if len(usernames) > 0:
        output = reversed([_to_username_line(un) for un in usernames])
        description.append(format.multiline_code(format.vertical_list(output)))
    description = None if len(description) <= 0 else '\n'.join(description)

    embed = discord.Embed(
        title=f'{user.name}#{user.discriminator} ({user.id})',
        color=user.color,
        description=description
    )

    embed.set_thumbnail(url=str(user.avatar_url or user.default_avatar_url))
    embed.set_footer(text=hex(user.id))

    _add_time_field(embed, 'Created At', user.created_at, now)
    try:
        _add_time_field(embed, 'Joined On', user.joined_at, now)
    except AttributeError:
        pass

    try:
        if user.premium_since is not None:
            _add_time_field(embed, 'Boosting Since', user.premium_since, now)
    except AttributeError:
        pass

    try:
        if len(user.roles) > 1:
            roles = reversed([r for r in user.roles if r.name != '@everyone'])
            roles = format.code_list(r.name for r in roles)
            embed.add_field(name='Roles', value=roles)
    except AttributeError:
        pass

    return embed


def _add_time_field(embed, name, time, now):
    if time is None:
        embed.add_field(name=name, value='N/A')
        return
    time_string = time.strftime('%b %d %Y %-I:%M:%S %p')
    delta = humanize.naturaltime(now - time)
    embed.add_field(name=name, value=f'{time_string} ({delta})')


def _to_username_line(username):
    date_string = username.timestamp.strftime("%b %d %Y")
    user_string = username.name
    if username.discriminator is not None:
        user_string = f'{username.name}#{username.discriminator:0>4d}'
    return f'{date_string} {user_string}'


def _get_guild_count(ctx, user):
    return sum(1 if g.get_member(user.id) is not None else 0
               for g in ctx.bot.guilds)


def _get_extra_usernames(ctx, user):
    usernames = ctx.session.query(models.Username) \
        .filter_by(user_id=user.id) \
        .order_by(models.Username.timestamp) \
        .limit(20)
    usernames = list(usernames)
    while len(usernames) > 0 and usernames[-1].name == user.name:
        usernames.pop()
    return usernames


class MessageUI:

    UPDATE_FREQUENCY = 5.0          # Every 5 seconds

    def __init__(self, client):
        self.client = client
        self.message = None
        self.reactions = collections.OrderedDict()
        self.stop_event = asyncio.Event()

    async def create_content(self):
        return None

    async def create_embed(self):
        return None

    async def on_update(self):
        pass

    def add_button(self, reaction, handler):
        self.reactions[reaction] = handler
        return self

    async def run(self, channel):
        self.message = await channel.send(
                content=await self.create_content(),
                embed=await self.create_embed())
        for reaction in self.reactions.keys():
            await self.message.add_reaction(reaction)
        return self.client.loop.create_task(self._background_loop())

    async def _background_loop(self):
        while not self.stop_event.is_set():
            try:
                await self._handle_reactions()
                await self.on_update()
                content = await self.create_content()
                embed = await self.create_embed()
                if self._has_changed(content, embed):
                    await self.message.edit(content=content, embed=embed)
            except Exception:
                logging.exception('Error while updating message UI:')

    def _has_changed(self, content, embed):
        if self.message.content != content:
            return True
        if (embed is not None) != (len(self.message.embeds) <= 0):
            return True
        if embed is not None and len(self.message.embeds) > 0:
            if embed.to_dict() != self.message.embeds[0].to_dict():
                return True
        return False

    async def _handle_reactions(self):
        def match_message(react, _):
            return react.message == self.message
        try:
            react, member = await self.client.wait_for(
                'reaction_add', check=match_message,
                timeout=self.UPDATE_FREQUENCY)
            logging.info(f"{str(react.emoji)}, {member}, "
                         f"{react.emoji in self.self.reactions}")
            try:
                # Remove the reaction if possible.
                await react.message.remove_reaction(react.emoji, member)
            except discord.Forbidden:
                pass
            handler = self.reactions.get(react.emoji)
            if handler is not None:
                handler()
        except asyncio.TimeoutError:
            pass

    async def stop(self, delete=False):
        try:
            self.stop_event.set()
            if delete:
                await self.delete()
            elif self.message is not None:
                await self.message.clear_reactions()
        except discord.Forbidden:
            pass

    async def delete(self):
        if self.message is not None:
            await self.message.delete()
