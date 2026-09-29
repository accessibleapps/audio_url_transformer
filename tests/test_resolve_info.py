import dataclasses
import random
import socket

import pytest

from audio_url_transformer import (
    AudioURLTransformer,
    Capabilities,
    MediaDescriptor,
    ResolveError,
    resolve_info,
)
from audio_url_transformer.resolve import (
    EXTRACT_FAILED,
    HLS_MIME_TYPE,
    KIND_HLS,
    KIND_PREPARED,
    KIND_PROGRESSIVE,
    NO_AUDIO_RENDITION,
)

YT_URL = 'https://www.youtube.com/watch?v=AbCdEfGhIjK'
ALL_AUDIO = Capabilities.from_client(['audio/mp4', 'audio/webm', 'audio/ogg', 'audio/mpeg'], hls=True)


def resolve(fake_ydl, info, caps=None, url=YT_URL):
    return resolve_info(url, caps, ydl=fake_ydl(info))


def audio_format(format_id, acodec, abr, ext='m4a', vcodec='none', **extra):
    fmt = {
        'format_id': format_id,
        'url': 'https://cdn.example.com/%s.%s' % (format_id, ext),
        'ext': ext,
        'acodec': acodec,
        'vcodec': vcodec,
        'abr': abr,
    }
    fmt.update(extra)
    return fmt


def info_with(formats, **extra):
    info = {'id': 'x1', 'extractor_key': 'Example', 'title': 'T', 'duration': 60, 'formats': formats}
    info.update(extra)
    return info


# --- Transformer acceptance ("Done when" row) -------------------------------

def test_no_format_18_picks_aac_audio_only(fake_ydl, load_info):
    ydl = fake_ydl(load_info('youtube_vod_no_format_18'))
    d = resolve_info(YT_URL, Capabilities.legacy(), ydl=ydl)
    assert isinstance(d, MediaDescriptor)
    assert d.kind == KIND_PROGRESSIVE
    assert d.rendition_id == '140'
    assert d.mime_type == 'audio/mp4'
    assert d.codec == 'mp4a.40.2'
    assert d.duration_seconds == 212.0
    assert d.is_live is False
    assert d.title == 'Fixture Video'
    assert d.source_id == 'youtube:AbCdEfGhIjK'
    assert d.original_url == YT_URL
    assert ydl.calls == [(YT_URL, False, False)]


def test_aac_family_beats_opus_even_when_client_supports_both(fake_ydl, load_info):
    d = resolve(fake_ydl, load_info('youtube_vod_no_format_18'), ALL_AUDIO)
    assert d.rendition_id == '140'


def test_opus_when_client_lacks_aac(fake_ydl, load_info):
    caps = Capabilities.from_client(['audio/webm'])
    d = resolve(fake_ydl, load_info('youtube_vod_no_format_18'), caps)
    assert d.rendition_id == '251'
    assert d.mime_type == 'audio/webm'
    assert d.codec == 'opus'


def test_highest_bitrate_up_to_192(fake_ydl):
    info = info_with([
        audio_format('lo', 'mp4a.40.5', 48),
        audio_format('mid', 'mp4a.40.2', 160),
        audio_format('hi', 'mp4a.40.2', 256),
    ])
    assert resolve(fake_ydl, info).rendition_id == 'mid'


def test_lowest_above_192_when_nothing_at_or_below(fake_ydl):
    info = info_with([
        audio_format('a320', 'mp4a.40.2', 320),
        audio_format('a256', 'mp4a.40.2', 256),
    ])
    assert resolve(fake_ydl, info).rendition_id == 'a256'


def test_exactly_192_is_within_cap(fake_ydl):
    info = info_with([audio_format('a192', 'mp4a.40.2', 192), audio_format('a193', 'mp4a.40.2', 193)])
    assert resolve(fake_ydl, info).rendition_id == 'a192'


def test_audio_only_beats_muxed_video(fake_ydl):
    info = info_with([
        audio_format('muxed', 'mp4a.40.2', 96, ext='mp4', vcodec='avc1.42001E'),
        audio_format('audio', 'mp4a.40.5', 48),
    ])
    d = resolve(fake_ydl, info)
    assert d.rendition_id == 'audio'
    assert d.rendition.audio_only is True


def test_muxed_video_used_when_it_is_the_only_compatible_progressive(fake_ydl):
    info = info_with([
        audio_format('18', 'mp4a.40.2', 96, ext='mp4', vcodec='avc1.42001E'),
        audio_format('251', 'opus', 135, ext='webm'),
    ])
    d = resolve(fake_ydl, info, Capabilities.legacy())
    assert d.rendition_id == '18'
    assert d.mime_type == 'video/mp4'
    assert d.rendition.audio_only is False


