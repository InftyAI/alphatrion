import os
import tempfile

import alphatrion as at


def test_sdk():
    at.init(project_id="test_project", artifact_insecure=True)

    with at.CraftExperiment.run(
        name="craft_exp",
        description="test description",
        meta={"key": "value"},
    ) as exp:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            file = "file.txt"
            with open(file, "w") as f:
                f.write("Hello, AlphaTrion!")

            at.log_artifact(paths=file, version="v1")

        versions = exp._runtime._artifact.list_versions("craft_exp")
        assert "v1" in versions
