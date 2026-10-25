(() => {
    'use strict';
    document.querySelectorAll('.photo-grid').forEach(grid => {
        const photos = [...grid.children].map(item => {
            const image = item.querySelector('img');
            return { item, ratio: Number(image?.getAttribute('width')) / Number(image?.getAttribute('height')) };
        });
        if (!photos.length || photos.some(photo => !Number.isFinite(photo.ratio) || photo.ratio <= 0)) return;

        function layout() {
            const width = grid.clientWidth;
            if (!width) return;
            const style = getComputedStyle(grid);
            const columns = Number.parseInt(style.getPropertyValue('--gallery-columns'), 10);
            const gap = Number.parseFloat(style.getPropertyValue('--gallery-gap'));
            const itemWidth = (width - (columns - 1) * gap) / columns;
            const heights = Array(columns).fill(0);
            grid.style.setProperty('--gallery-item-width', `${itemWidth}px`);
            // Known image dimensions let us place even lazy-loaded photos immediately.
            // Keep the DOM order so keyboard and viewer navigation follow the publication.
            photos.forEach(({ item, ratio }) => {
                const top = Math.min(...heights);
                const column = heights.indexOf(top);
                item.style.setProperty('--gallery-x', `${column * (itemWidth + gap)}px`);
                item.style.setProperty('--gallery-y', `${top}px`);
                heights[column] += itemWidth / ratio + gap;
            });
            grid.style.setProperty('--gallery-height', `${Math.max(...heights) - gap}px`);
            grid.classList.add('is-masonry');
        }

        let frame = 0;
        function scheduleLayout() {
            cancelAnimationFrame(frame);
            frame = requestAnimationFrame(layout);
        }
        if (typeof ResizeObserver === 'function') {
            let previousWidth = -1;
            const observer = new ResizeObserver(([entry]) => {
                if (entry.contentRect.width === previousWidth) return;
                previousWidth = entry.contentRect.width;
                scheduleLayout();
            });
            observer.observe(grid);
        } else {
            window.addEventListener('resize', scheduleLayout);
        }
        layout();
    });
})();
