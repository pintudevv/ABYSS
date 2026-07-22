from setuptools import setup, find_packages

setup(
    name="abyss-security",
    version="1.0.0",
    description="ABYSS -- Hybrid ML Malware Detection & Incident Response CLI",
    author="ABYSS Team",
    packages=find_packages(include=["backend", "backend.*"]),
    package_data={
        "backend": ["mock_data/*"],
    },
    include_package_data=True,
    install_requires=[
        "rich>=12.0.0",
    ],
    entry_points={
        "console_scripts": [
            "abyss=backend.abyss_cli:run_cli_scanner",
        ],
    },
    python_requires=">=3.8",
)
