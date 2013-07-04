import sys
try:
    import entree
except ImportError:
    sys.path.insert(0, abspath(dirname(__file__)))
    import entree

from os.path import join, abspath, dirname
from setuptools import find_packages
from distutils.core import setup


CWD = abspath(dirname(__file__))


def install_requires():
    with open(join(CWD, 'requirements.txt'), 'r') as f:
        reqs = [one for one in f.read().split("\n") if '#' not in one and one]

    base = ['setuptools>=0.6b1']
    print base + reqs
    return base + reqs


setup(
    name='Entree',
    version=entree.__versionstr__,
    description='Entree - Django powered SSO',
    long_description=open('README.md').read(),
    author='yed_',
    author_email='yed@vanyli.net',
    maintainer='yed_',
    maintainer_email='yed@vanyli.net',
    license='BSD',
    url='http://github.com/yedpodtrzitko/django-entree/',

    packages=find_packages(
        where='.',
        exclude=('docs', 'tests',)
    ),

    include_package_data=True,

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Programming Language :: Python :: 2.7",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=install_requires(),
    tests_require=['nose', 'coverage', 'mock'],
    test_suite='tests.run_tests.run_all'
)

