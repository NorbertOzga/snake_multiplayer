#!/usr/bin/env python3

# Import section
import pygame
from pygame.locals import *
import sys
import socket
import json
import time
import errno
from venom import *

# Server and its address configuration
SERVER_ADDRESS = "20.86.147.135"
SERVER_PORT = 10000
MYNAME = ""


# Points
def drawPoints(player1_points, player2_points):
    # Clear HUD
    pygame.draw.rect(DISPLAY, BLACK, \
                     (72, \
                      SIZE_Y * POINT_SIZE, \
                      (SIZE_X * POINT_SIZE) / 2 - 72, \
                      32))
    pygame.draw.rect(DISPLAY, BLACK, \
                     (72 + (SIZE_X * POINT_SIZE) / 2, \
                      SIZE_Y * POINT_SIZE, \
                      (SIZE_X * POINT_SIZE) - 72 - (SIZE_X * POINT_SIZE) / 2, \
                      32))
    # Prepare and display points
    P1_PT = font.render(str(player1_points).zfill(8), True, WHITE)
    DISPLAY.blit(P1_PT, (74, SIZE_Y * POINT_SIZE + 2))
    P2_PT = font.render(str(player2_points).zfill(8), True, WHITE)
    DISPLAY.blit(P2_PT, (74 + (SIZE_X * POINT_SIZE) / 2, SIZE_Y * POINT_SIZE + 2))


# Connecting
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.1)
SERVER = (SERVER_ADDRESS, SERVER_PORT)


# Draw initial points
# drawPoints(0,0)

# Drawing food
def drawFood(x, y, color):
    pygame.draw.circle(DISPLAY, color, (x * POINT_SIZE + POINT_SIZE / 2, y * POINT_SIZE + POINT_SIZE / 2),
                       POINT_SIZE / 2)


# Drawing snake
def generateSnake(snakeData, color):
    for point in snakeData:
        pygame.draw.rect(DISPLAY, color, (point[0] * POINT_SIZE, point[1] * POINT_SIZE, POINT_SIZE, POINT_SIZE))


# Initial message to the server
# sock.sendto("CLIENT".encode(),SERVER)

# Additional variables
lastData = None


# Message composer
def composeMessage(message_type=None, nickname=None, user_id=None, \
                   game_name=None, game_id=None, d=None):
    header = Header(sender=1, message_type=message_type)
    body = Body()

    temp = {}
    temp["sender"] = 1
    if nickname:
        body.data["nickname"] = nickname
    if user_id:
        body.data["user_id"] = user_id
    if game_name:
        body.data["game_name"] = game_name
    if game_id:
        body.data["game_id"] = game_id
    if d:
        body.data["move"] = d
    message = Message(header=header, body=body)
    return message.to_bytes()


# Sending messages
def sendMessage(message):
    sock.sendto(message, SERVER)


# Properly getting messages
def getMessage(returnNone=False):
    unpacked = None
    try:
        data, address = sock.recvfrom(1024)
        unpacked = Message.from_bytes(data)
    except socket.timeout as e:
        if returnNone:
            return None
        else:
            pass
    return unpacked


# Checks if message is 200 OK
def messageOK(message):
    # print(message.body.data)
    # return message.body.data["operation_success"]
    return True


# Checks if message has expected type
def messageType(message, message_type):
    return message.header.message_type == message_type


USER_ID = 0
GAME_ID = 0

# Temporary console part - managing nicks, games and joins

# Nickname input while
while True:
    nick = input("Podaj nick: ")
    MYNAME = nick
    sendMessage(composeMessage(MessageType.LOGIN_CLIENT, nick))
    inp = getMessage()
    if messageType(inp, MessageType.LOGIN_SERVER):
        if messageOK(inp):
            print("Twoje ID:", inp.body.data["user_id"], "\n")
            USER_ID = inp.body.data["user_id"]
            break
        else:
            print("Wybrany nick jest już zajęty! Wybierz inny.")
    else:
        print("Uzyskano inny typ odpowiedzi niż oczekiwano. Koniec programu.")
        exit(1)

# Gets current game list
while True:
    sendMessage(composeMessage(MessageType.LIST_GAMES_CLIENT, user_id=USER_ID))
    inp = getMessage()
    if messageType(inp, MessageType.LIST_GAMES_SERVER):
        if messageOK(inp):
            print("ID gry\t\tWolna?\t\tNazwa gry")
            print("----------------------------------------")
            for game in inp.body.data["games"]:
                game = list(game.values())
                print(game[0], "\t\t", \
                      "Tak" if game[1] else "Nie", "\t\t", \
                      game[2])
        else:
            print("Nie udało się uzyskać listy gier. Koniec programu.")
            exit(2)
    else:
        print("Uzyskano inny typ odpowiedzi niż oczekiwano. Koniec programu.")
        exit(1)
    print("----------------------------------------")
    ch = input("N - nowa gra\tD - dołącz\tQ - wyjdź\t? ")
    ch = ch.upper()
    if (ch == "N"):
        name = input("Nazwa gry: ")
        sendMessage(composeMessage(MessageType.CREATE_GAME_CLIENT, user_id=USER_ID, game_name=name))
        inp2 = getMessage()
        if messageType(inp2, MessageType.CREATE_GAME_SERVER):
            if messageOK(inp2):
                pass
            else:
                print("Nie udało się utworzyć nowej gry.")
        else:
            print("Uzyskano inny typ odpowiedzi niż oczekiwano. Koniec programu.")
            exit(1)
    elif (ch == "D"):
        game_id = int(input("ID gry: "))
        sendMessage(composeMessage(MessageType.JOIN_GAME_CLIENT, user_id=USER_ID, game_id=game_id))
        inp2 = getMessage()
        if messageType(inp2, MessageType.JOIN_GAME_SERVER):
            if messageOK(inp2):
                print("Dołączono do gry #", game_id)
                GAME_ID = game_id
                is_player_1 = inp2.body.data["is_player_1"]
                break
            else:
                print("Nie udało się dołączyć do rozgrywki.")
        else:
            print("Uzyskano inny typ odpowiedzi niż oczekiwano. Koniec programu.")
            exit(1)
    elif (ch == "Q"):
        exit(0)

# Initialization
pygame.init()

# Frames Per Second configuration
FPS = 30
FramePerSec = pygame.time.Clock()

# Game size (defines window size)
SIZE_X = 25
SIZE_Y = 25
POINT_SIZE = 24
