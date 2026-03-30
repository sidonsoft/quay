/**
 * Minimal Stealth Script for Quay Browser
 * Provides basic fingerprinting protection
 * This is a placeholder for more comprehensive stealth libraries
 */

(function() {
    'use strict';

    // Prevent script detection
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', description: 'Portable Document Format' }
        ],
        configurable: true
    });

    // Prevent extensions detection
    Object.defineProperty(navigator, 'extensions', {
        get: () => [],
        configurable: true
    });

    // Prevent hardware concurrency spoofing
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8,
        configurable: true
    });

    // Prevent language spoofing
    Object.defineProperty(navigator, 'language', {
        get: () => 'en-US',
        configurable: true
    });

    // Prevent languages array spoofing
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
        configurable: true
    });

    // Prevent vendor spoofing
    Object.defineProperty(navigator, 'vendor', {
        get: () => 'Google Inc.',
        configurable: true
    });

    // Prevent WebGL vendor detection
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return getParameter.call(this, parameter);
    };

    // Mark script as loaded
    window.__stealth_script_loaded = true;

    console.log('[Quay Stealth] Basic stealth protection initialized');
})();
