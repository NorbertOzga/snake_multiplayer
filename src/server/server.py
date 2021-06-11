import socket
from datetime import datetime
import random
import time


class UDPServer:
    games = {}  # list of current games
    users = {}  # "IP": "user ID"
    game_shape = (25, 25)

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
        self.printwt(f'Server binded to {self.host}:{self.port}')

    def handle_request(self, data, client_address):

        ''' Handle the client '''
        # handle request

        req = data.decode('utf-8')
        self.printwt(f'[ REQUEST from {client_address} ]')
        print('\n', req, '\n')

        req = eval(req)
        if req["message_type"] == 1:
            resp = self.register_user(req)
        elif req["message_type"] == 3:
            resp = self.list_games(req)
        elif req["message_type"] == 5:
            resp = self.create_game(req)
        elif req["message_type"] == 7:
            resp = self.join_game(req)
        elif req["message_type"] == 9:
            resp = self.exit_game(req)
        elif req["message_type"] == 11:
            resp = self.game_state(req)
        else:
            resp = {
                "sender": 0,
                "message_type": 12}
        # send response to the client
        resp = str(resp)
        self.printwt(f'[ RESPONSE to {client_address} ]')
        self.sock.sendto(resp.encode('utf-8'), client_address)
        print(self.games)
        print(self.users)
        print('\n', resp, '\n')

    def wait_for_client(self):
        """ Wait for a client """
        try:
            # receive message from a client

            data, client_address = self.sock.recvfrom(1024)
            # handle client's request

            self.handle_request(data, client_address)
        except OSError as err:
            self.printwt(err)

    def shutdown_server(self):
        """ Shutdown the server """

        self.printwt('Shutting down server...')
        self.sock.close()

    def register_user(self, nickname):
        if nickname not in self.users.values():
            user_id = self.get_new_user_id()
            if user_id != -1:
                self.users[user_id] = nickname
                return {
                    "sender": 0,
                    "message_type": 2,
                    "response": 200,
                    "user_id": user_id
                }

        return {
            "sender": 0,
            "message_type": 2,
            "response": 500
        }

    def list_games(self, req):
        if req["user_id"] not in self.users.keys():
            return {
                "sender": 0,
                "message_type": 4,
                "success": 500
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
            "success": 200
        }

    def join_game(self, req):
        game_id = req["game_id"]
        if self.games[game_id]["players_num"] < 2:
            if self.games[game_id]["player_1"] == "":
                self.games[game_id]["player_1"] = self.users[req["user_id"]]
            else:
                self.games[game_id]["player_2"] = self.users[req["user_id"]]

            self.games[game_id]["players_num"] += 1

            return {
                "sender": 0,
                "message_type": 8,
                "response": 200,
            }
        else:
            return {
                "sender": 0,
                "message_type": 8,
                "response": 500,
            }

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

    def game_state(self, req):
        if req["game_id"] in self.games.keys():
            return {
                "sender": 0,
                "message_type": 12,
                "game_state": self.games[req["game_id"]],
                "success": 200
            }
        else:
            return {
                "sender": 0,
                "message_type": 12,
                "success": 500
            }

    def create_game(self, req):
        game_id = self.get_new_game_id()
        if game_id != -1:
            self.games[game_id] = {
                "game_name": req["game_name"],
                "players_num": 0,
                "player_1": "",
                "player_2": ""
            }
            return {
                "sender": 0,
                "message_type": 6,
                "response": 200,
                "game_id": game_id
            }
        else:
            return {
                "sender": 0,
                "message_type": 6,
                "response": 500
            }

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

    " GAME LOGIC "
    '''
    def update_game_state(self, request):
        curr_game = self.games[request["name"]]
        if "d1" in request:
            curr_game["d1"] = request["d1"]
        elif "d2" in request:
            curr_game["d2"] = request["d2"]

        return self.game_loop(request["name"])


    @staticmethod
    def move(point, direction):
        if direction == "u":
            return point[0]+1, point[1]
        elif direction == "d":
            return point[0]-1, point[1]
        elif direction == "r":
            return point[0], point[1]+1
        elif direction == "l":
            return point[0], point[1]-1

    def move_snakes(self, p1, p2, d1, d2, p1_eat_food, p2_eat_food):
        if not p1_eat_food and len(p1) > 1:
            p1 = p1[:-1]
        if not p2_eat_food and len(p2) > 1:
            p2 = p2[:-1]

        head1 = p1[0]
        new_head1 = self.move(head1, d1)
        if len(p1) > 1:
            if new_head1 == p1[1]:
                pass
            else:
                p1.insert(0, new_head1)

        head2 = p2[0]
        new_head2 = self.move(head2, d2)
        if len(p2) > 1:
            if new_head2 == p2[1]:
                pass
            else:
                p2.insert(0, new_head2)

        return p1, p2

    def check_collisions(self, p1, p2):
        p1_collision, p2_collision = 0, 0
        if p1[0][0] < 0 or p1[0][0] > self.game_shape[0] or p1[0][1] < 0 or p1[0][1] > self.game_shape[1]:
            p1_collision = 1
        if p2[0][0] < 0 or p2[0][0] > self.game_shape[0] or p2[0][1] < 0 or p2[0][1] > self.game_shape[1]:
            p2_collision = 1

        if p1[0] in p2:
            p1_collision = 1
        if p2[0] in p1:
            p2_collision = 1
        return p1_collision, p2_collision

    def check_food(self, p1, p2, food):

        while True:
            new_food = (random.randint(0, self.game_shape[0]-1), random.randint(0, self.game_shape[0]-1))
            if new_food not in p1 and new_food not in p2:
                break

        if p1[0] == food:
            return True, False, new_food
        elif p2[0] == food:
            return False, True, new_food

        return False, False, food

    def game_loop(self, game_name):

        curr_game = self.games[game_name]
        p1 = curr_game["p1"]
        p2 = curr_game["p2"]
        d1 = curr_game["d1"]
        d2 = curr_game["d2"]
        food = curr_game["food"]

        p1_eat_food, p2_eat_food, new_food = self.check_food(p1, p2, food)
        #p1, p2 = self.move_snakes(p1, p2, d1, d2, p1_eat_food, p2_eat_food)
        p1_collision, p2_collision = self.check_collisions(p1, p2)

        curr_game["p1"] = p1
        curr_game["p2"] = p2
        curr_game["food"] = new_food
        curr_game["p1_game_over"] = p1_collision
        curr_game["p2_game_over"] = p2_collision

        return str(curr_game)
    '''


def main():
    """ Create a UDP Server and handle multiple clients simultaneously """

    udp_server_multi_client = UDPServer('0.0.0.0', 10000)
    udp_server_multi_client.configure_server()
    while True:
        udp_server_multi_client.wait_for_client()


if __name__ == '__main__':
    main()