from genesis.adapter import Message, Completion


class FakeAdapter:
    def __init__(self, reply: str = "ok"):
        self.reply = reply

    def complete(self, messages: list[Message]) -> Completion:
        return Completion(text=self.reply)
