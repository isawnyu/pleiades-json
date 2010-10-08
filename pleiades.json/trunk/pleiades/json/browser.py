import geojson
from shapely.geometry import asShape

from zope.interface import implements, Interface, Attribute
from zope.publisher.browser import BrowserPage, BrowserView

from zgeo.geographer.interfaces import IGeoreferenced
from pleiades.openlayers.proj import Transform, PROJ_900913
from pleiades.capgrids import Grid

from Products.PleiadesEntity.geo import FeatureGeoItem, NotLocatedError


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


class W(object):
    # spatial 'within' wrapper for use as a sorting key
    def __init__(self, o):
        self.o = o
    def __lt__(self, other):
        return asShape(self.o.geometry).within(asShape(other.o.geometry))


class FeatureCollection(BrowserPage):
    
    """
    """
    
    def __call__(self):
        sm = bool(self.request.form.get('sm', 0))
        xs = []
        ys = []
        x = list(self.context.getLocations())
        if len(x) > 0:
            features = [wrap(ob, sm) for ob in x]
        else:
            features = [wrap(ob, sm) for ob in self.context.getFeatures()] \
                     + [wrap(ob, sm) for ob in self.context.getParts()] 
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
            features=sorted(features, key=W, reverse=True),
            bbox=bbox
            )
        
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/json')
        return geojson.dumps(c)

def wrap2(ob):
    try:
        gi = IGeoreferenced(ob).__geo_interface__
        geom = gi.get('geometry', gi)
        shape = asShape(geom)
        return dict(
            id=ob.UID(),
            bbox=shape.bounds,
            properties=dict(
                pid=ob.getId(),
                title=ob.title,
                description=ob.description,
                ),
            geometry=geom
            )
    except (AttributeError, NotLocatedError):
        return None

class PlaceContainerFeatureCollection(BrowserPage):
    
    """
    """
    
    def __call__(self):
        xs = []
        ys = []
        def generate():
            for ob in self.context.values():
                w = wrap2(ob)
                if w is not None:
                    b = w["bbox"]
                    xs.extend([b[0], b[2]])
                    ys.extend([b[1], b[3]])
                    yield w
        features = list(p for p in generate())
        if len(xs) * len(ys) > 0:
            bbox = [min(xs), min(ys), max(xs), max(ys)]
        else:
            bbox = None
        c = geojson.FeatureCollection(
            features=features,
            bbox=bbox
            )        
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/json')
        return geojson.dumps(c)

