import alphatrion as at


def test_log_params():
    at.init(project_id="test_project", artifact_insecure=True)

    with at.CraftExperiment.run(name="test_experiment") as exp:
        params = {"param1": 0.1, "param2": "value2", "param3": 3}
        at.log_params(params=params)

        new_exp = exp._runtime._metadb.get_exp(exp_id=exp._runtime._current_exp_id)
        assert new_exp is not None
        assert new_exp.params == params