def test_mp3_is_last_family(fake_ydl):
    info = info_with([audio_format('mp3', 'mp3', 128, ext='mp3'), audio_format('opus', 'opus', 64, ext='webm')])
    caps = Capabilities.from_client(['audio/mpeg', 'audio/webm'])
    assert resolve(fake_ydl, info, caps).rendition_id == 'opus'
    caps = Capabilities.from_client(['audio/mpeg'])
    d = resolve(fake_ydl, info, caps)
    assert d.rendition_id == 'mp3'
    assert d.mime_type == 'audio/mpeg'


def test_selection_is_independent_of_format_ids_and_order(fake_ydl, load_info):
    info = load_info('youtube_vod_no_format_18')
    for fmt in info['formats']:
        fmt['format_id'] = 'opaque-' + fmt['url'][-3:]
    rng = random.Random(1234)
    picked = set()
    for _ in range(10):
        rng.shuffle(info['formats'])
        d = resolve(fake_ydl, info)
        picked.add(d.origin_url)
    assert picked == {'https://rr1.example.googlevideo.com/videoplayback?itag=140&expire=1790000000&sig=SECRET140'}


def test_finite_hls_stays_finite(fake_ydl, load_info):
    d = resolve(fake_ydl, load_info('hls_vod'), ALL_AUDIO)
    assert d.kind == KIND_HLS
    assert d.mime_type == HLS_MIME_TYPE
    assert d.is_live is False
    assert d.duration_seconds == 1800.5
    assert d.rendition_id == 'hls-128'
    assert d.origin_url.endswith('audio_128.m3u8')


def test_live_hls_stays_live(fake_ydl, load_info):
    d = resolve(fake_ydl, load_info('youtube_live_hls'), ALL_AUDIO,
                url='https://www.youtube.com/watch?v=LiVeStReAm1')
    assert d.kind == KIND_HLS
    assert d.is_live is True
    assert d.duration_seconds is None
    assert d.expires_at == 1790001234.0


def test_live_duration_is_dropped_even_if_extractor_reports_one(fake_ydl, load_info):
    info = load_info('youtube_live_hls')
    info['duration'] = 3600
    d = resolve(fake_ydl, info, ALL_AUDIO)
    assert d.is_live is True
    assert d.duration_seconds is None


def test_unknown_duration_stays_null(fake_ydl):
    info = info_with([audio_format('a', 'mp4a.40.2', 128)])
    del info['duration']
    assert resolve(fake_ydl, info).duration_seconds is None
    info['duration'] = None
    assert resolve(fake_ydl, info).duration_seconds is None


def test_expiry_and_headers_survive_privately(fake_ydl, load_info):
    info = load_info('youtube_vod_no_format_18')
    for fmt in info['formats']:
        if fmt['format_id'] == '140':
            fmt['http_headers'] = {'Referer': 'https://www.youtube.com/'}
            fmt['cookies'] = 'SID=abc'
    d = resolve(fake_ydl, info)
    assert d.expires_at == 1790000000.0
    assert 'sig=SECRET140' in d.origin_url
    headers = dict(d.required_headers)
    assert headers == {
        'Accept-Language': 'en-us,en;q=0.5',
        'Cookie': 'SID=abc',
        'Referer': 'https://www.youtube.com/',
        'User-Agent': 'Mozilla/5.0 (fixture)',
    }


def test_no_expiry_is_null(fake_ydl):
    d = resolve(fake_ydl, info_with([audio_format('a', 'mp4a.40.2', 128)]))
    assert d.expires_at is None
    assert d.required_headers == ()


# --- Prepared fallback -------------------------------------------------------

def test_dash_only_finite_source_is_prepared_by_remux(fake_ydl, load_info):
    d = resolve(fake_ydl, load_info('dash_only'), ALL_AUDIO)
    assert d.kind == KIND_PREPARED
    assert d.mime_type == 'audio/mp4'
    assert d.codec == 'mp4a.40.2'
    assert d.duration_seconds == 95.0
    job = d.preparation_job
    assert job.action == 'remux'
    assert job.input_format_id == 'dash-audio-aac'
    assert job.fast_start is True


def test_unsupported_codec_is_transcoded_to_aac_160(fake_ydl):
    info = info_with([audio_format('vorbis', 'vorbis', 128, ext='ogg')])
    d = resolve(fake_ydl, info, ALL_AUDIO)
    assert d.kind == KIND_PREPARED
    assert d.preparation_job.action == 'transcode'
    assert d.preparation_job.target_bitrate_kbps == 160
    assert d.preparation_job.input_format_id == 'vorbis'


def test_legacy_client_gets_prepared_aac_for_opus_only_source(fake_ydl):
    info = info_with([audio_format('251', 'opus', 135, ext='webm')])
    d = resolve(fake_ydl, info, Capabilities.legacy())
    assert d.kind == KIND_PREPARED
    assert d.mime_type == 'audio/mp4'
    assert d.preparation_job.action == 'transcode'


