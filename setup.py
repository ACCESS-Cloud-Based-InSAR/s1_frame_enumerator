from pathlib import Path

from setuptools import find_packages, setup

readme = Path(__file__).parent / 'README.md'

setup(
    name='s1-frame-enumerator',
    use_scm_version=True,
    description='Enumerates Sentinel-1 A/B Interferograms using burst-derived Frames',
    long_description=readme.read_text(),
    long_description_content_type='text/markdown',

    url='https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-enumerator',
    project_urls={},
    author='ACCESS Team',
    author_email='access-cloud-based-insar@jpl.nasa.gov',
    license='Apache 2.0',
     classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.8',
    install_requires=[
        'geopandas', 'rasterio', 'asf_search', 'tqdm', 'requests', 'dem_stitcher'
    ],

    extras_require={
        'develop': [
            'flake8',
            'flake8-import-order',
            'flake8-blind-except',
            'flake8-builtins',
            'pytest',
            'pytest-cov',
        ]
    },
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
