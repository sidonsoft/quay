async def _inject_spoofing_scripts_for_tab_async(self, tab: Tab) -> bool:
        """Inject spoofing scripts into a tab using Runtime.evaluate (post-navigation).
        
        CRITICAL FIX: Use Runtime.evaluate instead of Page.addScriptToEvaluateOnNewDocument
        because the latter only works for documents created AFTER injection, not for
        already-loaded pages.
        """
        try:
            # Get connection for the tab
            conn = await self._get_connection(tab)

            # Enable required domains
            await conn.send("Runtime.enable")
            await conn.send("Page.enable")

            # Execute spoofing scripts directly via Runtime.evaluate
            # This ensures they run on the already-loaded page
            
            # 1. Stealth script
            if self._stealth:
                if self._stealth_script is None:
                    self._stealth_script = self._load_script("stealth.js")
                logger.debug("Executing stealth script via Runtime.evaluate")
                result = await conn.send(
                    "Runtime.evaluate",
                    params={
                        "expression": self._stealth_script,
                        "returnByValue": False,
                        "userGesture": True,
                    },
                )
                if error := parse_cdp_error(result, "Runtime.evaluate (Stealth)"):
                    logger.warning(f"Stealth script execution failed: {error.message}")

            # 2. WebRTC spoofing script
            if self._webrtc_spoof:
                if self._webrtc_spoof_script is None:
                    self._webrtc_spoof_script = self._load_script("webrtc_spoof.js")
                logger.debug("Executing WebRTC spoofing script via Runtime.evaluate")
                result = await conn.send(
                    "Runtime.evaluate",
                    params={
                        "expression": self._webrtc_spoof_script,
                        "returnByValue": False,
                        "userGesture": True,
                    },
                )
                if error := parse_cdp_error(result, "Runtime.evaluate (WebRTC)"):
                    logger.warning(f"WebRTC spoof script execution failed: {error.message}")

            # 3. Media spoofing script
            if self._media_spoof:
                if self._media_spoof_script is None:
                    self._media_spoof_script = self._load_script("media_spoof.js")
                logger.debug("Executing media spoofing script via Runtime.evaluate")
                result = await conn.send(
                    "Runtime.evaluate",
                    params={
                        "expression": self._media_spoof_script,
                        "returnByValue": False,
                        "userGesture": True,
                    },
                )
                if error := parse_cdp_error(result, "Runtime.evaluate (Media)"):
                    logger.warning(f"Media spoof script execution failed: {error.message}")

            # 4. WebGL spoofing script
            if self._webgl_spoof:
                if self._webgl_spoof_script is None:
                    self._webgl_spoof_script = self._load_script("webgl_spoof.js")
                logger.debug("Executing WebGL spoofing script via Runtime.evaluate")
                result = await conn.send(
                    "Runtime.evaluate",
                    params={
                        "expression": self._webgl_spoof_script,
                        "returnByValue": False,
                        "userGesture": True,
                    },
                )
                if error := parse_cdp_error(result, "Runtime.evaluate (WebGL)"):
                    logger.warning(f"WebGL spoof script execution failed: {error.message}")

            # 5. Font spoofing script
            if self._font_spoof:
                if self._font_spoof_script is None:
                    self._font_spoof_script = self._load_script("font_spoof.js")
                logger.debug("Executing font spoofing script via Runtime.evaluate")
                result = await conn.send(
                    "Runtime.evaluate",
                    params={
                        "expression": self._font_spoof_script,
                        "returnByValue": False,
                        "userGesture": True,
                    },
                )
                if error := parse_cdp_error(result, "Runtime.evaluate (Font)"):
                    logger.warning(f"Font spoof script execution failed: {error.message}")

            logger.info("All spoofing scripts executed successfully via Runtime.evaluate")
            return True

        except Exception as e:
            logger.error(f"Failed to inject spoofing scripts: {e}")
            return False