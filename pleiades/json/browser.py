import logging
from math import fabs, atan2, cos, pi, sin, sqrt
from urllib import quote

import geojson
from pyproj import Proj
from shapely.geometry import asShape, LineString, Point

from Acquisition import aq_inner
from DateTime import DateTime
from plone.app.layout.viewlets.content import ContentHistoryViewlet
from plone.memoize.instance import memoize
from Products.CMFCore.utils import getToolByName
from zope.interface import implements, Interface, Attribute
from zope.publisher.browser import BrowserPage, BrowserView
from ZTUtils import make_query

from pleiades.capgrids import Grid
from pleiades.contentratings.basic import rating
from pleiades.geographer.geo import FeatureGeoItem, NotLocatedError
from pleiades.kml.browser import PleiadesBrainPlacemark
from pleiades.openlayers.proj import Transform, PROJ_900913
from zgeo.geographer.interfaces import IGeoreferenced

log = logging.getLogger("pleiades.json")

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
        try:
            return asShape(self.o.geometry).within(asShape(other.o.geometry))
        except ValueError:
            return False

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
        x = sorted(self.context.getLocations(), key=rating, reverse=True)
        location_ratings = sorted(
            (rating(o) for o in self.context.getLocations()), reverse=True)

        if len(x) > 0:
            features = [wrap(ob, sm) for ob in x]
        else:
            features = [wrap(ob, sm) for ob in self.context.getFeatures()] \
                     + [wrap(ob, sm) for ob in self.context.getParts()]

        # get place bounds and representative point
        repr_point = None
        for f, r in zip(features, location_ratings):
            if f.geometry and hasattr(f.geometry, '__geo_interface__'):
                shape = asShape(f.geometry)
                b = shape.bounds
                xs.extend([b[0], b[2]])
                ys.extend([b[1], b[3]])
                if repr_point is None and r > 0.0:
                    repr_point = shape.centroid
        if len(xs) * len(ys) > 0:
            bbox = [min(xs), min(ys), max(xs), max(ys)]
        else:
            bbox = None
        
        if repr_point:
            reprPoint = (repr_point.x, repr_point.y)
        else:
            reprPoint = None

        # Names
        objs = sorted(self.context.getNames(), key=rating, reverse=True)
        names = [o.getNameAttested() or o.getNameTransliterated() for o in objs]

        # Modification time and and actor
        try:
            context = aq_inner(self.context)
            rt = getToolByName(context, "portal_repository")
            records = []
            history = rt.getHistoryMetadata(context)
            if history:
                metadata = history.retrieve(-1)['metadata']['sys_metadata']
                records.append((metadata['timestamp'], metadata))
            for ob in context.listFolderContents():
                history = rt.getHistoryMetadata(ob)
                if not history: continue
                metadata = history.retrieve(-1)['metadata']['sys_metadata']
                records.append((metadata['timestamp'], metadata))
            records = sorted(records, reverse=True)
            modified = DateTime(records[0][0]).HTML4()
            actor = records[0][1]['principal']
        except:
            log.error(
                "Failed to find last change metadata for %s", repr(self.context))
            modified = None
            actor = None

        return geojson.FeatureCollection(
            id=self.context.getId(),
            title=self.context.Title(),
            description=self.context.Description(),
            features=sorted(features, key=W, reverse=True),
            modified=modified,
            author=actor,
            names=[unicode(n, "utf-8") for n in names],
            reprPoint=reprPoint,
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

def sign(x):
    if x < 0:
        return -1.0
    else:
        return 1.0

def stick_interpolate(cc, bbox):
    """Given a context centroid and a box, find the bisecting line that goes 
    through each centroid, interpolated to the context centroid point.
    
    Approximate using a circle around the box.
    """

    TOLERANCE = 1.0e-6
    
    # transform to a coordinate system centered on ccx, ccy
    llx, lly, urx, ury = bbox
    ccx, ccy = cc
    llx -= ccx
    urx -= ccx
    lly -= ccy
    ury -= ccy

    # Centroid of the transformed box
    cx = (llx + urx)/2.0
    cy = (lly + ury)/2.0

    W = urx - llx
    H = ury - lly

    # Radius of a circle that circumscribes the box
    R = sqrt(W*W + H*H)/2.0

    # If the bbox centroid is at the origin, things collapse
    if (fabs(cx) < TOLERANCE and fabs(cy) < TOLERANCE):
        rx = ry = sx = sy = 0.0
    elif (fabs(cx) >= TOLERANCE and fabs(cy) >= TOLERANCE):
        theta = atan2(cy, cx)
        dx = R*sin(theta)
        dy = R*cos(theta)
        shiftx = dx #*sign(cx)
        shifty = dy #*sign(cy)
        if theta <= -pi/2.0 or theta >= pi/2.0:
            shiftx, shifty = shifty, shiftx
        rx = cx - shiftx
        sx = cx + shiftx
        ry = cy - shifty
        sy = cy + shifty
        if cx > 0:
            rx = max(0.0, rx)
        else:
            rx = min(0.0, rx)
        if cy > 0:
            ry = max(0.0, ry)
        else:
            ry = min(0.0, ry)
    # Our stick is on one of the axes
    else:
        # On the x axis
        if fabs(cx) < TOLERANCE:
            rx = sx = 0.0
            if cy > 0:
                ry = max(0.0, cy-R)
                sy = cy+R
            else:
                ry = min(0.0, cy+R)
                sy = cy-R
        # On the y axis
        if fabs(cy) < TOLERANCE:
            ry = sy = 0.0
            if cx > 0:
                rx = max(0.0, cx-R)
                sx = cx+R
            else:
                rx = min(0.0, cx+R)
                sx = cx-R
    return (rx+ccx, ry+ccy), (sx+ccx, sy+ccy)

def aggregate(context_centroid, portal_url, geom_bbox, objects):
    """A feature that is related to roughly located objects"""
    bbox = geom_bbox #geom.bounds
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    query = {
        'location_precision': ['rough'],
        'path': {'query': [ob.context.getPath() for ob in objects],
                 'depth': 0}
        }

    props = dict(
        title="Aggregation of roughly located objects",
        snippet="%s degree by %s degree cell" % (
            bbox[2]-bbox[0], bbox[3]-bbox[1]),
        link="%s/search?%s" % (portal_url, make_query(query)))
    
    description = "".join(
        "<li><a href=\"%s\">%s</a> (<em>%s; %s</em>): %s</li>" % (
            ob.alternate_link, 
            ob.name, 
            ob.featureTypes, 
            ob.timePeriods, 
            ob.altLocation or "") for ob in objects)
    props['description'] = "<div><ul>" + description + "</ul></div>"

    # Compute the "sticks"
    # First, project to spherical mercator
    cclon, cclat = context_centroid

    tsm = Proj(PROJ_900913)
    
    (ccx, llx, urx), (ccy, lly, ury) = tsm(
        [cclon, bbox[0], bbox[2]], 
        [cclat, bbox[1], bbox[3]])

    (rx, ry), (sx, sy) = stick_interpolate((ccx, ccy), (llx, lly, urx, ury))

    # Transform back from centroid origin system, and back to long, lat
    (rlon, slon), (rlat, slat) = tsm(
        [rx, sx], [ry, sy], inverse=True)

    return dict(
        type="pleiades.stoa.org.BoxBoundedRoughFeature",
        id=repr(bbox),
        properties=props,
        bbox=bbox,
        geometry=dict(type="LineString", coordinates=[[rlon, rlat], [slon, slat]]))


class RoughlyLocatedFeatureCollection(JsonBase):
    """."""

    def criteria(self, g):
        return dict(
            where={'query': g.bounds, 'range': 'intersection' }, 
            portal_type={'query': ['Place']},
            location_precision={'query': ['rough']}
            )

    def getFeatures(self):
        portal_url = getToolByName(self.context, 'portal_url')()
        catalog = getToolByName(self.context, 'portal_catalog')
        try:
            g = IGeoreferenced(self.context)
            context_centroid = asShape(g.geo).centroid
        except NotLocatedError:
            return []
        log.debug("Criteria: %s", self.criteria(g))
        geoms = {}
        objects = {}
        brains = catalog(**self.criteria(g))
        for brain in brains:
            if brain.getId == self.context.getId():
                # skip self
                continue
            item = PleiadesBrainPlacemark(brain, self.request) 
            geo = brain.zgeo_geometry
            if geo and geo.has_key('type') and geo.has_key('coordinates'):
                key = repr(geo)
                if not key in geoms:
                    geoms[key] = geo
                if key in objects:
                    objects[key].append(item)
                else:
                    objects[key] = [item]
        return list(
            [aggregate(
                (context_centroid.x, context_centroid.y),
                portal_url,
                asShape(geoms[key]).bounds, 
                val) for key, val in objects.items()]
                )
                #],
                #key=W,
                #reverse=True)

    @memoize
    def _data(self):
        sm = bool(self.request.form.get('sm', 0))
        xs = []
        ys = []
        # get place bounds
        features = self.getFeatures()
        for f in features:
            b = f.get('bbox')
            if b:
                xs.extend([b[0], b[2]])
                ys.extend([b[1], b[3]])
        if len(xs) * len(ys) > 0:
            bbox = [min(xs), min(ys), max(xs), max(ys)]
        else:
            bbox = None
        
        return geojson.FeatureCollection(
            id=self.context.getId(),
            features=features,
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

