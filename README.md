Experiment with Cuckoo filters
------------------------------

A Cuckoo filter is a data structure for probabilistic set-membership
queries with a low false positive probability (FPP). As an improvement
over the classic Bloom filter, items can be added or removed into
Cuckoo filters at will. A Cuckoo filter also utilizes space more
efficiently.

Cuckoo filters were originally described in:
 Fan, B., Andersen, D. G., Kaminsky, M., & Mitzenmacher, M. D. (2014, December).
 Cuckoo filter: Practically better than bloom.
 In Proceedings of the 10th ACM International on Conference on emerging Networking
 Experiments and Technologies (pp. 75-88). ACM.

This package implements the basic Cuckoo filter as well as several
derivations built on top of it.

Classic Cuckoo filter
---------------------

```python
import math

from random import randrange
from cuckoo.filter import CuckooFilter

capacity = 1000000
error_rate = 0.000001
# Create a classic Cuckoo filter with a fixed capacity of 1000000
# buckets
cuckoo = CuckooFilter(capacity=capacity, error_rate=error_rate)

bucket_size = 6
# Setting the bucket size is optional, the bigger the bucket,
# the more number of items a filter can hold, and the longer
# the fingerprint needs to be to stay at the same error rate
cuckoo = CuckooFilter(capacity=capacity, error_rate=error_rate, bucket_size=bucket_size)

# The fingerprint length is computed using the following formula:
fingerprint_size = int(math.ceil(math.log(1.0 / error_rate, 2) + math.log(2 * bucket_size, 2)))

for _ in range(1, 100000):
    item = str(randrange(1, 1000000000))
    cuckoo.insert(item)

    if cuckoo.contains(item):
        print '{} has been added'.format(item)

    cuckoo.delete(item)

    if not cuckoo.contains(item):
        print '{} has been removed'.format(item)
```

Bitarray Cuckoo filter
----------------------

A classic Cuckoo filter is implemented using a Python list of Bucket
objects. Each Bucket, again, stores a fixed list of fingerprints. The
implementation is easy and straightforward but unnecessary wasteful
for applications that needs to keep hundreds of millions of items.

The bitarray Cuckoo filter is built to deal with such situation. The
whole filter is compressed into a bitarray to minimize memory usage.
For example, a bitarray Cuckoo filter with capacity of 100.000.000,
bucket size of 4, and error rate of 0.000001 will requires:

- 23-bit fingerprint, computed using the above formula.
- 9.200.000.000 bits = 1.08 GB = capacity * bucket size * fingerprint.

And it can theoretically store up to 400.000.000 items at full capacity.

```python
import math

from random import randrange
from cuckoo.filter import BCuckooFilter

capacity = 1000000
error_rate = 0.000001
# Create a bit array Cuckoo filter with a fixed capacity of 1000000
# buckets
cuckoo = BCuckooFilter(capacity=capacity, error_rate=error_rate)

bucket_size = 6
# Setting the bucket size is optional, the bigger the bucket,
# the more number of items a filter can hold, and the longer
# the fingerprint needs to be to stay at the same error rate
cuckoo = BCuckooFilter(capacity=capacity, error_rate=error_rate, bucket_size=bucket_size)

# The fingerprint length is computed using the following formula:
fingerprint_size = int(math.ceil(math.log(1.0 / error_rate, 2) + math.log(2 * bucket_size, 2)))

for _ in range(1, 100000):
    item = str(randrange(1, 1000000000))
    cuckoo.insert(item)

    if cuckoo.contains(item):
        print '{} has been added'.format(item)

    cuckoo.delete(item)

    if not cuckoo.contains(item):
        print '{} has been removed'.format(item)
```

Scalable Cuckoo filter
----------------------

Having a fix capacity is a problem when using Cuckoo filter in practice.
Allocating too much capacity and it goes to waste while allocating too
little and it degrades the filter performance and causes FP. Therefore,
the scalable Cuckoo filter is introduced as an attempt to solve the fix
capacity issue.

Inspired by Scalable Bloom filter, Scalable Cuckoo filter utilizes
multiple filters to scale the capacity dynamically.  When an existing
filter approaches its capacity, a new one, double in size, will be
created.  A scalable Cuckoo filter will handle all usual operations
seamlessly and transparently.

Internally, scalable Cuckoo filter uses bitarray Cuckoo filter for
efficiency although it can be changed easily.

```python
import math

from random import randrange
from cuckoo.filter import ScalableCuckooFilter

initial_capacity = 1000000
error_rate = 0.000001
# Create a scalable Cuckoo filter with an initial capacity of 1000000
# buckets
cuckoo = ScalableCuckooFilter(initial_capacity=initial_capacity, error_rate=error_rate)

bucket_size = 6
# Setting the bucket size is optional, the bigger the bucket,
# the more number of items a filter can hold, and the longer
# the fingerprint needs to be to stay at the same error rate
cuckoo = ScalableCuckooFilter(initial_capacity=initial_capacity, error_rate=error_rate, bucket_size=bucket_size)

# The fingerprint length is computed using the following formula:
fingerprint_size = int(math.ceil(math.log(1.0 / error_rate, 2) + math.log(2 * bucket_size, 2)))

for _ in range(1, 100000):
    item = str(randrange(1, 1000000000))
    cuckoo.insert(item)

    if cuckoo.contains(item):
        print '{} has been added'.format(item)

    cuckoo.delete(item)

    if not cuckoo.contains(item):
        print '{} has been removed'.format(item)
```
