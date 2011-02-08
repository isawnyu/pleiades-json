
import logging

import geojson
from pleiades.geographer.geo import NotLocatedError
from shapely.geometry import asShape
from zgeo.geographer.interfaces import IGeoreferenced

log = logging.getLogger('pleiades.json')

def location_precision(rec, catalog):
    v = catalog._catalog.getIndex('location_precision').getEntryForObject(
        rec.getRID(), default=['unlocated'])
    try:
        return v[0]
    except IndexError:
        return 'unlocated'

def getGeometry(rec, catalog):
    geo = None
    try:
        geo = dict(rec.zgeo_geometry.items())
    except:
        log.warn("Unlocated: %s" % rec.getPath())
    return geo

class PlaceContainerFeatureCollection(object):
    def __init__(self, context):
        self.context = context
    def __call__(self):
        xs = []
        ys = []
        catalog = self.context.portal_catalog
        def wrap2(brain):
            try:
                rel_path = brain.getPath().replace('/plone', '')
                geo = getGeometry(brain, catalog)
                if geo is None:
                    return None
                g = asShape(geo)
                return dict(
                    id=str(brain.getRID()),
                    bbox=g.bounds,
                    properties=dict(
                        path=rel_path,
                        title=brain.Title,
                        description=brain.Description,
                        type=brain.portal_type,
                        ),
                    geometry=dict(geo)
                    )
            except (AttributeError, NotLocatedError, TypeError):
                return None

        def generate():
            for brain in catalog(
                portal_type={'query': ['Place', 'Location']}):
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
        return geojson.dumps(c)

if __name__ == '__main__':
    site = app['plone']
    view = PlaceContainerFeatureCollection(site)
    sys.stdout.write(view())
    
