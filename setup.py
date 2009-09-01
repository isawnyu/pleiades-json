from setuptools import setup, find_packages
import os

version = '0.2'

setup(name='pleiades.json',
      version=version,
      description="",
      long_description=open("README.txt").read(),
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='',
      author='Plone Foundation',
      author_email='plone-developers@lists.sourceforge.net',
      url='http://svn.plone.org/svn/plone/plone.example',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['pleiades'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'geojson',
          'shapely',
          'zgeo.plone.geographer',
          'pleiades.openlayers'
          ],
      tests_require=[
          'pleiades.workspace'
          ],
      )
