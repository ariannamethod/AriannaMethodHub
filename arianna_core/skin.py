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

    if ent < 4:
        bg_color = '#000000'
    elif ent < 6 and aff < 0.2:
        bg_color = '#00FF00'
    elif ent >= 6:
        bg_color = '#FF0000'
    elif aff > 0.3:
        bg_color = '#FF4500'
    else:
        bg_color = '#008000'
    flash = 'animation: flash 1s infinite;' if ent > 5 else ''
    css = (
        f'body {{ background-color: {bg_color}; color: #00FF00; {flash} }} '
        '@keyframes flash { 0% { opacity: 1; } '
        '50% { opacity: 0.5; } 100% { opacity: 1; } }'
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
