from __future__ import absolute_import

import re
from . import soundcloud
import youtube_dl

class AudioURLTransformer(object):
 audio_extensions = ('.mp3', '.wav', '.ogg', '.flac', '.wma', '.m4a', '.aac')

 def __init__(self, soundcloud_client_id=None):
  if soundcloud_client_id:
   self.soundcloud_api = soundcloud.SoundCloudAPI(soundcloud_client_id)
  self.youtube_dl = youtube_dl.YoutubeDL(params=dict(outtmpl = u"%(title)s [%(extractor)s '%(id)s].%(ext)s", quiet=True, ))
  self.youtube_dl.add_default_info_extractors()

 def transform(self, url):
  if url.lower().endswith(self.audio_extensions):
   return url
  for (regexp, processor) in self.matches.iteritems():
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
  return r.sub(r'http://audioboom.com/boos/\1.mp3', url)

 def transform_youtube(self, url):
  info = self.youtube_dl.extract_info(url, download=False, process=False)
  for format in info['formats'][-1::-1]:
   if format['url']:
    return format['url']



 AUDIOBOO_FM_RE = re.compile(r'https?://(?:www.)?audioboo.fm/boos/(\d+).*')
 AUDIOBOO_SHORT_RE = re.compile(r'https?://(?:www.)?boo.fm/b(\d+).*')
 AUDIOBOOM_RE = re.compile(r'https?://(?:www.)?audioboom.com/boos/(\d+).*')
 matches = {
  re.compile(r'(^https?://(www\.)?(m\.)?soundcloud.com/.*/.*$)'): transform_soundcloud,
  re.compile(r'(https?://(?:www\.)?sndup.net/(.+)/a)'): transform_sndup,
  re.compile(r'(https?://(?:www\.)?twup.me/.+)'): transform_twup,
  re.compile(r'(https?://(?:www\.)?(m\.)?youtube.com/watch.+)'): transform_youtube,
  re.compile(r'(https?://(?:www\.)?(m\.)?youtu.be/.+)'): transform_youtube,
  #audioboo
  AUDIOBOO_FM_RE: lambda self, url: self.transform_audioboom(url, self.AUDIOBOO_FM_RE),
  AUDIOBOO_SHORT_RE: lambda self, url: self.transform_audioboom(url, self.AUDIOBOO_SHORT_RE),
  AUDIOBOOM_RE: lambda self, url: self.transform_audioboom(url, self.AUDIOBOOM_RE),
   }
