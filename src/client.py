#!/usr/bin/env python3

# Import section
import threading
import pygame
from pygame.locals import *
import sys
import socket
import json
import time
import errno
from venom import *
import os
import ssl

# Server and its address configuration
SERVER_ADDRESS = "20.93.184.26" # IPv4 address
SERVER_PORT = 10000             # server port

# Player name
MYNAME = ""

# Points
def drawPoints(player1_points, player2_points):
    # Clear HUD
    pygame.draw.rect(DISPLAY, BLACK,
                     (72, SIZE_Y * POINT_SIZE, (SIZE_X * POINT_SIZE) / 2 - 72, 32))
    pygame.draw.rect(DISPLAY, BLACK,
                     (72 + (SIZE_X * POINT_SIZE) / 2, SIZE_Y * POINT_SIZE,
                      (SIZE_X * POINT_SIZE) - 72 - (SIZE_X * POINT_SIZE) / 2, 32))
    # Prepare and display points
    P1_PT = font.render(str(player1_points).zfill(8), True, WHITE)
    DISPLAY.blit(P1_PT, (74, SIZE_Y * POINT_SIZE + 2))
    P2_PT = font.render(str(player2_points).zfill(8), True, WHITE)
    DISPLAY.blit(P2_PT, (74 + (SIZE_X * POINT_SIZE) / 2, SIZE_Y * POINT_SIZE + 2))

# Connecting
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setblocking(1)
SERVER = (SERVER_ADDRESS, SERVER_PORT)
sock.connect(SERVER)

# SSL context creation
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.verify_mode = ssl.CERT_REQUIRED
context.load_verify_locations('server.pem')
context.load_cert_chain(certfile="client.pem", keyfile="client.key")

if ssl.HAS_SNI:
    secure_sock = context.wrap_socket(sock, server_side=False, server_hostname=SERVER[0])
else:
    secure_sock = context.wrap_socket(sock, server_side=False)

cert = secure_sock.getpeercert()

if not cert or ('commonName', 'SNAKE') not in cert['subject'][5]:
    raise Exception("ERROR")

sock = secure_sock

# Drawing food
def drawFood(x, y, color):
    pygame.draw.circle(DISPLAY, color, (x * POINT_SIZE + POINT_SIZE / 2, y * POINT_SIZE + POINT_SIZE / 2),
                       POINT_SIZE / 2)

# Drawing snake
def generateSnake(snakeData, color):
    for point in snakeData:
        pygame.draw.rect(DISPLAY, color, (point[0] * POINT_SIZE, point[1] * POINT_SIZE, POINT_SIZE, POINT_SIZE))

# Additional variables
lastData = None

# Simple message composer
def composeMessage(message_type=None, nickname=None, user_id=None, \
                   game_name=None, game_id=None, d=None):
    header = Header(sender=1, message_type=message_type)
    body = Body()
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
    sock.write(message)

# Properly getting messages
def getMessage(returnNone=False):
    unpacked = None
    try:
        data = b''
        while not data:
            data = sock.read(1024)
        unpacked = Message.from_bytes(data)
    except socket.timeout as e:
        print("error")
        if returnNone:
            return None
        else:
            pass
    return unpacked

# Checks if message indicates successful operation
def messageOK(message):
    # return message.body.data["operation_success"]
    return True

# Checks if message has expected type
def messageType(message, message_type):
    return message.header.message_type == message_type

# ID variables
USER_ID = 0
GAME_ID = 0

# Console part - managing nicks, games and joins

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

# Listing current games loop
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

# PyGame initialization
pygame.init()

# Frames Per Second configuration (PyGame)
FPS = 30
FramePerSec = pygame.time.Clock()

# Game size (defines window size; PyGame)
SIZE_X = 25
SIZE_Y = 25
POINT_SIZE = 24

# Colors (PyGame)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
P1_C = (127, 255, 127)
P2_C = (127, 127, 255)
FOOD_COLOR = (255, 127, 0)

# Creating window (PyGame)
DISPLAY = pygame.display.set_mode((SIZE_X * POINT_SIZE, SIZE_Y * POINT_SIZE + 16))
DISPLAY.fill(WHITE)
pygame.display.set_caption("Snake Client")

# Fonts configuration (PyGame)
font = pygame.font.SysFont("Courier", 12)

# Adding HUD (PyGame)
pygame.draw.rect(DISPLAY, (0, 0, 0), (0, SIZE_Y * POINT_SIZE, SIZE_X * POINT_SIZE, SIZE_Y * POINT_SIZE + 16))
PLAYER1 = font.render("Player 1: ", True, P1_C)
DISPLAY.blit(PLAYER1, (2, SIZE_Y * POINT_SIZE + 2))
PLAYER2 = font.render("Player 2: ", True, P2_C)
DISPLAY.blit(PLAYER2, (2 + (SIZE_X * POINT_SIZE) / 2, SIZE_Y * POINT_SIZE + 2))

# Main game loop (PyGame)
last_key = "r"  # default selected snake's direction
last_update = time.time()

# Additional variable for checking game exit
endGame = False

# Function for checking last pressed key
def check_last_pressed_key(last_key):
    global endGame
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                return "l"
            elif event.key == pygame.K_RIGHT:
                return "r"
            elif event.key == pygame.K_UP:
                return "u"
            elif event.key == pygame.K_DOWN:
                return "d"
            elif event.key == pygame.K_ESCAPE:
                endGame = True
    return last_key

# Additional variable
last_last_key = ""

# Main PyGame loop
while True:
    now = time.time()
    last_key = check_last_pressed_key(last_key)
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sock.close()
            sys.exit()
    out = composeMessage(MessageType.SEND_MOVE, user_id=USER_ID, game_id=GAME_ID, d=last_key.encode())
    sendMessage(out)
    if endGame:
        out = composeMessage(MessageType.EXIT_GAME_CLIENT, user_id=USER_ID, game_id=GAME_ID)
        sendMessage(out)
        inp = getMessage()
        if messageType(inp, MessageType.EXIT_GAME_SERVER):
            if messageOK(inp):
                break
            else:
                print("Nie udało się opuścić gry.")
        else:
            print("Uzyskano inny typ odpowiedzi niż oczekiwano. Koniec programu.")
            exit(0)
    pygame.display.update()
    FramePerSec.tick(FPS)
    last_key = check_last_pressed_key(last_key)
    inp = getMessage(True)
    try:
        input = inp.body.data
    except:
        input = lastData
    last_key = check_last_pressed_key(last_key)
    if True:
        if input != None:
            if lastData != None:
                generateSnake(lastData["p1_snake"], WHITE)
                generateSnake(lastData["p2_snake"], WHITE)
                drawFood(lastData["food"][0], lastData["food"][1], WHITE)
                lastData = input
            else:
                lastData = input
            generateSnake(input["p1_snake"], P1_C)
            generateSnake(input["p2_snake"], P2_C)
            drawFood(input["food"][0], input["food"][1], FOOD_COLOR)
            drawPoints(input["pt1"], input["pt2"])
            try:
                if is_player_1 and input['p1_over'] == 1:
                    break
                if not is_player_1 and input['p2_over'] == 1:
                    break
            except:
                print("error")
            last_update = time.time()

if input["p1_over"] or input["p2_over"]:
    print("Przegrana! ", end="")

if is_player_1:
    print("Punkty:", input["pt1"])
else:
    print("Punkty:", input["pt2"])
