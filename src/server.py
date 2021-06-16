import socket
from datetime import datetime
import random
import time
from venom import *

class UDPServer:
    games = {}  # list of current games
    users = {}  # "IP": "user ID"
    game_shape = (25, 25)
    queue = {}

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None  # Connection socket

    def printwt(self, msg):
        ''' Print message with current date and time '''

        current_date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{current_date_time}] {msg}')

    def configure_server(self):
        ''' Configure the server '''
        # create UDP socket with IPv4 addressing

        self.printwt('Creating socket...')
        self.printwt('Socket created')
        # bind server to the address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.printwt(f'Binding server to {self.host}:{self.port}...')
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(0.2)
        self.printwt(f'Server binded to {self.host}:{self.port}')

    def handle_request(self, data, client_address):

        ''' Handle the client '''
        # handle request

        req = Message.from_bytes(data)
        self.printwt(f'[ REQUEST from {client_address} ]')
        print('\n', req, '\n')

        req = eval(req)
        if req.header.message_type == MessageType.LOGIN_CLIENT:
            resp = self.register_user(req.data)
        elif req.header.message_type == MessageType.LIST_GAMES_CLIENT:
            resp = self.list_games(req.data)
        elif req.header.message_type == MessageType.CREATE_GAME_CLIENT:
            resp = self.create_game(req.data)
        elif req.header.message_type == MessageType.JOIN_GAME_CLIENT:
            resp = self.join_game(req, client_address)
        elif req.header.message_type == MessageType.EXIT_GAME_CLIENT:
            resp = self.exit_game(req.data)
        elif req.header.message_type == MessageType.SEND_MOVE:
            self.store_move(req.data)
            return
        else:
            resp = {
                "sender": 0,
                "message_type": 12}
        # send response to the client

        self.printwt(f'[ RESPONSE to {client_address} ]')
        self.sock.sendto(resp, client_address)

    def wait_for_client(self):
        """ Wait for a client """
        try:
            # receive message from a client

            data, client_address = self.sock.recvfrom(1024)
            # handle client's request

            self.handle_request(data, client_address)

        except socket.timeout as e:
            pass

    def shutdown_server(self):
        """ Shutdown the server """

        self.printwt('Shutting down server...')
        self.sock.close()

    def register_user(self, data):
        nickname = data["nickname"]
        if nickname not in self.users.values():
            user_id = self.get_new_user_id()
            if user_id != -1:
                self.users[user_id] = nickname
                header = Header(sender=0, message_type=MessageType.LOGIN_SERVER)
                body = Body()
                body.data["operation_success"] = b'\x20'
                body.data["user_id"] = user_id
                message = Message(header=header, body=body)
                return message.to_bytes()

        body = Body()
        header = Header(sender=0, message_type=MessageType.LOGIN_SERVER)
        body.data["operation_success"] = b'\x50'
        message = Message(header=header, body=body)
        return message.to_bytes()

    def list_games(self, req):
        if req["user_id"] not in self.users.keys():
            return {
                "sender": 0,
                "message_type": 4,
                "response": 500
            }

        game_info_list = []
        for game_id in self.games:
            can_join = 1 if self.games[game_id]["players_num"] < 2 else 0
            game_name = self.games[game_id]["game_name"]
            game_info_list.append([game_id, can_join, len(game_name), game_name])

        return {
            "sender": 0,
            "message_type": 4,
            "number_of_games": len(game_info_list),
            "list_of_games": game_info_list,
            "response": 200
        }

    def join_game(self, req, client_address):
        game_id = req["game_id"]
        if self.games[game_id]["players_num"] < 2:
            if self.games[game_id]["player_1"] == "":
                self.games[game_id]["player_1"] = self.users[req["user_id"]]
                self.games[game_id]["p1"].append([5, 5])
            else:
                self.games[game_id]["player_2"] = self.users[req["user_id"]]
                self.games[game_id]["p2"].append([15, 15])

            self.games[game_id]["players_num"] += 1

            try:
                self.queue[game_id][1].append(client_address)
            except KeyError:
                self.queue[game_id] = [time.time(), [client_address]]

            header = Header(sender=0, message_type=MessageType.JOIN_GAME_SERVER)
            body = Body()
            body.data["operation_success"] = b'\x20'
            message = Message(header=header, body=body)
            return message.to_bytes()
        else:
            header = Header(sender=0, message_type=MessageType.JOIN_GAME_SERVER)
            body = Body()
            body.data["operation_success"] = b'\x50'
            message = Message(header=header, body=body)
            return message.to_bytes()

    def exit_game(self, req):
        game_id = req["game_id"]

        if self.games[game_id]["player_1"] == self.users[req["user_id"]]:
            self.games[game_id]["player_1"] = ""
        else:
            self.games[game_id]["player_2"] = ""

        self.games[game_id]["players_num"] -= 1

        return {
            "sender": 0,
            "message_type": 10,
            "response": 200,
        }

    def game_state(self, game_id):
        if game_id in self.games.keys():
            return {
                "sender": 0,
                "message_type": 12,
                "game_state": self.games[game_id],
                "response": 200
            }
        else:
            return {
                "sender": 0,
                "message_type": 12,
                "response": 500
            }

    def check_gameover(self, game_id):
        if self.games[game_id]["players_num"] == 2 and self.games[game_id]["p1_game_over"] and self.games[game_id]["p2_game_over"]:
            return True
        elif self.games[game_id]["players_num"] == 1 and (self.games[game_id]["p1_game_over"] or self.games[game_id]["p2_game_over"]):
            return True
        return False

    def create_game(self, req):
        game_id = self.get_new_game_id()
        if game_id != -1:
            self.games[game_id] = {
                "game_name": req["game_name"],
                "players_num": 0,
                "player_1": "",
                "player_2": "",
                "d1": "r",
                "d2": "l",
                "p1": [], # dodałem te dwie linijki, bo inaczej
                "p2": [], # serwer sypał się przy dołączaniu
                "f": (10, 10),
                "pt": [0, 0],
                "p1_game_over": 0,
                "p2_game_over": 0
            }
            header = Header(sender=0, message_type=MessageType.CREATE_GAME_SERVER)
            body = Body()
            body.data["operation_success"] = b'\x20'
            body.data["game_id"] = game_id
            message = Message(header=header, body=body)
            return message.to_bytes()

        else:
            header = Header(sender=0, message_type=MessageType.CREATE_GAME_SERVER)
            body = Body()
            body.data["operation_success"] = b'\x50'
            message = Message(header=header, body=body)
            return message.to_bytes()

    def get_new_game_id(self):
        games_ids = self.games.keys()
        for new_game_id in range(10000, 2 ** 16):
            if new_game_id not in games_ids:
                return new_game_id

        return -1

    def get_new_user_id(self):
        users_ids = self.users.keys()
        for new_user_id in range(10000, 2 ** 16):
            if new_user_id not in users_ids:
                return new_user_id

        return -1

    def store_move(self, req):
        game_id = req["game_id"]
        current_game = self.games[game_id]
        print(current_game)
        if current_game["player_1"] == self.users[req["user_id"]]:
            #if not self.direction_problem(req["d"], current_game["d1"]):
            current_game["d1"] = req["d"]
        elif current_game["player_2"] == self.users[req["user_id"]]:
            #if not self.direction_problem(req["d"], current_game["d2"]):
            current_game["d2"] = req["d"]

    @staticmethod
    def direction_problem(old_direction, new_direction):
        if old_direction == "" or new_direction == "":
            return False
        if (old_direction == "u" and new_direction == "d") or (old_direction == "d" and new_direction == "u"):
            return True
        elif (old_direction == "r" and new_direction == "l") or (old_direction == "l" and new_direction == "r"):
            return True
        return False

    def process_game(self, game_id):

        curr_game = self.games[game_id]
        s1 = curr_game["p1"]
        s2 = curr_game["p2"]
        d1 = curr_game["d1"]
        d2 = curr_game["d2"]
        food = curr_game["f"]

        p1_eat_food, p2_eat_food, new_food = self.check_food(s1, s2, food)
        if p1_eat_food:
            curr_game["pt"][0] += 10
        if p2_eat_food:
            curr_game["pt"][1] += 10
        if s1:
            s1 = self.move_snake(s1, d1, p1_eat_food)
        if s2:
            s2 = self.move_snake(s2, d2, p2_eat_food)

        p1_collision, p2_collision = self.check_collisions(s1, s2)

        curr_game["p1"] = s1
        curr_game["p2"] = s2
        curr_game["f"] = new_food
        curr_game["p1_game_over"] = p1_collision
        curr_game["p2_game_over"] = p2_collision

        self.games[game_id] = curr_game

    @staticmethod
    def move(point, direction):
        if direction == "r":
            return point[0]+1, point[1]
        elif direction == "l":
            return point[0]-1, point[1]
        elif direction == "d":
            return point[0], point[1]+1
        elif direction == "u":
            return point[0], point[1]-1

    def move_snake(self, snake, direction, eat_food):
        new_head = self.move(snake[0], direction)
        snake.insert(0, new_head)

        if not eat_food:
            snake = snake[:-1]

        return snake

    def check_collisions(self, s1, s2):
        p1_collision, p2_collision = 0, 0
        print(s1, s2)
        if s1:
            if s1[0][0] < 0 or s1[0][0] > self.game_shape[0] or s1[0][1] < 0 or s1[0][1] > self.game_shape[1]:
                p1_collision = 1
        if s2:
            if s2[0][0] < 0 or s2[0][0] > self.game_shape[0] or s2[0][1] < 0 or s2[0][1] > self.game_shape[1]:
                p2_collision = 1
        if s1:
            if s1[0] in s2:
                p1_collision = 1
        if s2:
            if s2[0] in s1:
                p2_collision = 1
        return p1_collision, p2_collision

    def check_food(self, s1, s2, food):

        while True:
            new_food = (random.randint(0, self.game_shape[0]-1), random.randint(0, self.game_shape[0]-1))
            if new_food not in s1 and new_food not in s2:
                break
        if s1:
            if s1[0] == food:
                return True, False, new_food
        if s2:
            if s2[0] == food:
                return False, True, new_food

        return False, False, food

    def check_games(self):
        now = time.time()
        for game_id in self.queue.keys():
            recive_time, hosts = self.queue[game_id]
            if now - recive_time > 0.05:
                print("-----------IF--------------------")
                self.process_game(game_id)
                resp = self.game_state(game_id)

                for host in hosts:
                    self.sock.sendto(resp.encode('utf-8'), host)
                try:
                    self.queue[game_id][0] = time.time()
                except KeyError:
                    continue
            else:
                print("---------------ELSE---------------")

        to_remove = []
        for game_id in self.queue.keys():
            if self.check_gameover(game_id):
                to_remove.append(game_id)

        for game_id in to_remove:
            del self.games[game_id]
            del self.queue[game_id]


def main():
    """ Create a UDP Server and handle multiple clients simultaneously """

    udp_server_multi_client = UDPServer('0.0.0.0', 10000)
    udp_server_multi_client.configure_server()
    while True:
        udp_server_multi_client.wait_for_client()
        udp_server_multi_client.check_games()


if __name__ == '__main__':
    main()