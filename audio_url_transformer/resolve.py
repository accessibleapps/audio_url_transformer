"""Structured media resolution: ``resolve_info(url, capabilities)``.

``AudioURLTransformer.transform(url)`` returns one bare URL and is kept as is
for existing callers.  ``resolve_info`` instead returns an immutable
``MediaDescriptor`` describing the source and the single rendition chosen for
the client, including private delivery details (signed origin URL, expiry,
required request headers) that must stay on the server.

Rendition policy (sounds-todo chunk 12, "Which rendition to pick"):

1. Seekable progressive audio in a codec the client can decode, by family
   AAC/M4A, then Opus/WebM, then MP3.  Within a family audio-only beats muxed
   video, then the highest bitrate up to 192 kbps wins (or, if every candidate
   is above 192 kbps, the lowest one).
2. HLS, when the source offers it and the client supports HLS.
3. A finite source with nothing directly playable gets a ``prepared``
   rendition: remux when the input is already AAC, otherwise AAC 160 kbps.
4. A live source with nothing directly playable gets a ``prepared`` rolling
   AAC HLS rendition (2 s segments, 6-segment playlist), for HLS clients.

Selection depends only on the extracted metadata and the client
capabilities, never on site-specific format IDs.
"""
from __future__ import absolute_import

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

try:  # Python 3
    from urllib.parse import parse_qs, urlsplit
except ImportError:  # pragma: no cover
    from urlparse import parse_qs, urlsplit  # type: ignore

KIND_PROGRESSIVE = 'progressive'
KIND_HLS = 'hls'
KIND_PREPARED = 'prepared'

EXTRACT_FAILED = 'EXTRACT_FAILED'
NO_AUDIO_RENDITION = 'NO_AUDIO_RENDITION'

TARGET_MAX_ABR_KBPS = 192.0
PREPARED_AAC_KBPS = 160
LIVE_SEGMENT_SECONDS = 2
LIVE_PLAYLIST_SEGMENTS = 6

MAX_CLIENT_MIME_TYPES = 16
MAX_CLIENT_MIME_TYPE_LENGTH = 128

HLS_MIME_TYPE = 'application/vnd.apple.mpegurl'
PREPARED_MIME_TYPE = 'audio/mp4'
PREPARED_CODEC = 'mp4a.40.2'

# Codec family -> (family rank, audio MIME type the client must support).
FAMILY_AAC = 'aac'
FAMILY_OPUS = 'opus'
FAMILY_MP3 = 'mp3'
_FAMILY_ORDER = {FAMILY_AAC: 0, FAMILY_OPUS: 1, FAMILY_MP3: 2}

_DIRECT_EXTENSION_MIME = {
    '.m4a': ('audio/mp4', FAMILY_AAC),
    '.aac': ('audio/aac', FAMILY_AAC),
    '.mp4': ('audio/mp4', FAMILY_AAC),
    '.mp3': ('audio/mpeg', FAMILY_MP3),
    '.opus': ('audio/ogg', FAMILY_OPUS),
}

_HLS_PROTOCOLS = ('m3u8', 'm3u8_native')
_PROGRESSIVE_PROTOCOLS = ('http', 'https')
_PATH_EXPIRE_RE = re.compile(r'/expire/(\d+)(?:/|$)')


class ResolveError(Exception):
    """A resolution failure with a server-side error code.

    ``code`` is ``EXTRACT_FAILED`` or ``NO_AUDIO_RENDITION``.  Messages never
    contain signed origin URLs.
    """

    def __init__(self, code, message):
        # type: (str, str) -> None
        super(ResolveError, self).__init__('%s: %s' % (code, message))
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Capabilities:
    """What the client can decode (``PlaybackSupport`` in the browser)."""

    audio_mime_types: Tuple[str, ...] = ('audio/mp4',)
    hls: bool = False

    @classmethod
    def legacy(cls):
        # type: () -> Capabilities
        """Older clients: the AAC/M4A target only, no HLS."""
        return cls()

    @classmethod
    def from_client(cls, audio_mime_types, hls=False):
        # type: (Optional[Iterable[str]], bool) -> Capabilities
        """Validate client-reported capabilities.

        At most 16 MIME types of at most 128 characters each; an absent or
        empty list means a legacy client.
        """
        if audio_mime_types is None:
            return cls(hls=bool(hls))
        types = tuple(audio_mime_types)
        if len(types) > MAX_CLIENT_MIME_TYPES:
            raise ValueError('at most %d audio MIME types are allowed, got %d'
                             % (MAX_CLIENT_MIME_TYPES, len(types)))
        for mime in types:
            if not isinstance(mime, str) or not mime or len(mime) > MAX_CLIENT_MIME_TYPE_LENGTH:
                raise ValueError('invalid audio MIME type %r' % (mime,))
        if not types:
            return cls(hls=bool(hls))
        return cls(audio_mime_types=tuple(m.lower() for m in types), hls=bool(hls))

    def supports_mime(self, mime_type):
        # type: (str) -> bool
        return mime_type.lower() in self.audio_mime_types


