# Flood damage and assessment guidance

Flooding is the most challenging major disaster type for EO-based damage
assessment. The damage that matters operationally — interior water
contact, sewer back-flow, structural undermining of foundations — is
largely invisible from overhead. Reports based on EO imagery alone
systematically under-estimate flood damage; the report should make this
caveat explicit.

**Damage modes.**
- **Inundation without structural damage.** Most flooded buildings
  remain externally intact. From above, the only EO-visible signature
  is water around the building (during inundation) or sediment
  staining and debris fields (after waters recede). These structures
  often classify as `no-damage` or `minor-damage` despite severe
  interior loss. Inundation depth (which determines insurance and
  habitability) cannot be reliably estimated from overhead imagery.
- **Foundation undermining.** Fast-moving water erodes soil around and
  beneath foundations, sometimes causing partial collapse hours or
  days after waters recede. Damage may not be visible in the
  immediate post-event imagery.
- **Wash-out (`destroyed`).** Buildings displaced or destroyed by
  fast-moving water — typically in flash floods, dam-break floods,
  or storm-surge flooding. The structure is removed from its
  foundation; the footprint shows scoured ground or debris.
- **Debris impact damage.** Floodwaters transport debris (vehicles,
  parts of other structures, vegetation) at velocity; the impact can
  cause `major-damage`-class structural failures.

**Flood subtypes** produce different damage signatures:
- **Riverine flooding.** Gradual rise of water along a river system.
  Long inundation duration, mostly low velocity. Mostly `no-damage` and
  `minor-damage` from EO; severe interior damage. Midwest-flooding
  events are the canonical case.
- **Flash flooding.** Rapid rise, high velocity. Capable of structural
  destruction, especially in narrow canyons and steep watersheds.
  More `major-damage` and `destroyed` than riverine flooding.
- **Storm-surge flooding.** Coastal saltwater inundation driven by
  storm wind and pressure. High velocity at shoreline, decreases
  inland. Coastal `destroyed` cluster; inland buildings intact but
  inundated. Often co-occurs with hurricane wind damage.
- **Levee or dam failure.** Sudden, high-velocity release into normally
  protected areas. Severe `destroyed` damage close to the breach,
  decreasing with distance. Often catastrophic over a localized area.

**Spatial patterns.** Flood damage follows topography:
- Severity decreases with elevation. Two adjacent buildings on a slope
  can have very different damage status even though they were exposed
  to the same flood event.
- Riverbank proximity is a strong predictor in riverine events.
- Storm surge is sharply confined to coastal low-elevation zones.

**EO-signature challenges.**
- Floodwater may have already receded by the post-disaster pass,
  removing the most diagnostic signal.
- Sediment color changes (lightening of vegetation and ground) can be
  the only post-flood signal, and is subtle.
- Many flood-affected buildings will be visited by responders without
  any EO-based damage flag, on the basis of inundation maps from
  hydraulic models or high-water-mark surveys.

**Implications for the report:**
- A flood tile that predicts mostly `no-damage` should be reported with
  explicit caveats: "external appearance is preserved; interior damage
  is not assessable from overhead." Welfare checks should be
  recommended for all structures in flood-affected areas, not just
  those flagged with non-zero damage.
- The presence of any `destroyed` predictions in a flood scene is a
  strong signal of severe local conditions (flash flood, surge,
  levee/dam failure) and should be elevated in priority.
- The system's confidence is appropriately low on flood scenes;
  reports should defer to inundation maps and field reports over EO
  predictions for habitability decisions.
