'''
We are now dealing with a more advance group of probabilistic filters whose
members can expire after some time, for example, time-decaying Bloom filter
by Dautrich et al. "Inferential time-decaying Bloom filters". Proceedings of
the 16th International Conference on Extending Database Technology. ACM, 2013.

In cuckoo filter, the idea is that if we can somehow encode a timestamp into
the fingerprint, we will be able to know if that fingerprint is still active.
In other words, if the fingerprint is older than a certain threshold, it could
be expunged from the filter and its space freed up.

Approach No. 1
--------------
fingerprint = fingerprint + encode_ts(int(time.time()))

def encode_ts(ts):
    # As an example, unit will be 1 for second. The higher level of the
    # granularity, the more costly it is to store the timestamp.
    d = (ts-start_ts)/unit

    # TODO
    d = compress(d)

    return d
'''
