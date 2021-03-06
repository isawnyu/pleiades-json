# Tests of roughly located neighbors and supporting functions

from math import sqrt
from pleiades.json.browser import aggregate, stick_interpolate
import unittest

SQRT2 = sqrt(2.0)


class InterpolationTestCase(unittest.TestCase):

    def assertPointEqual(self, a, b):
        return self.assertEqual(a[0], b[0]) and self.assertEqual(a[1], b[1])

    def assertPointAlmostEqual(self, a, b, precision=7):
        return self.assertAlmostEqual(
            a[0], b[0], precision) and self.assertAlmostEqual(
                a[1], b[1], precision)

    def test_center(self):
        """A singularity that we have to special case"""
        r, s = stick_interpolate((0.0, 0.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointEqual(r, (0.0, 0.0))
        self.assertPointEqual(s, (0.0, 0.0))

    def test_right_center_edge(self):
        r, s = stick_interpolate((1.0, 0.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (1.0, 0.0))
        self.assertPointAlmostEqual(s, (-SQRT2, 0.0))

    def test_left_center_edge(self):
        r, s = stick_interpolate((-1.0, 0.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (-1.0, 0.0))
        self.assertPointAlmostEqual(s, (SQRT2, 0.0))

    def test_beyond_right_center_edge(self):
        r, s = stick_interpolate((2.0, 0.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (SQRT2, 0.0))
        self.assertPointAlmostEqual(s, (-SQRT2, 0.0))

    def test_beyond_left_center_edge(self):
        r, s = stick_interpolate((-2.0, 0.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (-SQRT2, 0.0))
        self.assertPointAlmostEqual(s, (SQRT2, 0.0))

    def test_top_center_edge(self):
        r, s = stick_interpolate((0.0, 1.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (0.0, 1.0))
        self.assertPointAlmostEqual(s, (0.0, -SQRT2))

    def test_bottom_center_edge(self):
        r, s = stick_interpolate((0.0, -1.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (0.0, -1.0))
        self.assertPointAlmostEqual(s, (0.0, SQRT2))

    def test_beyond_top_center_edge(self):
        r, s = stick_interpolate((0.0, 2.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (0.0, SQRT2))
        self.assertPointAlmostEqual(s, (0.0, -SQRT2))

    def test_beyond_bottom_center_edge(self):
        r, s = stick_interpolate((0.0, -2.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (0.0, -SQRT2))
        self.assertPointAlmostEqual(s, (0.0, SQRT2))

    def test_inside_lower_left_corner(self):
        r, s = stick_interpolate((-0.9, -0.9), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (-0.9, -0.9))
        self.assertPointAlmostEqual(s, (1.0, 1.0))

    def test_inside_upper_right_corner(self):
        r, s = stick_interpolate((0.9, 0.9), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (0.9, 0.9))
        self.assertPointAlmostEqual(s, (-1.0, -1.0))

    def test_beyond_upper_right_corner(self):
        r, s = stick_interpolate((2.0, 2.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(r, (1.0, 1.0))
        self.assertPointAlmostEqual(s, (-1.0, -1.0))

    def test_beyond_and_left_upper_right_corner(self):
        r, s = stick_interpolate((1.0, 2.0), (-1.0, -1.0, 1.0, 1.0))
        self.assertPointAlmostEqual(
            r, (0.63245553203367588, 1.2649110640673518))
        self.assertPointAlmostEqual(
            s, (-0.63245553203367599, -1.264911064067352))


class AggregationTestCase(unittest.TestCase):

    def test_beyond_and_left_upper_right_corner(self):
        class MockContext(object):
            def getPath(self):
                return "foo"

        class MockBrainWrapper(object):
            alternate_link = "http://example.com"
            featureTypes = ["unknown"]
            timePeriods = ["roman"]
            altLocation = "somewhere"
            snippet = "Somewhere"

            def __init__(self, name):
                self.context = MockContext()
                self.name = name

        result = aggregate(
            (1.0, 2.0),
            "http://localhost/",
            (-1.0, -1.0, 1.0, 1.0),
            [MockBrainWrapper("1"), MockBrainWrapper("2")])
        self.assertEqual(
            result['type'], "pleiades.stoa.org.BoxBoundedRoughFeature")
