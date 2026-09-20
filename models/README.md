# Speech Models

ATLAS uses offline [Vosk](https://alphacephei.com/vosk/) models. This
directory is where a downloaded model is extracted, e.g.:

```
models/
└── vosk-model-small-en-us-0.15/
    ├── am/
    ├── conf/
    └── ...
```

Set `[speech].model_path` in your configuration to the extracted model
directory. Model installation automation arrives in Phase 3 (Atlas.md
section 53, first-run experience); for now, download a model manually from
https://alphacephei.com/vosk/models and point the config at it.

No model is committed to this repository.
