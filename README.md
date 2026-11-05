# audio_url_transformer

Turn a link someone shared, such as a YouTube video, a SoundCloud track or a Suno song, into a URL an audio player can actually play. [Accessible Apps](https://getaccessibleapps.com) uses it so a link in a post or feed can be played right where you found it.

## Install

```bash
pip install git+https://github.com/accessibleapps/audio_url_transformer.git
```

Depends on `requests` and [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Quick use

```python
from audio_url_transformer import AudioURLTransformer

transformer = AudioURLTransformer()
playable = transformer.transform("https://www.youtube.com/watch?v=...")
```

Or from the command line:

```bash
python -m audio_url_transformer "https://www.youtube.com/watch?v=..."
```

`transform(url)` returns one playable URL:

- Links that already end in an audio file extension (`.mp3`, `.m4a`, `.ogg`, `.wav`, `.flac` and so on) come back unchanged.
- YouTube, Twitter video and Vine links go through yt-dlp.
- Suno share links are read from the page's audio tag.
- audioboom and old audioboo links become their `.mp3` address.
- SoundCloud links need an API client ID: `AudioURLTransformer(soundcloud_client_id="...")`.
- Anything else raises `ValueError`.

`is_audio_url(url)` tells you whether a link is something it knows how to handle, without fetching anything.

## Picking the best stream: `resolve_info`

`transform` hands back whatever URL it finds. When you know what your player can decode, `resolve_info` picks the best option for it and tells you everything you need to fetch it:

```python
from audio_url_transformer import AudioURLTransformer, Capabilities, ResolveError

caps = Capabilities.from_client(["audio/mp4", "audio/webm", "audio/mpeg"], hls=True)
try:
    media = transformer.resolve_info(url, caps)
except ResolveError as e:
    print(e.code)  # "EXTRACT_FAILED" or "NO_AUDIO_RENDITION"

media.kind              # "progressive", "hls" or "prepared"
media.origin_url        # where to fetch it
media.required_headers  # headers the source needs
media.expires_at        # when a signed URL stops working, if known
media.is_live, media.title, media.duration_seconds
```

The order it prefers:

1. A plain file the client can decode: AAC first, then Opus, then MP3. Audio-only beats video, and it takes the highest bitrate up to 192 kbps.
2. An HLS stream, if the client says it supports HLS.
3. Otherwise a `prepared` rendition, with a `preparation_job` describing the work: remux it if it's already AAC, or transcode it to 160 kbps AAC. For live sources, it's a rolling AAC HLS stream (HLS clients only).

The choice is made from the stream metadata and the client's capabilities, not from site-specific format IDs. The descriptor contains signed source URLs and headers, so keep it on your server and don't pass it to clients.

## Tests

```bash
pip install -e ".[test]"
pytest
```
