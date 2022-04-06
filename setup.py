import setuptools
import re

with open("README.md", "r") as fh:
    long_description = fh.read()

version = ''
with open('snowfin/__init__.py') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('version is not set')

requirements = []
with open('requirements.txt') as f:
  requirements = f.read().splitlines()

setuptools.setup(
     name='snowfin',
     version=version,
     author='kajdev',
     description="An async discord http interactions framework built on top of Sanic.",
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="https://github.com/kajdev/snowfin",
     packages=["snowfin"],
     python_requires=">=3.10",
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: MIT License",
         "Operating System :: OS Independent",
     ],
     install_requires=requirements
 )