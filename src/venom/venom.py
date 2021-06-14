import struct
from enum import Enum


class MessageType(Enum):
    LOGIN_CLIENT = 0x01
    LOGIN_SERVER = 0x02
    LIST_GAMES_CLIENT = 0x03
    LIST_GAMES_SERVER = 0x04
    CREATE_GAME_CLIENT = 0x05
    CREATE_GAME_SERVER = 0x06
    JOIN_GAME_CLIENT = 0x07
    JOIN_GAME_SERVER = 0x08
    EXIT_GAME_CLIENT = 0x09
    EXIT_GAME_SERVER = 0x0a
    SEND_MOVE = 0x0b
    SEND_STATE = 0x0c
    UNKNOWN = 0x0d


class Header:
    @staticmethod
    def from_bytes(header_bytes: bytes):
        sender, message_type = struct.unpack("!bb", header_bytes)
        return Header(sender, MessageType(message_type))
    
    def __init__(self, sender: int, message_type: MessageType):
        self.sender = sender
        self.message_type = message_type

    def to_bytes(self):
        return struct.pack("!bb", self.sender, self.message_type.value)       


class Body:
    @staticmethod
    def from_bytes(
        body_bytes: bytes,
        message_type: MessageType
    ):
        
        body = Body()

        if message_type == MessageType.SEND_MOVE:
            user_id, game_id, move = struct.unpack("!HHc", body_bytes)
            
            body.data["user_id"] = user_id
            body.data["game_id"] = game_id
            body.data["move"] = move

        elif message_type == MessageType.SEND_STATE:
            game_id, p1_direction, p2_direction, food_x, \
            food_y, pt1, pt2, p1_over, p2_over = struct.unpack(
                "!Hcc4H??", body_bytes[:14]
            )
            p1_snake_len, p2_snake_len = struct.unpack("!HH", body_bytes[14:18])
            p1_snake = struct.unpack(
                f"!{p1_snake_len}H", body_bytes[18:(p1_snake_len * 2)+ 18]
            )
            p2_snake = struct.unpack(
                f"!{p2_snake_len}H", 
                body_bytes[
                    (p1_snake_len * 2) + 18: (p2_snake_len * 2) + (p1_snake_len * 2) + 18
                ],
            )

            body.data["game_id"] = game_id
            body.data["p1_direction"] = p1_direction
            body.data["p2_direction"] = p2_direction
            body.data["food"] = (food_x, food_y)
            body.data["pt1"] = pt1
            body.data["pt2"] = pt2
            body.data["p1_over"] = p1_over
            body.data["p2_over"] = p2_over
            body.data["p1_snake"] = p1_snake
            body.data["p2_snake"] = p2_snake


        elif message_type == MessageType.LOGIN_CLIENT:
            nickname_len, = struct.unpack("!B", body_bytes[:1])
            nickname = body_bytes[1:nickname_len + 1].decode("ascii")

            body.data["nickname"] = nickname

        elif message_type == MessageType.LOGIN_SERVER:
            operation_success = True if body_bytes[:1] == b"\x20" else False
            user_id, = struct.unpack("!H", body_bytes[1:3])
            
            body.data["operation_success"] = operation_success
            body.data["user_id"] = user_id

        elif message_type == MessageType.LIST_GAMES_CLIENT:
            pass

        elif messageType == MessageType.LIST_GAMES_SERVER:
            pass

        elif message_type == MessageType.JOIN_GAME_CLIENT:
            user_id, game_id = struct.unpack("!HH", body_bytes)
            
            body.data["user_id"] = user_id
            body.data["game_id"] = game_id

        elif message_type == MessageType.JOIN_GAME_SERVER:
            operation_success = True if body_bytes[:1] == b"\x20" else False

            body.data["operation_success"] = operation_success

        return body

    def __init__(self):
        self.data = {}

    def to_bytes(self, message_type: MessageType) -> bytes:
        if message_type == MessageType.SEND_MOVE:
            return struct.pack(
                "!HHc", 
                self.data["user_id"], 
                self.data["game_id"], 
                self.data["move"],
            )

        elif message_type == MessageType.SEND_STATE:
            response = b""

            response += struct.pack(
                "!Hcc4H??", 
                self.data["game_id"],
                self.data["p1_direction"], 
                self.data["p2_direction"],
                self.data["food"][0],
                self.data["food"][1],
                self.data["pt1"],
                self.data["pt2"],
                self.data["p1_over"],
                self.data["p2_over"],
            )
            response += struct.pack(
                "!HH", len(self.data["p1_snake"]), len(self.data["p2_snake"])
            )
            for i in range(len(self.data["p1_snake"])):
                response += struct.pack("!H", self.data["p1_snake"][i])
            for i in range(len(self.data["p2_snake"])):
                response += struct.pack("!H", self.data["p2_snake"][i])

            return response

        elif message_type == MessageType.LOGIN_CLIENT:
            nickname_len = len(self.data["nickname"])

            return struct.pack("!B", nickname_len) \
                   + self.data["nickname"].encode("ascii")

        elif message_type == MessageType.LOGIN_SERVER:
            response = b"\x20" if self.data["operation_success"] else b"\x50"
            response += struct.pack("!H", self.data["user_id"])

            return response

        elif message_type == MessageType.LIST_GAMES_CLIENT:
            pass

        elif messageType == MessageType.LIST_GAMES_SERVER:
            pass

        elif message_type == MessageType.JOIN_GAME_CLIENT:
            return struct.pack("!HH", self.data["user_id"], self.data["game_id"])

        elif message_type == MessageType.JOIN_GAME_SERVER:
            if self.data["operation_success"]:
                return b"\x20"
            else:
                return b"\x50"


class Message:
    @staticmethod
    def from_bytes(message_bytes: bytes):
        msg = Message(
            header=Header(message_bytes[:2]),
            body=Body.from_bytes(message_bytes[2:])
        )
        
    def __init__(self, header=None, body=None):
        self.header = header
        self.body = body

    def to_bytes(self) -> bytes:
        if self.header is None or self.body is None:
            raise ValueError("Header or body is None.")

        return self.header.to_bytes() + self.body.to_bytes(self.header.message_type)