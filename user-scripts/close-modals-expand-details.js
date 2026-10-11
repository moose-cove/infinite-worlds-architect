// ==UserScript==
// @name         Auto-close modal popups and expand/collapse details
// @namespace    https://infiniteworlds.app/
// @version      1.0
// @description  Automatically close frequent popups and expand/collapse details
// @match        https://infiniteworlds.app/
// @icon         https://infinite-worlds-images.us-east-1.linodeobjects.com/00000__logo_square_on_background_512.jpg
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    const checkedClass = "userscript-checked";

    function hasDesiredText(target, desiredText) {
        for (let desired of desiredText) {
            if (target.includes(desired)) {
                return true;
            }
        }
        return false;
    }

    function closeModal() {
        const selector = "#alert-modal button.btn-success";
        const button = document.querySelector(selector);
        if (button === null) {
            return;
        }
        const desiredText = [
            "18 years",
            "Changes discarded",
            "Changes saved",
            "Discord server",
            "NSFW",
        ];
        const text = button.closest("#alert-modal").textContent;
        if (hasDesiredText(text, desiredText)) {
            button.click();
        }
    }
    const observer1 = new MutationObserver(closeModal);
    observer1.observe(document.body, {characterData: true, childList: true, subtree: true});

    // Inside modals
    function expandDetails() {
        const desiredText = [
            "Latest details",
            "Inputs",
            "Outputs",
        ];
        const selector = ".modal-content button > .left.fa-angle-right";
        Array.from(document.querySelectorAll(selector))
            .filter(e => !e.classList.contains(checkedClass))
            .filter(e => hasDesiredText(e.closest("button").textContent, desiredText))
            .forEach(e => e.click());
        Array.from(document.querySelectorAll(selector))
            .filter(e => !e.classList.contains(checkedClass))
            .forEach(e => e.classList.add(checkedClass));
    }
    const observer2 = new MutationObserver(expandDetails);
    observer2.observe(document.body, {characterData: true, childList: true, subtree: true});

    // Outside of modals
    function collapseDetails() {
        const desiredText = [
            "Example worlds",
        ];
        const selector = "#appGoesHere .left.fa-angle-down";
        Array.from(document.querySelectorAll(selector))
            .filter(e => !e.classList.contains(checkedClass))
            .filter(e => hasDesiredText(e.closest("button").textContent, desiredText))
            .forEach(e => e.click());
        Array.from(document.querySelectorAll(selector))
            .filter(e => !e.classList.contains(checkedClass))
            .forEach(e => e.classList.add(checkedClass));
    }
    const observer3 = new MutationObserver(collapseDetails);
    observer3.observe(document.body, {characterData: true, childList: true, subtree: true});

})();