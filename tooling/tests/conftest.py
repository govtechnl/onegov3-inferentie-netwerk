import pytest

from inferentienet.model import load_world


@pytest.fixture(scope="session")
def world():
    return load_world()
