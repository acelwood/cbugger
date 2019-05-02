import sublime
import sublime_plugin


class LoadDebuggerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.insert(edit, 0, "Load the executable")
		
		# how to get PASSWORD
		# ssh = subprocess.Popen(["ssh", remote, "ls"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
		# # while True:
		# # 	line = 
		# # ssh.communicate
		# # files = [line for ]
		# print(ssh.stdout.readline())
		# print(ssh.stdout.readline())
		# print(ssh.stdout.readline())

		# print(ssh.stderr.readline())

		# # global ssh
		# ssh.terminate()

	def open_remote(self, server):
		# check universal newlines, shell variable, more?
		remote = server["user"] + "@" + server["host"]
		print(remote)
		# print(server["password"])
		
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

		ssh.connect(server["host"], username=server["user"], password=server["password"], timeout=30)
		stdin,stdout,stderr=ssh.exec_command("ls -a")

		remote_list=stdout.readlines()
		path = "~" # edit for where file is !!! 

		# shell.close_shell()
		# stdin.write(cmd + '\n')
		# # time.sleep(0.1)
		# finish = 'end of stdOUT buffer. finished with exit status'
		# echo_cmd = 'echo {} $?'.format(finish)
		# stdin.write(echo_cmd + '\n')

		# stdin.flush()
		# time.sleep(0.1)

		# shout = []
		# sherr = []
		# exit_status = 0
		# for line in stdout:
		# 	if str(line).startswith(cmd) or str(line).startswith(echo_cmd):
		# 		# up for now filled with shell junk from stdin
		# 		shout = []
		# 	elif str(line).startswith(finish):
		# 		# our finish command ends with the exit status
		# 		exit_status = int(str(line).rsplit(maxsplit=1)[1])
		# 		if exit_status:
		# 			# stderr is combined with stdout.
		# 			# thus, swap sherr with shout in a case of failure.
		# 			sherr = shout
		# 			shout = []
		# 		break
		# 	else:
		# 		# get rid of 'coloring and formatting' special characters
		# 		shout.append(re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line).
		# 					 replace('\b', '').replace('\r', ''))

		# # first and last lines of shout/sherr contain a prompt
		# if shout and echo_cmd in shout[-1]:
		# 	shout.pop()
		# if shout and cmd in shout[0]:
		# 	shout.pop(0)
		# if sherr and echo_cmd in sherr[-1]:
		# 	sherr.pop()
		# if sherr and cmd in sherr[0]:
		# 	sherr.pop(0)

		# print(shout)
		# print(sherr)

		# buff = ''
		# while finish not in buff:
		# 	if shell.recv_ready():
		# 		resp = shell.recv(9999)    
		# 		# code won't stuck here
		# 		out = resp.decode('ascii')
		# 		out = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', out).replace('\b', '').replace('\r', '')
		# 		buff+=out # ascii or utf-8
		# 		print(out)
		# 		print("ONE LOAD")

		# for line in stdout:
		# 	if str(line).startswith("ls") or str(line).startswith("echo"):
		# 		# up for now filled with shell junk from stdin
		# 		print("1: " + str(line))
		# 	elif str(line).startswith(finish):
		# 		# our finish command ends with the exit status
		# 		exit_status = int(str(line).rsplit(maxsplit=1)[1])
		# 		if exit_status:
		# 			# stderr is combined with stdout.
		# 			# thus, swap sherr with shout in a case of failure.
		# 			print("exit status "+ exit_status)
		# 			break
		# 	else:
		# 		print(line)
		# path = "~" # edit for where file is !!! 

		# ssh.close()

		def choose_remote(index):
			if index == -1:
				return

			nonlocal path, remote_list
			print(remote_list[index])

			# try:
			stdin,stdout,stderr=ssh.exec_command("cd "+ remote_list[index])
			# blocking recv
			exit = stdout.channel.recv_exit_status()

			if exit == 0:
				stdin,stdout,stderr=ssh.exec_command("ls -a")
				remote_list=stdout.readlines()
				sublime.active_window().show_quick_panel(remote_list, choose_remote)
			else:
				global executable_file
				executable_file = remote_list[index]
				stdin,stdout,stderr=ssh.exec_command("pwd")
				path=stdout.readline()
				print("Found ya " + executable_file + " at " + path)
	
				ssh.close()
				return

		# END OF CHOOSE LOCAL FUNCTION
			
		sublime.active_window().show_quick_panel(remote_list, choose_remote)


