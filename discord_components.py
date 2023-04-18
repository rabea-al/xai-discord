from xai_components.base import InArg, OutArg, InCompArg, Component, xai_component
import discord

import asyncio
import os

@xai_component
class DiscordClientInit(Component):
    """
    Initializes a Discord client with the default intents and enables message content.

    ##### ctx:
    - discord_client: A Discord client instance with the default intents and message content enabled.
    """

    def execute(self, ctx) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            print(f'We have logged in as {client.user}')

        ctx['discord_client'] = client


@xai_component
class DiscordMessageResponder(Component):
    """
    Adds a message responder that listens for a specified trigger message and responds with the specified response.

    ##### inPorts:
    - msg_trigger: The message trigger that the bot listens for.
    - msg_response: The response the bot sends when the trigger is detected.

    ##### ctx:
    - message_responders: A list of tuples containing message triggers and their corresponding responses.
    - on_message_handlers: A list of message handling functions that are called when a message is received.
    """

    msg_trigger: InCompArg[str]
    msg_response: InCompArg[str]

    def execute(self, ctx) -> None:
        client = ctx['discord_client']

        if 'message_responders' not in ctx:
            ctx['message_responders'] = []

        trigger_response = (self.msg_trigger.value, self.msg_response.value)
        ctx['message_responders'].append(trigger_response)

        if 'on_message_handlers' not in ctx:
            ctx['on_message_handlers'] = []

        if 'message_responder' not in ctx:
            async def message_responder(message):
                for trigger, response in ctx['message_responders']:
                    if message.content.startswith(trigger):
                        await message.channel.send(response)
                        break

            ctx['message_responder'] = message_responder
            ctx['on_message_handlers'].append(message_responder)



@xai_component
class DiscordShutdownBot(Component):
    """
    Adds a shutdown command for the Discord bot that can be executed by an administrator.

    ##### inPorts:
    - shutdown_cmd: The command that, when received from an administrator, will shut down the bot.

    ##### ctx:
    - on_message_handlers: A list of message handling functions that are called when a message is received.
    """
    shutdown_cmd: InCompArg[str]

    def execute(self, ctx) -> None:
        client = ctx['discord_client']

        async def shutdown_bot(message):
            if message.content.startswith(self.shutdown_cmd.value) and message.author.guild_permissions.administrator:
                await message.channel.send("Shutting down...")
                await client.close()

        if 'on_message_handlers' not in ctx:
            ctx['on_message_handlers'] = []

        ctx['on_message_handlers'].append(shutdown_bot)


@xai_component
class DiscordDeployBot(Component):
    """
    Deploys the Discord bot using the provided token, running either in Xircuits or as a standalone script.

    ##### inPorts:
    - token: The bot token to be used for authentication.

    ##### ctx:
    - on_message_handlers: A list of message handling functions that are called when a message is received.
    """

    token: InArg[str]

    def execute(self, ctx) -> None:
        client = ctx['discord_client']
        token = os.getenv("DISCORD_BOT_TOKEN") if self.token.value is None else self.token.value

        @client.event
        async def on_message(message):
            if message.author == client.user:
                return

            if 'on_message_handlers' in ctx:
                for handler in ctx['on_message_handlers']:
                    await handler(message)

        if "JPY_PARENT_PID" in os.environ or "jupyter" in os.environ.get("PATH", ""):
            # If running in Jupyter, get the current event loop and run the Discord bot within it
            loop = asyncio.get_event_loop()
            loop.create_task(client.start(token))
        else:
            # If running as a standalone script, use client.run()
            client.run(token)