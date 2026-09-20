# Third-Party Plugins

Drop a plugin here as either:

- `plugins/<name>/__init__.py` (a package), or
- `plugins/<name>.py` (a single module)

exposing a module-level `PLUGIN_CLASS` that points at a class implementing
`atlas.plugins.base.AtlasPlugin`. See `docs/plugins.md` for the interface and
`tests/fixtures/plugins/` for working examples.

ATLAS discovers and loads everything in this directory at startup. A plugin
that fails to initialize is disabled with a logged reason; it never prevents
ATLAS from starting (Atlas.md section 44).
