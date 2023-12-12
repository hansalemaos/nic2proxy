import re
import shutil
import tempfile
from touchtouch import touch
import ctypes
import os
import subprocess
import sys
from ctypes import wintypes
from functools import cache
from time import strftime
import socketserver
from getpublicipv4 import get_ip_of_this_pc

get_timest = lambda: strftime("%Y_%m_%d_%H_%M_%S")

startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE
creationflags = subprocess.CREATE_NO_WINDOW
invisibledict = {
    "startupinfo": startupinfo,
    "creationflags": creationflags,
    "start_new_session": True,
}

windll = ctypes.LibraryLoader(ctypes.WinDLL)
user32 = windll.user32
kernel32 = windll.kernel32
GetExitCodeProcess = windll.kernel32.GetExitCodeProcess
CloseHandle = windll.kernel32.CloseHandle
GetExitCodeProcess.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.POINTER(ctypes.c_ulong),
]
CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
GetExitCodeProcess.restype = ctypes.c_int
CloseHandle.restype = ctypes.c_int

GetWindowRect = user32.GetWindowRect
GetClientRect = user32.GetClientRect
_GetShortPathNameW = kernel32.GetShortPathNameW
_GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
_GetShortPathNameW.restype = wintypes.DWORD


@cache
def get_short_path_name(long_name):
    try:
        output_buf_size = 4096
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        _ = _GetShortPathNameW(long_name, output_buf, output_buf_size)
        return output_buf.value
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        return long_name


psexe = shutil.which("powershell.exe")
DIR = os.sep.join((__file__.split(os.sep)[:-1]))
FilePath = get_short_path_name(DIR + os.sep + "s5light-windows-amd64-v3.exe")
configfile = (DIR + os.sep + "config.yaml")
touch(configfile)
configfile =get_short_path_name(configfile)
try:
    mywanip = get_ip_of_this_pc()
    while not re.match(r'^\d+\.\d+\.\d+\.\d+', mywanip):
        mywanip = get_ip_of_this_pc()
except Exception as fe:
    sys.stderr.write(f"{fe:}\n")
    sys.stderr.flush()

def send_ctrl_commands(pid, command=0):
    # CTRL_C_EVENT = 0
    # CTRL_BREAK_EVENT = 1
    # CTRL_CLOSE_EVENT = 2
    # CTRL_LOGOFF_EVENT = 3
    # CTRL_SHUTDOWN_EVENT = 4
    commandstring = r"""import ctypes, sys; CTRL_C_EVENT, CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT = 0, 1, 2, 3, 4; kernel32 = ctypes.WinDLL("kernel32", use_last_error=True); (lambda pid, cmdtosend=CTRL_C_EVENT: [kernel32.FreeConsole(), kernel32.AttachConsole(pid), kernel32.SetConsoleCtrlHandler(None, 1), kernel32.GenerateConsoleCtrlEvent(cmdtosend, 0), sys.exit(0) if isinstance(pid, int) else None])(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else None) if __name__ == '__main__' else None"""
    subprocess.Popen(
        [sys.executable, "-c", commandstring, str(pid), str(command)],
        **invisibledict,
    )  # Send Ctrl-C


def get_tmpfile(suffix=".bat"):
    tfp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    filename = tfp.name
    filename = os.path.normpath(filename)
    tfp.close()
    touch(filename)
    return filename


def get_free_port():
    with socketserver.TCPServer(("localhost", 0), None) as s:
        port = s.server_address[1]
    return port


