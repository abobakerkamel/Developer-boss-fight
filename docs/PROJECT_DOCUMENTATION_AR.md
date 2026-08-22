# توثيق مشروع Developer Boss Fight — بالعربي

## الفكرة

Developer Boss Fight هو تطبيق AR / Computer Vision لحظي يحول حركات اليد أمام الكاميرا إلى أسلحة وتصرفات داخل لعبة Boss Fight. المشروع مبني بـPython وOpenCV وMediaPipe ويستخدم 21 Hand Landmarks لكل يد.

## الـPipeline

```text
Camera
→ MediaPipe Hand Tracking
→ 21 Landmarks
→ Gesture Classification
→ Temporal Stabilization
→ Motion / Aiming Analysis
→ Game Controller
→ Boss Mechanics
→ VFX + HUD + Sound
→ Final AR Frame
```

## الحركات

- ✋ Open Palm → Firewall Shield
- ☝️ Pointing → Debug Blaster + Target Lock
- 👊 Fist + حركة سريعة → Force Punch
- 🤏 Pinch → Gravity Claw
- 🙌 إيدين مفتوحين → Deploy Ultimate بعد وصول الطاقة 100%

## أصعب مشكلة CV: الفرق بين 🤏 و👊

المشكلتان متشابهتان هندسيًا لأن الأصابع تكون مطوية في الحالتين. لذلك لم يعتمد المشروع على `open/closed` فقط. الحل الحالي يستخدم:

- المسافة بين Thumb Tip وIndex Tip بعد تطبيعها بحجم الكف
- زوايا مفاصل الأصابع
- شرط Compact Fist أقوى
- شرط خاص بمكان الإبهام في القبضة
- فحص PINCH قبل FIST
- Temporal Stabilization على عدة Frames

الفكرة المهمة هي أن المسافة لا تكون Pixel ثابتة، بل نسبة إلى Palm Scale حتى لا تتغير النتيجة لو قربت أو بعدت عن الكاميرا.

## التصويب

بدل الاعتماد على Segment واحد، اتجاه التصويب يُستخرج من:

```text
MCP → PIP → DIP → TIP
```

ثم يتم عمل Smoothing عبر عدة Frames، فيخرج الـAim Line من طرف السبابة بشكل أقرب لاتجاه الإصبع الحقيقي.

## الـBosses

1. BUG — Level 99 — 100 HP
2. MEMORY LEAK — Level 120 — 150 HP، يعيد +5 HP كل 0.5 ثانية بعد ثانيتين بدون Damage
3. DEPENDENCY HELL — Level 150 — 200 HP، قتال عادي في V2.5
4. PRODUCTION BUG — Level 999 — 300 HP، يدخل Rage عند 50% HP ويهاجم أسرع بوضوح

## Deploy Energy

الطاقة لا تزيد من الضربات العادية. فقط صد هجمات الـBoss بالـFirewall:

```text
Block 1 → 33%
Block 2 → 66%
Block 3 → 100%
```

بعدها تفتح اليدين معًا لتشغيل Ultimate، ثم ترجع الطاقة إلى 0%.

## لماذا المشروع مهم تقنيًا؟

لأنه لا يكتفي بـHand Tracking. هو يربط الرؤية الحاسوبية بمنطق لعبة كامل: Gesture Geometry + Temporal Features + Targeting + State Machines + Boss Mechanics + VFX + Audio + Testing.
