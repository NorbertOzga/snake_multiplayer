import socket
from datetime import datetime
import random
import time
from venom import *
import threading
from _thread import *
import os
import ssl

games = {}  # list of current games
users = {}  # "IP": "user ID"
game_shape = (25, 25)
queue = {}

class UDPServer:
    game_shape = (25, 25)

    def __init__(self):
        #self.host = host
        #self.port = port
        self.sock = None  # Connection socket
        self.close_sock = False

    def printwt(self, msg):
        ''' Print message with current date and time '''

        current_date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        os.system(f'''echo "[{current_date_time}] {msg}" >> logs.txt''')

    def handle_request(self, data, client_address, sock):
        ''' Handle the client '''
        # handle request
        if not data:
            self.close_sock = True
            return
        req = Message.from_bytes(data)
        self.printwt(f'[ REQUEST from {client_address} "Message type: {req.header.message_type}]')

        if req.header.message_type == MessageType.LOGIN_CLIENT:
            resp = self.register_user(req.body.data)
        elif req.header.message_type == MessageType.LIST_GAMES_CLIENT:
            resp = self.list_games(req.body.data)
        elif req.header.message_type == MessageType.CREATE_GAME_CLIENT:
            resp = self.create_game(req.body.data)
        elif req.header.message_type == MessageType.JOIN_GAME_CLIENT:
            resp = self.join_game(req.body.data, client_address[0])
        elif req.header.message_type == MessageType.EXIT_GAME_CLIENT:
            resp = self.exit_game(req.body.data)
        elif req.header.message_type == MessageType.SEND_MOVE:
            self.store_move(req.body.data)
            self.check_games(req.body.data["game_id"])
            return
        else:
            resp = {
                "sender": 0,
                "message_type": 12
            }
        # send response to the client

        self.printwt(f'[ RESPONSE to {client_address} Message type {resp.header.message_type}]')
        sock.write(resp.to_bytes())
        if self.close_sock:
            sock.close()

    def wait_for_client(self, sock, client_address):
        self.socket = sock
        self.client_address = client_address
        """ Wait for a client """
        while True:
            if self.close_sock:
                break
            # receive message from a client
            data = sock.read(1024)
            # handle client's request

            self.handle_request(data, client_address, sock)

    def shutdown_server(self):
        """ Shutdown the server """
        self.printwt('Shutting down server...')
        self.sock.close()

    def register_user(self, data):
        nickname = data["nickname"]
        if nickname not in users.values():
            user_id = self.get_new_user_id()
            if user_id != -1:
                users[user_id] = nickname
                header = Header(sender=0, message_type=MessageType.LOGIN_SERVER)
                body = Body()
                body.data["operation_success"] = True
                body.data["user_id"] = user_id
                message = Message(header=header, body=body)
                return message

        body = Body()
        header = Header(sender=0, message_type=MessageType.LOGIN_SERVER)
        body.data["operation_success"] = False
        message = Message(header=header, body=body)
        return message

    def list_games(self, data):
        if data["user_id"] not in users.keys():
            body = Body()
            header = Header(sender=0, message_type=MessageType.LIST_GAMES_SERVER)
            body.data["operation_success"] = b'\x50'
            message = Message(header=header, body=body)
            return message

        game_info_list = []

        for game_id in games:
            can_join = 1 if games[game_id]["players_num"] < 2 else 0
            game_name = games[game_id]["game_name"]
            game_info_list.append({"game_id": game_id, "can_join": can_join, "game_name": game_name})

        body = Body()
        header = Header(sender=0, message_type=MessageType.LIST_GAMES_SERVER)
        body.data["operation_success"] = b'\x20'
        body.data["games"] = game_info_list
        message = Message(header=header, body=body)
        return message

    def join_game(self, data, client_address):
        game_id = data["game_id"]
        users[client_address] = game_id
        if games[game_id]["players_num"] < 2:
            if games[game_id]["player_1"] == -1:
                games[game_id]["player_1"] = data["user_id"]
                games[game_id]["p1_snake"].append([5, 5])
                is_player_1 = True
            else:
                games[game_id]["player_2"] = data["user_id"]
                games[game_id]["p2_snake"].append([15, 15])
                is_player_1 = False

            games[game_id]["players_num"] += 1

            try:
                queue[game_id][1].append(client_address)
            except KeyError:
                queue[game_id] = [time.time(), [client_address]]

            header = Header(sender=0, message_type=MessageType.JOIN_GAME_SERVER)
            body = Body()
            body.data["operation_success"] = True
            body.data["is_player_1"] = is_player_1
            message = Message(header=header, body=body)
            return message
        else:
            header = Header(sender=0, message_type=MessageType.JOIN_GAME_SERVER)
            body = Body()
            body.data["operation_success"] = False
            message = Message(header=header, body=body)
            return message

    def exit_game(self, data):
        game_id = data["game_id"]

        if games[game_id]["player_1"] == data["user_id"]:
            games[game_id]["player_1"] = -1
        else:
            games[game_id]["player_2"] = -1

        games[game_id]["players_num"] -= 1
        if games[game_id]["players_num"] == 0:
            del games[game_id]
            del queue[game_id]


        header = Header(sender=0, message_type=MessageType.EXIT_GAME_SERVER)
        body = Body()
        body.data["operation_success"] = True
        message = Message(header=header, body=body)
        return message

    def game_state(self, game_id):

        if games[game_id]["player_1"] == users[self.client_address[0]] and games[game_id]["p1_over"]:
            self.close_sock = True
        elif games[game_id]["player_2"] == users[self.client_address[0]] and games[game_id]["p2_over"]:
            self.close_sock = True

        if game_id in games.keys():
            header = Header(sender=0, message_type=MessageType.SEND_STATE)
            body = Body()
            body.data["operation_success"] = b'\x20'
            body.data["game_id"] = game_id
            body.data["p1_direction"] = games[game_id]["p1_direction"].encode("ascii")
            body.data["p2_direction"] = games[game_id]["p2_direction"].encode("ascii")
            body.data["p1_snake"] = games[game_id]["p1_snake"]
            body.data["p2_snake"] = games[game_id]["p2_snake"]
            body.data["food"] = games[game_id]["food"]
            body.data["pt1"] = games[game_id]["pt1"]
            body.data["pt2"] = games[game_id]["pt2"]
            body.data["players_num"] = games[game_id]["players_num"]
            body.data["p1_over"] = games[game_id]["p1_over"]
            body.data["p2_over"] = games[game_id]["p2_over"]
            message = Message(header=header, body=body)
            return message
        else:
            header = Header(sender=0, message_type=MessageType.SEND_STATE)
            body = Body()
            body.data["operation_success"] = b'\x50'
            message = Message(header=header, body=body)
            return message

    def check_gameover(self, game_id):
        if games[game_id]["players_num"] == 2 and games[game_id]["p1_over"] and games[game_id]["p2_over"]:
            return True
        elif games[game_id]["players_num"] == 1 and (games[game_id]["p1_over"] or games[game_id]["p2_over"]):
            return True
        return False

    def create_game(self, data):
        game_id = self.get_new_game_id()
        if game_id != -1:
            games[game_id] = {
                "game_name": data["game_name"],
                "players_num": 0,
                "player_1": -1,
                "player_2": -1,
                "p1_direction": "r",
                "p2_direction": "l",
                "p1_snake": [],
                "p2_snake": [],
                "food": (10, 10),
                "pt1": 0,
                "pt2": 0,
                "p1_over": 0,
                "p2_over": 0
            }
            header = Header(sender=0, message_type=MessageType.CREATE_GAME_SERVER)
            body = Body()
            body.data["operation_success"] = b'\x20'
            body.data["game_id"] = game_id
            message = Message(header=header, body=body)
            return message

        else:
            header = Header(sender=0, message_type=MessageType.CREATE_GAME_SERVER)
            body = Body()
            body.data["operation_success"] = b'\x50'
            message = Message(header=header, body=body)
            return message

    def get_new_game_id(self):
        games_ids = games.keys()
        for new_game_id in range(10000, 2 ** 16):
            if new_game_id not in games_ids:
                return new_game_id

        return -1

    def get_new_user_id(self):
        users_ids = users.keys()
        for new_user_id in range(10000, 2 ** 16):
            if new_user_id not in users_ids:
                return new_user_id

        return -1

    def store_move(self, data):
        game_id = data["game_id"]
        try:
            current_game = games[game_id]
        except KeyError:
            return

        if current_game["player_1"] == data["user_id"]:
            current_game["p1_direction"] = data["move"].decode("ascii")
        elif current_game["player_2"] == data["user_id"]:
            current_game["p2_direction"] = data["move"].decode("ascii")

    def process_game(self, game_id):

        curr_game = games[game_id]

        s1 = curr_game["p1_snake"]
        s2 = curr_game["p2_snake"]
        d1 = curr_game["p1_direction"]
        d2 = curr_game["p2_direction"]
        food = curr_game["food"]

        p1_eat_food, p2_eat_food, new_food = self.check_food(s1, s2, food)
        if p1_eat_food:
            curr_game["pt1"] += 10
        if p2_eat_food:
            curr_game["pt2"] += 10
        if s1:
            s1 = self.move_snake(s1, d1, p1_eat_food)
        if s2:
            s2 = self.move_snake(s2, d2, p2_eat_food)

        p1_collision, p2_collision = self.check_collisions(s1, s2)

        curr_game["p1_snake"] = s1
        curr_game["p2_snake"] = s2
        curr_game["food"] = new_food
        curr_game["p1_over"] = p1_collision
        curr_game["p2_over"] = p2_collision
        mess = f'''[GAME: {game_id} GAME STATE {games[game_id]}]'''
        self.printwt(mess)
        games[game_id] = curr_game

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
        p1_collision, p2_collision = False, False
        if s1:
            if s1[0][0] < 0 or s1[0][0] > self.game_shape[0] or s1[0][1] < 0 or s1[0][1] > self.game_shape[1]:
                p1_collision = True
        if s2:
            if s2[0][0] < 0 or s2[0][0] > self.game_shape[0] or s2[0][1] < 0 or s2[0][1] > self.game_shape[1]:
                p2_collision = True
        if s1:
            if s1[0] in s2:
                p1_collision = True
        if s2:
            if s2[0] in s1:
                p2_collision = True
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

    def check_games(self, game_id):
        now = time.time()
        recive_time, hosts = queue[game_id]
        if now - recive_time > 0.2:
            self.process_game(game_id)
            resp = self.game_state(game_id)
            self.socket.write(resp.to_bytes())
            try:
                queue[game_id][0] = time.time()
            except KeyError:
                pass
        else:
            resp = self.game_state(game_id)
            self.socket.write(resp.to_bytes())

        to_remove = []
        for game_id in queue.keys():
            if self.check_gameover(game_id):
                to_remove.append(game_id)

        for game_id in to_remove:
            del games[game_id]
            del queue[game_id]
        if self.close_sock:
            self.socket.close()


def main():
    """ Create a UDP Server and handle multiple clients simultaneously """
    mean_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mean_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    mean_socket.bind(('0.0.0.0', 10000))
    mean_socket.listen(2)

    ThreadCount = 0
    #udp_server_multi_client.configure_server()
    while True:
        Client, address = mean_socket.accept()
        secure_sock = ssl.wrap_socket(Client, server_side=True, ca_certs="client.pem", certfile="server.pem",
                                      keyfile="server.key", cert_reqs=ssl.CERT_REQUIRED,
                                      ssl_version=ssl.PROTOCOL_TLSv1_2)
        print('Connected to: ' + address[0] + ':' + str(address[1]))
        cert = secure_sock.getpeercert()
        if not cert or ('commonName', 'SNAKE') not in cert['subject'][5]:
            raise Exception("ERROR")

        udp_server_multi_client = UDPServer()
        start_new_thread(udp_server_multi_client.wait_for_client, (secure_sock, address))

        ThreadCount += 1
        print('Thread Number: ' + str(ThreadCount))


if __name__ == '__main__':
    main()