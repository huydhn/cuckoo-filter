'''
Test serialize and de-serialize the filter using pickle
'''

import unittest
import pickle

from netaddr import IPAddress
from cuckoo.filter import CuckooFilter, BCuckooFilter, ScalableCuckooFilter


class SerializationTest(unittest.TestCase):
    '''
    Test various implementation of Cuckoo filters.
    '''
    def test_serialize_static_filters(self):
        '''
        Adding and deleting items from the static Cuckoo filters.
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
            },

            {
                'item': '192.168.1.191',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.insert,
            },

            {
                'item': '192.168.1.192',
                'transformer': lambda string: string,
                'action': cuckoo.insert,
            },

            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.insert,
            },

            {
                'item': '192.168.1.192',
                'transformer': lambda string: string,
                'action': cuckoo.delete,
            },

            # Add the same item again
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.insert,
            },

            # Remove a duplicated item
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.delete,
            },

            # Remove the last copy of the duplicated item
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.delete,
            },
        ]

        self.results = {
            '192.168.1.190': True,
            str(int(IPAddress('192.168.1.191'))): True,
            '192.168.1.192': False,
            str(int(IPAddress('192.168.1.193'))): False,
        }

        for case in cases:
            item = case['transformer'](case['item'])
            self.assertTrue(case['action'](item), 'Insert / delete {0} from the filter ok'.format(item))

        # Dump and load the filter using pickle
        filter_reload = pickle.loads(pickle.dumps(cuckoo))

        for item, exists in self.results.items():
            # Make sure that all items are in the bucket
            self.assertEqual(filter_reload.contains(item), exists, 'Item {0} is in the filter'.format(item))
            self.assertEqual(item in filter_reload, exists, 'Item {0} is in the bucket'.format(item))

        # Test the bitarray Cuckoo filter
        bcuckoo = BCuckooFilter(capacity, error_rate)

        for case in cases:
            # Use the method from bit array Cuckoo filter
            case['action'] = bcuckoo.insert if case['action'] == cuckoo.insert else bcuckoo.delete

            item = case['transformer'](case['item'])
            self.assertTrue(case['action'](item), 'Insert / delete {0} from the filter ok'.format(item))

        bfilter_reload = pickle.loads(pickle.dumps(bcuckoo))

        for item, exists in self.results.items():
            # Make sure that all items are in the bucket
            self.assertEqual(bfilter_reload.contains(item), exists, 'Item {0} is in the filter'.format(item))
            self.assertEqual(item in bfilter_reload, exists, 'Item {0} is in the bucket'.format(item))


    def test_serialize_dynamic_filter(self):
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
            },

            {
                'item': '192.168.1.191',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.insert,
            },

            {
                'item': '192.168.1.192',
                'transformer': lambda string: string,
                'action': cuckoo.insert,
            },

            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.insert,
            },

            {
                'item': '192.168.1.192',
                'transformer': lambda string: string,
                'action': cuckoo.delete,
            },

            # Add the same item again
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.insert,
            },

            # Remove a duplicated item
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.delete,
            },

            # Remove the last copy of the duplicated item
            {
                'item': '192.168.1.193',
                'transformer': lambda string: str(int(IPAddress(string))),
                'action': cuckoo.delete,
            },
        ]

        self.results = {
            '192.168.1.190': True,
            str(int(IPAddress('192.168.1.191'))): True,
            '192.168.1.192': False,
            str(int(IPAddress('192.168.1.193'))): False,
        }

        for case in cases:
            item = case['transformer'](case['item'])
            self.assertIsNotNone(case['action'](item), 'Save {0} into the filter ok'.format(item))

        filter_reload = pickle.loads(pickle.dumps(cuckoo))

        for item, exists in self.results.items():
            # Make sure that all items are in the bucket
            self.assertEqual(filter_reload.contains(item), exists, 'Item {0} is in the filter'.format(item))
            self.assertEqual(item in filter_reload, exists, 'Item {0} is in the bucket'.format(item))