class MultiProxyServer:
    r"""
    MultiProxyServer class for managing and starting multiple proxy servers on Windows.

    This class provides functionality to configure, start, and manage proxy servers.
    It binds each proxy to a specific network interface.
    It also includes methods for generating YAML configuration files,
    retrieving the public IPv4 address of the host, and handling console events for controlling
    server processes. It uses https://github.com/hang666/s5light under the hood

    Usage:
    1. Create an instance of MultiProxyServer with the desired interfaces and log folder.
    2. Write the YAML configuration file with the write_yaml_config() method.
    3. Start the proxy servers with the start_proxy() method.
    4. Get information about the running servers with the __str__() method.

    Example:
        from nic2proxy import MultiProxyServer
        interfaces = {
            0: {
                "bind_address": "0.0.0.0",
                "bind_port": None,
                "out_address": "192.168.9.100", # Address of the NIC you want to use
                "tcp_timeout": 60,
                "udp_timeout": 60,
                "whitelist": (),
            },
            1: {
                "bind_address": "0.0.0.0",
                "bind_port": None,
                "out_address": "192.168.10.100", # Address of the NIC you want to use
                "tcp_timeout": 60,
                "udp_timeout": 60,
                "whitelist": (),
            },
        }

        prox = MultiProxyServer(interfaces=interfaces, logfolder="c:\\proxylogs")
        prox.write_yaml_config().start_proxy()
        print(prox)
        #  prox.kill_proxy() to kill 'em all!
    """
    def __init__(self, interfaces, logfolder):
        r"""
        Initialize the MultiProxyServer instance.

        Parameters:
        - interfaces (dict): A dictionary containing configuration details for each proxy interface.
        - logfolder (str): The folder path where log files will be stored.
        """
        self.interfaces = interfaces
        self.logfolder = os.path.normpath(logfolder)
        self.timestamp = get_timest()
        self.tmpfilestdout = os.path.normpath(
            os.path.join(self.logfolder, f"{self.timestamp}_stdout.txt")
        )
        self.tmpfilestderr = os.path.normpath(
            os.path.join(self.logfolder, f"{self.timestamp}_stderr.txt")
        )
        touch(self.tmpfilestdout)
        touch(self.tmpfilestderr)
        self.tmpfilestdout = get_short_path_name(self.tmpfilestdout)
        self.tmpfilestderr = get_short_path_name(self.tmpfilestderr)
        self.procpids = []
        self.running_servers = []
        self.proxy_ps_shell=None

    def __str__(self):
        r"""
        Return a string representation of the running proxy servers.

        Returns:
        str: A string containing information about the running proxy servers.

        """
        s = []
        for server, port in self.running_servers:
            s.append(f"{mywanip}:{port}")
        return "\n".join(s)

    def __repr__(self):
        return self.__str__()

    def write_yaml_config(self):
        r"""
        Write the YAML configuration file based on the provided interfaces.

        Returns:
        MultiProxyServer: The current MultiProxyServer instance.

        """
        yamlfile = ["accounts:"]
        for k, v in self.interfaces.items():
            for kk, vv in v.items():
                if kk == "bind_port":
                    continue
                elif kk == "bind_address":
                    portforconnection = v["bind_port"] or get_free_port()
                    yamlfile.append(f'''  - {kk}: "{vv}:{portforconnection}"''')
                    self.running_servers.append((vv, portforconnection))
                elif kk in ["udp_bind_ip", "out_address"]:
                    yamlfile.append(f'''    {kk}: "{vv}"''')
                elif kk in ["tcp_timeout", "udp_timeout"]:
                    yamlfile.append(f"""    {kk}: {vv}""")
                elif kk == "whitelist":
                    vvlist = list(vv)
                    vvlist.extend(["127.0.0.1", mywanip, v["out_address"]])
                    vvlist = [f'      - "{x}"' for x in (set(vvlist))]
                    yamlfile.append(f"""    {kk}:""")
                    yamlfile.append("\n".join(vvlist))
        wholefile = "\n".join(yamlfile)
        with open(configfile, mode="w", encoding="utf-8") as f:
            f.write(wholefile)
        print(f"Config written to: {configfile}")
        return self

    def start_proxy(self):
        r"""
        Start the proxy servers using PowerShell commands.

        Returns:
        MultiProxyServer: The current MultiProxyServer instance.

        """
        # might need elevated rights
        WhatIf = ""
        Verb = ""
        UseNewEnvironment = ""
        Wait = ""
        stdinadd = ""
        WindowStyle = "Hidden"
        wholecommandline = f"""{psexe} -ExecutionPolicy RemoteSigned Start-Process -FilePath {FilePath}{WhatIf}{Verb}{UseNewEnvironment}{Wait}{stdinadd} -RedirectStandardOutput {self.tmpfilestdout} -RedirectStandardError {self.tmpfilestderr} -WorkingDirectory {DIR} -WindowStyle {WindowStyle}"""
        self.proxy_ps_shell = subprocess.Popen(
            wholecommandline,
            cwd=DIR,
            env=os.environ.copy(),
            shell=True,
            **invisibledict,
        )
        self._get_proxy_pid()
        return self

    def _get_proxy_pid(self):
        r"""
        Retrieve the process IDs (PIDs) of the running proxy servers.

        """
        allprocs = set()
        while not allprocs:
            try:
                pp = subprocess.Popen(
                    ["wmic", "process", "list", "FULL"],
                    stdout=subprocess.PIPE,
                )

                alllists = [[]]
                for ini, line in enumerate(iter(pp.stdout.readline, b"")):
                    try:
                        line2 = line.decode("utf-8")
                        if line2 == "\r\r\n":
                            alllists.append([])
                        alllists[-1].append(line2)
                    except KeyboardInterrupt:
                        break

                for q in alllists:
                    for qq in q:
                        if "powershell.exe" in qq:
                            continue
                        if FilePath in qq:
                            for qqq in q:
                                if "Handle=" in qqq:
                                    va = qqq.strip().split("=")[-1]
                                    allprocs.add(
                                        (
                                            qq.split("=")[-1]
                                            .strip("\"'")
                                            .strip()
                                            .strip("\"'")
                                            .strip(),
                                            va,
                                        )
                                    )
            except Exception as fe:
                sys.stderr.write(f'{fe}\n')
                sys.stderr.flush()
        for q in allprocs:
            self.procpids.append(q[-1])

    def kill_proxy(self):
        r"""
        Terminate the running proxy servers by sending Ctrl+C commands.

        """
        for pr in self.procpids:
            send_ctrl_commands(int(pr))

