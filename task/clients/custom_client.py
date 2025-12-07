import json
import aiohttp
import requests
from aiohttp import ClientResponseError
from requests import HTTPError

from task.clients.base import BaseClient
from task.constants import DIAL_ENDPOINT
from task.models.message import Message
from task.models.role import Role


class DialClient(BaseClient):
    _endpoint: str
    _api_key: str

    def __init__(self, deployment_name: str):
        super().__init__(deployment_name)
        self._endpoint = DIAL_ENDPOINT + f"/openai/deployments/{deployment_name}/chat/completions"

    def get_completion(self, messages: list[Message]) -> Message:
        request_data = {
            'model': self._deployment_name,
            'messages': self._prepare_request_messages(messages),
        }

        response = requests.post(self._endpoint, headers=self._headers, json=request_data)
        try:
            response.raise_for_status()
        except HTTPError as e:
            raise Exception(f"HTTP {response.status_code}: {response.text}") from e

        resp_data = response.json()
        if not (raw_choices := resp_data.get('choices', [])):
            raise Exception(f"No choices in response found")
        if not (raw_message := raw_choices[0].get('message')):
            raise Exception(f"No message in response found")
        if (raw_role := raw_message.get('role')) not in Role:
            raise Exception(f"Wrong role '{raw_role}'")
        if not (raw_content := raw_message.get('content')):
            raise Exception(f"No content in response found")

        message = Message(Role(raw_role), raw_content)
        print(message.content)

        return message

    async def stream_completion(self, messages: list[Message]) -> Message:
        request_data = {
            'model': self._deployment_name,
            'messages': self._prepare_request_messages(messages),
            'stream': True,
        }

        contents = []

        async with aiohttp.ClientSession() as session:
            async with session.post(self._endpoint, headers=self._headers, json=request_data) as response:
                try:
                    response.raise_for_status()
                except ClientResponseError as e:
                    raise Exception(f"HTTP {response.status}: {response.text}") from e

                resp_chunk = self._parse_stream_chunk(await response.content.readuntil(separator=b'\n\n'))
                raw_chunk = json.loads(resp_chunk)
                if not (raw_choices := raw_chunk.get('choices', [])):
                    raise Exception(f"No choices in response found")
                if (raw_role := raw_choices[0].get('delta', {}).get('role')) not in Role:
                    raise Exception(f"Wrong role '{raw_role}'")
                role = Role(raw_role)

                while resp_chunk_bytes := await response.content.readuntil(separator=b'\n\n'):
                    resp_chunk = self._parse_stream_chunk(resp_chunk_bytes)
                    if resp_chunk == '[DONE]':
                        break
                    raw_chunk = json.loads(resp_chunk)
                    if not (raw_choices := raw_chunk.get('choices', [])):
                        raise Exception("No choices in response found")
                    raw_choice = raw_choices[0]
                    if raw_choice.get('finish_reason') is not None:
                        break
                    if not (raw_delta := raw_choice.get('delta')):
                        print(raw_choices)
                        raise Exception("No delta in response found")
                    if not (raw_content := raw_delta.get('content')):
                        raise Exception("No content in response found")

                    print(raw_content, end='')
                    contents.append(raw_content)
        print('\n')

        return Message(role, ''.join(contents))

    @staticmethod
    def _prepare_request_messages(messages: list[Message]) -> list[dict[str, str]]:
        return [m.to_dict() for m in messages]

    @property
    def _headers(self) -> dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'API-KEY': self._api_key,
        }

    @staticmethod
    def _parse_stream_chunk(chunk: bytes) -> str:
        return chunk.decode('utf-8').strip().removeprefix('data: ')
