# Testing

## Automated checks

```bash
python -m compileall -q main.py src tests
python -m unittest discover -s tests -v
```

The repository includes unit coverage for game-core transitions, motion speed, player damage, combo, Deploy Energy, Memory Leak regeneration, aiming smoothing, and current V2.5 gameplay configuration.

## Manual CV test matrix

Because camera geometry depends on lighting, distance, hand shape, and webcam field of view, gesture behavior also needs manual validation.

| Test | Expected result |
|---|---|
| Open palm held during impact | projectile blocked; player HP unchanged; energy +1 block |
| Point index at boss | visible ray follows fingertip |
| Point at weak point | weak-point lock / critical feedback |
| Closed fist held still | gauntlet ready, no repeated punch spam |
| Fist moved quickly | Force Punch |
| Thumb + index pinch | Gravity Claw, not FIST |
| Three successful blocks | Deploy Energy reaches 100% |
| Two open palms at 100% | Ultimate triggers; energy resets |
| Stop damaging Memory Leak | regen countdown then +5 HP ticks |
| Production Bug below 50% HP | Rage feedback + faster attacks |

## Performance checks

Record:

- webcam resolution
- average FPS
- CPU/GPU model
- whether landmarks are visible (`D`)
- number of active VFX

Use performance measurements before introducing threading or GPU rendering; optimization without profiling can increase architectural complexity without improving the demo.
