# Uncertainty and caveats in damage predictions

Per-building damage predictions from an EO-trained classifier carry several
distinct sources of uncertainty that operational users should keep in
mind. None of them are arguments against using the system; they are
arguments for treating the output as a decision-support signal rather
than ground truth.

**Model confidence is not calibrated.** The softmax probability attached
to each prediction reflects the model's relative ranking among the four
classes but should not be read as a literal probability that the class
is correct. A `destroyed` prediction at confidence 0.9 is not "90%
chance the building is destroyed" — it means the model strongly
preferred `destroyed` over the other three classes on this patch.
Confidence is best used as a ranking signal: low-confidence predictions
warrant manual review before they drive decisions.

**Class-boundary uncertainty.** The boundaries between classes are not
equally clear-cut. The hardest boundary is `no-damage` vs
`minor-damage`: it depends heavily on imagery resolution, lighting
between pre and post, and shadow geometry. The boundary between
`major-damage` and `destroyed` is generally cleaner because complete
collapse leaves an unambiguous signature. Reports that need a hard
threshold (e.g., damaged / not-damaged) should set it between
`minor-damage` and `major-damage` rather than between `no-damage` and
`minor-damage`.

**Spatial correlation.** Buildings that are physically close to each
other in a tile are not independent samples. Nearby structures share
lighting, shadow geometry, debris fields, smoke, and water — and the
model has seen them together during training. A cluster of confident
predictions in one neighborhood is partially evidence about the
neighborhood, not evidence about each individual building. Aggregating
to quadrant-level (mean severity per quadrant) accounts for this
implicitly.

**Training-data bias.** Class frequencies in xView2 train are highly
imbalanced. Some disaster events have very few examples of certain
damage classes — for example, the palu-tsunami train split contains
exactly one `minor-damage` building. The model therefore has effectively
no training signal for that class in tsunami imagery, and predictions
of `minor-damage` on tsunami scenes should be treated as noise.

**Dataset-domain generalization.** The classifier was trained on a
specific set of disasters at a specific sensor resolution. Performance
on out-of-distribution scenes (different climates, different urban form,
different sensor) is unknown and likely lower. Within the curated demo
catalog this is not an issue; for any future operational use it would
be.

**Edge effects.** Building patches near the edge of a 1024×1024 tile
have less surrounding context than centrally located ones. Predictions
for edge-located buildings may be marginally less reliable.

**Reporting practice.** The Uncertainty & Caveats section of the report
should call out: any quadrant where building counts are small (high
variance), any prediction class that is rare for the disaster type in
question, and the standard EO-limitation caveats (interior damage not
visible, registration / lighting effects on minor-damage predictions).
