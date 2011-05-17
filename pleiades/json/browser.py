
from urllib import quote

import geojson
from shapely.geometry import asShape

from pleiades.capgrids import Grid
from pleiades.geographer.geo import FeatureGeoItem, NotLocatedError
from pleiades.openlayers.proj import Transform, PROJ_900913
from plone.memoize.instance import memoize
from zgeo.geographer.interfaces import IGeoreferenced
from zope.interface import implements, Interface, Attribute
from zope.publisher.browser import BrowserPage, BrowserView


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
    except (TypeError, ValueError, NotLocatedError):
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
        return dict(
            type=self.context.type, coordinates=self.context.coordinates)


class W(object):
    # spatial 'within' wrapper for use as a sorting key
    def __init__(self, o):
        self.o = o
    def __lt__(self, other):
        return asShape(self.o.geometry).within(asShape(other.o.geometry))


class IJSON(Interface):
    def mapping():
        """As dict"""
    def value():
        """As JSON"""
    def data_uri():
        """JSON data URI"""


class JsonBase(BrowserView):
    implements(IJSON)

    def mapping(self):
        raise NotImplementedError

    def value(self):
        raise NotImplementedError

    def data_uri(self):
        return "data:application/json," + quote(self.value())

    # backwards compatibility
    to_json = value


class Feature(JsonBase):

    @memoize
    def _data(self):
        sm = bool(self.request.form.get('sm', 0))
        return wrap(self.context, sm)
        
    def mapping(self):
        return dict(self._data())

    def value(self):
        return geojson.dumps(self._data())

    def __call__(self):
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/json')
        return self.value()


class FeatureCollection(JsonBase):

    @memoize
    def _data(self):
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
        
        return geojson.FeatureCollection(
            id=self.context.getId(),
            features=sorted(features, key=W, reverse=True),
            bbox=bbox
            )

    def mapping(self):
        return dict(self._data())

    def value(self):
        return geojson.dumps(self._data())

    def __call__(self):
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/json')
        return self.value()


class PlaceContainerFeatureCollection(BrowserPage):
    
    """
    """
    
    def __call__(self):
        xs = []
        ys = []
        catalog = self.context.portal_catalog
        portal_path = self.context.portal_url.getPortalObject().getPhysicalPath()
        def wrap2(brain):
            try:
                ob = brain.getObject()
                rel_path = ob.getPhysicalPath()[len(portal_path):]
                g = IGeoreferenced(ob)
                return dict(
                    id=str(brain.getRID()),
                    bbox=g.bounds,
                    properties=dict(
                        path='/'.join(rel_path),
                        title=brain.Title,
                        description=ob.Description() or ob.getDescription(),
                        type=brain.portal_type,
                        ),
                    geometry=dict(type=g.type, coordinates=g.coordinates)
                    )
            except (AttributeError, NotLocatedError, TypeError):
                return None
        def generate():
            for brain in catalog(portal_type={'query': ['Place', 'Location']}):
                w = wrap2(brain)
                if w is not None:
                    b = w["bbox"]
                    xs.extend([b[0], b[2]])
                    ys.extend([b[1], b[3]])
                    yield w
        features = list(item for item in generate())
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

