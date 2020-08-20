"""Testing utilities."""
import json
from typing import Dict


def get_json(client, path: str) -> Dict:
    """Make a GET call to the given path of the given client.

    This function asserts that the statuscode is between 200 and 300,
    and then loads the data as JSON.
    Args:
        client ([type]): the client to call
        path (str): the path

    Returns:
        Dict: the loaded json
    """
    response = client.get(path)
    assert 200 <= response.status_code < 300
    return json.loads(response.data.decode())
