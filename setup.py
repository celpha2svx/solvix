from setuptools import find_packages, setup


setup(
    name="solvix",
    version="0.2.6",
    description="Computational intelligence layer for developers",
    author="Solvix Contributors",
    author_email="maintainers@solvix.dev",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "tree-sitter>=0.25.0",
        "tree-sitter-language-pack>=0.13.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "pygments>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "solvix=cli.main:main",
        ]
    },
)
