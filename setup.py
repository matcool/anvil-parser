import setuptools

with open('README.md', 'r') as file:
    long_description = file.read()

setuptools.setup(
    name='anvil-parser2',
    version='0.10.6',
    author='0xTiger',
    description='A parser for the Minecraft anvil file format, supports all Minecraft verions',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/0xTiger/anvil-parser2',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'nbt',
        'frozendict',
    ],
    include_package_data=True
)
