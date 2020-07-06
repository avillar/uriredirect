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
    description = 'URI Redirection supporting Content-negotiation and Content-negotiation-by-application-profile for Django',
    packages = ['uriredirect',
                'uriredirect.admin',
                'uriredirect.http',
                'uriredirect.models',
                'uriredirect.tests',
                'uriredirect.views',
                ],
    include_package_data = True,
    author = ['Rob Atkinson','Ryan Clark',],
    zip_safe = False,
    install_requires = ['python-mimeparse', 
                        'rdflib>=4.0',
                        'rdflib-jsonld',
                        'requests' ],
    long_description = open('readme.md').read(),
    url = 'https://github.com/rob-metalinkage/uriredirect',
    download_url = 'https://github.com/usgin/uriredirect/tarball/master',
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Linked Data Publishing Systems',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
        'Natural Language :: English',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],

)

