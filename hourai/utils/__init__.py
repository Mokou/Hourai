import discord
import inspect
import time
import functools
from hourai import config

MODERATOR_PREFIX = 'mod'

async def success(ctx, suffix=None):
    if suffix:
        await ctx.send(f'{config.SUCCESS_RESPONSE}: {suffix}')
    else:
        await ctx.send(config.SUCCESS_RESPONSE)

def pretty_print(resource):
    output = []
    if hasattr(resource, 'name'):
        output.append(resource.name)
    if hasattr(resource, 'id'):
        output.append('({})'.format(resource.id))
    return ' '.join(output)

def log_time(func):
    """ Logs the time to run a function to std out. """
    @functools.wraps(func)
    def time_logger(*args, **kwargs):
        real_time = time.time()
        cpu_time = time.process_time()
        try:
            func(*args, **kwargs)
        finally:
            # TODO(james7132): Log this using logging
            real_time = time.time() - real_time
            cpu_time = time.process_time() - cpu_time
            print('{} called. real: {} s, cpu: {} s.'.format(
                  func.__qualname__, real_time, cpu_time))

    @functools.wraps(func)
    async def async_time_logger(*args, **kwargs):
        real_time = time.time()
        cpu_time = time.process_time()
        try:
            await func(*args, **kwargs)
        finally:
            # TODO(james7132): Log this using logging
            real_time = time.time() - real_time
            cpu_time = time.process_time() - cpu_time
            print('{} called. real: {} s, cpu: {} s.'.format(
                  func.__qualname__, real_time, cpu_time))
    return async_time_logger if inspect.iscoroutinefunction(func) else time_logger

async def send_dm(user, *args, **kwargs):
    """ Shorthand to send a user a DM. """
    dm_channel = user.dm_channel or await user.create_dm()
    await dm_channel.send(*args, **kwargs)

def any_in(population, seq):
    return any(val in population for val in seq)

def is_moderator(member):
    """ Checks if a user is a moderator. """
    return any(is_moderator_role(r) for r in member.roles)

def is_moderator_role(role):
    """ Checks if a role is a moderator role. """
    return role.permissions.administrator or role.name.lower().startswith(MODERATOR_PREFIX)

def is_online(member):
    return member.status == discord.Status.online

def all_with_roles(members, roles):
    """ Filters a list of members to those with roles. Returns a generator of members """
    role_set = set(roles)
    return filter(lambda m: any_in(role_set, m.roles), members)

def all_without_roles(members, roles):
    """ Filters a list of members to those without roles. Returns a generator of members """
    role_set = set(roles)
    return filter(lambda m: not any_in(role_set, m.roles), members)

def find_moderator_roles(guild):
    """ Finds all of the moderator roles on a server. Returns an generator of roles """
    return filter(lambda r: is_moderator_role(r), guild.roles)

def find_moderators(guild):
    """ Finds all of the moderators on a server. Returns a generator of members. """
    return all_with_roles(find_moderator_roles(guild), guild.members)

def find_bots(guild):
    """ Finds all of the bots on a server. Returns a generator of members. """
    return filter(lambda m: m.bot, guild.members)

def find_online_moderators(guild):
    """ Finds all of the online moderators on a server. Returns a generator of members. """
    return filter(is_online, guild.members)

def mention_random_online_mod(guild):
    """
    Returns a string containing a mention of a currently online moderator.
    If no moderator is online, returns a ping to the server owner.
    """
    moderators = list(find_online_moderators(guild))
    if len(online_mods) > 0:
        return random.choice(moderators).mention
    else:
        return f'{ctx.guild.owner.mention}, no mods are online!'
