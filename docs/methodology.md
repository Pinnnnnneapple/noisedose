# Methodology

noisedose calculates occupational noise exposure for screening and planning. Durations are in hours, equivalent levels are A-weighted decibels, and peaks require a separately measured peak metric with its frequency weighting identified. A competent person must plan and interpret measurements made with calibrated class 1 or class 2 equipment. Results do not certify compliance or replace a workplace assessment.

The equations below describe the project's calculation conventions. They are explanatory summaries, not verbatim reproductions of full standards. ISO 9612:2009 is the requested historical reference; using these equations does not establish conformity with that edition or a later edition. See [limitations](limitations.md) before interpreting a report.

## Energy exposure

For task or interval m, let T_m be its duration and L_m its representative equivalent level. Tasks must cover distinct periods without double counting. With T = sum(T_m), the equivalent level over the recorded period is

```text
L_Aeq,T = 10 log10(sum(T_m * 10^(L_m/10)) / T).
L_EX,8h = 10 log10(sum(T_m * 10^(L_m/10)) / 8)
        = L_Aeq,T + 10 log10(T / 8).
```

These are exact energy equations. The divisor 8 is the reference duration in hours; it does not assert that eight hours were measured. Arithmetic averaging of decibels gives a different quantity. Equally representative, equal-duration repeated measurements combine as

```text
L_m = 10 log10(sum(10^(L_mi/10)) / n_m).
```

Use duration weights when sample durations differ. The estimate assumes the samples represent the task's actual noise conditions and the assigned task duration.

Weekly exposure is normalized to five reference workdays:

```text
L_EX,w = 10 log10(sum_d(10^(L_EX,8h,d/10)) / 5).
```

Quiet or nonworking days assigned zero energy are omitted from the numerator; the denominator stays 5. A numeric level of 0 dB is nonzero energy and is not a missing day. Measured quiet-day exposure may be included. Weekly averaging requires a representative week and does not automatically authorize substituting a weekly value for a daily legal requirement.

## Exchange-rate dose and TWA

Let L_c be a criterion level, Q the exchange rate in decibels, and L_th the selected integration threshold. Allowable duration and actual accumulated dose are

```text
T_allow(L) = 8 * 2^((L_c - L) / Q)
D_actual = 100 * sum_m(T_m / T_allow(L_m)), for L_m >= L_th.
```

An interval strictly below the threshold contributes zero dose. Equality is included. Thresholding is a dose integration setting; it must not silently remove low-level energy from L_Aeq or L_EX. The EU energy calculation has no dose integration threshold.

[OSHA Appendix A](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.95AppA) gives the dose framework and OSHA conversion. The project's OSHA conventions use L_c = 90 dBA and Q = 5 dB. Hearing conservation uses an 80 dBA integration threshold and a 50% dose (85 dBA TWA) action value. The PEL calculation uses a separate 90 dBA threshold and 100% dose (90 dBA TWA) limit. Do not use a hearing conservation dose as the PEL dose. The governing requirements are in [29 CFR 1910.95](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.95).

The NIOSH convention uses L_c = 85 dBA, Q = 3 dB and an 80 dBA dose threshold. The ACGIH screening convention uses 85 dBA, a 3 dB exchange rate, and an 80 dBA dose threshold; confirm integration settings and all requirements against the current copyrighted Noise TLV before using an ACGIH comparison. NIOSH recommendations and ACGIH guidelines have different authority from an enforceable OSHA limit.

For positive dose, the reported conversions are

```text
OSHA TWA = 16.61 * log10(D / 100) + 90
NIOSH TWA = 10 * log10(D / 100) + 85   [requested project convention]
General exact exchange-rate inverse = (Q / log10(2)) * log10(D / 100) + L_c.
```

