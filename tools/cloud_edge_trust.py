"""Use the managed cloud CA with edge-tts while preserving TLS verification."""
import importlib
import os
import ssl


def configure():
    certificate_file = os.environ.get('SSL_CERT_FILE')
    if not certificate_file:
        raise RuntimeError('Managed SSL_CERT_FILE is missing; do not disable certificate verification.')
    for name in ('edge_tts.voices', 'edge_tts.communicate'):
        context = importlib.import_module(name)._SSL_CTX
        context.load_verify_locations(cafile=certificate_file)
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            raise RuntimeError('TLS certificate and hostname checks must remain enabled.')
