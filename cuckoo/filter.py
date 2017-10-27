'''
A Cuckoo filter is a data structure for probabilistic set-membership queries
with a low false positive probability (FPP).  As an improvement over the classic
Bloom filter, items can be added or removed into Cuckoo filters at will.  Cuckoo
filter also utilizes space more efficiently.

Cuckoo filters were originally described in:
    Fan, B., Andersen, D. G., Kaminsky, M., & Mitzenmacher, M. D. (2014, December).
    Cuckoo filter: Practically better than bloom.
    In Proceedings of the 10th ACM International on Conference on emerging Networking
    Experiments and Technologies (pp. 75-88). ACM.
'''

import codecs
import random
import math
import mmh3

from cuckoo.bucket import Bucket
from cuckoo.exception import CapacityException


class CuckooFilter(object):
    '''
    Implement the text book Cuckoo filter.
    '''
    DEFAULT_ERROR_RATE = 0.0001

    def __init__(self, capacity, error_rate, bucket_size=4, max_kicks=500):
        '''
        Initialize Cuckoo filter parameters.

        capacity: The size of the filter, it defines how many buckets the filter contains.

        error_rate: The desired error rate, the lower the error rate and the bigger the
            bucket size, the longer the fingerprint needs to be.

        bucket_size : The maximum number of fingerprints a bucket can hold.  Default size
            is 4, which closely approaches the best size for FPP between 0.00001 and 0.002
            (see Fan et al.).  Also according to the author, if your targeted FPP is greater
            than 0.002, a bucket size of 2 is more space efficient.

        max_kicks : The number of times entries are kicked / moved around before the filter
            is considered full.  Defaults to 500 used by Fan et al. in the above paper.
        '''
        # TODO:
        # - Naive approached #1: use multiple Cuckoo filters with different capacities
        self.capacity = capacity

        # NOTE:
        # - If the bucket size increases, a longer fingerprint will be needed to retain the
        #   same FPP rate
        # - The minimum fingerprint size is f >= ceil(log2(1/e) + log2(2b)) in which e is the
        #   error rate
        self.bucket_size = bucket_size
        self.max_kicks = max_kicks

        # Save the error rate to calculate the correct fingerprint size
        self.error_rate = error_rate if error_rate else CuckooFilter.DEFAULT_ERROR_RATE

        # A long fingerprint reduces the FPP rate but does not contribute much to the load
        # factor of the filter according to the research. In our implementation, we choose
        # to calculate the minimal fingerprint size using the target error rate and the
        # bucket size
        self.fingerprint_size = int(math.ceil(math.log(1.0 / self.error_rate, 2) + math.log(2 * self.bucket_size, 2)))

        # Initialize the list of bucket
        self.buckets = [None] * self.capacity

        # The current number of items in the filter
        self.size = 0


    def insert(self, item):
        '''
        Insert an into the filter, throw an exception if the filter is full and the insertion fails.
        '''
        # Generate the fingerprint
        fingerprint = self.fingerprint(item)

        # Save it here to use it later when all available bucket are full
        indices = []

        for index in self.indices(item, fingerprint):
            indices.append(index)

            if self.buckets[index] is None:
                # Initialize the bucket if needed
                self.buckets[index] = Bucket(size=self.bucket_size)

            if self.buckets[index].insert(fingerprint):
                # Update the number of items in the filter
                self.size = self.size + 1
                return index

        # If all available buckets are full, we need to kick / move some fingerprint around
        index = random.choice(indices)

        for _ in range(self.max_kicks):
            # Swap the item's fingerprint with a fingerprint in the bucket
            fingerprint = self.buckets[index].swap(fingerprint)

            # Compute the potential bucket to move the swapped fingerprint to
            index = (index ^ self.index(fingerprint)) % self.capacity

            if self.buckets[index] is None:
                # Initialize the bucket if needed
                self.buckets[index] = Bucket(size=self.bucket_size)

            if self.buckets[index].insert(fingerprint):
                # Update the number of items in the filter
                self.size = self.size + 1
                return index

        raise CapacityException('Cuckoo filter is approaching its capacity ({0}/{1})'.format(self.size, self.capacity))


    def contains(self, item):
        '''
        Check if an item is in the filter, return false if it does not exist.
        '''
        # Generate the fingerprint
        fingerprint = self.fingerprint(item)

        # TODO: investigate if it is possible to devise a novel approach in which
        # there could be more than 2 indexes as it is currently used by partial-key
        # Cuckoo hashing
        for index in self.indices(item, fingerprint):
            if self.buckets[index] is None:
                # Initialize the bucket if needed
                self.buckets[index] = Bucket(size=self.bucket_size)

            if fingerprint in self.buckets[index]:
                return True

        return False


    def delete(self, item):
        '''
        Remove an item from the filter, return false if it does not exist.
        '''
        # Generate the fingerprint
        fingerprint = self.fingerprint(item)

        for index in self.indices(item, fingerprint):
            if self.buckets[index] is None:
                # Initialize the bucket if needed
                self.buckets[index] = Bucket(size=self.bucket_size)

            if self.buckets[index].delete(fingerprint):
                # Update the number of items in the filter
                self.size = self.size - 1
                return True

        return False


    def index(self, item):
        '''
        Calculate the (first) index of an item in the filter.
        '''
        item_hash = mmh3.hash_bytes(item)
        # Because of this modular computation, it will be tricky to increase the
        # capacity of the filter directly
        return int(codecs.encode(item_hash, 'hex'), 16) % self.capacity


    def indices(self, item, fingerprint):
        '''
        Calculate all possible indices for the item.
        '''
        index = self.index(item)
        indices = [index]

        # TODO: this is partial-key Cuckoo hashing, investigate if it is possible
        # to devise a novel approach in which there could be more than 2 indices
        indices.append((index ^ self.index(fingerprint)) % self.capacity)

        for index in indices:
            yield index


    def fingerprint(self, item):
        '''
        Take an item and returns its fingerprint in bits.  The fingerprint of an item
        is computed by truncating its Murmur hashing (murmur3) to the fingerprint size.
        '''
        item_hash = mmh3.hash_bytes(item)
        # Only get up to the size of the fingerprint
        return item_hash[:self.fingerprint_size]


    def load_factor(self):
        '''
        Provide some useful details about the current state of the filter.
        '''
        return round(float(self.size) / (self.capacity * self.bucket_size), 4)


    def __contains__(self, item):
        return self.contains(item)


    def __repr__(self):
        return '<CuckooFilter: size={0}, capacity={1}, fingerprint_size={2}, bucket_size={3}>'.format(
            self.size, self.capacity, self.fingerprint_size, self.bucket_size)


    def __sizeof__(self):
        return super(self.__class__, self).__sizeof__() + sum(b.__sizeof__() for b in self.buckets)


