from setuptools import setup, find_packages

setup(
    name="adk-shared",
    version="0.2.2",
    packages=find_packages(),
    install_requires=[
        "python-dotenv>=1.1.1",
        "setuptools>=80.9.0",
    ],
    python_requires=">=3.13",
    description="Shared utilities for ADK agents deployment",
    author="Alfredo Delgado",
    url="https://github.com/AlfieDelgado/adk-deployment-engine",
)