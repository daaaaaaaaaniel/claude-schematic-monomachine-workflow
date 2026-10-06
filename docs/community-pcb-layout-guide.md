# PCB layout guide, distilled from Sourcery Studios #pcb-creation

**Scope:** every message in #pcb-creation on the Sourcery Studios Discord from 1 January to 6 October 2026 (688 messages). This is a first pass covering the advice, links, parts and footprints people shared there. Dates are UTC. Each item links to the message it came from.

**How to use this:** sections 1–7 are layout and manufacturing practice, sections 8–10 are parts, footprints and resources, and section 11 lists open questions. Section 12 restates the practical rules as a short checklist an agent (or a tired human) can follow.

**Caveat:** this is hobbyist community advice, mostly about Eurorack modules, mostly built in KiCad (some EasyEDA) and fabricated at JLCPCB. Where people disagreed, both sides are given.

---

## 1. Before layout: schematic and footprints

- **Most first-revision errors come from a small set of mistakes:** potentiometers wired backwards, swapped op-amp inputs, reversed diodes, and footprints with holes slightly too small. Check those specifically, even if you skim everything else. (kalj and [deetun, 2026-07-03](https://discord.com/channels/770322244584210432/795378569836232726/1522630930165137469))
- **Breadboard the circuit after drawing the schematic** and before laying out the board. ([deetun, 2026-07-03](https://discord.com/channels/770322244584210432/795378569836232726/1522630930165137469))
- **Pots and switches deserve double and triple checks.** Look at the part from the front panel side and work out which way it turns. Someone built a 4-gang pot footprint, triple-checked it against the real part, and the knob still worked backwards. Another builder had to flip a horizontal dual-gang pot to the other side of the board. ([freed_j, 2026-01-11](https://discord.com/channels/770322244584210432/795378569836232726/1459714118033346734); tkilla64, 2026-01-11)
- **Make your own footprints from the datasheet.** Take the pad, hole and courtyard dimensions from the datasheet. David Haillant considers this the only way to trust a footprint, and suggests checking it against a 3D model. ([David Haillant, 2026-05-12](https://discord.com/channels/770322244584210432/795378569836232726/1503682385072361482))
- **Hole sizes are where footprints fail most.** Examples from the channel: a 0.95 mm hole for a 0.99 mm pin, pot side tabs that wouldn't fit, and SK6812MINI-E LED holes a few microns too small. Check the hole diameter against the lead size in the datasheet, and also check the mounting tabs, not just the electrical pins. (The2dCour, mightywombat, 2026-04-04/05; [Sourcery, 2026-02-21](https://discord.com/channels/770322244584210432/795378569836232726/1474683367294238853))
- **Use oval (slotted) holes for switches.** They fit both the PC-mount and the solder-lug versions of a part. ([deetun, 2026-05-12](https://discord.com/channels/770322244584210432/795378569836232726/1503701568422416404))
- **Watch the annular ring.** A footprint that AI generated had a pad ring that was too thin. (trevortjes, 2026-05-12)
- **Check pin assignments when you make a custom symbol and footprint pair.** A homemade vactrol footprint had its pins mixed up. (mightywombat, 2026-01-25)
- **Keep a personal library of preferred parts.** KiCad has no favourites feature and ships thousands of resistor footprints when you'll use about five. People keep a go-to library ([trevortjes, 2026-03-17](https://discord.com/channels/770322244584210432/795378569836232726/1483509362323488950)), or a "default schematic" with every part they've used, already paired with the right footprint, and copy parts from it into new designs ([Jos Bouten, 2026-02-06](https://discord.com/channels/770322244584210432/795378569836232726/1469392219562578132)).
- **Multi-board power nets:** if you use plain +5V and GND symbols on both boards, the PCB editor will try to route a trace between them. Give the second board its own nets (e.g. C_GND, C_+5V) that meet at the connector. Keep the real net names visible, because hiding them invites mistakes. ([David Haillant, 2026-01-02](https://discord.com/channels/770322244584210432/795378569836232726/1456524546944270489); SyntheticFeO suggested hidden labels, David disagreed.)
- **ERC power warnings:** add a PWR_FLAG to nets you know are powered, or change the type of the pin that supplies them. ([David Haillant, 2026-01-02](https://discord.com/channels/770322244584210432/795378569836232726/1456662854588432416))
- **Choose the right op amp for the supply.** The TL072 is a dual-supply part. For a single supply use something like the LM358 (same dual op-amp pinout). ([Luther, 2026-01-31](https://discord.com/channels/770322244584210432/795378569836232726/1467229540630925580))
- **Unused op-amp sections:** Locrius confirmed Ninja Hagen's proposed dual-supply termination (posted as an image), but twig warned not to reuse it blindly: follow the datasheet for your exact part, and see TI's app note (section 10). Leaving pads for 0 Ω and unpopulated resistors lets you press the spare section into use later. ([David Haillant, 2026-05-12](https://discord.com/channels/770322244584210432/795378569836232726/1503743345682419815); [twig, 2026-05-12](https://discord.com/channels/770322244584210432/795378569836232726/1503753972391870714); [Jos Bouten, 2026-05-14](https://discord.com/channels/770322244584210432/795378569836232726/1504424628859179098))
- **On V1, design for debugging.** Add test points and places to cut traces and add bodges, and compact the board in V2. ([freed_j, 2026-01-11](https://discord.com/channels/770322244584210432/795378569836232726/1459714118033346734)) A more radical version: leave any connection you're unsure of unconnected and wire it by hand, then order a clean board once it works. Shipping costs make this pricier than it used to be. ([Sourcery, 2026-07-04](https://discord.com/channels/770322244584210432/795378569836232726/1522857658175197184))

## 2. Placement

- **Work in blocks.** Group parts that belong together, route each group, then move the routed blocks around to find the best arrangement. ([The2dCour, 2026-03-16](https://discord.com/channels/770322244584210432/795378569836232726/1483198651265188000))
- **Lay out from input to output** in a single line where you can. Feedback paths are what turn layouts into spaghetti. ([trevortjes, 2026-03-16](https://discord.com/channels/770322244584210432/795378569836232726/1483231776510836921))
- **Place parts so nets stay short.** In one review, a single resistor's position dragged a net across the entire underside of the board. ([The2dCour, 2026-01-29](https://discord.com/channels/770322244584210432/795378569836232726/1466547520166690942))
- **Put decoupling caps right at the IC power pins.** 100 nF bypass caps should sit as close to the power pins as you can get them. ([Luther, 2026-01-30](https://discord.com/channels/770322244584210432/795378569836232726/1466693880849104919)) twig's pre-fab checklist also includes "does every IC have a capacitor next to its power rails?" ([twig, 2026-07-03](https://discord.com/channels/770322244584210432/795378569836232726/1522632852511002695))
- **Respect courtyards.** JLC flagged parts placed too tight. ([Locrius, 2026-04-21](https://discord.com/channels/770322244584210432/795378569836232726/1496095859060903968))
- **Transistor footprints:** a triangular (tripod) pad arrangement helps avoid solder bridges at no extra space ([Brendahoward63, 2026-03-17](https://discord.com/channels/770322244584210432/795378569836232726/1483436951725015134)). SANDELINΩS prefers inline pads with wider spacing.
- **Horizontal resistor footprints** make crossings easier to deal with on dense through-hole boards. ([Locrius, 2026-03-17](https://discord.com/channels/770322244584210432/795378569836232726/1483362673310695496))
- **Plan for module depth.** The power header is usually the deepest part of a module. Put it on the lower board, or use angled headers in sandwich builds ([Ed Random, 2026-03-04](https://discord.com/channels/770322244584210432/795378569836232726/1478833566593974393)). The counterpoint is not to sacrifice repairability or ease of assembly to fit very shallow skiffs ([SANDELINΩS, 2026-03-04](https://discord.com/channels/770322244584210432/795378569836232726/1478727917608370316)).
- **Panel rigidity:** spread jacks and RK09 pots so the front panel is held to the PCB at both top and bottom. ([tkilla64, 2026-06-18](https://discord.com/channels/770322244584210432/795378569836232726/1517082629231345746))

## 3. Routing

- **One layer mostly vertical, the other mostly horizontal.** This is the classic way to untangle crossings ([Luther, 2026-01-24](https://discord.com/channels/770322244584210432/795378569836232726/1464628218857525382)), and it worked for mightywombat after several placement attempts ([mightywombat, 2026-03-17](https://discord.com/channels/770322244584210432/795378569836232726/1483269600396181585)). It breaks down when the bottom layer is crowded.
- **Avoid tracks that "kiss" pads or other nets.** Route around components rather than squeezing between pads, and use free space where it exists. ([The2dCour, 2026-01-29](https://discord.com/channels/770322244584210432/795378569836232726/1466547520166690942))
- **Space tracks evenly** from each other and from pads. ([SyntheticFeO, 2026-01-30](https://discord.com/channels/770322244584210432/795378569836232726/1466796540377956365))
- **Running Vref under the board with vias is fine** as long as it stays away from high currents and fast digital signals. ([Locrius, 2026-01-12](https://discord.com/channels/770322244584210432/795378569836232726/1460373410101198930))
- **On multi-board designs, keep clocks local.** The2dCour duplicated signals on several header pins so the clock and signals derived from it don't have to wander across the second board. ([The2dCour, 2026-02-28](https://discord.com/channels/770322244584210432/795378569836232726/1477298842750816306))
- **Track widths** (community defaults, not hard rules):

| Use | Width | Who |
|---|---|---|
| Signal | 0.3 mm minimum. KiCad's 0.2 mm default looks fragile for hobby boards. | [Jos Bouten](https://discord.com/channels/770322244584210432/795378569836232726/1466581064633028630) |
| Power, normal analog module | 0.4–0.5 mm, or a power plane if there's a power-hungry processor | [Locrius](https://discord.com/channels/770322244584210432/795378569836232726/1485335047786598592) |
| Power, LEDs, drivers or 555s | 0.6 mm, and don't go below 0.4 without a reason | [The2dCour](https://discord.com/channels/770322244584210432/795378569836232726/1485339441928208444) |
| Power between connectors and through-hole parts | 1 mm, narrowing to 0.5 mm at SMD pads | [tkilla64](https://discord.com/channels/770322244584210432/795378569836232726/1485348617404420309) |
| Professional signal floor, for reference | 0.11 mm (4.5 mil) | trevortjes |

- **KiCad netclass widths not sticking?** A new track that continues from an existing, narrower track inherits that track's width. Start a fresh track instead. ([Locrius, 2026-03-22](https://discord.com/channels/770322244584210432/795378569836232726/1485327541785854043))
- **Thermal reliefs:** KiCad doesn't let you set the number of spokes. The workaround is to set the pad's zone connection to none and draw the spokes yourself ([trevortjes, 2026-03-23](https://discord.com/channels/770322244584210432/795378569836232726/1485663595822973072)). For reflowed small passives, keep the copper on both pads balanced to avoid tombstoning; Locrius's old DFM rule was a ratio below 2:1 ([Locrius, 2026-03-23](https://discord.com/channels/770322244584210432/795378569836232726/1485698535935578314)).

## 4. Ground, pours and vias

- **Ground fill on both layers, stitched with vias,** is the common recommendation, though not mandatory. ([tkilla64, 2026-01-30](https://discord.com/channels/770322244584210432/795378569836232726/1466789838408782008))
- **Don't overdo stitching vias.** Add more only for a reason: heat, tying two planes together, sometimes RF. ([The2dCour, 2026-02-05](https://discord.com/channels/770322244584210432/795378569836232726/1468830854439506025))
- **Enable "remove islands"** in the zone settings. Not every area needs to be ground. Watch for GND pads that end up stranded on isolated islands; reroute or add a via to fix them. ([Locrius, 2026-02-06](https://discord.com/channels/770322244584210432/795378569836232726/1469232377514426459))
- **Put more GND pins on board-to-board connectors,** especially next to analog signals, to avoid large current loops. ([David Haillant, 2026-01-02](https://discord.com/channels/770322244584210432/795378569836232726/1456524957738733702))
- **Refill zones (press B) before exporting gerbers.** Running DRC also offers to refill them. One caution: after panelizing with KiKit, pressing B wrecked the ground plane because the pours overlapped. (Luther, 2026-01-23; [David Haillant, 2026-07-03](https://discord.com/channels/770322244584210432/795378569836232726/1522635790125891685); kalj, 2026-07-03)

## 5. Multi-channel, multi-board and sub-boards

- **For dual or quad modules, plan multi-channel from the start.** You can't truly mirror a layout, because footprints aren't symmetrical; mirroring flips the tracks but not the parts. Use KiCad's duplicate / multi-channel layout ([Locrius, 2026-09-23](https://discord.com/channels/770322244584210432/795378569836232726/1552363227482947715)) together with hierarchical sheets in the schematic ([David Haillant, 2026-09-24](https://discord.com/channels/770322244584210432/795378569836232726/1552731340687016000)). Knobhead had AI place and route the second half; it looked good but needed double and triple checking.
- **Avoid sub-boards** unless the sub-board is reused across designs, or it cuts the number of traces by much more than the connector pins it adds. ([Luther, 2026-03-01](https://discord.com/channels/770322244584210432/795378569836232726/1477539902114762762))
- **A common split:** one board holds all the I/O (jacks, pots, switches) and the processing board piggybacks on it through headers. (Jos Bouten, 2026-06-05)

## 6. Front panels as PCBs

- **Thickness:** 1.6 mm is the standard choice (2 mm costs more). It flexes a bit but is rigid once jacks, pots and switches tie it to the board behind. Avoid large cutouts and thin walls. ([David Haillant, 2026-06-18](https://discord.com/channels/770322244584210432/795378569836232726/1517073024661061672); Sourcery)
- **Workflow A:** draw the panel in Front Panel Express, export DXF, and import it into the KiCad footprint editor. Mounting holes are a separate one-PTH footprint placed at FPE's XY coordinates. ([David Haillant, 2026-10-03](https://discord.com/channels/770322244584210432/795378569836232726/1555986156796252293); [David Haillant, 2026-10-03](https://discord.com/channels/770322244584210432/795378569836232726/1555986802723000463))
- **Workflow B:** MeeBilt's front panel video (section 10). The crossed diagonal background is a KiCad copper pour set to a hatched fill instead of solid. ([tkilla64, 2026-10-03](https://discord.com/channels/770322244584210432/795378569836232726/1555989899776098404); [tkilla64, 2026-10-03](https://discord.com/channels/770322244584210432/795378569836232726/1555990505681195090))
- **Square non-plated holes (e.g. for slider pots):** draw the square on the Edge.Cuts (outline) layer. JLC also does oval holes; check whether your fab accepts non-round holes and at what cost. ([tkilla64, 2026-04-09](https://discord.com/channels/770322244584210432/795378569836232726/1491819476407287858); trevortjes)
- **Template generator:** clacktronics' automatic KiCad PCB and panel template generator (section 10). ([Stibbons, 2026-09-10](https://discord.com/channels/770322244584210432/795378569836232726/1547675757021495336))

## 7. Fabrication and assembly constraints (mostly JLCPCB)

- **Minimum size:** boards with a side under 15 mm trigger a ~$15 surcharge when panelized (V-cut handling), whether you panelize or JLC does. Single, unpanelized boards should be at least ~10 mm wide; 9.6 mm boards about 111 mm long went through. kalj widened a board from 13.97 to 15.1 mm and the surcharge disappeared. Locrius had a 9.7 × 110 mm board refused for SMT assembly. ([kalj, 2026-02-22](https://discord.com/channels/770322244584210432/795378569836232726/1475211687660490862); [Locrius, 2026-02-21](https://discord.com/channels/770322244584210432/795378569836232726/1474713097301262447); [Ed Random, 2026-02-21](https://discord.com/channels/770322244584210432/795378569836232726/1474750268997505036))
- **Quantities:** JLC's order form now allows multiples of 5 only up to 30, then 50, 75 and 100. To get odd quantities, panelize (e.g. 10 per panel). V-scored panels constrain board dimensions and component positions near the edges, leave rougher edges, and cost more. ([David Haillant, 2026-09-01](https://discord.com/channels/770322244584210432/795378569836232726/1544305519773224991); deetun)
- **Stencils:**
  - With no paste layer, JLC doesn't open apertures for through-hole pads, which is what you want for a stencil that only covers the SMD parts. ([Knobhead, 2026-04-14](https://discord.com/channels/770322244584210432/795378569836232726/1493704735058952345))
  - Through-hole parts that are soldered like SMD parts (e.g. SMT spacers) do need paste-layer apertures. ([Locrius, 2026-04-14](https://discord.com/channels/770322244584210432/795378569836232726/1493714243336536196))
  - Order a custom stencil size; it costs the same as the standard 380 × 280 mm. Leave enough margin to tape it down. ([tkilla64, 2026-06-03](https://discord.com/channels/770322244584210432/795378569836232726/1511710173939634339))
  - Put several copies of a board, or several designs, on one stencil. ([twig, 2026-06-03](https://discord.com/channels/770322244584210432/795378569836232726/1511683149581778964))
  - Hold the board in a jig made of spare PCBs of the same thickness taped to the bench, which gives a flat surface level with the board. ([tkilla64, 2026-06-08](https://discord.com/channels/770322244584210432/795378569836232726/1513639066715816016))
  - Apply the paste in one pass, and cut oversized stencils down. ([trevortjes, 2026-06-08](https://discord.com/channels/770322244584210432/795378569836232726/1513625666476708023))
- **Solder mask colour:** JLC's black varies from batch to batch and sometimes comes out greyish. (nuriamarti, Ed Random, Locrius, 2026-02-27)
- **PCBWay assembly** has no stock catalogue: they buy whatever parts you specify, and you exchange a BOM spreadsheet until it's agreed. Specify exact manufacturer part numbers (Mouser-style). It's more hands-on and costs more than JLC. ([twig, 2026-08-05](https://discord.com/channels/770322244584210432/795378569836232726/1534591691661770833); Locrius)
- **Fixing holes that are too small:** enlarge them with CNC drill bits in a pin vise if the pads are big enough ([SyntheticFeO, 2026-04-08](https://discord.com/channels/770322244584210432/795378569836232726/1491500529057005568)), or trim and file the part's tabs instead.
- **DIY alternatives:**
  - 3D-printed "PCB Forge" boards were tried and judged not worth it. The plastic melts while soldering, the parts are hard to sand flat, and the result was more work than protoboard. ([SANDELINΩS, 2026-08-05](https://discord.com/channels/770322244584210432/795378569836232726/1534665329819521134); [SANDELINΩS, 2026-02-28](https://discord.com/channels/770322244584210432/795378569836232726/1477274430655959161))
  - SyntheticFeO's home-etched single-sided boards use Bungard copper rivets as plated through-holes and vias: 1 mm inner-diameter rivets in 1.5 mm holes, with headers soldered directly to the rivets. ([SyntheticFeO, 2026-06-05](https://discord.com/channels/770322244584210432/795378569836232726/1512489648817967186))
- **Shipping and EU duties** came up a lot (DDP option, keeping orders under about $60–70, Global Direct Line, FedEx charging VAT). These change often, so check them when you order.

---

## 8. Components recommended

There were few explicit catalog recommendations in this period, and **no Tayda or Mouser part numbers were posted**. These are the parts that came up with enough detail to act on:

| Part | Catalog / number | Recommended for | Notes | Source |
|---|---|---|---|---|
| SK6812MINI-E addressable RGB LED (OPSCO) | JLCPCB / LCSC **C5149201** — https://jlcpcb.com/partdetail/OPSCOOptoelectronics-SK6812MINIE/C5149201 | Panel LEDs | Needs a microcontroller. Easy to solder, but one builder's footprint holes were slightly too small and needed filing. | [twig, 2026-02-21](https://discord.com/channels/770322244584210432/795378569836232726/1474569626724728853); [Sourcery](https://discord.com/channels/770322244584210432/795378569836232726/1474683367294238853) |
| USB-C receptacle, SHOU HAN TYPE-C 16PIN 2MD(073) | JLCPCB / LCSC **C2765186** — https://jlcpcb.com/partdetail/SHOUHAN-TYPE_C_16PIN_2MD_073/C2765186 | USB-C power input | Answer to a request for a USB-C connector stocked at JLC; the requester only needed PD. | [tkilla64, 2026-06-16](https://discord.com/channels/770322244584210432/795378569836232726/1516503499092000888) |
| Sunled XZMDKCBDDG45S-9 LED | DigiKey — https://www.digikey.nl/en/products/detail/sunled/XZMDKCBDDG45S-9/4902045 | Flush panel LEDs | Posted in a thread about reverse-mount LEDs on flush panels | [Luther, 2026-02-18](https://discord.com/channels/770322244584210432/795378569836232726/1473737168685109310) |
| Thonk MOSS-101 | Thonk — https://www.thonk.co.uk/shop/moss-101/ | Low-profile, flush buttons | Posted in answer to how commercial synths get buttons flush with no visible holes; replies said they're SMD | [Luther, 2026-02-18](https://discord.com/channels/770322244584210432/795378569836232726/1473732836686299389) |
| Dailywell DWB3 mini toggle, DPDT ON-ON | Thonk — https://www.thonk.co.uk/shop/mini-toggle-switches/ | Panel toggle switch | David Haillant shared a KiCad footprint (section 9) | pennache / [David Haillant, 2026-05-12](https://discord.com/channels/770322244584210432/795378569836232726/1503683176105513010) |
| LM358 | generic | Single-supply op amp | Use instead of the dual-supply TL072 on single-supply circuits | [Luther, 2026-01-31](https://discord.com/channels/770322244584210432/795378569836232726/1467229540630925580) |
| RK09 pots | generic | Panel pots | Spread them out to anchor the panel at top and bottom | [tkilla64, 2026-06-18](https://discord.com/channels/770322244584210432/795378569836232726/1517082629231345746) |
| Bungard "Favorit" via rivets | ELMI — https://www.elmisrl.it/product/rivetti-bungard-favorit/ | Through-holes on home-etched boards | 1 mm ID in a 1.5 mm hole | [SyntheticFeO, 2026-06-05](https://discord.com/channels/770322244584210432/795378569836232726/1512489648817967186) |

## 9. KiCad footprints, symbols and libraries

- **DPDT mini toggle (4.7/4.8 mm pin pitch):** `SW-TOGGLE-DPDT-P4.7-4.8.kicad_mod` by David Haillant. It's drawn for the solder-lug variant but should fit PC-mount pins. It was posted as a Discord attachment and those links expire, so save it from the original message: [message link](https://discord.com/channels/770322244584210432/795378569836232726/1503683176105513010). David also keeps footprints on his GitHub (mentioned in the thread but not linked).
- **CERN KiCad libraries:** CERN's full component library for KiCad. https://gitlab.com/ohwr/cern-kicad-libs ([Harm0, 2026-05-12](https://discord.com/channels/770322244584210432/795378569836232726/1503878918426595378))
- **Eurorack panel and PCB template generator (KiCad):** https://clacktronics.co.uk/content/applications/eurorack-panel.html ([Stibbons, 2026-09-10](https://discord.com/channels/770322244584210432/795378569836232726/1547675757021495336))
- **Example projects with KiCad files or gerbers:**
  - RackRat, SANDELINΩS's Eurorack Proco Rat, with KiCad board files: https://codeberg.org/Sandelinos/RackRat
  - SANDELINΩS's VCO, viewable in the browser: https://kicanvas.org/?repo=https%3A%2F%2Fcodeberg.org%2FSandelinos%2FVCO%2Fsrc%2Fbranch%2Fmain
  - TOILmodular dual RAT, with gerbers; use the "thonk" version per its README: https://github.com/TOILmodular/RAT
  - The2dCour's Stereo Multiplexer (not production ready): https://github.com/the2dcour/Stereo-Multiplexer/
  - twig's Cyclic module, with notes on the PCBWay sponsorship: https://www.divergentwaves.co.uk/module/cyclic/
- **Shared EasyEDA designs:** the Modular Synth Builders team on OSHWLab. https://oshwlab.com/Modular-synth-builders/works ([Ed Random, 2026-03-10](https://discord.com/channels/770322244584210432/795378569836232726/1480798649708576840))

## 10. Learning resources and tools

| Resource | What it is | Shared by |
|---|---|---|
| MeeBilt, *Eurorack DIY: 909 Rimshot (Episode 6) – The Frontpanel* — https://www.youtube.com/watch?v=C2qw4Dp-MPQ | Making a Eurorack front panel as a PCB in KiCad | [tkilla64, 2026-10-03](https://discord.com/channels/770322244584210432/795378569836232726/1555989899776098404) |
| tkilla64's YouTube (RP2040 project, 909 Toms) | Stencil and fixture technique shown in the build videos (not linked) | [tkilla64, 2026-06-08](https://discord.com/channels/770322244584210432/795378569836232726/1513639066715816016) |
| TI app brief SBOA204A — https://www.ti.com/lit/ab/sboa204a/sboa204a.pdf | Terminating unused op amps correctly | [Jos Bouten, 2026-05-14](https://discord.com/channels/770322244584210432/795378569836232726/1504424628859179098) |
| KiCanvas — https://github.com/theacodes/kicanvas (fork: https://github.com/Huaqiu-Electronics/ecad-viewer) | View KiCad projects in the browser, now including Codeberg repos. Useful for sharing boards for review. | [kalj, 2026-03-08](https://discord.com/channels/770322244584210432/795378569836232726/1480096629313765416); [SANDELINΩS](https://discord.com/channels/770322244584210432/795378569836232726/1480113222022332478) |
| KiKit (not linked) | KiCad panelization tool | kalj, 2026-02-21 |
| Front Panel Express (not linked) | Panel drawing tool, exported to DXF for KiCad | David Haillant, 2026-10-03 |
| JohnyJohansen, *PCB Via Rivets* — https://youtu.be/CvO5JaOkEXI | Rivets as plated through-holes and vias on DIY boards | [SyntheticFeO, 2026-06-05](https://discord.com/channels/770322244584210432/795378569836232726/1512499607060480174) |
| QZW Labs, *3D Print Your Own PCB* — https://www.youtube.com/watch?v=PLliKgzKKUI | 3D-printed PCB method (cutting rather than sanding) | Locrius, 2026-02-28 |
| Ali Khalil, *DIY PCB on a 3018 PRO CNC* — https://www.youtube.com/watch?v=SBm8JZHsEAg | CNC-milled single-sided boards | Locrius, 2026-02-28 |
| PCB Forge — https://castpixel.itch.io/pcb-forge | 3D-printed PCB molds plus copper tape. **Tested and judged not worth it** (see section 7). | SANDELINΩS, 2026-02-27 |
| EasyEDA Pro | Praised for footprint management, reuse blocks and 3D case view; lacks built-in SPICE | The2dCour, 2026-03-10 |

## 11. Open questions in the channel

- **Thonkiconn footprint with a bent ground pin** (as on ST Modular PCBs): asked on 2026-10-05, no answer yet. ([daniel, 2026-10-05](https://discord.com/channels/770322244584210432/795378569836232726/1556774483916754945))
- **Is there a shipping-cost penalty for putting many designs in one JLC order, and at what point is it cheaper to split?** No answer. (Jos Bouten, 2026-09-11)
- **A shared master checklist for PCB design** was proposed but never compiled. Section 12 is a start. ([trevortjes, 2026-07-03](https://discord.com/channels/770322244584210432/795378569836232726/1522641077280964609); [Jos Bouten, 2026-07-03](https://discord.com/channels/770322244584210432/795378569836232726/1522671665538924577))

---

## 12. Checklist (for humans and agents)

Jos Bouten keeps a rules list built from his past mistakes (e.g. "add mounting holes", "route power to every sub-board"), and twig kept one too, while admitting to rarely following it. Both agreed the most effective check is **another person reviewing the schematic and PCB**, though even a five-person review at Locrius's job missed an IC with no ground. This list combines the channel's advice:

**Schematic**
1. Breadboard or simulate the circuit before layout.
2. Check every op amp's supply type (single vs dual) and its input polarity.
3. Check diode orientation, especially reverse-protection diodes.
4. Terminate unused op-amp sections per the datasheet, or leave pads (0 Ω / DNP) to use them.
5. Use separate nets for secondary-board power that meet at the connector, and keep net names visible.

**Footprints**
6. Build every new footprint from the datasheet: pads, hole diameters, mounting tabs, courtyard.
7. Check pin numbering between symbol and footprint.
8. For pots and switches, confirm rotation direction and which pins are which, as seen from the panel.
9. Use oval holes where a part comes in PC-mount and solder-lug variants.

**Placement**
10. Group functional blocks, route them, then arrange the blocks; flow from input to output.
11. Place 100 nF decoupling at every IC power pin.
12. Respect courtyards.
13. Spread jacks and pots to anchor the panel at top and bottom.
14. Keep the power header low or angled to save depth.

**Routing**
15. Signals ≥0.3 mm, power 0.4–0.6 mm (1 mm between connectors and through-hole parts).
16. Use one layer mainly horizontal and the other mainly vertical.
17. Keep clean clearances and even spacing, with no tracks squeezed past pads.
18. Keep Vref and analog lines away from high current and fast digital; keep clocks local.

**Ground**
19. GND pour on both layers with "remove islands" on.
20. Use stitching vias where they're needed, not everywhere.
21. Make sure no GND pad sits on an isolated island.
22. Put plenty of GND pins on board-to-board connectors.

**Manufacturing**
23. Board sides ≥15 mm if it will be panelized (≥10 mm single).
24. Panelize for odd quantities.
25. Square holes go on Edge.Cuts.
26. Front panels 1.6 mm, avoiding thin walls.
27. Include a paste layer only where you want stencil apertures.

**Before export**
28. Refill zones (B), but not on a KiKit-panelized board.
29. DRC with 0 errors and 0 warnings.
30. Check the 3D view of both sides.
31. Get someone else to review it.
32. Treat V1 as a prototype: add test points and room for bodges.
