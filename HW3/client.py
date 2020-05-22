#!/usr/bin/python3
import boto3
import sys
import socket
import os

HOST = sys.argv[1]
PORT = int(sys.argv[2])
login_user = None

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
	if cmd[0] == 'exit':
		data = CommunicateWithServer(conn, cmd_orig)
		return True

	elif cmd[0] == 'logout':
		data = CommunicateWithServer(conn, cmd_orig)
		print(data.decode().strip())
		login_user = None
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
				else:
					login_user = cmd[1]
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
				CreateUserContent(file_name, login_user)
				print('Create post successfully.')
				os.remove(file_name)
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
					CreateUserContent(file_name, login_user)
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
					CreateUserComment(file_name, author)
					os.remove(file_name)
					print('Comment successfully.')
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
	objectkey = 'comment' + '_' + board_name + '_' + objectkey
	bucket_name = TurnIntoBucketName(username)
	s3 = boto3.resource('s3')
	bucket = s3.Bucket(bucket_name)
	target_object = bucket.Object(objectkey)
	comment = target_object.get()['Body'].read().decode()
	return comment

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

def CreateUserContent(objectkey, username):
	bucket_name = TurnIntoBucketName(username)
	s3 = boto3.resource('s3')
	bucket = s3.Bucket(bucket_name)
	bucket.upload_file(objectkey, objectkey)

def CreateUserComment(objectkey, username):
	bucket_name = TurnIntoBucketName(username)
	s3 = boto3.resource('s3')
	bucket = s3.Bucket(bucket_name)
	bucket.upload_file(objectkey, objectkey)

def TurnIntoBucketName(username):
	return str(username + 'tommytyc')

def TurnIntoUserName(bucket_name):
	length = len(bucket_name) - 8
	return bucket_name[:length]

if __name__ == '__main__':
	ConnectServer()