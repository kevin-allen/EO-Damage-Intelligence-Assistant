# Building damage taxonomy

The xView2 dataset uses the Joint Damage Scale (JDS), a four-class ordinal
taxonomy for per-building damage assessment from overhead imagery. The
boundaries reflect what is observable in pre/post satellite views — interior
damage is generally not visible.

**no-damage.** The structure appears undisturbed. Roof outline intact, walls
intact, footprint unchanged between pre and post. No visible debris fields
attributable to the building. Surrounding ground may show storm or fire
effects (water, ash) without the building itself being affected.

**minor-damage.** Visible exterior damage, but the structure is fundamentally
intact. Examples: missing roof tiles or shingles, partial roof tarping,
broken windows, displaced exterior elements (gutters, antennas), debris
adjacent to the building, partial discoloration consistent with smoke or
water exposure. The footprint is still recognizable in both pre and post
imagery.

**major-damage.** Partial structural compromise. Examples: partial roof
collapse, exposed structural members, partial wall failure, a portion of
the building footprint removed in post. Major-damage buildings are often
still standing in part but no longer functional. Large debris fields
adjacent to the structure (its own materials) are characteristic.

**destroyed.** The building is no longer recognizable as a building in the
post imagery. Complete collapse, foundation-only remnants, washed away,
burned to foundation. The footprint area may be visible as a debris field
or scoured surface, but no structure remains.

A fifth category, **un-classified**, is used in the xView2 labels when the
annotator could not confidently assign one of the four classes. Our
pipeline skips un-classified buildings at the dataset, training, and
aggregation stages.

The classes are ordinal but not equidistant. The boundary between
`no-damage` and `minor-damage` is the most judgment-heavy and the most
sensitive to imagery resolution: at sub-meter GSD a missing window pane
may be visible; at 1-m GSD it is not. The boundary between `major-damage`
and `destroyed` is generally more visually obvious, as complete collapse
leaves an unambiguous signature.

Compared to FEMA's "Substantial Damage" framework (which uses a >50% of
market value threshold to declare a building substantially damaged), the
JDS provides finer gradations between intact and totally destroyed. This
finer-grained scale is appropriate for EO-based first-cut assessment, but
the binary substantial-damage decision is still made downstream by field
inspectors. The JDS classes also do not encode habitability — a
`minor-damage` building may be uninhabitable due to interior conditions
not visible from overhead.

In our reports, building footprints come from xView2 reference polygons.
The damage class is the only model-predicted attribute. The system does
not detect or localize buildings.
