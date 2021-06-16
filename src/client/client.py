#!/usr/bin/env python3

# Import section
import pygame
from pygame.locals import *
import sys
import socket
import json
import time
import errno
# Initialization
pygame.init()

# Frames Per Second configuration
FPS=30
FramePerSec=pygame.time.Clock()

# Game size (defines window size)
SIZE_X=25
SIZE_Y=25
POINT_SIZE=32

# Colors
BLACK=(0,0,0)
WHITE=(255,255,255)
P1_C=(127,255,127)
P2_C=(127,127,255)
FOOD_COLOR=(255,127,0)

# Template server and its address configuration
SERVER_ADDRESS=	"20.86.147.135"
SERVER_PORT=	10000
MYNAME = ""
# Creating window
DISPLAY=pygame.display.set_mode((SIZE_X*POINT_SIZE,SIZE_Y*POINT_SIZE+16))
DISPLAY.fill(WHITE)
pygame.display.set_caption("Snake Client")

# Fonts configuration
font=pygame.font.SysFont("Courier",12)

# Adding HUD
pygame.draw.rect(DISPLAY,(0,0,0),(0,SIZE_Y*POINT_SIZE,SIZE_X*POINT_SIZE,SIZE_Y*POINT_SIZE+16))
PLAYER1=font.render("Player 1: ", True, P1_C)
DISPLAY.blit(PLAYER1,(2,SIZE_Y*POINT_SIZE+2))
PLAYER2=font.render("Player 2: ", True, P2_C)
DISPLAY.blit(PLAYER2,(2+(SIZE_X*POINT_SIZE)/2,SIZE_Y*POINT_SIZE+2))

# Points
def drawPoints(player1_points, player2_points):
	# Clear HUD
	pygame.draw.rect(DISPLAY,BLACK, \
			(72, \
			SIZE_Y*POINT_SIZE, \
			(SIZE_X*POINT_SIZE)/2-72, \
			32))
	pygame.draw.rect(DISPLAY,BLACK, \
			(72+(SIZE_X*POINT_SIZE)/2, \
			SIZE_Y*POINT_SIZE, \
			(SIZE_X*POINT_SIZE)-72-(SIZE_X*POINT_SIZE)/2, \
			32))
	# Prepare and display points
	P1_PT=font.render(str(player1_points).zfill(8),True,WHITE)
	DISPLAY.blit(P1_PT,(74,SIZE_Y*POINT_SIZE+2))
	P2_PT=font.render(str(player2_points).zfill(8),True,WHITE)
	DISPLAY.blit(P2_PT,(74+(SIZE_X*POINT_SIZE)/2,SIZE_Y*POINT_SIZE+2))

# Connecting
sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.2)
SERVER=(SERVER_ADDRESS,SERVER_PORT)

# Draw initial points
drawPoints(0,0)

# Drawing food
def drawFood(x,y,color):
	pygame.draw.circle(DISPLAY,color,(x*POINT_SIZE+POINT_SIZE/2,y*POINT_SIZE+POINT_SIZE/2),POINT_SIZE/2)

# Drawing snake
def generateSnake(snakeData,color):
	for point in snakeData:
		pygame.draw.rect(DISPLAY,color,(point[0]*POINT_SIZE,point[1]*POINT_SIZE,POINT_SIZE,POINT_SIZE))

# Initial message to the server
# sock.sendto("CLIENT".encode(),SERVER)

# Additional variables
lastData=None

# Message composer
def composeMessage(message_type=None, nickname=None, user_id=None, \
					game_name=None, game_id=None, d=None):
	temp={}
	temp["sender"]=1
	if message_type:		
		temp["message_type"]=message_type
	if nickname:
		temp["nickname"]=nickname
	if user_id:
		temp["user_id"]=user_id
	if game_name:
		temp["game_name"]=game_name
	if game_id:
		temp["game_id"]=game_id
	if d:
		temp["d"]= d
	return json.dumps(temp)

# Sending messages
def sendMessage(message):
	sock.sendto(message.encode(),SERVER)

# Properly getting messages
def getMessage():
	try:
		data,address=sock.recvfrom(1024)
		data=data.decode("UTF-8").replace("\'","\"")
	except socket.timeout as e:
		return {"response": 200, "message_type": 20}
	return json.loads(data)

# Checks if message is 200 OK
def messageOK(message):
	try:
		return message["response"]==200
	except:
		return message["success"]==200

# Checks if message has expected type
def messageType(message,message_type):
	return message["message_type"]==message_type

