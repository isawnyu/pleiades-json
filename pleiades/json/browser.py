
import geojson
from shapely.geometry import asShape

from zope.interface import implements
from zope.publisher.browser import BrowserPage

from zgeo.geographer.interfaces import IGeoreferenced
from pleiades.openlayers.proj import Transform, PROJ_900913

TGOOGLE = Transform(PROJ_900913)

def wrap(ob, project_sm=False):
    g = IGeoreferenced(ob)
    if project_sm:
        geo = TGOOGLE(g)
    else:
        geo = g
    geometry = geojson.GeoJSON.to_instance(
        dict(type=geo.type, coordinates=geo.coordinates)
        )
    return geojson.Feature(
        id=ob.getId(),
        geometry=geometry,
        properties=dict(
            title=ob.title,
            description=ob.description,
            link=ob.absolute_url()
            )
        )

class Feature(BrowserPage):
    
    """
    """
    
    def __call__(self):
        f = wrap(self.context)
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/json')
        return geojson.dumps(f)


class FeatureCollection(BrowserPage):
    
    """
    """
    
    def __call__(self):
        sm = bool(self.request.form.get('sm', 0))
        xs = []
        ys = []
        features = [wrap(o, sm) for o in self.context.getFeatures()]
        
        # get place bounds
        for f in features:
            shape = asShape(f.geometry)
            b = shape.bounds
            xs.extend([b[0], b[2]])
            ys.extend([b[1], b[3]])
        minx = min(xs)
        miny = min(ys)
        maxx = max(xs)
        maxy = max(ys)
        
        c = geojson.FeatureCollection(
            id=self.context.getId(),
            features=features,
            bbox=[minx, miny, maxx, maxy]
            )
        
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/json')
        return geojson.dumps(c)        