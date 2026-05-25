# Urban infrastructure risk and cascading effects

Damage to the built environment is rarely confined to the directly affected
buildings. Urban infrastructure is highly interconnected, and the loss of
one node can degrade or disable many others. Reports should distinguish
between damage to *buildings* (the per-building output of the classifier)
and damage to *systems* (which is inferred from where the damage lands).

**Critical infrastructure classes**, in rough order of urgency for
restoration:

- **Healthcare.** Hospitals, urgent-care centers, dialysis clinics. A
  still-standing but inoperative hospital is one of the highest-priority
  restoration targets after a disaster because of its multiplier effect on
  downstream survival.
- **Water and wastewater.** Treatment plants, pump stations, and
  distribution lines. Loss of pressure causes contamination ingress; loss
  of wastewater treatment causes public-health emergencies within days.
- **Electrical power.** Substations, transmission corridors, and
  generation facilities. Loss of power cascades into water, communications,
  fuel pumping, and medical care.
- **Telecommunications.** Cell towers, fiber routes, central offices.
  Loss of communications hampers all subsequent response.
- **Transportation.** Bridges, overpasses, ports, airports, rail hubs,
  arterial roads. Determines what is *reachable* and at what cost.
- **Fuel and gas.** Refineries, pipelines, fuel depots, retail stations.
  Both a hazard (fire, explosion) and a constraint on response logistics.
- **Public safety.** Fire stations, police stations, emergency operations
  centers. Damage here is doubly costly: response capacity is reduced
  exactly when it is most needed.
- **Schools and community shelters.** Critical for evacuation, mass care,
  and post-event sheltering.

**Cascading effects.** Loss propagates along functional dependencies:

- Power loss → water-pressure loss → contamination ingress → public-health
  load on healthcare → demand for transportation to functioning hospitals.
- Bridge loss → access cut to an otherwise-intact neighborhood →
  delayed response → secondary mortality.
- Cell tower loss → loss of 911 → underreported survivor signals →
  systematic underestimate of need in that area.

These chains have to be inferred — the classifier sees buildings, not
functions. Reports should be careful to flag *where* damage falls (e.g.,
"severe damage in a quadrant containing the regional hospital") rather
than claim a specific cascade is in progress.

**Spatial co-location of lifelines.** Power, telecom, water, and major
transportation routes often share rights-of-way. A flood, wildfire, or
storm-surge that affects one corridor often affects several. This is why
moderate damage along a single lifeline corridor can have outsized
operational impact, while severe damage scattered across a residential
neighborhood may have less.

**Implication for the report.** When the priority-zones table identifies
a high-severity quadrant, the recommended-actions section should note
whether the area is plausibly co-located with lifeline infrastructure
(based on general urban form: city centers, riverfronts, port areas),
and recommend confirmation rather than asserting infrastructure damage
the model cannot directly see.
