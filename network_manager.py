import netifaces
from wifi_manager import WifiManager

ADDR_FIELD_NAME = 'addr'
LOOPBACK_IP = '127.0.0.1'


class NetworkManager:
    '''Manages network of the device.'''
    _instance = None

    # Private Section
    def __init__(self, primary_wifi_ssid, primary_wifi_key,
                 backup_ssid_to_keys):
        if NetworkManager._instance is not None:
            raise Exception("This class is a singleton. Please use"
                            "get_instance() to get a class object.")
        self.wifi_manager = WifiManager.get_instance(primary_wifi_ssid,
                                                     primary_wifi_key,
                                                     backup_ssid_to_keys)
        NetworkManager._instance = self

    def _extract_ip_addresses(self, interface_name):
        '''Extracts a list of IP addresses from the interface.'''
        if netifaces.AF_INET not in netifaces.ifaddresses(interface_name):
            return []
        ip_addresses = []
        for internet_addresses in netifaces.ifaddresses(interface_name)[
                netifaces.AF_INET]:
            if ADDR_FIELD_NAME not in internet_addresses:
                continue
            ip_addresses.append(internet_addresses[ADDR_FIELD_NAME])
        return ip_addresses

    def _is_local_interface(self, interface_name):
        '''Returns true if the interface is a loop interface.
        
        This depends on if it has IP 127.0.0.1.'''
        return any(ip_address == LOOPBACK_IP
                   for ip_address in self._extract_ip_addresses(interface_name))

    def _get_ethernet_interface_names(self):
        '''Returns a set of the ethernet interface names.'''
        # Pi has three types of interfaces:
        # 1. local => IP is 127.0.0.1
        # 2. wifi => We can read from WifiManager
        # 3. ethernet => the rest one
        # TODO: handle the virtual interfaces installed by virtualization
        # softwares, e.g. docker, virtualbox, if needed in future. There
        # is no such need now and in the forseeable future.
        interface_names = set(netifaces.interfaces())
        interface_names_not_wifi = interface_names - set(
            self.wifi_manager.get_wifi_interface_names())
        return set(interface_name for interface_name in interface_names_not_wifi
                   if not self._is_local_interface(interface_name))

    # Public Section
    @staticmethod
    def get_instance(primary_wifi_ssid, primary_wifi_key,
                     backup_ssid_to_keys):
        '''Returns the singleton instance.'''
        if NetworkManager._instance is None:
            NetworkManager(primary_wifi_ssid, primary_wifi_key,
                           backup_ssid_to_keys)
        return NetworkManager._instance

    def get_ethernet_ip(self):
        '''Returns the first-found IP of the ethernet interfaces.'''
        for ethernet_interface_name in self._get_ethernet_interface_names():
            ip_addresses = self._extract_ip_addresses(ethernet_interface_name)
            if len(ip_addresses) > 0:
                return ip_addresses[0]
        return None

    def get_wifi_ip(self):
        '''Similar to above. Returns the first-found IP of Wi-Fi interfaces.'''
        connected_interface_name = self.wifi_manager.get_connected_interface_name()
        if connected_interface_name is None:
            return None
        ip_addresses = self._extract_ip_addresses(connected_interface_name)
        return ip_addresses[0] if len(ip_addresses) > 0 else None