The published OSHA coefficient 16.61 is rounded; the calculation may retain `5/log10(2)` internally. For Q = 3, Q/log10(2) is about 9.9658, whereas exact energy uses coefficient 10. A doubling of energy is 10 log10(2) = 3.0103 dB. The exact 3 dB doubling dose rule therefore differs slightly from energy exposure: a single doubling differs by about 0.0103 dB when converted using the project's NIOSH TWA convention. Keep the dose calculation, the requested TWA convention, and exact energy L_EX distinct. For zero dose the logarithmic TWA is undefined (negative infinity mathematically), not 0 dBA.

### Actual and projected exposure

Actual dose integrates only the recorded intervals. A projection assumes the recorded mix of tasks continues at the same proportions and levels. For a recorded duration T and a specified shift duration H:

```text
D_projected,8h = D_actual * 8 / T
D_projected,shift = D_actual * H / T.
```

Report these as separate quantities with their reference durations. An eight-hour projection is not the observed dose or the dose for a longer shift. The actual L_EX,8h already normalizes the observed energy to eight hours; projecting the recorded pattern to H hours gives `L_Aeq,T + 10 log10(H/8)`. Projection requires T > 0 and representative sampling. If known remaining tasks differ, calculate them explicitly instead of scaling the observed mix.

An EU report may show an energy index relative to 85 dBA: `100 * 10^((L_EX,8h - 85)/10)`. Its equivalent reference duration is `8 * 10^((85 - L)/10)`. This uses exact energy without a threshold. It is not a legal EU dose limit; a 100% energy index is not the EU 87 dBA exposure limit.

## EU action and limit values

