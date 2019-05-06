import sublime
import sublime_plugin

import sys
import time
from os import listdir, path
import json
import imp
import re
import html

import Cbugger.src.shell
import Cbugger.src.debugger
import Cbugger.src.phantoms

imp.reload(Cbugger.src.shell)
imp.reload(Cbugger.src.debugger)
imp.reload(Cbugger.src.phantoms)

from Cbugger.src.shell import GDBHandler
from Cbugger.src.debugger import *
from Cbugger.src.phantoms import *

shell = None

class StartDebuggerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		clear_all_phantoms(self.view, edit)
		self.start_remote_debugger(edit)

	def start_remote_debugger(self, edit):
		# using SFTP directory
		# again this is only for Mac? Maybe Linux too?
		package_path = path.expanduser("~/Library/Application Support/Sublime Text 3/Packages/")
		remote_setup_path = package_path + "User/sftp_servers"
		# remote_setup_path = "User/sftp_servers"
		# make into list of lists to display actual path or hostname?
		# CHOOSE REMOTE FROM SFTP PATH NAME 
		# UNLESS YOU WANT TO MAKE OTHER PARTS RELY ON THAT
		remotes = [f for f in listdir(remote_setup_path)]
		remote_file = None

		# put this in another file like a real programmer
		def call_remote(index):
			# error handling
			if index == -1:
				return

			server_file = remotes[index]

			remote_file = remote_setup_path + '/' + remotes[index]
			with open(remote_file, 'r') as file:
				fixed = [line for line in file if (line.lstrip() != "" and not line.lstrip().startswith('//'))]
				if(fixed[-2].strip().endswith(",")):
					fixed.insert(len(fixed)-1, "\t\"dummy_json\": true\n")
				fixed_json = ''.join(fixed)

				server = json.loads(fixed_json)

			self.open_remote(server, server_file)
		# END OF CALL REMOTE FUNCTION		

		# fix menu design!
		sublime.active_window().show_quick_panel(remotes, call_remote)

	
	# MOVE THIS INTO ANOTHER FILE
	# maybe a class like the example???
	def open_remote(self, server, server_file):
		
		global shell
		shell = GDBHandler(server["host"], server["user"], server["password"])

		file_name = self.view.file_name()
		if file_name is not None:
			file_name = file_name.rsplit('/')[-1]

		def get_file_name(string):
			nonlocal file_name
			file_name = string

		def no_file_name():
			nonlocal file_name
			file_name = "ERROR BAD FILE"

		if file_name is None:
			sublime.active_window().show_input_panel("Enter the file name", "", get_file_name, None, no_file_name)
		while file_name is None:
			pass

		if len(file_name.split(' ')) > 1:
			sublime.error_message("Please enter a valid file name")
			shell.close()
			return

		dir_path = self.view.file_name().split(server_file)
		file_name = dir_path[0]
	
		if len(dir_path) > 1:
			directory = path.dirname(dir_path[1])
			cmd = "cd " + directory
			_, stdout, _, exit = shell.execute(cmd)
			if exit != 0:
				sublime.error_message("Not a valid directory")
			file_name = dir_path[1]

		cmd = "ls -1a"
		_, stdout,_,_ = shell.execute(cmd)

		remote_list = stdout

		def choose_remote(index):
			if index == -1:
				return

			nonlocal remote_list

			_, stdout, stderr, exit = shell.execute("cd "+ remote_list[index])

			if exit == 0:
				_,stdout,stderr,_= shell.execute("ls -1a")
				remote_list = stdout
				sublime.active_window().show_quick_panel(remote_list, choose_remote)
			else:				
				launch_remote(remote_list[index], shell, file_name)
		
		# END OF CHOOSE REMOTE FUNCTION
			
		sublime.active_window().show_quick_panel(remote_list, choose_remote)
		# continues asynchronously

# also it's going to break as soon as the line numbers shift
class SetBreakpointCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		point = [s for s in self.view.sel()]
		line_number = self.view.rowcol(self.view.sel()[0].begin())[0] + 1
		key = "breakpoint" + str(line_number)
		# don't add if it's already there
		if line_number in breakpoints:
			return

		file = self.view.file_name().rsplit('/')[-1] 

		breakpoints[line_number] = {'num': -1, 'enabled': True, 'file': file}
		self.view.add_regions(key, point, "mark", "Packages/Cbugger/img/red_hex_smallest.png", sublime.HIDDEN | sublime.PERSISTENT)
	
		if shell is not None:
			success = set_breakpoint_in_gdb(shell, line_number)
			
			if success and file not in shell.files:
				shell.files.append(file)

		print(breakpoints)


class ClearBreakpointCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		point = [s for s in self.view.sel()]
		line_number = self.view.rowcol(self.view.sel()[0].begin())[0] + 1
		key = "breakpoint" + str(line_number)
		self.view.run_command("clear_bookmarks", {"name" : key})

		if shell is not None and line_number in breakpoints:
			file = self.view.file_name().rsplit('/')[-1] # check this
			remove_breakpoint_in_gdb(shell, file, line_number)
		
		if line_number in breakpoints:
			breakpoints.pop(line_number)

		print(breakpoints)


# when view is modified --> maybe should have used ViewEventListener
class DebuggerEventListener(sublime_plugin.EventListener):
	def on_modified(self, view):
	
		if view.file_name() is not None and len(breakpoints) > 0:
			file = view.file_name().rsplit('/')[-1]
			if shell is not None and file not in shell.files:
				return

			for brkpt in breakpoints:
				if breakpoints[brkpt]['file'] != file:
					print("Not for this file")
					continue

				breakpoint_name = "breakpoint" + str(brkpt)
				if len(view.get_regions(breakpoint_name)) == 0:
					print("Breakpoint not found: "+breakpoint_name)
					continue 

				line = view.get_regions(breakpoint_name)[0]
				num = view.rowcol(line.begin())[0] + 1

				# lines have been modified
				if num != brkpt:
					# remove old breakpoint
					view.run_command("clear_bookmarks", {"name" : breakpoint_name})
					enabled = breakpoints[brkpt]['enabled']
					if shell is not None and file in shell.files:
						remove_breakpoint_in_gdb(shell, file, brkpt)
					breakpoints.pop(brkpt)

					# set new breakpoint
					key = "breakpoint" + str(num)
					breakpoints[num] = {'num': -1, 'enabled': enabled, 'file': file}
					view.add_regions(key, [line], "mark", "Packages/Cbugger/img/red_hex_smallest.png", sublime.HIDDEN | sublime.PERSISTENT)			
					
					if shell is not None and file in shell.files:
						success = set_breakpoint_in_gdb(shell, num)
						if breakpoints[num]['enabled'] == False:
							_,stdout,_ = shell.execute_in_gdb("-break-disable " + str(breakpoints[num]['num']))
						
					print(breakpoints)
			# sublime.error_message("Source file no longer matches executable")


# NEED TO EXPAND THIS FOR LOCAL: want to be able to set & display etc
class SetDebuggerInputCommand(sublime_plugin.TextCommand):
	def run(self, edit, isStdIn):
		if shell is None:
			# actually should you have to???
			sublime.error_message("Please launch the debugger first")
			return

		# do nothing, use defaults from class init
		def on_cancel():
			pass

		if isStdIn == "True":
			_,stdout,_,_ = shell.execute_separate("ls -1a")
			file_list = stdout.readlines()

			# potentially add navigation
			def choose_file(index):
				if index == -1:
					return
				shell.set_input_file(file_list[index])		
			
			sublime.active_window().show_quick_panel(file_list, choose_file)

		else:
			def get_line(string):
				shell.set_cmd_line_args(string)

			sublime.active_window().show_input_panel("Command line", "", get_line, None, on_cancel)


