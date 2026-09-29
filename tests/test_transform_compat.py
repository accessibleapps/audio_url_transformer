"""The bare-URL entry point used by the production wrapper keeps working."""
import os
import subprocess
import sys

from audio_url_transformer import AudioURLTransformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_constructor_and_transform_signatures_unchanged():
    aut = AudioURLTransformer()
    assert aut.transform('https://files.example.com/a.MP3') == 'https://files.example.com/a.MP3'
    assert aut.is_audio_url('https://files.example.com/a.ogg')
    assert AudioURLTransformer(soundcloud_client_id='cid').soundcloud_api.client_id == 'cid'


def test_transform_youtube_still_returns_format_18_url(fake_ydl, load_info):
    info = load_info('youtube_vod_no_format_18')
    info['formats'].append({'format_id': '18', 'url': 'https://cdn.example.com/18.mp4',
                            'ext': 'mp4', 'acodec': 'mp4a.40.2', 'vcodec': 'avc1.42001E'})
    aut = AudioURLTransformer()
    aut.youtube_dl = fake_ydl(info)
    assert aut.transform('https://www.youtube.com/watch?v=AbCdEfGhIjK') == 'https://cdn.example.com/18.mp4'
    assert aut.youtube_dl.calls == [('https://www.youtube.com/watch?v=AbCdEfGhIjK', False, False)]


def test_transform_sndup_and_audioboom_unchanged():
    aut = AudioURLTransformer()
    assert aut.transform('http://www.sndup.net/43sc/a') == 'http://sndup.net/43sc/a'
    assert aut.transform('https://audioboom.com/boos/2502158-first') == 'https://audioboom.com/boos/2502158.mp3'


def test_package_main_prints_bare_url():
    # Runs in a child process: the in-process socket block does not apply,
    # but a direct audio URL needs no network.
    out = subprocess.check_output(
        [sys.executable, '-m', 'audio_url_transformer', 'https://files.example.com/x.mp3'],
        cwd=ROOT)
    assert out.decode().strip() == 'https://files.example.com/x.mp3'