@dataclass(frozen=True)
class PreparationJob:
    """Work a preparer must do before a ``prepared`` rendition is playable.

    ``action`` is ``remux`` (input already AAC), ``transcode`` (to AAC at
    ``target_bitrate_kbps``) or ``live_hls`` (rolling AAC HLS).
    """

    action: str
    input_format_id: Optional[str]
    target_codec: str = PREPARED_CODEC
    target_bitrate_kbps: Optional[int] = None
    fast_start: bool = True
    segment_seconds: Optional[int] = None
    playlist_segments: Optional[int] = None


@dataclass(frozen=True)
class Rendition:
    """One deliverable rendition.  All fields are private to the server."""

    rendition_id: str
    kind: str
    mime_type: str
    codec: Optional[str]
    origin_url: str
    expires_at: Optional[float]
    required_headers: Tuple[Tuple[str, str], ...]
    abr_kbps: Optional[float] = None
    audio_only: bool = True
    preparation_job: Optional[PreparationJob] = None


@dataclass(frozen=True)
class MediaDescriptor:
    """Private (server-side only) description of a resolved source."""

    source_id: str
    original_url: str
    title: Optional[str]
    duration_seconds: Optional[float]
    is_live: bool
    rendition: Rendition

    # Flat accessors matching the chunk 12 descriptor field names.
    @property
    def rendition_id(self):
        # type: () -> str
        return self.rendition.rendition_id

    @property
    def kind(self):
        # type: () -> str
        return self.rendition.kind

    @property
    def mime_type(self):
        # type: () -> str
        return self.rendition.mime_type

    @property
    def codec(self):
        # type: () -> Optional[str]
        return self.rendition.codec

    @property
    def origin_url(self):
        # type: () -> str
        return self.rendition.origin_url

    @property
    def expires_at(self):
        # type: () -> Optional[float]
        return self.rendition.expires_at

    @property
    def required_headers(self):
        # type: () -> Tuple[Tuple[str, str], ...]
        return self.rendition.required_headers

    @property
    def preparation_job(self):
        # type: () -> Optional[PreparationJob]
        return self.rendition.preparation_job


@dataclass(frozen=True)
class _Candidate:
    format_id: str
    url: str
    protocol: str
    family: Optional[str]
    acodec: Optional[str]
    audio_only: bool
    abr_kbps: Optional[float]
    container_mime: Optional[str]
    raw: Mapping[str, Any]


def resolve_info(url, capabilities=None, ydl=None):
    # type: (str, Optional[Capabilities], Any) -> MediaDescriptor
    """Resolve ``url`` into a ``MediaDescriptor`` for a client.

    ``ydl`` is a ``yt_dlp.YoutubeDL``-like object with
    ``extract_info(url, download=False, process=False)``.  It is only needed
    for URLs that are not direct audio file links.
    """
    caps = capabilities if capabilities is not None else Capabilities.legacy()
    direct = _resolve_direct(url, caps)
    if direct is not None:
        return direct
    if ydl is None:
        raise ValueError('resolve_info needs a YoutubeDL instance for %s' % url)
    try:
        info = ydl.extract_info(url, download=False, process=False)
    except Exception as exc:
        raise ResolveError(EXTRACT_FAILED, '%s: %s' % (type(exc).__name__, exc))
    if not isinstance(info, Mapping):
        raise ResolveError(EXTRACT_FAILED, 'extractor returned no media info')
    if info.get('_type') not in (None, 'video'):
        raise ResolveError(EXTRACT_FAILED, 'unsupported result type %r' % (info.get('_type'),))
    return descriptor_from_info(url, info, caps)


def needs_extractor(url, capabilities=None):
    # type: (str, Optional[Capabilities]) -> bool
    """True unless ``url`` is a direct audio link the client can play."""
    caps = capabilities if capabilities is not None else Capabilities.legacy()
    return _resolve_direct(url, caps) is None


def descriptor_from_info(original_url, info, capabilities):
    # type: (str, Mapping[str, Any], Capabilities) -> MediaDescriptor
    """Build a descriptor from an already extracted yt-dlp info dict."""
    is_live = bool(info.get('is_live')) or info.get('live_status') == 'is_live'
    duration = None if is_live else _as_float(info.get('duration'))
    rendition = select_rendition(info, capabilities, is_live)
    return MediaDescriptor(
        source_id=_source_id(original_url, info),
        original_url=original_url,
        title=info.get('title'),
        duration_seconds=duration,
        is_live=is_live,
        rendition=rendition,
    )


