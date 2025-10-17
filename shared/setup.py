from setuptools import setup, find_packages

setup(
    name="adk-shared",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-dotenv",
    ],
    python_requires=">=3.13",
    description="Shared utilities for ADK agents deployment",
    author="Alfredo Delgado",
    url="https://github.com/AlfieDelgado/adk-deployment-engine",
)