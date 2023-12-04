"""Test the Advantage Air Diagnostics."""
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.core import HomeAssistant

from . import add_mock_config

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.usefixtures("mock_get")
async def test_select_async_setup_entry(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    mock_get,
) -> None:
    """Test select platform."""

    entry = await add_mock_config(hass)
    diag = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert diag == snapshot
