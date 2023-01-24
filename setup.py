from setuptools import setup, find_packages

__version__ = "1.2"
__doc__ = """Determine if certain audio links need to be transformed before they can be played, and do so"""

setup(
 name = 'audio_url_transformer',
 version = __version__,
 description = __doc__,
 packages = find_packages(),
 install_requires = [
  'requests',
  'yt_dlp',
 ],
 classifiers = [
  'Development Status :: 4 - Beta',
  'Intended Audience :: Developers',
  'Programming Language :: Python',
  'Topic :: Software Development :: Libraries',
 ],
)
