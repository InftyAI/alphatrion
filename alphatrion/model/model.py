from alphatrion.runtime.runtime import Runtime


class Model:
    def __init__(self, runtime: Runtime):
        self._runtime = runtime

    def create(
        self,
        name: str,
        project_id: str,
        description: str | None = None,
        meta: dict | None = None,
    ):
        return self._runtime._metadb.create_model(
            name=name,
            project_id=project_id,
            description=description,
            meta=meta,
        )

    def update(self, model_id: int, **kwargs):
        self._runtime._metadb.update_model(model_id=model_id, **kwargs)

    def get(self, model_id: int):
        return self._runtime._metadb.get_model(model_id=model_id)

    def list(self, page: int = 0, page_size: int = 10):
        return self._runtime._metadb.list_models(page=page, page_size=page_size)

    def delete(self, model_id: int):
        self._runtime._metadb.delete_model(model_id=model_id)
