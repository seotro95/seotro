"""Release-owned identities for the four reviewed F5-Hmong/Vocos artifacts.

These values are shipped with the application, not learned from remote main
or a writable manifest beside downloaded weights. The downloader and runtime
verifier share this trust anchor. A local verified-models.json is only a receipt.
"""
from types import MappingProxyType

MODEL_RELEASE = 'hmong-nhanh-0.8.1'
SOURCES = (
    ('Pakorn2112/F5TTS-Hmong', 'c50fc0cc991bc0c4f22d86c7a6152730c667c0d5'),
    ('charactr/vocos-mel-24khz', '0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21'),
)
PINNED_MODELS = MappingProxyType({
    'f5-hmong/model_159952.safetensors': MappingProxyType({
        'sha256': '0b5e23fd6c9c1519f38195cbe0fdca3402beb75026b22ace483886529add3288',
        'size': 1348435761,
        'url': 'https://huggingface.co/Pakorn2112/F5TTS-Hmong/resolve/c50fc0cc991bc0c4f22d86c7a6152730c667c0d5/model_159952.safetensors',
    }),
    'f5-hmong/vocab.txt': MappingProxyType({
        'sha256': '2a05f992e00af9b0bd3800a8d23e78d520dbd705284ed2eedb5f4bd29398fa3c',
        'size': 13800,
        'url': 'https://huggingface.co/Pakorn2112/F5TTS-Hmong/resolve/c50fc0cc991bc0c4f22d86c7a6152730c667c0d5/vocab.txt',
    }),
    'vocos/config.yaml': MappingProxyType({
        'sha256': 'da9033922f969a47f0c160010226919e59f27761fd5066f3828d46de6650b0fc',
        'size': 461,
        'url': 'https://huggingface.co/charactr/vocos-mel-24khz/resolve/0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21/config.yaml',
    }),
    'vocos/pytorch_model.bin': MappingProxyType({
        'sha256': '97ec976ad1fd67a33ab2682d29c0ac7df85234fae875aefcc5fb215681a91b2a',
        'size': 54365991,
        'url': 'https://huggingface.co/charactr/vocos-mel-24khz/resolve/0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21/pytorch_model.bin',
    }),
})
