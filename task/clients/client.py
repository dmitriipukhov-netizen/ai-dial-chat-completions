from typing import cast

from aidial_client import Dial, AsyncDial
from aidial_client.types.chat import ChatCompletionResponse, Message as RequestMessage

from task.clients.base import BaseClient
from task.constants import DIAL_ENDPOINT
from task.models.message import Message
from task.models.role import Role


class DialClient(BaseClient):

    def __init__(self, deployment_name: str):
        super().__init__(deployment_name)
        self._client = Dial(base_url=DIAL_ENDPOINT, api_key=self._api_key)
        self._async_client = AsyncDial(base_url=DIAL_ENDPOINT, api_key=self._api_key)

    def get_completion(self, messages: list[Message]) -> Message:
        completion: ChatCompletionResponse = self._client.chat.completions.create(
            deployment_name=self._deployment_name,
            messages=self._prepare_request_messages(messages),
        )
        choices = completion.choices
        if not choices:
            raise Exception(f"No choices in response found")

        message = Message(Role.AI, choices[0].message.content)
        print(message.content)
        return message

    async def stream_completion(self, messages: list[Message]) -> Message:
        completion = await self._async_client.chat.completions.create(
            deployment_name=self._deployment_name,
            messages=self._prepare_request_messages(messages),
            stream=True
        )

        contents = []
        async for chunk in completion:
            choices = chunk.choices
            if not choices:
                raise Exception(f"No choices in response chunk found")
            choice = choices[0]
            if choice.finish_reason:
                print()
                break
            content = choice.delta.content
            print(content, end='')
            contents.append(content)

        print()

        return Message(Role.AI, ''.join(contents))

    @staticmethod
    def _prepare_request_messages(messages: list[Message]) -> list[RequestMessage]:
        # The return type of task.models.Message.to_dict() is too wide type, "dirty" typecast is needed
        return [cast(RequestMessage, cast(object, m.to_dict())) for m in messages]
