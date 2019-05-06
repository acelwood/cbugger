import sublime
import sublime_plugin

import subprocess
import threading
import json
import re

from . import shell

# PUT THIS IN A CLASS --> MULTIPLE DEBUGGERS :OOOOOOO
breakpoints = {}

menu = ['Continue', 'Next', 'Step', 'Print', 'More']
secondary_menu = ['Backtrace', 'Print All', 'Add Vars', 'Remove Vars', 'Disable Breakpoint', 'Enable Breakpoint', 'Back to Main Menu']


def launch_remote(executable_file, shell, source_path):

	_, stdout,_,_ = shell.execute("pwd")
	shell.current_directory = stdout[0].strip("\n")

	# ERROR CATCHING if gdb doesn't launch?
	start_gdb_cmd = "gdb -q --interpreter=mi2 "
	_,stdout,_ = shell.execute_in_gdb(start_gdb_cmd)

	set_exe_cmd = "-file-exec-and-symbols " + executable_file
	_,stdout,_ = shell.execute_in_gdb(set_exe_cmd)

	# error handling here --> WHAT IF MORE LINES IN MESSAGE?
	msg = stdout[-1]
	print(msg)
	if msg['message'] == 'error': # or msg['payload'].contains("not in executable format"):
		shell.executable = None
		sublime.error_message("The file you have chosen is not a valid executable or has permissions errors")
		# potentially call choose remote/open remote? although that's messy now
		return
	
	shell.executable = executable_file.strip("\n")
	
	# else add breakpoints & start debugging!
	file = source_path.rsplit('/')[-1]
	shell.files.append(file)

	for num in breakpoints:
		set_breakpoint_in_gdb(shell, num)


def set_breakpoint_in_gdb(shell, num):

	file = breakpoints[num]['file']
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
		breakpoints[num]['num'] = int(msg['payload']['bkpt']['number'])

	return True


def remove_breakpoint_in_gdb(shell, file, num):
	rm_breakpoint_cmd = "-break-delete " + str(breakpoints[num]['num'])
	_,stdout,_ = shell.execute_in_gdb(rm_breakpoint_cmd)

	msg = stdout[0]
	if msg['message'] == 'error':
		print("Breakpoint does not exist") # other error possibilities?


def set_args_in_gdb(shell):

    set_args_cmd = "-exec-arguments " + shell.command_line_args
    if shell.stdin_file is not None:
        set_args_cmd += (" < " + shell.stdin_file)

    _,stdout,_ = shell.execute_in_gdb(set_args_cmd)
    print(set_args_cmd)
    print(stdout)


def debugger_handler(shell, view, panel_name, gdb_cmd):

	_,stdout,_ = shell.execute_in_running(gdb_cmd)
	if len(stdout) == 0:
		sublime.error_message("Connection broken")
		return

	# display output from program
	program_output = [line['payload'] for line in stdout if line['type'] == 'output']
	text = "".join(program_output)

	v = sublime.active_window().find_output_panel(panel_name)
	if v is None:
		v = sublime.active_window().create_output_panel(panel_name)
	# how to decide when to erase

	# display stopping message
	stopped_message = stdout[-1]
	stop_text = "\nCBUGGER MESSAGE: "

	reason = stopped_message['payload']['reason']
	if reason == 'exited-normally':
		stop_text += "The program exited normally"

	elif reason == 'exited':
		stop_text += "The program exited with status " + str(int(stopped_message['payload']['exit-code']))

	elif reason == 'breakpoint-hit':
		# other breakpoint info???
		frame = stopped_message['payload']['frame']
		stop_text += "Breakpoint hit: " + frame['file'] + ":" + frame['line'] + " - " + frame['func']

	elif reason == 'end-stepping-range':
		frame = stopped_message['payload']['frame']
		# for next or step
		stop_text += "Next line: " + frame['file'] + ":" + frame['line'] + " - " + frame['func']

	elif reason == 'signal-received':
		# seg fault handle
		if stopped_message['payload']['signal-name'] == 'SIGSEGV':
			stop_text += "SEGMENTATION FAULT"
			# don't print variables
			reason = 'exited'
		else:
			stop_text += "Signal Received: " + stopped_message['payload']['signal-meaning']
	
	else:
		print("OTHER REASON STOPPED")
		print(stopped_message['payload'])

	text += (stop_text + '\n')

	# display preset variables if at breakpoint
	if not reason.startswith('exited'):

		_,stdout,_ = shell.execute_in_gdb("-stack-list-variables --all-values")
		variables = stdout[-1]['payload']['variables'] # error handling
		var_text = ""
		var_seen = False

		# if len(shell.variables) > 0:
		for var in variables:
			if var['name'] in shell.variables:
				var_seen = True
				var_text += ("CBUGGER: " + var['name'] + " = " + var['value'] + "\n")

		# display variables on this line
		line_num = int(stopped_message['payload']['frame']['line'])
		region_start = view.text_point(line_num - 1, 0)
		line_string = view.substr(view.line(region_start))
		line_tokens = line_string.split()
		
		for var in variables:
			if var['name'] in line_tokens:
				var_seen = True
				var_text += ("CBUGGER: " + var['name'] + " = " + var['value'] + "\n")

		if var_seen:
			text += "CBUGGER MESSAGE: Variable values - note that current line has not executed\t(watch out for uninitialized)\n"
			text += var_text


	v.run_command("display_text_in_panel", { "text": text})

	if sublime.active_window().active_panel() != panel_name:
		sublime.active_window().run_command("show_panel", {"panel": "output." + panel_name})

	# BAD ORGANIZING --> another function? another class? figure out the async thing
	# how to make menu more compact?
	# if reason == 'breakpoint-hit' or reason == 'end-stepping-range':
	if not reason.startswith('exited'):
		# KEY BINDINGS!!!
		global menu
		def menu_handler_wrapper(index):
			menu_handler(shell, view, panel_name, index)

		# one potential issue: menu disappears quickly if select anywhere else
		sublime.active_window().show_quick_panel(menu, menu_handler_wrapper)

