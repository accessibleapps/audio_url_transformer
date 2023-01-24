from .audio_url_transformer import AudioURLTransformer
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: %s <url>" % sys.argv[0])
        sys.exit(1)
    import logging
    logging.basicConfig(level=logging.INFO)
    transformer = AudioURLTransformer()
    print(transformer.transform(sys.argv[1]))
