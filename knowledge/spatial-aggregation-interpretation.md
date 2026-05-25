# Interpreting spatial aggregations of damage

The system reports damage aggregated to four image quadrants (NW, NE, SW,
SE), with a `mean_severity` value per quadrant and a count of buildings.
This produces a coarse but actionable spatial signal. The geographic
units are not neighborhoods — they are arbitrary image-coordinate
quadrants — and the report should treat them accordingly.

**What the quadrant signal can tell you.** The mean-severity value per
quadrant captures the local concentration of damage. A quadrant with
`mean_severity = 0.8` is dominated by `major-damage` or `destroyed`
buildings; one at `0.2` is dominated by intact buildings. Sorting
quadrants by `mean_severity` descending gives a useful prioritization
order *within the tile*: the area most likely to need urgent response
is at the top.

The signal is most informative when there is *contrast* across
quadrants. A tile with one quadrant at 0.9 and three at 0.1 reveals a
clear spatial concentration, suggesting a localized impact (an
earthquake-induced building cluster failure, a fire front, a
storm-surge inundation line). A tile with all four quadrants at ~0.6
suggests a uniformly affected area, where geographic prioritization
within the tile adds little — the priority signal is at the tile level,
not the quadrant level.

**What it cannot tell you.** The quadrant boundaries are placed at the
image center (512, 512 in pixel coordinates for a 1024×1024 tile). They
do not align with streets, neighborhoods, parcel boundaries, or natural
features. A real damage cluster that straddles the center line is split
across two quadrants and appears as moderate severity in each, even
though it should be treated as a single high-priority area. Reports
should describe the quadrant signal as "image-quadrant" rather than as
a named area.

**Sparse quadrants are noisy.** A quadrant with very few buildings can
show extreme `mean_severity` values that are not statistically
meaningful. A 2-building quadrant with 1 destroyed and 1 major reads
0.83, but a single mis-classification flips it dramatically. The
priority-zones table includes the building count for exactly this
reason: high severity over few buildings is a softer signal than the
same severity over many buildings.

**Empty quadrants are not informative.** A quadrant with zero buildings
in the tile (e.g., open water, agricultural land, undeveloped area)
reports `total = 0, mean_severity = 0.0`. This is not "no damage there";
it means "no buildings to assess there." Reports should not treat empty
quadrants as low-priority.

**Cross-quadrant patterns to look for.** Common spatial patterns:
- **Gradient.** Severity decreases along a clear axis (e.g., away from
  the coast in a hurricane, along the fire perimeter in a wildfire).
  Suggests a directional hazard.
- **Cluster.** One quadrant dominates the rest. Suggests a focused
  impact (epicentral, low-elevation flooding pocket, single building
  collapse propagating).
- **Uniform.** All quadrants roughly equal. Suggests a broad,
  non-localized hazard at the tile scale.

The LLM commentary in the report should describe the observed pattern
in these qualitative terms rather than restate the numbers (which are
already in the table).
