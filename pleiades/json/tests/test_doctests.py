import unittest
from Testing import ZopeTestCase as ztc
from Products.PloneTestCase import PloneTestCase as ptc
from pleiades.json.tests.base import PleiadesJSONFunctionalTestCase

ptc.setupPloneSite()


def test_suite():
    return unittest.TestSuite([

        ztc.FunctionalDocFileSuite(
            'json.txt', package='pleiades.json.tests',
            test_class=PleiadesJSONFunctionalTestCase
        ),

        ztc.FunctionalDocFileSuite(
            'wrap.txt', package='pleiades.json.tests',
            test_class=PleiadesJSONFunctionalTestCase
            ),

        ztc.FunctionalDocFileSuite(
            'place.txt', package='pleiades.json.tests',
            test_class=PleiadesJSONFunctionalTestCase
            ),

    ])
