#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup, find_packages

VERSION = __import__('uriredirect').__version__

import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = 'uriredirect',
    version = VERSION,
    description = 'URI Redirecttion for Django',
    packages = ['uriredirect.admin',
                'uriredirect.http',
                'uriredirect.models',
                'uriredirect.tests',
                'uriredirect.views',
                ],
    include_package_data = True,
    author = 'Ryan Clark',
    zip_safe = False,
    install_requires = ['mimeparse', ],
    long_description = open('readme.md').read(),
    url = 'https://github.com/usgin/uriredirect',
    download_url = 'https://github.com/usgin/uriredirect/tarball/master',
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
        'Natural Language :: English',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],

)

