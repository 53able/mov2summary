from setuptools import setup, find_packages

setup(
    name="mov2summary",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'ffmpeg-python==0.2.0',
        'openai==0.27.7',
        'pytube==15.0.0',
    ],
)
