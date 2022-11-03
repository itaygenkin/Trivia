##############################################################################
# server.py
##############################################################################
import select
import socket
from operator import itemgetter
import requests

import chatlib
import random

# GLOBALS
users = {"itay": {"password": "a123", "score": 0, "questions_asked": [], "isCreator": False},
		 "oscar": {"password": "oscar", "score": 1000, "questions_asked": [], "isCreator": False},
		 "master": {"password": "master", "score": 0, "questions_asked": [], "isCreator": True}}
questions = {
	chatlib.generate_question_number().__next__(): {"question": "How much is 2+2", "answers": ["1", "2", "3", "4"], "correct": 4},
	chatlib.generate_question_number().__next__(): {"question": "What is the capital of France?", "answers": ["Lion", "Marseille", "Paris", "Montpelier"],
		   "correct": 3}
}
logged_users = {}  # a dictionary of client hostnames to usernames
client_sockets = []  # a list of client sockets
messages_to_send = []  # a list of messages which the server might send to clients

ERROR_MSG = "Error! "
SERVER_PORT = 5678
SERVER_IP = "127.0.0.1"


# HELPER SOCKET METHODS

def build_and_send_message(conn, code, data=""):
	"""
	Builds a new message using chatlib, wanted code and message.
	Add the socket and the message to the list 'message_to_send'
	Parameters: conn (socket object), code (str), data (str)
	Returns: Nothing
	"""
	global messages_to_send
	msg = chatlib.build_message(code, data)
	messages_to_send.append((conn, msg))


def recv_message_and_parse(conn):
	"""
	Receives a new message from given socket,
	then parses the message using chatlib.
	Parameters: conn (socket object)
	Returns: cmd (str) and data (str) of the received message.
	If error occurred, will return None, None
	"""
	try:
		full_msg = conn.recv(1024).decode()
		cmd, data = chatlib.parse_message(full_msg)
		print("[CLIENT] ", full_msg)  # Debug print
		return cmd, data
	except Exception as e:
		print('some error')
		print(e)
		return None, None


# Data Loaders #

def gather_answers(correct_answer, incorrect_answers, correct_question_index):
	answers = []
	for i in range(1, 5):
		if i == correct_question_index:
			answers.append(correct_answer)
		else:
			answers.append(incorrect_answers[0])
			incorrect_answers.pop(0)
	return answers


def load_questions_from_web():
	global questions
	response = requests.get(url="https://opentdb.com/api.php?amount=50&type=multiple")
	payload = response.json()["results"]
	for q in payload:
		question = chatlib.parse_notation(q['question'])
		correct_answer = q['correct_answer']
		incorrect_answers = q['incorrect_answers']
		rand = random.randint(1, 4)
		answers = gather_answers(correct_answer, incorrect_answers, rand)
		questions[chatlib.generate_question_number().__next__()] = {"question": question, "answers": answers, "correct": rand}


def load_user_database():  # TODO: implement
	"""
	Loads users list from file	## FILE SUPPORT TO BE ADDED LATER
	Recieves: -
	Returns: user dictionary
	"""
	users = {
		"test": {"password": "test", "score": 0, "questions_asked": []},
		"yossi": {"password": "123", "score": 50, "questions_asked": []},
		"master": {"password": "master", "score": 200, "questions_asked": []}
	}
	return users


# SOCKET CREATOR

def setup_socket():
	"""
	Creates new listening socket and returns it
	Receives: -
	Returns: the socket object
	"""
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind((SERVER_IP, SERVER_PORT))
	sock.listen()
	print("Server is up and listening for users...")
	return sock


def send_error(conn, error_msg):
	"""
	Send error message with given message
	Receives: socket, message error string from called function
	Returns: None
	"""
	try:
		build_and_send_message(conn, "ERROR", error_msg)
	except ConnectionAbortedError as cae:
		raise cae


##### MESSAGE HANDLING


def handle_getscore_message(conn, username):
	global users
	score = (users[username])["score"]
	build_and_send_message(conn, chatlib.PROTOCOL_SERVER["score"], str(score))


def handle_highscore_message(conn):
	global users
	all_score = [[user, users[user]["score"]] for user in users]
	all_score.sort(key=itemgetter(1), reverse=True)
	data = [join_list_to_str(x) for x in all_score]
	build_and_send_message(conn, chatlib.PROTOCOL_SERVER["all_score"], "\n".join(data))


def join_list_to_str(my_list):
	output = ""
	for x in my_list:
		output = output + str(x) + ": "
	return output[:-2]


def handle_logout_message(conn):
	"""
	Closes the given socket and remove the user from the logged users
	Receives: socket
	Returns: None
	"""
	global logged_users, client_sockets
	logged_users.pop(conn.__str__())
	build_and_send_message(conn, chatlib.PROTOCOL_CLIENT["logout_msg"], "LOGOUT")
	client_sockets.remove(conn)
	conn.close()


def handle_login_message(conn, data):
	"""
	Gets socket and message data of login message. Checks  user and pass exists and match.
	If not - sends error and finished. If all ok, sends OK message and adds user and address to logged_users
	Receives: socket, message code and data
	Returns: None (sends answer to client)
	"""
	global users
	global logged_users

	try:
		[user, password, mode] = chatlib.split_data(data, 2)
		user_mode = chatlib.convert_user_mode(mode)

		if user not in users.keys() or users[user]["password"] != password:
			send_error(conn, "Incorrect username or password")
			return False
		elif user in logged_users.values():
			send_error(conn, f'{user} is already logged in')
			return False
		elif user_mode and not users[user]["isCreator"]:
			send_error(conn, f"{user} is not permitted to log in to creator mode")
			return False
		else:
			logged_users[conn.__str__()] = user
			build_and_send_message(conn, chatlib.PROTOCOL_SERVER["login_ok_msg"], "")
			return True

	except AttributeError as e:
		send_error(conn, "Incorrect username or password")
		return False


