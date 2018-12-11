#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'six',
    'jsonschema',
    'Click',
    'enum34 ; python_version<"3.4"',
]

setup_requirements = [
    'pytest-runner',
]

test_requirements = [
    'pytest',
]

setup(
    name='ubimaior',
    version='0.1.0',
    description="Manage hierarchy of objects as if they were one.",
    long_description=readme + '\n\n' + history,
    author="Massimiliano Culpo",
    author_email='massimiliano.culpo@gmail.com',
    url='https://github.com/alalazo/ubimaior',
    packages=find_packages(include=['ubimaior']),
    include_package_data=True,
    install_requires=requirements,
    license="GNU General Public License v3",
    zip_safe=False,
    keywords='ubimaior',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    extras_require={
        'YAML': 'PyYAML',
        'TOML': 'toml'
    },
    entry_points="""
        [console_scripts]
        ubimaior=ubimaior.commands:main
    """,
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
