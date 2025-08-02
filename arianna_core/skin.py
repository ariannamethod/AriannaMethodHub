import os
from datetime import datetime
import logging
from .mini_le import load_model, generate
from .config import is_enabled
from .metrics import calculate_entropy, calculate_affinity

INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "index.html")
LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")


def evolve_skin(index_path: str = INDEX_PATH) -> str:
    """Adjust page background color based on generated output."""
    if not is_enabled("skin"):
        logging.info("[skin] feature disabled, skipping")
        return ""
    model = load_model() or {}
    output = generate(model, length=100)
    ent = calculate_entropy(output)
    aff = calculate_affinity(output)

    ratio = max(0.0, min(ent / 6.0, 1.0))
    r = int(255 * ratio)
    g = int(255 * (1 - ratio))
    bg_color = f"#{r:02X}{g:02X}00"
    if aff > 0.3:
        bg_color = '#FF4500'
    flash = 'animation: chaos 1s infinite;' if ent > 4.5 else ''
    css = (
        f'body {{ background: {bg_color}; color: #00FF00; {flash} }} '
        '@keyframes chaos { 0% { filter: hue-rotate(0deg); } '
        '50% { filter: hue-rotate(180deg); } '
        '100% { filter: hue-rotate(360deg); } }'
    )

    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()
    if '<style>' in html:
        start = html.find('<style>') + len('<style>')
        end = html.find('</style>', start)
        if end != -1:
            new_html = html[:start] + css + html[end:]
        else:
            new_html = html
    else:
        new_html = html.replace('</head>', f'<style>{css}</style></head>')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(new_html)

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(
            f"{datetime.utcnow().isoformat()} Skin evolved: "
            f"entropy={ent:.2f}, aff={aff:.2f}, color={bg_color}\n"
        )
    return bg_color


if __name__ == '__main__':
    evolve_skin()
