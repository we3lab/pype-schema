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
    "Sphinx==4.2.0",
]

requirements = [
    "pint==0.19.2",
    "networkx==2.8.5",
    "pyvis==0.2.1",
    "matplotlib==3.5.2",
    "pandas==1.4.0",
    "numpy==1.22.1"
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
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    description="Class hierarchy to represent a wastewater treatment plant's configuration.",
    entry_points={},
    long_description=readme,
    long_description_content_type="text/x-rst",
    package_data={"wwtp_configuration": ["wwtp_configuration/data/*"]},
    include_package_data=True,
    keywords="wwtp-configuration",
    name="wwtp-configuration",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    python_requires=">=3.9",
    install_requires=requirements,
    setup_requires=setup_requirements,
    tests_require=test_requirements,
    extras_require=extra_requirements,
    test_suite="tests",
    url="https://github.com/we3lab/wwtp-configuration",
    version="0.2.3",
    zip_safe=False,
)
