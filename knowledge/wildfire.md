# Wildfire damage and assessment guidance

Wildfire damage is the most binary of the major disaster types: a
structure either survives (typically with minor or no visible damage) or
burns to its foundation. Intermediate states are rare. This produces a
characteristic bimodal damage distribution: most buildings in a fire-
affected tile are either `no-damage` or `destroyed`, with comparatively
few in `minor-damage` or `major-damage`. EO imagery captures this signal
clearly because burned-to-foundation structures leave an unambiguous
visual signature.

**Damage modes.**
- **Full combustion (`destroyed`).** Complete loss of the structure
  above the foundation. The remaining footprint shows a debris field
  of ash and unburned metal (appliances, vehicle remains, HVAC units).
  Concrete slab foundations are often clearly visible as light-colored
  rectangles in the ash field.
- **Partial damage (`minor-damage` / `major-damage`).** Less common in
  pure wildfire scenes. Caused by ember-driven roof ignitions that
  were extinguished, partial side-wall damage from adjacent burning,
  or smoke and heat damage without ignition.
- **Intact (`no-damage`).** Structures that survived the fire — usually
  through defensible space (cleared vegetation, fire-resistant
  materials), favorable wind/topography, or active suppression.
  Surviving structures may look almost untouched from above even when
  adjacent properties are completely destroyed.

**Wildland-urban interface (WUI).** Most loss-of-life-and-property
wildfires affect WUI areas — where developed land meets wildland
vegetation. WUI tiles show characteristic spatial mixing: surviving
structures interspersed with destroyed structures, often along clear
property lines or vegetation gradients. The 2018 Camp Fire (which
destroyed the town of Paradise, California) is a canonical example;
the 2017 Tubbs and 2017 Thomas fires in northern California are
similar.

**Ember-driven spread.** Wildfires propagate not only by direct flame
contact but by wind-blown embers, which can ignite structures hundreds
of meters to several kilometers from the main fire front. This is why
WUI fires produce "spot" damage patterns inconsistent with a simple
fire-front boundary: isolated destroyed structures appear well outside
the main burn area.

**Spatial patterns.**
- Damage often aligns with the fire's direction of travel (wind-driven
  spread).
- Topography matters: fire moves faster uphill, so structures on
  hillsides are differentially affected.
- Defensible space and construction type produce visible "lucky" islands
  of surviving structures within otherwise destroyed neighborhoods.
- Vegetation cover and density in pre-disaster imagery is the best
  ex-post predictor of where damage will land.

**Post-fire structural concerns.**
- Even structurally intact buildings in fire zones may have toxic
  contamination (ash, soot infiltration, asbestos from neighboring
  collapses); welfare checks should include re-entry safety
  assessment.
- Still-standing partially-damaged structures may have weakened
  framing and are at risk of delayed collapse, especially under wind
  loading.
- Smoldering hotspots can re-ignite for days to weeks after the main
  fire passes.

**Implications for the report:**
- A wildfire tile with mostly `destroyed` and `no-damage` predictions
  and very little `minor-damage` is the typical wildfire signature; this
  is not a model error.
- The spatial pattern within a wildfire tile — which structures survived
  and which did not — is operationally important for re-entry and
  re-building. The priority-zones table is most useful in moderate-
  wildfire tiles where some quadrants survived while others did not.
- Recommended actions should include hotspot monitoring, re-entry
  staging, and welfare checks on structurally-surviving residents who
  may nonetheless need evacuation due to contamination or utility loss.
