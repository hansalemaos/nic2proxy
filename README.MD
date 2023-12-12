# Creates Proxies and binds them to a NIC - Windows only

## pip install nic2proxy

### Tested against Windows / Python 3.11 / Anaconda


```python
MultiProxyServer class for managing and starting multiple proxy servers on Windows.

This class provides functionality to configure, start, and manage proxy servers.
It binds each proxy to a specific network interface.
It also includes methods for generating YAML configuration files,
retrieving the public IPv4 address of the host, and handling console events for controlling
server processes. It uses https://github.com/hang666/s5light under the hood

Usage:
1. Create an instance of MultiProxyServer with the desired interfaces and log folder.
2. Write the YAML configuration file with the write_yaml_config() method.
3. Start the proxy servers with the start_proxy() method. (Uses powershell - might need elevated rights)
4. Get information about the running servers with the __str__() method.

Example:
from nic2proxy import MultiProxyServer
interfaces = {
	0: {
		"bind_address": "0.0.0.0",
		"bind_port": None, # None -> finds a free one 
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
```