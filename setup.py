"""Setup configuration for KIVA-CLI.

Installation:
    pip install -e .  # Editable mode (development)
    pip install .     # Standard installation

Entry points:
    kiva - Main CLI executable
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
README = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(
    name="kiva-cli",
    version="0.1.0-alpha",
    description="KIVA CLI - Project & Application Orchestration",
    long_description=README,
    long_description_content_type="text/markdown",
    author="ECOS Ecosystem",
    author_email="gerivonderbitsh+dev@gmail.com",
    url="https://github.com/gerivdb/KIVA-CLI",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=[
        # No external dependencies (stdlib only for phase 1A)
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=24.0.0",
            "ruff>=0.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "kiva=kiva_cli.kiva:main",
        ],
    },
    scripts=["bin/kiva"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Systems Administration",
    ],
    keywords="cli orchestration devops deployment project-management ecos",
)
