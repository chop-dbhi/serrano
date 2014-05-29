import sys
from setuptools import setup, find_packages

install_requires = [
    'avocado>=2.3.4,<2.4',
    'restlib2>=0.4.1,<0.5.0',
    'django-preserialize>=1.0.7,<1.1',
]

if sys.version_info < (2, 7):
    install_requires.append('ordereddict>=1.1')

kwargs = {
    # Packages
    'packages': find_packages(exclude=['tests', '*.tests', '*.tests.*',
                                       'tests.*']),
    'include_package_data': True,

    # Dependencies
    'install_requires': install_requires,

    # Test dependencies
    'tests_require': [
        'avocado[permissions,search,extras]>=2.3.1,<2.4'
        'coverage',
        'whoosh',
        'python-memcached>=1.48',
        'django-objectset>=0.2.3',
    ],

    'test_suite': 'test_suite',

    # Optional dependencies
    'extras_require': {},

    # Metadata
    'name': 'serrano',
    'version': __import__('serrano').get_version(),
    'author': 'Byron Ruth',
    'author_email': 'b@devel.io',
    'description': 'Hypermedia implementation for Avocado',
    'license': 'BSD',
    'keywords': 'hypermedia rest api avocado serrano cilantro harvest',
    'url': 'http://github.com/cbmi/serrano',
    'classifiers': [
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Framework :: Django',
        'Topic :: Internet :: WWW/HTTP',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Information Technology',
    ],
}

setup(**kwargs)
