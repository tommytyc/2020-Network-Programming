#!/usr/bin/python3
import threading
import time
import socket
import sys
import os
import sqlite3
import re
from datetime import date

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
	# Create table post(id, board_name, title, content, author, date)
	cursor.execute(
		"""
			create table if not exists post(
				id integer primary key autoincrement,
				board_name text,
				title text,
				content text,
				author text,
				date text
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

def Write(conn, msg):
	conn.sendall(msg.encode())	

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

def GetBoardList():
	cursor.execute("select * from board")
	return cursor.fetchall()

def CreatePost(board_name, title, content, author, date):
	cursor.execute(" insert into post(board_name, title, content, author, date) values(?, ?, ? ,?, ?) ", (board_name, title, content, author, date))
	dbconn.commit()

def GetPostList(board_name):
	cursor.execute(" select id, title, author, date from post where board_name = ? ", (board_name,))
	return cursor.fetchall()

def GetPost(post_id):
	cursor.execute(" select * from post where id = ? ", (post_id,))
	return cursor.fetchone()

def CheckPostExist(post_id):
	cursor.execute(" select * from post where id = ? ", (post_id,))
	tmp = cursor.fetchall()
	if tmp != []:
		return True
	else:
		return False

def DeletePost(post_id):
	cursor.execute(" delete from post where id = ? ", (post_id,))
	cursor.execute(" delete from comment where post_id = ? ", (post_id,))
	dbconn.commit()

def UpdatePostTitle(post_id, message):
	cursor.execute(" update post set title = ? where id = ? ", (message, post_id))
	dbconn.commit()

def UpdatePostContent(post_id, message):
	cursor.execute(" update post set content = ? where id = ? ", (message, post_id))
	dbconn.commit()

def CreateComment(post_id, comment, commenter):
	cursor.execute(" insert into comment(post_id, comment, commenter) values(?, ?, ?) ", (post_id, comment, commenter))
	dbconn.commit()

def GetPostCommentList(post_id):
	cursor.execute(" select commenter, comment from comment where post_id = ? ", (post_id,))
	return cursor.fetchall()

def GetCommentCount(post_id):
	cursor.execute(" select count(*) from comment where post_id = ? ", (post_id,))
	return cursor.fetchone()

def HandleCommand(conn, cmd, cmd_orig, login_status, login_user):
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
		Write(conn, msg)
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
		Write(conn, msg)
		return login_status, login_user, False
		
	elif cmd[0] == 'whoami':
		if len(cmd) != 1:
			msg = 'Usage: whoami\n'
		else:
			if login_status == False:
				msg = 'Please login first.\n'
			else:
				msg = login_user + '\n'
		Write(conn, msg)
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
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'create-board':
		if len(cmd) != 2:
			msg = 'Usage: create-board <name>\n'
		else:
			if login_status == False:
				msg = 'Please login first.\n'
			else:
				if CheckBoardExist(cmd[1]):
					msg = 'Board already exists.\n'
				else:
					CreateBoard(cmd[1], login_user)
					msg = 'Create board successfully.\n'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'list-board':
		if len(cmd) > 2 or (len(cmd) == 2 and cmd[1][:2] != '##'):
			msg = 'Usage: list-board ##<key>\n'
		elif len(cmd) == 1:
			board_list = GetBoardList()
			msg = 'Index\tName\tModerator\n'
			board_cnt = 0
			for board in board_list:
				board_cnt += 1
				msg += str(board_cnt) + '\t' + board[0] + '\t' + board[1] + '\n'

		elif len(cmd) == 2:
			board_list = GetBoardList()
			msg = 'Index\tName\tModerator\n'
			board_cnt = 0
			key = cmd[1][2:]
			for board in board_list:
				if re.search(key, board[0]) != None:
					board_cnt += 1
					msg += str(board_cnt) + '\t' + board[0] + '\t' + board[1] + '\n'

		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'create-post':
		if login_status == False:
			msg = 'Please login first.\n'
		else:
			cmd_orig_title = cmd_orig.find('--title')
			cmd_orig_content = cmd_orig.find('--content')
			if '--title' in cmd and '--content' in cmd and cmd.index('--title') < cmd.index('--content') and cmd[2] == '--title':
				if login_status == False:
					msg = 'Please login first.\n'
				else:
					if CheckBoardExist(cmd[1]):
						today = str(date.today())
						CreatePost(cmd[1], cmd_orig[cmd_orig_title + 8 : cmd_orig_content].strip(), cmd_orig[cmd_orig_content + 10 :].strip(), login_user, today)
						msg = 'Create post successfully.\n'
					else:
						msg = 'Board does not exist.\n'
			else:
				msg = 'Usage: create-post <board-name> --title <title> --content <content>\n'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'list-post':
		if len(cmd) > 3 or len(cmd) < 2 or (len(cmd) == 3 and cmd[2][:2] != '##'):
			msg = 'Usage: list-post <board-name> ##<key>\n'
		elif len(cmd) == 2:
			if CheckBoardExist(cmd[1]):
				msg = 'ID\tTitle\tAuthor\tDate\n'
				post_list = GetPostList(cmd[1])
				for post in post_list:
					day = post[3].split('-', -1)
					msg += str(post[0]) + '\t' + post[1] + '\t' + post[2] + '\t' + day[1] + '/' + day[2] + '\n'
			else:
				msg = 'Board does not exist.\n'
		elif len(cmd) == 3:
			if CheckBoardExist(cmd[1]):
				msg = 'ID\tTitle\tAuthor\tDate\n'
				post_list = GetPostList(cmd[1])
				key = cmd[2][2:]
				for post in post_list:
					if re.search(key, post[1]) != None:
						day = post[3].split('-', -1)
						msg += str(post[0]) + '\t' + post[1] + '\t' + post[2] + '\t' + day[1] + '/' + day[2] + '\n'
			else:
				msg = 'Board is not exist.\n'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'read':
		if len(cmd) != 2:
			msg = 'Usage: read <post-id>\n'
		else:
			post_id = int(cmd[1])
			if CheckPostExist(post_id):
				post = GetPost(post_id)
				post_content = str(post[3]).replace('<br>', '\n')
				msg = 'Author\t:'
				msg += post[4] + '\nTitle\t:' + post[2] + '\nDate\t:' + post[5] + '\n--\n' + post_content + '\n--\n'
				comment_count = GetCommentCount(post_id)
				comment_list = GetPostCommentList(post_id)
				if comment_count != 0:
					for comment in comment_list:
						msg += comment[0] + ': ' + str(comment[1]).replace('<br>', '\n\t') + '\n'
			else:
				msg = 'Post does not exist.\n'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'delete-post':
		if login_status == False:
			msg = 'Please login first.\n'
		else:
			if len(cmd) != 2:
				msg = 'Usage: delete-post <post-id>\n'
			else:
				post_id = int(cmd[1])
				if CheckPostExist(post_id):
					post = GetPost(post_id)
					author = post[4]
					if login_user == author:
						DeletePost(post_id)
						msg = 'Delete successfully.\n'
					else:
						msg = 'Not the post owner.\n'
				else:
					msg = 'Post does not exist.\n'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'update-post':
		if login_status == False:
			msg = 'Please login first.\n'
		else:
			if (cmd[2] != '--title' and cmd[2] != '--content') or len(cmd) < 4:
				msg = 'Usage: update-post <post-id> --title/content <new>\n'
			else:
				post_id = int(cmd[1])
				if CheckPostExist(post_id):
					post = GetPost(post_id)
					author = post[4]
					if login_user == author:
						if cmd[2] == '--title':
							cmd_orig_title = cmd_orig.find('--title')
							UpdatePostTitle(post_id, cmd_orig[cmd_orig_title + 8:].strip())
						else:
							cmd_orig_content = cmd_orig.find('--content')
							UpdatePostContent(post_id, cmd_orig[cmd_orig_content + 10:].strip())
						msg = 'Update successfully.\n'
					else:
						msg = 'Not the post owner.\n'
				else:
					msg = 'Post does not exist.\n'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'comment':
		if login_status == False:
			msg = 'Please login first.\n'
		else:
			if len(cmd) < 3:
				msg = 'Usage: comment <post-id> <comment>\n'
			else:
				post_id = int(cmd[1])
				if CheckPostExist(post_id):
					cmd_orig_post_id = cmd_orig.find(cmd[1])
					CreateComment(post_id, cmd_orig[cmd_orig_post_id + len(cmd[1]):].strip(), login_user)
					msg = 'Comment successfully.\n'
				else:
					msg = 'Post does not exist.\n'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'exit':
		conn.close()
		conn_pool.remove(conn)
		return login_status, login_user, True

	else:
		msg = 'Command not found. Your command is ' + cmd[0] + '.\n'
		Write(conn, msg)
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
		cmd_orig = str(data.decode().strip())
		cmd = str(cmd_orig).split(' ', -1)
		login_status, login_user, exitornot = HandleCommand(conn, cmd, cmd_orig, login_status, login_user)
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
