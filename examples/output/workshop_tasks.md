# Noise exposure assessment

Worker: Synthetic operator

Area: workshop tasks

Source: examples/workshop_tasks.csv

Measured: 8.00 h; LAeq: 90.8 dBA; LEX,8h: 90.8 dBA.

Projection shift: 8.00 h (representative-pattern estimate).

| Metric | osha-pel | osha-hc | niosh-rel | eu |
|---|---|---|---|---|
| Actual dose (%) | 49.5 | 77.9 | 375.0 | 380.7 |
| 8h TWA (dBA) | 84.9 | 88.2 | 90.7 | 90.8 |
| Projected 8h dose (%) | 49.5 | 77.9 | 375.0 | 380.7 |
| Projected 8h TWA (dBA) | 84.9 | 88.2 | 90.7 | 90.8 |
| Projected shift dose (%) | 49.5 | 77.9 | 375.0 | 380.7 |
| Projected shift TWA (dBA) | 84.9 | 88.2 | 90.7 | 90.8 |
| Status | ACTION LEVEL | ACTION LEVEL | OVER LIMIT | OVER LIMIT |

## Task energy contribution

Percent of unthresholded acoustic energy; differs from OSHA dose share.

| Task | Hours | LAeq dBA | Energy % |
|---|---:|---:|---:|
| Grinding | 1.500 | 97.0 | 78.1 |
| Welding | 3.000 | 88.0 | 19.7 |
| Assembly | 3.500 | 78.0 | 2.3 |

EU LCpeak: 128.0 dBC; BELOW ACTION. Peak protection is not inferred from NRR/SNR/HML.

Protector: foam (osha50), estimated 79.8 dBA: acceptable.

Estimated daily EU limit screen: at/below 87 dBA. Unprotected action obligations remain; peak protection is not assessed.
- Laboratory ratings estimate attenuation; individual field fit and protection are not assured.
- Attenuation is floored at zero; impulse noise and peak protection are not assessed.
- NRR minus 7 dB for A weighting, then 50% attenuation retained.

Simplified uncertainty: u = 1.88 dB; U = 3.10 dB (k = 1.65, one-sided ~95%). Upper estimate 93.90 dBA. Sampling budget complete.

## Recommendations

- Enrol exposed workers in a hearing conservation programme; arrange audiometry, training and monitoring as applicable.
- Engineering controls first: follow the hierarchy of controls, reduce noise at source, isolate equipment and then review exposure time.
- Select and individually fit-test hearing protection; verify continuous correct use and repeat the assessment after controls.
- EU upper action level reached: implement a technical/organisational noise reduction programme and enforce protector use as applicable.

## Notes


Actual dose uses recorded durations and each preset's threshold and exchange rate. TWA and LEX,8h are normalized to 8 hours. Projections repeat the measured exposure mix; they are estimates, not additional observations. EU action levels use unprotected exposure; 87 dBA / 140 dBC limit screening receives no estimated protector credit. Exposure-limit equality is ACTION LEVEL; OVER LIMIT denotes strictly above the limit. See docs/methodology.md for formulas and references.

Not a substitute for a competent person's assessment with calibrated class 1/2 instruments. Estimates depend on representative measurements and correct protector fit. NIOSH/ACGIH are guidance criteria, not OSHA permissible limits.
