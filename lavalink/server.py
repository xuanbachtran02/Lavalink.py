"""
MIT License

Copyright (c) 2017-present Devoxin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

This module serves to contain all entities which are deserialized using responses from
the Lavalink server.
"""
from enum import Enum as _Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from uuid import uuid4

from .errors import InvalidTrack

if TYPE_CHECKING:
    from .abc import DeferredAudioTrack


class Enum(_Enum):
    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.value == other.value  # pylint: disable=comparison-with-callable

        if isinstance(other, str):
            return self.value.lower() == other.lower()  # pylint: disable=comparison-with-callable

        return False

    @classmethod
    def from_str(cls, other: str):
        try:
            return cls[other.upper()]
        except KeyError:
            try:
                return cls(other)
            except ValueError as error:
                raise ValueError(f'{other} is not a valid {cls.__name__} enum!') from error


class AudioTrack:
    """
    .. _ISRC: https://en.wikipedia.org/wiki/International_Standard_Recording_Code

    Represents an AudioTrack.

    Parameters
    ----------
    data: Union[Dict[str, Union[Optional[str], bool, int]], :class:`AudioTrack`]
        The data to initialise an AudioTrack from.
    requester: :class:`any`
        The requester of the track.
    extra: Dict[Any, Any]
        Any extra information to store in this AudioTrack.

    Attributes
    ----------
    track: Optional[:class:`str`]
        The base64-encoded string representing a Lavalink-readable AudioTrack.
        This is marked optional as it could be None when it's not set by a custom :class:`Source`,
        which is expected behaviour when the subclass is a :class:`DeferredAudioTrack`.
    identifier: :class:`str`
        The track's id. For example, a youtube track's identifier will look like ``dQw4w9WgXcQ``.
    is_seekable: :class:`bool`
        Whether the track supports seeking.
    author: :class:`str`
        The track's uploader.
    duration: :class:`int`
        The duration of the track, in milliseconds.
    stream: :class:`bool`
        Whether the track is a live-stream.
    title: :class:`str`
        The title of the track.
    uri: :class:`str`
        The full URL of track.
    artwork_url: Optional[:class:`str`]
        A URL pointing to the track's artwork, if applicable.
    isrc: Optional[:class:`str`]
        The `ISRC`_ for the track, if applicable.
    position: :class:`int`
        The playback position of the track, in milliseconds.
        This is a read-only property; setting it won't have any effect.
    source_name: :class:`str`
        The name of the source that this track was created by.
    requester: :class:`int`
        The ID of the user that requested this track.
    plugin_info: Optional[Dict[str, Any]]
        Addition track info provided by plugins.
    user_data: Optional[Dict[str, Any]]
        The user data that was attached to the track, if any.
    extra: Dict[str, Any]
        Any extra properties given to this AudioTrack will be stored here.
    """
    __slots__ = ('__unique_id', 'raw', 'track', 'identifier', 'is_seekable', 'author', 'duration', 'stream', 'title', 'uri',
                 'artwork_url', 'isrc', 'position', 'source_name', 'plugin_info', 'user_data', 'extra')

    def __init__(self, data: dict, requester: int = 0, **extra):
        self.__unique_id: str = uuid4().hex

        if isinstance(data, AudioTrack):
            extra = {**data.extra, **extra}
            data = data.raw

        self.raw: Dict[str, Union[Optional[str], bool, int]] = data
        info = data.get('info', data)

        try:
            self.track: Optional[str] = data.get('encoded')
            self.identifier: str = info['identifier']
            self.is_seekable: bool = info['isSeekable']
            self.author: str = info['author']
            self.duration: int = info['length']
            self.stream: bool = info['isStream']
            self.title: str = info['title']
            self.uri: str = info['uri']
            self.artwork_url: Optional[str] = info.get('artworkUrl')
            self.isrc: Optional[str] = info.get('isrc')
            self.position: int = info.get('position', 0)
            self.source_name: str = info.get('sourceName', 'unknown')
            self.plugin_info: Optional[Dict[str, Any]] = data.get('pluginInfo')
            self.user_data: Optional[Dict[str, Any]] = data.get('userData')
            self.extra: Dict[str, Any] = {**extra, 'requester': requester}
        except KeyError as error:
            raise InvalidTrack(f'Cannot build a track from partial data! (Missing key: {error.args[0]})') from error

    def __getitem__(self, name):
        if name == 'info':
            return self

        return super().__getattribute__(name)

    @classmethod
    def from_dict(cls, mapping: dict):
        return cls(mapping)

    @property
    def unique_id(self) -> str:
        """
        A unique ID assigned to the track during creation.
        This is a hex string generated by ``uuid.uuid4()``.

        This exists for internal purposes, however may be used outside of the library.
        It is strongly advised that this ID is not changed.
        """
        return self.__unique_id

    @property
    def requester(self) -> int:
        return self.extra['requester']

    @requester.setter
    def requester(self, requester):
        self.extra['requester'] = requester

    def __repr__(self):
        return f'<AudioTrack title={self.title} identifier={self.identifier}>'


