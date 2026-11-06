from django import forms

from . import ml
from .validation import LIMITS

PLACEHOLDERS = {"temperature": "e.g. 21.5", "humidity": "e.g. 55", "wind_speed": "e.g. 12", "pressure": "e.g. 1013"}
STEPS = {"temperature": "0.1", "humidity": "1", "wind_speed": "0.1", "pressure": "0.1"}


def city_choices():
    return [(c["slug"], c["name"]) for c in ml.cities()]


def model_choices():
    if not ml.is_ready():
        return [("best", "Best model (auto)")]
    return [("best", "Best model (auto)")] + [(o["key"], o["label"]) for o in ml.model_options()]


class _Base(forms.Form):
    city = forms.ChoiceField(required=False, label="City")
    model = forms.ChoiceField(required=False, label="Model")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"].choices = city_choices()
        self.fields["model"].choices = model_choices()
        for f in ("city", "model"):
            self.fields[f].widget.attrs.update({"class": "form-select glass-input"})
        self.fields["model"].initial = "best"


class WeatherForm(_Base):
    temperature = forms.FloatField(label="Today’s mean temperature (°C)", min_value=LIMITS["temperature"][0], max_value=LIMITS["temperature"][1])
    humidity = forms.FloatField(label="Mean relative humidity (%)", min_value=LIMITS["humidity"][0], max_value=LIMITS["humidity"][1])
    wind_speed = forms.FloatField(label="Mean wind speed (km/h)", min_value=LIMITS["wind_speed"][0], max_value=LIMITS["wind_speed"][1])
    pressure = forms.FloatField(label="Mean surface pressure (hPa)", min_value=LIMITS["pressure"][0], max_value=LIMITS["pressure"][1])
    date = forms.DateField(label="Date of these readings", input_formats=["%Y-%m-%d"], widget=forms.DateInput(attrs={"type": "date"}))

    field_order = ["city", "model", "temperature", "humidity", "wind_speed", "pressure", "date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            f.error_messages["required"] = "Please enter a value."
            f.error_messages["invalid"] = "Enter a valid value."
            if name in PLACEHOLDERS:
                f.widget.attrs.update({"placeholder": PLACEHOLDERS[name], "step": STEPS[name]})


class BatchForm(_Base):
    file = forms.FileField(label="CSV file")