def handle_logged_message(conn):
	global logged_users
	build_and_send_message(conn, chatlib.PROTOCOL_SERVER["logged_msg"], ','.join(logged_users.values()))


def create_random_question(user):
	"""
	randomly choose a question which @user hasn't been asked
	:param user: the user who asked a question
	:return: a question number and the question data
	:rtype: int, str
	"""
	global questions, users
	# check if all questions have been asked
	if len(users[user]['questions_asked']) == len(questions):
		return None, None
	question_data = random.choice(list(questions.items()))
	question_number = question_data[0]

	# check whether the user were asked this question
	while question_number in users[user]["questions_asked"]:
		question_data = random.choice(list(questions.items()))
		question_number = question_data[0]

	question = question_data[1]['question']
	answer = '#'.join((question_data[1])['answers'])
	return question_number, str(question_number) + '#' + question + '#' + answer


def handle_question_message(conn):
	global users, logged_users
	user = logged_users[conn.__str__()]

	question_number, question = create_random_question(user)
	if question_number is None:
		send_error(conn, "No more questions")
		return

	users[user]['questions_asked'].append(question_number)
	build_and_send_message(conn, chatlib.PROTOCOL_SERVER['question'], question)


def handle_answer_message(conn, user, ans):
	global users, questions
	ans_list = chatlib.split_data(ans, 1)
	correct_answer = questions[int(ans_list[0])]['correct']
	if correct_answer == int(ans_list[1]):
		users[user]['score'] += 5
		build_and_send_message(conn, chatlib.PROTOCOL_SERVER['correct'])
	else:
		build_and_send_message(conn, chatlib.PROTOCOL_SERVER['wrong'])


def handle_add_question(conn, data):
	global questions
	question_data = chatlib.split_data(data, 2)
	question_to_add = {'question': question_data[0], 'answers': question_data[1].split('$'), 'correct': question_data[2]}
	questions[chatlib.generate_question_number().__next__()] = question_to_add
	build_and_send_message(conn, chatlib.PROTOCOL_SERVER["add_succ"])


def handle_client_message(conn, cmd, data):
	"""
	Gets message code and data and calls the right function to handle command
	Receives: socket, message code and data
	Returns: None
	"""
	global logged_users
	if cmd == "LOGIN":
		return handle_login_message(conn, data)

	match cmd:
		case "LOGOUT":
			handle_logout_message(conn)
			return True
		case "GET_QUESTION":
			handle_question_message(conn)
			return True
		case "SEND_ANSWER":
			handle_answer_message(conn, logged_users[conn.__str__()], data)
			return True
		case "MY_SCORE":
			handle_getscore_message(conn, logged_users[conn.__str__()])
			return True
		case "HIGHSCORE":
			handle_highscore_message(conn)
			return True
		case "LOGGED":
			handle_logged_message(conn)
			return True
		case "ADD_QUESTION":
			handle_add_question(conn, data)
			return True
		case _:
			try:
				send_error(conn, "Error")
				return False
			except ConnectionAbortedError as cae:
				raise cae


def main():
	global users, questions, client_sockets, messages_to_send
	load_questions_from_web()
	print("Welcome to Trivia Server!\n")

	server_socket = setup_socket()

	while True:  # TODO: fix bug which call every event handler twice
		ready_to_read, ready_to_write, in_error = select.select([server_socket] + client_sockets, client_sockets, [])

		# sending every message to its recipient
		for message in messages_to_send:
			curr_sock, data_to_send = message
			if curr_sock in ready_to_write:
				try:
					curr_sock.send(data_to_send.encode())
					print("[SERVER] ", data_to_send)  # Debug print
				except ConnectionAbortedError as cae:
					# check if the client has already logged in yet
					if logged_users.__contains__(curr_sock.__str__()):
						logged_users.pop(curr_sock.__str__())

					client_sockets.remove(curr_sock)
					curr_sock.close()
				finally:
					messages_to_send.remove(message)

		# reading the messages that every socket sent to the server
		for curr_sock in ready_to_read:
			# first time connecting
			if curr_sock is server_socket:
				(client_socket, client_address) = curr_sock.accept()
				print("Client connected!", client_address)
				client_sockets.append(client_socket)
				try:
					cmd, data = recv_message_and_parse(client_socket)
					handle_client_message(client_socket, cmd, data)
				except Exception as e:
					print("Unappropriated log out occurred")
					try:
						client_sockets.remove(client_socket)
						if logged_users.__contains__(curr_sock.__str__()):
							logged_users.pop(curr_sock.__str__())
						client_socket.close()
					except Exception as e:
						print(e)
			else:
				try:
					cmd, data = recv_message_and_parse(curr_sock)
					handle_client_message(curr_sock, cmd, data)
				except ConnectionAbortedError as cae:
					print(logged_users[curr_sock.__str__()], "suddenly left the game")
					client_sockets.remove(curr_sock)
					logged_users.pop(curr_sock.__str__())
					curr_sock.close()


if __name__ == '__main__':
	main()
