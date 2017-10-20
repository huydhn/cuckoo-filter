'''
Cuckoo filter internal bucket.
'''
import random


class Bucket(object):
    '''
    Bucket class for storing fingerprints.
    '''

    def __init__(self, size=4):
        '''
        Initialize a dynamic or static bucket to keep a set of Cuckoo fingerprints.

        size: The maximum number of fingerprints the bucket can store.
              Default size is 4, which closely approaches the best size for FPP between 0.00001 and 0.002 (see Fan et al.).
              If your targeted FPP is greater than 0.002, a bucket size of 2 is more space efficient.
        '''
        self.size = size

        # The bucket is implemented as an array cause it's possible to have multiple items with the same fingerprints.
        self.bucket = []


    def insert(self, fingerprint):
        '''
        Insert a fingerprint into the bucket, the fingerprint basically is just a bit vector.  The longer the bit vector,
        the lower the collision rate.

        The insertion of duplicate entries is allowed.
        '''
        if not self.is_full():
            self.bucket.append(fingerprint)
            # When the bucket is not full, just append the fingerprint there and return
            return True

        else:
            # In static mode, the size of the bucket is fixed.  It means that the
            # filter is reaching its capacity here.
            return False


    def contains(self, fingerprint):
        '''
        Check if this bucket contains the provided fingerprint.
        '''
        return fingerprint in self.bucket


    def delete(self, fingerprint):
        '''
        Delete a fingerprint from the bucket.

        Returns True if the fingerprint was present in the bucket.
        This is useful for keeping track of how many items are present in the filter.
        '''
        try:
            del self.bucket[self.bucket.index(fingerprint)]
            return True

        except ValueError:
            # No such fingerprint in the bucket
            return False


    def swap(self, fingerprint):
        '''
        Swap a fingerprint with a randomly chosen fingerprint from the bucket.

        The given fingerprint is stored in the bucket.
        The swapped fingerprint is returned.
        '''
        bucket_index = random.choice(range(len(self.bucket)))

        # Swap the two fingerprints
        fingerprint, self.bucket[bucket_index] = self.bucket[bucket_index], fingerprint
        # and return the one from the bucket
        return fingerprint


    def is_full(self):
        '''
        Signify that the bucket is full, a fingerprint will need to be swapped out.
        '''
        return len(self.bucket) >= self.size


    def __contains__(self, fingerprint):
        return self.contains(fingerprint)


    def __repr__(self):
        return '<Bucket: {0}>'.format(self.bucket)


    def __sizeof__(self):
        # pylint: disable=missing-super-argument
        return super().__sizeof__() + self.bucket.__sizeof__()