class ScalableCuckooFilter(object):
    '''
    Implement a scalable Cuckoo filter which has the ability to extend its capacity dynamically.
    '''
    SCALE_FACTOR = 2

    # pylint: disable=unused-argument
    def __init__(self, capacity, error_rate, bucket_size=4, max_kicks=500):
        '''
        Initialize Cuckoo filter parameters.

        capacity: The size of the filter, it defines how many buckets the filter contains.

        error_rate: The desired error rate, the lower the error rate and the bigger the
            bucket size, the longer the fingerprint needs to be.

        bucket_size : The maximum number of fingerprints a bucket can hold.  Default size
            is 4, which closely approaches the best size for FPP between 0.00001 and 0.002
            (see Fan et al.).  Also according to the author, if your targeted FPP is greater
            than 0.002, a bucket size of 2 is more space efficient.

        max_kicks : The number of times entries are kicked / moved around before the filter
            is considered full.  Defaults to 500 used by Fan et al. in the above paper.
        '''
        self.filters = []

        # Initialize the first Cuckoo filter
        self.filters.append(CuckooFilter(capacity, error_rate, bucket_size, max_kicks))


    def insert(self, item):
        '''
        Insert an into the filter, when the filter approaches its capacity, increasing it.
        '''
        for cuckoo in reversed(self.filters):
            try:
                # Using this naive approach, items will always be added into the last or
                # the biggest filter first.  If all filters are full, new one will be created
                return cuckoo.insert(item)

            except CapacityException:
                # Fail to insert the item
                pass

        last_filter = self.filters[-1]
        # Fail to insert the item in all available filters, create a new one
        capacity = last_filter.capacity * ScalableCuckooFilter.SCALE_FACTOR

        # Everything else is the same, for now
        bucket_size = last_filter.bucket_size
        error_rate = last_filter.error_rate
        max_kicks = last_filter.max_kicks

        # Create a new Cuckoo filter with more capacity
        self.filters.append(CuckooFilter(capacity, error_rate, bucket_size, max_kicks))

        # Add the item into the new and bigger filter
        return self.filters[-1].insert(item)


    def contains(self, item):
        '''
        Check if an item is in the filter, return false if it does not exist.
        '''
        for cuckoo in reversed(self.filters):
            if item in cuckoo:
                return True

        return False


    def delete(self, item):
        '''
        Remove an item from the filter, return false if it does not exist.
        '''
        # Using this naive approach, items can be removed from old filters make them
        # them under capacity (usable) again
        for cuckoo in reversed(self.filters):
            if cuckoo.delete(item):
                return True

        return False


    def __contains__(self, item):
        return self.contains(item)


    def __repr__(self):
        # Sum the number of items across all filters and theirs total capacity
        size, capacity = reduce(lambda a, b: (a[0] + b[0], a[1] + b[1]), ((f.size, f.capacity) for f in self.filters))

        return '<ScalableCuckooFilter: size={0}, capacity={1}, fingerprint_size={2}, bucket_size={3}>'.format(
            size, capacity, self.filters[-1].fingerprint_size, self.filters[-1].bucket_size)


    def __sizeof__(self):
        return super(self.__class__, self).__sizeof__() + sum(f.__sizeof__() for f in self.filters)
