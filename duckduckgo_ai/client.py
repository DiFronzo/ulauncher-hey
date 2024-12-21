import httpx
import asyncio
import json
from typing import AsyncGenerator, List, Literal, Dict

STATUS_URL = "https://duckduckgo.com/duckchat/v1/status"
CHAT_URL = "https://duckduckgo.com/duckchat/v1/chat"
STATUS_HEADERS = {"x-vqd-accept": "1"}

# Type aliases for Python
Model = Literal[
    "gpt-4o-mini",
    "claude-3-haiku-20240307",
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "mistralai/Mixtral-8x7B-Instruct-v0.1",
]

ModelAlias = Literal["gpt-4o-mini", "claude-3-haiku", "llama", "mixtral"]

Messages = List[Dict[str, str]]


_model: Dict[str, Model] = {
    "gpt-4o-mini": "gpt-4o-mini",
    "claude-3-haiku": "claude-3-haiku-20240307",
    "llama": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "mixtral": "mistralai/Mixtral-8x7B-Instruct-v0.1",
}


class Chat:
    def __init__(self, vqd: str, model: Model):
        self.old_vqd = vqd
        self.new_vqd = vqd
        self.model = model
        self.messages: Messages = []

    async def fetch(self, content: str) -> httpx.Response:
        """Fetch the original message."""
        self.messages.append({"content": content, "role": "user"})
        payload = {"model": self.model, "messages": self.messages}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                CHAT_URL,
                headers={"x-vqd-4": self.new_vqd, "Content-Type": "application/json"},
                json=payload,
            )
            if response.status_code != 200:
                raise Exception(
                    f"{response.status_code}: Failed to send message. {response.reason_phrase}"
                )
            return response

    async def fetch_full(self, content: str) -> str:
        """Fetch the full message."""
        response = await self.fetch(content)
        text = ""

        async for event in self._parse_stream(response):
            if "message" in event:
                text += event["message"]

        new_vqd = response.headers.get("x-vqd-4")
        self.old_vqd = self.new_vqd
        self.new_vqd = new_vqd

        self.messages.append({"content": text, "role": "assistant"})
        return text

    async def fetch_stream(self, content: str) -> AsyncGenerator[str, None]:
        """Fetch the streaming message."""
        response = await self.fetch(content)
        text = ""

        async for event in self._parse_stream(response):
            if "message" in event:
                data = event["message"]
                text += data
                yield data

        new_vqd = response.headers.get("x-vqd-4")
        self.old_vqd = self.new_vqd
        self.new_vqd = new_vqd

        self.messages.append({"content": text, "role": "assistant"})

    async def _parse_stream(self, response: httpx.Response) -> AsyncGenerator[Dict, None]:
        """Parse the event stream from the response."""
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[len("data: ") :]
                if data != "[DONE]":
                    yield json.loads(data)

    def redo(self):
        """Redo the last action."""
        self.new_vqd = self.old_vqd
        if len(self.messages) >= 2:
            self.messages.pop()
            self.messages.pop()


async def init_chat(model: ModelAlias) -> Chat:
    """Initialize chat."""
    async with httpx.AsyncClient() as client:
        response = await client.get(STATUS_URL, headers=STATUS_HEADERS)
        vqd = response.headers.get("x-vqd-4")
        if not vqd:
            raise Exception(
                f"{response.status_code}: Failed to initialize chat. {response.reason_phrase}"
            )
    return Chat(vqd, _model[model])

async def main():
    chat = await init_chat("gpt-4o-mini")
    response = await chat.fetch_full("Hello!")
    print(response)

asyncio.run(main())
