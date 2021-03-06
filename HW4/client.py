#!/usr/bin/python3
import boto3
import sys
import socket
import os
import threading
import redis

HOST = sys.argv[1]
PORT = int(sys.argv[2])
login_user = None
login_status = False
UserSub_list = []
UserSub_dict = {}
channel_list = []

def ListenChannel(usersub, channel, key_word, sub_idx):
	sub = usersub.rsub[sub_idx]
	for message in sub.listen():
		if isinstance(message.get('data'), bytes) and message['data'].decode() == channel+'_kill':
			break
		elif isinstance(message.get('data'), bytes) and 'kill' in message['data'].decode():
			pass
		elif isinstance(message.get('data'), bytes):
			msg = message['data'].decode()
			msg = msg.split(']', -1)
			msg = msg[1].split('-', -1)
			msg = msg[0]
			if key_word in msg:
				print(message['data'].decode() + '\n% ', end = '')

class UserSub():
	def __init__(self, user):
		self.name = user
		self.sub_board = []
		self.sub_author = []
		self.r = redis.Redis(host='redis-12667.c228.us-central1-1.gce.cloud.redislabs.com', port=12667, password='jg0e1RU7OQpMkKabhWi4nQWYVSYmy5uV')
		self.rsub = []

	def AddSub(self, sub_type, channel, key_word):
		if sub_type == 'board':
			flag = True
			for i in self.sub_board:
				if i[0] == channel:
					i[1].append(key_word)
					flag = False
			if flag:
				self.sub_board.append((channel, [key_word]))
		elif sub_type == 'author':
			flag = True
			for i in self.sub_author:
				if i[0] == channel:
					i[1].append(key_word)
					flag = False
			if flag:
				self.sub_author.append((channel, [key_word]))
		tsub = self.r.pubsub()
		tsub.subscribe(channel)
		self.rsub.append(tsub)
		sub_idx = self.rsub.index(tsub)
		return sub_idx

	def CheckSubOrNot(self, sub_type, channel, key_word):
		if sub_type == 'board':
			for i in self.sub_board:
				if i[0] == channel:
					if key_word in i[1]:
						return True
					else:
						return False
			return False
		elif sub_type == 'author':
			for i in self.sub_author:
				if i[0] == channel:
					if key_word in i[1]:
						return True
					else:
						return False
			return False

def AddUserSub(user, sub_type, channel, key_word):
	global UserSub_list
	global UserSub_dict
	idx = UserSub_dict.get(user, None)
	flag = True
	if idx == None:
		new_usersub = UserSub(user)
		sub_idx = new_usersub.AddSub(sub_type, channel, key_word)
		UserSub_list.append(new_usersub)
		UserSub_dict[user] = UserSub_list.index(new_usersub)
		idx = UserSub_dict[user]
	else:
		if UserSub_list[idx].CheckSubOrNot(sub_type, channel, key_word):
			print('Already subscribed.')
			flag = False
		else:
			sub_idx = UserSub_list[idx].AddSub(sub_type, channel, key_word)
	if flag:
		print('Subscribe successfully.')
		t = threading.Thread(target = ListenChannel, args = (UserSub_list[idx], channel, key_word, sub_idx))
		t.start()

def PubPost(channel, board_name, title, author):
	r = redis.Redis(host='redis-12667.c228.us-central1-1.gce.cloud.redislabs.com', port=12667, password='jg0e1RU7OQpMkKabhWi4nQWYVSYmy5uV')
	if title != channel+'_kill':
		r.publish(channel, str('*[' + board_name + '] ' + title + ' - by ' + author + '*'))
	else:
		r.publish(channel, channel+'_kill')
		

