# Limitations

noisedose supports exposure screening, calculation checks, and planning. It does not certify a workplace, hearing protector, measurement campaign, or person's safety, and it does not establish regulatory compliance. A competent person must perform and interpret the assessment using calibrated class 1 or class 2 equipment, appropriate settings, representative sampling, and the applicable legal and technical requirements.

## Measurement coverage

The calculation assumes each entered equivalent level represents its assigned duration. Overlapping intervals double count exposure; gaps and unrecorded tasks can understate it. A short sample cannot establish a whole shift's exposure unless its representativeness is justified. Projecting to eight hours or a specified shift assumes that the observed task mix and noise levels continue unchanged. Keep actual dose, projected eight-hour dose, and projected shift dose separate.

Instrument class alone does not verify calibration, frequency response, microphone placement, wind protection, overload handling, or the meter's integration settings. Validate those conditions and retain measurement records. Phone readings, product labels, and generic example data do not substitute for suitable workplace measurements. The sawmill, workshop, and office examples are illustrative and imply no product or occupational endorsement.

Equivalent A-weighted exposure and C-weighted peaks are different measurements. An equivalent level cannot reconstruct an unrecorded peak. Missing peak data leaves peak risk unknown. Do not subtract an NRR, SNR, HML reduction, or another A-weighted scalar from L_Cpeak. Impulsive noise and complex spectra can require more detailed measurement and specialist assessment.

## Regulatory interpretation

OSHA hearing conservation and PEL calculations use different dose integration thresholds and must remain separate. EU action values use unprotected exposure; the exposure limit accounts for protection actually afforded. Estimated attenuation alone cannot establish that limit's compliance. NIOSH recommendations, ACGIH guidance, and EU or OSHA legal requirements are not interchangeable. Local implementation, industry-specific rules, amendments, and other hazards can affect the required response. See the official sources in [methodology](methodology.md#references-and-editions).

Source thresholds must retain their exact values. Software classification of a result as strictly above a limit uses an unrounded value greater than that limit. Equality is at the limit, and action obligations can arise at equality. A rounded display or a status code is not a legal decision, nor does a result below a criterion imply zero hearing risk.

ISO 9612:2009 is an explicitly requested older, withdrawn reference. The simplified calculations do not implement a full ISO assessment or certify conformity with any edition. The ACGIH Noise TLV is copyrighted and must be checked in the current edition. The documentation summarizes conventions and links to sources; it does not reproduce full standards or provide access to them.

## Dose and energy conventions

A dose threshold excludes intervals strictly below that threshold from dose only. Physical sound energy remains nonzero below it. The EU energy method has no dose threshold. The exact 3 dB dose doubling rule differs slightly from the 3.0103 dB doubling of physical energy. The project's NIOSH TWA convention is `10 * log10(D/100) + 85`; the exact inverse of a Q dB exchange-rate dose uses `Q/log10(2)`. These differences can affect values near a classification boundary. Zero dose has no finite logarithmic TWA.

Weekly exposure uses an energy sum divided by five reference days. Omitting a nonworking day as zero energy does not mean entering a 0 dB exposure, and it does not change the denominator. Weekly averaging must satisfy the applicable conditions before being used in place of a daily comparison.

## Uncertainty coverage

The simplified task model assumes independent task sampling and duration errors. It treats shared instrument and microphone position errors as fully correlated across tasks, adding each component once. The assumed standard uncertainties of 0.7 dB for class 1, 1.5 dB for class 2, and 1.0 dB for position require site-specific review. They do not cover every systematic error, task misclassification, omitted exposure, or sampling bias.

Sampling standard uncertainty is the sample standard deviation divided by the square root of the sample count. With fewer than two samples it is unknown. Missing components cannot be treated as measured zero uncertainties. A known-component subtotal is a partial budget and does not support a complete ISO uncertainty claim or a complete exposure upper bound.

The multiplier 1.65 gives an approximate one-sided 95% upper bound under a normal approximation: `upper95 = L_EX,8h + 1.65 * u_c`. It does not define a symmetric 95% interval. Small samples, temporal dependence, correlated tasks, nonnormal errors, or uncertain variance estimates can require a different treatment. The stated coverage is an assumption, not a guarantee for an individual measurement campaign.

## Hearing protection

Laboratory attenuation ratings do not establish the attenuation received by an individual worker. Fit, wear time, maintenance, spectacle arms, other protective equipment, and training can change protection. A few unprotected intervals can materially increase exposure. Generic examples imply no endorsement.

The NIOSH 1998 derating options are historical. The [NIOSH 2025 policy update](https://www.cdc.gov/niosh/docs/2025-104/default.html) supersedes that guidance and recommends individual quantitative fit testing. The OSHA Appendix B base estimate and OSHA 50% engineering-control variant answer different assessment questions and must be labeled separately. The extra 5 dB for dual protection is approximate; the ratings of two devices are not additive. SNR and HML estimates require compatible C- and A-weighted equivalent measurements and suitable rating data.

EN 458 selection bands address predicted protected levels and communication needs. They are neither an individual fit test nor a legal compliance decision. Use suitable protection within a hearing loss prevention program that also addresses engineering controls, monitoring, training, and professional follow-up.
