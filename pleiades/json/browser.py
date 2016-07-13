from Acquisition import aq_inner
from collective.geo.geographer.interfaces import IGeoreferenced
from DateTime import DateTime
from math import fabs, atan2, cos, pi, sin, sqrt
from pleiades.geographer.geo import extent, representative_point
from pleiades.geographer.geo import NotLocatedError
from pleiades.kml.browser import PleiadesBrainPlacemark
from pleiades.openlayers.proj import Transform, PROJ_900913
from plone.memoize.instance import memoize
from Products.CMFCore.utils import getToolByName
from Products.PleiadesEntity.time import to_ad
from pyproj import Proj
from shapely.geometry import asShape, mapping, Point, shape
from urllib import quote
from zope.interface import implements, Interface
from zope.publisher.browser import BrowserPage, BrowserView
from ZTUtils import make_query
import geojson
import logging

log = logging.getLogger("pleiades.json")

TGOOGLE = Transform(PROJ_900913)


class SnippetWrapper(object):

    def __init__(self, context):
        self.context = context

    @property
    def featureTypes(self):
        return ", ".join(x.capitalize() for x in (
            self.context.getFeatureType() or ["unknown"]))

    @property
    def snippet(self):
        sdata = [self.featureTypes]
        timespan = self.timeSpanAD
        if timespan:
            sdata += ["%(start)s - %(end)s" % timespan]
        return "; ".join(sdata)

    @property
    def author(self):
        return {'name': self.context.Creator(), 'uri': self.alternate_link}

    @property
    def timeSpan(self):
        try:
            trange = self.context.temporalRange()
            if trange:
                return {'start': int(trange[0]), 'end': int(trange[1])}
            else:
                return None
        except AttributeError:
            return None

    @property
    def timeSpanAD(self):
        span = self.timeSpan
        if span:
            return dict([(k, to_ad(v)) for k, v in span.items()])
        else:
            return None


def make_ld_context(context_items=None):
    """Returns a JSON-LD Context object.

    See http://json-ld.org/spec/latest/json-ld."""
    ctx = {
        'type': '@type',
        'id': '@id',
        'FeatureCollection': '_:n1',
        'bbox': 'http://geovocab.org/geometry#bbox',
        'features': '_:n3',
        'Feature': 'http://geovocab.org/spatial#Feature',
        'properties': '_:n4',
        'geometry': 'http://geovocab.org/geometry#geometry',
        'Point': 'http://geovocab.org/geometry#Point',
        'LineString': 'http://geovocab.org/geometry#LineString',
        'Polygon': 'http://geovocab.org/geometry#Polygon',
        'MultiPoint': 'http://geovocab.org/geometry#MultiPoint',
        'MultiLineString': 'http://geovocab.org/geometry#MultiLineString',
        'MultiPolygon': 'http://geovocab.org/geometry#MultiPolygon',
        'GeometryCollection': 'http://geovocab.org/geometry#GeometryCollection',
        'coordinates': '_:n5',
        'description': 'http://purl.org/dc/terms/description',
        'title': 'http://purl.org/dc/terms/title',
        'link': '_:n6',
        'location_precision': '_:n7',
        'snippet': 'http://purl.org/dc/terms/abstract',
        'connectsWith': '_:n8',
        'names': '_:n9',
        'recent_changes': '_:n10',
        'reprPoint': '_:n11'
        }
    for item in context_items or []:
        t, uri = item.split("=")
        ctx[t.strip()] = uri.strip()
    return ctx


def wrap(ob, project_sm=False):
    try:
        ex = extent(ob)
        precision = ex['precision']
        geometry = ex['extent']
        if project_sm:
            g = geometry.get('geometry', geometry)
            geo = TGOOGLE(g)
            geometry = geojson.GeoJSON.to_instance(geo)
    except (KeyError, TypeError, ValueError, NotLocatedError):
        geometry = None
        precision = None
    return geojson.Feature(
        id=ob.getId(),
        properties=dict(
            title=ob.Title(),
            snippet=SnippetWrapper(ob).snippet,
            description=ob.Description(),
            link=ob.absolute_url(),
            location_precision=precision,
            ),
        geometry=geometry,
    )


class W(object):
    # spatial 'within' wrapper for use as a sorting key

    def __init__(self, o):
        self.o = o

    def __lt__(self, other):
        try:
            return asShape(self.o.geometry).within(asShape(other.o.geometry))
        except ValueError:
            return False


