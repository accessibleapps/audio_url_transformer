from setuptools import setup

__version__ = 0.1
__doc__ = """Determine if certain audio links need to be transformed before they can be played, and do so"""

setup(
 name = 'audio_url_transformer',
 version = __version__,
 description = __doc__,
 py_modules = ['audio_url_transformer'],
 install_requires = [
  'requests',
 ],
 classifiers = [
  'Development Status :: 3 - Alpha',
  'Intended Audience :: Developers',
  'Programming Language :: Python',
  'Topic :: Software Development :: Libraries',
 ],
)
