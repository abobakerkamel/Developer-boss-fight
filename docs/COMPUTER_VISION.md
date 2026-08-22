# Computer Vision and Gesture Recognition

## MediaPipe hand representation

Each detected hand is represented by 21 landmarks. The project uses geometric relationships rather than a separately trained gesture classifier.

## Static gestures

| Gesture | Gameplay action | Primary cues |
|---|---|---|
| Open Palm | Firewall Shield | extended fingers + thumb geometry |
| Pointing | Debug Blaster | extended index, folded middle/ring/pinky |
| Fist | Force Gauntlet | all four fingers folded + thumb near palm |
| Pinch | Gravity Claw | normalized thumb-tip ↔ index-tip distance |
| Both open palms | Deploy Ultimate | two-hand composition |

## The difficult case: PINCH vs FIST

PINCH and FIST are deceptively similar in landmark space. Both contain bent fingers and a compact silhouette. A naive rule such as "if most fingers are folded, call it FIST" produces false positives.

The current classifier separates them using several techniques:

1. **Scale normalization** — thumb-tip to index-tip distance is divided by palm scale, making the threshold less sensitive to camera distance.
2. **Classifier priority** — PINCH is evaluated before FIST.
3. **Index bend geometry** — a natural pinch keeps a curved-but-not-fully-crushed index finger.
4. **Compact-fist rejection** — PINCH is rejected when all fingers satisfy a stricter deep-fold condition.
5. **Fist-specific thumb rule** — FIST requires the thumb to sit close to the palm/index base.
6. **Temporal stabilization** — a gesture must remain stable across recent frames before it becomes a gameplay event.

Conceptually:

```text
thumb_tip ↔ index_tip distance
----------------------------  < threshold  → possible PINCH
         palm scale
```

The important point is that the threshold is **relative**, not a fixed pixel distance.

## Precise pointing

Early versions used a single segment, PIP → TIP, which was responsive but visually noisy. V2.4+ estimates direction from multiple finger segments:

```text
MCP → PIP → DIP → TIP
```

Distal segments receive more weight, then the direction is smoothed across recent frames. The resulting ray is used by the targeting system and rendered from the fingertip so the visual aim matches the user's perception.

## Dynamic punch

A fist alone does not equal a punch. The application combines:

- static state: FIST
- temporal velocity: hand center movement across a short time window

A high enough velocity triggers Force Punch; a larger threshold triggers Critical Force Punch.

This distinction is important because it upgrades the system from static pose recognition to simple temporal gesture understanding.

## Stabilization and cooldown

Camera inference can oscillate between neighboring classes from one frame to the next. The stabilizer maintains recent classifications, applies majority-like confirmation, and enforces cooldowns to prevent a held pose from firing dozens of attacks per second.

## Known limitations

- Rule-based thresholds can still vary by hand shape and camera angle.
- Severe occlusion can break PINCH/FIST separation.
- Z-depth from monocular hand tracking is not yet used as a primary punch feature.
- Per-user calibration and a learned temporal classifier are possible future upgrades.
