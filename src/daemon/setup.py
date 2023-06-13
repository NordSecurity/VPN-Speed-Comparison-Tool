from setuptools import setup, find_packages
from os import path
from io import open

here = path.abspath(path.dirname(__file__))

setup(
    name="vpnspeed-daemon",  # Required
    version="0.1",  # Required
    # https://pypi.org/classifiers/
    classifiers=[  # Optional
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    packages=find_packages(),  # Required
    python_requires=">=3.7, <4",
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        "yarl==1.4.2",
        "pillow==9.5.0",
        "asyncio",
        "aiodocker",
        "aiorwlock",
        "aiohttp",
        "aiofiles",
        "dataclasses",
        "jsonpickle",
        "jsonpath-ng",
        "pexpect",
        "PyYAML==6.0",
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
    ],  # Optional
    # List additional groups of dependencies here (e.g. development
    # dependencies). Users will be able to install these using the "extras"
    # syntax, for example:
    #
    #   $ pip install sampleproject[dev]
    #
    # Similar to `install_requires` above, these must be valid existing
    # projects.
    # extras_require={  # Optional
    #     'dev': ['check-manifest'],
    #     'test': ['coverage'],
    # },
    package_data={  # Optional
        "vpnspeed": [
            "resources/*",
            "resources/*/*",
            "resources/*/*/*",
            "resources/*/*/*/*",
        ]
    },
    entry_points={  # Optional
        "console_scripts": [
            "vpnspeedd=vpnspeed:run",
        ],
    },
)
