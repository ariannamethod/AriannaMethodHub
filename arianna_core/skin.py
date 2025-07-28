import math
from datetime import datetime
from .mini_le import load_model, generate

INDEX_PATH = 'index.html'
LOG_FILE = 'arianna_core/log.txt'

WORDS = ['resonance', 'echo', 'thunder', 'love']


def calculate_entropy(text: str) -> float:
    """Return Shannon entropy of ``text``."""
    if not text:
        return 0.0
    freq = {c: text.count(c) / len(text) for c in set(text)}
    return -sum(p * math.log2(p) for p in freq.values())


def affinity(text: str) -> float:
    """Return proportion of characters belonging to affinity words."""
    if not text:
        return 0.0
    lower = text.lower()
    return sum(lower.count(w) for w in WORDS) / len(text)


def evolve_skin(index_path: str = INDEX_PATH) -> str:
    """Adjust page background color based on generated output."""
    model = load_model() or {}
    output = generate(model, length=100)
    ent = calculate_entropy(output)
    aff = affinity(output)

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
        '50% { filter: hue-rotate(180deg); } 100% { filter: hue-rotate(360deg); } }'
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
            f"{datetime.utcnow().isoformat()} Skin evolved: entropy={ent:.2f}, "
            f"aff={aff:.2f}, color={bg_color}\n"
        )
    return bg_color


if __name__ == '__main__':
    evolve_skin()
