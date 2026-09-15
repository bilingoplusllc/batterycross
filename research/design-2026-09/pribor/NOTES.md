# GAUGE

**The direction in one word: GAUGE.** The page is the face of a panel meter.
Dark is the instrument's resting state, declared in `:root`; `prefers-color-scheme: light`
is the only override. Every quantity is shown as a **position against a graduated scale**,
and the scale — a ruled line with ticks — is the load-bearing element of the composition:
it is the section divider, the bottom edge of the masthead, the dimension line under a
silhouette, and the voltage axis itself.

## What the decisions are derived from

**One derivation: everything on the page is ruled in millimeters, the same unit the
specimens are measured in.** The 4 px spacing unit is the tick pitch; the type sizes
(11 / 13 / 16 / 19 / 21 / 27 / clamp) step on it; the drawings are literally drawn in
millimeter coordinates (`viewBox="0 0 26 8"` = 26 mm × 8 mm), so a rectangle's width
attribute *is* the diameter from the record. Nothing is drawn by hand, so no drawing can
flatter a cell that does not fit.

**Two type voices, both from the OS.** Mono carries every measured quantity, designation
and legend — including all headings, which is the inversion that keeps this away from the
three taken looks. System sans carries prose only. No serif anywhere. The instrument
character comes from tabular figures, tracked uppercase legends, hairlines and drawing
weights, so nothing collapses if a font stack resolves differently.

**Scale honesty rule (this is why the drawings survive 320→1920).** An SVG that carries
text is fixed in pixels and may only scale *up* at a breakpoint, never down. An SVG that
must be fluid carries no text at all — its labels are HTML in a sibling grid cell. Every
comparison therefore happens inside one shared frame: all six tray rows use the same
`viewBox` and the same column width, so one scale is guaranteed at every viewport, and a
millimeter rule sits in the same column as the last row.

**The family envelope is one shape, repeated.** A dashed 11.6 × 5.4 mm box is drawn in
*every* row. LR44 and SR44 fill it exactly. LR43 and SR43 leave a red void band 1.2 mm
tall inside it. CR2032 bursts 8.4 mm past its right edge and sits 2.2 mm below its top.
The family reads as a family and the outsider reads as an outsider without a word.

**Voltage is a position, never a figure in a cell.** Four indices on a 1.20–3.20 V scale at
156 px/V, with the 1.45–1.60 V interchange window shaded. Colour is a function of the
relation to that window, not of the chemistry: blue inside, amber below (it fits and the
device reads wrong), red above (wrong class). Every table row and every card carries the
same needle at 78 px/V. The two channels are orthogonal and never encode the same thing.

**Discontinued is a state of the drawing.** Live = solid bright metal, continuous outline.
Out of production = hollow, dashed outline, one diagonal slash, struck designation, hollow
index wedge, and a route line to what to buy instead. Never a gray plate with a word on it.

## What I deliberately did not do

- **No serif, no Georgia headings, no cream, no navy, no green.** Green is banned twice
  over; I stayed in graphite/azure/amber/red so nothing rhymes with MileageCurve, FedPay
  or KeepsUntil.
- **No box-shadows at all**, inner ones included (MileageCurve owns inset shadows). Depth
  is value steps and hairlines. Radii are 0; the panels are chamfered by `clip-path`
  instead, which is a different corner language from "radii 0–3 px".
- **No absolute positioning anywhere** — not for decor, not for the needles. Data positions
  live in SVG coordinate space, which is not CSS positioning. Verified: zero
  `position:absolute` in either file.
- **No graph-paper backdrop.** A graticule at a readable contrast is loud and at a quiet
  contrast is a rule-7 violation waiting to happen. Ticks differ by *length*, never by fade.
- **No window band in the small readout chips.** 0.15 V is 23 px on the big rail and 11 px
  in a chip — at chip size it was decoration pretending to be information, so I removed it
  and let colour carry the verdict there. The chip does not pretend to resolve 0.05 V; the
  rail does.
- **No scripts, no font files, no `@import`, no `url()`, no image `src`.** Zero external
  requests by construction, not by luck.
- **No hidden ad slot twins.** One node per slot; its declared size is swapped by a custom
  property in a media query, and the caption states that an unfilled slot is omitted from
  the HTML rather than hidden — `display:none` still counts as a child.

## Verified in the browser, not in the build

Driven at 320 / 375 / 768 / 1024 / 1280 / 1920 in both colour schemes, both pages:
`scrollWidth === innerWidth` at every width, and no element escapes its `overflow-x:auto`
container. Contrast audited on *computed* colours: **zero text failures** in either theme;
every drawn line, outline, tick and index is ≥ 3:1.

Four real defects were found this way and fixed: a CSS escape that swallowed its own
terminator and printed the slot size as "336 ×280"; the interchange window shipped at
**1.22:1** — the exact invisible-band failure the brief names; the baseline that every
height comparison is read against at 1.77:1; and light-theme `--ink-3` passing on the panel
but failing at **4.36:1** on the masthead and the whole footer.

**One knowingly accepted item.** Two interior tints — the window band and the missing-1.2 mm
void — sit at ~1.9–2.2:1. Both are enclosed by outlines at 7.9:1 and 6.9:1, so the objects
are delimited well above 3:1; raising the fills to 3:1 would turn context into a solid block
that outshouts the needle it exists to frame. The boundary carries the contrast, the fill
carries the tint. Flagging it rather than hiding it.
