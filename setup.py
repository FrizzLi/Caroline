from setuptools import setup

with open("reqs.txt", encoding="utf-8") as f:
    reqs = f.read().splitlines()

setup(name="setup", install_requires=reqs)

# TODO: Tests -> check this whether it is necessary for tests, or anything else
