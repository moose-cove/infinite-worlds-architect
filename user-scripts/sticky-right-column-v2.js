// ==UserScript==
// @name         Infinite Worlds Sticky Right Column (v2)
// @namespace    https://infiniteworlds.app/
// @version      2.1.0
// @description  Keep the right image/control column sticky and fit it in viewport height.
// @match        https://infiniteworlds.app/*
// @icon         https://infinite-worlds-images.us-east-1.linodeobjects.com/00000__logo_square_on_background_512.jpg
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
    "use strict";

    const STICKY_CLASS = "iw-sticky-right";
    const MAIN_IMAGE_CLASS = "iw-sticky-main-image";
    const STYLE_ID = "iw-sticky-style-v2";

    const MIN_WIDTH = 769;
    const TOP_GAP_PX = 12;
    const TOP_VAR = "--iw-sticky-top";
    const VIEWPORT_BOTTOM_GAP = 8;
    const MIN_IMAGE_HEIGHT = 140;

    function ensureStyle() {
        if (document.getElementById(STYLE_ID)) return;
        const style = document.createElement("style");
        style.id = STYLE_ID;
        style.textContent = `
      @media (min-width: ${MIN_WIDTH}px) {
        .${STICKY_CLASS} {
          position: sticky !important;
          top: var(${TOP_VAR}, ${TOP_GAP_PX}px) !important;
          align-self: flex-start !important;
          z-index: 2 !important;
        }
      }

      .${MAIN_IMAGE_CLASS} {
        display: block !important;
        width: auto !important;
        max-width: 100% !important;
        height: auto !important;
        object-fit: contain !important;
        margin-left: auto !important;
        margin-right: auto !important;
      }
    `;
        document.head.appendChild(style);
    }

    function cleanText(value) {
        return (value || "").replace(/\s+/g, " ").trim().toLowerCase();
    }

    function isPanelCol(node) {
        return !!(node && node.classList && node.classList.contains("anvil-panel-col"));
    }

    function rowChildCols(row) {
        if (!row) return [];
        return Array.from(row.children).filter(isPanelCol);
    }

    function findRightColumnFromMarker(marker) {
        let node = marker;
        while (node && node !== document.body) {
            if (isPanelCol(node)) {
                const directParent = node.parentElement;
                const row =
                    directParent && directParent.classList.contains("anvil-panel-row")
                        ? directParent
                        : node.closest(".anvil-panel-row");
                const cols = rowChildCols(row);
                if (cols.length >= 2 && cols[cols.length - 1] === node) return node;
            }
            node = node.parentElement;
        }
        return null;
    }

    function addScore(scoreMap, node, points) {
        if (!node) return;
        scoreMap.set(node, (scoreMap.get(node) || 0) + points);
    }

    function bestByScore(scoreMap) {
        let bestNode = null;
        let bestScore = -1;
        for (const [node, score] of scoreMap.entries()) {
            if (score > bestScore) {
                bestNode = node;
                bestScore = score;
            }
        }
        return bestScore > 0 ? bestNode : null;
    }

    function findTargetColumn() {
        const scoreMap = new Map();

        for (const marker of document.querySelectorAll('[title*="image instructions" i]')) {
            addScore(scoreMap, findRightColumnFromMarker(marker), 60);
        }

        for (const textNode of document.querySelectorAll(".button-text")) {
            if (cleanText(textNode.textContent) === "swap image") {
                addScore(scoreMap, findRightColumnFromMarker(textNode), 60);
            }
        }

        for (const marker of document.querySelectorAll("i.fa-wrench, .fa-wrench")) {
            addScore(scoreMap, findRightColumnFromMarker(marker), 20);
        }

        const scoredTarget = bestByScore(scoreMap);
        if (scoredTarget) return scoredTarget;

        let fallback = null;
        let fallbackScore = -1;

        for (const row of document.querySelectorAll(".anvil-panel-row")) {
            const cols = rowChildCols(row);
            if (cols.length < 2) continue;

            const left = cols[0];
            const right = cols[cols.length - 1];
            let score = 0;

            if (right.querySelector('[title*="image instructions" i]')) score += 40;
            if (right.querySelector("i.fa-wrench, .fa-wrench")) score += 20;
            if (right.querySelector(".anvil-image img")) score += 10;

            const leftTextLength = (left.textContent || "").length;
            if (leftTextLength > 700 || left.querySelector(".anvil-rich-text, .anvil-text-area")) {
                score += 15;
            }

            if (score > fallbackScore) {
                fallback = right;
                fallbackScore = score;
            }
        }

        return fallbackScore >= 25 ? fallback : null;
    }

    function clearStickyClass() {
        for (const node of document.querySelectorAll("." + STICKY_CLASS)) {
            node.classList.remove(STICKY_CLASS);
            node.style.removeProperty(TOP_VAR);
            node.style.maxHeight = "";
            node.style.overflowY = "";
            node.style.overflowX = "";
        }

        for (const img of document.querySelectorAll("." + MAIN_IMAGE_CLASS)) {
            img.classList.remove(MAIN_IMAGE_CLASS);
            img.style.maxHeight = "";
        }
    }

    function isPinned(node) {
        const position = getComputedStyle(node).position;
        return position === "fixed" || position === "sticky";
    }

    // Bottom edge of any fixed/sticky bar (e.g. the site header) covering the top of the
    // viewport above the target column, or 0 if nothing is pinned there.
    function headerBottom(target) {
        const rect = target.getBoundingClientRect();
        const xs = [rect.left + 4, rect.left + rect.width / 2, rect.right - 4];
        let bottom = 0;

        for (const x of xs) {
            for (const hit of document.elementsFromPoint(x, 1)) {
                if (target.contains(hit)) continue;
                for (let node = hit; node && node !== document.body; node = node.parentElement) {
                    if (node.contains(target) || !isPinned(node)) continue;
                    const box = node.getBoundingClientRect();
                    if (box.top <= 1 && box.bottom < window.innerHeight / 2) {
                        bottom = Math.max(bottom, box.bottom);
                    }
                    break;
                }
            }
        }

        return Math.ceil(bottom);
    }

    function fitStickyContent(target, topPx) {
        const availableHeight = Math.max(220, window.innerHeight - topPx - VIEWPORT_BOTTOM_GAP);

        target.style.maxHeight = availableHeight + "px";
        target.style.overflowY = "auto";
        target.style.overflowX = "hidden";

        const img = target.querySelector(".anvil-image img");
        if (!img) return;

        img.classList.add(MAIN_IMAGE_CLASS);

        const imageBox = img.closest(".anvil-image");
        if (!imageBox) return;

        img.style.maxHeight = "none";

        const totalHeight = target.scrollHeight;
        const imageBlockHeight = imageBox.offsetHeight;
        const nonImageHeight = Math.max(0, totalHeight - imageBlockHeight);

        const allowedImageHeight = Math.max(MIN_IMAGE_HEIGHT, availableHeight - nonImageHeight - 6);
        img.style.maxHeight = allowedImageHeight + "px";
    }

    function applySticky() {
        clearStickyClass();
        if (window.innerWidth < MIN_WIDTH) return;

        const target = findTargetColumn();
        if (!target) return;

        target.classList.add(STICKY_CLASS);

        const fullHeightForm = target.closest(".anvil-role-full-height-form");
        if (fullHeightForm) fullHeightForm.style.overflow = "visible";

        positionSticky(target);
    }

    function positionSticky(target) {
        const topPx = headerBottom(target) + TOP_GAP_PX;
        target.style.setProperty(TOP_VAR, topPx + "px");
        fitStickyContent(target, topPx);
    }

    // The header can change height or become pinned as the page scrolls, so re-measure
    // on scroll and refit only when the offset actually moved.
    function refreshOffset() {
        const target = document.querySelector("." + STICKY_CLASS);
        if (!target) return;
        const topPx = headerBottom(target) + TOP_GAP_PX;
        if (target.style.getPropertyValue(TOP_VAR) !== topPx + "px") positionSticky(target);
    }

    let rafId = 0;
    function scheduleApply() {
        cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(applySticky);
    }

    let scrollRafId = 0;
    function scheduleRefresh() {
        if (scrollRafId) return;
        scrollRafId = requestAnimationFrame(() => {
            scrollRafId = 0;
            refreshOffset();
        });
    }

    ensureStyle();
    scheduleApply();

    const observer = new MutationObserver(scheduleApply);
    observer.observe(document.body, { childList: true, subtree: true });

    window.addEventListener("resize", scheduleApply, { passive: true });
    document.addEventListener("scroll", scheduleRefresh, { capture: true, passive: true });
})();
