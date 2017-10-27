'''
Test Cuckoo filter
'''

try:
    import unittest2 as unittest
# pylint: disable=bare-except
except:
    import unittest

import os
import timeit

from netaddr import IPAddress
# pylint: disable=import-error
from cuckoo.filter import CuckooFilter, ScalableCuckooFilter


class BucketTest(unittest.TestCase):
    '''
    Test classic Cuckoo filter
    '''
    def setUp(self):
        '''
        Setup some variables for the test
        '''
        self.enable_load_test = os.environ.get('ENABLE_LOAD_TEST', False)


    def test_classic_filter(self):
        '''
        Adding and deleting items in a Cuckoo filter
        '''
        # Use a small capacity filter for testing
        capacity = 128
        # Use the fix error rate of 0.000001 for testing
        error_rate = 0.000001

        cuckoo = CuckooFilter(capacity, error_rate)

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


    # pylint: disable=no-self-use
    def test_load(self):
        '''
        Load a huge number of items and test the filter performance
        '''
        if not self.enable_load_test:
            return

        number = 10
        # Classic Cuckoo filter with 100_000_000
        allocation_time = timeit.timeit('CuckooFilter(capacity=100000000, error_rate=0.000001)',
                                        setup='from cuckoo.filter import CuckooFilter',
                                        number=number)
        print '# Pre-allocate 100_000_000 buckets in: {0}'.format(round(float(allocation_time) / number, 4))


    def test_dynamic_capacity_filter(self):
        '''
        Use a filter with dynamic bucket size
        '''
        # Use a small capacity filter for testing
        capacity = 2
        # Use the fix error rate of 0.000001 for testing
        error_rate = 0.000001

        cuckoo = ScalableCuckooFilter(capacity, error_rate, bucket_size=1)

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

            self.assertIsNotNone(case['action'](item), 'Save {0} into the filter ok'.format(item))

            # Make sure that all items are in the bucket
            self.assertEqual(cuckoo.contains(item), case['included'], 'Item {0} is in the filter'.format(item))
            self.assertEqual(item in cuckoo, case['included'], 'Item {0} is in the bucket'.format(item))