class L(object):
    # Spatial length wrapper for use as a sorting key

    def __init__(self, o):
        self.k, v = o

    def __lt__(self, other):
        try:
            return asShape(
                eval(self.k)).length < asShape(eval(other.k)).length
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


def getContents(context, **kw):
    for r in context.getFolderContents():
        test = 1
        for k, v in kw.items():
            test *= (r[k] == v or v in r[k])
            if not test:
                break
        if test:
            try:
                yield r.getObject()
            except:
                raise


class FeatureCollection(JsonBase):

    @memoize
    def _data(self, published_only=False):
        if published_only:
            contentFilter = {'review_state': 'published'}
        else:
            contentFilter = {}
        sm = bool(self.request.form.get('sm', 0))
        x = sorted(
            getContents(
                self.context,
                **dict(
                    [('portal_type', 'Location')] + contentFilter.items())),
            reverse=True)

        if len(x) > 0:
            features = [wrap(ob, sm) for ob in x]
        else:
            features = [wrap(ob, sm) for ob in self.context.getFeatures()]

        try:
            ex = extent(self.context)
            bbox = shape(ex['extent']).bounds
            reprPoint = representative_point(self.context)['coords']
        except:
            bbox = None
            reprPoint = None

        # Names
        objs = sorted(
            getContents(
                self.context,
                **dict(
                    [('portal_type', 'Name')] + contentFilter.items())),
            reverse=True)
        names = [o.getNameAttested() or o.getNameTransliterated() for o in objs]

        # Modification time, actor, contributors
        try:
            context = aq_inner(self.context)
            rt = getToolByName(context, "portal_repository")
            records = []
            history = rt.getHistoryMetadata(context)
            if history:
                metadata = history.retrieve(-1)['metadata']['sys_metadata']
                records.append((metadata['timestamp'], metadata))
            for ob in getContents(self.context, **contentFilter):
                history = rt.getHistoryMetadata(ob)
                if not history:
                    continue
                metadata = history.retrieve(-1)['metadata']['sys_metadata']
                records.append((metadata['timestamp'], metadata))
            records = sorted(records, reverse=True)
            recent_changes = []
            modified = DateTime(records[0][0]).HTML4()
            principal0 = records[0][1]['principal']
            recent_changes.append(dict(modified=modified, principal=principal0))
            for record in records[1:]:
                principal = record[1]['principal']
                if principal != principal0:
                    modified = DateTime(record[0]).HTML4()
                    recent_changes.append(
                        dict(modified=modified, principal=principal))
                    break
        except:
            log.error(
                "Failed to find last change metadata for %s",
                repr(self.context),
            )
            recent_changes = None

        # connections
        connections = [o.getId() for o in self.context.getRefs(
            "connectsWith") + self.context.getBRefs("connectsWith")]

        return {
            '@context': make_ld_context(),
            'type': 'FeatureCollection',
            'id': self.context.getId(),
            'title': self.context.Title(),
            'description': self.context.Description(),
            'features': sorted(features, key=W, reverse=True),
            'recent_changes': recent_changes,
            'names': [unicode(n, "utf-8") for n in names],
            'reprPoint': reprPoint,
            'bbox': bbox,
            'connectsWith': connections
            }

    def mapping(self):
        return dict(self._data())

    def value(self, **kw):
        return geojson.dumps(self._data(**kw))

    def __call__(self, **kw):
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/json')
        self.request.response.setHeader(
            'Access-Control-Allow-Origin', '*')
        return self.value(**kw)


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
        shiftx = dx  # *sign(cx)
        shifty = dy  # *sign(cy)
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
    bbox = geom_bbox  # geom.bounds
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
        "<li><a href=\"%s\">%s</a> (<em>%s</em>): %s</li>" % (
            ob.alternate_link,
            ob.name,
            ob.snippet,
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
            where={'query': g.bounds, 'range': 'intersection'},
            portal_type={'query': ['Place']},
            location_precision={'query': ['rough']},
        )

    def getFeatures(self):
        portal_url = getToolByName(self.context, 'portal_url')()
        catalog = getToolByName(self.context, 'portal_catalog')
        try:
            g = IGeoreferenced(self.context)
            s = shape(g.geo)
            context_centroid = s.centroid
            if context_centroid.is_empty:
                context_centroid = Point(*s.exterior.coords[0])
        except (ValueError, NotLocatedError):
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
            if geo and 'type' in geo and 'coordinates' in geo:
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
                val,
            ) for key, val in sorted(objects.items(), key=L, reverse=True)]
        )

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


