import shlex
import subprocess
import sys
import shutil
import os
from subprocess import run , PIPE , STDOUT
import readline

PATH_SEP = os.pathsep
PATH = os.environ.get('PATH', '')


last_prefix = None
tab_press_count = 0


builtin_command = {}
BUILTINS = {"exit": "builtin", "echo": "builtin", "type": "builtin" , "pwd":"builtin" , "cd":"builtin"}


def parse_path(path):
    """ Parses system PATH and stores available executables """
    global BUILTINS
    BUILTINS.update({"exit": "builtin", "echo": "builtin", "type": "builtin", "pwd": "builtin", "cd": "builtin"})


    path_dirs = path.split(PATH_SEP)
    path_dirs = [dir for dir in path_dirs if os.path.exists(dir) and os.path.isdir(dir)]  # Ensure only directories

    for directory in path_dirs:
        try:
            for file in os.listdir(directory):
                full_path = os.path.join(directory, file)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    BUILTINS[file] = full_path
        except PermissionError:
            continue  


def command(func):
    """ Decorator to register built-in shell commands """
    builtin_command[func.__name__.split("_")[1]] = func
    return func


@command
def shell_exit(args):
    """ Handles the exit command """
    exit(int(args[0]) if args else 0)
@command
def shell_pwd(args):
    sys.stdout.write(os.getcwd() + "\n")
    sys.stdout.flush()
@command
def shell_cd(args):
    if not args or args[0] == "~":
        path = os.path.expanduser("~")
    else:
        path = os.path.abspath(os.path.expanduser(args[0]))
    try:
        os.chdir(path)
    except FileNotFoundError:
        sys.stdout.write(f"cd: no such file or directory: {path}\n")
    except NotADirectoryError:
        sys.stdout.write(f"not a directory: {path}\n")
        
    sys.stdout.flush()
    

@command
def shell_echo(args):
    """ Implements the echo command """
    sys.stdout.write(" ".join(args) + "\n")
    sys.stdout.flush()


@command
def shell_type(args):
    """ Implements the type command to check command type """
    if not args:
        sys.stdout.write("type: missing operand\n")
    elif args[0] in builtin_command:
        sys.stdout.write(f"{args[0]} is a shell builtin\n")
    elif args[0] in BUILTINS:
        sys.stdout.write(f"{args[0]} is {BUILTINS[args[0]]}\n")
    else:
        sys.stdout.write(f"{args[0]}: not found\n")
    sys.stdout.flush()

def complete(text , state):
    global last_prefix , tab_press_count

    matches = sorted([cmd for cmd in BUILTINS.keys() if cmd.startswith(text)])
    
    if state < len(matches):
        return matches[state] + " "

    if not matches:
        return None
    
    if text != last_prefix:
        tab_press_count = 0
        last_prefix = text

    tab_press_count += 1

    if len(matches) > 1:
        if tab_press_count == 1:
            sys.stdout.write("\a")
            sys.stdout.flush()
            return None
        elif tab_press_count == 2:
            sys.stdout.write("\n" + "  ".join(matches) + "\n")
            sys.stdout.write("$ " + text)
            sys.stdout.flush()
            return None


def main():
    """ Main shell loop """
    parse_path(PATH)


    readline.set_completer(complete)
    readline.parse_and_bind("tab: complete")

    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        try:
            user_input = input().strip()
        except EOFError:
            sys.stdout.write("\n")
            break

        if not user_input:
            continue

        try:
            parts = shlex.split(user_input)
        except ValueError:
            sys.stdout.write("Error: Unmatched quotes \n")
            sys.stdout.flush()

        if not parts:
            continue
        
        redirected_mode = None
        target_stream = None
        operator = None


        if ">" in parts or ">>" in parts or "1>" in parts or "1>>" in parts or "2>" in parts or "2>>" in parts:
            if ">>" in parts:
                index = parts.index(">>")
                target_stream = "stdout"
                redirected_mode = "a"

            elif "1>>" in parts:
                index = parts.index("1>>")
                target_stream = "stdout"
                redirected_mode = "a"

            elif "2>>" in parts:
                index = parts.index("2>>")
                target_stream = "stderr"
                redirected_mode = "a"

            elif ">" in parts:
                index = parts.index(">")
                target_stream = "stdout"
                redirected_mode = "w"

            elif "1>" in parts:
                index = parts.index("1>")
                target_stream = "stdout"
                redirected_mode = "w"

            elif "2>" in parts:
                index = parts.index("2>")
                target_stream = "stderr"
                redirected_mode = "w"
             

            if index + 1 >= len(parts):
                sys.stdout.write("Error: No output file specified ")
                sys.stdout.flush()
                continue

            cmd = parts[:index]
            output_file = parts[index + 1]

            os.makedirs(os.path.dirname(output_file) , exist_ok=True)
            open(output_file, "a").close()

            with open(output_file , redirected_mode) as f:
                try:
                    if cmd[0] in builtin_command:
                        orginal_stdout = sys.stdout
                        orginal_stderr = sys.stderr


                        if target_stream == "stdout":
                            sys.stdout = f
                        elif target_stream == "stderr":
                            sys.stderr = f
                        builtin_command[cmd[0]](cmd[1:])

                        sys.stdout = orginal_stdout
                        sys.stderr = orginal_stderr

                    elif cmd[0] in BUILTINS:
                        subprocess.run(cmd, stdout=f if target_stream == "stdout" else None, stderr=f if target_stream == "stderr" else None)
                    else:
                        sys.stdout.write(f"{cmd[0]}: command not found \n ")
                finally:
                    sys.stdout = sys.__stdout__
                    sys.stderr = sys.__stderr__
                    sys.stdout.flush()
                    sys.stderr.flush()

            continue
                

        cmd = parts[0]
        args = parts[1:]
        

        if cmd in builtin_command:
            builtin_command[cmd](args)
        elif cmd in BUILTINS:
            subprocess.run([cmd] + args)
        else:
            sys.stdout.write(f"{cmd}: command not found\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

