from setuptools import setup

setup(
    name="csv-diff-python2-blue-monk",
    install_requires=[
    ],
    extras_require={
    },
    entry_points={
        'console_scripts': [
            'csvdiff2=csvdiff2.csvdiff:main',
        ],
    },
)