class EndReason(Enum):
    FINISHED = 'finished'
    LOAD_FAILED = 'loadFailed'
    STOPPED = 'stopped'
    REPLACED = 'replaced'
    CLEANUP = 'cleanup'

    def may_start_next(self) -> bool:
        """
        Returns whether the next track may be started from this event.

        This is mostly used as a hint to determine whether the ``track_end_event`` should be
        responsible for playing the next track.

        Returns
        -------
        :class:`bool`
            Whether the next track may be started.
        """
        return self is EndReason.FINISHED or self is EndReason.LOAD_FAILED


class LoadType(Enum):
    TRACK = 'TRACK'
    PLAYLIST = 'PLAYLIST'
    SEARCH = 'SEARCH'
    EMPTY = 'EMPTY'
    ERROR = 'ERROR'


class Severity(Enum):
    COMMON = 'common'
    SUSPICIOUS = 'suspicious'
    FAULT = 'fault'


class PlaylistInfo:
    """
    Attributes
    ----------
    name: :class:`str`
        The name of the playlist.
    selected_track: :class:`int`
        The index of the selected/highlighted track.
        This will be -1 if there is no selected track.
    """
    __slots__ = ('name', 'selected_track')

    def __init__(self, name: str, selected_track: int = -1):
        self.name: str = name
        self.selected_track: int = selected_track

    def __getitem__(self, k):  # Exists only for compatibility, don't blame me
        if k == 'selectedTrack':
            k = 'selected_track'
        return self.__getattribute__(k)

    @classmethod
    def from_dict(cls, mapping: dict):
        return cls(mapping.get('name'), mapping.get('selectedTrack', -1))

    @classmethod
    def none(cls):
        return cls('', -1)

    def __repr__(self):
        return f'<PlaylistInfo name={self.name} selected_track={self.selected_track}>'


class LoadResultError:
    """
    Attributes
    ----------
    message: :class:`str`
        The error message.
    severity: :enum:`Severity`
        The severity of the error.
    cause: :class:`str`
        The cause of the error.
    """
    __slots__ = ('message', 'severity', 'cause')

    def __init__(self, error: Dict[str, Any]):
        self.message: str = error['message']
        self.severity: Severity = Severity.from_str(error['severity'])
        self.cause: str = error['cause']


