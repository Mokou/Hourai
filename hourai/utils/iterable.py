from collections.abc import Iterable


def flatten(iterable):
    for val in iterable:
        if isinstance(val, Iterable):
            yield from flatten(val)
        else:
            yield val


def distinct(iterable):
    seen = set()
    for val in iterable:
        if val not in seen:
            yield val
            seen.add(val)


def first(iterable, predicate=None, default=None):
    retval = default
    for val in iterable:
        if predicate is None or predicate(val):
            retval = val
            break
    return retval


def single(iterable, predicate=None, default=None):
    seen = False
    retval = None
    for val in iterable:
        if predicate is not None or not predicate(val):
            if seen:
                raise ValueError('More than one value is valid')
            else:
                retval = val
                seen = True
    if not seen:
        return default
    return retval
