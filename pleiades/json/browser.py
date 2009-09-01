import geojson
from shapely.geometry import asShape

from zope.interface import implements
from zope.publisher.browser import BrowserPage

from zgeo.geographer.interfaces import IGeoreferenced
from pleiades.openlayers.proj import Transform, PROJ_900913

from Products.PleiadesEntity.geo import FeatureGeoItem


TGOOGLE = Transform(PROJ_900913)

def wrap(ob, project_sm=False):
    try:    
        g = IGeoreferenced(ob)
        if project_sm:
            geo = TGOOGLE(g)
        else:
            geo = g
        geometry = geojson.GeoJSON.to_instance(
                    dict(type=geo.type, coordinates=geo.coordinates)
                    )
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
        
class Feature(BrowserPage):
    
    """
    """
    
    def __call__(self):
        sm = bool(self.request.form.get('sm', 0))
        f = wrap(self.context, sm)
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
        x = self.context.getLocations()
        if len(x) > 0:
            features = [wrap(self.context, sm)] + features
            
        # get place bounds
        for f in features:
            if f.geometry:
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
