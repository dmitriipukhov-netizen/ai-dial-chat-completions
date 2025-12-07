import asyncio

from task.clients.base import BaseClient
from task.clients.client import DialClient
from task.clients.custom_client import DialClient as DialCustomClient
from task.constants import DEFAULT_SYSTEM_PROMPT
from task.models.conversation import Conversation
from task.models.message import Message
from task.models.role import Role


COMMAND_EXIT = 'exit'
MODEL = 'gpt-4.1-nano-2025-04-14'


async def start(stream: bool) -> None:
    user_client_input = input("Use custom client? (y/N): ")
    use_custom_client = user_client_input or user_client_input in "Yy"
    client: BaseClient = DialCustomClient(MODEL) if use_custom_client else DialClient(MODEL)

    conversation = Conversation()

    user_system_prompt = input(f'Enter system prompt or leave blank to use default ("{DEFAULT_SYSTEM_PROMPT}"): ')
    system_prompt = user_system_prompt or DEFAULT_SYSTEM_PROMPT
    print(f"System prompt: {system_prompt}")
    client.get_completion([Message(Role.SYSTEM, system_prompt)])

    while True:
        user_input = input("Me: ")
        if user_input == COMMAND_EXIT:
            break

        user_message = Message(Role.USER, user_input)
        conversation.messages.append(user_message)

        print('AI:', end=' ')
        if stream:
            ai_message = await client.stream_completion(conversation.messages)
        else:
            ai_message = client.get_completion(conversation.messages)

        conversation.messages.append(ai_message)


user_stream_input = input("Do you need streaming answers? (Y/n): ")
use_stream_response = not user_stream_input or user_stream_input not in "Nn"
asyncio.run(
    start(stream=use_stream_response)
)
