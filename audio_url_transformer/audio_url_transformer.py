from __future__ import absolute_import
from logging import getLogger
logger = getLogger('audio_url_transformer')

import re
from . import soundcloud


class AudioURLTransformer(object):
 audio_extensions = ('.mp3', '.wav', '.ogg', '.flac', '.wma', '.m4a', '.aac', '.mp4')

 def __init__(self, soundcloud_client_id=None):
  if soundcloud_client_id:
   self.soundcloud_api = soundcloud.SoundCloudAPI(soundcloud_client_id)
   logger.debug("Initialized Soundcloud support")
  self.youtube_dl = None

 def transform(self, url):
  if url.lower().endswith(self.audio_extensions):
   return url
  for (regexp, processor) in self.matches.items():
   if not regexp.search(url):
    continue
   return processor(self, url)
  raise ValueError("Unable to find a processor for url %s" % url)

 def is_audio_url(self, url):
  if url.endswith(self.audio_extensions):
   return True
  for regexp in self.matches:
   if regexp.search(url):
    return True
  return False

 def transform_soundcloud(self, url):
  return self.soundcloud_api.get_stream_url(url)

 def transform_sndup(self, url):
  return re.sub(r'(http://(?:www\.)?sndup.net/(.+)/a)', r'http://sndup.net/\2/a', url)

 def transform_twup(self, url):
  return re.sub(r'(http://(?:www\.)?twup.me/.+)', r'\1', url)

 def transform_audioboom(self, url, r):
  return r.sub(r'https://audioboom.com/boos/\1.mp3', url)

 def youtube_dl_transformer(self, url, format_ids):
  if self.youtube_dl is None:
   import youtube_dl
   self.youtube_dl = youtube_dl.YoutubeDL(params=dict(outtmpl = u"%(title)s [%(extractor)s '%(id)s].%(ext)s", quiet=True, ))
   self.youtube_dl.add_default_info_extractors()
   logger.debug("Initialized Youtube support")
  info = self.youtube_dl.extract_info(url, download=False, process=False)
  for format in [i for i in info['formats'] if i['format_id'] in format_ids]:
   if format['url']:
    return format['url']
  raise ValueError("Unable to find URL for format IDs %r" % format_ids)

 def transform_youtube(self, url):
    return self.youtube_dl_transformer(url, format_ids=('18', ))

 def transform_vine(self, url):
  return self.youtube_dl_transformer(url, format_ids=('h264-450', 'h264-200'))

 def transform_twitter(self, url):
  info = self.youtube_dl.extract_info(url, download=False, process=False)
  return info['formats'][-1]['url']



 AUDIOBOO_FM_RE = re.compile(r'https?://(?:www.)?audioboo.fm/boos/(\d+).*')
 AUDIOBOO_SHORT_RE = re.compile(r'https?://(?:www.)?boo.fm/b(\d+).*')
 AUDIOBOOM_RE = re.compile(r'https?://(?:www.)?audioboom.com/boos/(\d+).*')
 NEW_AUDIOBOOM_RE = re.compile(r'https?://(?:www.)?audioboom.com/posts/(\d+).*')
 matches = {
  re.compile(r'(^https?://(www\.)?(m\.)?soundcloud.com/.*/.*$)'): transform_soundcloud,
  re.compile(r'(https?://(?:www\.)?sndup.net/(.+)/a)'): transform_sndup,
  re.compile(r'(https?://(?:www\.)?twup.me/.+)'): transform_twup,
  re.compile(r'(https?://(?:www\.)?(m\.)?youtube.com/watch.+)'): transform_youtube,
  re.compile(r'(https?://(?:www\.)?(m\.)?youtu.be/.+)'): transform_youtube,
  re.compile(r'https?://vine.co/.+'): transform_vine,
  re.compile(r'https?://amp.twimg.com/v/.+'): transform_twitter,
  #audioboo
  AUDIOBOO_FM_RE: lambda self, url: self.transform_audioboom(url, self.AUDIOBOO_FM_RE),
  AUDIOBOO_SHORT_RE: lambda self, url: self.transform_audioboom(url, self.AUDIOBOO_SHORT_RE),
  AUDIOBOOM_RE: lambda self, url: self.transform_audioboom(url, self.AUDIOBOOM_RE),
  NEW_AUDIOBOOM_RE: lambda self, url: self.transform_audioboom(url, self.NEW_AUDIOBOOM_RE),
   }
