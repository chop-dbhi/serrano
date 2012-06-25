import distribute_setup
distribute_setup.use_setuptools()
from setuptools import setup, find_packages

kwargs = {
    # Packages
    'packages': find_packages(),
    'include_package_data': True,

    # Dependencies
    'install_requires': [
        'avocado>=2.0a', # Hack, to work with the dependency link
        'restlib2>=1.0a', # Hack, to work with the dependency link
    ],

    # Test dependencies
    'tests_require': [
        'coverage',
    ],

    # Optional dependencies
    'extras_require': {},

    # Resources unavailable on PyPi
    'dependency_links': [
        'https://github.com/cbmi/avocado/tarball/2.x#egg=avocado-2.0',
        'https://github.com/bruth/restlib2/tarball/master#egg=restlib2-1.0',
    ],

    # Metadata
    'name': 'serrano',
    'version': __import__('serrano').get_version(),
    'author': 'Byron Ruth',
    'author_email': 'b@devel.io',
    'description': 'Hypermedia implementation for Avocado',
    'license': 'BSD',
    'keywords': 'hypermedia rest api avocado serrano cilantro harvest',
    'url': 'https://github.com/cbmi/serrano',
    'classifiers': [
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7'
        'Framework :: Django',
        'Topic :: Internet :: WWW/HTTP',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Information Technology',
    ],
}

setup(**kwargs)
