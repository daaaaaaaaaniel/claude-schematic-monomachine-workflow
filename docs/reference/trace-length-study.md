# Routed trace length by net type, THT vs SMD boards

From the other session's measurement (relayed by d, 2026-10-07) of the same 53 open-source Eurorack boards as
`pcb-layout-study/`: 2,277 routed nets, 1,511 on mostly-THT boards and 766 on mostly-SMD boards.
"Per conn" = net trace length ÷ (pins − 1). "Whole net" = median / longest 10%. All in mm. Copper pours aren't counted.

| Net type | THT per conn | THT whole net | SMD per conn | SMD whole net |
|---|---|---|---|---|
| Op-amp + input | 24.2 | 33.9 / 67.7 | 13.9 | 17.5 / 37.7 |
| Pin of another IC (MCU/DAC/etc) | 22.7 | 25.7 / 77.9 | 6.6 | 10.8 / 52.8 |
| Board-to-board header | 19.9 | 25.2 / 54.6 | 11.7 | 17.4 / 49.3 |
| Pot | 19.5 | 23.1 / 52.9 | 8.8 | 8.8 / 23.8 |
| Jack | 15.4 | 19.1 / 69.4 | 21.8 | 21.8 / 74.9 |
| Supply | 15.1 | 84.2 / 193.3 | 12.7 | 111.5 / 227.9 |
| Op-amp output | 13.6 | 31.2 / 61.5 | 7.5 | 17.0 / 71.9 |
| Op-amp − input | 11.7 | 31.5 / 55.0 | 5.9 | 16.7 / 24.1 |
| LED | 8.7 | 8.8 / 27.0 | 10.0 | 10.0 / 72.1 |
| Between passives only | 6.8 | 12.1 / 41.2 | 5.7 | 6.6 / 64.6 |
| Ground | 6.8 | 138.0 / 339.0 | 1.8 | 59.7 / 214.3 |

Takeaways for this project:
- Long runs belong to panel-facing nets (jacks, pots, board-to-board headers). Long jack lines are normal.
- The longest single traces (80–110 mm) are all two-pin nets crossing the board.
- On THT boards, op-amp nets run about twice as long as on SMD boards. A THT op-amp − node of ~12 mm per link is
  typical, so the control board doesn't need to meet the main board's 3–6 mm figures.
- A high-impedance + input (for example a 1 MΩ node) deserves the same short-node rule as a − input.
- Ground is carried by the pour, not traces.
