#!/usr/bin/env python
import setuptools

requirements = [
    'numpy',
    'PyYAML',
    'netCDF4',
    'pysftp'
]

setuptools.setup(
    name="atmoswing_vigicrues",
    version="0.9.0",
    author="Pascal Horton",
    author_email="pascal.horton@terranum.ch",
    package_dir={"atmoswing_vigicrues": "atmoswing_vigicrues"},
    packages=setuptools.find_packages(where="atmoswing_vigicrues"),
    entry_points={
        "console_scripts": ["atmoswing_vigicrues=atmoswing_vigicrues.__main__:main"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Pytest"
    ],
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest',
            'pytest-pep8',
            'pytest-cov',
            'pre-commit'
        ]
    }
)
