import enum
from . import proto
from datetime import datetime, timezone
from sqlalchemy import types
from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.schema import Table, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

feed_channels_table = Table('feed_channels', Base.metadata,
                            Column('feed_id', types.BigInteger,
                                   ForeignKey('feeds.id')),
                            Column('channel_id', types.BigInteger,
                                   ForeignKey('channels.id')))


class UnixTimestamp(types.TypeDecorator):
    impl = types.BigInteger

    def __init__(self):
        types.TypeDecorator.__init__(self)

    def process_bind_param(self, value, dialect):
        return int(value.replace(tzinfo=timezone.utc).timestamp() * 1000)

    def process_result_value(self, value, dialect):
        return datetime.utcfromtimestamp(value / 1000)


class Protobuf(types.TypeDecorator):
    impl = types.LargeBinary

    def __init__(self, message_type):
        self.message_type = message_type
        types.TypeDecorator.__init__(self)

    def process_bind_param(self, value, dialect):
        assert isinstance(value, self.message_type), (
            f'{type(value)} cannot be assigned to a column of type '
            f'{self.message_type}')
        return value.SerializeToString()

    def process_result_value(self, value, dialect):
        msg = self.message_type()
        msg.ParseFromString(value)
        return msg


class PendingAction(Base):
    __tablename__ = 'pending_actions'

    id = Column(types.Integer, primary_key=True)
    timestamp = Column(UnixTimestamp, nullable=False)
    data = Column(Protobuf(proto.Action), nullable=False)


class Username(Base):
    __tablename__ = 'usernames'

    user_id = Column(types.BigInteger, primary_key=True, autoincrement=False)
    timestamp = Column(UnixTimestamp, primary_key=True)
    name = Column(types.String(255), nullable=False)
    discriminator = Column(types.Integer)

    def __str__(self):
        if self.discriminator is not None:
            name = f"{self.name}#{self.discriminator}"
        else:
            name = self.name
        return f"Username({self.user_id}, {self.timestamp}, {name})"

    def to_fullname(self):
        return (self.name
                if self.discriminator is None
                else f'{self.name}#{self.discriminator}')

    @classmethod
    def from_resource(cls, resource, *args, **kwargs):
        kwargs.update({
            'id': resource.id,
            'username': resource.name,
            'timestamp': datetime.utcnow(),
        })
        return cls(*args, **kwargs)


Index("idx_username_user_id", Username.user_id)


class Alias(Base):
    __tablename__ = 'aliases'

    guild_id = Column(types.BigInteger, primary_key=True, autoincrement=False)
    name = Column(types.String(2000), primary_key=True)
    content = Column(types.String(2000))


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(types.BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(types.BigInteger, nullable=True)

    feeds = relationship("Feed", secondary=feed_channels_table,
                         back_populates="channels")

    def get_resource(self, bot):
        return bot.get_channel(self.id)


@enum.unique
class FeedType(enum.Enum):
    RSS = enum.auto()
    REDDIT = enum.auto()
    HACKER_NEWS = enum.auto()
    TWITTER = enum.auto()


class Feed(Base):
    __tablename__ = 'feeds'
    __table_args__ = (UniqueConstraint('type', 'source'),)

    id = Column(types.Integer, primary_key=True, autoincrement=True)
    _type = Column('type', types.String(255), nullable=False)
    source = Column(types.String(8192), nullable=False)
    last_updated = Column(UnixTimestamp, nullable=False)

    channels = relationship("Channel", secondary=feed_channels_table,
                            back_populates="feeds")

    @property
    def type(self):
        return FeedType._member_map_.get(self._type, None)

    @type.setter
    def set_type(self, value):
        assert isinstance(value, FeedType)
        self._type = value.name

    def get_channels(self, bot):
        """ Returns a generator for all channels in the feed. """

        return (ch.get_resource(bot) for ch in self.channels)
