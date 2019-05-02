import sublime
import sublime_plugin


class RunDebuggerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.insert(edit, 0, "Run the debugger")


