"""The Windows backend: pywin32/WinRT implementations of every
atlas.platform interface. Only `atlas.platform.get_backend()` imports this
package; everything else goes through the interfaces."""

from __future__ import annotations

from atlas.platform import PlatformBackend


def create_backend() -> PlatformBackend:
    from atlas.platform.win32.applications import Win32ApplicationManager
    from atlas.platform.win32.credentials import CredentialManagerStore
    from atlas.platform.win32.discovery import discover_installed_applications
    from atlas.platform.win32.keyboard import Win32KeyboardController
    from atlas.platform.win32.monitors import Win32MonitorManager
    from atlas.platform.win32.mouse import Win32MouseController
    from atlas.platform.win32.sapi import SapiTranscriber
    from atlas.platform.win32.system import Win32SystemController
    from atlas.platform.win32.voice import WindowsVoiceLoop
    from atlas.platform.win32.windowing import Win32WindowManager

    def windows_voice(app, on_event=None):  # type: ignore[no-untyped-def]
        assert app.config is not None
        return WindowsVoiceLoop(
            app,
            wake_phrase=app.config.wake.phrase,
            listen_timeout_seconds=app.config.wake.timeout_seconds,
            device_id=app.config.audio.device,
            sample_rate=app.config.audio.sample_rate,
            on_event=on_event,
        )

    return PlatformBackend(
        name="win32",
        window_manager=Win32WindowManager,
        monitor_manager=Win32MonitorManager,
        keyboard_controller=Win32KeyboardController,
        mouse_controller=Win32MouseController,
        system_controller=Win32SystemController,
        application_manager=Win32ApplicationManager,
        secret_store=CredentialManagerStore(),
        discover_applications=discover_installed_applications,
        voice_engines={"windows": windows_voice},
        native_transcriber=SapiTranscriber,
    )
