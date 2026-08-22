# Contributing

Contributions are welcome, especially around gesture robustness, temporal motion features, VFX performance, boss mechanics, and cross-platform audio.

## Development workflow

1. Fork the repository and create a focused branch.
2. Create a Python 3.12 virtual environment.
3. Install `requirements.txt`.
4. Keep computer-vision logic, game logic, and rendering concerns separated.
5. Add or update tests for behavior changes.
6. Run:

```bash
python -m compileall -q main.py src tests
python -m unittest discover -s tests -v
```

## Design rules

- Do not put game rules in rendering classes.
- Do not put rendering code in `GameController`.
- Normalize geometric thresholds by hand/palm scale where possible.
- Dynamic gestures should use temporal features rather than single-frame heuristics.
- Prefer local/ROI blur over full-frame blur for performance-sensitive VFX.
- Keep boss data in `config/` rather than hard-coding new waves.

## Pull requests

Keep PRs small enough to review. For gesture changes, explain the geometry and include failure cases. For VFX changes, report FPS impact if material.
