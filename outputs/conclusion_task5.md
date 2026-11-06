# Task 5 - Conclusion
Test set = last 90 days (chronological split, no shuffling). Metrics in °C.

| Model                                              |   MAE |   RMSE |   MAPE |   sMAPE |
|:---------------------------------------------------|------:|-------:|-------:|--------:|
| ARIMAX + Fourier one-step                          | 0.659 |  0.87  |  2.266 |   2.253 |
| Persistence one-step                               | 0.69  |  0.939 |  2.351 |   2.337 |
| Feature model next-day (Django model)              | 0.692 |  0.876 |  2.394 |   2.372 |
| Climatology multi-step (train mean by day-of-year) | 1.01  |  1.218 |  3.496 |   3.473 |
| ARIMAX + yearly Fourier multi-step                 | 1.062 |  1.278 |  3.681 |   3.657 |
| Seasonal-naive multi-step (same day last year)     | 1.398 |  1.787 |  4.769 |   4.686 |
| ARIMA (2,1,2) non-seasonal multi-step              | 2.201 |  2.925 |  8.018 |   7.559 |
| Persistence multi-step                             | 2.245 |  2.995 |  8.208 |   7.701 |

**Multi-step (90-day) winner:** Climatology multi-step (train mean by day-of-year) (MAE 1.01 °C).
**One-step (next day) winner:** ARIMAX + Fourier one-step (MAE 0.659 °C).

One-step and multi-step numbers are not comparable: one-step models see the real previous days, multi-step models must extrapolate 90 days.
Daily temperature is very persistent, so one-step persistence is a strong baseline - a model must beat it to be useful. Over a long horizon
the ARIMAX forecast converges to the seasonal (Fourier) curve, so it can't know about individual heat waves; that is why its interval widens
and why it behaves like the climatology baseline.
ARIMAX diagnostics: Ljung-Box p-values {7: 7.407982746830066e-06, 14: 3.3646859155608456e-07, 30: 4.1544144806925015e-06}; walk-forward mean MAE (30-day horizon) = 1.1945578001646848.
Monthly SARIMA (m=12): {'model': 'SARIMA(1,0,1)(1,1,1,12), monthly means, 24-month holdout', 'MAE': 0.873, 'RMSE': 1.154, 'MAPE': 4.073, 'sMAPE': 4.209, 'aic': 229.84139088100954}.
