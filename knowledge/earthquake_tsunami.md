# Earthquake and tsunami damage and assessment guidance

Earthquakes and tsunamis frequently co-occur in subduction-zone events
(the 2011 Tōhoku and 2018 Palu disasters are recent examples). The two
hazards produce distinct damage signatures, and a single tile may show
either or both.

**Earthquake (shaking-induced) damage.**

Shaking damage depends on three things: ground motion intensity, local
soil conditions (which can amplify motion several-fold over short
distances), and building construction type. The classifier output for
the same intensity can therefore look very different across two tiles
in the same event.

Failure modes by construction type:
- **Unreinforced masonry.** Brittle failure of mortar joints, parapet
  collapse, partial wall collapse. Common failure pattern in older
  city centers (Mexico City, central Italy). Mid-range damage classes
  predominate.
- **Soft-story buildings.** Buildings with a weak ground floor
  (parking, retail) collapse the upper floors onto the ground floor —
  pancake collapse. Highly visible from above as a sudden shortening
  of the building footprint.
- **Reinforced concrete frames.** Performance highly dependent on
  detailing. Older non-ductile frames can fail catastrophically; newer
  code-compliant frames typically remain standing with damage.
- **Light wood frame.** Generally performs well in moderate shaking due
  to ductility. Fails in extreme shaking via cripple-wall collapse,
  foundation displacement, or chimney failures.

Earthquake damage spatial patterns:
- Damage is strongly correlated with proximity to active faults and
  with local soil amplification.
- Sediment-filled basins amplify shaking; structures in basins can be
  far more damaged than those on bedrock nearby.
- The trapped-survivor window is short (~72 hours); spatial
  prioritization should weight high `destroyed` and `major-damage`
  density heavily.

**Tsunami (wave-inundation) damage.**

Tsunami damage is distinctively destructive at the shoreline and rapidly
decreases inland. The dominant failure mode is structural displacement
by wave impact and scour, with secondary debris-impact damage farther
inland from waterborne debris fields.

Tsunami damage patterns:
- **Scour and wash-out.** Near shoreline, structures may be entirely
  swept away. The remaining footprint shows scoured ground or sand
  deposits, often with no recognizable building debris.
- **Wave-impact destruction.** A clear inundation line is often visible
  in post-tsunami imagery: structures seaward are destroyed; structures
  landward are largely intact. The line can be sharp (depending on
  topography).
- **Debris fields.** Tsunami waters carry vehicles, building parts,
  vegetation, and watercraft far inland; these debris fields can cause
  major-damage hits to otherwise-protected structures.

The 2018 Palu tsunami (Sulawesi, Indonesia) is in the xView2 dataset and
illustrates classic tsunami damage geometry: dense `destroyed`-class
buildings along the bay shore, transitioning to `no-damage` over a few
hundred meters inland.

**Combined earthquake-tsunami events.**

In subduction-zone events both hazards strike the same area. From EO
imagery the two can be hard to separate without complementary data
(inundation maps, ground-motion data). The combined damage signature is
typically: heavy `destroyed` near the coast (tsunami-dominated),
shaking-induced collapses inland (earthquake-dominated), and a mixed
zone between them.

**Implications for the report:**
- Highly concentrated `destroyed` damage in a coastal tile is most
  likely tsunami-driven and indicates a sharp inundation line that
  should drive evacuation-and-rescue prioritization.
- Distributed `major-damage` across an inland tile is most likely
  shaking-driven; construction type and soil conditions determine the
  spatial pattern.
- Recommended actions should emphasize the 72-hour trapped-survivor
  window and the need for heavy urban-search-and-rescue capability for
  pancake collapses.
- Reports should explicitly note when the tile is too small or too
  uniformly destroyed to distinguish earthquake from tsunami damage
  modes.
