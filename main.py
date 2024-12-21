import logging
import asyncio
from duckduckgo_ai import client as ddg

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction


logger = logging.getLogger(__name__)

class HeyExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    def get_hey_headers(self):
        headers = {}
        if self.preferences["hey_headers"]:
            for header in self.preferences["hey_headers"].split(","):
                header_key, header_value = header.split(":")
                headers[header_key.strip()] = header_value.strip()
        return headers

    def list_models(self):
        models = []

        models = list(ddg.ModelAlias.__args__)

        if not models:
            raise heyException("Error connecting to DDG.")

        return models

    async def generate(self, event):

        logger.info(event)

        chat = await ddg.init_chat(event['model'])
        response = await chat.fetch_full(f"""
        system prompt: {self.preferences['hey_system_prompt']}
        prompt: {event['query']}                                
        """)

        logger.debug(response)

        return response

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        # event is instance of ItemEnterEvent

        query = event.get_data()
        logger.debug(query)
        # do additional actions here...
        response = asyncio.run(extension.generate(query))

        logger.debug(response)

        # you may want to return another list of results
        return RenderResultListAction(
            [
                ExtensionResultItem(
                    icon="images/hey.png", name="hey says..", description=response['response'], on_enter=CopyToClipboardAction(response['response'])
                )
            ]
        )


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        model = event['model']
        query = event.get_query().replace(extension.preferences["hey_kw"] + " ", "")

        items = [
            ExtensionResultItem(
                icon="images/hey.png",
                name="Ask default model...",
                description=query,
                on_enter=ExtensionCustomAction({"query": query, "model": extension.preferences["hey_default_model"]}, keep_app_open=True),
            )
        ]

        items.append(
            ExtensionResultItem(
                icon="images/hey.png",
                name="Ask " + "...",
                description=query,
                on_enter=ExtensionCustomAction({"query": query, "model": model}, keep_app_open=True),
            )
        )

        return RenderResultListAction(items)


class heyException(Exception):
    """Exception thrown when there was an error calling the API"""

    pass


if __name__ == "__main__":
    HeyExtension().run()
