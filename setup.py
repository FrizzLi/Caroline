from setuptools import find_packages, setup

with open("reqs.txt") as f:
    reqs = f.read().splitlines()

setup(name="setup", install_requires=reqs)
