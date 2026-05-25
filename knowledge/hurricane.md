# Hurricane damage and assessment guidance

Hurricanes (also called typhoons and cyclones depending on the basin)
produce three coupled damage mechanisms: wind, storm surge, and rainfall
flooding. Each mechanism produces a different signature in overhead
imagery, and each has a different relationship to standard building
damage classes.

**Wind damage** is the most directly visible from above. Failure modes,
in roughly increasing wind speed:
- Loss of shingles, tiles, or roof covering (visible as discoloration or
  exposed underlayment); classifies as `minor-damage`.
- Loss of roof sheathing or partial roof removal; classifies as
  `major-damage`.
- Loss of upper-story walls, partial structural collapse; `major-damage`.
- Complete loss of structure, often leaving only foundation slabs;
  `destroyed`.

Wind damage scales steeply with wind speed: doubling the wind speed
roughly quadruples the pressure load. Cat 4–5 storms (Michael, Maria,
Ida) produce extensive `destroyed`-class buildings near landfall; Cat
1–2 storms produce mostly `minor-damage` even in heavily exposed areas.

**Storm surge** produces inundation at low elevations along the coast.
From overhead, surge damage is often partly hidden — a flooded but
intact-looking building from above may have severe interior damage,
collapsed walls below the visible roofline, or foundation undermining.
Surge damage is most visible at the destroyed end of the spectrum
(complete washout of structures within a few hundred meters of the
coast). Hurricane Katrina (2005) and Hurricane Ian (2022) produced
canonical examples of total surge destruction in coastal communities.

**Rainfall flooding** produces inland inundation, often miles to
hundreds of miles from the storm track (Hurricane Harvey, 2017,
deposited 60+ inches of rain on metropolitan Houston). Rainfall-flood
damage is the most under-estimated by EO assessment, because flooded
buildings often appear intact from above. The flood signature is in
the surrounding water extent and in debris fields after waters recede.

**Spatial patterns.** Hurricane damage shows clear directional and
distance gradients:
- Highest wind damage at the eye-wall path on the right-front quadrant
  (in the Northern Hemisphere); damage decreases away from this axis.
- Surge damage is sharply confined to low-elevation coastal zones
  (typically within ~1 km of coastline, less inland).
- Rain flooding follows watersheds and is concentrated in low-lying
  inland basins.

A hurricane scenario tile may show very different patterns depending on
where it sits along the storm's path. A coastal tile may be dominated
by surge damage (uniform across the inundated zone); an inland tile may
show wind damage clustered around the storm-track axis.

**Implications for the report:**
- A predominantly `major-damage` distribution with little `destroyed` in
  a hurricane tile is consistent with wind damage in the Cat 2–3 range
  or with the periphery of a stronger storm.
- A `destroyed`-heavy distribution in a coastal tile is consistent with
  storm surge near eye-wall landfall.
- Tiles with mostly `no-damage` predictions in a flooding-prone area
  should not be interpreted as confirmation of safety — flood damage is
  often invisible from above.
- Recommended actions should include flood-damage welfare checks on
  externally-intact buildings in low-elevation hurricane scenarios.
