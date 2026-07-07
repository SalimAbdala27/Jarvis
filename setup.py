from setuptools import setup


setup(
    name="jarvis",
    version="0.1.0",
    packages=[
        "jarvis",
        "jarvis.tools",
    ],
    include_package_data=True,
    install_requires=[],
    extras_require={"browser": ["playwright>=1.30.0,<1.39.0"]},
    python_requires=">=3.7",
)
