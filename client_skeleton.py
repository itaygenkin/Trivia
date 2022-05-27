import socket
import time

import chatlib  # To use chatlib functions or consts, use chatlib.****

SERVER_IP = "127.0.0.1"  # Our server will run on same computer as client
SERVER_PORT = 5678

# HELPER SOCKET METHODS


def build_and_send_message(conn, code, data):
	"""
	Builds a new message using chatlib, wanted code and message. 
	Prints debug info, then sends it to the given socket.
	Parameters: conn (socket object), code (str), data (str)
	Returns: Nothing
	"""
	msg = chatlib.build_message(code, data)
	conn.send(msg.encode())
	

def recv_message_and_parse(conn):
	"""
	Receives a new message from given socket,
	then parses the message using chatlib.
	Parameters: conn (socket object)
	Returns: cmd (str) and data (str) of the received message. 
	If error occurred, will return None, None
	"""
	full_msg = conn.recv(1024).decode()
	cmd, data = chatlib.parse_message(full_msg)
	return cmd, data


def build_send_recv_parse(conn, cmd, data=""):
	build_and_send_message(conn, cmd, data)
	return recv_message_and_parse(conn)


def get_score(conn):
	(cmd, data) = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["score"], "")
	return data


def get_highscore(conn):
	(cmd, data) = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["high"], "")
	print(data)
	time.sleep(2.5)
	return data


def play_question(conn):
	(cmd, data) = build_send_recv_parse(conn, chatlib.SEMI_PROTOCOL_CLIENT['1'])
	if data is None:
		print("ERROR")
		return
	else:
		data = chatlib.split_data(data, 4)
		print('\n'.join(data))
	ans = input("Answer: ")
	(cmd, data) = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["send_ans"], ans)
	if cmd is None:
		print("ERROR")
		return
	else:
		print(data)


def get_logged_user(conn):
	(cmd, data) = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["logged_msg"])
	if cmd is None:
		print("ERROR")
	else:
		print(data)


def connect():
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((SERVER_IP, SERVER_PORT))
	return sock


def error_and_exit(error_msg):
	print(error_msg)
	exit()


def login(conn):
	"""
	get username and password from the user and login
	:param conn: socket
	:return: None
	"""
	while True:
		username = input("Please enter username: \n")
		password = input("Please enter password: \n")
		data = [username, password]
		build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["login_msg"], '#'.join(data))
		r = recv_message_and_parse(conn)
		# print(r)
		if r[0] is None or r[0] == "ERROR":
			print("Login failed")
		else:
			print("Login success")
			break
	return


def logout(conn):
	build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["logout_msg"], "")
	conn.close()


def main():
	# Implement code
	my_sock = connect()
	login(my_sock)
	command = input("1 - Get question\n2 - Get score\n3 - Get high score\n4 - get logged in\n5 - Log out\n")
	while True:
		cmd = chatlib.SEMI_PROTOCOL_CLIENT[command]
		(cmd, data) = build_send_recv_parse(my_sock, cmd)
		if command == '1':
			play_question(my_sock)
		elif command == '2':
			print(get_score(my_sock))
		elif command == '3':
			get_highscore(my_sock)
		elif command == '4':
			get_logged_user(my_sock)
		elif command == '5':
			break
		command = input("1 - next question\n2 - my score\n3 - highscore\n4 - Get logged in users\n5 - Log out")
	logout(my_sock)
	print("Logout success")
	pass


if __name__ == '__main__':
	main()
