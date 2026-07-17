"""Construye Any2Mp3.app con: python setup.py py2app."""

import sys

from setuptools import setup

sys.setrecursionlimit(10_000)

setup(
    name="Any2Mp3",
    version="1.0.0",
    app=[{"script": "desktop.py", "dest_base": "Any2Mp3"}],
    options={
        "py2app": {
            "iconfile": "Any2Mp3.icns",
            "resources": ["templates", "static"],
            "plist": {
                "CFBundleIdentifier": "com.carlosh.any2mp3",
                "CFBundleDisplayName": "Any2Mp3",
                "LSMinimumSystemVersion": "12.0",
                "NSHighResolutionCapable": True,
            },
        }
    },
    setup_requires=["py2app"],
)
