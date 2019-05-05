class StartDebuggerCommand(sublime_plugin.TextCommand):
	def run(self, edit, local):

		if local == "True":
			self.start_local_debugger(edit)
		else:
			self.start_remote_debugger(edit)

	def start_local_debugger(self, edit):
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
				launch_local(local_folder)

		# END OF CHOOSE LOCAL FUNCTION
		sublime.active_window().show_quick_panel(local, choose_local)

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