class ConnectionsFeatureCollection(FeatureCollection):

    @memoize
    def _data(self, published_only=False):
        context = self.context
        catalog = getToolByName(self.context, 'portal_catalog')
        wftool = getToolByName(self.context, 'portal_workflow')
        portal_url = getToolByName(self.context, 'portal_url')()
        sm = bool(self.request.form.get('sm', 0))
        xs = []
        ys = []
        if published_only:
            func = lambda f: wftool.getInfoFor(f, 'review_state') == 'published'
        else:
            func = lambda f: True
        conxns = [
            o for o in context.getConnectedPlaces()
            if func(o)]
        geoms = {}
        objects = {}
        features = []
        for ob in conxns:
            try:
                f = wrap(ob, sm)
                s = asShape(f.geometry)
                b = s.bounds
                xs.extend([b[0], b[2]])
                ys.extend([b[1], b[3]])
                gi = IGeoreferenced(ob)
                if gi.precision == 'rough':
                    brain = catalog(portal_type='Place', getId=ob.getId())[0]
                    item = PleiadesBrainPlacemark(brain, self.request)
                    geo = gi.__geo_interface__['geometry']
                    key = repr(geo)
                    if key not in geoms:
                        geoms[key] = geo
                    if key in objects:
                        objects[key].append(item)
                    else:
                        objects[key] = [item]
                else:
                    features.append(f)
            except (NotLocatedError, ValueError):
                log.error("Failed to located %s", ob)

        if len(xs) * len(ys) > 0:
            bbox = [min(xs), min(ys), max(xs), max(ys)]
        else:
            bbox = None

        try:
            g = IGeoreferenced(self.context)
            s = shape(g.geo)
            context_centroid = s.centroid
            if context_centroid.is_empty:
                context_centroid = Point(*s.exterior.coords[0])
        except (ValueError, NotLocatedError):
            if bbox is not None:
                context_centroid = Point(
                    (bbox[0]+bbox[2])/2.0, (bbox[1]+bbox[3])/2.0)
            else:
                return []

        rough_features = [
            aggregate(
                (context_centroid.x, context_centroid.y),
                portal_url,
                asShape(geoms[key]).bounds,
                val,
            ) for key, val in objects.items()
        ]

        return geojson.FeatureCollection(
            id=self.context.getId(),
            title=self.context.Title(),
            description=self.context.Description(),
            features=rough_features + sorted(features, key=W, reverse=True),
            bbox=bbox,
        )


class PlaceContainerFeatureCollection(BrowserPage):

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
            except (AttributeError, NotLocatedError, TypeError, ValueError):
                log.warn("Could not wrap2 catalog brain of %s", brain.getId)
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
            bbox=bbox,
        )
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/json')
        return geojson.dumps(c)


class SearchBatchFeatureCollection(FeatureCollection):

    @memoize
    def _data(self, brains=None):
        features = []
        xs = []
        ys = []

        for brain in brains:
            try:
                extent = brain.zgeo_geometry
                bbox = brain.bbox
                if not (extent or bbox):
                    continue
                bbox = bbox or shape(extent).bounds
                extent = extent or mapping(box(*bbox))
                reprPt = brain.reprPt and brain.reprPt[0] or list(
                    shape(extent).centroid.coords)[0]
                precision = brain.reprPt and brain.reprPt[1] or "unlocated"
                mark = PleiadesBrainPlacemark(brain, self.request)
            except Exception as e:
                log.exception(
                    "Search marking failure for %s: %s",
                    brain.getPath(), str(e))
                continue

            features.append(
                geojson.Feature(
                    id=brain.getId,
                    properties=dict(
                        title=brain.Title,
                        snippet=mark.snippet,
                        description=brain.Description,
                        link=brain.getURL(),
                        location_precision=precision,
                    ),
                    geometry={'type': 'Point', 'coordinates': reprPt},
                )
            )
            xs.extend([bbox[0], bbox[2]])
            ys.extend([bbox[1], bbox[3]])
        if len(xs) * len(ys) > 0:
            bbox = [min(xs), min(ys), max(xs), max(ys)]
        else:
            bbox = None

        return {
            '@context': make_ld_context(),
            'type': 'FeatureCollection',
            'id': 'search',
            'title': "Search Results",
            'description': "Geolocated objects in a batch of search results",
            'features': sorted(features, key=W, reverse=True),
            'bbox': bbox
            }

    def data_uri(self, **kw):
        return "data:application/json," + quote(self.value(**kw))
