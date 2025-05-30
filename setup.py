from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

setup_requirements = []

test_requirements = [
    "black>=22.3.0",
    "flake8>=4.0.0",
    "codecov>=2.1.4",
    "pytest>=6.2.5",
    "pytest-cov>=3.0.0",
    "pytest-html>=3.1.1",
]

dev_requirements = [
    *setup_requirements,
    *test_requirements,
    "tox>=3.24.5",
    "Sphinx==7.0.1",
    "sphinx-rtd-theme==2.0.0",
]

requirements = [
    "pint>=0.19.2",
    "networkx>=2.8.5",
    "pyvis>=0.3.0",
    "matplotlib>=3.5.2",
    "pandas>=1.4.0",
    "numpy>=1.22.1",
    "scipy>=1.8.0",
    "epyt>=1.0.0"
]

extra_requirements = {
    "setup": setup_requirements,
    "test": test_requirements,
    "dev": dev_requirements,
    "all": [
        *requirements,
        *dev_requirements,
    ],
}

setup(
    author="WE3 Lab",
    author_email="fchapin@stanford.edu",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: Free for non-commercial use",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    description="Class hierarchy to represent configurations of process engineering systems.",
    entry_points={},
    long_description=readme,
    long_description_content_type="text/x-rst",
    package_data={"pype_schema": ["pype_schema/data/*"]},
    include_package_data=True,
    keywords="pype-schema",
    name="pype-schema",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    python_requires=">=3.10",
    install_requires=requirements,
    setup_requires=setup_requirements,
    tests_require=test_requirements,
    extras_require=extra_requirements,
    test_suite="tests",
    url="https://github.com/we3lab/pype-schema",
    version="0.6.1",
    zip_safe=False,
)
