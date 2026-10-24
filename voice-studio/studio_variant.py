"""Product selection shared by the standard and Hmong launchers."""
import os

IS_HMONG = os.environ.get('VOICE_STUDIO_VARIANT', '').lower() == 'hmong'
APP_NAME = 'Voice Studio Hmong' if IS_HMONG else 'Voice Studio'
APP_VERSION = '1.5.1-hmong' if IS_HMONG else '3.6.2'
DEFAULT_LANGUAGE = 'mww' if IS_HMONG else 'vi'
DEFAULT_DATA_FOLDER = '.data-hmong' if IS_HMONG else '.data'
