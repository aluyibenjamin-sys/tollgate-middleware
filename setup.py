from setuptools import setup, find_packages

setup(
    name="tollgate-middleware",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask>=2.0.0",
    ],
    description="A tamper-resistant HTTP 402 monetization layer for Flask apps.",
    author="aluyibenjamin-sys",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Flask",
    ],
)
