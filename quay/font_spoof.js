// Font Spoofing Script for Quay Browser
// Fakes font enumeration to prevent fingerprinting

(function() {
    // Store original FontFace constructor
    const OriginalFontFace = window.FontFace;
    
    // Realistic font list that looks like a typical macOS Chrome installation
    const SPOOFED_FONTS = [
        'Arial',
        'Arial Black',
        'Arial Narrow',
        'Arial Rounded MT Bold',
        'Arial MT',
        'Arial Narrow Bold',
        'Arial Bold',
        'Arial Black MT',
        'Arial Bold MT',
        'Helvetica',
        'Helvetica Neue',
        'Times New Roman',
        'Times',
        'Georgia',
        'Verdana',
        'Tahoma',
        'Trebuchet MS',
        'Palatino',
        'Garamond',
        'Bookman',
        'Comic Sans MS',
        'Impact',
        'Lucida Sans Unicode',
        'Geneva',
        'Lucida Console',
        'Courier New',
        'Courier',
        'Monaco',
        'Menlo',
        'Monaco',
        'Andale Mono',
        'Lucida Console',
        'Liberation Mono',
        'Apple Color Emoji',
        'Segoe UI Emoji',
        'Segoe UI Symbol',
        'Noto Color Emoji',
        'Apple SD Gothic Neo',
        'Apple Color Emoji',
        'Hiragino Kaku Gothic Pro',
        'Hiragino Sans',
        'Hiragino Mincho Pro',
        'Meiryo',
        'MS Gothic',
        'MS PGothic',
        'MS UI Gothic',
        'Yu Gothic',
        'Yu Gothic UI',
        'Segoe UI',
        'Segoe UI Black',
        'Segoe UI Bold',
        'Segoe UI Emoji',
        'Segoe UI Historic',
        'Segoe UI Light',
        'Segoe UI Semibold',
        'Segoe UI Symbol',
        'Segoe UI Variable',
        'Segoe UI Variable Display',
        'Segoe UI Variable Text',
        'Segoe UI',
        'SF Mono',
        'SF Pro Display',
        'SF Pro Icons',
        'SF Pro Text',
        'SF Pro Rounded',
        'SF Pro',
        'PingFang SC',
        'PingFang TC',
        'PingFang HK',
        'PingFang UI',
        'STHeiti',
        'STSong',
        'KaiTi',
        'STKaiti',
        'STSong-Light',
        'STHeiti Light',
        'Heiti SC',
        'Heiti TC',
        'Heiti HK',
        'Heiti UI',
        'Songti SC',
        'Songti TC',
        'Songti HK',
        'Songti UI',
        'Songti SC Light',
        'Songti TC Light',
        'Songti HK Light',
        'Songti UI Light',
        'Lantinghei SC',
        'Lantinghei TC',
        'Lantinghei HK',
        'Lantinghei UI',
        'Lantinghei SC Light',
        'Lantinghei TC Light',
        'Lantinghei HK Light',
        'Lantinghei UI Light'
    ];

    // Spoof document.fonts
    const originalFonts = Object.getOwnPropertyDescriptor(Document.prototype, 'fonts');
    
    if (originalFonts && originalFonts.get) {
        Object.defineProperty(Document.prototype, 'fonts', {
            get: function() {
                // Create a spoofed FontFaceList
                const spoofedFonts = new FontFaceList();
                
                // Add spoofed fonts
                SPOOFED_FONTS.forEach(fontName => {
                    try {
                        const font = new OriginalFontFace(fontName, 'local("fake-font")');
                        spoofedFonts.add(font);
                    } catch (e) {
                        // Skip if font creation fails
                    }
                });
                
                return spoofedFonts;
            },
            configurable: true
        });
    }

    // Expose spoofing flag
    window.__font_spoofed = true;
    console.log('[Quay] Font spoofing enabled - font enumeration hidden');
})();