class LoadResult:
    """
    Attributes
    ----------
    load_type: :class:`LoadType`
        The load type of this result.
    tracks: List[Union[:class:`AudioTrack`, :class:`DeferredAudioTrack`]]
        The tracks in this result.
    playlist_info: Optional[:class:`PlaylistInfo`]
        The playlist metadata for this result.
        The :class:`PlaylistInfo` could contain empty/false data if the :class:`LoadType`
        is not :enum:`LoadType.PLAYLIST`.
    plugin_info: Optional[Dict[:class:`str`, Any]]
        Additional playlist info provided by plugins.
    error: Optional[:class:`LoadResultError`]
        The error associated with this ``LoadResult``.
        This will be ``None`` if :attr:`load_type` is not :attr:`LoadType.ERROR`.
    """
    __slots__ = ('load_type', 'playlist_info', 'tracks', 'plugin_info', 'error')

    def __init__(self, load_type: LoadType, tracks: List[Union[AudioTrack, 'DeferredAudioTrack']],
                 playlist_info: Optional[PlaylistInfo] = PlaylistInfo.none(), plugin_info: Optional[Dict[str, Any]] = None,
                 error: Optional[LoadResultError] = None):
        self.load_type: LoadType = load_type
        self.playlist_info: PlaylistInfo = playlist_info
        self.tracks: List[Union[AudioTrack, 'DeferredAudioTrack']] = tracks
        self.plugin_info: Optional[Dict[str, Any]] = plugin_info
        self.error: Optional[LoadResultError] = error

    def __getitem__(self, k):  # Exists only for compatibility, don't blame me
        if k == 'loadType':
            k = 'load_type'
        elif k == 'playlistInfo':
            k = 'playlist_info'

        return self.__getattribute__(k)

    @classmethod
    def empty(cls):
        return LoadResult(LoadType.EMPTY, [])

    @classmethod
    def from_dict(cls, mapping: dict):
        plugin_info: Optional[dict] = None
        playlist_info: Optional[PlaylistInfo] = PlaylistInfo.none()
        tracks: Optional[Union[AudioTrack, 'DeferredAudioTrack']] = []

        data: Union[List[Dict[str, Any]], Dict[str, Any]] = mapping['data']
        load_type = LoadType.from_str(mapping['loadType'])

        if isinstance(data, dict):
            plugin_info = data.get('pluginInfo')

        if load_type == LoadType.TRACK:
            tracks = [AudioTrack(data, 0)]
        elif load_type == LoadType.PLAYLIST:
            playlist_info = PlaylistInfo.from_dict(data['info'])
            tracks = [AudioTrack(track, 0) for track in data['tracks']]
        elif load_type == LoadType.SEARCH:
            tracks = [AudioTrack(track, 0) for track in data]
        elif load_type == LoadType.ERROR:
            error = LoadResultError(data)
            return cls(load_type, [], playlist_info, plugin_info, error)

        return cls(load_type, tracks, playlist_info, plugin_info)

    @property
    def selected_track(self) -> Optional[AudioTrack]:
        """
        Convenience method for returning the selected track using
        :attr:`PlaylistInfo.selected_track`.

        This could be ``None`` if :attr:`playlist_info` is ``None``,
        or :attr:`PlaylistInfo.selected_track` is an invalid number.

        Returns
        -------
        Optional[:class:`AudioTrack`]
        """
        if self.playlist_info is not None:
            index = self.playlist_info.selected_track

            if 0 <= index < len(self.tracks):
                return self.tracks[index]

        return None

    def __repr__(self):
        return f'<LoadResult load_type={self.load_type} playlist_info={self.playlist_info} tracks=[{len(self.tracks)} item(s)]>'


class Plugin:
    """
    Represents a Lavalink server plugin.

    Parameters
    ----------
    data: Dict[str, Any]
        The data to initialise a Plugin from.

    Attributes
    ----------
    name: :class:`str`
        The name of the plugin.
    version: :class:`str`
        The version of the plugin.
    """
    __slots__ = ('name', 'version')

    def __init__(self, data: Dict[str, Any]):
        self.name: str = data['name']
        self.version: str = data['version']

    def __str__(self):
        return f'{self.name} v{self.version}'

    def __repr__(self):
        return f'<Plugin name={self.name} version={self.version}>'
