"""Pure-Python tests (no Django needed):  python -m unittest forecast.test_logic   (also run by `manage.py test`)."""
import datetime as dt
import unittest

from . import batchio, insights, ml, openapi, openmeteo, trainer, validation
from .testutils import make_bundle

BUNDLE = None


def setUpModule():
    global BUNDLE
    BUNDLE = make_bundle()
    ml.reset()
    ml.register(BUNDLE)


def tearDownModule():
    ml.reset()


class ValidationTests(unittest.TestCase):
    def test_valid(self):
        clean, err = validation.validate_inputs({"temperature": "21.5", "humidity": 55, "wind_speed": 12, "pressure": 1013, "date": "2026-04-15"})
        self.assertEqual(err, {})
        self.assertEqual(clean["date"], dt.date(2026, 4, 15))

    def test_errors(self):
        _, err = validation.validate_inputs({"temperature": "abc", "humidity": 101, "wind_speed": "", "pressure": "nan", "date": "2026-02-30"})
        self.assertEqual(set(err), {"temperature", "humidity", "wind_speed", "pressure", "date"})


class TrainerAndPredictTests(unittest.TestCase):
    def test_bundle_shape(self):
        self.assertEqual(set(BUNDLE["models"]), {"ridge", "gbr", "rf"})
        self.assertIn(BUNDLE["best_model"], BUNDLE["models"])
        for m in BUNDLE["models"].values():
            self.assertEqual(sorted(m["estimators"]), trainer.HORIZONS)

    def test_predict_structure(self):
        s = BUNDLE["sample"]
        r = ml.predict("cairo", "best", date=s["date"], **s["inputs"])
        self.assertEqual(len(r["forecast"]), 7)
        self.assertEqual([f["day"] for f in r["forecast"]], list(range(1, 8)))
        for f in r["forecast"]:
            self.assertLess(f["low"], f["prediction"])
            self.assertLess(f["prediction"], f["high"])
        self.assertEqual(r["prediction"], r["forecast"][0]["prediction"])
        self.assertEqual({e["feature"] for e in r["explain"]}, {"temperature", "humidity", "wind_speed", "pressure", "season"})

    def test_matches_training_sample(self):           # "app prediction == notebook/training prediction"
        s = BUNDLE["sample"]
        for key in BUNDLE["models"]:
            r = ml.predict("cairo", key, date=s["date"], **s["inputs"])
            for f in r["forecast"]:
                self.assertAlmostEqual(f["prediction"], s["predictions"][key][f["day"]], delta=0.01)

    def test_outside_range_flag(self):
        r = ml.predict("cairo", "ridge", 54, 50, 10, 1010, "2026-07-01")
        self.assertIn("temperature", r["outside_training_range"])

    def test_cache_returns_independent_copies(self):
        a = ml.predict("cairo", "ridge", 20, 50, 10, 1010, "2026-05-01")
        a["forecast"].clear()
        b = ml.predict("cairo", "ridge", 20, 50, 10, 1010, "2026-05-01")
        self.assertEqual(len(b["forecast"]), 7)

    def test_unknown_city_and_model(self):
        with self.assertRaises(KeyError):
            ml.predict("nowhere", "best", 20, 50, 10, 1010, "2026-05-01")
        with self.assertRaises(KeyError):
            ml.predict("cairo", "magic", 20, 50, 10, 1010, "2026-05-01")

    def test_comparison_and_options(self):
        c = ml.comparison("cairo")
        self.assertIn("Persistence (today = tomorrow)", c["series"])
        self.assertEqual(len(c["series"]["Ridge Regression"]), 7)
        self.assertEqual(sum(o["best"] for o in ml.model_options("cairo")), 1)


class BatchTests(unittest.TestCase):
    def test_roundtrip_with_errors(self):
        data = (batchio.SAMPLE_CSV + "2026-13-40,99,50,10,1000\n2026-05-01,abc,50,10,1000\n").encode()
        res = batchio.run_batch(batchio.parse_csv(data), ml.predict, "cairo", "best", ["cairo"], ["ridge", "gbr", "rf"])
        self.assertEqual([r["status"] for r in res], ["ok", "ok", "ok", "error", "error"])
        out = batchio.to_csv(res)
        self.assertTrue(out.startswith("line,status,error"))
        self.assertEqual(len(out.strip().splitlines()), 6)

    def test_bad_files(self):
        for bad in (b"", b"a,b\n1,2\n", b"date,temperature,humidity,wind_speed,pressure\n"):
            with self.assertRaises(batchio.BatchError):
                batchio.parse_csv(bad)
        with self.assertRaises(batchio.BatchError):
            batchio.parse_csv(b"x" * (batchio.MAX_BYTES + 1))


class OpenMeteoTests(unittest.TestCase):
    def payload(self):
        times = [f"2026-10-{d:02d}T{h:02d}:00" for d in (27, 28, 29) for h in range(24)]
        n = len(times)
        return {"hourly": {"time": times, "temperature_2m": [20.0] * n, "relative_humidity_2m": [50] * n,
                           "wind_speed_10m": [10] * n, "surface_pressure": [1012] * n}}

    def test_latest_complete_day(self):
        s = openmeteo.summarize(self.payload(), today=dt.date(2026, 10, 29))
        self.assertEqual(s["date"], "2026-10-28")            # today (29th) is incomplete -> excluded
        self.assertEqual(s["temperature"], 20.0)
        self.assertEqual(len(s["history"]), 2)

    def test_errors(self):
        with self.assertRaises(openmeteo.UpstreamError):
            openmeteo.summarize({"nope": 1})
        with self.assertRaises(openmeteo.UpstreamError):
            openmeteo.summarize(self.payload(), today=dt.date(2026, 10, 27))   # nothing complete before the 27th

        class Resp:
            def raise_for_status(self): raise RuntimeError("boom")
        with self.assertRaises(openmeteo.UpstreamError):
            openmeteo.fetch_latest(30, 31, http_get=lambda *a, **k: Resp())


class InsightsAndSpecTests(unittest.TestCase):
    def test_insights(self):
        i = insights.compute(BUNDLE["history"], BUNDLE["climatology"])
        self.assertEqual(len(i["monthly"]["mean"]), 12)
        self.assertEqual(len(i["recent"]["labels"]), 365)
        self.assertIn("trend_per_decade", i["kpis"])
        import json
        json.dumps(i)                                         # must be JSON-serialisable for json_script

    def test_openapi(self):
        spec = openapi.build_spec(["cairo"], ["ridge"])
        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertIn("/api/predict/", spec["paths"])
        self.assertIn("/api/batch/", spec["paths"])


if __name__ == "__main__":
    unittest.main()
