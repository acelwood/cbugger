**Abstract**: In computer science classes, learning how to debug a program can be just as difficult as learning 
how to write it in the first place. Due to a limited number of tools for C programs, the main debugging challenges 
for Yale students taking the core sequence are: the most popular debugger (gdb) has a steep learning curve because 
it is text-based, the results of the debugger are divorced from the code, and programs should ideally be debugged on
the Zoo where the final test scripts are run. Therefore, the purpose of this project is to provide a more intuitive 
and accessible interface for debugging C programs that displays the debugging results in relation to the code that 
produced it, and allows debugging to take place on a remote computer system. This was achieved by developing a plugin 
for Sublime Text 3, a popular text editor used by Yale students. It already has a plugin for remotely editing files, 
which was the inspiration for creating a plugin for remote debugging. The Sublime Text API provides front-end 
functionality, and the python library paramiko is used to open an SSH connection to the remote server, where gdb is
launched to perform the actual debugging commands. This plugin is currently integrated with the SFTP plugin to retrieve
information about the remote servers in order to log in. The user selects what remote server to debug on, and then 
selects what executable file to run in the debugger. From there, the user can perform most standard debugging operations 
by clicking in Sublime: setting and removing breakpoints with a right-click on a line, setting command line arguments 
and standard input files, running the debugger, selecting what to do next after hitting a breakpoint. This project 
successfully functions as a simple remote debugging tool compatible with C programs, and there are many possible 
enhancements such as integrating more gdb commands or adding valgrind capabilities.

How To Run:
To install this program on your own computer:

1. Install Sublime Text 3
2. Install the Sublime SFTP plugin
3. Download the code as a zip file from https://github.com/acelwood/cbugger.git
4. Unzip the file and rename the folder ‘CBugger’
5. Move the file to ‘/User/<NAME>/Library/Application Support/Sublime Text 3/Packages/’
6. Reload Sublime Text 3 

Currently only known to be compatible with Mac OSX due to some file hard-coding. If you change the path in the instructions to be the Linux location for Sublime Text 3 packages, and change the path in the code to be the Linux location for the SFTP file servers, it should work on Linux as well. Unfortunately, the Windows compatibility is unknown and unlikely.

To test or use the program:

1. Setup Sublime SFTP plugin if it’s never been done before: https://docs.google.com/document/d/15kyAx28zdL9LvnCjwPzKDiFIzcNlsFVolT0F9bux4qE/edit?usp=sharing
2. Open a file to edit using SFTP
3. Select ‘Launch Remote Debugger’ under the ‘Debugger’ menu along the top bar
	- If the ‘Debugger’ menu does not appear, reload Sublime Text and make sure the package was put in the right folder
    - On Mac, selecting CTRL-\` will display the Python console and show any error messages that might be occurring.
4. Set inputs like command line arguments or standard input files, set variables to display.
5. Set or remove breakpoints by right-clicking
6. Select ‘Run’ under ‘Debugger’ to run the debugger!

To develop or extend the work
1. Open the cbugger.py file
2. Open any files in the /src/ directory
3. Edit away!
4. Save the cbugger.py to reload changes to the plugin
