#!/usr/bin/python3
import threading
import time
import socket
import sys

global HOST
global PORT
HOST = '127.0.0.1'
PORT = int(sys.argv[1])

class UserInfo():
	def __init__(self, name, email, password):
		self.name = name
		self.email = email
		self.password = password

User = dict()

conn_pool = []

def init():
	global server
	server = None
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((HOST, PORT))
	server.listen(10)

def client_handle():
	while True:
		conn, addr = server.accept()
		conn_pool.append(conn)
		print("New connection.")
		threads = threading.Thread(target = BBS_handle, args = (conn,))
		threads.setDaemon(True)
		threads.start()

def BBS_handle(conn):
	login_status = False
	login_user = None
	msg = None
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
		if cmd[0] == 'register':
			if len(cmd) != 4:
				msg = 'Usage: register <username> <email> <password>\n'
			else:
				# 參數數量正確，檢查username
				if cmd[1] in User:
					msg = 'Username is already used.\n'
				else:
					tmp_userinfo = UserInfo(cmd[1], cmd[2], cmd[3])
					User[cmd[1]] = tmp_userinfo
					msg = 'Register successfully.\n'
			conn.sendall(msg.encode())

		elif cmd[0] == 'login':
			if len(cmd) != 3:
				msg = 'Usage: login <username> <password>\n'
			else:
				# 參數數量正確，檢查username & passwd & login status
				if login_status == True:
					msg = 'Please logout first.\n'
				else: 
					if cmd[1] in User:
						if cmd[2] == User[cmd[1]].password:
							login_status = True
							login_user = cmd[1]
							msg = 'Welcome, ' + cmd[1] + '.\n'
						else:
							msg = 'Login failed.\n'
					else:
						msg = 'Login failed.\n'
			conn.sendall(msg.encode())
			
		elif cmd[0] == 'whoami':
			if len(cmd) != 1:
				msg = 'Usage: whoami\n'
			else:
				if login_status == False:
					msg = 'Please login first.\n'
				else:
					msg = login_user + '\n'
			conn.sendall(msg.encode())
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
		elif cmd[0] == 'exit':
			conn.close()
			conn_pool.remove(conn)
			break

		else:
			msg = 'Command not found. Your command is ' + cmd[0] + '.\n'
			conn.sendall(msg.encode())

			

if __name__ == "__main__":
	init()
	thread = threading.Thread(target = client_handle)
	thread.setDaemon(True)
	thread.start()
	while True:
		cmd = input()
		if cmd == 'exit':
			break