def select_rendition(info, capabilities, is_live):
    # type: (Mapping[str, Any], Capabilities, bool) -> Rendition
    candidates = _candidates(info)
    base_headers = info.get('http_headers') or {}

    progressive = [c for c in candidates
                   if c.protocol in _PROGRESSIVE_PROTOCOLS
                   and c.family is not None
                   and capabilities.supports_mime(_family_mime(c))]
    if progressive:
        best = min(progressive, key=_progressive_key)
        return _rendition(best, KIND_PROGRESSIVE, best.container_mime or _family_mime(best), base_headers)

    if capabilities.hls:
        hls = [c for c in candidates
               if c.protocol in _HLS_PROTOCOLS
               and (c.family is None or capabilities.supports_mime(_family_mime(c)))]
        if hls:
            best = min(hls, key=_hls_key)
            return _rendition(best, KIND_HLS, HLS_MIME_TYPE, base_headers)

    if not candidates:
        raise ResolveError(NO_AUDIO_RENDITION, 'source offers no audio formats')

    source = min(candidates, key=_preparation_input_key)
    if is_live:
        if not capabilities.hls:
            raise ResolveError(NO_AUDIO_RENDITION,
                               'live source has no rendition this client can decode without HLS')
        job = PreparationJob(action='live_hls', input_format_id=source.format_id,
                             target_bitrate_kbps=PREPARED_AAC_KBPS, fast_start=False,
                             segment_seconds=LIVE_SEGMENT_SECONDS,
                             playlist_segments=LIVE_PLAYLIST_SEGMENTS)
        return _rendition(source, KIND_PREPARED, HLS_MIME_TYPE, base_headers,
                          codec=PREPARED_CODEC, job=job)
    if source.family == FAMILY_AAC:
        job = PreparationJob(action='remux', input_format_id=source.format_id)
    else:
        job = PreparationJob(action='transcode', input_format_id=source.format_id,
                             target_bitrate_kbps=PREPARED_AAC_KBPS)
    return _rendition(source, KIND_PREPARED, PREPARED_MIME_TYPE, base_headers,
                      codec=PREPARED_CODEC, job=job)


def _resolve_direct(url, caps):
    # type: (str, Capabilities) -> Optional[MediaDescriptor]
    path = urlsplit(url).path.lower()
    for ext, (mime, family) in _DIRECT_EXTENSION_MIME.items():
        if path.endswith(ext):
            if not caps.supports_mime(_FAMILY_MIME[family]):
                return None
            rendition = Rendition(
                rendition_id='direct',
                kind=KIND_PROGRESSIVE,
                mime_type=mime,
                codec=None,
                origin_url=url,
                expires_at=_expiry_from_url(url),
                required_headers=(),
            )
            return MediaDescriptor(
                source_id=_url_hash_id(url),
                original_url=url,
                title=None,
                duration_seconds=None,
                is_live=False,
                rendition=rendition,
            )
    return None


_FAMILY_MIME = {FAMILY_AAC: 'audio/mp4', FAMILY_OPUS: 'audio/webm', FAMILY_MP3: 'audio/mpeg'}


def _family_mime(candidate):
    # type: (_Candidate) -> str
    if candidate.family == FAMILY_OPUS and candidate.container_mime == 'audio/ogg':
        return 'audio/ogg'
    return _FAMILY_MIME[candidate.family]  # type: ignore[index]


def _candidates(info):
    # type: (Mapping[str, Any]) -> Sequence[_Candidate]
    formats = info.get('formats')
    if not formats:
        formats = [info] if info.get('url') else []
    result = []
    for index, fmt in enumerate(formats):
        url = fmt.get('url')
        acodec = fmt.get('acodec')
        vcodec = fmt.get('vcodec')
        if not url or acodec == 'none':
            continue
        protocol = _protocol(fmt)
        if acodec is None and vcodec not in (None, 'none') and protocol not in _HLS_PROTOCOLS:
            # A video format that does not declare audio; HLS variants often
            # omit codecs, so only those are kept.
            continue
        ext = (fmt.get('audio_ext') if fmt.get('audio_ext') not in (None, 'none') else None) or fmt.get('ext')
        audio_only = vcodec == 'none'
        result.append(_Candidate(
            format_id=str(fmt.get('format_id') if fmt.get('format_id') is not None else index),
            url=url,
            protocol=protocol,
            family=_codec_family(acodec, ext),
            acodec=acodec if acodec not in (None, 'none') else None,
            audio_only=audio_only,
            abr_kbps=_as_float(fmt.get('abr')) or (_as_float(fmt.get('tbr')) if audio_only else None),
            container_mime=_container_mime(ext, audio_only),
            raw=fmt,
        ))
    return result


