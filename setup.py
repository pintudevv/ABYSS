from setuptools import setup, find_packages

setup(
    name="abyss-security",
    version="1.0.1",
    description="ABYSS -- Hybrid ML Malware Detection & Incident Response CLI",
    author="ABYSS Team",
    packages=find_packages(),
    py_modules=["abyss"],
    package_data={
        "": ["*.json", "*.txt", "*.csv", "*.db"],
    },
    include_package_data=True,
    install_requires=[
        "rich>=12.0.0",
    ],
    entry_points={
        "console_scripts": [
            "abyss=abyss:main",
        ],
    },
    python_requires=">=3.8",
)
