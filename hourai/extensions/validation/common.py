import re


class Validator():
    """Base class for all validators."""

    async def get_approval_reasons(self, bot, member):
        # Empty async generator
        if False:
            yield None

    async def get_rejection_reasons(self, bot, member):
        # Empty async generator
        if False:
            yield None


def split_camel_case(val):
    return re.sub('([a-z])([A-Z0-9])', '$1 $2', val).split()


def generalize_filter(filter_value):
    filter_value = re.escape(filter_value)

    def _generalize_character(char):
        return char + '+' if char.isalnum() else char
    generalized = (_generalize_character(char) for char in filter_value)
    return '(?i)' + ''.join(generalized)