def RemoveUserSub(user, sub_type, channel):
	flag = False
	idx = UserSub_dict.get(user, None)
	if idx == None:
		print("You haven't subscribed " + channel)
	else:
		usersub = UserSub_list[idx]
		new_sub_list = []
		if sub_type == 'board':
			for i in usersub.sub_board:
				if i[0] == channel:
					flag = True
					PubPost(channel, channel, channel+'_kill', channel)
					break
				else:
					new_sub_list.append(i)
			usersub.sub_board = new_sub_list
			if flag:
				print('Unsubscribe successfully.')
			else:
				print("You haven't subscribed " + channel)
		elif sub_type == 'author':
			for i in usersub.sub_author:
				if i[0] == channel:
					flag = True
					PubPost(channel, channel, channel+'_kill', channel)
				else:
					new_sub_list.append(i)
			usersub.sub_author = new_sub_list
			if flag:
				print('Unsubscribe successfully.')
			else:
				print("You haven't subscribed " + channel)

def RemoveUserAllSub(user):
	idx = UserSub_dict.get(user, None)
	if idx == None:
		pass
	else:
		usersub = UserSub_list[idx]
		for i in usersub.sub_board:
			PubPost(i[0], i[0], i[0]+'_kill', i[0])

		for i in usersub.sub_author:
			PubPost(i[0], i[0], i[0]+'_kill', i[0])

def PrintUserSub(user):
	idx = UserSub_dict.get(user, None)
	if idx == None:
		print("You haven't subscribed anything.")
	else:
		usersub = UserSub_list[idx]
		if len(usersub.sub_board) == 0 and len(usersub.sub_author) == 0:
			print("You haven't subscribed anything.")
		else:
			if len(usersub.sub_board) != 0:
				print('Board: ', end = '')
				for i in usersub.sub_board:
					print(i[0] + ': ', end = '')
					for j in i[1]:
						print(j, end = '')
						if j != i[1][-1]:
							print(', ', end = '')
						else:
							if i == usersub.sub_board[-1]:
								print()
							else:
								print('; ', end = '')
			if len(usersub.sub_author) != 0:
				print('Author: ', end = '')
				for i in usersub.sub_author:
					print(i[0] + ': ', end = '')
					for j in i[1]:
						print(j, end = '')
						if j != i[1][-1]:
							print(', ', end = '')
						else:
							if i == usersub.sub_author[-1]:
								print()
							else:
								print('; ', end = '')

def ConnectServer():
	conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		conn.connect((HOST, PORT))
	except socket.error:
		print('error happened.')
		exit(1)
	HandleBBS(conn)
		
def HandleBBS(conn):
	print("********************************\n")
	print("** Welcome to the BBS server. **\n")
	print("********************************\n")
	while True:
		input_cmd = input('% ')
		cmd_orig = str(input_cmd.strip())
		cmd = cmd_orig.split(' ', -1)
		exitornot = HandleClientCommand(conn, cmd_orig, cmd)
		if exitornot:
			break

