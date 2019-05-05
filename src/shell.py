import paramiko
import re

from Cbugger.src.pygdbmi import gdbmiparser

class GDBHandler:
    def __init__(self, host, user, psw):

        self.shell = ShellHandler(host, user, psw)
        # error catching if shell fails to connect

        self.current_directory = "~"

        self.executable = None
        self.files = []

        self.command_line_args = ""
        self.stdin_file = None
        # self.here_doc = ""

        self.variables = []
        self.recent_vars = []

    def __del__(self):
        self.shell.close()

    def set_input_file(self, file):
        self.stdin_file = file.strip("\n")
        set_args_in_gdb(self)

    def set_cmd_line_args(self, string):
        self.command_line_args = string.strip("\n")
        set_args_in_gdb(self)

    def add_variables(self, var_list):
        self.variables += var_list

    def remove_variables(self, var_list):
        for var in var_list:
            if var in self.variables:
                self.variables.remove(var)

    # maybe fix this weird inheritance thing eesh
    def execute(self, cmd):
        return self.shell.execute(cmd)

    def execute_in_gdb(self, cmd):
        return self.shell.execute_in_gdb(cmd)

    def execute_in_running(self, cmd):
        return self.shell.execute_in_running(cmd)

    def execute_separate(self, cmd):
        full_cmd = "cd " + self.current_directory + "; " + cmd
        ssh = self.shell.ssh
        stdin, stdout, stderr = ssh.exec_command(full_cmd)
        exit_status = stdout.channel.recv_exit_status()
        
        return stdin, stdout, stderr, exit_status


def set_args_in_gdb(shell):

    set_args_cmd = "-exec-arguments " + shell.command_line_args
    if shell.stdin_file is not None:
        set_args_cmd += (" < " + shell.stdin_file)

    _,stdout,_ = shell.execute_in_gdb(set_args_cmd)


class ShellHandler:

    def __init__(self, host, user, psw):

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=user, password=psw, port=22, timeout=60)

        channel = self.ssh.invoke_shell()
        self.stdin = channel.makefile('wb')
        self.stdout = channel.makefile('r')

    def __del__(self):
        self.ssh.close()

    def close(self):
        self.ssh.close() 

    def execute(self, cmd):
        """

        :param cmd: the command to be executed on the remote computer
        :examples:  execute('ls')
                    execute('finger')
                    execute('cd folder_name')
        """
        cmd = cmd.strip('\n')
        self.stdin.write(cmd + '\n')
        finish = 'end of stdOUT buffer. finished with exit status'
        echo_cmd = 'echo {} $?'.format(finish)
        self.stdin.write(echo_cmd + '\n')
        shin = self.stdin
        self.stdin.flush()

        shout = []
        sherr = []
        exit_status = 0
        for line in self.stdout:
            if str(line).startswith(cmd) or str(line).startswith(echo_cmd):
                # up for now filled with shell junk from stdin
                shout = []
            elif str(line).startswith(finish):
                # our finish command ends with the exit status
                exit_status = int(str(line).rsplit(maxsplit=1)[1])
                if exit_status:
                    # stderr is combined with stdout.
                    # thus, swap sherr with shout in a case of failure.
                    sherr = shout
                    shout = []
                break
            else:
                # get rid of 'coloring and formatting' special characters
                shout.append(re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line).
                             replace('\b', '').replace('\r', ''))

        # first and last lines of shout/sherr contain a prompt
        if shout and echo_cmd in shout[-1]:
            shout.pop()
        if shout and cmd in shout[0]:
            shout.pop(0)
        if sherr and echo_cmd in sherr[-1]:
            sherr.pop()
        if sherr and cmd in sherr[0]:
            sherr.pop(0)

        return shin, shout, sherr, exit_status


    def execute_in_gdb(self, cmd):

        cmd = cmd.strip('\n')
        self.stdin.write(cmd + '\n')
        shin = self.stdin
        self.stdin.flush()

        shout = []
        sherr = []
    
        for line in self.stdout:
            if str(line).startswith(cmd):# str(line).startswith(cmd):
                # up for now filled with shell junk from stdin
                shout = []
            elif str(line).startswith('(gdb)'):
                break
            else:
                # get rid of 'coloring and formatting' special characters
                line = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line).replace('\b', '').replace('\r', '')
                shout.append(gdbmiparser.parse_response(line))

        # last lines of shout/sherr contain a prompt
        if shout and cmd in shout[0]:
            shout.pop(0)
        if sherr and cmd in sherr[0]:
            sherr.pop(0)

        return shin, shout, sherr

    # okay seriously modularize this somehow or so help me 
    # FIX THISSS
    def execute_in_running(self, cmd):

        cmd = cmd.strip('\n')
        self.stdin.write(cmd + '\n')
        shin = self.stdin
        self.stdin.flush()

        shout = []
        sherr = []

        stopped_seen = False
        for line in self.stdout:
            if str(line).startswith(cmd):
                # up for now filled with shell junk from stdin
                shout = []
            elif str(line).startswith('(gdb') and stopped_seen:
                break
            else:
                # get rid of 'coloring and formatting' special characters
                line = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line).replace('\b', '').replace('\r', '')
                shout.append(gdbmiparser.parse_response(line))

                if shout[-1]['message'] == 'stopped':
                    stopped_seen = True

        # last lines of shout/sherr contain a prompt
        if shout and cmd in shout[0]:
            shout.pop(0)
        if sherr and cmd in sherr[0]:
            sherr.pop(0)

        return shin, shout, sherr