# WEIRD RECOMPILE BUG WHERE IT SEEMS TO EXECUTE MAKE IN A DIFFERENT THING
# ALSO CD HAS TOO MANY ARGS ISSUE
# TRY TO REPLICATE ANOTHER TIME
class RecompileExecutableCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		if shell is None:
			sublime.error_message("Please choose an executable to compile")
			return

		clear_all_phantoms(self.view, edit)
		# expand to more customizable (not just make, make + exe name, make in a different folder?)
		_,stdout,stderr,exit_status = shell.execute_separate("make")

		stdout = stdout.readlines()
		stderr = stderr.readlines()
		panel_name = 'make'

		# how to display warnings
		if exit_status != 0:
			# panel_name = 'make'
			error_text = "".join(stderr)

			# HOW TO MAKE PRETTY COLORS FOR ERRORS
			v = sublime.active_window().create_output_panel(panel_name)
			v.run_command("display_text_in_panel", { "text": error_text})
				
			if sublime.active_window().active_panel() != panel_name:
				sublime.active_window().run_command("show_panel", {"panel": "output." + panel_name})

			# phantom_set = sublime.PhantomSet(self.view, "make")
			# phantoms = []

			# file = self.view.file_name().rsplit('/')[-1] 
			# for line in stderr:
			# 	# right now only display in current file
			# 	tokens = line.split(":") 
			# 	if tokens[0] != file or not tokens[1].isdigit() or len(tokens) < 5:
			# 		continue

			# 	line_num = int(tokens[1])
			# 	region_start = self.view.text_point(line_num, 0)
			# 	region_end = self.view.text_point(line_num + 1, 0) - 2

			# 	print(tokens)
			# 	print(region_start)
			# 	print(region_end)

			# 	# def on_phantom_navigate(url):
			# 	# 	print("Navigated")
			# 		# hide phantoms
			# 		#self.view.erase_phantoms("make")
					
			# 	text = tokens[4]

			# 	if tokens[3].lstrip().startswith('error'):
			# 		message = "\t\t// COMPILER ERROR: " + tokens[4].strip("\n")

			# 		self.view.insert(edit, region_end, message)
			# 		inserted = sublime.Region(region_end, region_end+len(message))
			# 		compiler_phantoms.append(inserted)
			# 		# phantom = sublime.Phantom(sublime.Region(region_start, region_end),
			# 		# 					('<body id=inline-error>' + stylesheet +
			#   #                           '<div class="error-arrow"></div><div class="error">' +
			#   #                           '<span class="message">' + html.escape(text, quote=False) + '</span>' +
			#   #                           '<a href=hide>' + chr(0x00D7) + '</a></div>' +
			#   #                           '</body>'),
			#   #                           sublime.LAYOUT_INLINE,
			#   #                           on_phantom_navigate)

			# 		# print(phantom)
			# 		# phantoms.append(phantom)

			# 	elif tokens[3].lstrip().startswith('warning'):
			# 		message = "\t\t// COMPILER WARNING: " + tokens[4].strip("\n")

			# 		self.view.insert(edit, region_end, message)
			# 		inserted = sublime.Region(region_end, region_end+len(message))
			# 		compiler_phantoms.append(inserted)

			# phantom_set.update(phantoms)
			sublime.error_message("Make failed")


		else:
			# panel_name = 'debug'
			text = "CBUGGER MESSAGE: successfully recompiled\n"

			if len(stderr) > 0:
				text += "With Warnings:\n"
				for line in stderr:
					text += line

			# HOW TO MAKE APPROPRIATE SIZE
			v = sublime.active_window().create_output_panel(panel_name)
			# print success message
			v.run_command("display_text_in_panel", { "text": text})
				
			if sublime.active_window().active_panel() != panel_name:
				sublime.active_window().run_command("show_panel", {"panel": "output." + panel_name})



class DisplayTextInPanelCommand(sublime_plugin.TextCommand):
	def run(self, edit, text):
		self.view.insert(edit, self.view.size(), text)

class ClearPanelCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.erase(edit, sublime.Region(0, self.view.size()))


# actually refactor this to pass in -exec-run to something else that gets called
class RunDebuggerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		if shell is None:
			sublime.active_window().run_command("start_debugger")
			#self.view.run_command
			#sublime.error_message("Please choose an executable to run")
			return

		clear_all_phantoms(self.view, edit)

		panel_name = 'debug'
		v = sublime.active_window().create_output_panel(panel_name)

		set_args_in_gdb(shell)

		gdb_cmd = "-exec-run"
		debugger_handler(shell, self.view, panel_name, gdb_cmd)

	
class SetupPrintingCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		if shell is None:
			sublime.error_message("Please choose an executable before variables")
			return

		# meh
		if len(shell.variables) < 1:
			sublime.error_message("Enter a comma or space separated list of variable names")

		def on_cancel():
			return

		def get_line(string):
			variables = re.split(",\s*|\s+", string) 
			if variables[-1] == '':
				variables.pop()

			# print("Extracted" + str(variables))
			shell.add_variables(variables)

		sublime.active_window().show_input_panel("Variables", "", get_line, None, on_cancel)





