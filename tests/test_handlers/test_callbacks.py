import pytest
from handlers.booking.callbacks import write_me_handler
from states.booking_states import BookingState

@pytest.mark.asyncio
async def test_write_me_handler(mock_callback, fsm_context):
    await write_me_handler(mock_callback, fsm_context)

    # Состояние изменилось?
    assert await fsm_context.get_state() == BookingState.choosing_day
    # Текст отредактирован?
    mock_callback.message.edit_text.assert_called_once()