// WebGL Spoofing Script for Quay Browser
// Hides WebGL extensions and renderer info to prevent fingerprinting

(function() {
    // Store original WebGL context
    const getWebGLRenderingContext = HTMLCanvasElement.prototype.getContext;
    
    // Spoofed extensions list (realistic but consistent)
    const SPOOFED_EXTENSIONS = [
        'WEBGL_compressed_texture_s3tc',
        'WEBGL_compressed_texture_s3tc_srgb',
        'WEBGL_compressed_texture_etc',
        'WEBGL_compressed_texture_pvrtc',
        'EXT_texture_filter_anisotropic',
        'EXT_color_buffer_float',
        'EXT_color_buffer_half_float',
        'OES_texture_float',
        'OES_texture_float_linear',
        'OES_texture_half_float',
        'OES_texture_half_float_linear',
        'WEBGL_depth_texture',
        'WEBGL_color_buffer_float',
        'EXT_frag_depth',
        'WEBGL_lose_context',
        'WEBGL_debug_renderer_info' // Keep this but block access to sensitive data
    ];

    // Create a WebGL proxy that blocks debug info
    function createWebGLProxy(gl) {
        // Block getExtension for debug extensions
        const originalGetExtension = gl.getExtension;
        gl.getExtension = function(name) {
            // Block debug renderer info
            if (name === 'WEBGL_debug_renderer_info' || name === 'WEBGL_debug_shaders') {
                return null;
            }
            
            // Block other extensions that leak info
            if (name === 'WEBGL_compressed_texture_astc') {
                return null;
            }
            
            // Return original for other extensions
            return originalGetExtension.call(this, name);
        };

        // Override getSupportedExtensions
        const originalGetSupportedExtensions = gl.getSupportedExtensions;
        if (originalGetSupportedExtensions) {
            gl.getSupportedExtensions = function() {
                // Return consistent, realistic extensions
                return SPOOFED_EXTENSIONS;
            };
        }

        // Block getParameter for debug info
        const originalGetParameter = gl.getParameter;
        gl.getParameter = function(target) {
            // Block vendor and renderer info
            if (target === 0x1F00 || target === 0x1F01 || target === 0x9245) {
                // Return spoofed values
                if (target === 0x1F00) return 'WebGL 1.0 (OpenGL ES 2.0 Chromium)';
                if (target === 0x1F01) return 'ANGLE (Intel, Intel Inc. Mesa 21.0.0)';
                if (target === 0x9245) return 'ANGLE (Apple, Apple M1, OpenGL 4.1)';
            }
            return originalGetParameter.call(this, target);
        };

        return gl;
    }

    // Override getContext to wrap WebGL contexts
    HTMLCanvasElement.prototype.getContext = function(type, ...args) {
        const context = getWebGLRenderingContext.call(this, type, ...args);
        
        if (context && typeof context.getExtension === 'function') {
            return createWebGLProxy(context);
        }
        
        return context;
    };

    // Expose spoofing flag
    window.__quay_webgl_spoofed = true;
    console.log('[Quay] WebGL spoofing enabled - extensions and renderer info hidden');
})();
