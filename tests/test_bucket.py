'''
Test Cuckoo bucket.
'''

try:
    import unittest2 as unittest
# pylint: disable=bare-except
except:
    import unittest

import mmh3

from netaddr import IPAddress
# pylint: disable=import-error
from cuckoo.bucket import Bucket


class BucketTest(unittest.TestCase):
    '''
    Test Cuckoo bucket.
    '''

    def test_bucket(self):
        '''
        Adding and deleting items in a bucket.
        '''
        bucket = Bucket()

        # By default, a bucket has the capacity of 4
        cases = [
            {
                'item': '192.168.1.190',
                'transformer': lambda string: string,

                'action': bucket.insert,
                'expected': True,

                'full': False,
                'included': True,
            },

            {
                'item': '192.168.1.191',
                'transformer': lambda string: str(int(IPAddress(string))),

                'action': bucket.insert,
                'expected': True,

                'full': False,
                'included': True,
            },

            {
                'item': '192.168.1.192',
                'transformer': lambda string: string,

                'action': bucket.insert,
                'expected': True,

                'full': False,
                'included': True,
            },

            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),

                'action': bucket.insert,
                'expected': True,

                'full': True,
                'included': True,
            },

            {
                'item': '192.168.1.194',
                'transformer': lambda string: string,

                'action': bucket.insert,
                'expected': False,

                'full': True,
                'included': False,
            },

            {
                'item': '192.168.1.195',
                'transformer': lambda string: str(int(IPAddress(string))),

                'action': bucket.insert,
                'expected': False,

                'full': True,
                'included': False,
            },

            {
                'item': '192.168.1.195',
                'transformer': lambda string: str(int(IPAddress(string))),

                'action': bucket.delete,
                'expected': False,

                'full': True,
                'included': False,
            },

            {
                'item': '192.168.1.192',
                'transformer': lambda string: string,

                'action': bucket.delete,
                'expected': True,

                'full': False,
                'included': False,
            },

            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),

                'action': bucket.delete,
                'expected': True,

                'full': False,
                'included': False,
            },

            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),

                'action': bucket.insert,
                'expected': True,

                'full': False,
                'included': True,
            },

            # Add the same item again
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),

                'action': bucket.insert,
                'expected': True,

                'full': True,
                'included': True,
            },

            # Remove a duplicated item
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),

                'action': bucket.delete,
                'expected': True,

                'full': False,
                'included': True,
            },

            # Remove the last copy of the duplicated item
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),

                'action': bucket.delete,
                'expected': True,

                'full': False,
                'included': False,
            },
        ]

        for case in cases:
            item = case['transformer'](case['item'])

            # Generate all the fingerprints
            fingerprint = mmh3.hash_bytes(item)

            self.assertEqual(case['action'](fingerprint), case['expected'], 'Save {0} into the bucket ok'.format(item))
            self.assertEqual(bucket.is_full(), case['full'], 'Bucket capacity is ok')

            # Make sure that all items are in the bucket
            self.assertEqual(bucket.contains(fingerprint), case['included'], 'Item {0} is in the bucket'.format(item))
            self.assertEqual(fingerprint in bucket, case['included'], 'Item {0} is in the bucket'.format(item))
