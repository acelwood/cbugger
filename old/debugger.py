import sublime
import sublime_plugin

import sys
import time
from os import listdir, path
import json
import imp

import Debugger.src.shell

imp.reload(Debugger.src.shell)

from Debugger.src.shell import ShellHandler
# import re

# import paramiko 
# import subprocess
# import threading

breakpoints = []

executable_file = None

# ssh = None
# make this a class to be able to access channel, stdin, stdout
shell = None
server_file = None

class StartDebuggerCommand(sublime_plugin.TextCommand):
	def run(self, edit, local):

		if local == "True":
			self.start_local_debugger(edit)
		else:
			self.start_remote_debugger(edit)


	def start_remote_debugger(self, edit):
		# self.view.insert(edit, 0, "Open remote executable")

		# using SFTP directory
		package_path = path.expanduser("~/Library/Application Support/Sublime Text 3/Packages/")
		remote_setup_path = package_path + "User/sftp_servers"
		# remote_setup_path = "User/sftp_servers"
		# make into list of lists to display actual path or hostname?
		remotes = [f for f in listdir(remote_setup_path)]
		remote_file = None

		# put this in another file like a real programmer
		def call_remote(index):
			# error handling
			if index == -1:
				return

			global server_file
			server_file = remotes[index]

			remote_file = remote_setup_path + '/' + remotes[index]
			with open(remote_file, 'r') as file:
				fixed = [line for line in file if (line.lstrip() != "" and not line.lstrip().startswith('//'))]
				if(fixed[-2].strip().endswith(",")):
					fixed.insert(len(fixed)-1, "\t\"dummy_json\": true\n")
				fixed_json = ''.join(fixed)

				server = json.loads(fixed_json)

			self.open_remote(server)
		# END OF CALL REMOTE FUNCTION		

		# fix menu design!
		sublime.active_window().show_quick_panel(remotes, call_remote)

	
	# MOVE THIS INTO ANOTHER FILE
	# maybe a class like the example???
	def open_remote(self, server):
		
		shell = ShellHandler(server["host"], server["user"], server["password"])

		dir_path = self.view.file_name().split(server_file)
		if len(dir_path) > 1:
			directory = path.dirname(dir_path[1])
			cmd = "cd" + directory
			shell.execute(cmd)

		cmd = "ls -1a"
		_, stdout, stderr,_ = shell.execute(cmd)

		remote_list = stdout

		def choose_remote(index):
			if index == -1:
				return

			# # try:
			nonlocal remote_list

			_, stdout, stderr, exit = shell.execute("cd "+ remote_list[index])
			# stdin,stdout,stderr=ssh.exec_command("cd "+ remote_list[index])
			# # blocking recv
			# exit = stdout.channel.recv_exit_status()

			if exit == 0:
				_,stdout,stderr,_= shell.execute("ls -1a")
				remote_list = stdout
				sublime.active_window().show_quick_panel(remote_list, choose_remote)
			else:
				global executable_file
				executable_file = remote_list[index]
				
				launch_remote_debugger()
	

		# END OF CHOOSE LOCAL FUNCTION
			
		sublime.active_window().show_quick_panel(remote_list, choose_remote)


	def start_local_debugger(self, edit):
		# self.view.insert(edit, 0, "Open local executable")
		# print(path.dirname(self.view.file_name()))
		if self.view.file_name() is None:
			sublime.error_message("Select which file to debug by making sure you clicked in it")
			return

		local_folder = path.dirname(self.view.file_name())
		local = [f for f in listdir(local_folder)]

		def choose_local(index):
			if index == -1:
				return

			nonlocal local_folder
			nonlocal local
			local_folder += "/" + local[index]

			if path.isdir(local_folder):
				local = [f for f in listdir(local_folder)]
				sublime.active_window().show_quick_panel(local, choose_local)
			else:
				global executable_file
				executable_file = local_folder
				self.open_local()

		# END OF CHOOSE LOCAL FUNCTION
			
		sublime.active_window().show_quick_panel(local, choose_local)


	def open_local(self):

		# potentially choose debug tool based on OS 
		# or let user pick
		global executable_file 

		# NEED TO PUT THIS IN ANOTHER THREAD
		# HOLY SHIT PARALLEL PROGRAMMING IS USEFUL
		proc = subprocess.Popen(["lldb", executable_file], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		# detect error if executable not chosen
		if proc.stderr.readline():
			executable_file = None
			sublime.error_message("The file you have chosen is not a valid executable or has permissions errors")
			# close process
			proc.terminate() # cleaner/better to send signal???
			return
			# return


class RunDebuggerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		if executable_file is None:
			sublime.error_message("Please choose an executable")
			return

		print("Executable is: " + executable)

		# self.view.insert(edit, 0, "Run the debugger")


# also it's going to break as soon as the line numbers shift
class SetBreakpointCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		point = [s for s in self.view.sel()]
		line_number = self.view.rowcol(self.view.sel()[0].begin())[0] + 1
		key = "breakpoint" + str(line_number)
		breakpoints.append(line_number)
		self.view.add_regions(key, point, "mark", "Packages/Debugger/img/red_hex_smallest.png", sublime.HIDDEN | sublime.PERSISTENT)

class ClearBreakpointCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		point = [s for s in self.view.sel()]
		line_number = self.view.rowcol(self.view.sel()[0].begin())[0] + 1
		key = "breakpoint" + str(line_number)
		breakpoints.remove(line_number)
		self.view.run_command("clear_bookmarks", {"name" : key})

# when view is modified
# FIX THIS: remove breakpoints?
class DebuggerEventListener(sublime_plugin.EventListener):
	def on_modified(self, view):
		if len(breakpoints) > 1 and executable_file is not None:
			sublime.error_message("Source file no longer matches executable")

	

	