def _protocol(fmt):
    # type: (Mapping[str, Any]) -> str
    if fmt.get('fragments') or fmt.get('protocol') in ('http_dash_segments', 'dash'):
        return 'dash'
    protocol = fmt.get('protocol')
    if protocol:
        return str(protocol).split('+')[0]
    url = fmt.get('url') or ''
    if urlsplit(url).path.lower().endswith('.m3u8'):
        return 'm3u8_native'
    scheme = urlsplit(url).scheme.lower()
    return scheme or 'https'


def _codec_family(acodec, ext):
    # type: (Optional[str], Optional[str]) -> Optional[str]
    codec = (acodec or '').lower()
    if codec in ('mp3', 'mp4a.40.34', 'mp4a.6b'):
        return FAMILY_MP3
    if codec.startswith('mp4a') or codec == 'aac':
        return FAMILY_AAC
    if codec == 'opus':
        return FAMILY_OPUS
    if codec:
        return None  # a known but unsupported codec (vorbis, flac, ac-3, ...)
    ext = (ext or '').lower()
    if ext in ('m4a', 'aac'):
        return FAMILY_AAC
    if ext == 'opus':
        return FAMILY_OPUS
    if ext == 'mp3':
        return FAMILY_MP3
    return None


def _container_mime(ext, audio_only):
    # type: (Optional[str], bool) -> Optional[str]
    ext = (ext or '').lower()
    if ext in ('m4a', 'mp4'):
        return 'audio/mp4' if audio_only else 'video/mp4'
    if ext == 'webm':
        return 'audio/webm' if audio_only else 'video/webm'
    if ext in ('ogg', 'opus'):
        return 'audio/ogg'
    if ext == 'mp3':
        return 'audio/mpeg'
    if ext == 'aac':
        return 'audio/aac'
    return None


def _bitrate_key(abr):
    # type: (Optional[float]) -> Tuple[int, float]
    if abr is None:
        return (2, 0.0)
    if abr <= TARGET_MAX_ABR_KBPS:
        return (0, -abr)
    return (1, abr)


def _progressive_key(c):
    # type: (_Candidate) -> Tuple[Any, ...]
    return (_FAMILY_ORDER[c.family], not c.audio_only, _bitrate_key(c.abr_kbps), c.format_id)  # type: ignore[index]


def _hls_key(c):
    # type: (_Candidate) -> Tuple[Any, ...]
    return (not c.audio_only, _bitrate_key(c.abr_kbps), c.format_id)


def _preparation_input_key(c):
    # type: (_Candidate) -> Tuple[Any, ...]
    # Prefer an AAC input (remux, no generation loss), then any known codec.
    return (not c.audio_only, c.family != FAMILY_AAC, c.family is None,
            -(c.abr_kbps or 0.0), c.format_id)


def _rendition(candidate, kind, mime_type, base_headers, codec=None, job=None):
    # type: (_Candidate, str, str, Mapping[str, str], Optional[str], Optional[PreparationJob]) -> Rendition
    headers = dict(base_headers)
    headers.update(candidate.raw.get('http_headers') or {})
    cookies = candidate.raw.get('cookies')
    if cookies and 'Cookie' not in headers:
        headers['Cookie'] = cookies
    return Rendition(
        rendition_id=candidate.format_id,
        kind=kind,
        mime_type=mime_type,
        codec=codec if codec is not None else candidate.acodec,
        origin_url=candidate.url,
        expires_at=_expiry_from_url(candidate.url),
        required_headers=tuple(sorted((str(k), str(v)) for k, v in headers.items())),
        abr_kbps=candidate.abr_kbps,
        audio_only=candidate.audio_only,
        preparation_job=job,
    )


def _expiry_from_url(url):
    # type: (str) -> Optional[float]
    parts = urlsplit(url)
    values = parse_qs(parts.query).get('expire')
    if values:
        return _as_float(values[0])
    match = _PATH_EXPIRE_RE.search(parts.path)
    if match:
        return float(match.group(1))
    return None


def _source_id(original_url, info):
    # type: (str, Mapping[str, Any]) -> str
    extractor = info.get('extractor_key') or info.get('extractor')
    content_id = info.get('id')
    if extractor and content_id:
        return '%s:%s' % (str(extractor).lower(), content_id)
    return _url_hash_id(info.get('webpage_url') or original_url)


def _url_hash_id(url):
    # type: (str) -> str
    parts = urlsplit(url.strip())
    canonical = '%s://%s%s%s' % (parts.scheme.lower(), parts.netloc.lower(), parts.path,
                                 ('?' + parts.query) if parts.query else '')
    return 'url:' + hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:32]


def _as_float(value):
    # type: (Any) -> Optional[float]
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
