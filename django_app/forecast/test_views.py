"""Django view tests:  cd django_app && python manage.py test   (no database and no internet needed)."""
import io
import json
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from . import batchio, ml, openmeteo
from .testutils import make_bundle

GOOD = {"city": "cairo", "model": "best", "temperature": "24", "humidity": "50", "wind_speed": "12", "pressure": "1012", "date": "2026-04-15"}


class ViewTestBase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ml.reset()
        ml.register(make_bundle("cairo", "Cairo, Egypt", 30.04, 31.24, seed=1))
        ml.register(make_bundle("aswan", "Aswan, Egypt", 24.09, 32.90, seed=2))

    @classmethod
    def tearDownClass(cls):
        ml.reset()
        super().tearDownClass()

    def setUp(self):
        cache.clear()


class PageTests(ViewTestBase):
    def test_pages_render(self):
        for name in ("/", "/insights/", "/about/", "/batch/", "/api/", "/api/swagger/"):
            r = self.client.get(name)
            self.assertEqual(r.status_code, 200, name)
        self.assertContains(self.client.get("/"), "Noura Maher Elamin")
        self.assertContains(self.client.get("/"), 'rel="icon"')                       # browser-tab icon

    def test_background_follows_city(self):
        self.assertContains(self.client.get("/?city=alexandria"), "alexandria.jpg")
        self.assertContains(self.client.get("/insights/?city=alexandria"), "--city-photo: url('/static/forecast/alexandria.jpg")
        r = self.client.post("/", {**GOOD, "city": "alexandria", "humidity": "999"})      # invalid form keeps the chosen city's photo
        self.assertContains(r, "--city-photo: url('/static/forecast/alexandria.jpg")
        self.assertContains(self.client.get("/?city=aswan"), "--city-photo: url('/static/forecast/aswan.jpg")
        self.assertContains(self.client.get("/?city=unknown"), "--city-photo: url('/static/forecast/cairo.jpg")   # unknown city -> default
        self.assertContains(self.client.get("/"), "--city-photo: url('/static/forecast/cairo.jpg")

    def test_api_playground_page(self):
        r = self.client.get("/api/")
        self.assertContains(r, 'id="playground"')
        self.assertContains(r, "api.js")

    def test_insights_city_switch(self):
        self.assertContains(self.client.get("/insights/?city=aswan"), "Aswan")

    def test_index_prediction(self):
        r = self.client.post("/", GOOD)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "forecastChart")
        self.assertContains(r, "chart-data")
        self.assertEqual(len(r.context["result"]["forecast"]), 7)
        self.assertEqual(len(self.client.session["hist"]), 1)

    def test_index_validation_error_is_inline(self):
        r = self.client.post("/", {**GOOD, "humidity": "150"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "less than or equal to 100")
        self.assertIsNone(r.context["result"])

    def test_missing_and_text_inputs(self):
        r = self.client.post("/", {**GOOD, "temperature": "", "pressure": "abc"})
        self.assertContains(r, "Please enter a value.")
        self.assertContains(r, "Enter a valid value.")

    def test_history_export_and_clear(self):
        self.client.post("/", GOOD)
        csv_text = self.client.get("/history/export.csv").content.decode()
        self.assertIn("pred_tomorrow", csv_text)
        self.assertEqual(len(csv_text.strip().splitlines()), 2)
        r = self.client.post("/history/clear/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(self.client.get("/history/export.csv").content.decode().strip().splitlines()), 1)

    def test_history_is_capped(self):
        for i in range(12):
            self.client.post("/", {**GOOD, "temperature": str(20 + i)})
        self.assertEqual(len(self.client.session["hist"]), 8)

    def test_batch_page_upload(self):
        f = SimpleUploadedFile("in.csv", batchio.SAMPLE_CSV.encode(), content_type="text/csv")
        r = self.client.post("/batch/", {"city": "cairo", "model": "best", "file": f})
        self.assertContains(r, "data:text/csv;base64,")
        self.assertEqual(r.context["ok"], 3)

    def test_batch_page_bad_file(self):
        f = SimpleUploadedFile("bad.csv", b"a,b\n1,2\n", content_type="text/csv")
        r = self.client.post("/batch/", {"file": f})
        self.assertContains(r, "Missing column")

    def test_batch_sample_download(self):
        r = self.client.get("/batch/sample.csv")
        self.assertEqual(r["Content-Type"], "text/csv")


class ApiTests(ViewTestBase):
    def test_predict_get(self):
        r = self.client.get("/api/predict/", GOOD)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(len(d["forecast"]), 7)
        self.assertIn("explain", d)
        self.assertEqual(d["city_slug"], "cairo")

    def test_predict_post_and_model_choice(self):
        d = self.client.post("/api/predict/", {**GOOD, "model": "rf", "city": "aswan"}).json()
        self.assertEqual(d["model"], "rf")
        self.assertEqual(d["city_slug"], "aswan")

    def test_predict_defaults_when_city_model_omitted(self):
        p = {k: v for k, v in GOOD.items() if k not in ("city", "model")}
        self.assertEqual(self.client.get("/api/predict/", p).status_code, 200)

    def test_predict_validation(self):
        r = self.client.get("/api/predict/", {**GOOD, "humidity": "999"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("humidity", r.json()["errors"])
        self.assertEqual(self.client.get("/api/predict/", {**GOOD, "city": "mars"}).status_code, 400)
        self.assertEqual(self.client.get("/api/predict/", {**GOOD, "date": "nope"}).status_code, 400)

    def test_latest_ok_and_cached(self):
        fake = {"date": "2026-10-28", "temperature": 25.1, "humidity": 48, "wind_speed": 11, "pressure": 1011, "source": "Open-Meteo",
                "history": [{"date": "2026-10-28", "temperature": 25.1}]}
        with mock.patch("forecast.views.openmeteo.fetch_latest", return_value=fake) as m:
            r1 = self.client.get("/api/latest/?city=cairo")
            r2 = self.client.get("/api/latest/?city=cairo")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["temperature"], 25.1)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(m.call_count, 1)                    # second call served from cache

    def test_latest_upstream_failure_and_unknown_city(self):
        with mock.patch("forecast.views.openmeteo.fetch_latest", side_effect=openmeteo.UpstreamError("down")):
            self.assertEqual(self.client.get("/api/latest/?city=cairo").status_code, 502)
        self.assertEqual(self.client.get("/api/latest/?city=mars").status_code, 400)

    def test_batch_json_and_csv(self):
        data = batchio.SAMPLE_CSV + "2026-13-40,99,50,10,1000\n"
        f = SimpleUploadedFile("in.csv", data.encode(), content_type="text/csv")
        d = self.client.post("/api/batch/", {"file": f}).json()
        self.assertEqual((d["count"], d["ok"], d["failed"]), (4, 3, 1))
        f = SimpleUploadedFile("in.csv", data.encode(), content_type="text/csv")
        r = self.client.post("/api/batch/?format=csv", {"file": f})
        self.assertEqual(r["Content-Type"], "text/csv")
        self.assertTrue(r.content.decode().startswith("line,status"))

    def test_batch_errors(self):
        self.assertEqual(self.client.post("/api/batch/", {}).status_code, 400)
        f = SimpleUploadedFile("bad.csv", b"x,y\n1,2\n", content_type="text/csv")
        self.assertEqual(self.client.post("/api/batch/", {"file": f}).status_code, 400)
        self.assertEqual(self.client.get("/api/batch/").status_code, 405)

    def test_models_health_openapi(self):
        d = self.client.get("/api/models/").json()
        self.assertEqual({c["slug"] for c in d["cities"]}, {"cairo", "aswan"})
        self.assertEqual(self.client.get("/api/health/").json()["status"], "ok")
        spec = self.client.get("/api/openapi.json").json()
        self.assertIn("/api/predict/", spec["paths"])

    @override_settings(API_RATE_LIMIT=3)
    def test_rate_limit(self):
        codes = [self.client.get("/api/predict/", GOOD).status_code for _ in range(5)]
        self.assertEqual(codes[:3], [200, 200, 200])
        self.assertEqual(codes[3:], [429, 429])
        self.assertIn("Retry-After", self.client.get("/api/predict/", GOOD))


class NoModelTests(SimpleTestCase):
    def setUp(self):
        self._saved = dict(ml._REG)
        ml.reset()
        cache.clear()

    def tearDown(self):
        for b in self._saved.values():
            ml.register(b)

    def test_pages_and_api_degrade_gracefully(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 503)
        self.assertContains(r, "train_app_models.py", status_code=503)
        self.assertEqual(self.client.get("/api/predict/", GOOD).status_code, 503)
        self.assertEqual(self.client.get("/api/health/").json()["status"], "no_model")
