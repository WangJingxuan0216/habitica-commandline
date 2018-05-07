from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()


setup(
    name='habitica',
    version='0.0.1',
    author='Jingxuan Wang',
    author_email='wang.jingxuan0216@gmail.com',
    packages=find_packages(exclude=('dist','tests')),
    install_requires=[
        'docopt',
        'requests',
    ],
    scripts=['bin/habitica']
      )