def HandleClientCommand(conn, cmd_orig, cmd):
	global login_user
	global login_status
	global channel_list
	if cmd[0] == 'exit':
		if login_user != None:
			RemoveUserAllSub(login_user)
		data = CommunicateWithServer(conn, cmd_orig)
		return True

	elif cmd[0] == 'logout':
		data = CommunicateWithServer(conn, cmd_orig)
		print(data.decode().strip())
		RemoveUserAllSub(login_user)
		login_user = None
		login_status = False
		return False

	elif cmd[0] == 'whoami' or cmd[0] == 'create-board' or cmd[0] == 'list-board' or cmd[0] == 'list-post':
		data = CommunicateWithServer(conn, cmd_orig)
		print(data.decode().strip())
		return False

	else:
		if cmd[0] == 'register':
			if len(cmd) != 4:
				print('Usage: register <username> <email> <password>')
			else:
				data = CommunicateWithServer(conn, cmd_orig)
				if data.decode().strip() == '1':
					print('Username is already used.')
				else:
					CreateUserBucket(cmd[1])
					print('Register successfully.')
			return False

		elif cmd[0] == 'login':
			if len(cmd) != 3:
				print('Usage: login <username> <password>')
			else:
				data = CommunicateWithServer(conn, cmd_orig)
				if data.decode().strip() == '1':
					print('Login failed.')
				elif data.decode().strip() == '2':
					print('Please logout first.')
				else:
					login_user = cmd[1]
					login_status = True
					print('Welcome, ' + cmd[1] + '.')
			return False
		
		elif cmd[0] == 'create-post':
			data = CommunicateWithServer(conn, cmd_orig)
			if data.decode().strip() == '1':
				print('Please login first.')
			elif data.decode().strip() == '2':
				print('Board does not exist.')
			elif data.decode().strip() == '3':
				print('Usage: create-post <board-name> --title <title> --content <content>')
			else:
				cmd_orig_title = cmd_orig.find('--title')
				cmd_orig_content = cmd_orig.find('--content')
				post_content = cmd_orig[cmd_orig_content + 10 :].strip()
				post_title = cmd_orig[cmd_orig_title + 8 : cmd_orig_content].strip()
				file_name = cmd[1] + '_' + post_title
				print(post_content + '\n--', file = open(file_name, 'w'))
				CreateUserObject(file_name, login_user)
				print('Create post successfully.')
				os.remove(file_name)
				if cmd[1] not in channel_list:
					channel_list.append(cmd[1])
				if login_user not in channel_list:
					channel_list.append(login_user)
				PubPost(cmd[1], cmd[1], post_title, login_user)
				PubPost(login_user, cmd[1], post_title, login_user)
			return False

		elif cmd[0] == 'read':
			data = CommunicateWithServer(conn, cmd_orig)
			data = data.decode().strip().split('tommytyc', -1)
			if len(cmd) != 2:
				print('Usage: read <post-id>')
			else:
				if data[0] == '1':
					print('Post does not exist.')
				else:
					assert len(data) == 5
					hascomment = True			
					comment = ''
					msg = data[1]
					author = data[2]
					title = data[3]
					board_name = data[4]
					content = str(GetBucketContent(author, title, board_name)).replace('<br>', '\n')
					try:
						comment = str(GetBucketComment(author, title, board_name)).replace('<br>', '\n')
					except:
						hascomment = False
					print(msg)
					print(content)
					if hascomment:
						print(comment)
			return False

		elif cmd[0] == 'delete-post':
			if len(cmd) != 2:
				print('Usage: delete-post <post-id>')
			else:
				data = CommunicateWithServer(conn, cmd_orig)
				data = data.decode().strip().split('tommytyc', -1)
				if data[0] == '1':
					print('Please login first.')
				elif data[0] == '2':
					print('Not the post owner.')
				elif data[0] == '3':
					print('Post does not exist.')					
				else:
					assert len(data) == 4
					DeleteBucketContentComment(data[1], data[2], data[3])
					print('Delete successfully.')
			return False

		elif cmd[0] == 'update-post':
			if len(cmd) < 4 or (cmd[2] != '--title' and cmd[2] != '--content'):
				print('Usage: update-post <post-id> --title/content <new>')
			else:
				data = CommunicateWithServer(conn, cmd_orig)
				data = data.decode().strip().split('tommytyc', -1)
				if data[0] == '1':
					print('Please login first.')
				elif data[0] == '2':
					print('Not the post owner.')
				elif data[0] == '3':
					print('Post does not exist.')
				else:
					assert len(data) == 4
					author = data[1]
					new_title = data[2]
					board_name = data[3]
					new_content = str(GetBucketContent(author, new_title, board_name))
					DeleteBucketContentComment(author, new_title, board_name)
					if cmd[2] == '--title':
						cmd_orig_title = cmd_orig.find('--title')
						new_title = cmd_orig[cmd_orig_title + 8:].strip()
					else:
						cmd_orig_content = cmd_orig.find('--content')
						new_content = cmd_orig[cmd_orig_content + 10:].strip()
						new_content += '\n--'
					file_name = board_name + '_' + new_title
					print(new_content, file = open(file_name, 'w'))
					CreateUserObject(file_name, login_user)
					os.remove(file_name)
					print('Update successfully.')
			return False

		elif cmd[0] == 'comment':
			if len(cmd) < 3:
				print('Usage: comment <post-id> <comment>')
			else:
				data = CommunicateWithServer(conn, cmd_orig)
				data = data.decode().strip().split('tommytyc', -1)
				if data[0] == '1':
					print('Please login first.')
				elif data[0] == '2':
					print('Post does not exist.')
				else:
					cmd_orig_post_id = cmd_orig.find(cmd[1])
					author = data[1]
					title = data[2]
					board_name = data[3]
					file_name = 'comment' + '_' + board_name + '_' + title
					comment = ''
					try:
						comment += str(GetBucketComment(author, title, board_name))
					except:
						pass
					comment += login_user + ': ' + cmd_orig[cmd_orig_post_id + len(cmd[1]):].strip()
					print(comment, file = open(file_name, 'w')) 
					CreateUserObject(file_name, author)
					os.remove(file_name)
					print('Comment successfully.')
			return False

		elif cmd[0] == 'mail-to':
			data = CommunicateWithServer(conn, cmd_orig)
			data = data.decode().strip().split('tommytyc', -1)
			if data[0] == '1':
				print('Please login first.')
			elif data[0] == '2':
				print(cmd[1] + ' does not exist.')
			elif data[0] == '3':
				print('Usage: mail-to <username> --subject <subject> --content <content>')
			else:
				cmd_orig_subject = cmd_orig.find('--subject')
				cmd_orig_content = cmd_orig.find('--content')
				mail_content = cmd_orig[cmd_orig_content + 10 :].strip()
				mail_subject = cmd_orig[cmd_orig_subject + 10 : cmd_orig_content].strip().replace(' ', '_')
				file_name = 'mail_' + mail_subject
				print(mail_content + '\n--', file = open(file_name, 'w'))
				CreateUserObject(file_name, cmd[1])
				print('Sent successfully.')
				os.remove(file_name)
			return False

		elif cmd[0] == 'list-mail':
			if len(cmd) != 1:
				print('Usage: list-mail')
			else:
				data = CommunicateWithServer(conn, cmd_orig)
				data = data.decode().strip()
				if data == '1':
					print('Please login first.')
				else:
					print(data)
			return False

		elif cmd[0] == 'retr-mail':
			if len(cmd) != 2:
				print('Usage: retr-mail <mail#>')
			else:
				data = CommunicateWithServer(conn, cmd_orig)
				data = data.decode().strip().split('tommytyc', -1)
				if data[0] == '1':
					print('Please login first.')
				elif data[0] == '2':
					print('No such mail.')
				else:
					content = str(GetBucketMail(login_user, data[2].replace(' ', '_'))).replace('<br>', '\n')
					msg = data[1]
					print(msg)
					print(content)
			return False

		elif cmd[0] == 'delete-mail':
			if len(cmd) != 2:
				print('Usage: delete-mail <mail#>')
			else:
				data = CommunicateWithServer(conn, cmd_orig)
				data = data.decode().strip().split('tommytyc', -1)
				if data[0] == '1':
					print('Please login first.')
				elif data[0] == '2':
					print('No such mail.')
				else:
					subject = data[1].replace(' ', '_')
					DeleteBuckeMail(login_user, subject)
					print('Mail deleted.')
			return False

		elif cmd[0] == 'subscribe':
			if login_status == False:
				print('Please login first.')
			else:
				cmd_orig_board = cmd_orig.find('--board')
				cmd_orig_author = cmd_orig.find('--author')
				cmd_orig_keyword = cmd_orig.find('--keyword')
				if cmd_orig_board >= 0:
					sub_type = 'board'
					idx = cmd_orig_board
					offset = 8
				elif cmd_orig_author >= 0:
					sub_type = 'author'
					idx = cmd_orig_author
					offset = 9
				else:
					print('Usage: subscribe --board/author <board/author-name> --keyword <keyword>')
					return False
				if '--'+sub_type in cmd and '--keyword' in cmd and cmd.index('--'+sub_type) < cmd.index('--keyword') and cmd[1] == '--'+sub_type:
					AddUserSub(login_user, sub_type, cmd_orig[idx + offset : cmd_orig_keyword].strip(), cmd_orig[cmd_orig_keyword + 10 :])

			return False

		elif cmd[0] == 'unsubscribe':
			if login_status == False:
				print('Please login first.')
			else:
				if len(cmd) != 3 or (cmd[1] != '--board' and cmd[1] != '--author'):
					print('Usage: unsubscribe --board/author <board/author-name>')
				else:
					if cmd[1] == '--board':
						sub_type = 'board'
					else:
						sub_type = 'author'
					RemoveUserSub(login_user, sub_type, cmd[2])
			return False

		elif cmd[0] == 'list-sub':
			if login_status == False:
				print('Please login first.')
			else:
				if len(cmd) != 1:
					print('Usage: list-sub')
				else:
					PrintUserSub(login_user)
			return False