def menu_handler(shell, view, panel_name, index):
	global menu, secondary_menu
	def menu_handler_wrapper(index):
		menu_handler(shell, view, panel_name, index)

	def secondary_menu_handler_wrapper(index):
		secondary_menu_handler(shell, view, panel_name, index)
	

	if index == -1:
		# redisplay
		sublime.active_window().show_quick_panel(menu, menu_handler_wrapper)
		return

	if index == 0:
		# later specify how many # of times
		debugger_handler(shell, view, panel_name, "-exec-continue")

	elif index == 1:
		debugger_handler(shell, view, panel_name, "-exec-next")

	elif index == 2:
		debugger_handler(shell, view, panel_name, "-exec-step")

	elif index == 3:
		# DO MORE WITH PRINTING FUN STUFF
	
		def on_cancel(string):
			sublime.active_window().show_quick_panel(menu, menu_handler_wrapper)

		def get_name(variable_name):
			# string clean up on variable name?
			_,stdout,_ = shell.execute_in_gdb("-stack-list-variables --all-values")
			variables = stdout[-1]['payload']['variables'] # error handling

			text = "CBUGGER: "
			for var in variables:
				if var['name'] == variable_name:
					text += var['name'] + " = " + var['value'] + "\n"
			# error handling
			if text[-2] == ':':
				text += "Variable name not found in this scope\n"
			else:
				if variable_name not in shell.recent_vars:
					shell.recent_vars.append(variable_name)
					if len(shell.recent_vars) > 6:
						pop_ind = 0
						if shell.recent_vars[0] == variable_name:
							pop_ind = 1
						shell.recent_vars.pop(pop_ind) # remove oldest

			v = sublime.active_window().find_output_panel(panel_name)
			if v is None:
				v = sublime.active_window().create_output_panel(panel_name)

			v.run_command("display_text_in_panel", { "text": text})
			if sublime.active_window().active_panel() != panel_name:
				sublime.active_window().run_command("show_panel", {"panel": "output." + panel_name})

			# redisplay menu
			sublime.active_window().show_quick_panel(menu, menu_handler_wrapper)
			

		def list_get_name(index):
			if index == -1 or index == 0:
				# get variable name from user
				sublime.active_window().show_input_panel("Variable name", "", get_name, None, on_cancel)
			else:
				get_name(shell.recent_vars[index-1])

		variables_menu = ["Enter new variable"] + shell.recent_vars
		# display list of recent vars
		sublime.active_window().show_quick_panel(variables_menu, list_get_name)
		

	elif index == 4:
		# display secondary menu
		sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)


