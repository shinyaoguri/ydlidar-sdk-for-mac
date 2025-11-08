"""
YDLiDAR T-mini Pro Mac用ドライバー セットアップ
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ydlidar-tmini",
    version="1.0.0",
    author="Your Name",
    description="YDLiDAR T-mini Pro driver for macOS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Hardware :: Hardware Drivers",
    ],
    python_requires=">=3.7",
    install_requires=[
        "pyserial>=3.5",
    ],
    extras_require={
        "visualization": [
            "numpy>=1.20.0",
            "matplotlib>=3.3.0",
        ],
    },
)
