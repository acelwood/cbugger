import sublime
import sublime_plugin

import subprocess
import threading
import json

from . import shell

# PUT THIS IN A CLASS --> MULTIPLE DEBUGGERS :OOOOOOO
breakpoints = {}

def launch_remote(executable_file, shell, source_path):

	_, stdout,_,_ = shell.execute("pwd")
	shell.current_directory = stdout[0].strip("\n")

	# ERROR CATCHING if gdb doesn't launch?
	start_gdb_cmd = "gdb -q --interpreter=mi2 " + executable_file
	_,stdout,_ = shell.execute_in_gdb(start_gdb_cmd)

	shell.executable = executable_file.strip("\n")
	
	# error handling here --> WHAT IF MORE LINES IN MESSAGE?
	msg = stdout[0]
	if msg['message'] == 'error':
		shell.executable = None
		sublime.error_message("The file you have chosen is not a valid executable or has permissions errors")
		# potentially call choose remote/open remote? although that's messy now
		return
	
	# else add breakpoints & start debugging!
	file = source_path.rsplit('/')[-1]
	shell.files.append(file)

	for num in breakpoints:
		set_breakpoint_in_gdb(shell, file, num)


def set_breakpoint_in_gdb(shell, file, num):

	set_breakpoint_cmd = "-break-insert " + file + ":" + str(num)
	_,stdout,_ = shell.execute_in_gdb(set_breakpoint_cmd)

	msg = stdout[0]
	if msg['message'] == 'error':
		if msg['payload']['msg'].startswith("No source file"):
			if file in shell.files:
				shell.files.remove(file)
			sublime.error_message("This source file does not correspond to the executable")
			return False
		else:
			print("One of your breakpoints is invalid. Moving to the next")
	else:
		breakpoints[num] = int(msg['payload']['bkpt']['number'])

	# print("shell files are "+str(shell.files))
	# print(breakpoints)
	return True


def remove_breakpoint_in_gdb(shell, file, num):
	rm_breakpoint_cmd = "-break-delete " + str(breakpoints[num])
	_,stdout,_ = shell.execute_in_gdb(rm_breakpoint_cmd)

	msg = stdout[0]
	if msg['message'] == 'error':
		print("Breakpoint does not exist") # other error possibilities?


def launch_local(executable_file):

	# potentially choose debug tool based on OS 
	# or let user pick
	proc = subprocess.Popen(["lldb", executable_file], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	
	# detect error if executable not chosen
	if proc.stderr.readline():
		executable_file = None
		sublime.error_message("The file you have chosen is not a valid executable or has permissions errors")
		# close process
		proc.terminate() # cleaner/better to send signal???
		return
		# return

	# else
	# NEED TO PUT THIS IN ANOTHER THREAD
	# HOLY SHIT PARALLEL PROGRAMMING IS USEFUL
	# temporary
	proc.terminate()


def debugger_handler(shell, panel_name, gdb_cmd):

	_,stdout,_ = shell.execute_in_running(gdb_cmd)

	# display output from program
	program_output = [line['payload'] for line in stdout if line['type'] == 'output']
	text = "".join(program_output)

	v = sublime.active_window().find_output_panel(panel_name)
	if v is None:
		v = sublime.active_window().create_output_panel(panel_name)
	# how to decide when to erase

	# display stopping message
	stopped_message = stdout[-1]
	stop_text = "\nGDB MESSAGE: "

	reason = stopped_message['payload']['reason']
	if reason == 'exited-normally':
		stop_text += "The program exited normally"

	elif reason == 'exited':
		stop_text += "The program exited with status " + str(int(stopped_message['payload']['exit-code']))

	elif reason == 'breakpoint-hit':
		# other breakpoint info???
		frame = stopped_message['payload']['frame']
		stop_text += "Breakpoint hit: in file " + frame['file'] + " at line " + frame['line']

	elif reason == 'end-stepping-range':
		# other breakpoint info???
		frame = stopped_message['payload']['frame']
		stop_text += "Next line: in file " + frame['file'] + " at line " + frame['line']

	else:
		print(stopped_message['payload'])
		print("OTHER REASON STOPPED")

	text += (stop_text + '\n')

	v.run_command("display_text_in_panel", { "text": text})
	sublime.active_window().run_command("show_panel", {"panel": "output." + panel_name})

	# BAD ORGANIZING --> another function? another class? figure out the async thing
	if reason == 'breakpoint-hit' or reason == 'end-stepping-range':
		# how to make menu more compact?
		# KEY BINDINGS!!!
		menu = ['Continue', 'Next', 'Step', 'Print', 'More']

		def menu_handler(index):
			if index == -1:
				print('Canceled')
				# DO SOMETHING ELSE TO BE ABLE TO PICK BACK UP
				return

			# continue
			# later specify how many # of times
			if index == 0:
				# sublime.active_window().run_command("continue_debugger", {"gdb_cmd" : "-exec-continue"})
				debugger_handler(shell, panel_name, "-exec-continue")

			elif index == 1:
				# sublime.active_window().run_command("continue_debugger", {"gdb_cmd" : "-exec-next"})
				debugger_handler(shell, panel_name, "-exec-next")

			elif index == 2:
				#sublime.active_window().run_command("run_debugger", {"gdb_cmd" : "-exec-step"})
				debugger_handler(shell, panel_name, "-exec-step")

			elif index == 3:
				#sublime.active_window().run_command("run_debugger", {"gdb_cmd" : "-exec-next"})
				# DO MORE WITH PRINTING FUN STUFF
				_,stdout,_ = shell.execute_in_gdb("-stack-list-variables --all-values")

				for var in shell.variables:
					print(var)

				print("Variable values")
				for line in stdout:
					print(line)

				# redisplay menu
				sublime.active_window().show_quick_panel(menu, menu_handler)

			elif index == 4:
				#sublime.active_window().run_command("run_debugger", {"gdb_cmd" : "-stack-list-frames"})
				_,stdout,_ = shell.execute_in_gdb("-stack-list-frames")
				print("Backtrace")
				for line in stdout:
					print(line)

				# redisplay menu
				sublime.active_window().show_quick_panel(menu, menu_handler)

		# one potential issue: menu disappears quickly if select anywhere else
		sublime.active_window().show_quick_panel(menu, menu_handler)


