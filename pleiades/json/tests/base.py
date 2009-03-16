from Products.Five import zcml
from Products.Five import fiveconfigure

from Testing import ZopeTestCase as ztc

from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup

from pleiades.workspace.tests.base import ContentFunctionalTestCase

ztc.installProduct('ATVocabularyManager')
ztc.installProduct('Products.CompoundField')
ztc.installProduct('Products.ATBackRef')
ztc.installProduct('PleiadesEntity')
ztc.installProduct('zgeo.plone.geographer')

@onsetup
def setup_pleiades_json():
    """Set up the additional products required for the Pleiades site policy.
    
    The @onsetup decorator causes the execution of this body to be deferred
    until the setup of the Plone site testing layer.
    """

    # Load the ZCML configuration for the optilux.policy package.
    
    fiveconfigure.debug_mode = True
    import pleiades.json
    zcml.load_config('configure.zcml', pleiades.json)
    fiveconfigure.debug_mode = False
    
    # We need to tell the testing framework that these products
    # should be available. This can't happen until after we have loaded
    # the ZCML.

    ztc.installPackage('pleiades.workspace')
    ztc.installPackage('pleiades.json')
    
# The order here is important: We first call the (deferred) function which
# installs the products we need for the Pleiades package. Then, we let 
# PloneTestCase set up this product on installation.

setup_pleiades_json()
ptc.setupPloneSite(
    products=[
    'ATVocabularyManager',
    'Products.CompoundField',
    'Products.ATBackRef',
    'PleiadesEntity',
    'pleiades.workspace',
    'zgeo.plone.geographer', 
    ])

class PleiadesJSONTestCase(ptc.PloneTestCase):
    """We use this base class for all the tests in this package. If necessary,
    we can put common utility or setup code in here.
    """

class PleiadesJSONFunctionalTestCase(ContentFunctionalTestCase):
    """We use this base class for all the tests in this package. If necessary,
    we can put common utility or setup code in here.
    """

    # def afterSetUp(test):
    #     test.setRoles(('Manager',))
    #     pt = test.portal.portal_types
    #     for type in [
    #         'Topic', 
    #         'PlaceContainer', 
    #         'FeatureContainer',
    #         'Workspace Folder',
    #         'Workspace',
    #         'Workspace Collection',
    #         'Place',
    #         'Feature',
    #         ]:
    #         lpf = pt[type]
    #         lpf.global_allow = True
    # 
    #     _ = test.portal.invokeFactory(
    #         'PlaceContainer', id='places', title='Places', 
    #         description='All Places'
    #         )
    #     _ = test.portal.invokeFactory(
    #         'FeatureContainer', id='features', title='Features'
    #         )
    #     _ = test.portal.invokeFactory(
    #         'Workspace Folder', id='workspaces', title='Workspaces'
    #         )
    # 
    #     test.features = test.portal['features']
    #     test.places = test.portal['places']
    #     test.workspaces = test.portal['workspaces']
    # 
    #     # Add feature
    # 
    #     fid = test.features.invokeFactory('Feature', '1', title='Ninoe', featureType='settlement')
    #     f = test.features[fid]
    #     nameAttested = u'\u039d\u03b9\u03bd\u1f79\u03b7'.encode('utf-8')
    #     nid = f.invokeFactory('Name', 'ninoe', nameAttested=nameAttested, nameLanguage='grc', nameType='geographic', accuracy='accurate', completeness='complete')
    #     attestations = f[nid].Schema()['attestations']
    #     f[nid].update(attestations=[dict(confidence='certain', timePeriod='roman')])
    #     lid = f.invokeFactory('Location', 'location', title='Point 1', geometry='Point:[-86.4808333333333, 34.769722222222]')
    # 
    #     # Add place
    # 
    #     pid = test.places.invokeFactory('Place', '1', title='Ninoe')
    #     p = test.places[pid]
    #     nid = p.invokeFactory('Name', 'ninoe', nameAttested=nameAttested, nameLanguage='grc', nameType='geographic', accuracy='accurate', completeness='complete')
    #     attestations = p[nid].Schema()['attestations']
    #     p[nid].update(attestations=[dict(confidence='certain', timePeriod='roman')])
    # 
    #     # And references    
    #     f.addReference(p, 'feature_place')
