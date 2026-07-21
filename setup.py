from setuptools import setup, find_packages

setup(
    name="abyss-security",
    version="1.0.0",
    description="ABYSS -- Hybrid ML Malware Detection & Incident Response CLI",
    author="ABYSS Team",
    packages=find_packages(),
    py_modules=["backend.abyss_cli"],
    install_requires=[],
    entry_points={
        "console_scripts": [
            "abyss=backend.abyss_cli:run_cli_scanner",
        ],
    },
    python_requires=">=3.8",
)
