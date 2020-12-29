from setuptools import setup, find_packages

setup(
    name="filemon", 
    version='0.1.0',
    license='MIT',
    description='e-book management',

    author='Mihas Davidovich',
    author_email='mihal.d44@gmail.com',

    packages=find_packages(where='src'),
    package_dir={'': 'src'}

    )
