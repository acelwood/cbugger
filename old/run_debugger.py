import sublime
import sublime_plugin


class RunDebuggerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.insert(edit, 0, "Run the debugger")


class SetDebuggerInputCommand(sublime_plugin.TextCommand):
	def run(self, edit, isStdIn, isFile):
		if shell is None:
			# actually should you have to???
			sublime.error_message("Please launch the debugger first")
			return

		# do nothing, use defaults from class init
		def on_cancel():
			pass

		if isStdIn == "True":
			if isFile == "True":
				file_list = shell.execute_separate("ls -1a")
	
				# potentially add navigation
				def choose_file(index):
					if index == -1:
						return
					shell.set_input_file(file_list[index])		
				
				sublime.active_window().show_quick_panel(file_list, choose_file)

			else:
				def get_input_line(string):
					shell.set_here_doc(string)

				sublime.active_window().show_input_panel("Standard input", "", get_input_line, None, on_cancel)

		else:
			def get_line(string):
				shell.set_cmd_line_args(string)

			sublime.active_window().show_input_panel("Command line", "", get_line, None, on_cancel)