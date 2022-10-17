import socket
import time
import chatlib

SERVER_IP = "127.0.0.1"
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
	# TODO: debug
	full_msg = conn.recv(1024).decode()
	return chatlib.parse_message(full_msg)


def build_send_recv_parse(conn, cmd, data=""):
	build_and_send_message(conn, cmd, data)
	return recv_message_and_parse(conn)


def get_score(conn):
	(cmd, data) = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["score"], "")
	return data


def get_highscore(conn):
	(cmd, data) = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["high"], "")
	time.sleep(2.5)
	return data


def play_question(conn):
	(cmd, data) = build_send_recv_parse(conn, chatlib.SEMI_PROTOCOL_CLIENT['1'])
	if data is None:
		print("ERROR")
		return
	else:
		question_data = chatlib.split_data(data, 5)
		try:
			question_number = question_data[0]
			question_data.remove(question_number)
		except:
			print(data)
		question_data = [f'\n{x} - {question_data[x]}'for x in range(len(question_data))]
		print(''.join(question_data)[5:])
	ans = input("Answer: ")

	# check answer validity
	while ans not in ['1', '2', '3', '4']:
		print("Invalid answer")
		ans = input("Answer: ")
	(cmd, data) = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["send_ans"], question_number + '#' + ans)
	if cmd is None:
		print("ERROR")
		return
	elif cmd == "CORRECT_ANSWER":
		print("Correct Answer")
	else:
		print("--> ", data)  # TODO: reformat


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


def login(conn, user_mode):
	"""
	get username and password from the user and login
	:param conn: socket
	:param user_mode: char ('1' or '2')
	:return: None
	"""
	while True:
		username = input("Please enter username: \n")
		password = input("Please enter password: \n")
		data = [username, password]
		r = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["login_msg"], '#'.join(data))
		if r[0] is None or r[0] == "ERROR":
			print("Login failed")
			print(r[1])
		else:
			print("Login success")
			break
	return


def logout(conn):
	build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["logout_msg"], "")
	conn.close()


def user_game(my_sock):
	command = input("1 - Get question\n2 - Get score\n3 - Get high score\n4 - Get logged in\n5 - Log out\n")
	while True:
		cmd = chatlib.SEMI_PROTOCOL_CLIENT[command]
		(cmd, data) = build_send_recv_parse(my_sock, cmd)
		if command == '1':
			play_question(my_sock)
		elif command == '2':
			print(f'You have {get_score(my_sock)} points')
			time.sleep(2.5)
		elif command == '3':
			print(get_highscore(my_sock))
		elif command == '4':
			get_logged_user(my_sock)
		elif command == '5':
			break

		command = input("1 - Get question\n2 - Get score\n3 - Get high score\n4 - Get logged in users\n5 - Log out\n")
		while command not in ['1', '2', '3', '4', '5']:
			print("Invalid choice")
			command = input("1 - Get question\n2 - Get score\n3 - Get high score\n4 - Get logged in\n5 - Log out\n")

	logout(my_sock)
	print("Logout success")


def add_question(conn):  # TODO: validate input
	"""
	add question to database, only creator can add questions
	:param conn: socket
	"""
	question = input('Write a question please\n')
	answers = input('Write 4 answers separated by \'$\'\n')
	correct_answer = input('Write the correct answer\n')
	question_data = [question, answers, correct_answer]
	(cmd, data) = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT["add"], '#'.join(question_data))
	if cmd is None or cmd == "ERROR":
		print("A problem was found while adding question, please try again")
	elif cmd == "ADD_QUESTION_SUCCESSFULLY":
		print("Question has successfully added")


def creator(my_sock):  # TODO: validate command input
	command = input('1 - Add question\n2 - Log out\n')
	while True:
		if command == '1':
			add_question(my_sock)
		elif command == '2':
			break
		command = input('1 - Add question\n2 - Log out\n')

	logout(my_sock)
	print("Logout success")


def main():
	my_sock = connect()

	user_mode = input('1 - User\n2 - Manager\n')
	while user_mode not in ['1', '2']:
		user_mode = input('1 - User\n2 - Manager\n')

	login(my_sock, user_mode)

	if user_mode == '1':
		user_game(my_sock)
	else:
		creator(my_sock)

	pass


if __name__ == '__main__':
	main()