def GetBucketContent(username, objectkey, board_name):
	objectkey = board_name + '_' + objectkey
	bucket_name = TurnIntoBucketName(username)
	s3 = boto3.resource('s3')
	bucket = s3.Bucket(bucket_name)
	target_object = bucket.Object(objectkey)
	content = target_object.get()['Body'].read().decode()
	return content

def GetBucketComment(username, objectkey, board_name):
	objectkey = 'comment_' + board_name + '_' + objectkey
	bucket_name = TurnIntoBucketName(username)
	s3 = boto3.resource('s3')
	bucket = s3.Bucket(bucket_name)
	target_object = bucket.Object(objectkey)
	comment = target_object.get()['Body'].read().decode()
	return comment

def GetBucketMail(username, objectkey):
	objectkey = 'mail_' + objectkey
	bucket_name = TurnIntoBucketName(username)
	s3 = boto3.resource('s3')
	bucket = s3.Bucket(bucket_name)
	target_object = bucket.Object(objectkey)
	content = target_object.get()['Body'].read().decode()
	return content

def DeleteBucketContentComment(username, objectkey, board_name):
	objectkey = board_name + '_' + objectkey
	bucket_name = TurnIntoBucketName(username)
	s3 = boto3.resource('s3')
	bucket = s3.Bucket(bucket_name)
	target_object = bucket.Object(objectkey)
	target_object.delete()
	try:
		comment_object = bucket.Object('comment' + '_' + objectkey)
		comment_object.delete()
	except:
		pass

def DeleteBuckeMail(username, objectkey):
	objectkey = 'mail_' + objectkey
	bucket_name = TurnIntoBucketName(username)
	s3 = boto3.resource('s3')
	bucket = s3.Bucket(bucket_name)
	target_object = bucket.Object(objectkey)
	target_object.delete()

def CommunicateWithServer(conn, cmd):
	conn.sendall(cmd.encode())
	return GetInfoFromServer(conn)

def GetInfoFromServer(conn):
	data = conn.recv(1024)
	if len(data) == 0:
		conn.close()
		return
	return data

def CreateUserBucket(username):
	bucket_name = TurnIntoBucketName(username)
	s3 = boto3.resource('s3')
	s3.create_bucket(Bucket = bucket_name)

def CreateUserObject(objectkey, username):
	bucket_name = TurnIntoBucketName(username)
	s3 = boto3.resource('s3')
	bucket = s3.Bucket(bucket_name)
	bucket.upload_file(objectkey, objectkey)

def TurnIntoBucketName(username):
	return str(username.lower() + 'tommytyc')

def TurnIntoUserName(bucket_name):
	length = len(bucket_name) - 8
	return bucket_name[:length]

if __name__ == '__main__':
	ConnectServer()