
import geojson

from zope.interface import implements
from zope.publisher.browser import BrowserPage

from zgeo.geographer.interfaces import IGeoreferenced


class Feature(BrowserPage):

    """
    Example:
    
      >>> class GeoThing(object):
      ...     implements(IGeoreferenced)
      ...     type='Point'
      ...     coordinates=[0.0, 0.0]
      ...     Title=u'Foo'
      ...     Description=u'Foo thing'
      ...     def getId(self):
      ...         return 'foo'
      ...     def absolute_url(self):
      ...         return 'http://example.com/foo'
      >>> thing = GeoThing()
      >>> feature = Feature(thing, None)
      >>> feature()
      ''
      
    """
    def __call__(self):
        geo = IGeoreferenced(self.context)
        geometry = geojson.GeoJSON.to_instance(
            dict(type=geo.type, coordinates=geo.coordinates)
            )
        f = geojson.Feature(
            id=self.context.getId(),
            geometry=geometry,
            properties=dict(
                title=self.context.Title,
                description=self.context.Description,
                link=self.context.absolute_url()
                )
            )
        return geojson.dumps(f)

# class Collection