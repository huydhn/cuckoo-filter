'''
Standard Python setup script.
'''

from setuptools import setup, find_packages

setup(
    name='cuckoo-filter',
    version='1.0',
    description='Scalable Cuckoo filter',
    url='https://github.com/huydhn/cuckoo-filter',
    author='Huy Do',
    author_email='',
    license='MIT',
    install_requires=['mmh3', 'bitarray'],
    tests_require=['unittest2', 'coverage', 'nose>=1.3.7', 'netaddr'],
    packages=find_packages(),
)
