#!/usr/bin/env python3

# Import section
import pygame
from pygame.locals import *
import sys
import socket
import json

# Initialization
pygame.init()

# Frames Per Second configuration
FPS=30
FramePerSec=pygame.time.Clock()

# Game size (defines window size)
SIZE_X=10
SIZE_Y=10
POINT_SIZE=32

# Colors
BLACK=(0,0,0)
WHITE=(255,255,255)
P1_C=(127,255,127)
P2_C=(127,127,255)
FOOD_COLOR=(255,127,0)

# Template server and its address configuration
SERVER_ADDRESS=	"127.0.0.1"
SERVER_PORT=	1987

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
sock.sendto("CLIENT".encode(),SERVER)

# Additional variables
lastData=None

# Main loop
while True:
	data, address=sock.recvfrom(128)
	try:
		input=json.loads(data)
	except:
		input=lastData
	if input!=None:
		if lastData!=None:
			generateSnake(lastData["p1"],WHITE)
			generateSnake(lastData["p2"],WHITE)
			drawFood(lastData["f"][0],lastData["f"][1],WHITE)
			lastData=input
		else:
			lastData=input
		generateSnake(input["p1"],P1_C)
		generateSnake(input["p2"],P2_C)
		drawFood(input["f"][0],input["f"][1],FOOD_COLOR)
		drawPoints(input["pt"][0],input["pt"][1])
	pressed_keys=pygame.key.get_pressed()
	if pressed_keys[K_UP]:
		print("UP")
	if pressed_keys[K_DOWN]:
		print("DOWN")
	if pressed_keys[K_LEFT]:
		print("LEFT")
	if pressed_keys[K_RIGHT]:
		print("RIGHT")
	pygame.display.update()
	for event in pygame.event.get():
		if event.type==QUIT:
			pygame.quit()
			sock.close()
			sys.exit()
	FramePerSec.tick(FPS)