[Directive 2003/10/EC, Article 3](https://eur-lex.europa.eu/eli/dir/2003/10/oj) specifies the following daily exposure and C-weighted peak values:

| Comparison | L_EX,8h (dBA) | L_Cpeak (dBC) | Hearing protection |
| --- | ---: | ---: | --- |
| Lower action value | 80 | 135 | Unprotected exposure |
| Upper action value | 85 | 137 | Unprotected exposure |
| Exposure limit | 87 | 140 | Account for protection actually afforded |

Evaluate equivalent exposure and peak independently. Action values use unprotected exposure. A protector estimate cannot erase an action value. An NRR, SNR, or HML estimate alone does not establish compliance with the exposure limit. In particular, subtracting an A-weighted scalar attenuation from L_Cpeak is invalid.

Keep the exact source values in comparisons. An "above limit" classification means strictly greater than the limit, using unrounded values. Equality is at the limit. Action obligations may apply at equality, including OSHA's hearing conservation action level; a strict software exceedance label does not redefine those obligations. Report labels and exit statuses are screening conventions, not legal determinations.

## Simplified task uncertainty

For task m with n_m repeated representative level samples in dB, calculate the sample standard deviation with denominator n_m - 1 and the standard uncertainty of the sampled mean as

```text
s_m = sqrt(sum_i((L_mi - mean_dB_m)^2) / (n_m - 1))
u_sampling,m = s_m / sqrt(n_m).
```

Here `mean_dB_m` is the arithmetic mean used to compute the sample spread; energy averaging still determines the representative exposure level. This is a simplified propagation model. Fewer than two samples leaves sampling uncertainty unknown. A zero spread requires repeated identical measurements, not a missing or single measurement.

With duration standard uncertainty u(T_m) in hours, define energy weights and the combined standard uncertainty in dB:

```text
w_m = T_m * 10^(L_m/10) / sum_j(T_j * 10^(L_j/10))

u_c^2 = sum_m(w_m^2 * (s_m^2/n_m
          + ((10/ln(10)) * u(T_m)/T_m)^2))
        + u_instrument^2 + u_position^2.
```

Weights sum to one. This model treats task sampling and duration errors as independent between tasks and independent of each other. A shared instrument component and a shared microphone position component are each assumed fully correlated across tasks. Consequently, each is added once after the weighted task sum. Splitting one task into more rows must not reduce these shared components.

The project's assumed standard uncertainties are 0.7 dB for class 1 instrumentation or 1.5 dB for class 2, and 1.0 dB for microphone position. They are modeling assumptions, not guaranteed instrument errors, universal ISO constants, or substitutes for calibration and site-specific evidence. Duration uncertainties are standard uncertainties, not expanded bounds. A missing component is unknown; a subtotal of known components is a partial budget and must be labeled accordingly.

For a complete budget under this simplified model:

```text
U = 1.65 * u_c
upper95 = L_EX,8h + U.
```

The factor 1.65 approximates a one-sided 95% upper bound under a normal approximation. It is not a symmetric 95% interval. Small samples, dependent measurements, nonnormal errors, and uncertain variances can invalidate the approximation. No complete upper bound can be inferred from a partial budget. This calculation does not implement every sampling, uncertainty, or reporting requirement of ISO 9612:2009.

## Hearing protection estimates

All reductions below are estimates in decibels. A predicted protected equivalent A-weighted level is the unprotected level minus the applicable reduction. Real protection depends on fit, training, wear time, condition, and compatibility with other equipment. Generic examples or product data imply no endorsement.

### NRR methods

For A-weighted input, the [OSHA Appendix B](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.95AppB) base convention is

```text
R_base = max(0, NRR - 7)
L_A,protected = L_A - R_base.
```

The OSHA 50% engineering-control assessment variant is a distinct option:

```text
R_OSHA50 = max(0, 0.5 * (NRR - 7)).
```

The order matters: this is not `0.5 * NRR - 7`. See the [OSHA Technical Manual, noise chapter](https://www.osha.gov/otm/section-3-health-hazards/chapter-5) for the engineering-control context and dual protection estimates. C-weighted equivalent input uses the applicable NRR convention without the 7 dB A-weighting correction; a C-weighted equivalent level is not a C-weighted peak.

The historical [NIOSH 1998 criteria, publication 98-126](https://www.cdc.gov/niosh/docs/98-126/default.html) derating convention retained for comparison is

```text
R_historical = max(0, f * NRR - 7)
f = 0.50 for slow-recovery foam earplugs
f = 0.75 for earmuffs
f = 0.30 for other earplugs.
```

Apply the retained fraction first, then subtract 7, then clamp at zero. NIOSH's [2025 individual fit-testing recommendation](https://www.cdc.gov/niosh/docs/2025-104/default.html) supersedes this derating guidance. NIOSH now recommends individual quantitative fit testing to determine attenuation received by each worker. Historical derating must be labeled as historical.

For dual protection, the project uses the simplified combined nominal approximation `NRR_combined = max(NRR_plug, NRR_muff) + 5`, then applies the selected attenuation method to that combined rating. For A-weighted input, the project base reduction is `max(0, NRR_combined - 7)` and its OSHA 50% reduction is `max(0, 0.5 * (NRR_combined - 7))`. Thus, the project combines the ratings before derating; the 50% option also halves the additional 5 dB. With the historical NIOSH option, the selected protector-type fraction applies to the combined nominal rating before subtracting 7 and clamping at zero.

The OSHA Technical Manual dual-protection procedure adds 5 dB after adjusting the stronger device. Its A-weighted expressions are `(max(NRR_plug, NRR_muff) - 7) + 5` for the base procedure and `0.5 * (max(NRR_plug, NRR_muff) - 7) + 5` for the 50% variant. The project does not implement that OTM dual-protection procedure. Both approaches are approximate; label the convention used and do not add the two individual NRRs.

### SNR and HML

For SNR, use the C-weighted equivalent level: `L_A,protected = L_Ceq - SNR`. A-weighted input alone does not supply the required C-weighted level.

The SNR estimate is retained even if it exceeds the input LA. In this case no positive attenuation is credited, and an assessment note calls for review of the spectral suitability and matched measurements. The tool does not lower this conservative estimate to the unprotected A-weighted level.

For HML, let `delta = L_Ceq - L_Aeq`. H, M, and L are the manufacturer's high-, medium-, and low-frequency attenuation ratings. The predicted noise reduction PNR is

```text
if delta <= 2:
    PNR = M - (H - M)/4 * (delta - 2)
else:
    PNR = M - (M - L)/8 * (delta - 2)
L_A,protected = L_Aeq - PNR.
```

At delta = 2 both branches yield M. These equations require compatible equivalent A- and C-weighted measurements. They do not estimate protected L_Cpeak. ISO 4869-2 describes SNR, HML, and octave-band approaches; a scalar estimate lacks the frequency detail of an octave-band assessment.

The project's EN 458 selection guidance bands for predicted protected A-weighted levels are:

| Protected level (dBA) | Selection guidance |
| --- | --- |
| Below 65 | Too much attenuation |
| 65 to below 70 | Acceptable |
| 70 through 75 | Good |
| Above 75 through 80 | Acceptable |
| Above 80 | Insufficient attenuation |

These are selection guidance, not legal exposure limits or evidence of individual fit. Excessive attenuation can impede communication and warning signals.

## Input assumptions

Task durations are hours. Log intervals supplied in seconds are converted to hours. Importing a recognized header does not convert weighting, response time, or averaging settings: the user must verify that the data support the intended exposure calculation. In particular, LAS, LAF, or Lavg values are not automatically equivalent to an energy-averaged LAeq.

For timestamped logs, each row represents its forward interval; the final row uses the median of preceding intervals. A supplied fixed interval applies to every row. A single row or a log without timestamps requires a positive explicit interval. Timestamps must increase strictly and use compatible representations and timezones; clock-only midnight rollover is not inferred. These conventions can change total recorded duration and must be checked against instrument exports.

Repeated raw task samples support sampling uncertainty. A summary level plus a sample count does not reconstruct sample variation or create repeated measurements. A supplied task summary is retained; if no summary is supplied, the task level is derived from the samples by energy averaging. Duration uncertainty defaults to exact unless supplied, which is an explicit modeling assumption rather than evidence that timing error is absent.

## References and editions

- [OSHA, 29 CFR 1910.95, Occupational noise exposure](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.95), including [Appendix A, Noise Exposure Computation](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.95AppA) and [Appendix B, Methods for Estimating the Adequacy of Hearing Protector Attenuation](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.95AppB).
- [OSHA Technical Manual, Section III, Chapter 5, Noise](https://www.osha.gov/otm/section-3-health-hazards/chapter-5).
- [NIOSH, Criteria for a Recommended Standard: Occupational Noise Exposure, Revised Criteria 1998, DHHS (NIOSH) Publication 98-126](https://www.cdc.gov/niosh/docs/98-126/default.html). Its hearing protector derating guidance is superseded by [NIOSH Science Policy Update: Individual Fit-Testing Recommendation for Hearing Protection Devices, Publication 2025-104](https://www.cdc.gov/niosh/docs/2025-104/default.html).
- ACGIH, *TLVs and BEIs*, Physical Agents, Noise TLV. This is copyrighted material; obtain and verify the current edition and its qualifications through [ACGIH](https://www.acgih.org/). The project's screening convention is not a reproduction or verification of the current full TLV.
- [Directive 2003/10/EC of the European Parliament and of the Council of 6 February 2003](https://eur-lex.europa.eu/eli/dir/2003/10/oj), particularly Articles 2 and 3. Check national implementation and applicable amendments.
- [ISO 9612:2009, Acoustics — Determination of occupational noise exposure — Engineering method](https://www.iso.org/standard/41718.html). This requested older edition is withdrawn; consult the applicable edition for professional work. The catalog record does not provide access to the full standard.
- [ISO 4869-2:2018, Acoustics — Hearing protectors — Part 2: Estimation of effective A-weighted sound pressure levels when hearing protectors are worn](https://www.iso.org/standard/65582.html). The catalog describes the scope; it is not the full standard.
- EN 458:2016, *Hearing protectors — Recommendations for selection, use, care and maintenance — Guidance document*, the historical selection guidance reference. The [BSI EN 458 catalog](https://landingpage.bsigroup.com/LandingPage/Undated?UPI=000000000000325981) lists editions including its successor. Check the edition applicable to your assessment; no access to the full standard is implied.
