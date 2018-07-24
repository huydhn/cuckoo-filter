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
from abc import ABCMeta, abstractmethod
from functools import reduce

import mmh3
from bitarray import bitarray
from cuckoo.bucket import Bucket
from cuckoo.exception import CapacityException, InconsistencyException


class CuckooTemplate(object):
    '''
    The base template of a Cuckoo filter.  Do not use this
    directly.
    '''
    __metaclass__ = ABCMeta

    # The default error rate or FP rate of the Cuckoo filter.
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

        # The current number of items in the filter
        self.size = 0


    @abstractmethod
    def insert(self, item):
        '''
        Insert an into the filter, throw an exception if the filter is full and the insertion fails.
        '''
        pass


    @abstractmethod
    def contains(self, item):
        '''
        Check if an item is in the filter, return false if it does not exist.
        '''
        pass


    @abstractmethod
    def delete(self, item):
        '''
        Remove an item from the filter, return false if it does not exist.
        '''
        pass


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
        Calculate all possible indices for the item.  The fingerprint must be a
        bit array.
        '''
        index = self.index(item)
        indices = [index]

        # TODO: this is partial-key Cuckoo hashing, investigate if it is possible
        # to devise a novel approach in which there could be more than 2 indices
        indices.append((index ^ self.index(fingerprint.tobytes())) % self.capacity)

        for index in indices:
            yield index


    def fingerprint(self, item):
        '''
        Take an item and returns its fingerprint in bits.  The fingerprint of an item
        is computed by truncating its Murmur hashing (murmur3) to the fingerprint size.

        Return a bit array representation of the fingerprint.
        '''
        mmh3_hash = bitarray()
        mmh3_hash.frombytes(mmh3.hash_bytes(item))
        # Only get up to the size of the fingerprint
        return mmh3_hash[:self.fingerprint_size]


    def load_factor(self):
        '''
        Provide some useful details about the current state of the filter.
        '''
        return round(float(self.size) / (self.capacity * self.bucket_size), 4)


class CuckooFilter(CuckooTemplate):
    '''
    Implement the text book Cuckoo filter.
    '''
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
        super(CuckooFilter, self).__init__(capacity, error_rate, bucket_size, max_kicks)

        # Store a list of buckets like such is very Pythonic-ly wasteful cause there could
        # be millions of such objects and Python object is unacceptably big.
        self.buckets = [None] * self.capacity


    def insert(self, item):
        '''
        Insert an into the filter, throw an exception if the filter is full and the insertion fails.
        '''
        # Generate the fingerprint in bit array format
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

        # Keep the original index here so that it can be returned later
        original_index = index

        # Keep all the swapped fingerprints here so we can restore them later
        fingerprint_stack = [fingerprint]
        index_stack = [index]

        # TODO: find a way to improve this so that we can minimize the need to move
        # fingerprints around
        for _ in range(self.max_kicks):
            # Swap the item's fingerprint with a fingerprint in the bucket
            fingerprint = self.buckets[index].swap(fingerprint)

            # Save the swapped fingerprint here so we can restore it later
            fingerprint_stack.append(fingerprint)

            # Compute the potential bucket to move the swapped fingerprint to
            index = (index ^ self.index(fingerprint.tobytes())) % self.capacity

            # Save the index here so we can restore it later
            index_stack.append(index)

            if self.buckets[index] is None:
                # Initialize the bucket if needed
                self.buckets[index] = Bucket(size=self.bucket_size)

            if self.buckets[index].insert(fingerprint):
                # Update the number of items in the filter
                self.size = self.size + 1

                # Return the original index here cause that's where the original item
                # is saved
                return original_index

        if len(fingerprint_stack) != len(index_stack):
            # This is a serious error.  I don't expect this to happen but who knows.
            raise InconsistencyException('Cuckoo filter becomes inconsistent, continue at your own risk')

        # When the filter reaches its capacity, we will rewind the fingerprints stack and
        # restore them so that there are no change to the list of existing fingerprints.
        while len(fingerprint_stack) > 1:
            fingerprint = fingerprint_stack.pop()
            index = index_stack.pop()

            if not self.buckets[index_stack[-1]].find_and_replace(look_for=fingerprint_stack[-1],
                                                                  replace_with=fingerprint):
                # This is a serious error.  I don't expect this to happen but who knows
                raise InconsistencyException('Cuckoo filter becomes inconsistent')

        # After restoring fingerprints successfully, raise the capacity exception
        raise CapacityException('Cuckoo filter is approaching its capacity ({0}/{1})'.format(self.size, self.capacity))


    def contains(self, item):
        '''
        Check if an item is in the filter, return false if it does not exist.
        '''
        # Generate the fingerprint in bit array format
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
        # Generate the fingerprint in bit array format
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


    def __contains__(self, item):
        return self.contains(item)


    def __repr__(self):
        return '<CuckooFilter: size={0}, capacity={1}, fingerprint_size={2}, bucket_size={3}>'.format(
            self.size, self.capacity, self.fingerprint_size, self.bucket_size)


    def __sizeof__(self):
        return super(self.__class__, self).__sizeof__() + sum(b.__sizeof__() for b in self.buckets)


class BCuckooFilter(CuckooTemplate):
    '''
    Implement a compact Cuckoo filter using bit array so that it can keep millions of items.
    '''
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
        super(BCuckooFilter, self).__init__(capacity, error_rate, bucket_size, max_kicks)

        # The key different here is that the list of buckets is practically compressed
        # inside a bit array structure.  It solves the memory issue when Python object
        # is unnecessarily big.  It is a trade-off between speed and efficiency, using
        # the Bucket class is very easy but inefficient.
        #
        # The size of the structure will be capacity * bucket_size * fingerprint_size
        self.buckets = bitarray(self.capacity * self.bucket_size * self.fingerprint_size)

        # Empty the bit array
        self.buckets.setall(False)


    def _bit_index(self, index):
        '''
        Convert a bucket index to its location, bit index, in the bit array.
        '''
        sbit = self.bucket_size * self.fingerprint_size * index
        ebit = self.bucket_size * self.fingerprint_size * (index + 1)

        # Return the starting and ending bits of the bucket
        return (sbit, ebit)


    def _delete(self, fingerprint, index):
        '''
        Delete a fingerprint from the specified bucket.  Return False if
        there is no such fingerprint.
        '''
        start_bit, end_bit = self._bit_index(index)

        for i in range(start_bit, end_bit, self.fingerprint_size):
            if fingerprint == self.buckets[i:i + self.fingerprint_size]:
                # Wipe out the fingerprint
                self.buckets[i:i + self.fingerprint_size] = False
                return True

        return False


    def _find_and_replace(self, look_for, replace_with, index):
        '''
        Find an exact fingerprint the specified bucket and replace it with
        another fingerprint.  Return False if there is no such fingerprint.
        '''
        start_bit, end_bit = self._bit_index(index)

        for i in range(start_bit, end_bit, self.fingerprint_size):
            if look_for == self.buckets[i:i + self.fingerprint_size]:
                # Replace it with another fingerprint
                self.buckets[i:i + self.fingerprint_size] = replace_with
                return True

        return False


    def _include(self, fingerprint, index):
        '''
        Check if a fingerprint exists in the bucket at the specified index.
        '''
        start_bit, end_bit = self._bit_index(index)

        for i in range(start_bit, end_bit, self.fingerprint_size):
            if fingerprint == self.buckets[i:i + self.fingerprint_size]:
                return True

        return False


    def _insert(self, fingerprint, index):
        '''
        Insert a fingerprint into the bucket at the specified index.  Basically, it set
        the corresponding bits in the bucket:

                Bucket               Bucket
        ------------------------------------------ ...
        | F1 | F2 | F3 | F4 || F1 | F2 | F3 | F4 |

        When the bucket is full (all bits are set), the function will return False.
        '''
        start_bit, end_bit = self._bit_index(index)

        for i in range(start_bit, end_bit, self.fingerprint_size):
            stored_fingerprint = self.buckets[i:i + self.fingerprint_size]

            if stored_fingerprint.count(True):
                # if the fingerprint has been set (having a bit set), leave it alone
                continue

            self.buckets[i:i + self.fingerprint_size] = fingerprint
            # An empty slot has been found, save the fingerprint there then return
            return True

        # All fingerprints have been set, the bucket is full
        return False


    def _swap(self, fingerprint, index):
        '''
        Swap a fingerprint with a random fingerprint of the bucket at the specified index.
        '''
        start_bit, end_bit = self._bit_index(index)

        size = self.fingerprint_size
        # Get the bit index of a random fingerprint in the bucket
        rindex = random.choice([i for i in range(start_bit, end_bit, size) if fingerprint != self.buckets[i:i + size]])

        # There is tricky bug in swap function when an item is added several times.
        # In such case, there is a chance that a fingerprint is swapped with itself
        # thus trying to move fingerprints around won't work.
        #
        # Assuming that the bucket size is 4, the maximum number of times an item
        # can be added is 4 * 2 = 8.
        #
        # TODO: Investigate if there is a better solution for this cause this is
        # a form of local limit of Cuckoo filter.

        # Swap the two fingerprints
        swap_out = self.buckets[rindex:rindex + self.fingerprint_size]
        self.buckets[rindex:rindex + self.fingerprint_size] = fingerprint

        # and return the one from the bucket
        return swap_out


    def insert(self, item):
        '''
        Insert an into the filter, throw an exception if the filter is full and the insertion fails.
        '''
        # Generate the fingerprint in bit array format
        fingerprint = self.fingerprint(item)

        # Save it here to use it later when all available bucket are full
        indices = []

        for index in self.indices(item, fingerprint):
            indices.append(index)

            if self._insert(fingerprint, index):
                # Update the number of items in the filter
                self.size = self.size + 1
                return index

        # If all available buckets are full, we need to kick / move some fingerprint around
        index = random.choice(indices)

        # Keep the original index here so that it can be returned later
        original_index = index

        # Keep all the swapped fingerprints here so we can restore them later
        fingerprint_stack = [fingerprint]
        index_stack = [index]

        # TODO: find a way to improve this so that we can minimize the need to move
        # fingerprints around
        for _ in range(self.max_kicks):
            # Swap the item's fingerprint with a fingerprint in the bucket
            fingerprint = self._swap(fingerprint, index)

            # Save the swapped fingerprint here so we can restore it later
            fingerprint_stack.append(fingerprint)

            # Compute the potential bucket to move the swapped fingerprint to
            index = (index ^ self.index(fingerprint.tobytes())) % self.capacity

            # Save the index here so we can restore it later
            index_stack.append(index)

            if self._insert(fingerprint, index):
                # Update the number of items in the filter
                self.size = self.size + 1

                # Return the original index here cause that's where the original item
                # is saved
                return original_index

        if len(fingerprint_stack) != len(index_stack):
            # This is a serious error.  I don't expect this to happen but who knows.
            raise InconsistencyException('Cuckoo filter becomes inconsistent, continue at your own risk')

        # When the filter reaches its capacity, we will rewind the fingerprints stack and
        # restore them so that there are no change to the list of existing fingerprints.
        while len(fingerprint_stack) > 1:
            fingerprint = fingerprint_stack.pop()
            index = index_stack.pop()

            if not self._find_and_replace(look_for=fingerprint_stack[-1],
                                          replace_with=fingerprint,
                                          index=index_stack[-1]):
                # This is a serious error.  I don't expect this to happen but who knows
                raise InconsistencyException('Cuckoo filter becomes inconsistent')

        # After restoring fingerprints successfully, raise the capacity exception
        raise CapacityException('Cuckoo filter is approaching its capacity ({0}/{1})'.format(self.size, self.capacity))


    def contains(self, item):
        '''
        Check if an item is in the filter, return false if it does not exist.
        '''
        # Generate the fingerprint in bit array format
        fingerprint = self.fingerprint(item)

        # TODO: investigate if it is possible to devise a novel approach in which
        # there could be more than 2 indexes as it is currently used by partial-key
        # Cuckoo hashing
        for i in self.indices(item, fingerprint):
            if self._include(fingerprint, i):
                return True

        return False


    def delete(self, item):
        '''
        Remove an item from the filter, return false if it does not exist.
        '''
        # Generate the fingerprint in bit array format
        fingerprint = self.fingerprint(item)

        for index in self.indices(item, fingerprint):
            if self._delete(fingerprint, index):
                # Update the number of items in the filter
                self.size = self.size - 1
                return True

        return False


    def __contains__(self, item):
        return self.contains(item)


    def __repr__(self):
        return '<BCuckooFilter: size={0}, capacity={1}, fingerprint_size={2}, bucket_size={3}>'.format(
            self.size, self.capacity, self.fingerprint_size, self.bucket_size)


    def __sizeof__(self):
        return super(self.__class__, self).__sizeof__()


class ScalableCuckooFilter(object):
    '''
    Implement a scalable Cuckoo filter which has the ability to extend its capacity dynamically.
    '''
    SCALE_FACTOR = 2

    # The original work shows that a Cuckoo filter can have a load factor up to 95.5% (Table 2)
    # so we choose a threshold of 90% here as a conservative threshold.  It means that do not
    # try to use the filter when its load factor is larger than 90% because of its worsening
    # performance
    THRESHOLD_LOAD_FACTOR = 0.90

    # pylint: disable=unused-argument
    def __init__(self, initial_capacity, error_rate, bucket_size=4, max_kicks=500):
        '''
        Initialize Cuckoo filter parameters.

        initial_capacity: The initial size of the filter, it defines how many buckets the
            first filter contains.

        error_rate: The desired error rate, the lower the error rate and the bigger the
            bucket size, the longer the fingerprint needs to be.

        bucket_size : The maximum number of fingerprints a bucket can hold.  Default size
            is 4, which closely approaches the best size for FPP between 0.00001 and 0.002
            (see Fan et al.).  Also according to the author, if your targeted FPP is greater
            than 0.002, a bucket size of 2 is more space efficient.

        max_kicks : The number of times entries are kicked / moved around before the filter
            is considered full.  Defaults to 500 used by Fan et al. in the above paper.
        '''
        # Naive approached #1: use multiple Cuckoo filters with different capacities
        self.filters = []

        # Initialize the first Cuckoo filter
        self.filters.append(BCuckooFilter(initial_capacity, error_rate, bucket_size, max_kicks))


    def insert(self, item):
        '''
        Insert an into the filter, when the filter approaches its capacity, increasing it.
        '''
        for cuckoo in reversed(self.filters):
            # Do not wait until the capacity exception is raised cause it will degrade the
            # filter performance by having too many fingerprints being moved around. If a
            # filter has a load factor larger than x %, we don't use it anymore.
            if cuckoo.load_factor() > ScalableCuckooFilter.THRESHOLD_LOAD_FACTOR:
                continue

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
        self.filters.append(BCuckooFilter(capacity, error_rate, bucket_size, max_kicks))

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
