#!/usr/bin/env python

import sys, os
sys.path.insert(0, os.path.join(os.getcwd(),'lib'))

try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

import wsgiutils

try:
	os.remove ('MANIFEST')
except:
	pass

setup(name="WSGIUtils",
	version= wsgiutils.__version__,
	description="WSGI Utils are a collection of useful libraries for use in a WSGI environnment.",
	author="Colin Stewart",
	author_email="colin@owlfish.com",
	url="http://www.owlfish.com/software/wsgiutils/index.html",
	packages=[
		'wsgiutils',
	],
	package_dir = {'': 'lib'},
)
