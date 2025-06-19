(() => {
    const userUuid = window.USER_UUID;
    const exhibitionId = window.EXHIBITION_ID;
    const items = window.EXHIBITION_ITEMS;

    let currentItemIndex = 0;
    const slideCache = {};

    const currentItemContainer = document.getElementById('current-item');
    const pageIndicator = document.getElementById('page-indicator');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');

    function isImage(filename) {
        if (!filename) return false;
        const ext = filename.split('.').pop().toLowerCase();
        return ['png', 'jpg', 'jpeg'].includes(ext);
    }

    function simpleMarkdown(md) {
        let html = md
            .replace(/^(#{1,6})\s*(.+)$/gm, (m, hashes, title) => `<h${hashes.length}>${title}</h${hashes.length}>`)
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*\*/g, '<em>$1</em>')
            .replace(/!\[(.*?)\]\((.*?)\)/g, '<img src="$2" alt="$1" style="max-width:100%;"/>')
            .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>')
            .replace(/\n/g, '<br/>');
        html = html.replace(/\[carousel(?:\s+delay="([\d.]+)")?(?:\s+max_width="([^"]+)")?(?:\s+max_height="([^"]+)")?\]([\s\S]*?)\[\/carousel\]/g,
            (m, delay, maxW, maxH, inner) => {
                const interval = parseFloat(delay) || 3;
                const slides = inner.trim().split(/<br\/?\>/)
                    .filter(s => s.trim())
                    .map(item => {
                        let style = '';
                        if (maxW) style += `max-width:${maxW};`;
                        if (maxH) style += `max-height:${maxH};`;
                        return `<div class="slide" style="${style}">${item}</div>`;
                    }).join('');
                return `<div class="carousel" data-delay="${interval}"><div class="slides">${slides}</div></div>`;
            });
        return html;
    }

    function initCarousel(carousel) {
        if (carousel._initialized) return;
        const slides = carousel.querySelector('.slides');
        const total = slides.children.length;
        let idx = 0;

        function show(i) {
            slides.style.transform = `translateX(-${i * 100}%)`;
        }

        show(idx);
        const delay = parseFloat(carousel.dataset.delay) || 3;
        setInterval(() => {
            idx = (idx + 1) % total;
            show(idx);
        }, delay * 1000);
        carousel._initialized = true;
    }

    function updateCurrentItem() {
        const currentItem = items[currentItemIndex];
        const ext = currentItem.filename ? currentItem.filename.split('.').pop().toLowerCase() : '';

        const title = currentItem.name || (currentItem.filename ? currentItem.filename.split('.')[0].replace(/_/g, ' ') : 'Без названия');
        const description = currentItem.description || currentItem.desc || currentItem.text || currentItem.annotation || 'Описание отсутствует';

        let contentHtml = '';
        if (ext === 'md' || ext === 'html') {
            contentHtml = `<div id="layout-render" class="item-content layout-block"><div class="spinner"></div></div>`;
        } else if (isImage(currentItem.filename)) {
            contentHtml = `
        <div class="item-display">
          <img src="/uploads/exhibitions/${userUuid}/${exhibitionId}/${currentItem.filename}" class="display-image" alt="${title}" />
          <div class="item-info">
            <h2 class="item-title">${title}</h2>
            <p class="item-description">${description}</p>
          </div>
        </div>`;
        } else {
            contentHtml = `<a href="/uploads/exhibitions/${userUuid}/${exhibitionId}/${currentItem.filename}" class="download-link">Скачать файл (${currentItem.filename})</a>`;
        }

        currentItemContainer.innerHTML = `<div class="item-content">${contentHtml}</div>`;

        if (ext === 'md' || ext === 'html') {
            const url = `/uploads/exhibitions/${userUuid}/${exhibitionId}/${currentItem.filename}`;
            const key = currentItemIndex;
            if (slideCache[key]) {
                document.getElementById('layout-render').innerHTML = slideCache[key];
                document.getElementById('layout-render').querySelectorAll('.carousel').forEach(initCarousel);
            } else {
                fetch(url)
                    .then(res => res.text())
                    .then(text => {
                        let rendered = ext === 'md' ? simpleMarkdown(text) : text;
                        slideCache[key] = rendered;
                        document.getElementById('layout-render').innerHTML = rendered;
                        document.getElementById('layout-render').querySelectorAll('.carousel').forEach(initCarousel);
                    });
            }
        }

        pageIndicator.textContent = `${currentItemIndex + 1}/${items.length}`;
    }

    function animateTransition(direction) {
        const content = currentItemContainer.querySelector('.item-content');
        if (!content) return;
        const className = direction === 'left' ? 'swipe-left' : 'swipe-right';
        content.classList.add(className);
        setTimeout(() => {
            content.classList.remove('swipe-left', 'swipe-right');
        }, 300);
    }

    function prevItem() {
        if (currentItemIndex > 0) {
            currentItemIndex--;
            updateCurrentItem();
            animateTransition('right');
        }
    }

    function nextItem() {
        if (currentItemIndex < items.length - 1) {
            currentItemIndex++;
            updateCurrentItem();
            animateTransition('left');
        }
    }

    prevBtn.addEventListener('click', prevItem);
    nextBtn.addEventListener('click', nextItem);

    document.addEventListener('keydown', e => {
        if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
        if (e.code === 'Space' || e.code === 'ArrowRight') {
            e.preventDefault();
            nextItem();
        } else if (e.code === 'ArrowLeft') {
            e.preventDefault();
            prevItem();
        }
    });

    let startX = 0;
    currentItemContainer.addEventListener('touchstart', e => {
        startX = e.touches[0].clientX;
    });

    currentItemContainer.addEventListener('touchend', e => {
        const endX = e.changedTouches[0].clientX;
        const deltaX = endX - startX;
        if (Math.abs(deltaX) > 50) {
            if (deltaX < 0) nextItem();
            else prevItem();
        }
    });

    document.addEventListener('DOMContentLoaded', () => {
        updateCurrentItem();
    });
})();
