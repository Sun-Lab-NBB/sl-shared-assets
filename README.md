# sl-shared-assets
A Python library that provides data acquisition and processing assets shared between Sun (NeuroAI) lab libraries.

![PyPI - Version](https://img.shields.io/pypi/v/sl-shared-assets)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sl-shared-assets)
[![uv](https://tinyurl.com/uvbadge)](https://github.com/astral-sh/uv)
[![Ruff](https://tinyurl.com/ruffbadge)](https://github.com/astral-sh/ruff)
![type-checked: mypy](https://img.shields.io/badge/type--checked-mypy-blue?style=flat-square&logo=python)
![PyPI - License](https://img.shields.io/pypi/l/sl-shared-assets)
![PyPI - Status](https://img.shields.io/pypi/status/sl-shared-assets)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/sl-shared-assets)

___

## Detailed Description

This library makes the two main Sun lab libraries used for data acquisition 
([sl-experiment](https://github.com/Sun-Lab-NBB/sl-experiment)) and processing 
([sl-forgery](https://github.com/Sun-Lab-NBB/sl-forgery)) independent of each other.

The library broadly stores two types of assets. First, it stores dataclasses used to save the data acquired in the lab 
and configure data acquisition and processing runtimes. Second, it provides the low-level tools and methods used to 
manage the data at all stages of Sun lab data workflow: acquisition, processing, and analysis.

---

## Table of Contents

- [Dependencies](#dependencies)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Versioning](#versioning)
- [Authors](#authors)
- [License](#license)
- [Acknowledgements](#Acknowledgments)

___

## Dependencies

All library dependencies are installed automatically by all supported installation methods 
(see the [Installation](#installation) section).

---

## Installation

### Source

Note, installation from source is ***highly discouraged*** for anyone who is not an active project developer.

1. Download this repository to the local machine using the preferred method, such as git-cloning. Use one of the 
   [stable releases](https://github.com/Sun-Lab-NBB/sl-shared-assets/releases) that include precompiled binary and 
   source code distribution (sdist) wheels.
2. If the downloaded distribution is stored as a compressed archive, unpack it using the appropriate decompression tool.
3. ```cd``` to the root directory of the prepared project distribution.
4. Run ```python -m pip install .``` to install the project. Alternatively, if using a distribution with precompiled
   binaries, use ```python -m pip install WHEEL_PATH```, replacing 'WHEEL_PATH' with the path to the wheel file.

### pip

Use the following command to install the library using pip: ```pip install sl-shared-assets```.

---

## Usage

Most library components are intended to be used via other Sun lab libraries. For details on using shared 
assets for data acquisition and preprocessing, see the [sl-experiment](https://github.com/Sun-Lab-NBB/sl-experiment) 
library. For details on using shared assets for data processing and dataset formation, see the 
[sl-forgery](https://github.com/Sun-Lab-NBB/sl-forgery) library.

***Warning!*** End users should not use any component of this library directly or install this library into any Python 
environment. All assets from this library are intended to be used exclusively by developers working on other Sun lab 
libraries.

## API Documentation

Developers working on integrating sl-shared-assets into other libraries should see the 
[API documentation](https://sl-shared-assets-api-docs.netlify.app/) for the detailed description of the methods and 
classes exposed by components of this library.

**Note!** The API documentation includes important information about configuration Command-Line Interface (CLI) exposed
by this library as part of installation into a Python environment.

___

## Versioning

This project uses [semantic versioning](https://semver.org/). See the 
[tags on this repository](https://github.com/Sun-Lab-NBB/sl-shared-assets/tags) for the available project 
releases.

---

## Authors

- Ivan Kondratyev ([Inkaros](https://github.com/Inkaros))
- Kushaan Gupta ([kushaangupta](https://github.com/kushaangupta))
- Natalie Yeung

___

## License

This project is licensed under the GPL3 License: see the [LICENSE](LICENSE) file for details.

___

## Acknowledgments

- All Sun lab [members](https://neuroai.github.io/sunlab/people) for providing the inspiration and comments during the
  development of this library.
- The creators of all other dependencies and projects listed in the [pyproject.toml](pyproject.toml) file.

---