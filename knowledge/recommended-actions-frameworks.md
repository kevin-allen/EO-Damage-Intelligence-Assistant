# Recommended-actions frameworks by severity bucket

A common operational pattern is to map an aggregated severity signal to
a tier of recommended actions. The mapping is not deterministic — actual
actions depend on access, available resources, time since event, and
ground truth from field teams — but the tiering is useful as a first
cut. The four tiers below correspond to the severity_index buckets used
in this system.

**Minor severity (severity_index < 0.25).** Predominantly intact
buildings, isolated damage. Recommended actions emphasize routine
assessment and the search for buildings that need attention but did not
make the threshold for higher tiers.
- Targeted welfare checks on flagged buildings.
- Utility inspections on isolated `minor-damage` or `major-damage`
  predictions.
- Aerial/satellite re-imaging in a few days to confirm conditions are
  stable (no delayed collapses, no secondary fires).
- Communicate to the public that the area is generally clear and
  re-entry is being managed.

**Moderate severity (0.25 ≤ severity_index < 0.50).** Mixed damage
distribution. Recommended actions emphasize systematic inspection and
selective restoration.
- Door-to-door welfare checks in affected blocks.
- Structural triage: identify buildings safe to re-occupy vs.
  buildings requiring detailed engineering inspection.
- Utility restoration where damage is partial and addressable.
- Identify any clusters of higher severity within the moderately-
  damaged area that warrant uplift to a higher response tier.

**Severe severity (0.50 ≤ severity_index < 0.75).** Most buildings are
in the `major-damage` or `destroyed` classes. Recommended actions shift
toward active search-and-rescue and immediate life-safety.
- Active SAR sweeps prioritized to areas with high `destroyed` density.
- Rapid structural assessment to identify standing-but-unsafe buildings
  threatening rescuers.
- Mass-care setup for displaced residents (temporary shelter, food and
  water distribution points).
- Active hazard mitigation: gas shut-offs, fire suppression on standing
  structures, identification of unstable adjacent buildings.

**Catastrophic severity (severity_index ≥ 0.75).** The area is dominated
by `destroyed` buildings. Recommended actions are heavy-rescue scale.
- Heavy-equipment SAR (urban search and rescue teams with breaching and
  shoring capability).
- Mass-fatality management resources should be requested.
- Mass shelter activation at scale (gymnasiums, schools, hotels).
- Full assumption that critical infrastructure in the area is non-
  functional; alternate routes for power, water, and communication need
  to be established.
- Long-term planning: this area will require months-to-years of recovery
  work; recovery resources should be requested early in the response.

**Cross-cutting actions, applicable at every tier:**
- Document conditions for insurance and federal-assistance claims.
- Maintain situational awareness via repeated imaging.
- Coordinate with neighboring jurisdictions when damage crosses
  administrative boundaries.
- Communicate accurate, time-stamped status to the public to manage
  re-entry and reduce demand on already-overstretched response.

The system's report should adapt these actions to the disaster type
(wildfire actions differ from earthquake actions even at the same
severity bucket) and to the spatial pattern observed (cluster vs.
uniform), grounded in retrieved knowledge documents rather than fixed
boilerplate.