# more debugging commands
def secondary_menu_handler(shell, view, panel_name, index):
	global menu, secondary_menu
	def menu_handler_wrapper(index):
		menu_handler(shell, view, panel_name, index)

	def secondary_menu_handler_wrapper(index):
		secondary_menu_handler(shell, view, panel_name, index)

	def on_cancel():
		# redisplay menu
		sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)

	if index == -1:
		print('Canceled')
		sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)
		# DO SOMETHING ELSE TO BE ABLE TO PICK BACK UP
		return

	# Backtrace
	if index == 0:
		_,stdout,_ = shell.execute_in_gdb("-stack-list-frames")
		
		stacktrace = stdout[-1]['payload']['stack']
		text = "CBUGGER: Function call stack\n"
		for line in stacktrace:
			text += "CBUGGER: [" + line['level'] + "] " + line['fullname'] + ": " + line['line'] + "   " + line['func'] + "\n"

		v = sublime.active_window().find_output_panel(panel_name)
		v.run_command("display_text_in_panel", { "text": text})

		# redisplay menu
		sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)


	# Print all variables in stack frame
	elif index == 1:
		#sublime.active_window().run_command("run_debugger", {"gdb_cmd" : "-exec-next"})
		# DO MORE WITH PRINTING FUN STUFF
		_,stdout,_ = shell.execute_in_gdb("-stack-list-variables --all-values")

		text = "CBUGGER MESSAGE: All variables\t (watch out for uninitialized)\n"

		variables = stdout[-1]['payload']['variables'] # error handling
		for var in variables:
			text += ("CBUGGER: " + var['name'] + " = " + var['value'] + "\n")

		v = sublime.active_window().find_output_panel(panel_name)
		v.run_command("display_text_in_panel", { "text": text})
		# sublime.active_window().run_command("show_panel", {"panel": "output." + panel_name})
		# redisplay menu
		sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)

	elif index == 2:
		def get_line(string):
			variables = re.split(",\s*|\s+", string) 
			if variables[-1] == '':
				variables.pop()

			# print("Extracted" + str(variables))
			shell.add_variables(variables)
			# redisplay menu
			sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)

		sublime.active_window().show_input_panel("Variables", "", get_line, None, on_cancel)

	elif index == 3:
		remove_menu = ['Go Back', 'Enter list of variables'] + shell.variables

		def get_line(string):
			variables = re.split(",\s*|\s+", string) 
			if variables[-1] == '':
				variables.pop()
			shell.remove_variables(variables)
			# redisplay menu
			sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)

		def remove_menu_handler(index):
			if index == -1 or index == 0:
				sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)
			elif index == 1:
				sublime.active_window().show_input_panel("Variables", "", get_line, None, on_cancel)
			else:
				shell.variables.pop(index-2)
				nonlocal remove_menu
				remove_menu = ['Go Back', 'Enter list of variables'] + shell.variables
				if len(shell.variables) > 0:
					sublime.active_window().show_quick_panel(remove_menu, remove_menu_handler)
				else:
					sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)

		sublime.active_window().show_quick_panel(remove_menu, remove_menu_handler)
		
	elif index == 4:
		breakpoint_list = ['Back'] + [ ("Line " + str(num)) for num in breakpoints if breakpoints[num]['enabled']]
		breakpoint_menu = [ (num, breakpoints[num]['num']) for num in breakpoints if breakpoints[num]['enabled']]

		def disable_menu_handler(index):
			if index > 0:
				bpt_num = breakpoint_menu[index-1][1]
				bpt_line = breakpoint_menu[index-1][0]
				_,stdout,_ = shell.execute_in_gdb("-break-disable " + str(bpt_num))
				breakpoints[bpt_line]['enabled'] = False

			sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)

		sublime.active_window().show_quick_panel(breakpoint_list, disable_menu_handler)


	elif index == 5:
		breakpoint_list = ['Back'] + [ ("Line " + str(num)) for num in breakpoints if not breakpoints[num]['enabled']]
		breakpoint_menu = [ (num, breakpoints[num]['num']) for num in breakpoints if not breakpoints[num]['enabled']]

		def enable_menu_handler(index):
			if index > 0:
				bpt_num = breakpoint_menu[index-1][1]
				bpt_line = breakpoint_menu[index -1][0]
				_,stdout,_ = shell.execute_in_gdb("-break-enable " + str(bpt_num))
				breakpoints[bpt_line]['enabled'] = True

			sublime.active_window().show_quick_panel(secondary_menu, secondary_menu_handler_wrapper)

		sublime.active_window().show_quick_panel(breakpoint_list, enable_menu_handler)

	elif index == 6:
		# go back to main menu
		sublime.active_window().show_quick_panel(menu, menu_handler_wrapper)
	

		
