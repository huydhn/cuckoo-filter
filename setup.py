'''
Standard Python setup script.
'''

from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='scalable-cuckoo-filter',
    version='1.1',
    description='Scalable Cuckoo filter',
    url='https://github.com/huydhn/cuckoo-filter',
    author='Huy Do',
    author_email='huydhn@gmail.com',
    license='MIT',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=['mmh3', 'bitarray'],
    tests_require=['unittest2', 'coverage', 'nose>=1.3.7', 'netaddr', 'pytest-pep8'],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
