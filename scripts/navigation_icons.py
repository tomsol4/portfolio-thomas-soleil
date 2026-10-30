"""Render decorative link arrows consistently, without relying on system fonts."""
import re


PATHS = {
    '↗': 'M7 17 17 7M7 7h10v10',
    '→': 'M4 12h16M14 6l6 6-6 6',
    '←': 'M20 12H4M10 6l-6 6 6 6',
    '↑': 'M12 20V4M6 10l6-6 6 6',
    '↓': 'M12 4v16M6 14l6 6 6-6',
}
ICONS = {
    character: (
        '<svg class="nav-arrow" xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 24 24" width="24" height="24" fill="none" '
        'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="{path}"/></svg>'
    )
    for character, path in PATHS.items()
}
LINK = re.compile(r'(<a\b[^>]*>)(.*?)(</a>)', re.I | re.S)


def render_navigation_arrows(markup):
    def replace_link(match):
        # Only replace text in links; retain attributes, accessible labels and metadata.
        parts = re.split(r'(<[^>]+>)', match[2])
        for index in range(0, len(parts), 2):
            for character, icon in ICONS.items():
                parts[index] = parts[index].replace(character, icon)
        return match[1] + ''.join(parts) + match[3]

    return LINK.sub(replace_link, markup)
