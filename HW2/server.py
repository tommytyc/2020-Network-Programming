#!/usr/bin/python3
import threading
import time
import socket
import sys
import os
import sqlite3

global HOST
global PORT
HOST = '127.0.0.1'
PORT = int(sys.argv[1])

conn_pool = []

def Init():
	global server, dbconn, cursor
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((HOST, PORT))
	server.listen(10)
	dbconn = sqlite3.connect('db.sqlite', check_same_thread = False)
	cursor = dbconn.cursor()
	# Create table user(name, email, password)
	cursor.execute(
		"""
			create table if not exists user(
					name text,
					email text,
					password text,
					primary key(name)
			)
		"""
	)
	# Create table board(board_name, moderator)
	cursor.execute(
		"""
			create table if not exists board(
				board_name text,
				moderator text,
				primary key(board_name)
			)
		"""
	)
	# Create table post(id, board_name, title, content, author)
	cursor.execute(
		"""
			create table if not exists post(
				id integer primary key autoincrement,
				board_name text,
				title text,
				content text,
				author text
			)
		"""
	)
	# Create table comment(post_id, comment, commenter)
	cursor.execute(
		"""
			create table if not exists comment(
				post_id integer,
				comment text,
				commenter text
			)
		"""
	)
	

def HandleClient():
	while True:
		conn, addr = server.accept()
		conn_pool.append(conn)
		print("New connection.")
		threads = threading.Thread(target = HandleBBS, args = (conn,))
		threads.setDaemon(True)
		threads.start()

def CheckUserExist(name):
	cursor.execute(" select * from user where name = ? ", (name,))
	tmp = cursor.fetchall()
	if tmp != []:
		return True
	else:
		return False

def CreateUser(name, email, passwd):
	cursor.execute(" insert into user(name, email, password) values(?, ?, ?) ", (name, email, passwd))
	dbconn.commit()

def GetUser(name):
	cursor.execute(" select * from user where name = ? ", (name,))
	return cursor.fetchone()

def CheckBoardExist(board_name):
	cursor.execute("select * from board where board_name = ?", (board_name,))
	tmp = cursor.fetchall()
	if tmp != []:
		return True
	else:
		return False

def CreateBoard(board_name, moderator):
	cursor.execute("insert into board(board_name, moderator) values(?, ?)", (board_name, moderator))
	dbconn.commit()

def HandleCommand(conn, cmd, login_status, login_user):
	msg = None
	if cmd[0] == 'register':
		if len(cmd) != 4:
			msg = 'Usage: register <username> <email> <password>\n'
		else:
			if CheckUserExist(cmd[1]):
				msg = 'Username is already used.\n'
			else:
				CreateUser(cmd[1], cmd[2], cmd[3])
				msg = 'Register successfully.\n'
		conn.sendall(msg.encode())
		return login_status, login_user, False

	elif cmd[0] == 'login':
		if len(cmd) != 3:
			msg = 'Usage: login <username> <password>\n'
		else:
			# 參數數量正確，檢查username & passwd & login status
			if login_status == True:
				msg = 'Please logout first.\n'
			else: 
				if CheckUserExist(cmd[1]):
					user = GetUser(cmd[1])
					if cmd[2] == user[2]:
						login_status = True
						login_user = cmd[1]
						msg = 'Welcome, ' + cmd[1] + '.\n'
					else:
						msg = 'Login failed.\n'
				else:
					msg = 'Login failed.\n'
		conn.sendall(msg.encode())
		return login_status, login_user, False
		
	elif cmd[0] == 'whoami':
		if len(cmd) != 1:
			msg = 'Usage: whoami\n'
		else:
			if login_status == False:
				msg = 'Please login first.\n'
			else:
				msg = login_user + '\n'
		conn.sendall(msg.encode())
		return login_status, login_user, False

	elif cmd[0] == 'logout':
		if len(cmd) != 1:
			msg = 'Usage: logout\n'
		else:
			if login_status == False:
				msg = 'Please login first.\n'
			else:
				msg = 'Bye, ' + login_user + '.\n'
				login_user = None
				login_status = False
		conn.sendall(msg.encode())
		return login_status, login_user, False

	elif cmd[0] == 'create-board':
		if len(cmd) != 2:
			msg = 'Usage: create-board <name>\n'
		else:
			if login_status == False:
				msg = 'Please login first.\n'
			else:
				if CheckBoardExist(cmd[1]):
					msg = 'Board is already exist.\n'
				else:
					CreateBoard(cmd[1], login_user)
					msg = 'Create board successfully.\n'
		conn.sendall(msg.encode())
		return login_status, login_user, False

	elif cmd[0] == 'exit':
		conn.close()
		conn_pool.remove(conn)
		return login_status, login_user, True

	else:
		msg = 'Command not found. Your command is ' + cmd[0] + '.\n'
		conn.sendall(msg.encode())
		return login_status, login_user, False

def HandleBBS(conn):
	login_status = False
	login_user = None
	exitornot = False
	conn.sendall(b"********************************\n")
	conn.sendall(b"** Welcome to the BBS server. **\n")
	conn.sendall(b"********************************\n")
	while True:
		conn.sendall(b'% ')
		data = conn.recv(1024)
		if len(data) == 0:
			conn.close()
			conn_pool.remove(conn)
			break
		cmd = str(data.decode().strip())
		cmd = str(cmd).split(' ', -1)
		login_status, login_user, exitornot = HandleCommand(conn, cmd, login_status, login_user)
		if exitornot:
			break

if __name__ == "__main__":
	Init()
	thread = threading.Thread(target = HandleClient)
	thread.setDaemon(True)
	thread.start()
	while True:
		cmd = input()
		if cmd == 'exit':
			break
	dbconn.close()
	os.remove(str(os.getcwd() + '/db.sqlite'))
