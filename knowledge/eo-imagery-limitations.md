# EO imagery limitations and uncertainty

Earth-observation imagery is a powerful but imperfect signal for building
damage assessment. Reports and operational decisions derived from it should
account for several systemic limitations.

**Ground sample distance (GSD).** xView2 uses Maxar imagery at roughly
0.3–0.5 m GSD (WorldView-2/3, GeoEye-1). At this resolution individual
buildings are clearly resolvable, but fine surface texture is not. Roof
material can usually be identified; window-level damage often cannot.
Small structural features like cracks, leaning walls, and partial
floor-by-floor collapse are at or below the limit of resolution.

**Off-nadir angle.** Satellites do not always image straight down. At
off-nadir angles, vertical structures appear leaning, and a building's
facade can occlude the ground beside it. Pre and post imagery captured at
different look angles produces apparent geometry changes that are not
damage. Dense urban areas with tall buildings are especially affected.

**Cloud cover and atmospheric effects.** Optical sensors cannot see
through cloud or heavy haze. Even partial cover degrades resolution and
color fidelity. After a major event the next usable pass may be hours to
days away, during which secondary collapses, fire spread, or smouldering
can alter conditions. Reports based on post-event imagery captured days
late should note the gap.

**Lighting and shadow.** Sun angle and time-of-day differ between pre and
post passes. Long shadows can mimic structural displacement; the loss of
expected shadow can indicate roof failure. Lighting-driven appearance
changes are a primary source of false-positive minor-damage predictions,
particularly along structure edges.

**Image registration.** Pre and post imagery is rarely perfectly
co-registered. Sub-pixel and meter-level shifts both occur. The xView2
dataset is curated to high registration quality, but operational data
feeds typically have residual misalignment that confounds
change-detection methods.

**Occlusion.** Trees, debris piles, vegetation, and adjacent buildings
can fully or partially hide structures. After major events debris fields
can occlude entire blocks. EO assessment is unreliable wherever the
target is occluded; these areas should be flagged for in-person inspection
rather than scored low-priority.

**Interior damage invisibility.** This is the fundamental limit. A
flooded building with no exterior change appears intact from above. A
building with internal structural failure can look sound. EO-based
building damage assessment is best understood as an exterior-condition
proxy, not a structural integrity certificate.

**Sensor and acquisition differences.** When pre and post imagery are
from different sensors or different orbits, systematic differences in
color, contrast, GSD, and look angle can confound change detection. xView2
minimizes this by curation; operational data typically does not.

**Implication for reporting.** Absence of detected damage is not the
same as confirmed absence of damage. Areas with weak EO signal (cloud
cover, occluded, flooded) should be elevated to "needs further
assessment" rather than ranked low priority.
