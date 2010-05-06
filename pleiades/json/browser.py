import geojson
from shapely.geometry import asShape

from zope.interface import implements, Interface, Attribute
from zope.publisher.browser import BrowserPage, BrowserView

from zgeo.geographer.interfaces import IGeoreferenced
from pleiades.openlayers.proj import Transform, PROJ_900913
from pleiades.capgrids import Grid

from Products.PleiadesEntity.geo import FeatureGeoItem


TGOOGLE = Transform(PROJ_900913)

def wrap(ob, project_sm=False):
    try:
        gi = IGeoreferenced(ob).__geo_interface__
        g = gi.get('geometry', gi)
        if project_sm:
            geo = TGOOGLE(g)
        else:
            geo = g
        
        geometry = geojson.GeoJSON.to_instance(geo)
                    #dict(type=geo.type, coordinates=geo.coordinates)
                    #)
    except (TypeError, ValueError):
        geometry = None
    return geojson.Feature(
                    id=ob.getId(),
                    properties=dict(
                        title=ob.title,
                        description=ob.description,
                        link=ob.absolute_url()
                        ),
                    geometry=geometry
                    )
        

class IJSON(Interface):
    def to_json():
        """As JSON"""
            
    
class Feature(BrowserView):
    implements(IJSON)
    
    def to_json(self):
        sm = bool(self.request.form.get('sm', 0))
        f = wrap(self.context, sm)
        return geojson.dumps(f)
        
    def __call__(self):
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/json')
        return self.to_json()


class GridFeature(object):
    
    implements(IGeoreferenced)
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
    
    def getId(self):
        return self.context.id
    
    @property
    def title(self):
        return unicode(self.context.Title())
    
    @property
    def description(self):
        return unicode(self.context.Description())
    
    def absolute_url(self):
        return self.context.id
    
    @property
    def type(self):
        return self.context.type
    
    @property
    def coordinates(self):
        return self.context.coordinates
    
    @property
    def __geo_interface__(self):
        return dict(type=self.context.type, coordinates=self.context.coordinates)


class FeatureCollection(BrowserPage):
    
    """
    """
    
    def __call__(self):
        sm = bool(self.request.form.get('sm', 0))
        xs = []
        ys = []
        features = [wrap(o, sm) for o in self.context.getFeatures()]
        x = list(self.context.getLocations())
        if len(x) > 0:
            features = [wrap(ob, sm) for ob in x] + features
        
        # get place bounds
        for f in features:
            if f.geometry and hasattr(f.geometry, '__geo_interface__'):
                shape = asShape(f.geometry)
                b = shape.bounds
                xs.extend([b[0], b[2]])
                ys.extend([b[1], b[3]])
        
        if len(xs) * len(ys) > 0:
            bbox = [min(xs), min(ys), max(xs), max(ys)]
        else:
            bbox = None
        
        c = geojson.FeatureCollection(
            id=self.context.getId(),
            features=list(features),
            bbox=bbox
            )
        
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/json')
        return geojson.dumps(c)