def test_finite_hls_without_client_hls_is_prepared(fake_ydl, load_info):
    d = resolve(fake_ydl, load_info('hls_vod'), Capabilities.legacy())
    assert d.kind == KIND_PREPARED
    assert d.is_live is False
    assert d.preparation_job.action == 'remux'
    assert d.preparation_job.input_format_id == 'hls-128'


def test_live_unsupported_codec_gets_rolling_aac_hls(fake_ydl):
    info = info_with([audio_format('icecast', 'vorbis', 128, ext='ogg')], is_live=True)
    d = resolve(fake_ydl, info, ALL_AUDIO)
    assert d.kind == KIND_PREPARED
    assert d.is_live is True
    assert d.duration_seconds is None
    assert d.mime_type == HLS_MIME_TYPE
    job = d.preparation_job
    assert job.action == 'live_hls'
    assert (job.segment_seconds, job.playlist_segments) == (2, 6)


def test_live_without_decodable_rendition_or_hls_fails_visibly(fake_ydl, load_info):
    with pytest.raises(ResolveError) as err:
        resolve(fake_ydl, load_info('youtube_live_hls'), Capabilities.legacy())
    assert err.value.code == NO_AUDIO_RENDITION


def test_live_progressive_compatible_stream(fake_ydl):
    info = info_with([audio_format('radio', 'mp3', 128, ext='mp3')], live_status='is_live')
    d = resolve(fake_ydl, info, Capabilities.from_client(['audio/mpeg']))
    assert d.kind == KIND_PROGRESSIVE
    assert d.is_live is True


# --- Errors ------------------------------------------------------------------

def test_no_audio_formats_is_no_audio_rendition(fake_ydl):
    info = info_with([{'format_id': 'v', 'url': 'https://cdn.example.com/v.mp4', 'acodec': 'none', 'vcodec': 'avc1'}])
    with pytest.raises(ResolveError) as err:
        resolve(fake_ydl, info)
    assert err.value.code == NO_AUDIO_RENDITION


def test_extractor_failure_is_extract_failed(fake_ydl):
    with pytest.raises(ResolveError) as err:
        resolve_info(YT_URL, None, ydl=fake_ydl(error=RuntimeError('Video unavailable')))
    assert err.value.code == EXTRACT_FAILED
    assert 'Video unavailable' in err.value.message


def test_playlist_result_is_extract_failed(fake_ydl):
    with pytest.raises(ResolveError) as err:
        resolve(fake_ydl, {'_type': 'playlist', 'entries': []})
    assert err.value.code == EXTRACT_FAILED


# --- Records, identity, capabilities -----------------------------------------

def test_descriptor_and_rendition_are_immutable(fake_ydl, load_info):
    d = resolve(fake_ydl, load_info('youtube_vod_no_format_18'))
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.title = 'changed'
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.rendition.origin_url = 'https://evil.example/'
    hash(d)


def test_source_id_falls_back_to_canonical_url_hash(fake_ydl):
    info = info_with([audio_format('a', 'mp4a.40.2', 128)])
    del info['id']
    info['webpage_url'] = 'HTTPS://Media.Example.com/track?id=1'
    a = resolve(fake_ydl, info).source_id
    info['webpage_url'] = 'https://media.example.com/track?id=1'
    b = resolve(fake_ydl, info).source_id
    assert a == b
    assert a.startswith('url:') and len(a) == 36


def test_direct_audio_url_needs_no_extractor():
    d = resolve_info('https://files.example.com/song.mp3?expire=1790000099',
                     Capabilities.from_client(['audio/mpeg']))
    assert d.kind == KIND_PROGRESSIVE
    assert d.mime_type == 'audio/mpeg'
    assert d.duration_seconds is None
    assert d.expires_at == 1790000099.0


def test_capabilities_validation():
    assert Capabilities.from_client(None) == Capabilities.legacy()
    assert Capabilities.from_client([], hls=True) == Capabilities(hls=True)
    assert Capabilities.from_client(['Audio/MP4']).supports_mime('audio/mp4')
    with pytest.raises(ValueError):
        Capabilities.from_client(['audio/x-%d' % i for i in range(17)])
    with pytest.raises(ValueError):
        Capabilities.from_client(['audio/' + 'x' * 128])
    with pytest.raises(ValueError):
        Capabilities.from_client([''])


def test_transformer_method_uses_its_youtube_dl(fake_ydl, load_info):
    aut = AudioURLTransformer()
    aut.youtube_dl = fake_ydl(load_info('youtube_vod_no_format_18'))
    d = aut.resolve_info(YT_URL)
    assert d.rendition_id == '140'


def test_network_is_blocked_in_unit_tests():
    with pytest.raises(AssertionError):
        socket.create_connection(('example.com', 80))