USER_ID=0
GAME_ID=0

# Temporary console part - managing nicks, games and joins

# Nickname input while
while True:
	nick=input("Podaj nick: ")
	MYNAME = nick
	sendMessage(composeMessage(1,nick))
	inp=getMessage()
	if messageType(inp,2):
		if messageOK(inp):
			print("Twoje ID:",inp["user_id"])
			USER_ID=inp["user_id"]
			break
		else:
			print("Wybrany nick jest już zajęty! Wybierz inny.")
	else:
		print("Uzyskano inny typ odpowiedzi niż oczekiwano. Koniec programu.")
		exit(1)

# Gets current game list
while True:
	sendMessage(composeMessage(3,user_id=USER_ID))
	inp=getMessage()
	if messageType(inp,4):
		if messageOK(inp):
			for game in inp["list_of_games"]:
				print(game[0],"\t",\
						game[1],"\t",\
						game[2],"\t",\
						game[3])
		else:
			print("Nie udało się uzyskać listy gier. Koniec programu.")
			exit(2)
	else:
		print("Uzyskano inny typ odpowiedzi niż oczekiwano. Koniec programu.")
		exit(1)
	print("\n")
	ch=input("N - nowa gra\tD - dołącz\tQ - wyjdź\t? ")
	ch=ch.upper()
	if(ch=="N"):
		name=input("Nazwa gry: ")
		sendMessage(composeMessage(5,user_id=USER_ID,game_name=name))
		inp2=getMessage()
		if messageType(inp2,6):
			if messageOK(inp2):
				pass
			else:
				print("Nie udało się utworzyć nowej gry.")
		else:
			print("Uzyskano inny typ odpowiedzi niż oczekiwano. Koniec programu.")
			exit(1)
	elif(ch=="D"):
		game_id=int(input("ID gry: "))
		sendMessage(composeMessage(7,user_id=USER_ID,game_id=game_id))
		inp2=getMessage()
		if messageType(inp2,8):
			if messageOK(inp2):
				print("Dołączono do gry #",game_id)
				GAME_ID=game_id
				break
			else:
				print("Nie udało się dołączyć do rozgrywki.")
		else:
			print("Uzyskano inny typ odpowiedzi niż oczekiwano. Koniec programu.")
			exit(1)
	elif(ch=="Q"):
		exit(0)

# Old main game loop
last_key = "r"
last_update = time.time()
while True:
	now = time.time()
	pressed_keys=pygame.key.get_pressed()
	if pressed_keys[K_UP]:
		out=composeMessage(11,user_id=USER_ID,game_id=GAME_ID,d="u")
		last_key = "u"
	elif pressed_keys[K_DOWN]:
		out=composeMessage(11,user_id=USER_ID,game_id=GAME_ID,d="d")
		last_key = "d"
	elif pressed_keys[K_LEFT]:
		out=composeMessage(11,user_id=USER_ID,game_id=GAME_ID,d="l")
		last_key = "l"
	elif pressed_keys[K_RIGHT]:
		out=composeMessage(11,user_id=USER_ID,game_id=GAME_ID,d="r")
		last_key = "r"
	else:
		out = composeMessage(11, user_id=USER_ID, game_id=GAME_ID, d=last_key)
	for event in pygame.event.get():
		if event.type==QUIT:
			pygame.quit()
			sock.close()
			sys.exit()
	print("out", out)
	sendMessage(out)
	pygame.display.update()
	FramePerSec.tick(FPS)
	print("GAME")
	try:
		data, address = sock.recvfrom(1024)
	except socket.timeout as e:
		input = None
	try:
		print(data.decode('utf-8'))
		input = eval(data.decode('utf-8'))["game_state"]
	except:
		input = lastData

	print(input)
	if  now - last_update > 0.1:
		if input != None:
			if lastData != None:
				generateSnake(lastData["p1"], WHITE)
				generateSnake(lastData["p2"], WHITE)
				drawFood(lastData["f"][0], lastData["f"][1], WHITE)
				lastData = input
			else:
				lastData = input
			generateSnake(input["p1"], P1_C)
			generateSnake(input["p2"], P2_C)
			drawFood(input["f"][0], input["f"][1], FOOD_COLOR)
			drawPoints(input["pt"][0], input["pt"][1])
			try:
				if MYNAME == input['player_1'] and input['p1_game_over'] ==1:
					break
				if MYNAME == input['player_2'] and input['p1_game_over'] ==1:
					break
			except:
				print("error")
			last_update = time.time()