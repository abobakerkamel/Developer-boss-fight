# Gameplay Design

## Core interaction loop

```text
Boss attacks → player blocks → counter-attack → combo builds →
three successful blocks → Deploy Energy 100% → Ultimate
```

The intention is to make gestures context-sensitive gameplay actions rather than isolated visual demos.

## Player controls

| Input | Action | Logic |
|---|---|---|
| ✋ Open Palm | Firewall Shield | defend against incoming projectile |
| ☝ Pointing | Debug Blaster | aim ray, target lock, weak-point critical |
| 👊 Fist + fast movement | Force Punch | speed-gated physical attack |
| 🤏 Pinch | Gravity Claw | grab/manipulate boss position |
| 🙌 Two Open Palms | Deploy Ultimate | requires 100% Deploy Energy |

## Deploy Energy

Deploy Energy is deliberately defensive in V2.5:

- successful Firewall block 1 → ~33%
- successful Firewall block 2 → ~66%
- successful Firewall block 3 → 100%
- normal attacks do not charge it
- Ultimate consumes the full meter and resets the block count

This creates a tactical loop: the player cannot spam offense to reach Ultimate; they must survive and block correctly.

## Waves

| Wave | Boss | HP | Mechanic |
|---|---|---:|---|
| 1 | BUG — Level 99 | 100 | baseline training boss |
| 2 | MEMORY LEAK — Level 120 | 150 | regenerates after the player stops damaging it |
| 3 | DEPENDENCY HELL — Level 150 | 200 | standard combat in current V2.5 build |
| 4 | PRODUCTION BUG — Level 999 | 300 | Rage Mode below 50% HP |

## Memory Leak

After 2 seconds without taking damage, Memory Leak regenerates +5 HP every 0.5 seconds until hit again or fully healed. The HUD exposes a countdown and regeneration state so the mechanic is readable on video.

## Production Bug Rage

At ≤50% HP the final boss enters Rage Mode.

Normal attack behavior:
- attack interval ≈ 3.6 s
- projectile travel ≈ 0.9 s

Rage behavior:
- attack interval ≈ 1.15 s
- projectile travel ≈ 0.38 s
- shorter charge animation
- explicit `RAGE MODE x3 ATTACK SPEED` HUD feedback

## Combo and score

Consecutive successful hits build a combo. Combo increases the damage multiplier up to a cap and contributes to score. Taking player damage breaks momentum.

## Boss attacks

Boss attacks use a readable visual sequence:

```text
BOSS CHARGING...
      ↓
Energy Orb
      ↓
Launch + Trail + Sparks
      ↓
INCOMING ATTACK
      ↓
Firewall Block OR Player Hit
```

The visual telegraph is intentionally larger than a realistic projectile because the mechanic needs to remain readable in webcam footage.
