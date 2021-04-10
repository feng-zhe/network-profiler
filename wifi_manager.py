import pywifi

from pywifi import const

P2P_DEV_PREFIX = 'p2p-dev-'
VERIFICATION_OBSERVATION_COUNT = 3
VERIFICATION_DURATION_SECS = 10


class WifiManager:
    '''Manages Wi-Fi connection.
    
    The Wi-Fi should only be managed by one instance of this class.

    If it finds out unexpected situation happens, it may trigger a Wi-Fi
    reconnect, i.e. disconnect first and then connect again.
    '''
    _instance = None    # singleton

    # Private Section
    def __init__(self, primary_ssid, primary_key, backup_ssid_to_keys):
        '''Initializes the internal variables. Virtually private.
        
        Args:
            primary_ssid:   The primary Wi-Fi ssid.
            primary_key:    The primary Wi-Fi key.
            backup_ssid_to_keys:  A dictionary from backup AP's ssid to its key.
        '''
        if WifiManager._instance is not None:
            raise Exception("This class is a singleton. Please use"
                            "get_instance() to get a class object.")
        self.primary_ssid = primary_ssid
        self.primary_key = primary_key
        self.backup_ssid_to_keys = backup_ssid_to_keys
        self.wifi = pywifi.PyWiFi()
        WifiManager._instance = self

    def _get_interfaces(self):
        '''Gets Wi-Fi interfaces.
        
        The p2p-dev-* interfaces will be filtered out since they don't
        really exist. (They may be created by wpa_supplicant p2p module)'''
        return [
            iface for iface in self.wifi.interfaces()
            if not iface.name().startswith(P2P_DEV_PREFIX)
        ]

    def _get_connected_interface(self):
        '''Gets the interface which has wifi connected.
        
        Returns None if not find.'''
        for iface in self._get_interfaces():
            if iface.status() == const.IFACE_CONNECTED:
                return iface
        return None

    def _get_profiles_with_key(self, profiles):
        '''Returns a list of Wi-Fi proflies with known keys.
        
        The primary profile will be the first one if exists.'''
        primary_profile = None
        known_wifi_profiles = []
        for profile in all_wifi_profiles:
            if profile.ssid == self.primary_ssid:
                profile.key = self.primary_key
                primary_profile = profile
                continue
            if profile.ssid in backup_ssid_to_keys.keys():
                profile.key = self.backup_ssid_to_keys[profile.ssid]
                known_wifi_profiles.append(profile)
                continue
        if primary_profile:
            return [primary_profile] + known_wifi_profiles
        return known_wifi_profiles

    def _verify_connected(self, iface):
        '''Verifies if then interface can be believed to be connected to Wi-Fi.

        In experiment, it turns out it is possible that the interface is in connected
        status for once but soon become non-connected status because of the wrong key.
        Thus the verification criteria is to have consecutive VERIFICATION_OBSERVATION_COUNT
        number of connected status during the verification.'''
        observed_connected_count = 0
        for _ in range(VERIFICATION_DURATION_SECS):
            if iface.status() == const.IFACE_CONNECTED:
                observed_connected_count = observed_connected_count + 1
            else:
                observed_connected_count = 0
            if observed_connected_count >= VERIFICATION_OBSERVATION_COUNT:
                return True
            time.sleep(1)
        return False

    # Public Section
    @staticmethod
    def get_instance(primary_ssid, primary_key, backup_ssid_to_keys):
        '''Returns the singleton instance.'''
        if WifiManager._instance is None:
            WifiManager(primary_ssid, primary_key, backup_ssid_to_keys)
        return WifiManager._instance

    def reconnect(self, iface):
        '''Tries to connect wifi via interface iface. Primary AP will be tried first.
        
        Note this will first disconnect and then try to connect Wi-Fi.

        Args:
            iface:  the Wi-Fi interface.
            
        Returns:
            True if reconnection is successful.'''
        iface.scan()
        time.sleep(10)    # wait for the scan result.
        # only keep the ones whose key is known by us.
        known_wifi_profiles = self._get_profiles_with_key(iface.scan_results())
        iface.remove_all_network_profiles()
        for profile in known_wifi_profiles:
            iface.add_network_profile(profile)
            iface.connect(profile)
            if self._verify_connected(iface):
                return True
            # Somehow we cannot do `self.remove_network_profile(profile)`
            # because it will fail to remove it.
            iface.remove_network_profile(iface.network_profiles()[0])
        return False

    def reconnect(self):
        '''Similar to the above one but this function tries all Wi-Fi interfaces.'''
        for iface in self._get_interfaces():
            if self.reconnect(iface):
                return True
        return False

    def is_connected(self):
        '''Returns True if any interface has wifi connected.'''
        return self._get_connected_interface() != None

    def get_connected_interface_name(self):
        '''Gets the connected interface name.'''
        iface = self._get_connected_interface()
        return iface.name() if iface else None

    def get_wifi_interface_names(self):
        '''Gets all physical Wi-Fi interface names.'''
        return [iface.name() for iface in self._get_interfaces()]

    def is_connected_to_primary(self):
        '''Returns true if we are connecting to the primary access point.'''
        iface = self._get_connected_interface()
        if iface == None:
            return False
        if len(iface.network_profiles()) != 1:
            # There should be only one profile which is used for connection.
            # If this is not true, it would either be:
            # 1. the wifi is not only managed by us
            # 2. other objects of this class crashed in the middle of some operation.
            # In either case, we need to remove all AP and connect Wi-Fi again.
            if not self.reconnect(iface):
                return False
        # Now iface is connected and it has only one profile (the connected one).
        return iface.network_profiles()[0].name() == self.primary_ssid
