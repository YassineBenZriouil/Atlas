"""Typed configuration schema. Mirrors Atlas.md section 35 categories."""

from __future__ import annotations

from dataclasses import dataclass, field

CURRENT_CONFIG_VERSION = 1


@dataclass
class AudioConfig:
    device: str = "default"
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class SpeechConfig:
    engine: str = "vosk"
    model_path: str = ""
    language: str = "en-us"


@dataclass
class WakeConfig:
    phrase: str = "atlas"
    timeout_seconds: float = 8.0


@dataclass
class TTSConfig:
    enabled: bool = False
    voice: str = "default"
    volume: float = 1.0


@dataclass
class ApplicationEntry:
    executable: str = ""
    aliases: list[str] = field(default_factory=list)


@dataclass
class CommandsConfig:
    require_confirmation: bool = True
    disabled: list[str] = field(default_factory=list)


@dataclass
class PluginsConfig:
    enabled: list[str] = field(default_factory=list)
    disabled: list[str] = field(default_factory=list)


@dataclass
class AppearanceConfig:
    show_tray_icon: bool = True
    launch_minimized: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"
    max_bytes: int = 5_000_000
    backup_count: int = 5


@dataclass
class SecurityConfig:
    dangerous_commands_require_confirmation: bool = True


@dataclass
class StartupConfig:
    start_with_windows: bool = False


@dataclass
class AtlasConfig:
    config_version: int = CURRENT_CONFIG_VERSION
    audio: AudioConfig = field(default_factory=AudioConfig)
    speech: SpeechConfig = field(default_factory=SpeechConfig)
    wake: WakeConfig = field(default_factory=WakeConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    applications: dict[str, ApplicationEntry] = field(default_factory=dict)
    folders: dict[str, str] = field(default_factory=dict)
    commands: CommandsConfig = field(default_factory=CommandsConfig)
    plugins: PluginsConfig = field(default_factory=PluginsConfig)
    appearance: AppearanceConfig = field(default_factory=AppearanceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    startup: StartupConfig = field(default_factory=StartupConfig)
