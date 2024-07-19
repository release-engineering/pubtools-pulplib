from setuptools import setup

try:
    from setuptools import find_namespace_packages
except ImportError:
    # Workaround for RHEL-8 RPM packaging that uses setuptools 39.2
    # find_namespace_packages is supported since setuptools 40.1
    # Loosely backported from https://github.com/pypa/setuptools/blob/main/setuptools/discovery.py
    from setuptools import PackageFinder

    class PEP420PackageFinder(PackageFinder):
        @staticmethod
        def _looks_like_package(_path):
            return True

    find_namespace_packages = PEP420PackageFinder.find


def get_description():
    return "A Pulp library for publishing tools"


def get_long_description():
    with open("README.md") as f:
        text = f.read()

    # Long description is everything after README's initial heading
    idx = text.find("\n\n")
    return text[idx:]


def get_requirements():
    with open("requirements.txt") as f:
        return f.read().splitlines()


setup(
    name="pubtools-pulplib",
    version="2.39.2",
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    package_data={"pubtools.pulplib._impl.schema": ["*.yaml"]},
    url="https://github.com/release-engineering/pubtools-pulplib",
    license="GNU General Public License",
    description=get_description(),
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=get_requirements(),
    python_requires=">=3.6",
    project_urls={
        "Documentation": "https://release-engineering.github.io/pubtools-pulplib/",
        "Changelog": "https://github.com/release-engineering/pubtools-pulplib/blob/master/CHANGELOG.md",
    },
)
