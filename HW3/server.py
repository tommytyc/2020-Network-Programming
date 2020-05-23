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
	# Create table post(id, board_name, title, author, date)
	cursor.execute(
		"""
			create table if not exists post(
				id integer primary key autoincrement,
				board_name text,
				title text,
				author text,
				date text
			)
		"""
	)
	# Create table mail(receiver, sender, subject, date)
	cursor.execute(
		"""
			create table if not exists mail(
				receiver text,
				sender text,
				subject text,
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

def CreatePost(board_name, title, author, date):
	cursor.execute(" insert into post(board_name, title, author, date) values(?, ? ,?, ?) ", (board_name, title, author, date))
	dbconn.commit()

def CreateMail(receiver, sender, subject, date):
	cursor.execute(" insert into mail(receiver, sender, subject, date) values(?, ? ,?, ?) ", (receiver, sender, subject, date))
	dbconn.commit()

def GetUserMailCount(user):
	cursor.execute(" select count(*) from mail where receiver = ? ", (user,))
	return cursor.fetchone()

def GetUserMailList(user):
	cursor.execute(" select * from mail where receiver = ? ", (user,))
	return cursor.fetchall()

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

def DeleteMail(user, subject):
	cursor.execute(" delete from mail where receiver = ? and subject = ?", (user, subject))
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

def HandleServerCommand(conn, cmd, cmd_orig, login_status, login_user):
	msg = None
	if cmd[0] == 'register':
		if CheckUserExist(cmd[1]):
			# msg = 'Username is already used.\n'
			msg = '1'
		else:
			CreateUser(cmd[1], cmd[2], cmd[3])
			# msg = 'Register successfully.\n'
			msg = '0'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'login':
		if login_status == True:
			msg = '2'
		else: 
			if CheckUserExist(cmd[1]):
				user = GetUser(cmd[1])
				if cmd[2] == user[2]:
					login_status = True
					login_user = cmd[1]
					msg = '0'
				else:
					msg = '1'
			else:
				msg = '1'
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
			msg = '1'
		else:
			cmd_orig_title = cmd_orig.find('--title')
			cmd_orig_content = cmd_orig.find('--content')
			if '--title' in cmd and '--content' in cmd and cmd.index('--title') < cmd.index('--content') and cmd[2] == '--title':
				if login_status == False:
					msg = '1'
				else:
					if CheckBoardExist(cmd[1]):
						today = str(date.today())
						CreatePost(cmd[1], cmd_orig[cmd_orig_title + 8 : cmd_orig_content].strip(), login_user, today)
						msg = '0'
					else:
						msg = '2'
			else:
				msg = '3'
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
		post_id = int(cmd[1])
		if CheckPostExist(post_id):
			post = GetPost(post_id)
			msg = 'Author\t:'
			msg += post[3] + '\nTitle\t:' + post[2] + '\nDate\t:' + post[4] + '\n--\n'
			tmp = '0'
			tmp += 'tommytyc' + msg + 'tommytyc' + post[3] + 'tommytyc' + post[2] + 'tommytyc' + post[1]
			Write(conn, tmp)
		else:
			msg = '1'
			Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'delete-post':
		if login_status == False:
			msg = '1'
		else:
			post_id = int(cmd[1])
			if CheckPostExist(post_id):
				post = GetPost(post_id)
				author = post[3]
				title = post[2]
				board_name = post[1]
				if login_user == author:
					DeletePost(post_id)
					msg = '0'
					msg += 'tommytyc' + author + 'tommytyc' + title + 'tommytyc' + board_name
				else:
					msg = '2'
			else:
				msg = '3'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'update-post':
		if login_status == False:
			msg = '1'
		else:
			post_id = int(cmd[1])
			if CheckPostExist(post_id):
				post = GetPost(post_id)
				author = post[3]
				title = post[2]
				board_name = post[1]
				if login_user == author:
					if cmd[2] == '--title':
						cmd_orig_title = cmd_orig.find('--title')
						UpdatePostTitle(post_id, cmd_orig[cmd_orig_title + 8:].strip())
					msg = '0'
					msg += 'tommytyc' + author + 'tommytyc' + title + 'tommytyc' + board_name
				else:
					msg = '2'
			else:
				msg = '3'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'comment':
		if login_status == False:
			msg = '1'
		else:
			post_id = int(cmd[1])
			if CheckPostExist(post_id):
				post = GetPost(post_id)
				author = post[3]
				title = post[2]
				board_name = post[1]
				msg = '0'
				msg += 'tommytyc' + author + 'tommytyc' + title + 'tommytyc' + board_name
			else:
				msg = '2'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'mail-to':
		if login_status == False:
			msg = '1'
		else:
			cmd_orig_title = cmd_orig.find('--subject')
			cmd_orig_content = cmd_orig.find('--content')
			if '--subject' in cmd and '--content' in cmd and cmd.index('--subject') < cmd.index('--content') and cmd[2] == '--subject':
				if login_status == False:
					msg = '1'
				else:
					if CheckUserExist(cmd[1]):
						today = str(date.today())
						CreateMail(cmd[1], login_user, cmd_orig[cmd_orig_title + 10 : cmd_orig_content].strip(), today)
						mail_count = GetUserMailCount(cmd[1])
						msg = '0'
						msg += 'tommytyc' + str(mail_count[0])
					else:
						msg = '2'
			else:
				msg = '3'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'list-mail':
		if login_status == False:
			msg = '1'
		else:
			mail_list = GetUserMailList(login_user)
			msg = 'ID\tSubject\tFrom\tDate\n'
			mail_id = 0
			for mail in mail_list:
				mail_id += 1
				day = mail[3].split('-', -1)
				msg += str(mail_id) + '\t' + mail[2] + '\t' + mail[1] + '\t' + day[1] + '/' + day[2] + '\n'
		Write(conn, msg)
		return login_status, login_user, False

	elif cmd[0] == 'retr-mail':
		if login_status == False:
			msg = '1'
			Write(conn, msg)
		else:	
			mail_list = GetUserMailList(login_user)
			if int(cmd[1]) > len(mail_list) or int(cmd[1]) < 1:
				msg = '2'
				Write(conn, msg)
			else:
				mail_num = int(cmd[1]) - 1
				msg = 'Subject\t:'
				msg += mail_list[mail_num][2] + '\nFrom\t:' + mail_list[mail_num][1] + '\nDate\t:' + mail_list[mail_num][3] + '\n--\n'
				tmp = '0'
				tmp += 'tommytyc' + msg + 'tommytyc' + mail_list[mail_num][2]
				Write(conn, tmp)
		return login_status, login_user, False

	elif cmd[0] == 'delete-mail':
		if login_status == False:
			msg = '1'
			Write(conn, msg)
		else:
			mail_list = GetUserMailList(login_user)
			if int(cmd[1]) > len(mail_list) or int(cmd[1]) < 1:
				msg = '2'
				Write(conn, msg)
			else:
				mail_num = int(cmd[1]) - 1
				DeleteMail(login_user, mail_list[mail_num][2])
				msg = '0'
				msg += 'tommytyc' + mail_list[mail_num][2]
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
	while True:
		data = conn.recv(1024)
		if len(data) == 0:
			conn.close()
			conn_pool.remove(conn)
			break
		cmd_orig = str(data.decode().strip())
		cmd = cmd_orig.split(' ', -1)
		login_status, login_user, exitornot = HandleServerCommand(conn, cmd, cmd_orig, login_status, login_user)
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
