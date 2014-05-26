import re
import soundcloud

class AudioURLTransformer(object):
 def __init__(self, soundcloud_client_id=None):
  if soundcloud_client_id:
   self.soundcloud_api = soundcloud.SoundCloudAPI(soundcloud_client_id)

 def transform(self, url):
  for (regexp, processor) in self.matches.iteritems():
   if not regexp.search(url):
    continue
   return processor(self, url)

 def transform_soundcloud(self, url):
  return self.soundcloud_api.get_stream_url(url)

 def transform_sndup(self, url):
  return re.sub(r'(http://(?:www\.)?sndup.net/(.+)/a)', r'http://sndup.net/\2/a', url)

 def transform_twup(self, url):
  return re.sub(r'(http://(?:www\.)?twup.me/.+)', r'\1', url)

 def transform_audioboo(self, url):
  return re.sub(r'(https?://(?:www\.)?(audio)?boo.fm/b(oos/)?(\d+)(.*)?)', r'http://audioboo.fm/boos/\4.mp3', url)

 matches = {
  re.compile(r'(^https?://(www\.)?(m\.)?soundcloud.com/.*/.*$)'): transform_soundcloud,
  re.compile(r'(http://(?:www\.)?sndup.net/(.+)/a)'): transform_sndup,
  re.compile(r'(http://(?:www\.)?twup.me/.+)'): transform_twup,
  re.compile(r'(https?://(?:www\.)?(audio)?boo.fm/b(oos/)?(\d+)(.*)?)'): transform_audioboo,
 }