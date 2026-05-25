# Disaster-response prioritization

Disaster response is fundamentally a triage problem: scarce response
capacity (search teams, medical resources, transportation, shelter) must
be allocated across an affected area to maximize lives saved and minimize
follow-on harm. Different agencies use different formal frameworks, but
the underlying priority hierarchy is broadly shared.

**The hierarchy of priorities** in standard incident-command framing:

1. **Life-safety.** Areas with credible signal of trapped, stranded, or
   injured survivors get top priority. From overhead imagery this signal
   is the density of `destroyed` and `major-damage` buildings in
   populated areas, combined with reported survivor signals (cell phone
   traffic, distress calls, ham radio).

2. **Stabilization.** Prevent the situation from worsening. Examples:
   gas leaks, unstable structures threatening rescuers, levee breaches,
   active fire spread, blocked evacuation routes. EO contributes by
   flagging structural compromise adjacent to critical hazards (fuel
   storage, electrical substations, hospitals).

3. **Critical infrastructure restoration.** Hospitals, water supply,
   electricity, telecommunications. A still-standing but non-functional
   hospital is high-priority because of its multiplier effect on
   downstream care.

4. **Property recovery.** Damage assessment for insurance, rebuilding,
   public-assistance funding. Lower urgency than life-safety.

**Geographic prioritization** within an affected area typically follows
two principles:

- **Cluster intensity.** Areas with high concentrations of severe damage
  are prioritized over areas with scattered damage of the same total
  count. Clusters suggest focused impact and likely concentrated
  survivor populations.
- **Access feasibility.** Prioritization is tempered by what is
  physically reachable. A high-severity area cut off by a destroyed
  bridge or blocked road may be served later than a moderately-damaged
  area on a working access route.

**Per-disaster-type prioritization** differs in important ways:

- **Earthquake.** The trapped-survivor window is short (~72 hours).
  Severe and catastrophic clusters are sorted on access and structure
  type — heavy reinforced-concrete failures have higher trapped-survivor
  probability than wood-frame.
- **Hurricane.** First priority after the storm is medical evacuation in
  flooded zones; second is preventing secondary harm (fire,
  electrocution, contaminated water). Wind damage is usually well
  visible from above; storm surge / flooding damage is partially
  hidden.
- **Wildfire.** Damage is mostly bimodal (intact / destroyed). Priority
  is preventing re-ignition, evacuating remaining residents, and
  identifying still-burning structures.
- **Flood.** A flooded but standing building can hide casualties or
  trapped occupants. High-water-mark observations should drive
  welfare-check priority even when buildings appear externally intact.

**Operational practice.** Responders typically compute a priority score
per geographic unit (here: per quadrant) combining severity, density of
affected buildings, and access. The score is triaged against the supply
of teams and the disaster timeline. EO-derived reports support — but do
not replace — this prioritization; field teams remain the source of
truth.
