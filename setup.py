from setuptools import setup, find_packages
from usleep_api import __version__

with open('README.md') as readme_file:
    readme = readme_file.read()

with open("requirements.txt") as req_file:
    requirements = list(filter(None, req_file.read().split("\n")))

setup(
    name='usleep_api',
    version=__version__,
    description='Python bindings to the U-Sleep web API.',
    long_description=readme,
    author='Mathias Perslev',
    author_email='map@di.ku.dk',
    url='https://github.com/perslev/U-Sleep-API-Python-Bindings',
    packages=find_packages(),
    package_dir={'usleep_api':
                 'usleep_api'},
    include_package_data=True,
    install_requires=requirements,
    classifiers=['Environment :: Console',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7',
                 'Programming Language :: Python :: 3.8',
                 'Programming Language :: Python :: 3.9']
)
