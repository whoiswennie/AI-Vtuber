class ModelCache:
    def __init__(self):
        self._cache = dict()

    def get(self, model_key: str, model_factory):
        result = self._cache.get(model_key)

        if result is None:
            result = model_factory()
            self._cache[model_key] = result
        return result

    def clear(self):
        self._cache.clear()

# A global cache of models. This is mainly used by the daemon processes to avoid loading the same model multiple times.
GLOBAL_MODEL_CACHE = ModelCache()