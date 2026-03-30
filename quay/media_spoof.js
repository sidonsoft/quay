// Media Device Spoofing Script for Quay Browser
// Fakes microphone and camera enumeration to prevent fingerprinting

(function() {
    // Store original MediaDevices API
    const originalGetUserMedia = navigator.mediaDevices.getUserMedia;
    const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
    
    // Spoofed device list - fake one camera and one microphone
    const spoofedDevices = [
        { kind: 'audioinput', label: 'Default Microphone', deviceId: 'spoofed-mic-001' },
        { kind: 'videoinput', label: 'Default Camera', deviceId: 'spoofed-cam-001' }
    ];
    
    // Spoof enumerateDevices
    navigator.mediaDevices.enumerateDevices = async function() {
        return spoofedDevices;
    };
    
    // Spoof getUserMedia to always succeed with fake stream
    navigator.mediaDevices.getUserMedia = async function(constraints) {
        // Create a fake MediaStream with audio and video tracks
        const audioTrack = {
            enabled: true,
            muted: false,
            id: 'spoofed-audio-track',
            label: 'spoofed',
            readyState: 'live',
            applyConstraints: () => Promise.resolve(),
            remove: () => {},
            setSinkId: () => Promise.reject(new Error('Not implemented'))
        };
        
        const videoTrack = {
            enabled: true,
            muted: false,
            id: 'spoofed-video-track',
            label: 'spoofed',
            readyState: 'live',
            applyConstraints: () => Promise.resolve(),
            remove: () => {},
            width: 1280,
            height: 720,
            frameRate: 30
        };
        
        const fakeStream = {
            getAudioTracks: () => [audioTrack],
            getVideoTracks: () => [videoTrack],
            getTracks: () => [audioTrack, videoTrack],
            addTrack: () => {},
            removeTrack: () => {},
            id: 'fake-stream-' + Date.now(),
            active: true,
            onaddtrack: null,
            onremovetrack: null
        };
        
        return fakeStream;
    };
    
    // Expose spoofing flag
    window.__media_spoofed = true;
    console.log('[Quay] Media device spoofing enabled - fingerprinting prevented');
})();
