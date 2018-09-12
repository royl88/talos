# coding=utf-8

TEMPLATE = '''# Tox (https://tox.readthedocs.io/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py27, py35

[testenv]
commands = python setup.py test
deps =
    coverage
    pytest
    pytest-runner
    pytest-html
'''