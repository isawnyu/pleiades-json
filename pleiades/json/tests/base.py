from pleiades.workspace.tests.base import ContentFunctionalTestCase
from Products.Five import fiveconfigure
from Products.Five import zcml
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup
from Testing import ZopeTestCase as ztc

ztc.installProduct('ATVocabularyManager')
ztc.installProduct('Products.CompoundField')
ztc.installProduct('Products.ATBackRef')
ztc.installProduct('PleiadesEntity')


@onsetup
def setup_pleiades_json():
    """Set up the additional products required for the Pleiades site policy.

    The @onsetup decorator causes the execution of this body to be deferred
    until the setup of the Plone site testing layer.
    """
    fiveconfigure.debug_mode = True
    import pleiades.json
    zcml.load_config('configure.zcml', pleiades.json)
    fiveconfigure.debug_mode = False

    # We need to tell the testing framework that these products
    # should be available. This can't happen until after we have loaded
    # the ZCML.

    ztc.installPackage('pleiades.geographer')
    ztc.installPackage('pleiades.iterate')
    ztc.installPackage('plone.app.iterate')
    ztc.installPackage('pleiades.json')

# The order here is important: We first call the (deferred) function which
# installs the products we need for the Pleiades package. Then, we let
# PloneTestCase set up this product on installation.
setup_pleiades_json()
ptc.setupPloneSite(products=[
    'ATVocabularyManager',
    'Products.CompoundField',
    'Products.ATBackRef',
    'PleiadesEntity',
    # 'pleiades.workspace',
    'plone.app.iterate',
    'pleiades.geographer',
    'pleiades.contentratings'
])


class PleiadesJSONTestCase(ptc.PloneTestCase):
    """We use this base class for all the tests in this package. If necessary,
    we can put common utility or setup code in here.
    """


class PleiadesJSONFunctionalTestCase(ContentFunctionalTestCase):
    """We use this base class for all the tests in this package. If necessary,
    we can put common utility or setup code in here.
    """
    def afterSetUp(self):
        super(PleiadesJSONFunctionalTestCase, self).afterSetUp()
        pid = self.places.invokeFactory('Place', '2', title='Ninoe')
        p = self.places[pid]
        nameAttested = u'\u039d\u03b9\u03bd\u1f79\u03b7'.encode('utf-8')
        nid = p.invokeFactory(
            'Name', 'ninoe', nameAttested=nameAttested, nameLanguage='grc',
            nameType='geographic', accuracy='accurate', completeness='complete')
        attestations = p[nid].Schema()['attestations']
        attestations.resize(1)
        p[nid].update(
            attestations=[dict(confidence='certain', timePeriod='roman')])
        p.invokeFactory(
            'Location', 'position', title='Point 1',
            geometry='Point:[-86.4808333333333, 34.769722222222]')

        pid = self.places.invokeFactory('Place', '3', title='Ninoe',)
        p = self.places[pid]
        p.invokeFactory(
            'Location', 'undetermined', title='Undetermined location',
            geometry=None, location='http://atlantides.org/capgrids/35/E2')
        p.addReference(self.places['2'], "connectsWith")
