import attr
from frozenlist2 import frozenlist


def frozenlist_or_none_converter(obj, map_fn=(lambda x: x)):
    if obj is not None:
        return frozenlist(map_fn(obj))
    return None


@attr.s(kw_only=True, frozen=True)
class FakePublishOptions(object):
    """Options controlling a repository"""

    rsync_extra_args = attr.ib(
        default=None, type=list, converter=frozenlist_or_none_converter  # type: ignore
    )
