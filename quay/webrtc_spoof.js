// WebRTC Spoofing Script for Quay Browser
// Prevents IP address leaks via WebRTC

(function() {
    // Store original RTCPeerConnection
    const OriginalRTCPeerConnection = window.RTCPeerConnection;
    
    // Create a spoofed RTCPeerConnection that doesn't leak IPs
    window.RTCPeerConnection = function(config) {
        // Remove candidates from the config to prevent IP leaks
        if (config && config.iceServers) {
            config.iceServers = [];
        }
        
        const peerConnection = new OriginalRTCPeerConnection(config);
        
        // Override createOffer to prevent candidate gathering
        const originalCreateOffer = peerConnection.createOffer;
        peerConnection.createOffer = function() {
            return Promise.resolve({
                type: 'offer',
                sdp: 'm=application 0 UDP/DTLS/SCTP 5000\r\n'
            });
        };
        
        // Override createAnswer similarly
        const originalCreateAnswer = peerConnection.createAnswer;
        peerConnection.createAnswer = function() {
            return Promise.resolve({
                type: 'answer',
                sdp: 'm=application 0 UDP/DTLS/SCTP 5000\r\n'
            });
        };
        
        return peerConnection;
    };
    
    // Expose spoofing flag
    window.__quay_webrtc_spoofed = true;
    console.log('[Quay] WebRTC spoofing enabled - IP leaks prevented');
})();
