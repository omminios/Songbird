"""
Setup script for Songbird CLI
"""
from setuptools import setup, find_packages
import os

# Read long description from README if it exists
long_description = "Sync playlists between Spotify and YouTube Music"
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()

setup(
    name="songbird",
    version="0.1.0",
    author="Songbird Project",
    description="Sync playlists between Spotify and YouTube Music",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.28.0",
        "python-dotenv>=0.19.0",
        "spotipy>=2.22.0",
        "pydantic>=1.10.0",
        "pyyaml>=6.0",
        "structlog>=22.1.0",
        "PyJWT>=2.6.0",
        "boto3>=1.26.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
    },
    entry_points={
        "console_scripts": [
            "songbird=songbird.cli:cli",
        ],
    },
)