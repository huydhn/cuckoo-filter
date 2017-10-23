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
import mmh3

from cuckoo.bucket import Bucket


class CuckooFilter(object):
    '''
    Implement a text book Cuckoo filter.
    '''

    def __init__(self, capacity, fingerprint_size, bucket_size=4, max_kicks=500):
        '''
        Initialize Cuckoo filter parameters.

        capacity: The size of the filter, it defines how many buckets the filter contains.

        fingerprint_size: The size of the fingerprint in bytes, a larger fingerprint size
            results in a lower FPP.

        bucket_size : The maximum number of fingerprints a bucket can hold.  Default size
            is 4, which closely approaches the best size for FPP between 0.00001 and 0.002
            (see Fan et al.).  Also according to the author, if your targeted FPP is greater
            than 0.002, a bucket size of 2 is more space efficient.

        max_kicks : The number of times entries are kicked / moved around before the filter
            is considered full.  Defaults to 500 used by Fan et al. in the above paper.
        '''
        # TODO: investigate if it is possible to extend the capacity dynamically if needed
        self.capacity = capacity

        # TODO: investigate if it is possible to increase fingerprint size if needed
        self.fingerprint_size = fingerprint_size

        # TODO: investigate if it is possible to extend the bucket size dynamically if needed
        self.bucket_size = bucket_size
        self.max_kicks = max_kicks

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

        raise Exception('Cuckoo filter is approaching its capacity ({0}/{1})'.format(self.size, self.capacity))


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
        # TODO: because of this modular computation, it will be tricky to increase the
        # capacity of the filter directly
        return int(codecs.encode(item_hash, 'hex'), 16) % self.capacity
        # Double check if they are the same
        # int.from_bytes(item_hash, byteorder='big')


    def indices(self, item, fingerprint):
        '''
        Calculate all possible indices for the item
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
        return '<CuckooFilter: size={0}, capacity={1}, fingerprint={2}, bucket={3}'.format(
            self.size, self.capacity, self.fingerprint_size, self.bucket_size)


    def __sizeof__(self):
        # pylint: disable=missing-super-argument
        return super().__sizeof__() + self.size
