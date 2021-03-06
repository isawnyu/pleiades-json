from setuptools import setup, find_packages

version = '0.16'

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
          'geojson',
          'shapely',
          'pleiades.openlayers',
          'pleiades.geographer'
          ],
      tests_require=[
          'pleiades.workspace'
          ],
      )
