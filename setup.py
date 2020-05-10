import setuptools


def requirements(file_name):
    return open(file_name, 'rt').read().splitlines()


setuptools.setup(name='tortoise_rest_utils',
                 version='1.1.2',
                 author='t1waz',
                 author_email='milewiczmichal87@gmail.com',
                 description='REST tools for building backends '
                             'with TorToiseORM and Starlette framework',
                 url='https://www.github.com/t1waz/rest_utils',
                 license='MIT',
                 packages=setuptools.find_packages(),
                 classifiers=[
                       "Programming Language :: Python :: 3",
                       "License :: OSI Approved :: MIT License",
                       "Operating System :: OS Independent",
                 ],
                 python_requires='>=3.6',
                 zip_safe=False,
                 install_requires=requirements('requirements.txt'))
