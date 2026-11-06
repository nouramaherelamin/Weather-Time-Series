"""python manage.py check_model  ->  verifies the app's predictions match the numbers recorded at training time."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from forecast import ml


class Command(BaseCommand):
    help = "Check that the web app reproduces the notebook/training predictions for the stored sample input."

    def handle(self, *args, **options):
        if not ml.is_ready():
            raise CommandError(f"No trained bundles found in {settings.MODELS_DIR}. Run `python train_app_models.py`.")
        bad = 0
        for c in ml.cities():
            b = ml.get_bundle(c["slug"])
            s = b["sample"]
            for key in b["models"]:
                r = ml.predict(c["slug"], key, date=s["date"], **s["inputs"])
                for f in r["forecast"]:
                    expected = s["predictions"][key][f["day"]]
                    if abs(f["prediction"] - expected) > 0.01:
                        bad += 1
                        self.stderr.write(f"MISMATCH {c['slug']}/{key}/day{f['day']}: app={f['prediction']} training={expected:.3f}")
            self.stdout.write(f"{c['name']}: sample {s['date']} checked for {len(b['models'])} models x 7 days")
        if bad:
            raise CommandError(f"{bad} mismatches")
        self.stdout.write(self.style.SUCCESS("OK - app predictions match the training pipeline"))
