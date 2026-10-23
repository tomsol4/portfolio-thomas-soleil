"""Accessible viewer shared by galleries and individual photographs."""


def lightbox_markup():
    return '''<dialog class="lightbox" id="lightbox" aria-label="Visionneuse de photographies">
<div class="lightbox-top"><p id="photo-counter" aria-live="polite" aria-atomic="true"></p><button type="button" class="lightbox-close" aria-label="Fermer la photo" autofocus>×</button></div>
<div class="lightbox-stage"><button type="button" class="lightbox-prev" aria-label="Photo précédente">‹</button><img alt="" hidden><p class="photo-status" id="photo-status" role="status"></p><button type="button" class="lightbox-next" aria-label="Photo suivante">›</button></div>
<div class="lightbox-bottom"><span class="lightbox-hint">← → pour naviguer · Échap pour fermer</span><a id="photo-print" hidden>Demander un tirage</a><a id="photo-original" target="_blank" rel="noopener">Ouvrir la photo<span class="sr-only"> (nouvel onglet)</span></a></div>
</dialog>'''
