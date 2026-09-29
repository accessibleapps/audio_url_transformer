"""Live network smoke check (formerly test_audio_url_transformer.py).

This hits real services, so it is not part of the pytest suite.  Run it
explicitly with ``python -m audio_url_transformer.smoke`` or the
``audio-url-transformer-smoke`` console script.
"""
from __future__ import absolute_import, print_function

import sys

from .audio_url_transformer import AudioURLTransformer

SOUNDCLOUD_CLIENT_ID = '6fa58c015833fc68768f361ca8dbbe93'

TEST_URLS = [
    'http://soundcloud.com/virginmagneticmaterial/bon-iver-michicant-virgin',
    'http://sndup.net/43sc/a',
    'http://twup.me/uE',
    'https://audioboo.fm/boos/2198170-vipadvisor-gas-vs-electric-cooker',
    'https://boo.fm/b2198170',
    'https://audioboom.com/boos/2502158-first-impressions-of-audioboom',
    'https://www.youtube.com/watch?v=v8qoB1XwtHM',
    'http://youtu.be/6GZDBO_TOHg',
]


def main(argv=None):
    urls = list(argv if argv is not None else sys.argv[1:]) or TEST_URLS
    aut = AudioURLTransformer(soundcloud_client_id=SOUNDCLOUD_CLIENT_ID)
    failures = 0
    for url in urls:
        try:
            print(aut.transform(url))
        except Exception as exc:
            failures += 1
            print('FAILED %s: %s: %s' % (url, type(exc).__name__, exc), file=sys.stderr)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
