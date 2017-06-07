import logging
from netifaces import interfaces, ifaddresses


def get_best_if_address():
    address_to_use = None
    for ifaceName in interfaces():
        logging.debug("checking %s for zc" % ifaceName)
        logging.debug("ifaddresses for %s : %s" % (ifaceName, ifaddresses(ifaceName)))
        for (address_id, address_array) in ifaddresses(ifaceName).iteritems():
            for address_obj in address_array:
                str_address = str(address_obj['addr'])
                if (not str_address.startswith("127")) and ("." in str_address):
                    address_to_use = str_address
                else:
                    logging.debug("ignoring %s for zc" % str_address)
    return address_to_use