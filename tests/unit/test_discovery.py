from atlas.config.defaults import default_config
from atlas.config.schema import ApplicationEntry
from atlas.windows.discovery import DiscoveredApp, _slugify, merge_discovered_apps


def test_slugify_strips_non_alphanumerics():
    assert _slugify("CPU-Z MSI") == "cpuzmsi"
    assert _slugify("Windows PowerShell (x86)") == "windowspowershellx86"


def test_merge_fills_in_executable_for_matching_existing_alias():
    config = default_config()
    assert config.applications["discord"].executable == ""

    result = merge_discovered_apps(
        config, [DiscoveredApp(name="Discord", target=r"C:\Discord\Discord.exe")]
    )

    assert config.applications["discord"].executable == r"C:\Discord\Discord.exe"
    assert "Discord" in result.updated
    assert result.added == []


def test_merge_never_overwrites_an_existing_executable():
    config = default_config()
    config.applications["discord"].executable = r"C:\Already\Set.exe"

    result = merge_discovered_apps(
        config, [DiscoveredApp(name="Discord", target=r"C:\Discord\Discord.exe")]
    )

    assert config.applications["discord"].executable == r"C:\Already\Set.exe"
    assert result.updated == []
    assert result.added == []


def test_merge_adds_a_new_entry_for_an_unconfigured_app():
    config = default_config()

    result = merge_discovered_apps(
        config, [DiscoveredApp(name="qBittorrent", target=r"C:\qBittorrent\qbittorrent.exe")]
    )

    assert "qBittorrent" in result.added
    entry = config.applications["qbittorrent"]
    assert entry.executable == r"C:\qBittorrent\qbittorrent.exe"
    assert entry.aliases == ["qbittorrent"]


def test_merge_matches_by_existing_alias_not_just_key():
    """Notepad's curated aliases include "notes"/"note", but the
    discovered app is literally named "Notepad" - matching must go
    through the key too, not just require the discovered name to equal
    one of the aliases."""
    config = default_config()
    assert config.applications["notepad"].executable == ""

    result = merge_discovered_apps(
        config, [DiscoveredApp(name="Notepad", target="uwp:Microsoft.WindowsNotepad!App")]
    )

    assert config.applications["notepad"].executable == "uwp:Microsoft.WindowsNotepad!App"
    assert config.applications["notepad"].aliases == ["notepad", "notes", "note"]
    assert "Notepad" in result.updated


def test_merge_skips_when_slug_collides_without_an_alias_match():
    """Two differently-punctuated names ("My-Tool!!" and a pre-existing
    "mytool" entry with no matching alias) can slugify to the same key.
    The by-alias lookup must miss here (different lowercased text), so
    this specifically exercises the slug-collision guard, not the
    by-alias-match path."""
    config = default_config()
    config.applications["mytool"] = ApplicationEntry(executable=r"C:\existing.exe", aliases=[])
    app_count_before = len(config.applications)

    result = merge_discovered_apps(
        config, [DiscoveredApp(name="My-Tool!!", target=r"C:\discovered.exe")]
    )

    assert config.applications["mytool"].executable == r"C:\existing.exe"
    assert len(config.applications) == app_count_before
    assert result.added == []
    assert result.updated == []
