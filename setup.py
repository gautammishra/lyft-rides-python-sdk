#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from setuptools import find_packages
from setuptools import setup

with open('README.rst') as f:
    readme = f.read()

setup(
    name='lyft_rides',
    version='0.2',
    packages=find_packages(),
    description='Unofficial Lyft Rides API Python SDK',
    long_description=readme,
    url='https://github.com/gautammishra/lyft-rides-python-sdk',
    license='MIT',
    author='Gautam Mishra',
    author_email='gautam.mishra@hotmail.com',
    install_requires=['requests', 'pyyaml'],
    extras_require={
        ':python_version == "2.7"': ['future'],
    },
    keywords=['lyft', 'api', 'sdk', 'rides', 'library'],
)