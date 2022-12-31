#  Copyright 2022 Will Shanks

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at

#      http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""MUD client"""
from select import select
from socket import socket

from rich.console import Console
from rich.text import Text

from textual import events
from textual.app import App
from textual.widgets import Header, ScrollView
from textual_inputs import TextInput

console = Console()

config = {
    "mud_name": "Barren Realms",
    "address": "barrenrealmsmud.com",
    "port": 8000,
}


def connect(address: str, port: int) -> socket:
    """Connect to address

    Args:
        address: address to connect to
        port: port to conect to

    Returns:
        Connected socket object
    """
    sock = socket()
    sock.connect((address, port))
    return sock


class GameView(ScrollView):
    """A view of content received from the MUD server"""

    def __init__(self, sock: socket):
        super().__init__()
        self.socket = sock
        self.text = Text("")
        self.set_interval(1, self.read)

    async def read(self):
        """Read content from the server"""
        raw_msg = b""
        while True:
            ready = select([self.socket], [], [], 0.05)
            if not ready[0]:
                break
            raw_msg += self.socket.recv(4096)
        if not raw_msg:
            return
        try:
            new = raw_msg.decode("ascii")
        except UnicodeDecodeError:
            # If there are terminal codes in the message that do not decode,
            # just fall back to the string representation of the bytes.
            #
            # TODO: handle terminal codes
            new = str(raw_msg)
        pre_y = self.y
        self.text.append(new)
        await self.update(self.text)
        self.y = pre_y
        # pylint: disable=not-callable
        self.animate(
            "y", self.window.virtual_size.height, duration=1, easing="linear"
        )
        # pylint: enable=not-callable


class Input(TextInput):
    """Input box for commands to send to server"""

    def __init__(self, gameview: GameView, sock: socket):
        super().__init__()
        self.gameview = gameview
        self.socket = sock

    async def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            self.socket.sendall((self.value + "\n\r").encode("ascii"))
            pre_y = self.gameview.y
            self.gameview.text.append(self.value + "\n\r")
            await self.gameview.update(self.gameview.text)
            self.gameview.y = pre_y
            self.gameview.animate(
                "y",
                self.gameview.window.virtual_size.height,
                duration=1,
                easing="linear",
            )
            self.value = ""


class MudUI(App):
    """Main application class"""

    async def on_mount(self) -> None:
        """Method called once terminal enters application mode"""
        sock = connect(config["address"], config["port"])
        gameview = GameView(sock)
        input_ = Input(gameview=gameview, sock=sock)

        grid = await self.view.dock_grid(edge="left", name="left")
        grid.add_column(fraction=1, name="u")
        grid.add_row(fraction=1, name="top", min_size=3)
        grid.add_row(fraction=20, name="middle")
        grid.add_row(fraction=1, name="bottom", min_size=3)
        grid.add_areas(area1="u,top", area2="u,middle", area3="u,bottom")
        grid.place(
            area1=Header(),
            area2=gameview,
            area3=input_,
        )


def main():
    """Main entry point of the application"""
    MudUI.run(title=config["mud_name"])
