'''
Test Cuckoo filter
'''

try:
    import unittest2 as unittest
# pylint: disable=bare-except
except:
    import unittest

from netaddr import IPAddress
# pylint: disable=import-error
from cuckoo.filter import CuckooFilter


class BucketTest(unittest.TestCase):
    '''
    Test classic Cuckoo filter
    '''

    def test_filter(self):
        '''
        Adding and deleting items in a Cuckoo filter
        '''
        # Use a small capacity filter for testing
        capacity = 128
        # Use the fix fingerprint size of 8-bit for testing
        fingerprint_size = 8

        cuckoo = CuckooFilter(capacity, fingerprint_size)

        # By default, a bucket has the capacity of 4
        cases = [
            {
                'item': '192.168.1.190',
                'transformer': lambda string: string,
                'action': cuckoo.insert,
                'included': True,
            },

            {
                'item': '192.168.1.191',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.insert,
                'included': True,
            },

            {
                'item': '192.168.1.192',
                'transformer': lambda string: string,
                'action': cuckoo.insert,
                'included': True,
            },

            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.insert,
                'included': True,
            },

            {
                'item': '192.168.1.192',
                'transformer': lambda string: string,
                'action': cuckoo.delete,
                'included': False,
            },

            # Add the same item again
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.insert,
                'included': True,
            },

            # Remove a duplicated item
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.delete,
                'included': True,
            },

            # Remove the last copy of the duplicated item
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.delete,
                'included': False,
            },
        ]

        for case in cases:
            item = case['transformer'](case['item'])

            self.assertTrue(case['action'](item), 'Save {0} into the filter ok'.format(item))

            # Make sure that all items are in the bucket
            self.assertEqual(cuckoo.contains(item), case['included'], 'Item {0} is in the filter'.format(item))
            self.assertEqual(item in cuckoo, case['included'], 'Item {0} is in the bucket'.format(item))
