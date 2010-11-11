# Copyright (C) 2010 Luke Tucker
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301
# USA

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='radarpost',
    version="0.1",
    description="A news gathering engine",
    license="GPLv2 or any later version",
    author="Luke Tucker",
    author_email="voxluci@gmail.com",
    url="http://github.com/ltucker/radarpost",
    install_requires=[
        'couchdb', 
        'httplib2',
        'WebOb',
        'Jinja2',
        'WebTest',
        'Beaker',
	'Routes',
	'CherryPy',
	'pytz'
    ],
    dependency_links=[
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='nose.collector',
    entry_points="""
    [console_scripts]
    radarpost = radarpost.main:main
    
    [radarpost_plugins]
    feed = radarpost.feed
    commands = radarpost.cli
    server = radarpost.web.app
    agents = radarpost.agent
    """,
)
