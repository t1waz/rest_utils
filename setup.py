import subprocess
import sys

from setuptools import setup, find_packages
from setuptools.command.install import install


VERSION = '0.1.1'


class VerifyVersionCommand(install):
    def run(self):
        tag = subprocess.check_output(['git', 'tag', '--points-at', 'HEAD']).decode().strip()
        if tag != VERSION:
            sys.exit(f'Git tag: {tag} does not match the version of this app: {VERSION}')


def requirements(file_name):
    return open(file_name, 'rt').read().splitlines()


setup(name='async_easy_utils',
      version=VERSION,
      author='t1waz',
      author_email='milewiczmichal87@gmail.com',
      description='REST tools for building backends '
                  'with TorToiseORM and Starlette framework',
      url='https://www.github.com/t1waz/rest_utils',
      license='MIT',
      packages=find_packages(),
      classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
      ],
      python_requires='>=3.6',
      zip_safe=False,
      install_requires=requirements('requirements.txt'),
      cmdclass={
          'verify': VerifyVersionCommand,
      })
