from audio_url_transformer import AudioURLTransformer

soundcloud_client_id = '6fa58c015833fc68768f361ca8dbbe93'
aut = AudioURLTransformer(soundcloud_client_id=soundcloud_client_id)

test_urls = [
 'http://soundcloud.com/virginmagneticmaterial/bon-iver-michicant-virgin',
 'http://sndup.net/43sc/a',
 'http://twup.me/uE',
 'https://audioboo.fm/boos/2198170-vipadvisor-gas-vs-electric-cooker',
 'https://boo.fm/b2198170',
 'https://audioboom.com/boos/2502158-first-impressions-of-audioboom',
 'https://www.youtube.com/watch?v=v8qoB1XwtHM',
 'http://youtu.be/6GZDBO_TOHg',
]

for url in test_urls:
 print aut.transform(url)
