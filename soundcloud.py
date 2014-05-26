import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

class SoundCloudAPI(object):
 def __init__(self, client_id):
  self.client_id = client_id

 def get_stream_url(self, url):
  resolve_endpoint = 'https://api.soundcloud.com/resolve.json'
  params = {
   'client_id': self.client_id,
   'url': url
  }
  track_data = requests.get(resolve_endpoint, params=params).json()
  if track_data['streamable']:
   url = '%s?client_id=%s' % (track_data['stream_url'], self.client_id)

  return url
