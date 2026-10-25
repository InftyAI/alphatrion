import alphatrion.framework
import alphatrion.swarm


def test_import():
    assert alphatrion.swarm.__name__ == "alphatrion.swarm"
    assert alphatrion.framework.init is not None
