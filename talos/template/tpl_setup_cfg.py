# coding=utf-8

TEMPLATE = u'''[bdist_wheel]
# This flag says that the code is written to work on both Python 2 and Python
# 3. If at all possible, it is good practice to do this. If you cannot, you
# will need to generate wheels for each Python version that you support.
universal=1

[bdist_rpm]
packager = ${author} <${author_email}>
provides = ${author}

[aliases]
test=pytest

[tool:pytest]
addopts = tests -v --html=unit_test_report.html --cov=${pkg_name} --cov-report=term --cov-report=html
'''