from setuptools import setup, find_packages
from os import path
from io import open

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="vpnspeed",
    version="1.0.0",
    description="Speed comparision tool between multiple VPN Providers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    package_dir={
        "": "src/cli",
        "vpnspeed": "src/daemon/vpnspeed",
    },
    py_modules=["vpnspeed_cli"],
    packages=find_packages("src/daemon/"),
    python_requires=">=3.7, <4",
    install_requires=[
        "yarl==1.4.2",
        "pillow==8.3.2",
        "asyncio",
        "aiodocker",
        "aiorwlock",
        "aiohttp",
        "aiofiles",
        "dataclasses",
        "jsonpickle",
        "jsonpath-ng",
        "pexpect",
        "PyYAML",
        "pythonping",
        "jinja2",
        "pygeohash",
        "pycountry",
        "aiosqlite",
        "python-crontab",
        "pandas",
        "matplotlib",
        "dnspython3",
        "pycryptodome",
    ],
    # extras_require={
    #     'dev': ['check-manifest'],
    #     'test': ['coverage'],
    # },
    package_data={
        "vpnspeed": [
            "resources/*",
            "resources/*/*",
            "resources/*/*/*",
            "resources/*/*/*/*",
        ]
    },
    entry_points={
        "console_scripts": [
            "vpnspeed=vpnspeed_cli:run",
            "vpnspeedd=vpnspeed.daemon:run",
        ],
    },
)
