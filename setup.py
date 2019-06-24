import re
from setuptools import setup, find_packages

# Load version from module (without loading the whole module)
with open('src/ezgmail/__init__.py', 'r') as fo:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fo.read(), re.MULTILINE).group(1)

# Read in the README.md for the long description.
with open('README.md') as fo:
    long_description = fo.read()

setup(
    name='EZGmail',
    version=version,
    url='https://github.com/asweigart/ezgmail',
    author='Al Sweigart',
    author_email='al@inventwithpython.com',
    description=('''A Pythonic interface to the Gmail API that actually works as of June 2019.'''),
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='GPLv3+',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    test_suite='tests',
    install_requires=['google-api-python-client', 'oauth2client'],
    keywords='',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
)
